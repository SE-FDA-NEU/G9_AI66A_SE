"""US06 - Venue owner adds a new venue (#21): BR9, BR13, BR14."""
import io

import pytest

from db import connect

THONG_NHAT = {"name": "Thong Nhat Football Pitch 2", "sport": "Football", "area": "Cau Giay",
              "address": "12 Tran Thai Tong", "hourly_price": "250,000", "open_hour": "6", "close_hour": "22"}
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100


def add_venue(client, photo=None, **changes):
    data = {**THONG_NHAT, **changes}
    if photo:
        data["photo"] = photo
    return client.post("/owner/venues/new", data=data, content_type="multipart/form-data")


@pytest.fixture
def owner(login):
    response = login("lan.owner@example.com")
    assert response.status_code == 302, "owner login failed"
    return "lan.owner@example.com"
    


def test_owner_adds_a_venue_with_a_photo(client, owner, db):
    # US06 criterion 1
    response = add_venue(client, photo=(io.BytesIO(PNG), "pitch.png"))
    assert response.status_code == 302
    assert response.headers["Location"] == "/owner/venues"
    page = client.get("/owner/venues").get_data(as_text=True)
    assert "Venue added successfully!" in page
    assert "Thong Nhat Football Pitch 2" in page and "250,000" in page
    with connect(db) as conn:
        venue = conn.execute("SELECT * FROM venue WHERE name = 'Thong Nhat Football Pitch 2'").fetchone()
        photo = conn.execute("SELECT file_name FROM venue_photo WHERE venue_id = ?", (venue["id"],)).fetchone()
    assert venue["hourly_price"] == 250000
    assert (client.application.config["UPLOAD_DIR"] / photo["file_name"]).read_bytes() == PNG
    # customers can now find it and see the photo
    assert "Thong Nhat Football Pitch 2" in client.get("/search?sport=Football&area=Cau+Giay").get_data(as_text=True)
    assert f"/venues/{venue['id']}/photos/" in client.get(f"/venues/{venue['id']}").get_data(as_text=True)


@pytest.mark.parametrize("price", ["0", "-50,000", "999"])
def test_price_below_1000_is_refused(client, owner, price):
    # US06 criterion 2, BR13
    response = add_venue(client, hourly_price=price)
    assert response.status_code == 422
    assert "Hourly price must be at least 1,000 VND" in response.get_data(as_text=True)


def test_price_above_100_million_is_refused(client, owner):
    response = add_venue(client, hourly_price="100,000,001")
    assert "Hourly price must be at most 100,000,000 VND" in response.get_data(as_text=True)


@pytest.mark.parametrize("name, message", [("", "Please enter the venue name"),
                                           ("Sa", "Venue name must be 3 to 100 characters"),
                                           ("x" * 101, "Venue name must be 3 to 100 characters")])
def test_name_is_required_and_3_to_100_characters(client, owner, name, message):
    # US06 criterion 3, BR13
    response = add_venue(client, name=name)
    assert response.status_code == 422
    assert message in response.get_data(as_text=True)


def test_form_keeps_what_the_owner_typed(client, owner):
    page = add_venue(client, hourly_price="0").get_data(as_text=True)
    assert 'value="12 Tran Thai Tong"' in page
    assert "<option selected>Cau Giay</option>" in page


def test_customer_gets_403_on_the_add_venue_page(client, login):
    # US06 criterion 4, BR14
    login("minh@example.com")
    response = client.get("/owner/venues/new")
    assert response.status_code == 403
    assert "You do not have permission to access this page" in response.get_data(as_text=True)


def test_sport_and_area_come_from_drop_down_lists(client, owner):
    # US06 criterion 5, BR9: the page offers lists, and a typed value is refused
    page = client.get("/owner/venues/new").get_data(as_text=True)
    assert '<select name="sport"' in page and '<select name="area"' in page
    response = add_venue(client, sport="Golf", area="District 5")
    body = response.get_data(as_text=True)
    assert "Please choose a sport from the list" in body
    assert "Please choose an area from the list" in body


def test_photo_must_be_jpg_or_png(client, owner):
    response = add_venue(client, photo=(io.BytesIO(b"MZ"), "virus.exe"))
    assert response.status_code == 422
    assert "The photo must be a JPG or PNG file" in response.get_data(as_text=True)


def test_photo_larger_than_5_mb_is_refused(client, owner):
    response = add_venue(client, photo=(io.BytesIO(b"0" * (5 * 1024 * 1024 + 1)), "big.jpg"))
    assert response.status_code == 413
    assert "The photo is larger than 5 MB" in response.get_data(as_text=True)


def test_owner_sees_only_their_own_venues(client, owner):
    # BR14: Lan owns Thong Nhat; Hung's venues are not on her list
    body = client.get("/api/owner/venues").get_json()
    with connect(client.application.config["DATABASE"]) as conn:
        lan_id = conn.execute("SELECT id FROM user WHERE email = 'lan.owner@example.com'").fetchone()[0]
    assert body["venues"] and all(v["owner_id"] == lan_id for v in body["venues"])


