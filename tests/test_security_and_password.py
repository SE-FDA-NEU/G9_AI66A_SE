"""Tests for CSRF protection, HTTP rate limiting, password reset, and password change."""
import re
from datetime import datetime, timedelta

import pytest

import auth
from app import create_app
from db import connect
from errors import BusinessRuleError


def _extract_csrf(html):
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    assert match, "Expected csrf_token hidden input in HTML"
    return match.group(1)


def _extract_reset_token(html):
    match = re.search(r'/reset-password\?token=([^"&<\s]+)', html)
    assert match, "Expected reset-password link in flash output"
    return match.group(1)


def test_csrf_rejects_missing_and_invalid_token_and_accepts_valid_token(db, tmp_path):
    app = create_app(database=db)
    app.config["UPLOAD_DIR"] = tmp_path / "uploads"
    app.config["TESTING"] = True
    app.config["CSRF_ENABLED"] = True
    client = app.test_client()

    # Missing CSRF token on POST /login -> 400
    resp = client.post("/login", data={"email": "minh@example.com", "password": "sanbong1"})
    assert resp.status_code == 400
    assert b"Invalid or missing CSRF token" in resp.data

    # Fetch login page to obtain session CSRF token
    page = client.get("/login")
    assert page.status_code == 200
    token = _extract_csrf(page.get_data(as_text=True))

    # Wrong CSRF token -> 400
    bad = client.post(
        "/login",
        data={"email": "minh@example.com", "password": "sanbong1", "csrf_token": "wrong-token"},
    )
    assert bad.status_code == 400

    # Valid CSRF token -> 302 redirect to /dashboard
    ok = client.post(
        "/login",
        data={"email": "minh@example.com", "password": "sanbong1", "csrf_token": token},
    )
    assert ok.status_code == 302
    assert ok.headers["Location"].endswith("/dashboard")


def test_csrf_skips_api_routes(db, tmp_path):
    app = create_app(database=db)
    app.config["UPLOAD_DIR"] = tmp_path / "uploads"
    app.config["TESTING"] = True
    app.config["CSRF_ENABLED"] = True
    client = app.test_client()

    resp = client.post("/api/auth/login", json={"email": "minh@example.com", "password": "sanbong1"})
    assert resp.status_code == 200


def test_rate_limit_returns_429_when_enabled(db, tmp_path):
    app = create_app(database=db)
    app.config["UPLOAD_DIR"] = tmp_path / "uploads"
    app.config["TESTING"] = True
    app.config["RATELIMIT_ENABLED"] = True
    app.config["RATELIMIT_MAX_REQUESTS"] = 5
    app.config["RATELIMIT_WINDOW_SECONDS"] = 60
    client = app.test_client()

    for _ in range(5):
        resp = client.post("/api/auth/login", json={"email": "minh@example.com", "password": "wrong"})
        assert resp.status_code in (401, 423)

    blocked = client.post("/api/auth/login", json={"email": "minh@example.com", "password": "wrong"})
    assert blocked.status_code == 429
    assert "Too many requests" in blocked.get_json()["error"]

    # HTML endpoint also enforces rate limit and returns 429
    for _ in range(5):
        client.post("/forgot-password", data={"email": "nobody@example.com"})
    html_blocked = client.post("/forgot-password", data={"email": "nobody@example.com"})
    assert html_blocked.status_code == 429


def test_forgot_and_reset_password_flow_and_single_use_invalidation(db, tmp_path):
    app = create_app(database=db)
    app.config["UPLOAD_DIR"] = tmp_path / "uploads"
    app.config["TESTING"] = True
    client = app.test_client()

    # Non-existent email still shows generic confirmation (no enumeration)
    resp_unknown = client.post("/forgot-password", data={"email": "unknown@example.com"}, follow_redirects=True)
    assert resp_unknown.status_code == 200
    assert "If an account with that email exists" in resp_unknown.get_data(as_text=True)
    assert "/reset-password?token=" not in resp_unknown.get_data(as_text=True)

    # Existing email generates reset link
    resp = client.post("/forgot-password", data={"email": "minh@example.com"}, follow_redirects=True)
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "If an account with that email exists" in body
    token = _extract_reset_token(body)

    # BR2 validation on reset-password (too short / missing digit)
    bad_pw = client.post(
        "/reset-password",
        data={"token": token, "new_password": "short", "confirm_password": "short"},
    )
    assert bad_pw.status_code == 400
    assert "at least 8 characters" in bad_pw.get_data(as_text=True)

    # Mismatched confirmation
    mismatch = client.post(
        "/reset-password",
        data={"token": token, "new_password": "newpass123", "confirm_password": "otherpass123"},
    )
    assert mismatch.status_code == 400
    assert "Passwords do not match" in mismatch.get_data(as_text=True)

    # Valid reset succeeds
    ok = client.post(
        "/reset-password",
        data={"token": token, "new_password": "newpass123", "confirm_password": "newpass123"},
    )
    assert ok.status_code == 302
    assert ok.headers["Location"].endswith("/login")

    # Old password fails, new password works
    assert client.post("/login", data={"email": "minh@example.com", "password": "sanbong1"}).status_code == 401
    assert client.post("/login", data={"email": "minh@example.com", "password": "newpass123"}).status_code == 302

    # Reusing the same reset token is rejected because password_hash changed
    reused_get = client.get(f"/reset-password?token={token}")
    assert reused_get.status_code == 400
    reused_post = client.post(
        "/reset-password",
        data={"token": token, "new_password": "another123", "confirm_password": "another123"},
    )
    assert reused_post.status_code == 400


def test_reset_token_expiry(db):
    with connect(db) as conn:
        user = conn.execute("SELECT id, password_hash FROM user WHERE email = 'minh@example.com'").fetchone()
    now = datetime(2026, 1, 1, 12, 0, 0)
    token = auth.make_reset_token("secret", user["id"], user["password_hash"], now)
    assert auth.verify_reset_token("secret", token, user["password_hash"], now + timedelta(minutes=30)) == user["id"]
    with pytest.raises(BusinessRuleError) as exc:
        auth.verify_reset_token("secret", token, user["password_hash"], now + timedelta(hours=2))
    assert exc.value.status == 410


def test_change_password_flow(db, tmp_path):
    app = create_app(database=db)
    app.config["UPLOAD_DIR"] = tmp_path / "uploads"
    app.config["TESTING"] = True
    client = app.test_client()

    # Requires sign-in
    assert client.get("/account/password").status_code == 302

    client.post("/login", data={"email": "minh@example.com", "password": "sanbong1"})
    assert client.get("/account/password").status_code == 200

    # Wrong current password
    wrong_curr = client.post(
        "/account/password",
        data={"current_password": "wrongpass1", "new_password": "updated123", "confirm_password": "updated123"},
    )
    assert wrong_curr.status_code == 400
    assert "Current password is incorrect" in wrong_curr.get_data(as_text=True)

    # BR2 violation on new password
    weak = client.post(
        "/account/password",
        data={"current_password": "sanbong1", "new_password": "onlyletters", "confirm_password": "onlyletters"},
    )
    assert weak.status_code == 400
    assert "at least one letter and one digit" in weak.get_data(as_text=True)

    # Valid change
    ok = client.post(
        "/account/password",
        data={"current_password": "sanbong1", "new_password": "updated123", "confirm_password": "updated123"},
    )
    assert ok.status_code == 302

    client.post("/logout")
    assert client.post("/login", data={"email": "minh@example.com", "password": "updated123"}).status_code == 302
