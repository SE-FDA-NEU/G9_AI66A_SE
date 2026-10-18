"""Venues: search (US03), venue detail and availability for one date (US04), and an owner
adding a venue (US06).

Sport and area come from the fixed lists below, never from typed text (BR9), so
"Cau Giay", "cau giay" and "Q. Cau Giay" can never become three different areas.
"""
import uuid
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


PHOTO_TYPES = {".jpg", ".jpeg", ".png"}


def parse_price(text):
    """'250,000' or '250000' -> 250000. None when it is not a whole number."""
    cleaned = text.replace(",", "").replace(".", "").replace(" ", "")
    try:
        return int(cleaned)
    except ValueError:
        return None


def read_hour(text, default):
    try:
        return int(text)
    except (TypeError, ValueError):
        return default


def check_new_venue(form, photo_name=""):
    """Return (values, problems): the cleaned values, and one BusinessRuleError per broken rule."""
    values = {k: (form.get(k) or "").strip() for k in ("name", "sport", "area", "address")}
    values["hourly_price"] = parse_price(form.get("hourly_price") or "")
    values["open_hour"] = read_hour(form.get("open_hour"), 6)
    values["close_hour"] = read_hour(form.get("close_hour"), 22)
    problems = []
    if not values["name"]:
        problems.append(BusinessRuleError(422, "Please enter the venue name", "BR13", "name"))
    elif not 3 <= len(values["name"]) <= 100:
        problems.append(BusinessRuleError(422, "Venue name must be 3 to 100 characters", "BR13", "name"))
    if values["sport"] not in SPORTS:
        problems.append(BusinessRuleError(422, "Please choose a sport from the list", "BR9", "sport"))
    if values["area"] not in AREAS:
        problems.append(BusinessRuleError(422, "Please choose an area from the list", "BR9", "area"))
    if not values["address"]:
        problems.append(BusinessRuleError(422, "Please enter the address", None, "address"))
    price = values["hourly_price"]
    if price is None:
        problems.append(BusinessRuleError(
            422, "Hourly price must be a whole number of VND, for example 250,000", "BR13", "hourly_price"))
    elif price < 1000:
        problems.append(BusinessRuleError(422, "Hourly price must be at least 1,000 VND", "BR13", "hourly_price"))
    elif price > 100_000_000:
        problems.append(BusinessRuleError(422, "Hourly price must be at most 100,000,000 VND", "BR13", "hourly_price"))
    if not 0 <= values["open_hour"] < values["close_hour"] <= 24:
        problems.append(BusinessRuleError(422, "Opening time must be before closing time", None, "close_hour"))
    if photo_name and not any(photo_name.lower().endswith(ext) for ext in PHOTO_TYPES):
        problems.append(BusinessRuleError(422, "The photo must be a JPG or PNG file", None, "photo"))
    return values, problems


def create_venue(conn, owner, values):
    """Insert a venue owned by `owner` (BR14). `values` must have passed check_new_venue()."""
    cur = conn.execute(
        "INSERT INTO venue (owner_id, name, sport, area, address, hourly_price, open_hour, close_hour)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (owner["id"], values["name"], values["sport"], values["area"], values["address"],
         values["hourly_price"], values["open_hour"], values["close_hour"]))
    conn.commit()
    return cur.lastrowid


def save_photo(conn, upload_dir, venue_id, photo):
    """Store an uploaded photo under a random name - never the name the browser sent."""
    extension = "." + photo.filename.rsplit(".", 1)[-1].lower()
    file_name = f"venue{venue_id}-{uuid.uuid4().hex}{extension}"
    upload_dir.mkdir(parents=True, exist_ok=True)
    photo.save(upload_dir / file_name)
    conn.execute("INSERT INTO venue_photo (venue_id, file_name) VALUES (?, ?)", (venue_id, file_name))
    conn.commit()


def owner_venues(conn, owner):
    """Only the venues of this owner (BR14), newest first."""
    return conn.execute(
        "SELECT v.*, (SELECT COUNT(*) FROM venue_photo p WHERE p.venue_id = v.id) AS photo_count"
        " FROM venue v WHERE v.owner_id = ? ORDER BY v.id DESC", (owner["id"],)).fetchall()
