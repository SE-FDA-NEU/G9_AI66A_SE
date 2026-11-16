"""Owner analytics and CSV export service layer (BR14)."""
import csv
import io

CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _int(val):
    return int(val) if val is not None else 0


def _rounded_avg(val):
    return round(float(val), 1) if val is not None else None


def sanitize_csv_cell(value):
    """Prefix cells starting with formula-triggering characters to prevent CSV injection."""
    if value is None:
        return ""
    text = str(value)
    if text and text[0] in CSV_FORMULA_PREFIXES:
        return "'" + text
    return text


def get_owner_summary(conn, owner_id):
    """Return revenue, booking, cancellation, and per-venue analytics for one owner (BR14)."""
    venue_row = conn.execute(
        """
        SELECT COUNT(*) AS total_venues,
               COALESCE(SUM(CASE WHEN active = 1 THEN 1 ELSE 0 END), 0) AS active_venues
        FROM venue
        WHERE owner_id = ?
        """,
        (owner_id,),
    ).fetchone()

    booking_row = conn.execute(
        """
        SELECT COUNT(*) AS total_bookings,
               COALESCE(SUM(CASE WHEN b.status = 'confirmed' THEN 1 ELSE 0 END), 0) AS confirmed_bookings,
               COALESCE(SUM(CASE WHEN b.status = 'completed' THEN 1 ELSE 0 END), 0) AS completed_bookings,
               COALESCE(SUM(CASE WHEN b.status = 'cancelled' THEN 1 ELSE 0 END), 0) AS cancelled_bookings,
               COALESCE(SUM(CASE WHEN b.status != 'cancelled' THEN b.total_price ELSE 0 END), 0) AS gross_revenue,
               COALESCE(SUM(COALESCE(b.refund_amount, 0)), 0) AS total_refunded,
               COALESCE(SUM(b.total_price - COALESCE(b.refund_amount, 0)), 0) AS net_revenue
        FROM booking b
        JOIN venue v ON v.id = b.venue_id
        WHERE v.owner_id = ?
        """,
        (owner_id,),
    ).fetchone()

    per_venue_rows = conn.execute(
        """
        SELECT v.id,
               v.name,
               v.sport,
               v.area,
               v.active,
               COUNT(b.id) AS total_bookings,
               COALESCE(SUM(b.total_price - COALESCE(b.refund_amount, 0)), 0) AS net_revenue,
               AVG(CASE WHEN r.hidden = 0 THEN r.rating END) AS avg_rating,
               COUNT(CASE WHEN r.hidden = 0 THEN 1 END) AS review_count
        FROM venue v
        LEFT JOIN booking b ON b.venue_id = v.id
        LEFT JOIN review r ON r.booking_id = b.id
        WHERE v.owner_id = ?
        GROUP BY v.id
        ORDER BY net_revenue DESC, total_bookings DESC, v.id ASC
        """,
        (owner_id,),
    ).fetchall()

    total_bookings = _int(booking_row["total_bookings"])
    cancelled_bookings = _int(booking_row["cancelled_bookings"])
    cancellation_rate = round((cancelled_bookings / total_bookings) * 100, 1) if total_bookings > 0 else 0.0

    per_venue = [
        {
            "id": row["id"],
            "name": row["name"],
            "sport": row["sport"],
            "area": row["area"],
            "active": row["active"],
            "total_bookings": _int(row["total_bookings"]),
            "net_revenue": _int(row["net_revenue"]),
            "avg_rating": _rounded_avg(row["avg_rating"]),
            "review_count": _int(row["review_count"]),
        }
        for row in per_venue_rows
    ]

    recent_review_rows = conn.execute(
        """
        SELECT r.id, r.rating, r.comment, r.created_at, r.hidden, r.report_count,
               b.code AS booking_code, v.id AS venue_id, v.name AS venue_name,
               u.full_name AS customer_name
        FROM review r
        JOIN booking b ON b.id = r.booking_id
        JOIN venue v ON v.id = b.venue_id
        JOIN user u ON u.id = b.customer_id
        WHERE v.owner_id = ?
        ORDER BY r.id DESC
        LIMIT 15
        """,
        (owner_id,),
    ).fetchall()

    recent_alert_rows = conn.execute(
        """
        SELECT b.code, b.status, b.start_at, b.end_at, b.total_price, b.refund_amount,
               v.name AS venue_name, u.full_name AS customer_name, u.phone AS customer_phone
        FROM booking b
        JOIN venue v ON v.id = b.venue_id
        JOIN user u ON u.id = b.customer_id
        WHERE v.owner_id = ?
        ORDER BY b.id DESC
        LIMIT 10
        """,
        (owner_id,),
    ).fetchall()

    return {
        "total_venues": _int(venue_row["total_venues"]),
        "active_venues": _int(venue_row["active_venues"]),
        "total_bookings": total_bookings,
        "confirmed_bookings": _int(booking_row["confirmed_bookings"]),
        "completed_bookings": _int(booking_row["completed_bookings"]),
        "cancelled_bookings": cancelled_bookings,
        "cancellation_rate": cancellation_rate,
        "gross_revenue": _int(booking_row["gross_revenue"]),
        "total_refunded": _int(booking_row["total_refunded"]),
        "net_revenue": _int(booking_row["net_revenue"]),
        "per_venue": per_venue,
        "recent_reviews": [dict(r) for r in recent_review_rows],
        "recent_alerts": [dict(r) for r in recent_alert_rows],
    }


def export_owner_bookings_csv(conn, owner_id):
    """Export all bookings belonging to owner_id's venues as a sanitized CSV string (BR14)."""
    rows = conn.execute(
        """
        SELECT b.code,
               v.name AS venue_name,
               v.sport,
               u.full_name AS customer_name,
               u.email AS customer_email,
               b.start_at,
               b.end_at,
               b.status,
               b.total_price,
               COALESCE(b.refund_amount, 0) AS refund_amount,
               (b.total_price - COALESCE(b.refund_amount, 0)) AS net_price
        FROM booking b
        JOIN venue v ON v.id = b.venue_id
        JOIN user u ON u.id = b.customer_id
        WHERE v.owner_id = ?
        ORDER BY b.start_at DESC, b.id DESC
        """,
        (owner_id,),
    ).fetchall()

    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow([
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
    ])
    for row in rows:
        writer.writerow([
            sanitize_csv_cell(row["code"]),
            sanitize_csv_cell(row["venue_name"]),
            sanitize_csv_cell(row["sport"]),
            sanitize_csv_cell(row["customer_name"]),
            sanitize_csv_cell(row["customer_email"]),
            sanitize_csv_cell(row["start_at"]),
            sanitize_csv_cell(row["end_at"]),
            sanitize_csv_cell(row["status"]),
            sanitize_csv_cell(row["total_price"]),
            sanitize_csv_cell(row["refund_amount"]),
            sanitize_csv_cell(row["net_price"]),
        ])
    return buf.getvalue()
