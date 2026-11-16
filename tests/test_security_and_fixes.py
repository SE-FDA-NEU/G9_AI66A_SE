"""Tests for security hardening (CSRF, rate limiting, password reset, role guards) and bug fixes."""
from datetime import date, datetime, timedelta
import re

from app import create_app
import auth
import booking as booking_svc
from db import connect
from db_compat import CompatRow
from errors import BusinessRuleError
import pytest
import reviews
from routes.auth import safe_next
import venues


def _make_app(db, tmp_path, **extra_config):
    """Build an isolated Flask test app with optional config overrides."""
    app = create_app(database=db)
    app.config["TESTING"] = True
    app.config["UPLOAD_DIR"] = tmp_path / "uploads"
    app.config.update(extra_config)
    return app


def _extract_csrf_token(html):
    """Extract the hidden csrf_token value from rendered HTML."""
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    assert match, "Expected csrf_token hidden input in HTML"
    return match.group(1)


def test_csrf_missing_token_returns_400_and_valid_tokens_succeed(db, tmp_path):
    """CSRF_ENABLED=True rejects missing tokens with 400 and accepts form or header tokens."""
    app = _make_app(db, tmp_path, CSRF_ENABLED=True)
    client = app.test_client()

    res_missing = client.post("/login", data={"email": "minh@example.com", "password": "sanbong1"})
    assert res_missing.status_code == 400

    login_html = client.get("/login").get_data(as_text=True)
    token = _extract_csrf_token(login_html)

    res_form = client.post(
        "/login",
        data={"email": "minh@example.com", "password": "sanbong1", "csrf_token": token},
    )
    assert res_form.status_code == 302
    assert res_form.headers["Location"].endswith("/dashboard")

    dashboard_html = client.get("/dashboard").get_data(as_text=True)
    session_token = _extract_csrf_token(dashboard_html)
    res_header = client.post("/logout", headers={"X-CSRFToken": session_token})
    assert res_header.status_code == 302


def test_ratelimit_allows_20_requests_and_blocks_21st_with_429(db, tmp_path):
    """RATELIMIT_ENABLED=True permits 20 POST requests and returns 429 on the 21st."""
    app = _make_app(db, tmp_path, RATELIMIT_ENABLED=True)
    client = app.test_client()

    for _ in range(20):
        res = client.post("/forgot-password", data={"email": "nobody@example.com"})
        assert res.status_code in (200, 302)

    blocked = client.post("/forgot-password", data={"email": "nobody@example.com"})
    assert blocked.status_code == 429


def test_forgot_password_non_enumeration(client):
    """POST /forgot-password shows the same neutral message for known and unknown emails."""
    known = client.post("/forgot-password", data={"email": "minh@example.com"}, follow_redirects=True)
    unknown = client.post("/forgot-password", data={"email": "unknown@example.com"}, follow_redirects=True)

    assert known.status_code == 200
    assert unknown.status_code == 200
    expected = "If an account with that email exists, we sent a password reset link."
    assert expected in known.get_data(as_text=True)
    assert expected in unknown.get_data(as_text=True)


def test_reset_password_expiry_single_use_and_br2_validation(client, db, monkeypatch):
    """Reset token expires after 1 hour, enforces BR2, and is single-use."""
    monkeypatch.setenv("SHOW_VERIFICATION_LINK", "1")
    with connect(db) as conn:
        user = conn.execute("SELECT id, password_hash FROM user WHERE email = ?", ("minh@example.com",)).fetchone()

    expired_token = auth.make_reset_token(
        client.application.config["SECRET_KEY"],
        user["id"],
        user["password_hash"],
        datetime.now() - timedelta(hours=1, minutes=1),
    )
    res_expired = client.get(f"/reset-password?token={expired_token}")
    assert res_expired.status_code == 410

    res_forgot = client.post("/forgot-password", data={"email": "minh@example.com"}, follow_redirects=True)
    match = re.search(r"http://[^\"<\s]+/reset-password\?token=([^\"<\s]+)", res_forgot.get_data(as_text=True))
    assert match, "Reset link not flashed on screen"
    token = match.group(1)

    res_weak = client.post(
        "/reset-password",
        data={"token": token, "new_password": "short", "confirm_password": "short"},
    )
    assert res_weak.status_code == 400
    assert "at least 8 characters" in res_weak.get_data(as_text=True)

    res_ok = client.post(
        "/reset-password",
        data={"token": token, "new_password": "newpass1", "confirm_password": "newpass1"},
    )
    assert res_ok.status_code == 302

    res_reuse = client.post(
        "/reset-password",
        data={"token": token, "new_password": "another1", "confirm_password": "another1"},
    )
    assert res_reuse.status_code == 400


