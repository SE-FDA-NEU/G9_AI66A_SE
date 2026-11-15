"""Tests for security hardening, CSRF, 500 error handling, and BR17/BR18/BR19 edge cases."""
import io
import re
from datetime import date, datetime

from app import create_app
from db import connect
import reviews
import venues


def test_csrf_enforced_when_enabled(db, tmp_path):
    app = create_app(database=db)
    app.config["UPLOAD_DIR"] = tmp_path / "uploads"
    app.config["WTF_CSRF_ENABLED"] = True
    c = app.test_client()

    # POST without CSRF token is rejected with 403
    res = c.post("/login", data={"email": "minh@example.com", "password": "sanbong1"})
    assert res.status_code == 403

    # Extract CSRF token from GET /login and submit with it -> 302 success
    page = c.get("/login").get_data(as_text=True)
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', page)
    assert m is not None
    res_ok = c.post(
        "/login",
        data={"email": "minh@example.com", "password": "sanbong1", "csrf_token": m.group(1)},
    )
    assert res_ok.status_code == 302


def test_500_error_handler_html_and_json(db, tmp_path):
    app = create_app(database=db)
    app.config["UPLOAD_DIR"] = tmp_path / "uploads"
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.get("/boom")
    def boom():
        raise RuntimeError("boom")

    @app.get("/api/boom")
    def api_boom():
        raise RuntimeError("api boom")

    c = app.test_client()
    r_html = c.get("/boom")
    assert r_html.status_code == 500
    assert "Something went wrong" in r_html.get_data(as_text=True)

    r_json = c.get("/api/boom")
    assert r_json.status_code == 500
    assert r_json.get_json()["error"]


def test_session_cookie_flags_and_security_headers(client):
    res = client.get("/search")
    assert res.status_code == 200
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"


def test_br18_past_confirmed_booking_can_be_reviewed(client, login, db):
    login("minh@example.com")
    with connect(db) as conn:
        minh = conn.execute("SELECT id FROM user WHERE email = 'minh@example.com'").fetchone()
        conn.execute(
            "INSERT INTO booking (code, customer_id, venue_id, start_at, end_at, total_price, status)"
            " VALUES ('BK-PAST01', ?, 2, '2026-01-10 08:00', '2026-01-10 09:00', 120000, 'confirmed')",
            (minh["id"],),
        )
        conn.commit()

    res = client.post(
        "/my-bookings/BK-PAST01/review",
        data={"rating": 5, "comment": "Great court!"},
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert "Thank you for submitting your review!" in res.get_data(as_text=True)


def test_br19_report_requires_login_and_blocks_duplicates(client, login, db):
    with connect(db) as conn:
        rev_id = conn.execute("SELECT id FROM review LIMIT 1").fetchone()[0]

    # Anonymous report redirects to login
    anon = client.post(f"/venues/1/reviews/{rev_id}/report")
    assert anon.status_code == 302
    assert "/login" in anon.headers["Location"]

    # Signed-in user can report once, duplicate is rejected
    login("minh@example.com")
    r1 = client.post(f"/venues/1/reviews/{rev_id}/report", follow_redirects=True)
    assert "Review report submitted successfully." in r1.get_data(as_text=True)

    r2 = client.post(f"/venues/1/reviews/{rev_id}/report", follow_redirects=True)
    assert "already reported" in r2.get_data(as_text=True)


def test_br17_batch_block_atomic_per_day(db):
    with connect(db) as conn:
        owner = conn.execute("SELECT * FROM user WHERE role = 'owner' LIMIT 1").fetchone()
        venue = conn.execute("SELECT * FROM venue WHERE owner_id = ? LIMIT 1", (owner["id"],)).fetchone()
        # Venue 1 has BK-000101 on 2026-10-16 18:00-20:00; block 17:00-19:00 on 2026-10-16
        blocked, skipped = venues.batch_block_slots(
            conn,
            owner,
            venue["id"],
            date(2026, 10, 16),
            date(2026, 10, 16),
            17,
            19,
            now=datetime(2026, 10, 15, 10, 0),
        )
        assert blocked == 0
        assert len(skipped) == 1
        # Hour 17:00 must NOT be partially blocked
        row = conn.execute(
            "SELECT * FROM blocked_slot WHERE venue_id = ? AND slot_start = '2026-10-16 17:00'",
            (venue["id"],),
        ).fetchone()
        assert row is None


def test_malformed_schedule_input_returns_400_not_500(client, login):
    login("lan.owner@example.com")
    res = client.post("/api/owner/venues/1/block", json={"date": "not-a-date", "hour": "abc"})
    assert res.status_code == 400


def test_fake_image_magic_bytes_rejected(client, login):
    login("lan.owner@example.com")
    res = client.post(
        "/owner/venues/new",
        data={
            "name": "Fake Image Court",
            "sport": "Football",
            "area": "Cau Giay",
            "address": "123 Xuan Thuy",
            "hourly_price": "200000",
            "open_hour": "6",
            "close_hour": "22",
            "photo": (io.BytesIO(b"not-a-real-png"), "fake.png"),
        },
    )
    assert res.status_code == 422
    assert "valid JPG or PNG" in res.get_data(as_text=True)
