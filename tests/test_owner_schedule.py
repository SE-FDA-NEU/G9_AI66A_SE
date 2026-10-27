"""Tests for US09 (US22: Venue owner manages availability schedule).
Business Rules: BR13, BR14, BR15 (BR16, BR17 in requirements.md).
"""
from datetime import datetime

import pytest

from db import connect
import booking as svc


NOW = datetime(2026, 10, 11, 9, 0)
TOMORROW = "2026-10-12"


@pytest.fixture
def app_with_now(db):
    from app import create_app
    app = create_app(database=db)
    app.config["NOW"] = lambda: NOW
    return app


def test_schedule_requires_owner_role(client, login):
    # Customer is rejected with 403
    login("minh@example.com")
    res = client.get("/owner/venues/1/schedule")
    assert res.status_code == 403


def test_owner_blocks_slot_and_it_disappears_from_customer_view(app_with_now, db):
    # US22 AC 1, BR13: Block slot 18:00-19:00 on TOMORROW with reason
    client = app_with_now.test_client()
    client.post("/login", data={"email": "lan.owner@example.com", "password": "sanbong1"})

    # Check slot is initially free in customer API
    slots_before = client.get(f"/api/venues/1?date={TOMORROW}").get_json()["slots"]
    s18_before = next(s for s in slots_before if s["hour"] == 18)
    assert s18_before["status"] == "free"

    # Owner blocks 18:00
    res = client.post("/owner/venues/1/schedule/block", data={
        "date": TOMORROW,
        "hour": 18,
        "reason": "Grass maintenance",
    }, follow_redirects=True)
    assert res.status_code == 200

    # On owner schedule, slot shows "Blocked - Grass maintenance"
    owner_page = client.get(f"/owner/venues/1/schedule?date={TOMORROW}").get_data(as_text=True)
    assert "Blocked - Grass maintenance" in owner_page

    # On customer API /venues/1, slot is now blocked / no longer free (BR13)
    slots_after = client.get(f"/api/venues/1?date={TOMORROW}").get_json()["slots"]
    s18_after = next(s for s in slots_after if s["hour"] == 18)
    assert s18_after["status"] == "blocked"


def test_owner_unblocks_slot_and_it_becomes_free_immediately(app_with_now, db):
    # US22 AC 2, BR13: Unblocking immediately restores slot to free
    client = app_with_now.test_client()
    client.post("/login", data={"email": "lan.owner@example.com", "password": "sanbong1"})

    # Block 19:00
    client.post("/owner/venues/1/schedule/block", data={
        "date": TOMORROW, "hour": 19, "reason": "Sửa đèn"
    })

    # Unblock 19:00
    res = client.post("/owner/venues/1/schedule/unblock", data={
        "date": TOMORROW, "hour": 19
    }, follow_redirects=True)
    assert res.status_code == 200

    # Slot is immediately free for customers
    slots = client.get(f"/api/venues/1?date={TOMORROW}").get_json()["slots"]
    s19 = next(s for s in slots if s["hour"] == 19)
    assert s19["status"] == "free"


def test_block_slot_with_active_booking_is_refused(app_with_now, db):
    # US22 AC 3, BR14: Cannot block slot that already has a booking
    client = app_with_now.test_client()
    client.post("/login", data={"email": "lan.owner@example.com", "password": "sanbong1"})

    # Minh books slot 19:00-20:00 on TOMORROW
    with connect(db) as conn:
        minh = conn.execute("SELECT * FROM user WHERE email = 'minh@example.com'").fetchone()
        b = svc.create_booking(conn, minh, 1, TOMORROW, 19, 1, NOW)
        code = b["code"]

    # Owner attempts to block 19:00
    res = client.post("/api/owner/venues/1/block", json={
        "date": TOMORROW, "hour": 19, "reason": "Bảo trì"
    })
    assert res.status_code == 409
    body = res.get_json()
    assert f"Cannot block: this slot is already booked ({code}). Cancel booking first." in body["error"]


def test_block_slot_in_the_past_is_refused(app_with_now):
    # US22 AC 4, BR15: Cannot block past slots (NOW is 2026-10-11 09:00)
    client = app_with_now.test_client()
    client.post("/login", data={"email": "lan.owner@example.com", "password": "sanbong1"})

    # Try to block 08:00 on 2026-10-11 (past)
    res = client.post("/api/owner/venues/1/block", json={
        "date": "2026-10-11", "hour": 8, "reason": "Bảo trì"
    })
    assert res.status_code == 400
    assert "Can only block slots starting after current time" in res.get_json()["error"]


def test_batch_block_slots_reports_blocked_and_skipped(app_with_now, db):
    # US22 AC 5: Batch blocking across days, reporting count and skipping booked slot
    client = app_with_now.test_client()
    client.post("/login", data={"email": "lan.owner@example.com", "password": "sanbong1"})

    # Create a booking on 2026-10-13 06:00
    with connect(db) as conn:
        minh = conn.execute("SELECT * FROM user WHERE email = 'minh@example.com'").fetchone()
        svc.create_booking(conn, minh, 1, "2026-10-13", 6, 1, NOW)

    # Batch block 2026-10-12 to 2026-10-14 from 06:00 to 07:00 (3 days)
    res = client.post("/owner/venues/1/schedule/batch-block", data={
        "start_date": "2026-10-12",
        "end_date": "2026-10-14",
        "start_hour": 6,
        "end_hour": 7,
        "reason": "Regular maintenance",
    }, follow_redirects=True)
    assert res.status_code == 200
    page = res.get_data(as_text=True)
    # 2 blocked (Oct 12 and Oct 14), 1 skipped (Oct 13)
    assert "Blocked 2 slot(s)" in page
    assert "Skipped 1 already booked slot(s)" in page


def test_cross_owner_schedule_management_is_forbidden(app_with_now):
    # Security: Lan cannot manage Hung's venue (venue 5)
    client = app_with_now.test_client()
    client.post("/login", data={"email": "lan.owner@example.com", "password": "sanbong1"})

    res = client.get("/owner/venues/5/schedule")
    assert res.status_code == 403
