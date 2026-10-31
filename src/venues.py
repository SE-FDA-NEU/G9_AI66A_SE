"""Venues: search (US03), venue detail and availability for one date (US04), and an owner
adding a venue (US06).

Sport and area come from the fixed lists below, never from typed text (BR9), so
"Cau Giay", "cau giay" and "Q. Cau Giay" can never become three different areas.
"""
import uuid
from datetime import date, datetime, timedelta

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


def check_venue_owner(conn, venue_id, owner_id):
    """Ensure venue exists and belongs to owner (BR14, BR18). Returns venue or raises."""
    venue = conn.execute("SELECT * FROM venue WHERE id = ?", (venue_id,)).fetchone()
    if venue is None:
        raise BusinessRuleError(404, "Venue not found")
    if venue["owner_id"] != owner_id:
        raise BusinessRuleError(403, "You do not have permission to access this venue")
    return venue


def owner_bookings(conn, owner, date_str, venue_id=None):
    """Bookings for an owner on a specific date (US23, BR16, BR17, BR18)."""
    sql = """
    SELECT b.id, b.code, b.start_at, b.end_at, b.total_price, b.status,
           v.id AS venue_id, v.name AS venue_name,
           u.full_name AS customer_name, u.phone AS customer_phone
    FROM booking b
    JOIN venue v ON v.id = b.venue_id
    JOIN user u ON u.id = b.customer_id
    WHERE v.owner_id = ?
      AND date(b.start_at) = ?
    """
    params = [owner["id"], date_str]
    if venue_id:
        sql += " AND v.id = ?"
        params.append(venue_id)
    sql += " ORDER BY b.start_at ASC"
    return conn.execute(sql, tuple(params)).fetchall()


def owner_booking_detail(conn, owner, code):
    """View one booking for owner; 403 if it belongs to another owner (US23 AC 6, BR18)."""
    row = conn.execute(
        """
        SELECT b.id, b.code, b.start_at, b.end_at, b.total_price, b.status,
               b.refund_amount, b.created_at, b.cancelled_at,
               v.id AS venue_id, v.name AS venue_name, v.address, v.sport, v.owner_id,
               u.full_name AS customer_name, u.phone AS customer_phone, u.email AS customer_email
        FROM booking b
        JOIN venue v ON v.id = b.venue_id
        JOIN user u ON u.id = b.customer_id
        WHERE b.code = ?
        """, (code,)).fetchone()
    if row is None:
        raise BusinessRuleError(404, "Booking not found")
    if row["owner_id"] != owner["id"]:
        raise BusinessRuleError(403, "You do not have permission to view this booking")
    return row


def venue_schedule_slots(conn, venue, day, now):
    """All 1-hour slots for an owner schedule view (US22).
    Includes active booking codes and maintenance reasons."""
    slots_map = {}
    for hour in range(venue["open_hour"], venue["close_hour"]):
        key = f"{day.isoformat()} {hour:02d}:00"
        slots_map[key] = {
            "hour": hour,
            "start": f"{hour:02d}:00",
            "end": f"{hour + 1:02d}:00",
            "slot_start": key,
            "status": "free",
            "booking_code": None,
            "reason": None,
        }
        if datetime(day.year, day.month, day.day, hour) <= now:
            slots_map[key]["status"] = "past"

    # Overlay bookings
    booking_rows = conn.execute(
        """
        SELECT bs.slot_start, b.code, b.status
        FROM booking_slot bs
        JOIN booking b ON b.id = bs.booking_id
        WHERE bs.venue_id = ? AND date(bs.slot_start) = ?
        """, (venue["id"], day.isoformat())).fetchall()
    for r in booking_rows:
        key = r["slot_start"]
        if key in slots_map:
            slots_map[key]["status"] = "booked"
            slots_map[key]["booking_code"] = r["code"]

    # Overlay blocked slots
    blocked_rows = conn.execute(
        "SELECT slot_start, reason FROM blocked_slot WHERE venue_id = ? AND date(slot_start) = ?",
        (venue["id"], day.isoformat())).fetchall()
    for r in blocked_rows:
        key = r["slot_start"]
        if key in slots_map:
            slots_map[key]["status"] = "blocked"
            slots_map[key]["reason"] = r["reason"]

    return list(slots_map.values())


def block_single_slot(conn, owner, venue_id, slot_day, hour, reason="Under maintenance", now=None):
    """Block one slot for maintenance (US22, BR13, BR14, BR15)."""
    now = now or datetime.now()
    venue = check_venue_owner(conn, venue_id, owner["id"])
    slot_start = f"{slot_day.isoformat()} {hour:02d}:00"

    # BR15: Only allow blocking slots starting after current time
    slot_dt = datetime(slot_day.year, slot_day.month, slot_day.day, hour)
    if slot_dt <= now:
        raise BusinessRuleError(400, "Can only block slots starting after current time", "BR15")

    # BR14: Cannot block slot with active uncancelled booking
    booked = conn.execute(
        """
        SELECT b.code FROM booking_slot bs
        JOIN booking b ON b.id = bs.booking_id
        WHERE bs.venue_id = ? AND bs.slot_start = ?
        """, (venue_id, slot_start)).fetchone()
    if booked:
        raise BusinessRuleError(
            409,
            f"Cannot block: this slot is already booked ({booked['code']}). Cancel booking first.",
            "BR14")

    conn.execute(
        "INSERT OR REPLACE INTO blocked_slot (venue_id, slot_start, reason) VALUES (?, ?, ?)",
        (venue_id, slot_start, reason or "Under maintenance"))
    conn.commit()


def unblock_single_slot(conn, owner, venue_id, slot_day, hour):
    """Unblock a previously blocked slot (US22, BR13). Takes effect immediately."""
    check_venue_owner(conn, venue_id, owner["id"])
    slot_start = f"{slot_day.isoformat()} {hour:02d}:00"
    conn.execute(
        "DELETE FROM blocked_slot WHERE venue_id = ? AND slot_start = ?",
        (venue_id, slot_start))
    conn.commit()


def batch_block_slots(conn, owner, venue_id, start_day, end_day, start_hour, end_hour, reason="Under maintenance", now=None):
    """Batch block date range & hours (US22 AC 5). Returns (blocked_count, skipped_messages)."""
    now = now or datetime.now()
    check_venue_owner(conn, venue_id, owner["id"])
    blocked_count = 0
    skipped = []

    cur_day = start_day
    while cur_day <= end_day:
        for hour in range(start_hour, end_hour):
            slot_start = f"{cur_day.isoformat()} {hour:02d}:00"
            slot_dt = datetime(cur_day.year, cur_day.month, cur_day.day, hour)
            if slot_dt <= now:
                continue

            booked = conn.execute(
                """
                SELECT b.code FROM booking_slot bs
                JOIN booking b ON b.id = bs.booking_id
                WHERE bs.venue_id = ? AND bs.slot_start = ?
                """, (venue_id, slot_start)).fetchone()
            if booked:
                skipped.append(f"{cur_day.strftime('%d/%m/%Y')} {start_hour:02d}:00-{end_hour:02d}:00")
                break
            else:
                conn.execute(
                    "INSERT OR REPLACE INTO blocked_slot (venue_id, slot_start, reason) VALUES (?, ?, ?)",
                    (venue_id, slot_start, reason or "Under maintenance"))
                blocked_count += 1
        cur_day += timedelta(days=1)
    conn.commit()
    return blocked_count, skipped

