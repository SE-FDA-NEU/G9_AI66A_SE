"""Accounts: registration and email verification (US01), signing in (US02).

Every rule about accounts lives here, not in the routes. Functions take the database
connection and the current time, so a test can check BR5 without waiting 15 minutes.
"""
import re
import sqlite3
from datetime import datetime, timedelta

from itsdangerous import BadSignature, URLSafeSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from errors import BusinessRuleError

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

MAX_FAILED_SIGN_INS = 5                     # BR5
LOCK_TIME = timedelta(minutes=15)           # BR5

WRONG_SIGN_IN = "Email or password is incorrect"                     # BR6
LOCKED = "Account temporarily locked. Try again in 15 minutes"        # BR5

VERIFY_LINK_LIFETIME = timedelta(hours=24)  # BR4

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_PATTERN = re.compile(r"^\d{10}$")

# BR7: where each role lands after signing in
LANDING_PAGE = {"customer": "/dashboard", "owner": "/owner/venues", "admin": "/admin"}


def sign_in(conn, email, password, now):
    """Return the user row, or raise BusinessRuleError (BR5, BR6)."""
    user = conn.execute("SELECT * FROM user WHERE email = ?", (email.strip(),)).fetchone()
    if user is None:
        # BR6: the same sentence as a wrong password, so nobody learns which emails exist
        raise BusinessRuleError(401, WRONG_SIGN_IN, "BR6")

    if user["locked_until"] and user["locked_until"] > now.strftime(TIME_FORMAT):
        raise BusinessRuleError(423, LOCKED, "BR5")

    if not check_password_hash(user["password_hash"], password):
        failed = user["failed_login_count"] + 1
        if failed >= MAX_FAILED_SIGN_INS:
            # BR5: the 5th wrong password in a row locks the account for 15 minutes
            locked_until = (now + LOCK_TIME).strftime(TIME_FORMAT)
            conn.execute("UPDATE user SET failed_login_count = 0, locked_until = ? WHERE id = ?",
                         (locked_until, user["id"]))
            conn.commit()
            raise BusinessRuleError(423, LOCKED, "BR5")
        conn.execute("UPDATE user SET failed_login_count = ? WHERE id = ?", (failed, user["id"]))
        conn.commit()
        raise BusinessRuleError(401, WRONG_SIGN_IN, "BR6")

    # BR5: a successful sign-in resets the counter to 0
    conn.execute("UPDATE user SET failed_login_count = 0, locked_until = NULL WHERE id = ?",
                 (user["id"],))
    conn.commit()
    return user


def check_registration(conn, email, password, full_name, phone):
    """Return one BusinessRuleError per broken rule - an empty list when all is well.
    Every field is checked at once, so the user can fix everything in one go."""
    problems = []
    if not EMAIL_PATTERN.match(email):
        problems.append(BusinessRuleError(400, "Please enter a valid email address", None, "email"))
    elif conn.execute("SELECT 1 FROM user WHERE email = ?", (email,)).fetchone():
        problems.append(BusinessRuleError(409, "This email is already in use", "BR1", "email"))
    if len(password) < 8:
        problems.append(BusinessRuleError(400, "Password must be at least 8 characters", "BR2", "password"))
    elif not (re.search(r"[A-Za-z]", password) and re.search(r"\d", password)):
        problems.append(BusinessRuleError(
            400, "Password must contain at least one letter and one digit", "BR2", "password"))
    if not full_name:
        problems.append(BusinessRuleError(400, "Please enter your full name", None, "full_name"))
    if not PHONE_PATTERN.match(phone):
        problems.append(BusinessRuleError(400, "Phone number must be 10 digits", "BR3", "phone"))
    elif not phone.startswith("0"):
        problems.append(BusinessRuleError(400, "Phone number must start with 0", "BR3", "phone"))
    return problems


def register(conn, email, password, full_name, phone):
    """Create a customer account. It cannot book until its email is verified (BR4).
    Return the new user id, or raise the first broken rule."""
    email, full_name, phone = email.strip(), full_name.strip(), phone.strip()
    problems = check_registration(conn, email, password, full_name, phone)
    if problems:
        raise problems[0]
    try:
        cur = conn.execute(
            "INSERT INTO user (email, password_hash, full_name, phone, role) VALUES (?, ?, ?, ?, 'customer')",
            (email, generate_password_hash(password), full_name, phone))
    except sqlite3.IntegrityError:
        # BR1: someone registered the same email between the check above and this insert
        raise BusinessRuleError(409, "This email is already in use", "BR1", "email") from None
    conn.commit()
    return cur.lastrowid


def _serializer(secret_key):
    return URLSafeSerializer(secret_key, salt="verify-email")


def make_verify_token(secret_key, user_id, now):
    """A signed token holding the user id and the time it was made. Signing means nobody
    can forge one for another account; the time lets verify_email() apply BR4's 24 hours."""
    return _serializer(secret_key).dumps({"user": user_id, "at": now.strftime(TIME_FORMAT)})


def verify_email(conn, secret_key, token, now):
    """Mark the account as verified. Return its user id."""
    try:
        data = _serializer(secret_key).loads(token)
    except BadSignature:
        raise BusinessRuleError(
            404, "This verification link is not valid. Check that you copied the whole link.") from None
    if now - datetime.strptime(data["at"], TIME_FORMAT) > VERIFY_LINK_LIFETIME:
        raise BusinessRuleError(
            410, "This verification link has expired - links last 24 hours. Sign in and press"
            " \"Send a new link\" to get a fresh one.", "BR4")
    conn.execute("UPDATE user SET email_verified_at = COALESCE(email_verified_at, ?) WHERE id = ?",
                 (now.strftime(TIME_FORMAT), data["user"]))
    conn.commit()
    return data["user"]
