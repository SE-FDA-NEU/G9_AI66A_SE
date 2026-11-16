"""Admin portal service layer: platform analytics, account governance, venue control, and review moderation."""
import sqlite3

from werkzeug.security import generate_password_hash

import auth
import venues
from errors import BusinessRuleError
from time_utils import vn_now

VALID_ROLES = ("customer", "owner", "admin")
VALID_MOD_STATUSES = ("active", "pending", "approved", "rejected")
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _int(val):
    return int(val) if val is not None else 0


def _rounded_avg(val):
    return round(float(val), 1) if val is not None else None


def _as_str(value, field_name, default=""):
    if value is None:
        return default
    if not isinstance(value, str):
        raise BusinessRuleError(400, f"Invalid {field_name}: must be text", field=field_name)
    return value


def get_platform_stats(conn):
    """Return high-level platform KPIs across users, venues, bookings, revenue, and reviews."""
    user_row = conn.execute(
        """
        SELECT COUNT(*) AS total_users,
               COALESCE(SUM(CASE WHEN role = 'customer' THEN 1 ELSE 0 END), 0) AS customers_count,
               COALESCE(SUM(CASE WHEN role = 'owner' THEN 1 ELSE 0 END), 0) AS owners_count,
               COALESCE(SUM(CASE WHEN role = 'admin' THEN 1 ELSE 0 END), 0) AS admins_count,
               COALESCE(SUM(CASE WHEN suspended = 1 THEN 1 ELSE 0 END), 0) AS suspended_users_count,
               COALESCE(SUM(CASE WHEN email_verified_at IS NULL THEN 1 ELSE 0 END), 0) AS unverified_users_count
        FROM user
        """
    ).fetchone()

    venue_row = conn.execute(
        """
        SELECT COUNT(*) AS total_venues,
               COALESCE(SUM(CASE WHEN active = 1 THEN 1 ELSE 0 END), 0) AS active_venues_count,
               COALESCE(SUM(CASE WHEN active = 0 THEN 1 ELSE 0 END), 0) AS inactive_venues_count
        FROM venue
        """
    ).fetchone()

    zero_bookings_row = conn.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM venue v
        WHERE NOT EXISTS (SELECT 1 FROM booking b WHERE b.venue_id = v.id)
        """
    ).fetchone()

    booking_row = conn.execute(
        """
        SELECT COUNT(*) AS total_bookings,
               COALESCE(SUM(CASE WHEN status = 'confirmed' THEN 1 ELSE 0 END), 0) AS confirmed_bookings,
               COALESCE(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END), 0) AS completed_bookings,
               COALESCE(SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END), 0) AS cancelled_bookings,
               COALESCE(SUM(total_price), 0) AS gross_revenue,
               COALESCE(SUM(total_price - COALESCE(refund_amount, 0)), 0) AS net_revenue,
               COALESCE(SUM(COALESCE(refund_amount, 0)), 0) AS total_refunded
        FROM booking
        """
    ).fetchone()

    review_row = conn.execute(
        """
        SELECT AVG(CASE WHEN hidden = 0 THEN rating END) AS avg_rating,
               COUNT(*) AS total_reviews,
               COALESCE(SUM(CASE WHEN moderation_status = 'pending' THEN 1 ELSE 0 END), 0) AS pending_moderation_count,
               COALESCE(SUM(CASE WHEN report_count > 0 THEN 1 ELSE 0 END), 0) AS reported_reviews_count,
               COALESCE(SUM(CASE WHEN hidden = 1 THEN 1 ELSE 0 END), 0) AS hidden_reviews_count
        FROM review
        """
    ).fetchone()

    total_bookings = _int(booking_row["total_bookings"])
    cancelled_bookings = _int(booking_row["cancelled_bookings"])
    cancellation_rate = round((cancelled_bookings / total_bookings) * 100, 1) if total_bookings > 0 else 0.0

    return {
        "total_users": _int(user_row["total_users"]),
        "customers_count": _int(user_row["customers_count"]),
        "owners_count": _int(user_row["owners_count"]),
        "admins_count": _int(user_row["admins_count"]),
        "suspended_users_count": _int(user_row["suspended_users_count"]),
        "unverified_users_count": _int(user_row["unverified_users_count"]),
        "total_venues": _int(venue_row["total_venues"]),
        "active_venues_count": _int(venue_row["active_venues_count"]),
        "inactive_venues_count": _int(venue_row["inactive_venues_count"]),
        "venues_with_zero_bookings": _int(zero_bookings_row["cnt"]),
        "total_bookings": total_bookings,
        "confirmed_bookings": _int(booking_row["confirmed_bookings"]),
        "completed_bookings": _int(booking_row["completed_bookings"]),
        "cancelled_bookings": cancelled_bookings,
        "cancellation_rate": cancellation_rate,
        "gross_revenue": _int(booking_row["gross_revenue"]),
        "net_revenue": _int(booking_row["net_revenue"]),
        "total_refunded": _int(booking_row["total_refunded"]),
        "avg_rating": _rounded_avg(review_row["avg_rating"]),
        "total_reviews": _int(review_row["total_reviews"]),
        "pending_moderation_count": _int(review_row["pending_moderation_count"]),
        "reported_reviews_count": _int(review_row["reported_reviews_count"]),
        "hidden_reviews_count": _int(review_row["hidden_reviews_count"]),
    }


def get_sport_breakdown(conn):
    """Return venue, booking, revenue, and rating breakdown for all 4 sports (BR9)."""
    venue_rows = conn.execute(
        """
        SELECT sport,
               COUNT(*) AS venue_count,
               COALESCE(SUM(CASE WHEN active = 1 THEN 1 ELSE 0 END), 0) AS active_venue_count
        FROM venue
        GROUP BY sport
        """
    ).fetchall()
    venue_by_sport = {r["sport"]: r for r in venue_rows}

    booking_rows = conn.execute(
        """
        SELECT v.sport,
               COUNT(b.id) AS booking_count,
               COALESCE(SUM(b.total_price - COALESCE(b.refund_amount, 0)), 0) AS net_revenue
        FROM booking b
        JOIN venue v ON v.id = b.venue_id
        GROUP BY v.sport
        """
    ).fetchall()
    booking_by_sport = {r["sport"]: r for r in booking_rows}

    review_rows = conn.execute(
        """
        SELECT v.sport,
               AVG(r.rating) AS avg_rating
        FROM review r
        JOIN booking b ON b.id = r.booking_id
        JOIN venue v ON v.id = b.venue_id
        WHERE r.hidden = 0
        GROUP BY v.sport
        """
    ).fetchall()
    rating_by_sport = {r["sport"]: _rounded_avg(r["avg_rating"]) for r in review_rows}

    total_net_revenue = sum(_int(r["net_revenue"]) for r in booking_rows)
    result = []
    for sport in venues.SPORTS:
        v_info = venue_by_sport.get(sport)
        b_info = booking_by_sport.get(sport)
        net_rev = _int(b_info["net_revenue"]) if b_info else 0
        share = round((net_rev / total_net_revenue) * 100, 1) if total_net_revenue > 0 else 0.0
        result.append({
            "sport": sport,
            "venue_count": _int(v_info["venue_count"]) if v_info else 0,
            "active_venue_count": _int(v_info["active_venue_count"]) if v_info else 0,
            "booking_count": _int(b_info["booking_count"]) if b_info else 0,
            "net_revenue": net_rev,
            "revenue_share_pct": share,
            "avg_rating": rating_by_sport.get(sport),
        })
    return result


def get_area_breakdown(conn):
    """Return venue, booking, and net revenue breakdown grouped by area."""
    venue_rows = conn.execute(
        """
        SELECT area, COUNT(*) AS venue_count
        FROM venue
        GROUP BY area
        """
    ).fetchall()
    booking_rows = conn.execute(
        """
        SELECT v.area,
               COUNT(b.id) AS booking_count,
               COALESCE(SUM(b.total_price - COALESCE(b.refund_amount, 0)), 0) AS net_revenue
        FROM booking b
        JOIN venue v ON v.id = b.venue_id
        GROUP BY v.area
        """
    ).fetchall()
    booking_by_area = {r["area"]: r for r in booking_rows}

    areas = []
    for v_row in venue_rows:
        area = v_row["area"]
        b_info = booking_by_area.get(area)
        areas.append({
            "area": area,
            "venue_count": _int(v_row["venue_count"]),
            "booking_count": _int(b_info["booking_count"]) if b_info else 0,
            "net_revenue": _int(b_info["net_revenue"]) if b_info else 0,
        })
    areas.sort(key=lambda item: (-item["booking_count"], -item["venue_count"], item["area"]))
    return areas


def get_venue_analytics(conn, sport=None, area=None, q=None):
    """Return per-venue operational and financial analytics with optional filters."""
    sql = """
        SELECT v.id, v.name, v.sport, v.area, v.active, v.hourly_price,
               u.full_name AS owner_name, u.email AS owner_email
        FROM venue v
        JOIN user u ON u.id = v.owner_id
        WHERE 1 = 1
    """
    params = []
    if sport:
        sql += " AND v.sport = ?"
        params.append(sport)
    if area:
        sql += " AND v.area = ?"
        params.append(area)
    sql += " ORDER BY v.id ASC"

    venue_rows = conn.execute(sql, tuple(params)).fetchall()
    query = venues._fold_search_text(q.strip() if isinstance(q, str) else "")
    if query:
        venue_rows = [
            r for r in venue_rows
            if query in venues._fold_search_text(
                f"{r['name']} {r['sport']} {r['area']} {r['owner_name']} {r['owner_email']}"
            )
        ]

    booking_stats = {
        r["venue_id"]: r
        for r in conn.execute(
            """
            SELECT venue_id,
                   COUNT(*) AS total_bookings,
                   COALESCE(SUM(CASE WHEN status = 'confirmed' THEN 1 ELSE 0 END), 0) AS confirmed_count,
                   COALESCE(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END), 0) AS completed_count,
                   COALESCE(SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END), 0) AS cancelled_count,
                   COALESCE(SUM(total_price - COALESCE(refund_amount, 0)), 0) AS net_revenue
            FROM booking
            GROUP BY venue_id
            """
        ).fetchall()
    }

    hours_stats = {
        r["venue_id"]: _int(r["total_hours"])
        for r in conn.execute(
            """
            SELECT venue_id, COUNT(*) AS total_hours
            FROM booking_slot
            GROUP BY venue_id
            """
        ).fetchall()
    }

    review_stats = {
        r["venue_id"]: r
        for r in conn.execute(
            """
            SELECT b.venue_id,
                   AVG(r.rating) AS avg_rating,
                   COUNT(r.id) AS review_count
            FROM review r
            JOIN booking b ON b.id = r.booking_id
            WHERE r.hidden = 0
            GROUP BY b.venue_id
            """
        ).fetchall()
    }

    analytics = []
    for v in venue_rows:
        vid = v["id"]
        b = booking_stats.get(vid)
        rev = review_stats.get(vid)
        analytics.append({
            "id": vid,
            "name": v["name"],
            "sport": v["sport"],
            "area": v["area"],
            "owner_name": v["owner_name"],
            "owner_email": v["owner_email"],
            "active": bool(v["active"]),
            "hourly_price": _int(v["hourly_price"]),
            "total_bookings": _int(b["total_bookings"]) if b else 0,
            "confirmed_count": _int(b["confirmed_count"]) if b else 0,
            "completed_count": _int(b["completed_count"]) if b else 0,
            "cancelled_count": _int(b["cancelled_count"]) if b else 0,
            "total_hours": hours_stats.get(vid, 0),
            "net_revenue": _int(b["net_revenue"]) if b else 0,
            "avg_rating": _rounded_avg(rev["avg_rating"]) if rev else None,
            "review_count": _int(rev["review_count"]) if rev else 0,
        })
    return analytics


def list_users(conn, role=None, status=None, q=None):
    """Return user accounts with venue_count and booking_count, optionally filtered."""
    sql = """
        SELECT u.id, u.email, u.full_name, u.phone, u.role, u.email_verified_at,
               u.suspended, u.suspended_at, u.suspended_reason, u.created_at,
               (SELECT COUNT(*) FROM venue v WHERE v.owner_id = u.id) AS venue_count,
               (SELECT COUNT(*) FROM booking b WHERE b.customer_id = u.id) AS booking_count
        FROM user u
        WHERE 1 = 1
    """
    params = []
    if role in VALID_ROLES:
        sql += " AND u.role = ?"
        params.append(role)
    if status == "active":
        sql += " AND u.suspended = 0 AND u.email_verified_at IS NOT NULL"
    elif status == "suspended":
        sql += " AND u.suspended = 1"
    elif status == "unverified":
        sql += " AND u.suspended = 0 AND u.email_verified_at IS NULL"
    sql += " ORDER BY u.id ASC"

    rows = conn.execute(sql, tuple(params)).fetchall()
    query = venues._fold_search_text(q.strip() if isinstance(q, str) else "")
    if query:
        rows = [
            r for r in rows
            if query in venues._fold_search_text(f"{r['full_name']} {r['email']} {r['phone']}")
        ]

    return [
        {
            "id": r["id"],
            "email": r["email"],
            "full_name": r["full_name"],
            "phone": r["phone"],
            "role": r["role"],
            "email_verified_at": r["email_verified_at"],
            "suspended": bool(r["suspended"]),
            "suspended_at": r["suspended_at"],
            "suspended_reason": r["suspended_reason"],
            "created_at": r["created_at"],
            "venue_count": _int(r["venue_count"]),
            "booking_count": _int(r["booking_count"]),
        }
        for r in rows
    ]


def create_user_account(conn, email, password, full_name, phone, role, auto_verify=True, now=None):
    """Create a user account of any valid role with BR1, BR2, BR3, and BR7 validation."""
    email = _as_str(email, "email").strip().casefold()
    full_name = _as_str(full_name, "full_name").strip()
    phone = _as_str(phone, "phone").strip()
    role = _as_str(role, "role").strip()
    password = _as_str(password, "password")

    if role not in VALID_ROLES:
        raise BusinessRuleError(400, "Invalid account role. Choose customer, owner, or admin.", "BR7", "role")

    problems = auth.check_registration(conn, email, password, full_name, phone)
    if problems:
        raise problems[0]

    verified_at = (now or vn_now()).strftime(TIME_FORMAT) if auto_verify else None
    try:
        cur = conn.execute(
            """
            INSERT INTO user (email, password_hash, full_name, phone, role, email_verified_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (email, generate_password_hash(password), full_name, phone, role, verified_at),
        )
    except Exception as exc:
        if isinstance(exc, sqlite3.IntegrityError) or "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
            auth.raise_user_unique_conflict(conn, phone, exc)
        raise
    conn.commit()
    return cur.lastrowid


