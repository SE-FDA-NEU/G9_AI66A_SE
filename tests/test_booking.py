"""US05 Book a venue with per-segment pricing (issue #68).

The clock is pinned to Sunday 11/10/2026 09:00 so the dates below stay in the future.
Seed: venue 1 = Thong Nhat Football Pitch, open 06:00-22:00, standard 300,000 VND,
peak 450,000 on Tuesday 17:00-20:00. 13/10/2026 is a Tuesday.
"""
import re
import threading
from datetime import date, datetime

import pytest
from werkzeug.security import generate_password_hash

import booking as svc
from app import create_app
from db import connect
from errors import BusinessRuleError
from pricing import hour_prices, segments

NOW = datetime(2026, 10, 11, 9, 0)
TUESDAY = "2026-10-13"


def user(conn, email):
    return conn.execute("SELECT * FROM user WHERE email = ?", (email,)).fetchone()


def book(db, email, start, hours, day=TUESDAY, venue_id=1):
    with connect(db) as conn:
        return svc.create_booking(conn, user(conn, email), venue_id, day, start, hours, NOW)


def bookings_at(db, slot):
    with connect(db) as conn:
        return conn.execute("SELECT COUNT(*) FROM booking_slot WHERE venue_id = 1"
                            " AND slot_start = ?", (slot,)).fetchone()[0]


@pytest.fixture
def app(db):
    app = create_app(database=db)
    app.config["NOW"] = lambda: NOW
    return app


def signed_in(app, email):
    client = app.test_client()
    with connect(app.config["DATABASE"]) as conn:
        user_id = user(conn, email)["id"]
    with client.session_transaction() as s:
        s["user_id"] = user_id
    return client


# --- BR12: per-segment pricing ---------------------------------------------------------

def test_peak_price_applies_only_on_its_weekday(db):
    with connect(db) as conn:
        assert hour_prices(conn, 1, date(2026, 10, 13))[18] == 450000   # Tuesday, peak
        assert hour_prices(conn, 1, date(2026, 10, 14))[18] == 300000   # Wednesday, standard


def test_booking_across_boundary_is_two_lines_and_exact_sum(db):
    # 19:00-21:00 crosses 20:00: 1 h peak + 1 h standard = 750,000, not 2 x 450,000
    result = book(db, "minh@example.com", 19, 2)
    assert [(s["from"], s["to"], s["price"]) for s in result["segments"]] == [
        ("19:00", "20:00", 450000), ("20:00", "21:00", 300000)]
    assert result["total_price"] == 750000


def test_hours_with_the_same_price_form_one_line():
    prices = {17: 450000, 18: 450000, 19: 450000}
    assert segments(prices, 17, 3) == [{"from": "17:00", "to": "20:00", "hours": 3,
                                        "price_per_hour": 450000, "price": 1350000}]


def test_confirmed_price_does_not_change_when_rules_change(db, app):
    code = book(db, "minh@example.com", 19, 2)["code"]
    with connect(db) as conn:
        conn.execute("UPDATE pricing_rule SET price_per_hour = 999000")
    page = signed_in(app, "minh@example.com").get(f"/bookings/{code}").get_data(as_text=True)
    assert "750,000" in page and "999,000" not in page


# --- BR11: one booking per hour --------------------------------------------------------

def test_confirm_returns_code_and_hour_is_no_longer_free(db):
    result = book(db, "minh@example.com", 18, 1)
    assert re.fullmatch(r"BK-\d{6}", result["code"])
    with connect(db) as conn:
        assert 18 not in svc.free_hours(conn, svc.get_venue(conn, 1), date(2026, 10, 13), NOW)


def test_same_hour_confirmed_first_by_another_customer(db):
    book(db, "trang@example.com", 18, 1)
    with pytest.raises(BusinessRuleError) as e:
        book(db, "minh@example.com", 18, 1)
    assert (e.value.status, e.value.message) == (409, "This time slot is no longer available")
    assert bookings_at(db, "2026-10-13 18:00") == 1


def test_overlapping_booking_with_a_different_start_is_refused(db):
    # ADR 2: A books 18:00-20:00, B books 19:00-21:00 - the start times differ
    book(db, "trang@example.com", 18, 2)
    with pytest.raises(BusinessRuleError, match="no longer available"):
        book(db, "minh@example.com", 19, 2)


def test_two_customers_confirming_at_once_give_one_booking(db):
    results, barrier = [], threading.Barrier(2)

    def attempt(email):
        barrier.wait()
        try:
            results.append(book(db, email, 18, 1)["code"])
        except BusinessRuleError as e:
            results.append(e.status)

    threads = [threading.Thread(target=attempt, args=(e,))
               for e in ("minh@example.com", "trang@example.com")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(results) == 2 and results.count(409) == 1     # one code, one refusal
    assert bookings_at(db, "2026-10-13 18:00") == 1


def test_unique_constraint_catches_what_the_recheck_misses(db, monkeypatch):
    # Even if the re-check were skipped, the database refuses the second row (ADR 2)
    book(db, "trang@example.com", 18, 1)
    monkeypatch.setattr(svc, "check_request", lambda conn, u, v, d, s, h, now=None:
                        (svc.get_venue(conn, v), date.fromisoformat(d), s, h))
    with pytest.raises(BusinessRuleError) as e:
        book(db, "minh@example.com", 18, 1)
    assert e.value.status == 409
    with connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM booking WHERE start_at = '2026-10-13 18:00'"
                            ).fetchone()[0] == 1


