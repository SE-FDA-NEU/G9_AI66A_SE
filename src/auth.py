"""Accounts: registration and email verification (US01), signing in (US02).
Accounts: signing in (US02).

Every rule about accounts lives here, not in the routes. Functions take the database
connection and the current time, so a test can check BR5 without waiting 15 minutes.
"""
import hashlib
import hmac
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
    if not isinstance(email, str) or not isinstance(password, str):
        raise BusinessRuleError(401, WRONG_SIGN_IN, "BR6")
    normalized_email = email.strip().casefold()
    user = conn.execute("SELECT * FROM user WHERE lower(email) = ?", (normalized_email,)).fetchone()
    if user is None:
        # BR6: the same sentence as a wrong password, so nobody learns which emails exist
        raise BusinessRuleError(401, WRONG_SIGN_IN, "BR6")

    if user["locked_until"] and user["locked_until"] > now.strftime(TIME_FORMAT):
        raise BusinessRuleError(423, LOCKED, "BR5")

    if not check_password_hash(user["password_hash"], password):
        conn.execute(
            "UPDATE user SET failed_login_count = failed_login_count + 1 WHERE id = ?",
            (user["id"],),
        )
        row = conn.execute(
            "SELECT failed_login_count FROM user WHERE id = ?",
            (user["id"],),
        ).fetchone()
        if row and row["failed_login_count"] >= MAX_FAILED_SIGN_INS:
            # BR5: the 5th wrong password in a row locks the account for 15 minutes
            locked_until = (now + LOCK_TIME).strftime(TIME_FORMAT)
            conn.execute(
                "UPDATE user SET failed_login_count = 0, locked_until = ? WHERE id = ?",
                (locked_until, user["id"]),
            )
            conn.commit()
            raise BusinessRuleError(423, LOCKED, "BR5")
        conn.commit()
        raise BusinessRuleError(401, WRONG_SIGN_IN, "BR6")

    if user["suspended"]:
        reason = user["suspended_reason"] or "Policy violation"
        raise BusinessRuleError(403, f"Your account has been suspended. Reason: {reason}", "BR14")

    # BR5: a successful sign-in resets the counter to 0
    conn.execute("UPDATE user SET failed_login_count = 0, locked_until = NULL WHERE id = ?",
                 (user["id"],))
    conn.commit()
    return user


def check_registration(conn, email, password, full_name, phone):
    """Return one BusinessRuleError per broken rule - an empty list when all is well.
    Every field is checked at once, so the user can fix everything in one go."""
    email = email.strip().casefold() if isinstance(email, str) else ""
    password = password if isinstance(password, str) else ""
    full_name = full_name.strip() if isinstance(full_name, str) else ""
    phone = phone.strip() if isinstance(phone, str) else ""
    problems = []
    if not EMAIL_PATTERN.match(email):
        problems.append(BusinessRuleError(400, "Please enter a valid email address", None, "email"))
    elif conn.execute("SELECT 1 FROM user WHERE lower(email) = ?", (email,)).fetchone():
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
    elif conn.execute("SELECT 1 FROM user WHERE phone = ?", (phone,)).fetchone():
        problems.append(BusinessRuleError(409, "This phone number is already in use", "BR3", "phone"))
    return problems


def raise_user_unique_conflict(conn, phone, exc):
    """Raise the appropriate 409 BusinessRuleError for a unique user constraint violation."""
    if "phone" in str(exc).lower() or conn.execute("SELECT 1 FROM user WHERE phone = ?", (phone,)).fetchone():
        raise BusinessRuleError(409, "This phone number is already in use", "BR3", "phone") from None
    raise BusinessRuleError(409, "This email is already in use", "BR1", "email") from None


def register(conn, email, password, full_name, phone):
    """Create a customer account. It cannot book until its email is verified (BR4).
    Return the new user id, or raise the first broken rule."""
    email = email.strip().casefold() if isinstance(email, str) else ""
    full_name = full_name.strip() if isinstance(full_name, str) else ""
    phone = phone.strip() if isinstance(phone, str) else ""
    problems = check_registration(conn, email, password, full_name, phone)
    if problems:
        raise problems[0]
    try:
        cur = conn.execute(
            "INSERT INTO user (email, password_hash, full_name, phone, role) VALUES (?, ?, ?, ?, 'customer')",
            (email, generate_password_hash(password), full_name, phone))
    except Exception as exc:
        if (
            isinstance(exc, sqlite3.IntegrityError)
            or type(exc).__name__ == "IntegrityError"
            or getattr(exc, "pgcode", None) == "23505"
        ):
            # BR1 / BR3: someone registered the same email or phone between check and insert
            raise_user_unique_conflict(conn, phone, exc)
        raise
    conn.commit()
    return cur.lastrowid


