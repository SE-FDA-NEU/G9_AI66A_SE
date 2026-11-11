"""Tests for visual and timezone fixes (Milestone 4 / Sprint 4).

Covers:
1. Timezone consistency: time_utils.vn_now() returns valid naive UTC+7 time.
2. Past slot booking for today is rejected according to VN time.
3. Cancellation window logic (>=24h gives 100% refund, 2-24h gives 50% refund, <2h rejected with BR15).
4. Customer my_bookings correctly marks past/imminent bookings as non-cancellable or completed.
5. booking_done.html renders @media print CSS and proper h1 white color contrast.
"""
from datetime import date, datetime, timedelta, timezone

import pytest

import booking as svc
from app import create_app
from db import connect
from errors import BusinessRuleError
import time_utils


# -----------------------------------------------------------------------------
# Fixtures & Helpers
# -----------------------------------------------------------------------------

def _user(conn, email):
    return conn.execute("SELECT * FROM user WHERE email = ?", (email,)).fetchone()


def _make_app(db, now_fn=None):
    app = create_app(database=db)
    if now_fn:
        app.config["NOW"] = now_fn
    return app


def _client_for(db, email="minh@example.com", now_fn=None):
    app = _make_app(db, now_fn)
    client = app.test_client()
    with connect(db) as conn:
        u = _user(conn, email)
        assert u is not None, f"User {email} not found"
        user_id = u["id"]
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
    return client, app


# -----------------------------------------------------------------------------
# 1. Timezone consistency
# -----------------------------------------------------------------------------

def test_time_utils_vn_now_returns_valid_naive_utc_plus_7():
    """time_utils.vn_now() returns a naive datetime matching Vietnam UTC+7 offset."""
    vn_now = time_utils.vn_now()
    assert isinstance(vn_now, datetime)
    # Must be naive so SQLite comparisons with ISO strings don't fail or raise TypeError
    assert vn_now.tzinfo is None

    # Verify VN_TZ timezone offset is strictly +07:00
    offset = time_utils.VN_TZ.utcoffset(None)
    assert offset == timedelta(hours=7)

    # Verify vn_now is within 2 seconds of UTC now + 7 hours
    utc_now = datetime.now(timezone.utc).replace(tzinfo=None)
    expected_vn = utc_now + timedelta(hours=7)
    diff = abs((vn_now - expected_vn).total_seconds())
    assert diff < 2.0, f"vn_now ({vn_now}) deviates from expected UTC+7 ({expected_vn}) by {diff}s"


def test_time_utils_vn_tz_has_no_daylight_saving():
    """Vietnam Standard Time has no DST (dst is 0 / None)."""
    dst = time_utils.VN_TZ.dst(None)
    assert dst is None or dst == timedelta(0)


# -----------------------------------------------------------------------------
# 2. Past slot booking for today is rejected according to VN time
# -----------------------------------------------------------------------------

def test_free_hours_filters_out_past_hours_for_today(db):
    """free_hours() excludes hours that have already started or passed today in VN time."""
    # Venue 1 is open 06:00 to 22:00
    simulated_vn_now = datetime(2026, 10, 15, 14, 30)
    today = simulated_vn_now.date()

    with connect(db) as conn:
        venue = svc.get_venue(conn, 1)
        free = svc.free_hours(conn, venue, today, now=simulated_vn_now)

        # Hours 6..14 must be excluded because 14:00 is earlier than 14:30
        for h in range(6, 15):
            assert h not in free, f"Hour {h} should be excluded as past hour"

        # Hours 15..21 should be included (assuming no conflict)
        assert 15 in free
        assert 21 in free


def test_free_hours_tomorrow_keeps_all_open_hours(db):
    """free_hours() for a future date (e.g. tomorrow) retains open hours not taken."""
    simulated_vn_now = datetime(2026, 10, 15, 14, 30)
    tomorrow = simulated_vn_now.date() + timedelta(days=1)

    with connect(db) as conn:
        venue = svc.get_venue(conn, 1)
        free = svc.free_hours(conn, venue, tomorrow, now=simulated_vn_now)
        # All venue open hours (6..21) should be available if unbooked
        for h in range(venue["open_hour"], venue["close_hour"]):
            assert h in free


