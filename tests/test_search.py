"""The walking skeleton reads from the database, not from a list in the code."""
import pytest

from app import create_app
from db import connect


@pytest.fixture
def client(db):
    return create_app(database=db).test_client()


def test_health_reports_seeded_venues(client):
    assert client.get("/health").get_json() == {"status": "ok", "venues": 24}


def test_search_lists_all_seeded_venues(client):
    page = client.get("/search").get_data(as_text=True)
    assert "24</strong> venue(s) found" in page


def test_search_matches_sport_and_area_together(client):
    # BR9: Football + Cau Giay returns only football pitches in Cau Giay
    page = client.get("/search?sport=Football&area=Cau+Giay").get_data(as_text=True)
    assert "Thong Nhat Football Pitch" in page
    assert "Lan Anh Badminton Court" not in page


def test_search_with_no_match_shows_message(client):
    # BR9: explicit empty state
    page = client.get("/search?sport=Tennis&area=Ha+Dong").get_data(as_text=True)
    assert "No venues found" in page


def test_page_follows_the_database(client, db):
    # A venue inserted after start-up appears on the next request: the data is live.
    with connect(db) as conn:
        conn.execute("INSERT INTO venue (owner_id, name, sport, area, address, hourly_price,"
                     " open_hour, close_hour) VALUES (1, 'Test Court', 'Tennis', 'Ha Dong', 'x', 100000, 6, 22)")
    page = client.get("/search?sport=Tennis&area=Ha+Dong").get_data(as_text=True)
    assert "Test Court" in page
