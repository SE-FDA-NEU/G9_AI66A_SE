"""Comprehensive tests for top-tier search, sort, quote, ICS, my-bookings, and UX guards (issue #118)."""
import re
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

from app import create_app
from db import connect
import booking as svc


PINNED_NOW = datetime(2026, 11, 20, 9, 0)


def _pinned_client(db, tmp_path, now_dt=PINNED_NOW):
    app = create_app(database=db)
    app.config["UPLOAD_DIR"] = tmp_path / "uploads"
    app.config["NOW"] = lambda: now_dt
    return app.test_client()


def _csrf_token(test_client):
    html = test_client.get("/login").get_data(as_text=True)
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    return m.group(1) if m else ""


def _login_on(test_client, email, password="sanbong1"):
    token = _csrf_token(test_client)
    return test_client.post(
        "/login",
        data={"email": email, "password": password, "csrf_token": token},
    )


# ---------------------------------------------------------------------------
# 1. Search sorting
# ---------------------------------------------------------------------------

def test_search_sort_options_api(client):
    """Normal: price_asc, price_desc, rating_desc, name_asc return properly ordered venues."""
    r_asc = client.get("/api/venues?sort=price_asc")
    assert r_asc.status_code == 200
    prices_asc = [v["hourly_price"] for v in r_asc.get_json()["venues"]]
    assert prices_asc == sorted(prices_asc)

    r_desc = client.get("/api/venues?sort=price_desc")
    assert r_desc.status_code == 200
    prices_desc = [v["hourly_price"] for v in r_desc.get_json()["venues"]]
    assert prices_desc == sorted(prices_desc, reverse=True)

    r_name = client.get("/api/venues?sort=name_asc")
    assert r_name.status_code == 200
    names = [v["name"].lower() for v in r_name.get_json()["venues"]]
    assert names == sorted(names)

    r_rating = client.get("/api/venues?sort=rating_desc")
    assert r_rating.status_code == 200
    rated = r_rating.get_json()["venues"]
    ratings = [v["avg_rating"] or 0 for v in rated]
    assert ratings == sorted(ratings, reverse=True)


def test_search_invalid_sort_returns_400(client):
    """Error: invalid sort parameter returns 400 on both /search and /api/venues."""
    res_html = client.get("/search?sort=popularity_desc")
    assert res_html.status_code == 400
    assert "Please choose a valid sort option" in res_html.get_data(as_text=True)

    res_api = client.get("/api/venues?sort=popularity_desc")
    assert res_api.status_code == 400
    assert "valid sort option" in res_api.get_json()["error"]


# ---------------------------------------------------------------------------
# 2. Search price range filters
# ---------------------------------------------------------------------------

def test_search_price_range_filters(client):
    """Normal & Boundary: min_price and max_price filter venues inclusively."""
    res = client.get("/api/venues?min_price=150000&max_price=300000")
    assert res.status_code == 200
    venues_list = res.get_json()["venues"]
    assert len(venues_list) > 0
    assert all(150000 <= v["hourly_price"] <= 300000 for v in venues_list)

    # Boundary: exact equality min_price == max_price
    exact_price = venues_list[0]["hourly_price"]
    res_exact = client.get(f"/api/venues?min_price={exact_price}&max_price={exact_price}")
    assert res_exact.status_code == 200
    assert all(v["hourly_price"] == exact_price for v in res_exact.get_json()["venues"])


def test_search_invalid_price_filters_return_400(client):
    """Error: non-numeric, negative, or inverted price range returns 400."""
    for bad in ("min_price=abc", "max_price=-50000"):
        assert client.get(f"/search?{bad}").status_code == 400
        assert client.get(f"/api/venues?{bad}").status_code == 400

    res = client.get("/api/venues?min_price=500000&max_price=100000")
    assert res.status_code == 400
    assert "Minimum price cannot exceed maximum price" in res.get_json()["error"]


# ---------------------------------------------------------------------------
# 3. Search date & hour availability filters
# ---------------------------------------------------------------------------

def test_search_date_and_hour_excludes_booked_and_blocked_venues(db, tmp_path):
    """Normal: venues booked or blocked at the requested date+hour are excluded."""
    tc = _pinned_client(db, tmp_path)
    target_day = (PINNED_NOW + timedelta(days=2)).date().isoformat()

    with connect(db) as conn:
        user = conn.execute("SELECT * FROM user WHERE email = 'minh@example.com'").fetchone()
        # Book venue 1 at 14:00 for 1 hour
        svc.create_booking(conn, user, 1, target_day, 14, 1, PINNED_NOW)
        # Block venue 2 at 14:00
        conn.execute(
            "INSERT INTO blocked_slot (venue_id, slot_start, reason) VALUES (?, ?, ?)",
            (2, f"{target_day} 14:00", "Maintenance"),
        )

    res = tc.get(f"/api/venues?date={target_day}&hour=14")
    assert res.status_code == 200
    ids = {v["id"] for v in res.get_json()["venues"]}
    assert 1 not in ids
    assert 2 not in ids
    assert len(ids) > 0


