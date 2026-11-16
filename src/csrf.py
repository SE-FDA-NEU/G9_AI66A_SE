"""Session-based CSRF protection for HTML form and state-changing requests."""
import hmac
import os
import secrets

from flask import current_app, request, session

from errors import BusinessRuleError

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


def generate_csrf_token():
    """Return the per-session CSRF token, creating one if absent."""
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def validate_csrf():
    """Reject state-changing non-API requests without a matching CSRF token."""
    if request.method in SAFE_METHODS:
        return
    if request.path.startswith("/api/") and request.is_json:
        return
    is_testing = current_app.config.get("TESTING") or bool(os.environ.get("PYTEST_CURRENT_TEST"))
    if is_testing and not current_app.config.get("CSRF_ENABLED"):
        return

    expected = session.get("_csrf_token")
    submitted = request.form.get("csrf_token") or request.headers.get("X-CSRFToken")
    if (
        not expected
        or not isinstance(submitted, str)
        or not submitted
        or not hmac.compare_digest(expected, submitted)
    ):
        raise BusinessRuleError(400, "Invalid or missing CSRF token")


def init_csrf(app):
    """Register the Jinja csrf_token() helper and before_request validator."""
    app.jinja_env.globals["csrf_token"] = generate_csrf_token
    app.before_request(validate_csrf)
