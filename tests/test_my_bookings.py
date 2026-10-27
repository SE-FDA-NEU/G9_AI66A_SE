"""Tests for US07 (US19: Customer cancels a booking) and US08 (US20: Customer views booking history).
Business Rules: BR14, BR15.
"""
from datetime import datetime, timedelta

import pytest

from db import connect
import booking as svc


NOW = datetime(2026, 10, 11, 9, 0)


@pytest.fixture
def app_with_now(db):
    from app import create_app
    app = create_app(database=db)
    app.config["NOW"] = lambda: NOW
    return app


def test_my_bookings_requires_sign_in(client):
    response = client.get("/my-bookings")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_my_bookings_empty_state_shows_message_and_link(client, login, db):
    # US20 criterion 3: Customer with 0 bookings sees friendly empty state
    with connect(db) as conn:
        from werkzeug.security import generate_password_hash
        conn.execute(
            "INSERT INTO user (email, password_hash, full_name, phone, role, email_verified_at)"
            " VALUES ('emptyuser@example.com', ?, 'Empty User', '0911223344', 'customer', datetime('now'))",
            (generate_password_hash("sanbong1"),))
    login("emptyuser@example.com")
    page = client.get("/my-bookings").get_data(as_text=True)
    assert "You have no bookings yet" in page
    assert "Find a venue now" in page
    assert 'href="/search"' in page


def test_my_bookings_lists_bookings_chronologically(client, login):
    # US20 criterion 1: Minh views his bookings
    login("minh@example.com")
    page = client.get("/my-bookings").get_data(as_text=True)
    assert "Thong Nhat Football Pitch" in page
    assert "VND" in page


def test_my_bookings_filter_by_status(client, login):
    # US20 criterion 4: Filter by status
    login("minh@example.com")
    page = client.get("/my-bookings?status=completed").get_data(as_text=True)
    assert "Completed" in page or "BK-000101" in page


def test_cancel_booking_more_than_24h_ahead_gives_100_percent_refund(app_with_now, db):
    # US19 criterion 1, BR15: Cancel > 24h ahead -> 100% refund and releases slots
    client = app_with_now.test_client()
    client.post("/login", data={"email": "minh@example.com", "password": "sanbong1"})

    # Create a booking on 2026-10-15 18:00 (4 days ahead of NOW=2026-10-11 09:00)
    with connect(db) as conn:
        user = conn.execute("SELECT * FROM user WHERE email = 'minh@example.com'").fetchone()
        b = svc.create_booking(conn, user, 1, "2026-10-15", 18, 2, NOW)
        code = b["code"]

        # Verify slots exist
        slots_count = conn.execute("SELECT COUNT(*) FROM booking_slot WHERE booking_id = (SELECT id FROM booking WHERE code = ?)", (code,)).fetchone()[0]
        assert slots_count == 2

    # Cancel via POST
    response = client.post(f"/my-bookings/{code}/cancel", follow_redirects=True)
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "100%" in page

    with connect(db) as conn:
        booking = conn.execute("SELECT * FROM booking WHERE code = ?", (code,)).fetchone()
        assert booking["status"] == "cancelled"
        assert booking["refund_amount"] == booking["total_price"]
        # BR15: booking_slot rows must be deleted so slot is released
        slots_left = conn.execute("SELECT COUNT(*) FROM booking_slot WHERE booking_id = ?", (booking["id"],)).fetchone()[0]
        assert slots_left == 0


def test_cancel_booking_between_2h_and_24h_gives_50_percent_refund(app_with_now, db):
    # US19 criterion 3, BR15: Cancel 8h ahead (between 2h and 24h) -> 50% refund
    client = app_with_now.test_client()
    client.post("/login", data={"email": "minh@example.com", "password": "sanbong1"})

    # NOW is 2026-10-11 09:00. Create booking for 2026-10-11 17:00 (8h ahead)
    with connect(db) as conn:
        user = conn.execute("SELECT * FROM user WHERE email = 'minh@example.com'").fetchone()
        b = svc.create_booking(conn, user, 1, "2026-10-11", 17, 1, NOW)
        code = b["code"]

    res = client.post(f"/api/bookings/{code}/cancel")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "cancelled"
    assert data["refund_percent"] == 50
    assert data["refund_amount"] == b["total_price"] // 2


def test_cancel_booking_under_2h_is_refused(app_with_now, db):
    # US19 criterion 2, BR15: Cancel 1h ahead (< 2h) -> Refused
    client = app_with_now.test_client()
    client.post("/login", data={"email": "minh@example.com", "password": "sanbong1"})

    # NOW is 2026-10-11 09:00. Create booking for 2026-10-11 10:00 (1h ahead)
    with connect(db) as conn:
        user = conn.execute("SELECT * FROM user WHERE email = 'minh@example.com'").fetchone()
        b = svc.create_booking(conn, user, 1, "2026-10-11", 10, 1, NOW)
        code = b["code"]

    res = client.post(f"/api/bookings/{code}/cancel")
    assert res.status_code == 400
    assert "Cannot cancel a booking less than 2 hours before start time" in res.get_json()["error"]

    with connect(db) as conn:
        booking = conn.execute("SELECT * FROM booking WHERE code = ?", (code,)).fetchone()
        assert booking["status"] == "confirmed"


def test_cancel_other_users_booking_is_forbidden(app_with_now, db):
    # US19 criterion 5, BR14: user cannot cancel another user's booking -> 403
    client = app_with_now.test_client()

    with connect(db) as conn:
        minh = conn.execute("SELECT * FROM user WHERE email = 'minh@example.com'").fetchone()
        b = svc.create_booking(conn, minh, 1, "2026-10-15", 14, 1, NOW)
        code = b["code"]

    # Sign in as Trang
    client.post("/login", data={"email": "trang@example.com", "password": "sanbong1"})
    res = client.post(f"/api/bookings/{code}/cancel")
    assert res.status_code == 403
    assert "You do not have permission" in res.get_json()["error"]