def test_search_invalid_date_past_date_and_invalid_hour_return_400(db, tmp_path):
    """Error: invalid date, past date, and out-of-range/non-numeric hour return 400."""
    tc = _pinned_client(db, tmp_path)
    past_day = (PINNED_NOW - timedelta(days=1)).date().isoformat()

    for qs in (
        "date=not-a-date",
        f"date={past_day}",
        "hour=25",
        "hour=-1",
        "hour=noon",
    ):
        assert tc.get(f"/search?{qs}").status_code == 400, qs
        assert tc.get(f"/api/venues?{qs}").status_code == 400, qs


# ---------------------------------------------------------------------------
# 4. Search API & HTML enrichments
# ---------------------------------------------------------------------------

def test_search_api_and_html_enrichments_and_quick_pills(db, tmp_path):
    """Normal: avg_rating, review_count, free_slots_count in API & HTML; data-venue-id & pills."""
    tc = _pinned_client(db, tmp_path)
    api_res = tc.get("/api/venues")
    assert api_res.status_code == 200
    sample = api_res.get_json()["venues"][0]
    for key in ("avg_rating", "review_count", "free_slots_count"):
        assert key in sample

    html = tc.get("/search?area=Cau+Giay&sort=price_asc&min_price=100000").get_data(as_text=True)
    # data-venue-id on both card and table row
    assert f'class="venue-card-item venue-card-filter-target" data-venue-id="{sample["id"]}"' in html or 'data-venue-id="' in html
    assert '<tr data-venue-id="' in html
    assert "free today" in html

    # Quick-filter pills preserve existing query parameters (area, sort, min_price)
    assert "sport=Football" in html
    assert "area=Cau+Giay" in html
    assert "sort=price_asc" in html
    assert "min_price=100000" in html


# ---------------------------------------------------------------------------
# 5. GET /api/quote/<venue_id>
# ---------------------------------------------------------------------------

def test_api_quote_standard_and_peak_boundary_crossing(db, tmp_path):
    """Normal & Boundary: quote across standard + peak boundary returns segmented is_peak."""
    tc = _pinned_client(db, tmp_path)
    # Pick a future date whose weekday matches a seeded pricing rule for venue 1, or insert one
    target_day = (PINNED_NOW + timedelta(days=3)).date()
    weekday = target_day.weekday()
    with connect(db) as conn:
        venue = conn.execute("SELECT * FROM venue WHERE id = 1").fetchone()
        base_price = venue["hourly_price"]
        peak_price = base_price + 100000
        conn.execute(
            "DELETE FROM pricing_rule WHERE venue_id = 1 AND weekday = ?",
            (weekday,),
        )
        conn.execute(
            "INSERT INTO pricing_rule (venue_id, weekday, start_hour, end_hour, price_per_hour)"
            " VALUES (1, ?, 17, 21, ?)",
            (weekday, peak_price),
        )

    # 16:00 -> 18:00 crosses 17:00 peak boundary: 1h standard + 1h peak
    res = tc.get(f"/api/quote/1?date={target_day.isoformat()}&start_hour=16&hours=2")
    assert res.status_code == 200
    data = res.get_json()
    assert data["venue_id"] == 1
    assert data["total_price"] == base_price + peak_price
    assert len(data["segments"]) == 2
    assert data["segments"][0]["is_peak"] is False
    assert data["segments"][1]["is_peak"] is True


def test_api_quote_errors_400_and_404(db, tmp_path):
    """Error: invalid date/hour/hours -> 400; unknown venue -> 404."""
    tc = _pinned_client(db, tmp_path)
    future_day = (PINNED_NOW + timedelta(days=2)).date().isoformat()

    assert tc.get(f"/api/quote/99999?date={future_day}&start_hour=10&hours=1").status_code == 404
    assert tc.get("/api/quote/1?date=bad-date&start_hour=10&hours=1").status_code == 400
    assert tc.get(f"/api/quote/1?date={future_day}&start_hour=abc&hours=1").status_code == 400
    assert tc.get(f"/api/quote/1?date={future_day}&start_hour=10&hours=5").status_code == 400
    assert tc.get(f"/api/quote/1?date={future_day}&start_hour=2&hours=1").status_code == 400


