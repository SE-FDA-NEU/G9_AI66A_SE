"""Tests for US10 (US23: Venue owner views list of bookings).
Business Rules: BR16, BR17, BR18.
"""
from datetime import datetime

import pytest

from db import connect
import booking as svc


NOW = datetime(2026, 10, 11, 9, 0)
TODAY = "2026-10-11"


@pytest.fixture
def app_with_now(db):
    from app import create_app
    app = create_app(database=db)
    app.config["NOW"] = lambda: NOW
    return app


def test_owner_bookings_requires_owner_role(client, login):
    # Customer gets 403
    login("minh@example.com")
    res = client.get("/owner/bookings")
    assert res.status_code == 403


def test_owner_bookings_defaults_to_current_date_and_shows_title(app_with_now, db):
    # US23 AC 1, BR16: defaults to current date and displays count
    client = app_with_now.test_client()
    client.post("/login", data={"email": "lan.owner@example.com", "password": "sanbong1"})

    # Lan owns venue 1 and 2. Let's create 2 bookings on TODAY (2026-10-11)
    with connect(db) as conn:
        minh = conn.execute("SELECT * FROM user WHERE email = 'minh@example.com'").fetchone()
        svc.create_booking(conn, minh, 1, TODAY, 14, 1, NOW)
        svc.create_booking(conn, minh, 1, TODAY, 16, 2, NOW)

    page = client.get("/owner/bookings").get_data(as_text=True)
    assert f"2 bookings on 11/10/2026" in page
    assert "Thong Nhat Football Pitch" in page


def test_owner_bookings_shows_all_six_columns(app_with_now, db):
    # US23 AC 3, BR17: 6 columns: code, venue name, hours, customer name, phone, status
    client = app_with_now.test_client()
    client.post("/login", data={"email": "lan.owner@example.com", "password": "sanbong1"})

    with connect(db) as conn:
        minh = conn.execute("SELECT * FROM user WHERE email = 'minh@example.com'").fetchone()
        b = svc.create_booking(conn, minh, 1, TODAY, 10, 1, NOW)
        code = b["code"]

    page = client.get(f"/owner/bookings?date={TODAY}").get_data(as_text=True)
    assert code in page
    assert "Thong Nhat Football Pitch" in page
    assert "10:00-11:00" in page
    assert "Pham Duc Minh" in page
    assert "0901234567" in page
    assert "Confirmed" in page


def test_owner_bookings_empty_date_shows_explicit_message(app_with_now):
    # US23 AC 4: Empty date shows "Không có lịch đặt ngày DD/MM/YYYY"
    client = app_with_now.test_client()
    client.post("/login", data={"email": "lan.owner@example.com", "password": "sanbong1"})

    page = client.get("/owner/bookings?date=2026-12-25").get_data(as_text=True)
    assert "No bookings on 25/12/2026" in page


def test_owner_bookings_filter_by_venue(app_with_now, db):
    # US23 AC 5: Filter by venue updates count and list
    client = app_with_now.test_client()
    client.post("/login", data={"email": "lan.owner@example.com", "password": "sanbong1"})

    with connect(db) as conn:
        minh = conn.execute("SELECT * FROM user WHERE email = 'minh@example.com'").fetchone()
        svc.create_booking(conn, minh, 1, TODAY, 11, 1, NOW)  # venue 1
        svc.create_booking(conn, minh, 2, TODAY, 12, 1, NOW)  # venue 2

    # Filter venue 1
    page1 = client.get(f"/owner/bookings?date={TODAY}&venue_id=1").get_data(as_text=True)
    assert "1 booking on 11/10/2026 - Thong Nhat Football Pitch" in page1

    # Filter venue 2
    page2 = client.get(f"/owner/bookings?date={TODAY}&venue_id=2").get_data(as_text=True)
    assert "1 booking on 11/10/2026 - Lan Anh Badminton Court" in page2


def test_owner_cannot_view_booking_detail_of_another_owner(app_with_now, db):
    # US23 AC 6, BR18: Cross-owner booking access returns 403 Forbidden
    client = app_with_now.test_client()

    with connect(db) as conn:
        minh = conn.execute("SELECT * FROM user WHERE email = 'minh@example.com'").fetchone()
        # Venue 5 (NEU Football Pitch) is owned by Hung, not Lan!
        b = svc.create_booking(conn, minh, 5, TODAY, 14, 1, NOW)
        code = b["code"]

    # Sign in as Lan
    client.post("/login", data={"email": "lan.owner@example.com", "password": "sanbong1"})
    res = client.get(f"/owner/bookings/{code}")
    assert res.status_code == 403
    assert "You do not have permission to view this booking" in res.get_data(as_text=True)