def _serializer(secret_key):
    return URLSafeSerializer(secret_key, salt="verify-email")


def make_verify_token(secret_key, user_id, now):
    """A signed token holding the user id and the time it was made.

    Signing means nobody can forge one for another account; the time lets
    verify_email() apply the 24 hour limit (BR4).
    """
    return _serializer(secret_key).dumps({"user": user_id, "at": now.strftime(TIME_FORMAT)})


def verify_email(conn, secret_key, token, now):
    """Mark the account as verified. Return its user id.
    """
    try:
        data = _serializer(secret_key).loads(token)
    except BadSignature:
        raise BusinessRuleError(
            404, "This verification link is not valid. Check that you copied the whole link.") from None
    if now - datetime.strptime(data["at"], TIME_FORMAT) > VERIFY_LINK_LIFETIME:
        raise BusinessRuleError(
            410, "This verification link has expired - links last 24 hours. Sign in and press"
            " \"Send a new link\" to get a fresh one.", "BR4")
    user = conn.execute("SELECT id, email_verified_at FROM user WHERE id = ?", (data["user"],)).fetchone()
    if user and not user["email_verified_at"]:
        conn.execute(
            "UPDATE user SET email_verified_at = ? WHERE id = ?",
            (now.strftime(TIME_FORMAT), data["user"]),
        )
        conn.commit()
    return data["user"]


def check_password(password):
    """Validate password strength according to BR2."""
    if not isinstance(password, str) or len(password) < 8:
        raise BusinessRuleError(400, "Password must be at least 8 characters", "BR2", "password")
    if not (re.search(r"[A-Za-z]", password) and re.search(r"\d", password)):
        raise BusinessRuleError(
            400, "Password must contain at least one letter and one digit", "BR2", "password")


def _reset_serializer(secret_key):
    return URLSafeSerializer(secret_key, salt="reset-password")


def _password_fingerprint(password_hash):
    return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()[:16]


def make_reset_token(secret, user_id, password_hash, now):
    """Create a signed, single-use password reset token bound to the current password hash."""
    return _reset_serializer(secret).dumps({
        "user": user_id,
        "at": now.strftime(TIME_FORMAT),
        "pw": _password_fingerprint(password_hash),
    })


def peek_reset_token_user_id(secret, token):
    """Verify the token signature and return the embedded user_id."""
    try:
        data = _reset_serializer(secret).loads(token)
        user_id = data["user"]
    except (BadSignature, KeyError, TypeError):
        raise BusinessRuleError(400, "This password reset link is invalid or has expired.") from None
    return user_id


def verify_reset_token(secret, token, password_hash, now, max_age=3600):
    """Verify a password reset token's signature, expiry, and password fingerprint."""
    try:
        data = _reset_serializer(secret).loads(token)
        created_at = datetime.strptime(data["at"], TIME_FORMAT)
        user_id = data["user"]
        pw_fp = data["pw"]
    except (BadSignature, KeyError, TypeError, ValueError):
        raise BusinessRuleError(400, "This password reset link is invalid or has expired.") from None

    if (now - created_at).total_seconds() > max_age:
        raise BusinessRuleError(410, "This password reset link has expired. Please request a new one.")

    expected_fp = _password_fingerprint(password_hash)
    if not isinstance(pw_fp, str) or not hmac.compare_digest(pw_fp, expected_fp):
        raise BusinessRuleError(
            400, "This password reset link is no longer valid because the password has already been changed.")
    return user_id


def reset_password(conn, user_id, new_password):
    """Validate BR2, update password_hash, and clear any login lockout."""
    check_password(new_password)
    conn.execute(
        "UPDATE user SET password_hash = ?, failed_login_count = 0, locked_until = NULL WHERE id = ?",
        (generate_password_hash(new_password), user_id),
    )
    conn.commit()


def change_password(conn, user_id, current_password, new_password):
    """Verify current_password, validate BR2 on new_password, and update password_hash."""
    user = conn.execute("SELECT id, password_hash FROM user WHERE id = ?", (user_id,)).fetchone()
    if user is None:
        raise BusinessRuleError(404, "User account not found.")
    if not isinstance(current_password, str) or not check_password_hash(user["password_hash"], current_password):
        raise BusinessRuleError(400, "Current password is incorrect.", field="current_password")
    check_password(new_password)
    conn.execute(
        "UPDATE user SET password_hash = ? WHERE id = ?",
        (generate_password_hash(new_password), user_id),
    )
    conn.commit()