def test_account_password_change_enforces_br2_and_updates_password(client, login):
    """POST /account/password validates BR2 complexity and updates the signed-in user's password."""
    login("minh@example.com")

    res_weak = client.post(
        "/account/password",
        data={"current_password": "sanbong1", "new_password": "onlyletters", "confirm_password": "onlyletters"},
    )
    assert res_weak.status_code == 400
    assert "letter and one digit" in res_weak.get_data(as_text=True)

    res_ok = client.post(
        "/account/password",
        data={"current_password": "sanbong1", "new_password": "updated1", "confirm_password": "updated1"},
    )
    assert res_ok.status_code == 302

    client.post("/logout")
    assert client.post("/login", data={"email": "minh@example.com", "password": "updated1"}).status_code == 302


def test_owner_analytics_and_csv_export_require_owner_role(client, login):
    """Customers receive 403 on /owner/analytics and /owner/bookings/export.csv (BR14)."""
    login("minh@example.com")
    assert client.get("/owner/analytics").status_code == 403
    assert client.get("/owner/bookings/export.csv").status_code == 403


def test_submit_review_allows_confirmed_booking_past_end_at(db):
    """BR18 allows reviewing a confirmed booking once its end_at timestamp has passed."""
    with connect(db) as conn:
        user = conn.execute("SELECT id, full_name FROM user WHERE email = ?", ("minh@example.com",)).fetchone()
        past_day = (date.today() - timedelta(days=2)).isoformat()
        start_at = f"{past_day} 08:00"
        end_at = f"{past_day} 09:00"
        code = "BK-990001"
        conn.execute(
            "INSERT INTO booking (code, customer_id, venue_id, start_at, end_at, total_price, status)"
            " VALUES (?, ?, 1, ?, ?, 300000, 'confirmed')",
            (code, user["id"], start_at, end_at),
        )
        conn.commit()

        reviews.submit_review(conn, code, user, 5, "Great pitch after match!")
        saved = conn.execute(
            "SELECT r.rating, r.comment FROM review r JOIN booking b ON b.id = r.booking_id WHERE b.code = ?",
            (code,),
        ).fetchone()
        assert saved["rating"] == 5
        assert saved["comment"] == "Great pitch after match!"


def test_batch_block_slots_atomic_per_day_skip_and_out_of_range_hour_400(db, client, login):
    """batch_block_slots skips an entire day atomically if any hour is booked, and invalid hours return 400."""
    day1 = date.today() + timedelta(days=15)
    day2 = day1 + timedelta(days=1)
    now = datetime.combine(date.today(), datetime.min.time())

    with connect(db) as conn:
        owner = conn.execute("SELECT * FROM user WHERE email = ?", ("lan.owner@example.com",)).fetchone()
        customer = conn.execute("SELECT * FROM user WHERE email = ?", ("minh@example.com",)).fetchone()
        booking_svc.create_booking(conn, customer, 1, day1, 10, 1, now=now)

        blocked_count, skipped = venues.batch_block_slots(
            conn, owner, 1, day1, day2, 9, 12, reason="Repainting", now=now
        )
        assert len(skipped) == 1
        assert blocked_count == 3

        day1_blocks = conn.execute(
            "SELECT COUNT(*) FROM blocked_slot WHERE venue_id = 1 AND slot_start LIKE ?",
            (f"{day1.isoformat()}%",),
        ).fetchone()[0]
        assert day1_blocks == 0

        with pytest.raises(BusinessRuleError) as exc_info:
            venues.batch_block_slots(conn, owner, 1, day2, day2, 25, 26, reason="Invalid", now=now)
        assert exc_info.value.status == 400

    login("lan.owner@example.com")
    res_bad_hour = client.post(
        "/owner/venues/1/schedule/batch-block",
        data={
            "start_date": day2.isoformat(),
            "end_date": day2.isoformat(),
            "start_hour": "25",
            "end_hour": "26",
            "reason": "Invalid",
        },
        follow_redirects=True,
    )
    assert res_bad_hour.status_code == 200
    assert "Time range must be within opening hours" in res_bad_hour.get_data(as_text=True)


def test_compat_row_normalize_preserves_zero_seconds():
    """CompatRow._normalize formats zero-second timestamps as YYYY-MM-DD HH:MM and non-zero with :SS."""
    dt_zero = datetime(2026, 11, 16, 14, 30, 0)
    dt_sec = datetime(2026, 11, 16, 14, 30, 45)
    assert CompatRow._normalize(dt_zero) == "2026-11-16 14:30"
    assert CompatRow._normalize(dt_sec) == "2026-11-16 14:30:45"


def test_safe_next_rejects_backslash_open_redirect():
    """safe_next rejects backslash-prefixed protocol-relative redirect targets."""
    assert safe_next("/\\evil.com") is None
    assert safe_next("//evil.com") is None
    assert safe_next("/my-bookings") == "/my-bookings"
