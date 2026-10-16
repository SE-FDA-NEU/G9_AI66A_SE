"""US04 - Customer views venue details and availability (#17): BR10, BR16."""
from datetime import date, timedelta

from db import connect
from init_db import TUESDAY, WEDNESDAY

THONG_NHAT = 1          # first row of data/venues.csv, open 06:00-22:00


def slots(client, venue_id, day):
    return client.get(f"/api/venues/{venue_id}?date={day}")


def test_detail_page_shows_the_venue(client):
    page = client.get(f"/venues/{THONG_NHAT}").get_data(as_text=True)
    assert "Thong Nhat Football Pitch" in page
    assert "12 Tran Thai Tong, Cau Giay" in page
    assert "300,000 VND per hour" in page


def test_search_result_links_to_the_detail_page(client):
    page = client.get("/search?sport=Football&area=Cau+Giay").get_data(as_text=True)
    assert f'href="/venues/{THONG_NHAT}"' in page


def test_unknown_venue_is_404_with_a_message(client):
    response = client.get("/venues/999")
    assert response.status_code == 404
    assert "Venue not found" in response.get_data(as_text=True)


def test_sixteen_slots_three_booked_thirteen_free(client):
    # US04 criterion 2: Tuesday has bookings at 17:00, 19:00 and 20:00
    body = slots(client, THONG_NHAT, TUESDAY).get_json()
    assert len(body["slots"]) == 16
    assert (body["free"], body["booked"]) == (13, 3)
    booked = [s["start"] for s in body["slots"] if s["status"] == "booked"]
    assert booked == ["17:00", "19:00", "20:00"]


def test_availability_is_for_exactly_the_chosen_date(client):
    # US04 criterion 1, BR10: the day before Tuesday shows none of Tuesday's bookings
    day_before = (date.fromisoformat(TUESDAY) - timedelta(days=1)).isoformat()
    body = slots(client, THONG_NHAT, day_before).get_json()
    assert body["date"] == day_before
    assert body["booked"] == 0


def test_blocked_hours_are_shown_as_blocked(client):
    # BR16: maintenance on Wednesday 06:00-08:00
    body = slots(client, THONG_NHAT, WEDNESDAY).get_json()
    assert [s["start"] for s in body["slots"] if s["status"] == "blocked"] == ["06:00", "07:00"]
    assert body["free"] == 14


def test_past_date_is_refused(client):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    response = slots(client, THONG_NHAT, yesterday)
    assert response.status_code == 400
    assert response.get_json() == {"error": "Please choose today or a later date.", "rule": "BR10"}


def test_malformed_date_is_refused(client):
    response = slots(client, THONG_NHAT, "20-10-2026")
    assert response.status_code == 400
    assert "YYYY-MM-DD" in response.get_json()["error"]


def test_gallery_shows_only_this_venues_photos(client, db):
    # US04 criterion 3: a photo of venue 2 never appears on venue 1
    upload_dir = client.application.config["UPLOAD_DIR"]
    upload_dir.mkdir(parents=True)
    (upload_dir / "venue2.jpg").write_bytes(b"fake image")
    with connect(db) as conn:
        photo_id = conn.execute("INSERT INTO venue_photo (venue_id, file_name) VALUES (2, 'venue2.jpg')").lastrowid
    assert f"/venues/2/photos/{photo_id}" in client.get("/venues/2").get_data(as_text=True)
    assert "/photos/" not in client.get(f"/venues/{THONG_NHAT}").get_data(as_text=True)
    assert client.get(f"/venues/2/photos/{photo_id}").data == b"fake image"
    assert client.get(f"/venues/{THONG_NHAT}/photos/{photo_id}").status_code == 404
