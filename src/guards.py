"""Who is signed in, and the check every protected page runs first (BR7, BR8, BR14)."""
from datetime import datetime, timedelta
from functools import wraps

from flask import flash, g, redirect, request, session, url_for

from db import get_db
from errors import BusinessRuleError

SESSION_TIMEOUT = timedelta(minutes=30)     # BR8

NO_PERMISSION = "You do not have permission to access this page"     # BR14


def load_user():
    """Runs before every request: find the signed-in user, or end a session that has been
    idle for more than 30 minutes (BR8)."""
    g.user = None
    g.session_expired = False
    user_id = session.get("user_id")
    if user_id is None:
        return
    now = datetime.now()
    last_seen = session.get("last_seen")
    if last_seen and now - datetime.fromisoformat(last_seen) > SESSION_TIMEOUT:
        session.clear()
        g.session_expired = True
        return
    g.user = get_db().execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()
    session["last_seen"] = now.isoformat(timespec="seconds")


def start_session(user):
    session.clear()
    session.permanent = True
    session["user_id"] = user["id"]
    session["last_seen"] = datetime.now().isoformat(timespec="seconds")


def login_required(*roles):
    """Decorator for a page that needs a signed-in user - and, if roles are given, one of
    those roles. Example: @login_required("owner")."""
    def decorate(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if g.user is None:
                if request.path.startswith("/api/"):
                    raise BusinessRuleError(401, "Please sign in first", "BR8")
                if g.session_expired:
                    flash("Your session has expired", "error")              # BR8
                else:
                    flash("Please sign in to continue", "info")
                return redirect(url_for("auth.login_page", next=request.path))
            if roles and g.user["role"] not in roles:
                raise BusinessRuleError(403, NO_PERMISSION, "BR14")
            return view(*args, **kwargs)
        return wrapped
    return decorate
