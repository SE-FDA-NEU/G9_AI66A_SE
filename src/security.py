"""Shared security, CSRF, and DB error helpers."""
import hmac
import os
import secrets
import sqlite3

from flask import abort, current_app, request, session

try:
    import psycopg2
    _PG_INTEGRITY_ERROR = (psycopg2.IntegrityError,)
except ImportError:
    _PG_INTEGRITY_ERROR = ()


def is_integrity_error(exc):
    """Return True if exc is a SQLite or PostgreSQL IntegrityError."""
    return isinstance(exc, (sqlite3.IntegrityError,) + _PG_INTEGRITY_ERROR)


def is_valid_image_bytes(data, ext):
    """Verify basic image magic bytes matching the file extension (BR13/security)."""
    if not data:
        return False
    ext = ext.lower()
    if ext == ".png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in (".jpg", ".jpeg"):
        return data.startswith(b"\xff\xd8\xff")
    return False


def generate_csrf_token():
    """Return the per-session CSRF token, creating one if absent."""
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def validate_csrf():
    """Enforce CSRF token on state-changing form requests when CSRF is enabled."""
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return
    # Skip in pytest suites unless explicitly enabled via WTF_CSRF_ENABLED=True
    if (current_app.config.get("TESTING") or os.environ.get("PYTEST_CURRENT_TEST")) and not current_app.config.get("WTF_CSRF_ENABLED"):
        return
    if current_app.config.get("WTF_CSRF_ENABLED") is False:
        return
    # JSON APIs with application/json are not vulnerable to classic HTML form CSRF
    if request.path.startswith("/api/") and request.is_json:
        return

    expected = session.get("_csrf_token")
    submitted = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
    if not expected or not submitted or not hmac.compare_digest(str(expected), str(submitted)):
        abort(403, description="Invalid or missing CSRF token.")
