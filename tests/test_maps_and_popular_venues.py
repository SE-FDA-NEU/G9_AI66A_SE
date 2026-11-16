"""Tests for Google Maps embeds and interactive venue map UI."""
import json
import re

from db import connect


def test_venue_detail_renders_google_maps_embed_and_directions(client):
    """Venue detail page shows Location & Google Maps card with iframe and action links."""
    resp = client.get("/venues/1")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    assert 'id="venue-map"' in html
    assert "Location &amp; Google Maps" in html
    assert "<iframe" in html
    assert "maps.google.com/maps" in html
    assert "output=embed" in html
    assert "Open in Google Maps" in html
    assert "Get Directions" in html
    assert "https://www.google.com/maps/dir/?api=1&amp;destination=" in html or "https://www.google.com/maps/dir/?api=1&destination=" in html


def test_booking_confirmation_renders_google_maps_embed(client, login, db):
    """Booking receipt page renders compact embedded Google Maps iframe and directions link."""
    login("minh@example.com")
    with connect(db) as conn:
        row = conn.execute(
            "SELECT b.code FROM booking b "
            "JOIN user u ON u.id = b.customer_id "
            "WHERE u.email = 'minh@example.com' "
            "ORDER BY b.id LIMIT 1"
        ).fetchone()
    assert row is not None
    code = row["code"]

    resp = client.get(f"/bookings/{code}")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    assert "<iframe" in html
    assert 'height="220"' in html
    assert "maps.google.com/maps" in html
    assert "output=embed" in html
    assert "Get Directions (Google Maps)" in html


def test_search_page_stays_clean_without_map_clutter(client):
    """Search page stays clean without map panels/modals; Google Maps lives on venue detail."""
    resp = client.get("/search")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    assert 'id="toggleMapBtn"' not in html
    assert 'id="venueMapPanel"' not in html
    assert 'id="leafletVenueMap"' not in html
    assert 'id="gmapModal"' not in html
