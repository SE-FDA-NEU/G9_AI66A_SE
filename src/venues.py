"""Venues: search (US03), venue detail and availability for one date (US04).
"""Venues: search (US03).

Sport and area come from the fixed lists below, never from typed text (BR9), so
"Cau Giay", "cau giay" and "Q. Cau Giay" can never become three different areas.
"""
from datetime import date, datetime

from errors import BusinessRuleError

SPORTS = ["Football", "Badminton", "Tennis", "Pickleball"]          # same list as the CHECK in schema.py

# The 12 urban districts of Hanoi (BR9). Adding a district changes this list, not the schema.
AREAS = ["Ba Dinh", "Bac Tu Liem", "Cau Giay", "Dong Da", "Ha Dong", "Hai Ba Trung",
         "Hoan Kiem", "Hoang Mai", "Long Bien", "Nam Tu Liem", "Tay Ho", "Thanh Xuan"]

NO_MATCH = "No venues found"                                         # BR9

# BR9: sport AND area must both match; an empty filter means "any".
# q narrows by name or sport (US03 criterion 3); parameters are bound, never pasted in.
SEARCH_SQL = """
SELECT v.id, v.name, v.sport, v.area, v.address, v.hourly_price, v.open_hour, v.close_hour
FROM venue v
WHERE v.active = 1
  AND (:sport = '' OR v.sport = :sport)
  AND (:area  = '' OR v.area  = :area)
  AND (:q = '' OR v.name LIKE '%' || :q || '%' OR v.sport LIKE '%' || :q || '%')
ORDER BY v.area, v.sport, v.name
"""


def search(conn, sport="", area="", q=""):
    """Return the matching venues. An unknown sport or area is refused, not ignored (BR9)."""
    if sport and sport not in SPORTS:
        raise BusinessRuleError(400, "Please choose a sport from the list", "BR9", "sport")
    if area and area not in AREAS:
        raise BusinessRuleError(400, "Please choose an area from the list", "BR9", "area")
    return conn.execute(SEARCH_SQL, {"sport": sport, "area": area, "q": q.strip()}).fetchall()


def get_venue(conn, venue_id):
    venue = conn.execute("SELECT * FROM venue WHERE id = ? AND active = 1", (venue_id,)).fetchone()
    if venue is None:
        raise BusinessRuleError(404, "Venue not found. It may have been removed - search again.")
    return venue


def photos(conn, venue_id):
    """Only this venue's photos, oldest first (US04 criterion 3)."""
    return conn.execute("SELECT id, file_name FROM venue_photo WHERE venue_id = ? ORDER BY id",
                        (venue_id,)).fetchall()


def parse_day(text, now):
    """Turn ?date=YYYY-MM-DD into a date. Today or later only."""
    try:
        day = date.fromisoformat(text)
    except ValueError:
        raise BusinessRuleError(400, "Please choose a date in the form YYYY-MM-DD, for example 2026-10-20.",
                                "BR10") from None
    if day < now.date():
        raise BusinessRuleError(400, "Please choose today or a later date.", "BR10")
    return day


def day_slots(conn, venue, day, now):
    """Every 1-hour slot of exactly `day` (BR10), each one free, booked, blocked or past.

    A slot is booked when a booking_slot row holds it - cancelled bookings have none (BR15) -
    and blocked when the owner closed it (BR16). An hour that has already started is past.
    """
    taken = {r[0] for r in conn.execute(
        "SELECT slot_start FROM booking_slot WHERE venue_id = ? AND date(slot_start) = ?",
        (venue["id"], day.isoformat()))}
    blocked = {r[0] for r in conn.execute(
        "SELECT slot_start FROM blocked_slot WHERE venue_id = ? AND date(slot_start) = ?",
        (venue["id"], day.isoformat()))}
    slots = []
    for hour in range(venue["open_hour"], venue["close_hour"]):
        key = f"{day.isoformat()} {hour:02d}:00"
        if key in taken:
            status = "booked"
        elif key in blocked:
            status = "blocked"
        elif datetime(day.year, day.month, day.day, hour) <= now:
            status = "past"
        else:
            status = "free"
        slots.append({"hour": hour, "start": f"{hour:02d}:00", "end": f"{hour + 1:02d}:00", "status": status})
    return slots
