"""US04 - Customer views venue details and availability (#17): BR10, BR16."""
from datetime import date, datetime, timedelta

import pytest

import venues
from db import connect
from init_db import TUESDAY, WEDNESDAY

THONG_NHAT = 1          # first row of data/venues.csv, open 06:00-22:00


def slots(client, venue_id, day):
    return client.get(f"/api/venues/{venue_id}?date={day}")


# --- Normal cases -----------------------------------------------------------

def test_detail_page_shows_the_venue(client):
    """Normal: US04 AC1 - Detail page shows name, address, price, facilities, and date picker."""
    page = client.get(f"/venues/{THONG_NHAT}").get_data(as_text=True)
    assert "Thong Nhat Football Pitch" in page
    assert "12 Tran Thai Tong, Cau Giay" in page
    assert "300,000 VND per hour" in page
    assert 'id="day"' in page                          # date selector input present
    assert 'type="date"' in page


def test_sixteen_slots_three_booked_thirteen_free(client):
    """Normal: US04 AC2, BR10 - Tuesday has bookings at 17:00, 19:00 and 20:00 (13 free, 3 booked)."""
    body = slots(client, THONG_NHAT, TUESDAY).get_json()
    assert len(body["slots"]) == 16
    assert (body["free"], body["booked"]) == (13, 3)
    booked = [s["start"] for s in body["slots"] if s["status"] == "booked"]
    assert booked == ["17:00", "19:00", "20:00"]


def test_availability_is_for_exactly_the_chosen_date(client):
    """Normal: US04 AC1, BR10 - Day before Tuesday shows none of Tuesday's bookings."""
    day_before = (date.fromisoformat(TUESDAY) - timedelta(days=1)).isoformat()
    body = slots(client, THONG_NHAT, day_before).get_json()
    assert body["date"] == day_before
    assert body["booked"] == 0

    # Also check date query parameter on HTML page
    page = client.get(f"/venues/{THONG_NHAT}?date={day_before}").get_data(as_text=True)
    assert f'value="{day_before}"' in page


def test_blocked_hours_are_shown_as_blocked(client):
    """Normal: BR16 - Blocked maintenance hours on Wednesday 06:00-08:00."""
    body = slots(client, THONG_NHAT, WEDNESDAY).get_json()
    assert [s["start"] for s in body["slots"] if s["status"] == "blocked"] == ["06:00", "07:00"]
    assert body["free"] == 14
    assert body["blocked"] == 2


def test_api_venue_returns_complete_structure(client):
    """Normal: US04 - GET /api/venues/<id> returns complete venue info, slots, and counts."""
    response = slots(client, THONG_NHAT, TUESDAY)
    assert response.status_code == 200
    body = response.get_json()
    assert body["venue"]["name"] == "Thong Nhat Football Pitch"
    assert body["venue"]["hourly_price"] == 300000
    assert body["venue"]["open_hour"] == 6
    assert body["venue"]["close_hour"] == 22
    assert "slots" in body
    for slot in body["slots"]:
        assert {"hour", "start", "end", "status"} <= slot.keys()


def test_search_result_links_to_the_detail_page(client):
    """Normal: Navigation from search result to venue detail page."""
    page = client.get("/search?sport=Football&area=Cau+Giay").get_data(as_text=True)
    assert f'href="/venues/{THONG_NHAT}"' in page


# --- Error cases ------------------------------------------------------------

def test_malformed_date_is_refused(client):
    """Error: US04 BR10 - Malformed date string (DD-MM-YYYY) is refused with HTTP 400."""
    response = slots(client, THONG_NHAT, "20-10-2026")
    assert response.status_code == 400
    assert "YYYY-MM-DD" in response.get_json()["error"]
    assert response.get_json()["rule"] == "BR10"


@pytest.mark.parametrize("bad_date", [
    "not-a-date",
    "2026/10/20",
    "2026-02-31",
    "2026-13-01",
    "2026-10-99",
    "tomorrow",
])
def test_various_malformed_date_formats_refused(client, bad_date):
    """Error: US04 BR10 - Various invalid date strings return HTTP 400 with YYYY-MM-DD format reminder."""
    response = slots(client, THONG_NHAT, bad_date)
    assert response.status_code == 400
    assert "YYYY-MM-DD" in response.get_json()["error"]


def test_unknown_venue_is_404_with_a_message(client):
    """Error: US04 - Non-existent venue ID returns HTTP 404 for HTML and API routes."""
    # HTML route
    response = client.get("/venues/999")
    assert response.status_code == 404
    assert "Venue not found" in response.get_data(as_text=True)

    # API route
    api_resp = slots(client, 999, TUESDAY)
    assert api_resp.status_code == 404
    assert "Venue not found" in api_resp.get_json()["error"]


def test_nonexistent_photo_returns_404(client):
    """Error: US04 - Requesting a non-existent photo ID returns HTTP 404."""
    response = client.get(f"/venues/{THONG_NHAT}/photos/99999")
    assert response.status_code == 404
    assert "Photo not found" in response.get_data(as_text=True)


def test_inactive_venue_returns_404(client, db):
    """Error: US04 - Deactivated venue returns HTTP 404 on both HTML and API routes."""
    with connect(db) as conn:
        conn.execute("UPDATE venue SET active = 0 WHERE id = ?", (THONG_NHAT,))
    assert client.get(f"/venues/{THONG_NHAT}").status_code == 404
    assert slots(client, THONG_NHAT, TUESDAY).status_code == 404


# --- Boundary cases ---------------------------------------------------------

def test_past_date_is_refused(client):
    """Boundary: US04 BR10 - Date before today (yesterday) is refused with HTTP 400."""
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    response = slots(client, THONG_NHAT, yesterday)
    assert response.status_code == 400
    assert response.get_json() == {"error": "Please choose today or a later date.", "rule": "BR10"}