# --- BR11: opening hours and length ----------------------------------------------------

def test_only_start_times_inside_opening_hours_are_offered(db):
    with connect(db) as conn:
        hours = svc.free_hours(conn, svc.get_venue(conn, 1), date(2026, 10, 14), NOW)
    assert hours == list(range(6, 22))       # 06:00 ... 21:00


def test_tc13_booking_duration_boundaries(db):
    """TC-13, TC-14, TC-15: BR11 duration boundary check (0, 1, 4, 5 hours)."""
    # Boundary: 0 hours (refused)
    with pytest.raises(BusinessRuleError, match="1 to 4 consecutive hours"):
        book(db, "minh@example.com", 8, 0)

    # Boundary: 1 hour (minimum valid - accepted) - TC-13
    b1 = book(db, "minh@example.com", 8, 1)
    assert b1["code"].startswith("BK-")

    # Boundary: 4 hours (maximum valid - accepted) - TC-14
    b4 = book(db, "minh@example.com", 10, 4)
    assert b4["code"].startswith("BK-")

    # Boundary: 5 hours (just above limit - refused) - TC-15
    with pytest.raises(BusinessRuleError, match="1 to 4 consecutive hours"):
        book(db, "minh@example.com", 14, 5)


def test_more_than_four_hours_is_refused(db):
    with pytest.raises(BusinessRuleError, match="1 to 4 consecutive hours"):
        book(db, "minh@example.com", 8, 5)


def test_three_hours_from_21_says_the_venue_closes_at_22(app):
    page = signed_in(app, "minh@example.com").get(
        f"/booking/1?date={TUESDAY}&start_hour=21&hours=3")
    assert page.status_code == 422
    assert "The venue closes at 22:00" in page.get_data(as_text=True)


def test_blocked_hour_cannot_be_booked(db):
    # BR16
    with connect(db) as conn:
        conn.execute("INSERT INTO blocked_slot (venue_id, slot_start) VALUES (1, '2026-10-13 07:00')")
    with pytest.raises(BusinessRuleError, match="closed for maintenance"):
        book(db, "minh@example.com", 6, 2)


# --- Pages, BR4 and BR14 ---------------------------------------------------------------

def test_fully_booked_day_says_so_and_links_the_nearest_date(db, app):
    for start in (6, 10, 14, 18):
        book(db, "trang@example.com", start, 4)
    page = signed_in(app, "minh@example.com").get(f"/booking/1?date={TUESDAY}").get_data(as_text=True)
    assert "This venue is fully booked on 13/10/2026" in page
    assert 'href="?date=2026-10-14"' in page


def test_unverified_email_cannot_book(app):
    with connect(app.config["DATABASE"]) as conn:
        conn.execute(
            "INSERT INTO user (email, password_hash, full_name, phone, role, email_verified_at)"
            " VALUES (?, ?, ?, ?, ?, NULL)",
            ("khoa@example.com", generate_password_hash("sanbong1"), "Khoa Nguyen",
             "0901111111", "customer"),
        )
    client = signed_in(app, "khoa@example.com")
    page = client.post("/booking/1", data={"date": TUESDAY, "start_hour": 18, "hours": 1})
    assert page.status_code == 403
    assert "Please verify your email before booking" in page.get_data(as_text=True)


def test_page_flow_confirms_and_only_the_owner_can_open_the_booking(app):
    client = signed_in(app, "minh@example.com")
    quote = client.get(f"/booking/1?date={TUESDAY}&start_hour=19&hours=2").get_data(as_text=True)
    assert "750,000" in quote and "Confirm booking" in quote
    done = client.post("/booking/1", data={"date": TUESDAY, "start_hour": 19, "hours": 2})
    code = done.location.rsplit("/", 1)[-1]
    assert client.get(done.location).status_code == 200
    assert signed_in(app, "trang@example.com").get(f"/bookings/{code}").status_code == 403


def test_api_creates_a_booking_and_requires_sign_in(app):
    body = {"venue_id": 1, "date": TUESDAY, "start_hour": 19, "hours": 2}
    assert app.test_client().post("/api/bookings", json=body).status_code == 401
    r = signed_in(app, "minh@example.com").post("/api/bookings", json=body)
    assert r.status_code == 201
    assert r.get_json()["total_price"] == 750000
    with connect(app.config["DATABASE"]) as conn:
        upcoming = svc.upcoming(conn, user(conn, "minh@example.com")["id"], NOW)
    assert r.get_json()["code"] in [b["code"] for b in upcoming]