def test_api_create_venue(client, owner):
    # design.md section 3, endpoint 7
    created = client.post("/api/owner/venues", json={**THONG_NHAT, "hourly_price": 250000})
    assert created.status_code == 201
    assert "venue_id" in created.get_json()
    refused = client.post("/api/owner/venues", json={**THONG_NHAT, "hourly_price": 0})
    assert refused.status_code == 422
    assert refused.get_json() == {"error": "Hourly price must be at least 1,000 VND", "rule": "BR13"}
@pytest.mark.parametrize("price", ["1000", "100000000"])
def test_owner_can_create_venue_at_price_boundaries(client, owner, db, price):
    response = add_venue(client, hourly_price=price)

    assert response.status_code == 302
    assert response.headers["Location"] == "/owner/venues"

    with connect(db) as conn:
        venue = conn.execute(
            "SELECT * FROM venue WHERE name = ?",
            (THONG_NHAT["name"],),
        ).fetchone()

    assert venue is not None
    assert venue["hourly_price"] == int(price)

@pytest.mark.parametrize("name", ["ABC", "A" * 100])
def test_owner_can_create_venue_at_name_boundaries(client, owner, db, name):
    response = add_venue(client, name=name)

    assert response.status_code == 302
    assert response.headers["Location"] == "/owner/venues"

    with connect(db) as conn:
        venue = conn.execute(
            "SELECT * FROM venue WHERE name = ?",
            (name,),
        ).fetchone()

    assert venue is not None
    assert venue["name"] == name

def test_customer_cannot_create_venue_via_api(client, login, db):
    login("minh@example.com")

    with connect(db) as conn:
        count_before = conn.execute(
            "SELECT COUNT(*) FROM venue"
        ).fetchone()[0]

    response = client.post(
        "/api/owner/venues",
        json={**THONG_NHAT, "hourly_price": 250000},
    )

    assert response.status_code == 403

    with connect(db) as conn:
        count_after = conn.execute(
            "SELECT COUNT(*) FROM venue"
        ).fetchone()[0]

    assert count_after == count_before

@pytest.mark.parametrize("changes", [
    {"name": "   "},
    {"address": ""},
    {"sport": ""},
    {"area": ""},
    {"hourly_price": ""},
    {"hourly_price": "abc"},
])
def test_invalid_venue_is_not_saved(client, owner, db, changes):
    with connect(db) as conn:
        count_before = conn.execute(
            "SELECT COUNT(*) FROM venue"
        ).fetchone()[0]

    response = add_venue(client, **changes)

    assert response.status_code == 422

    with connect(db) as conn:
        count_after = conn.execute(
            "SELECT COUNT(*) FROM venue"
        ).fetchone()[0]

    assert count_after == count_before

@pytest.mark.parametrize("method", ["get", "post"])
def test_guest_cannot_access_owner_venues_api(client, db, method):
    with connect(db) as conn:
        count_before = conn.execute(
            "SELECT COUNT(*) FROM venue"
        ).fetchone()[0]

    if method == "get":
        response = client.get("/api/owner/venues")
    else:
        response = client.post(
            "/api/owner/venues",
            json={**THONG_NHAT, "hourly_price": 250000},
        )

    assert response.status_code == 401

    with connect(db) as conn:
        count_after = conn.execute(
            "SELECT COUNT(*) FROM venue"
        ).fetchone()[0]

    assert count_after == count_before
    
def test_owner_with_no_venues_sees_empty_list(client, owner, db):
    with connect(db) as conn:
        conn.execute(
            "INSERT INTO user (email, full_name, phone, password_hash, role) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                "empty.owner@example.com",
                "Empty Owner",
                "0900000000",
                "unused",
                "owner",
            ),
        )
        new_owner_id = conn.execute(
            "SELECT id FROM user WHERE email = ?",
            ("empty.owner@example.com",),
        ).fetchone()[0]
        conn.commit()

    with client.session_transaction() as session:
        session["user_id"] = new_owner_id

    response = client.get("/owner/venues")

    assert response.status_code == 200
    assert "You have no venues yet" in response.get_data(as_text=True)

    response = client.get("/api/owner/venues")

    assert response.status_code == 200
    assert response.get_json() == {"venues": []}

def test_new_venue_appears_first_in_owner_list(client, owner, db):
    response = add_venue(client, name="Newest Owner Venue")
    assert response.status_code == 302

    response = client.get("/api/owner/venues")
    assert response.status_code == 200

    venues = response.get_json()["venues"]
    assert venues[0]["name"] == "Newest Owner Venue"

    with connect(db) as conn:
        owner_id = conn.execute(
            "SELECT id FROM user WHERE email = ?",
            (owner,),
        ).fetchone()[0]

    assert all(venue["owner_id"] == owner_id for venue in venues)
    assert venues[0]["active"] == 1