def suspend_user(conn, target_user_id, actor_user_id, reason=""):
    """Suspend a user account (BR14). Prevents self-suspension."""
    if int(target_user_id) == int(actor_user_id):
        raise BusinessRuleError(400, "You cannot suspend your own account", "BR14")

    user = conn.execute("SELECT id FROM user WHERE id = ?", (target_user_id,)).fetchone()
    if user is None:
        raise BusinessRuleError(404, "User not found")

    now_str = vn_now().strftime(TIME_FORMAT)
    clean_reason = _as_str(reason, "reason").strip() or "Suspended by administrator"
    conn.execute(
        """
        UPDATE user
        SET suspended = 1, suspended_at = ?, suspended_reason = ?
        WHERE id = ?
        """,
        (now_str, clean_reason, target_user_id),
    )
    conn.commit()


def unsuspend_user(conn, target_user_id):
    """Restore a suspended user account."""
    user = conn.execute("SELECT id FROM user WHERE id = ?", (target_user_id,)).fetchone()
    if user is None:
        raise BusinessRuleError(404, "User not found")

    conn.execute(
        """
        UPDATE user
        SET suspended = 0, suspended_at = NULL, suspended_reason = NULL
        WHERE id = ?
        """,
        (target_user_id,),
    )
    conn.commit()


