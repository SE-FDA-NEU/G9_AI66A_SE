"""US03 - Customer searches for venues (#16): the page reads the database (BR9)."""
from db import connect


def test_health_reports_seeded_venues(client):
    assert client.get("/health").get_json() == {"status": "ok", "venues": 24}


def test_search_lists_all_seeded_venues(client):
    page = client.get("/search").get_data(as_text=True)
    assert 'id="count">24</strong> venue(s) found' in page


def test_search_matches_sport_and_area_together(client):
    # US03 criterion 1, BR9: Football + Cau Giay returns only football pitches in Cau Giay
    page = client.get("/search?sport=Football&area=Cau+Giay").get_data(as_text=True)
    assert "Thong Nhat Football Pitch" in page
    assert "Lan Anh Badminton Court" not in page


def test_search_with_no_match_shows_message(client):
    # US03 criterion 2, BR9: explicit empty state
    page = client.get("/search?sport=Tennis&area=Hoan+Kiem").get_data(as_text=True)
    assert "No venues found" in page
    assert 'id="no-match" hidden' not in page          # the message is visible
    assert 'id="results" hidden' in page               # and the empty table is not


def test_area_list_is_fixed_not_typed(client):
    # BR9: every district is offered, even one with no venue yet
    page = client.get("/search").get_data(as_text=True)
    assert ">Hoan Kiem</option>" in page


def test_unknown_sport_is_refused_with_a_message(client):
    # BR9: sport comes from the list; a hand-typed value is not silently ignored
    response = client.get("/search?sport=Golf")
    assert response.status_code == 400
    assert "Please choose a sport from the list" in response.get_data(as_text=True)


def test_typed_text_narrows_by_name_or_sport(client):
    # US03 criterion 3 - the same filter the page applies while typing
    page = client.get("/search?q=badminton").get_data(as_text=True)
    assert "Lan Anh Badminton Court" in page
    assert "Thong Nhat Football Pitch" not in page


def test_page_follows_the_database(client, db):
    # A venue inserted after start-up appears on the next request: the data is live.
    with connect(db) as conn:
        conn.execute("INSERT INTO venue (owner_id, name, sport, area, address, hourly_price,"
                     " open_hour, close_hour) VALUES (1, 'Test Court', 'Tennis', 'Hoan Kiem', 'x', 100000, 6, 22)")
    page = client.get("/search?sport=Tennis&area=Hoan+Kiem").get_data(as_text=True)
    assert "Test Court" in page


def test_api_search_returns_venues_or_the_no_match_message(client):
    # design.md section 3, endpoint 4
    found = client.get("/api/venues?sport=Football&area=Cau+Giay").get_json()
    assert {v["name"] for v in found["venues"]} >= {"Thong Nhat Football Pitch"}
    assert all(v["sport"] == "Football" and v["area"] == "Cau Giay" for v in found["venues"])
    assert client.get("/api/venues?sport=Tennis&area=Hoan+Kiem").get_json() == {
        "venues": [], "message": "No venues found"}
    bad = client.get("/api/venues?area=Saigon")
    assert bad.status_code == 400
    assert bad.get_json() == {"error": "Please choose an area from the list", "rule": "BR9"}