def test_check_request_rejects_past_hour_on_today(db):
    """svc.check_request() raises BR11 'This time slot has already started' for past slot today."""
    simulated_vn_now = datetime(2026, 10, 15, 14, 15)
    today = simulated_vn_now.date()

    with connect(db) as conn:
        u = _user(conn, "minh@example.com")

        # Slot 14:00 (which started 15 min ago) -> must be rejected
        with pytest.raises(BusinessRuleError) as exc_info:
            svc.check_request(conn, u, 1, today, start_hour=14, hours=1, now=simulated_vn_now)
        assert exc_info.value.rule == "BR11"
        assert exc_info.value.message == "This time slot has already started"

        # Slot 10:00 earlier today -> must be rejected
        with pytest.raises(BusinessRuleError) as exc_info_earlier:
            svc.check_request(conn, u, 1, today, start_hour=10, hours=2, now=simulated_vn_now)
        assert exc_info_earlier.value.message == "This time slot has already started"

        # Future slot starting at 15:00 -> accepted
        v, d, s, h = svc.check_request(conn, u, 1, today, start_hour=15, hours=1, now=simulated_vn_now)
        assert s == 15
        assert h == 1


def test_booking_api_rejects_past_slot_for_today(db):
    """POST /api/bookings returns 422 when attempting to book a past slot today."""
    simulated_vn_now = datetime(2026, 10, 15, 16, 45)
    client, _ = _client_for(db, "minh@example.com", now_fn=lambda: simulated_vn_now)

    # Attempt to book 16:00 on the same date (already started at 16:45)
    payload = {
        "venue_id": 1,
        "date": "2026-10-15",
        "start_hour": 16,
        "hours": 1
    }
    res = client.post("/api/bookings", json=payload)
    assert res.status_code == 422
    data = res.get_json()
    assert data["error"] == "This time slot has already started"
    assert data["rule"] == "BR11"


# -----------------------------------------------------------------------------
# 3. Cancellation window logic (BR14, BR15)
# -----------------------------------------------------------------------------

def test_cancellation_window_24h_or_more_gives_100_percent_refund(db):
    """Booking cancelled >= 24h before start time receives 100% refund and releases slots."""
    simulated_now = datetime(2026, 10, 15, 10, 0)
    # Start time is 2026-10-17 10:00 (exactly 48h ahead)
    match_start_date = "2026-10-17"
    match_start_hour = 10

    with connect(db) as conn:
        u = _user(conn, "minh@example.com")
        b = svc.create_booking(conn, u, 1, match_start_date, match_start_hour, 2, simulated_now)
        code = b["code"]
        total_price = b["total_price"]

        # Cancel with now set to simulated_now (48h ahead)
        res = svc.cancel_booking(conn, code, u, now=simulated_now)
        assert res["status"] == "cancelled"
        assert res["refund_percent"] == 100
        assert res["refund_amount"] == total_price
        assert "100%" in res["message"]

        # Check DB state
        booking_row = conn.execute("SELECT * FROM booking WHERE code = ?", (code,)).fetchone()
        assert booking_row["status"] == "cancelled"
        assert booking_row["refund_amount"] == total_price

        # Check slots were released
        slots_count = conn.execute(
            "SELECT COUNT(*) FROM booking_slot WHERE booking_id = ?", (booking_row["id"],)
        ).fetchone()[0]
        assert slots_count == 0


def test_cancellation_window_exactly_24h_gives_100_percent_refund(db):
    """Booking cancelled exactly 24h before start time receives 100% refund."""
    simulated_now = datetime(2026, 10, 15, 10, 0)
    # Start time is exactly 24h later: 2026-10-16 10:00
    with connect(db) as conn:
        u = _user(conn, "minh@example.com")
        b = svc.create_booking(conn, u, 1, "2026-10-16", 10, 1, simulated_now)
        code = b["code"]
        total_price = b["total_price"]

        res = svc.cancel_booking(conn, code, u, now=simulated_now)
        assert res["status"] == "cancelled"
        assert res["refund_percent"] == 100
        assert res["refund_amount"] == total_price


