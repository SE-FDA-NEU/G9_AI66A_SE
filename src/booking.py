"""Booking a venue (US05, issue #68): check, quote, confirm, read back.

Every rule is checked here, not in the routes: BR4 (verified email), BR11 (1-4 whole
hours inside opening hours, one booking per hour, re-checked right before confirming),
BR12 (per-segment price, frozen at confirm time), BR14 (own bookings only) and BR16
(blocked hours cannot be booked).
"""
import sqlite3
from datetime import date, datetime, timedelta

from errors import BusinessRuleError
from pricing import hour_prices, segments

MAX_HOURS = 4            # BR11
SEARCH_AHEAD_DAYS = 30   # how far nearest_free_day() looks

SLOT_TAKEN = "This time slot is no longer available"


def slot_key(day, hour):
    """booking_slot.slot_start / blocked_slot.slot_start format: 'YYYY-MM-DD HH:00'."""
    return f"{day.isoformat()} {hour:02d}:00"


def _day(value):
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise BusinessRuleError("BR11", "Choose a valid date", 400)


def get_venue(conn, venue_id):
    venue = conn.execute("SELECT * FROM venue WHERE id = ? AND active = 1", (venue_id,)).fetchone()
    if venue is None:
        raise BusinessRuleError("BR11", "Venue not found", 404)
    return venue


def taken_hours(conn, venue_id, day):
    """Hours of that day held by a booking (BR11) or blocked by the owner (BR16)."""
    prefix = day.isoformat() + " %"
    rows = conn.execute(
        "SELECT slot_start FROM booking_slot WHERE venue_id = ? AND slot_start LIKE ?"
        " UNION SELECT slot_start FROM blocked_slot WHERE venue_id = ? AND slot_start LIKE ?",
        (venue_id, prefix, venue_id, prefix))
    return {int(r[0][11:13]) for r in rows}


def free_hours(conn, venue, day, now=None):
    """Start hours still bookable on that day: open, not taken, not blocked, not past."""
    now = now or datetime.now()
    taken = taken_hours(conn, venue["id"], day)
    return [h for h in range(venue["open_hour"], venue["close_hour"])
            if h not in taken and datetime(day.year, day.month, day.day, h) > now]


def nearest_free_day(conn, venue, day, now=None):
    """The first day after `day` with at least one free hour, or None within 30 days."""
    for i in range(1, SEARCH_AHEAD_DAYS + 1):
        candidate = day + timedelta(days=i)
        if free_hours(conn, venue, candidate, now):
            return candidate
    return None


def check_request(conn, user, venue_id, day, start_hour, hours, now=None):
    """Validate a booking request; return (venue, day, start_hour, hours) or raise."""
    now = now or datetime.now()
    if user["role"] != "customer":
        raise BusinessRuleError("BR14", "Only customer accounts can book a venue", 403)
    if user["email_verified_at"] is None:
        raise BusinessRuleError("BR4", "Please verify your email before booking", 403)
    venue = get_venue(conn, venue_id)
    day = _day(day)
    try:
        start_hour, hours = int(start_hour), int(hours)
    except (TypeError, ValueError):
        raise BusinessRuleError("BR11", "Choose a start time and a number of hours", 400)

    open_h, close_h = venue["open_hour"], venue["close_hour"]
    if not 1 <= hours <= MAX_HOURS:
        raise BusinessRuleError("BR11", "A booking is 1 to 4 consecutive hours")
    if not open_h <= start_hour < close_h:
        raise BusinessRuleError(
            "BR11", f"Start time must be between {open_h:02d}:00 and {close_h - 1:02d}:00")
    if start_hour + hours > close_h:
        raise BusinessRuleError(
            "BR11", f"The venue closes at {close_h:02d}:00 - from {start_hour:02d}:00 you can"
                    f" book at most {close_h - start_hour} hour(s)")
    if datetime(day.year, day.month, day.day, start_hour) <= now:
        raise BusinessRuleError("BR11", "This time slot has already started")

    wanted = [slot_key(day, h) for h in range(start_hour, start_hour + hours)]
    marks = ",".join("?" * len(wanted))
    if conn.execute(f"SELECT 1 FROM blocked_slot WHERE venue_id = ? AND slot_start IN ({marks})",
                    (venue["id"], *wanted)).fetchone():
        raise BusinessRuleError("BR16", "This time slot is closed for maintenance")
    if conn.execute(f"SELECT 1 FROM booking_slot WHERE venue_id = ? AND slot_start IN ({marks})",
                    (venue["id"], *wanted)).fetchone():
        raise BusinessRuleError("BR11", SLOT_TAKEN, 409)
    return venue, day, start_hour, hours