def toggle_venue_active(conn, venue_id):
    """Toggle a venue's active status (1 -> 0 or 0 -> 1) and return the new boolean state."""
    venue = conn.execute("SELECT id, active FROM venue WHERE id = ?", (venue_id,)).fetchone()
    if venue is None:
        raise BusinessRuleError(404, "Venue not found")

    new_active = 0 if venue["active"] else 1
    conn.execute("UPDATE venue SET active = ? WHERE id = ?", (new_active, venue_id))
    conn.commit()
    return bool(new_active)


def list_moderation_reviews(conn, mod_status=None):
    """List reviews that have been reported, hidden, or moderated."""
    sql = """
        SELECT r.id, r.booking_id, r.rating, r.comment, r.report_count, r.hidden,
               r.moderation_status, r.moderated_at, r.moderated_by, r.created_at,
               b.code AS booking_code,
               v.id AS venue_id, v.name AS venue_name,
               u.full_name AS author_name, u.email AS author_email
        FROM review r
        JOIN booking b ON b.id = r.booking_id
        JOIN venue v ON v.id = b.venue_id
        JOIN user u ON u.id = b.customer_id
        WHERE (r.report_count > 0 OR r.hidden = 1 OR r.moderation_status IN ('pending', 'approved', 'rejected'))
    """
    params = []
    if mod_status == "reported":
        sql += " AND r.report_count > 0"
    elif mod_status in VALID_MOD_STATUSES:
        sql += " AND r.moderation_status = ?"
        params.append(mod_status)
    sql += " ORDER BY CASE WHEN r.moderation_status = 'pending' THEN 0 ELSE 1 END, r.report_count DESC, r.created_at DESC"

    rows = conn.execute(sql, tuple(params)).fetchall()
    return [
        {
            "id": r["id"],
            "booking_id": r["booking_id"],
            "booking_code": r["booking_code"],
            "venue_id": r["venue_id"],
            "venue_name": r["venue_name"],
            "author_name": r["author_name"],
            "author_email": r["author_email"],
            "rating": r["rating"],
            "comment": r["comment"],
            "report_count": _int(r["report_count"]),
            "hidden": bool(r["hidden"]),
            "moderation_status": r["moderation_status"],
            "moderated_at": r["moderated_at"],
            "moderated_by": r["moderated_by"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def moderate_review(conn, review_id, admin_user_id, action):
    """Approve (unhide & clear reports) or reject (keep hidden) a flagged review (BR19)."""
    action = _as_str(action, "action").strip().lower()
    if action not in ("approve", "reject"):
        raise BusinessRuleError(400, "Moderation action must be 'approve' or 'reject'")

    rev = conn.execute("SELECT id FROM review WHERE id = ?", (review_id,)).fetchone()
    if rev is None:
        raise BusinessRuleError(404, "Review not found")

    now_str = vn_now().strftime(TIME_FORMAT)
    if action == "approve":
        conn.execute(
            """
            UPDATE review
            SET hidden = 0, report_count = 0, moderation_status = 'approved',
                moderated_at = ?, moderated_by = ?
            WHERE id = ?
            """,
            (now_str, admin_user_id, review_id),
        )
    else:
        conn.execute(
            """
            UPDATE review
            SET hidden = 1, moderation_status = 'rejected',
                moderated_at = ?, moderated_by = ?
            WHERE id = ?
            """,
            (now_str, admin_user_id, review_id),
        )
    conn.commit()