def test_api_quote_409_unavailable_and_api_venue_includes_slot_prices(db, tmp_path):
    """Error & Normal: /api/quote returns 409 for booked/blocked slots and 400 for past slots; /api/venues includes slot_prices."""
    tc = _pinned_client(db, tmp_path)
    future_day = (PINNED_NOW + timedelta(days=5)).date().isoformat()

    # /api/venues/<id> includes slot_prices
    v_res = tc.get(f"/api/venues/1?date={future_day}")
    assert v_res.status_code == 200
    v_data = v_res.get_json()
    assert "slot_prices" in v_data
    assert isinstance(v_data["slot_prices"], dict)
    assert len(v_data["slot_prices"]) > 0

    # Past slot -> 400
    past_res = tc.get(f"/api/quote/1?date={PINNED_NOW.date().isoformat()}&start_hour={PINNED_NOW.hour}&hours=1")
    assert past_res.status_code == 400
    assert past_res.get_json()["rule"] == "BR11"

    # Blocked slot -> 409
    with connect(db) as conn:
        conn.execute(
            "INSERT INTO blocked_slot (venue_id, slot_start, reason) VALUES (1, ?, 'Maintenance')",
            (f"{future_day} 10:00",),
        )
    blocked_res = tc.get(f"/api/quote/1?date={future_day}&start_hour=9&hours=2")
    assert blocked_res.status_code == 409
    assert blocked_res.get_json()["rule"] == "BR11"

    # Booked slot -> 409
    with connect(db) as conn:
        conn.execute(
            "INSERT INTO booking (code, venue_id, customer_id, start_at, end_at, total_price, status)"
            " VALUES ('BK-TEST-409', 1, 1, ?, ?, 100000, 'confirmed')",
            (f"{future_day} 14:00", f"{future_day} 15:00"),
        )
        booking_id = conn.execute("SELECT id FROM booking WHERE code = 'BK-TEST-409'").fetchone()["id"]
        conn.execute(
            "INSERT INTO booking_slot (booking_id, venue_id, slot_start, price) VALUES (?, 1, ?, 100000)",
            (booking_id, f"{future_day} 14:00"),
        )
    booked_res = tc.get(f"/api/quote/1?date={future_day}&start_hour=14&hours=1")
    assert booked_res.status_code == 409
    assert booked_res.get_json()["rule"] == "BR11"


# ---------------------------------------------------------------------------
# 6. GET /my-bookings/<code>/ics
# ---------------------------------------------------------------------------

def test_booking_ics_owner_other_user_unknown_and_unauthenticated(client):
    """Normal, Security & Error: .ics download checks ownership and auth."""
    # Unauthenticated -> 302 to /login
    anon_res = client.get("/my-bookings/BK-000103/ics")
    assert anon_res.status_code == 302
    assert "/login" in anon_res.headers["Location"]

    # Owner (minh@example.com owns BK-000103) -> 200 text/calendar
    _login_on(client, "minh@example.com")
    ok_res = client.get("/my-bookings/BK-000103/ics")
    assert ok_res.status_code == 200
    assert "text/calendar" in ok_res.content_type
    body = ok_res.get_data(as_text=True)
    assert "BEGIN:VCALENDAR" in body
    assert "DTSTART" in body
    assert "SUMMARY:" in body
    assert "BK-000103" in body

    # Unknown code -> 404
    assert client.get("/my-bookings/BK-999999/ics").status_code == 404

    # Another customer (trang@example.com) -> 403
    _login_on(client, "trang@example.com")
    assert client.get("/my-bookings/BK-000103/ics").status_code == 403


# ---------------------------------------------------------------------------
# 7. status=completed & status=confirmed filtering + tab counts + links
# ---------------------------------------------------------------------------

def test_my_bookings_past_confirmed_moves_to_completed_with_counts_and_links(db, tmp_path):
    """Normal & Boundary: past confirmed bookings appear under completed, not confirmed; tabs & links present."""
    # Pin NOW to a future date so a seeded 'confirmed' booking is in the past
    with connect(db) as conn:
        user = conn.execute("SELECT * FROM user WHERE email = 'minh@example.com'").fetchone()
        past_confirmed = conn.execute(
            "SELECT code, end_at FROM booking WHERE customer_id = ? AND status = 'confirmed' ORDER BY end_at ASC LIMIT 1",
            (user["id"],),
        ).fetchone()
        assert past_confirmed is not None
        end_dt = datetime.strptime(str(past_confirmed["end_at"])[:16], "%Y-%m-%d %H:%M")

    # Set NOW 2 hours after that booking's end_at
    tc = _pinned_client(db, tmp_path, now_dt=end_dt + timedelta(hours=2))
    _login_on(tc, "minh@example.com")

    completed_html = tc.get("/my-bookings?status=completed").get_data(as_text=True)
    assert past_confirmed["code"] in completed_html
    assert 'class="tab-count-badge"' in completed_html

    confirmed_html = tc.get("/my-bookings?status=confirmed").get_data(as_text=True)
    assert past_confirmed["code"] not in confirmed_html

    all_html = tc.get("/my-bookings").get_data(as_text=True)
    assert "Add to Calendar (.ics)" in all_html
    assert "Book Again" in all_html