def quote(conn, venue_id, day, start_hour, hours):
    """Segments and total for a request that check_request() accepted (BR12)."""
    day = _day(day)
    segs = segments(hour_prices(conn, venue_id, day), start_hour, hours)
    return {"segments": segs, "total_price": sum(s["price"] for s in segs)}


def _next_code(conn):
    # Runs inside the BEGIN IMMEDIATE transaction, so no other writer can take the same code.
    last = conn.execute("SELECT MAX(CAST(substr(code, 4) AS INTEGER)) FROM booking").fetchone()[0]
    return f"BK-{(last or 0) + 1:06d}"


def create_booking(conn, user, venue_id, day, start_hour, hours, now=None):
    """Confirm a booking in one transaction; return {code, total_price, segments}.

    BR11 / ADR 2: BEGIN IMMEDIATE takes the write lock before the re-check, so two
    customers confirming the same hour are serialised; if a row still slips through,
    UNIQUE (venue_id, slot_start) on booking_slot refuses it and the customer sees
    "This time slot is no longer available". Either way exactly one booking exists.
    """
    if conn.in_transaction:
        conn.commit()
    conn.execute("BEGIN IMMEDIATE")
    try:
        venue, day, start_hour, hours = check_request(conn, user, venue_id, day, start_hour,
                                                      hours, now)
        q = quote(conn, venue["id"], day, start_hour, hours)
        code = _next_code(conn)
        end = datetime(day.year, day.month, day.day) + timedelta(hours=start_hour + hours)
        cur = conn.execute(
            "INSERT INTO booking (code, customer_id, venue_id, start_at, end_at, total_price)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (code, user["id"], venue["id"], slot_key(day, start_hour),
             end.strftime("%Y-%m-%d %H:%M"), q["total_price"]))
        prices = hour_prices(conn, venue["id"], day)
        for h in range(start_hour, start_hour + hours):
            conn.execute("INSERT INTO booking_slot (booking_id, venue_id, slot_start, price)"
                         " VALUES (?, ?, ?, ?)", (cur.lastrowid, venue["id"], slot_key(day, h),
                                                  prices[h]))
    except sqlite3.IntegrityError:
        conn.rollback()
        raise BusinessRuleError("BR11", SLOT_TAKEN, 409)
    except BaseException:
        conn.rollback()
        raise
    conn.commit()
    return {"code": code, **q}


def find_for_customer(conn, code, user):
    """One booking with its venue and price lines; only its own customer may read it (BR14)."""
    booking = conn.execute(
        "SELECT b.*, v.name AS venue_name, v.address, v.sport FROM booking b"
        " JOIN venue v ON v.id = b.venue_id WHERE b.code = ?", (code,)).fetchone()
    if booking is None:
        raise BusinessRuleError("BR14", "Booking not found", 404)
    if booking["customer_id"] != user["id"]:
        raise BusinessRuleError("BR14", "You do not have permission to view this booking", 403)
    # BR12: the prices stored at confirm time, never recalculated from today's rules
    rows = conn.execute("SELECT slot_start, price FROM booking_slot WHERE booking_id = ?"
                        " ORDER BY slot_start", (booking["id"],)).fetchall()
    first = int(booking["start_at"][11:13])
    segs = segments({int(r["slot_start"][11:13]): r["price"] for r in rows}, first, len(rows))
    return booking, segs


def upcoming(conn, user_id, now=None):
    """The customer's confirmed bookings that have not started yet, soonest first (BR14)."""
    now = now or datetime.now()
    return conn.execute(
        "SELECT b.code, b.start_at, b.end_at, b.total_price, v.name AS venue_name FROM booking b"
        " JOIN venue v ON v.id = b.venue_id WHERE b.customer_id = ? AND b.status = 'confirmed'"
        " AND b.start_at > ? ORDER BY b.start_at", (user_id, now.strftime("%Y-%m-%d %H:%M"))).fetchall()