def test_cancellation_window_between_2h_and_24h_gives_50_percent_refund(db):
    """Booking cancelled between 2h and 24h before start time receives 50% refund."""
    simulated_now = datetime(2026, 10, 15, 10, 0)
    # Start time is 2026-10-15 15:00 (5 hours ahead)
    with connect(db) as conn:
        u = _user(conn, "minh@example.com")
        b = svc.create_booking(conn, u, 1, "2026-10-15", 15, 2, simulated_now)
        code = b["code"]
        total_price = b["total_price"]

        res = svc.cancel_booking(conn, code, u, now=simulated_now)
        assert res["status"] == "cancelled"
        assert res["refund_percent"] == 50
        assert res["refund_amount"] == total_price // 2
        assert "50%" in res["message"]

        # Check DB state
        booking_row = conn.execute("SELECT * FROM booking WHERE code = ?", (code,)).fetchone()
        assert booking_row["status"] == "cancelled"
        assert booking_row["refund_amount"] == total_price // 2

        # Slots released
        slots_count = conn.execute(
            "SELECT COUNT(*) FROM booking_slot WHERE booking_id = ?", (booking_row["id"],)
        ).fetchone()[0]
        assert slots_count == 0


def test_cancellation_window_exactly_2h_gives_50_percent_refund(db):
    """Booking cancelled at exactly 2h boundary (120 minutes) is allowed with 50% refund."""
    simulated_now = datetime(2026, 10, 15, 10, 0)
    # Start time is 2026-10-15 12:00 (exactly 2.0h ahead)
    with connect(db) as conn:
        u = _user(conn, "minh@example.com")
        b = svc.create_booking(conn, u, 1, "2026-10-15", 12, 1, simulated_now)
        code = b["code"]

        res = svc.cancel_booking(conn, code, u, now=simulated_now)
        assert res["status"] == "cancelled"
        assert res["refund_percent"] == 50


def test_cancellation_window_under_2h_rejected_with_br15(db):
    """Booking cancelled less than 2h before start time is rejected with BR15."""
    simulated_now = datetime(2026, 10, 15, 10, 1)
    # Start time is 2026-10-15 12:00 (1 hour 59 minutes ahead < 2h)
    with connect(db) as conn:
        u = _user(conn, "minh@example.com")
        b = svc.create_booking(conn, u, 1, "2026-10-15", 12, 1, simulated_now)
        code = b["code"]

        with pytest.raises(BusinessRuleError) as exc_info:
            svc.cancel_booking(conn, code, u, now=simulated_now)

        assert exc_info.value.rule == "BR15"
        assert "less than 2 hours" in exc_info.value.message
        assert exc_info.value.status == 400

        # Booking must remain confirmed and slots must remain occupied
        booking_row = conn.execute("SELECT * FROM booking WHERE code = ?", (code,)).fetchone()
        assert booking_row["status"] == "confirmed"
        slots_count = conn.execute(
            "SELECT COUNT(*) FROM booking_slot WHERE booking_id = ?", (booking_row["id"],)
        ).fetchone()[0]
        assert slots_count == 1


def test_cancellation_of_already_cancelled_booking_fails(db):
    """Attempting to cancel an already cancelled booking raises BR15 error."""
    simulated_now = datetime(2026, 10, 15, 10, 0)
    with connect(db) as conn:
        u = _user(conn, "minh@example.com")
        b = svc.create_booking(conn, u, 1, "2026-10-18", 14, 1, simulated_now)
        code = b["code"]
        svc.cancel_booking(conn, code, u, now=simulated_now)

        # Second cancel attempt
        with pytest.raises(BusinessRuleError) as exc_info:
            svc.cancel_booking(conn, code, u, now=simulated_now)
        assert exc_info.value.rule == "BR15"
        assert "Only confirmed bookings can be cancelled" in exc_info.value.message


# -----------------------------------------------------------------------------
# 4. my_bookings marks past/imminent bookings as non-cancellable or completed
# -----------------------------------------------------------------------------

def test_my_bookings_marks_imminent_booking_as_starting_soon(db):
    """When match is starting in <2h, my_bookings shows non-cancellable button and starting_soon."""
    simulated_now = datetime(2026, 10, 15, 15, 10)
    # Create booking starting at 16:00 today (50 minutes ahead < 2h)
    with connect(db) as conn:
        u = _user(conn, "minh@example.com")
        svc.create_booking(conn, u, 1, "2026-10-15", 16, 1, datetime(2026, 10, 15, 10, 0))

    client, _ = _client_for(db, "minh@example.com", now_fn=lambda: simulated_now)
    res = client.get("/my-bookings")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    # Imminent booking should display disabled Non-cancellable (<2h) button
    assert "Non-cancellable (&lt;2h)" in html or "Non-cancellable (<2h)" in html
    assert "Cannot cancel less than 2 hours before match start time (BR15)" in html