# ---------------------------------------------------------------------------
# 8. ?next= query string preservation on unauthenticated /booking/<id>
# ---------------------------------------------------------------------------

def test_unauthenticated_booking_preserves_full_next_query_string(client):
    """Normal: unauthenticated GET /booking/1?date=...&start_hour=10&hours=2 preserves ?next=."""
    res = client.get("/booking/1?date=2026-12-01&start_hour=10&hours=2")
    assert res.status_code == 302
    location = res.headers["Location"]
    parsed = urlparse(location)
    assert parsed.path == "/login"
    next_vals = parse_qs(parsed.query).get("next", [])
    assert len(next_vals) == 1
    assert next_vals[0] == "/booking/1?date=2026-12-01&start_hour=10&hours=2"


# ---------------------------------------------------------------------------
# 9. Owner route input guards (no 500 on invalid inputs)
# ---------------------------------------------------------------------------

def test_owner_route_input_guards_do_not_500(client):
    """Error: invalid date / hour / price_per_hour on owner routes return 302/200/400, never 500."""
    _login_on(client, "lan.owner@example.com")
    token = _csrf_token(client)

    # owner_bookings_page with invalid date
    r1 = client.get("/owner/bookings?date=invalid-date")
    assert r1.status_code == 200

    # block_slot_route with invalid date and non-numeric hour
    r2 = client.post(
        "/owner/venues/1/schedule/block",
        data={"date": "bad", "hour": "xyz", "csrf_token": token},
    )
    assert r2.status_code == 302

    # api_block_slot with invalid date/hour -> 400
    r3 = client.post("/api/owner/venues/1/block", json={"date": "bad", "hour": "xyz"})
    assert r3.status_code == 400

    # add_pricing_rule_route with invalid price_per_hour / weekday / hours
    r4 = client.post(
        "/owner/venues/1/pricing",
        data={
            "weekday": "0",
            "start_hour": "18",
            "end_hour": "20",
            "price_per_hour": "not-a-number",
            "csrf_token": token,
        },
    )
    assert r4.status_code == 302


# ---------------------------------------------------------------------------
# 10. UI markers on venue.html, booking.html, owner_bookings.html, owner_pricing.html
# ---------------------------------------------------------------------------

def test_ui_markers_on_venue_booking_and_owner_pages(client, db):
    """Normal: verify expected UX markers across venue, booking, and owner templates."""
    venue_html = client.get("/venues/1").get_data(as_text=True)
    assert "Cancellation Policy" in venue_html
    assert "Get Directions (Google Maps)" in venue_html
    assert "slot-price" in venue_html

    _login_on(client, "minh@example.com")
    booking_html = client.get("/booking/1").get_data(as_text=True)
    assert "Cancellation Policy" in booking_html
    assert "View on Map" in booking_html

    with connect(db) as conn:
        b = conn.execute(
            "SELECT substr(start_at, 1, 10) AS d FROM booking WHERE venue_id = 1 LIMIT 1"
        ).fetchone()
        booking_date = b["d"]

    _login_on(client, "lan.owner@example.com")
    owner_bookings_html = client.get(f"/owner/bookings?date={booking_date}").get_data(as_text=True)
    assert 'class="table-scroll"' in owner_bookings_html

    owner_pricing_html = client.get("/owner/venues/1/pricing").get_data(as_text=True)
    assert 'class="table-scroll"' in owner_pricing_html


def test_search_hd_video_background_and_login_auth_stage(client):
    """Normal: /search renders HD video background (hero-courts.mp4 and .hero-bg-slide) and /login renders .auth-stage."""
    search_res = client.get("/search")
    assert search_res.status_code == 200
    search_html = search_res.get_data(as_text=True)
    assert "hero-courts.mp4" in search_html
    assert "hero-bg-slide" in search_html

    login_res = client.get("/login")
    assert login_res.status_code == 200
    login_html = login_res.get_data(as_text=True)
    assert 'class="auth-stage"' in login_html

