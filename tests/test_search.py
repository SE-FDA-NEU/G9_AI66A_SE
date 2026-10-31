"""US03 - Customer searches for venues (#16): the page reads the database (BR9)."""
from db import connect


def test_health_reports_seeded_venues(client):
    assert client.get("/health").get_json() == {"status": "ok", "venues": 24}


def test_root_page_shows_venue_search(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Find a venue" in response.get_data(as_text=True)


def test_search_lists_all_seeded_venues(client):
    page = client.get("/search").get_data(as_text=True)
    assert 'id="count">24</strong> venue(s) found' in page


# --- Normal cases -----------------------------------------------------------

def test_search_matches_sport_and_area_together(client):
    """Normal: US03 AC1, BR9 - Football + Cau Giay returns only football pitches in Cau Giay."""
    page = client.get("/search?sport=Football&area=Cau+Giay").get_data(as_text=True)
    assert "Thong Nhat Football Pitch" in page
    assert "Lan Anh Badminton Court" not in page


def test_search_by_sport_only_and_area_only(client):
    """Normal: Filtering by a single criterion (sport only or area only)."""
    # Sport only: Badminton across all areas
    page_sport = client.get("/search?sport=Badminton").get_data(as_text=True)
    assert "Lan Anh Badminton Court" in page_sport
    assert "Thong Nhat Football Pitch" not in page_sport

    # Area only: Cau Giay across all sports
    page_area = client.get("/search?area=Cau+Giay").get_data(as_text=True)
    assert "Thong Nhat Football Pitch" in page_area
    assert "Lan Anh Badminton Court" in page_area
    assert "My Dinh Football Pitch" not in page_area


def test_typed_text_narrows_by_name_or_sport(client):
    """Normal: US03 AC3 - Typing in search field narrows by name or sport."""
    page = client.get("/search?q=badminton").get_data(as_text=True)
    assert "Lan Anh Badminton Court" in page
    assert "Thong Nhat Football Pitch" not in page


def test_api_search_returns_matching_venues(client):
    """Normal: GET /api/venues returns matching venues array with valid schema."""
    found = client.get("/api/venues?sport=Football&area=Cau+Giay").get_json()
    assert {v["name"] for v in found["venues"]} >= {"Thong Nhat Football Pitch"}
    assert all(v["sport"] == "Football" and v["area"] == "Cau Giay" for v in found["venues"])
    sample = found["venues"][0]
    for key in ("id", "name", "sport", "area", "address", "hourly_price", "open_hour", "close_hour"):
        assert key in sample


def test_page_follows_the_database(client, db):
    """Normal: Live data update - newly inserted venue appears on the next request."""
    with connect(db) as conn:
        conn.execute("INSERT INTO venue (owner_id, name, sport, area, address, hourly_price,"
                     " open_hour, close_hour) VALUES (1, 'Test Court', 'Tennis', 'Hoan Kiem', 'x', 100000, 6, 22)")
    page = client.get("/search?sport=Tennis&area=Hoan+Kiem").get_data(as_text=True)
    assert "Test Court" in page


def test_area_list_is_fixed_not_typed(client):
    """Normal: BR9 - Every district from fixed list is offered, even one with no venue yet."""
    page = client.get("/search").get_data(as_text=True)
    assert ">Hoan Kiem</option>" in page


# --- Error cases ------------------------------------------------------------

def test_unknown_sport_is_refused_with_a_message(client):
    """Error: US03 BR9 - Unlisted sport returns HTTP 400 with user-friendly message."""
    response = client.get("/search?sport=Golf")
    assert response.status_code == 400
    assert "Please choose a sport from the list" in response.get_data(as_text=True)


def test_unknown_area_is_refused_with_a_message(client):
    """Error: US03 BR9 - Unlisted area returns HTTP 400 on both web and API."""
    # Web route
    response = client.get("/search?area=Saigon")
    assert response.status_code == 400
    assert "Please choose an area from the list" in response.get_data(as_text=True)

    # API route
    api_resp = client.get("/api/venues?area=Saigon")
    assert api_resp.status_code == 400
    assert api_resp.get_json() == {"error": "Please choose an area from the list", "rule": "BR9"}


def test_unknown_sport_on_api_is_refused(client):
    """Error: US03 BR9 - Unlisted sport on API returns HTTP 400 with BR9 rule."""
    bad = client.get("/api/venues?sport=Cricket")
    assert bad.status_code == 400
    assert bad.get_json() == {"error": "Please choose a sport from the list", "rule": "BR9"}


def test_both_sport_and_area_invalid_is_refused(client):
    """Error: US03 BR9 - When both sport and area are invalid, first validation failure returns HTTP 400."""
    response = client.get("/search?sport=Cricket&area=Saigon")
    assert response.status_code == 400
    assert "Please choose a sport from the list" in response.get_data(as_text=True)


# --- Boundary cases ---------------------------------------------------------

def test_search_with_no_match_shows_message(client):
    """Boundary: US03 AC2, BR9 - Query yielding 0 matching venues returns explicit empty-state message."""
    page = client.get("/search?sport=Tennis&area=Hoan+Kiem").get_data(as_text=True)
    assert "No venues found" in page
    assert 'id="no-match" hidden' not in page          # the message is visible
    assert 'id="results" hidden' in page               # and the empty table is not

    api_resp = client.get("/api/venues?sport=Tennis&area=Hoan+Kiem").get_json()
    assert api_resp == {"venues": [], "message": "No venues found"}


def test_search_empty_and_whitespace_query(client):
    """Boundary: Empty or whitespace-only query parameters return all active venues."""
    # Blank query
    page_blank = client.get("/search?q=").get_data(as_text=True)
    assert 'id="count">24</strong> venue(s) found' in page_blank

    # Whitespace-only query
    page_spaces = client.get("/search?q=%20%20%20").get_data(as_text=True)
    assert 'id="count">24</strong> venue(s) found' in page_spaces

    # API blank filters
    api_data = client.get("/api/venues?sport=&area=&q=").get_json()
    assert len(api_data["venues"]) == 24


def test_search_query_character_length_boundaries(client):
    """Boundary: US03 AC3 - Substring narrowing and case insensitivity boundaries."""
    # 1 character
    page_1 = client.get("/search?q=F").get_data(as_text=True)
    assert "Thong Nhat Football Pitch" in page_1

    # 3 characters boundary (AC3: reaches 3rd character 'bad')
    page_3 = client.get("/search?q=bad").get_data(as_text=True)
    assert "Lan Anh Badminton Court" in page_3
    assert "Thong Nhat Football Pitch" not in page_3

    # Case insensitivity
    upper = client.get("/api/venues?q=BADMINTON").get_json()
    lower = client.get("/api/venues?q=badminton").get_json()
    mixed = client.get("/api/venues?q=BadMinTon").get_json()
    assert len(upper["venues"]) == len(lower["venues"]) == len(mixed["venues"])
    assert len(upper["venues"]) > 0


def test_search_special_characters_and_sql_injection(client):
    """Boundary: SQL injection payloads and special characters are safely handled."""
    payloads = [
        "' OR '1'='1",
        "'; DROP TABLE venue; --",
        "%' UNION SELECT * FROM user --",
        "<script>alert('xss')</script>",
        "%%%",
    ]
    for p in payloads:
        response = client.get("/search", query_string={"q": p})
        assert response.status_code == 200
        api_resp = client.get("/api/venues", query_string={"q": p})
        assert api_resp.status_code == 200


def test_inactive_venues_excluded_from_search(client, db):
    """Boundary: Inactive venues (active=0) do not appear in search results."""
    with connect(db) as conn:
        conn.execute("UPDATE venue SET active = 0 WHERE name = 'Thong Nhat Football Pitch'")
    page = client.get("/search?sport=Football&area=Cau+Giay").get_data(as_text=True)
    assert "Thong Nhat Football Pitch" not in page

    api_resp = client.get("/api/venues?sport=Football&area=Cau+Giay").get_json()
    assert not any(v["name"] == "Thong Nhat Football Pitch" for v in api_resp["venues"])


def test_api_search_returns_venues_or_the_no_match_message(client):
    """API: design.md section 3, endpoint 4."""
    found = client.get("/api/venues?sport=Football&area=Cau+Giay").get_json()
    assert {v["name"] for v in found["venues"]} >= {"Thong Nhat Football Pitch"}
    assert all(v["sport"] == "Football" and v["area"] == "Cau Giay" for v in found["venues"])
    assert client.get("/api/venues?sport=Tennis&area=Hoan+Kiem").get_json() == {
        "venues": [], "message": "No venues found"}
    bad = client.get("/api/venues?area=Saigon")
    assert bad.status_code == 400
    assert bad.get_json() == {"error": "Please choose an area from the list", "rule": "BR9"}