def test_my_bookings_marks_in_progress_booking(db):
    """When current time is within match start and end time, my_bookings marks 'Match in progress'."""
    simulated_now = datetime(2026, 10, 15, 16, 30)
    # Booking starts 16:00 and ends 18:00
    with connect(db) as conn:
        u = _user(conn, "minh@example.com")
        svc.create_booking(conn, u, 1, "2026-10-15", 16, 2, datetime(2026, 10, 15, 10, 0))

    client, _ = _client_for(db, "minh@example.com", now_fn=lambda: simulated_now)
    res = client.get("/my-bookings")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    # In-progress banner rendered
    assert "Match in progress" in html


def test_my_bookings_marks_past_booking_as_completed(db):
    """When match end time has passed, my_bookings marks completed and shows review option."""
    simulated_now = datetime(2026, 10, 15, 19, 0)
    # Booking ended at 18:00
    with connect(db) as conn:
        from werkzeug.security import generate_password_hash
        conn.execute(
            "INSERT INTO user (email, password_hash, full_name, phone, role, email_verified_at)"
            " VALUES ('completed_user@example.com', ?, 'Past Match User', '0988776655', 'customer', datetime('now'))",
            (generate_password_hash("sanbong1"),))
        u = conn.execute("SELECT * FROM user WHERE email = 'completed_user@example.com'").fetchone()
        b = svc.create_booking(conn, u, 1, "2026-10-15", 16, 2, datetime(2026, 10, 15, 10, 0))
        code = b["code"]

    client, _ = _client_for(db, "completed_user@example.com", now_fn=lambda: simulated_now)
    res = client.get("/my-bookings")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    # Completed bookings offer venue rating and do not offer cancellation
    assert "Rate Venue" in html
    assert f"/my-bookings/{code}/review" in html
    assert f"/my-bookings/{code}/cancel" not in html

    # Verify no cancel button is rendered in the HTML body (excluding JS translation dictionary)
    body_content = html.split("<script>")[0]
    assert "✕ Cancel Booking" not in body_content


def test_my_bookings_shows_active_cancel_button_for_future_booking(db):
    """When booking is >24h ahead, my_bookings displays an active Cancel Booking button."""
    simulated_now = datetime(2026, 10, 15, 10, 0)
    # Booking on 2026-10-18 (3 days ahead)
    with connect(db) as conn:
        u = _user(conn, "minh@example.com")
        b = svc.create_booking(conn, u, 1, "2026-10-18", 16, 2, simulated_now)
        code = b["code"]

    client, _ = _client_for(db, "minh@example.com", now_fn=lambda: simulated_now)
    res = client.get("/my-bookings")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    # Active cancel button and action URL present
    assert f"/my-bookings/{code}/cancel" in html
    assert "Cancel Booking" in html


# -----------------------------------------------------------------------------
# 5. booking_done.html renders @media print CSS and proper h1 white contrast
# -----------------------------------------------------------------------------

def test_booking_done_renders_media_print_css(db):
    """booking_done.html contains dedicated @media print CSS rules for printing tickets."""
    simulated_now = datetime(2026, 10, 15, 10, 0)
    with connect(db) as conn:
        u = _user(conn, "minh@example.com")
        b = svc.create_booking(conn, u, 1, "2026-10-18", 16, 2, simulated_now)
        code = b["code"]

    client, _ = _client_for(db, "minh@example.com", now_fn=lambda: simulated_now)
    res = client.get(f"/bookings/{code}")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    # Check print stylesheet
    assert "@media print" in html
    # Non-printable chrome should be hidden
    assert "header.top, nav, footer, .back-link, .ticket-actions" in html
    # Background and print color adjust
    assert "print-color-adjust: exact;" in html or "-webkit-print-color-adjust: exact;" in html
    # Print action button
    assert "window.print()" in html
    assert "Print booking" in html


def test_booking_done_renders_h1_white_color_contrast(db):
    """booking_done.html forces h1 white color contrast against the dark green card header."""
    simulated_now = datetime(2026, 10, 15, 10, 0)
    with connect(db) as conn:
        u = _user(conn, "minh@example.com")
        b = svc.create_booking(conn, u, 1, "2026-10-18", 16, 2, simulated_now)
        code = b["code"]

    client, _ = _client_for(db, "minh@example.com", now_fn=lambda: simulated_now)
    res = client.get(f"/bookings/{code}")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    # Header title has explicit white color rule to guarantee WCAG AAA contrast with #183b2b
    assert "color: #ffffff !important;" in html
    assert '<h1 id="ticket-title">Your court is reserved</h1>' in html
    assert "ticket-top" in html
