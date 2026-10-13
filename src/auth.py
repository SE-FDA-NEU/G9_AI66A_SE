"""Accounts: signing in (US02).

Every rule about accounts lives here, not in the routes. Functions take the database
connection and the current time, so a test can check BR5 without waiting 15 minutes.
"""
from datetime import timedelta

from werkzeug.security import check_password_hash

from errors import BusinessRuleError

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

MAX_FAILED_SIGN_INS = 5                     # BR5
LOCK_TIME = timedelta(minutes=15)           # BR5

WRONG_SIGN_IN = "Email or password is incorrect"                     # BR6
LOCKED = "Account temporarily locked. Try again in 15 minutes"        # BR5

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