def test_gallery_shows_only_this_venues_photos(client, db):
    """Boundary: US04 AC3 - Photo isolation: photo of venue 2 never appears on venue 1."""
    upload_dir = client.application.config["UPLOAD_DIR"]
    upload_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / "venue2.jpg").write_bytes(b"fake image")
    with connect(db) as conn:
        photo_id = conn.execute("INSERT INTO venue_photo (venue_id, file_name) VALUES (2, 'venue2.jpg')").lastrowid
    assert f"/venues/2/photos/{photo_id}" in client.get("/venues/2").get_data(as_text=True)
    assert "/photos/" not in client.get(f"/venues/{THONG_NHAT}").get_data(as_text=True)
    assert client.get(f"/venues/2/photos/{photo_id}").data == b"fake image"
    assert client.get(f"/venues/{THONG_NHAT}/photos/{photo_id}").status_code == 404


def test_today_availability_marks_elapsed_hours_as_past(client, db):
    """Boundary: US04 - Availability for today marks elapsed hours as 'past' and future hours as 'free'/'booked'."""
    with connect(db) as conn:
        venue = venues.get_venue(conn, THONG_NHAT)
        fixed_day = date(2026, 10, 20)
        # Midday at 14:00: hours 6..14 (<= 14) are past, hours 15..21 are not past
        mock_now = datetime(2026, 10, 20, 14, 0)
        computed_slots = venues.day_slots(conn, venue, fixed_day, mock_now)
        past_hours = [s["hour"] for s in computed_slots if s["status"] == "past"]
        assert past_hours == list(range(6, 15))
        assert all(s["status"] != "past" for s in computed_slots if s["hour"] > 14)

    # Calling default route without date defaults to today
    resp = client.get(f"/api/venues/{THONG_NHAT}")
    assert resp.status_code == 200
    assert resp.get_json()["date"] == date.today().isoformat()


def test_daily_slot_boundaries_match_opening_and_closing_hours(client):
    """Boundary: 16 slots strictly span [open_hour, close_hour), boundaries verified."""
    body = slots(client, THONG_NHAT, TUESDAY).get_json()
    all_slots = body["slots"]
    assert len(all_slots) == 16
    # Lowest slot: 06:00 - 07:00
    assert all_slots[0]["hour"] == 6
    assert all_slots[0]["start"] == "06:00"
    assert all_slots[0]["end"] == "07:00"
    # Highest slot: 21:00 - 22:00
    assert all_slots[-1]["hour"] == 21
    assert all_slots[-1]["start"] == "21:00"
    assert all_slots[-1]["end"] == "22:00"
    # No hours outside 6..21
    hours = [s["hour"] for s in all_slots]
    assert min(hours) == 6
    assert max(hours) == 21
    assert 5 not in hours and 22 not in hours


def test_far_future_date_availability(client):
    """Boundary: US04 BR10 - Date 1 year in future has all 16 slots free, 0 booked, 0 blocked."""
    future_day = (date.today() + timedelta(days=365)).isoformat()
    body = slots(client, THONG_NHAT, future_day).get_json()
    assert body["date"] == future_day
    assert body["free"] == 16
    assert body["booked"] == 0
    assert body["blocked"] == 0
    assert all(s["status"] == "free" for s in body["slots"])


def test_venue_with_zero_photos_gallery(client):
    """Boundary: US04 AC3 - Venue with no photos renders detail page cleanly without photo elements."""
    page = client.get(f"/venues/{THONG_NHAT}").get_data(as_text=True)
    assert "/photos/" not in page


def test_venue_with_multiple_photos_ordered(client, db):
    """Boundary: US04 AC3 - Venue with multiple photos lists them in ascending ID order (oldest first)."""
    upload_dir = client.application.config["UPLOAD_DIR"]
    upload_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / "p1.jpg").write_bytes(b"img1")
    (upload_dir / "p2.jpg").write_bytes(b"img2")
    with connect(db) as conn:
        id1 = conn.execute("INSERT INTO venue_photo (venue_id, file_name) VALUES (1, 'p1.jpg')").lastrowid
        id2 = conn.execute("INSERT INTO venue_photo (venue_id, file_name) VALUES (1, 'p2.jpg')").lastrowid

    page = client.get("/venues/1").get_data(as_text=True)
    pos1 = page.find(f"/venues/1/photos/{id1}")
    pos2 = page.find(f"/venues/1/photos/{id2}")
    assert pos1 != -1 and pos2 != -1
    assert pos1 < pos2                                 # oldest photo first


def test_cancelled_booking_frees_up_slot(client, db):
    """Boundary: US04, BR15 - When a booking is cancelled, its slots are released and show as 'free'."""
    # Seeded booking on TUESDAY has slot at 17:00 (BK-000106)
    body_before = slots(client, THONG_NHAT, TUESDAY).get_json()
    assert any(s["start"] == "17:00" and s["status"] == "booked" for s in body_before["slots"])

    with connect(db) as conn:
        booking = conn.execute("SELECT id FROM booking WHERE code = 'BK-000106'").fetchone()
        conn.execute("DELETE FROM booking_slot WHERE booking_id = ?", (booking["id"],))
        conn.execute("UPDATE booking SET status = 'cancelled' WHERE id = ?", (booking["id"],))
        conn.commit()

    body_after = slots(client, THONG_NHAT, TUESDAY).get_json()
    slot_17 = next(s for s in body_after["slots"] if s["start"] == "17:00")
    assert slot_17["status"] == "free"
    assert body_after["booked"] == body_before["booked"] - 1
    assert body_after["free"] == body_before["free"] + 1
