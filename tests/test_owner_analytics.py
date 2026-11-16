"""Tests for Owner Revenue & Occupancy Analytics, CSV Export, and Google Maps Directions."""
import csv
import io

import pytest

import owner_analytics
from db import connect


def _insert_booking(conn, code, customer_id, venue_id, start_at, end_at, total_price, status="confirmed", refund_amount=None):
    cur = conn.execute(
        """
        INSERT INTO booking (code, customer_id, venue_id, start_at, end_at, total_price, status, refund_amount)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (code, customer_id, venue_id, start_at, end_at, total_price, status, refund_amount),
    )
    conn.commit()
    return cur.lastrowid


def test_get_owner_summary_kpis_and_per_venue_isolation(db):
    with connect(db) as conn:
        lan_id = conn.execute("SELECT id FROM user WHERE email = 'lan.owner@example.com'").fetchone()["id"]
        other_owner_id = conn.execute("SELECT id FROM user WHERE role = 'owner' AND id != ? LIMIT 1", (lan_id,)).fetchone()["id"]
        minh_id = conn.execute("SELECT id FROM user WHERE email = 'minh@example.com'").fetchone()["id"]

        # Clear any pre-seeded bookings/reviews so math is deterministic
        conn.execute("DELETE FROM review")
        conn.execute("DELETE FROM booking_slot")
        conn.execute("DELETE FROM booking")
        conn.commit()

        lan_venues = conn.execute("SELECT id, name FROM venue WHERE owner_id = ? ORDER BY id", (lan_id,)).fetchall()
        other_venue = conn.execute("SELECT id FROM venue WHERE owner_id = ? LIMIT 1", (other_owner_id,)).fetchone()
        assert len(lan_venues) >= 2
        assert other_venue is not None

        v1_id = lan_venues[0]["id"]
        v2_id = lan_venues[1]["id"]
        # Mark v2 inactive to verify active_venues vs total_venues
        conn.execute("UPDATE venue SET active = 0 WHERE id = ?", (v2_id,))
        conn.commit()

        # Lan's bookings:
        # 1) confirmed: 300,000
        _insert_booking(conn, "BK-ANA-001", minh_id, v1_id, "2026-12-20 08:00", "2026-12-20 09:00", 300000, "confirmed", None)
        # 2) completed: 500,000 + visible 5-star review + another completed 400,000 with hidden 1-star review
        b2_id = _insert_booking(conn, "BK-ANA-002", minh_id, v1_id, "2026-12-10 10:00", "2026-12-10 12:00", 500000, "completed", None)
        b3_id = _insert_booking(conn, "BK-ANA-003", minh_id, v1_id, "2026-12-11 10:00", "2026-12-11 12:00", 400000, "completed", None)
        # 3) cancelled on v2: total_price=200,000, refund_amount=100,000 -> net=100,000, excluded from gross_revenue
        _insert_booking(conn, "BK-ANA-004", minh_id, v2_id, "2026-12-22 14:00", "2026-12-22 15:00", 200000, "cancelled", 100000)

        # Other owner's booking (must NOT be included in Lan's summary)
        _insert_booking(conn, "BK-OTH-999", minh_id, other_venue["id"], "2026-12-20 18:00", "2026-12-20 19:00", 999000, "confirmed", None)

        conn.execute("INSERT INTO review (booking_id, rating, comment, hidden) VALUES (?, 5, 'Great pitch', 0)", (b2_id,))
        conn.execute("INSERT INTO review (booking_id, rating, comment, hidden) VALUES (?, 1, 'Spam', 1)", (b3_id,))
        conn.commit()

        summary = owner_analytics.get_owner_summary(conn, lan_id)

    assert summary["total_venues"] == len(lan_venues)
    assert summary["active_venues"] == len(lan_venues) - 1
    assert summary["total_bookings"] == 4
    assert summary["confirmed_bookings"] == 1
    assert summary["completed_bookings"] == 2
    assert summary["cancelled_bookings"] == 1
    assert summary["cancellation_rate"] == 25.0
    assert summary["gross_revenue"] == 1200000
    assert summary["total_refunded"] == 100000
    assert summary["net_revenue"] == 1300000

    per_venue_by_id = {v["id"]: v for v in summary["per_venue"]}
    assert set(per_venue_by_id.keys()) == {v["id"] for v in lan_venues}
    assert other_venue["id"] not in per_venue_by_id

    assert per_venue_by_id[v1_id]["total_bookings"] == 3
    assert per_venue_by_id[v1_id]["net_revenue"] == 1200000
    assert per_venue_by_id[v1_id]["avg_rating"] == 5.0
    assert per_venue_by_id[v1_id]["review_count"] == 1

    assert per_venue_by_id[v2_id]["total_bookings"] == 1
    assert per_venue_by_id[v2_id]["net_revenue"] == 100000
    assert per_venue_by_id[v2_id]["avg_rating"] is None
    assert per_venue_by_id[v2_id]["review_count"] == 0


def test_role_guard_for_analytics_and_csv_export(client, login):
    # Unauthenticated -> redirected to /login
    assert client.get("/owner/analytics").status_code == 302
    assert client.get("/owner/bookings/export.csv").status_code == 302

    # Customer -> 403 Forbidden
    login("minh@example.com")
    assert client.get("/owner/analytics").status_code == 403
    assert client.get("/owner/bookings/export.csv").status_code == 403

    # Owner -> 200 OK and navigation links present on owner pages
    login("lan.owner@example.com")
    analytics_res = client.get("/owner/analytics")
    assert analytics_res.status_code == 200
    analytics_html = analytics_res.get_data(as_text=True)
    assert "Revenue &amp; Venue Analytics" in analytics_html
    assert "/owner/bookings/export.csv" in analytics_html

    venues_html = client.get("/owner/venues").get_data(as_text=True)
    assert "/owner/analytics" in venues_html
    assert "/owner/bookings/export.csv" in venues_html

    bookings_html = client.get("/owner/bookings").get_data(as_text=True)
    assert "/owner/analytics" in bookings_html
    assert "/owner/bookings/export.csv" in bookings_html


@pytest.mark.parametrize("dangerous_prefix", ["=", "+", "-", "@", "\t", "\r"])
def test_csv_export_headers_isolation_and_formula_injection_sanitization(client, login, db, dangerous_prefix):
    with connect(db) as conn:
        lan_id = conn.execute("SELECT id FROM user WHERE email = 'lan.owner@example.com'").fetchone()["id"]
        other_owner_id = conn.execute("SELECT id FROM user WHERE role = 'owner' AND id != ? LIMIT 1", (lan_id,)).fetchone()["id"]
        minh_id = conn.execute("SELECT id FROM user WHERE email = 'minh@example.com'").fetchone()["id"]

        conn.execute("DELETE FROM review")
        conn.execute("DELETE FROM booking_slot")
        conn.execute("DELETE FROM booking")

        lan_venue = conn.execute("SELECT id, name FROM venue WHERE owner_id = ? LIMIT 1", (lan_id,)).fetchone()
        other_venue = conn.execute("SELECT id FROM venue WHERE owner_id = ? LIMIT 1", (other_owner_id,)).fetchone()

        # Inject formula-like payload in customer full_name
        payload_name = f"{dangerous_prefix}SUM(1,1)"
        conn.execute("UPDATE user SET full_name = ? WHERE id = ?", (payload_name, minh_id))

        _insert_booking(conn, "BK-CSV-001", minh_id, lan_venue["id"], "2026-12-20 09:00", "2026-12-20 11:00", 500000, "cancelled", 250000)
        _insert_booking(conn, "BK-CSV-OTHER", minh_id, other_venue["id"], "2026-12-20 12:00", "2026-12-20 13:00", 300000, "confirmed", None)
        conn.commit()

    login("lan.owner@example.com")
    res = client.get("/owner/bookings/export.csv")
    assert res.status_code == 200
    assert res.mimetype == "text/csv"
    assert "attachment; filename=owner-bookings.csv" in res.headers["Content-Disposition"]

    text = res.get_data(as_text=True)
    rows = list(csv.reader(io.StringIO(text)))
    assert rows[0] == [
        "code",
        "venue_name",
        "sport",
        "customer_name",
        "customer_email",
        "start_at",
        "end_at",
        "status",
        "total_price",
        "refund_amount",
        "net_price",
    ]
    assert len(rows) == 2
    data_row = rows[1]
    assert data_row[0] == "BK-CSV-001"
    assert data_row[3] == f"'{payload_name}"
    assert data_row[8] == "500000"
    assert data_row[9] == "250000"
    assert data_row[10] == "250000"
    assert "BK-CSV-OTHER" not in text


def test_google_maps_directions_links_on_venue_and_booking_done(client, login, db):
    with connect(db) as conn:
        venue = conn.execute("SELECT id, address, area FROM venue ORDER BY id LIMIT 1").fetchone()
        minh_id = conn.execute("SELECT id FROM user WHERE email = 'minh@example.com'").fetchone()["id"]
        _insert_booking(conn, "BK-MAP-001", minh_id, venue["id"], "2026-12-21 08:00", "2026-12-21 09:00", 250000, "confirmed", None)

    venue_html = client.get(f"/venues/{venue['id']}").get_data(as_text=True)
    assert "Get Directions (Google Maps)" in venue_html
    assert "https://www.google.com/maps/search/?api=1&query=" in venue_html
    assert 'target="_blank"' in venue_html
    assert 'rel="noopener noreferrer"' in venue_html

    login("minh@example.com")
    done_html = client.get("/bookings/BK-MAP-001").get_data(as_text=True)
    assert "Get Directions (Google Maps)" in done_html
    assert "https://www.google.com/maps/search/?api=1&query=" in done_html
    assert 'target="_blank"' in done_html
    assert 'rel="noopener noreferrer"' in done_html
