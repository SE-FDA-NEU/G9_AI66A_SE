"""Venues: search (US03), venue detail and availability for one date (US04), and an owner
adding a venue (US06).

Sport and area come from the fixed lists below, never from typed text (BR9), so
"Cau Giay", "cau giay" and "Q. Cau Giay" can never become three different areas.
"""
import re
import uuid
import unicodedata
from datetime import date, datetime, timedelta

import storage
from errors import BusinessRuleError
from time_utils import vn_now

SPORTS = ["Football", "Badminton", "Tennis", "Pickleball"]          # same list as the CHECK in schema.py

# The 12 urban districts of Hanoi (BR9). Adding a district changes this list, not the schema.
AREAS = ["Ba Dinh", "Bac Tu Liem", "Cau Giay", "Dong Da", "Ha Dong", "Hai Ba Trung",
         "Hoan Kiem", "Hoang Mai", "Long Bien", "Nam Tu Liem", "Tay Ho", "Thanh Xuan"]

NO_MATCH = "No venues found"                                         # BR9

# BR9: sport AND area must both match; an empty filter means "any".
# Text search is applied after the fixed sport/area filters so it can consistently search
# venue name, sport, area, and address, including Vietnamese text without diacritics.
SEARCH_SQL = """
SELECT v.id, v.name, v.sport, v.area, v.address, v.hourly_price, v.open_hour, v.close_hour,
       (SELECT p.id FROM venue_photo p WHERE p.venue_id = v.id ORDER BY p.id LIMIT 1) AS cover_photo_id,
       ROUND(AVG(CASE WHEN r.hidden = 0 THEN r.rating END), 1) AS avg_rating,
       COUNT(CASE WHEN r.hidden = 0 THEN r.id END) AS review_count
FROM venue v
LEFT JOIN booking b ON b.venue_id = v.id
LEFT JOIN review r ON r.booking_id = b.id
WHERE v.active = 1
  AND (:sport = '' OR v.sport = :sport)
  AND (:area  = '' OR v.area  = :area)
GROUP BY v.id, v.name, v.sport, v.area, v.address, v.hourly_price, v.open_hour, v.close_hour
ORDER BY v.area, v.sport, v.name
"""

SORT_OPTIONS = {"", "default", "price_asc", "price_desc", "rating_desc", "name_asc"}


def _fold_search_text(value):
    decomposed = unicodedata.normalize("NFD", str(value)).casefold()
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def _parse_price_filter(value, field):
    if value is None or str(value).strip() == "":
        return None
    parsed = parse_price(str(value).strip())
    if parsed is None or parsed < 0:
        raise BusinessRuleError(400, "Price filter must be a valid non-negative number", None, field)
    return parsed


def _parse_hour_filter(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        hour_int = int(str(value).strip())
    except (TypeError, ValueError):
        raise BusinessRuleError(400, "Hour must be between 0 and 23", None, "hour") from None
    if not 0 <= hour_int <= 23:
        raise BusinessRuleError(400, "Hour must be between 0 and 23", None, "hour")
    return hour_int


def _sort_key(sort):
    if sort == "price_asc":
        return lambda v: (v["hourly_price"], v["area"], v["name"])
    if sort == "price_desc":
        return lambda v: (-v["hourly_price"], v["area"], v["name"])
    if sort == "rating_desc":
        return lambda v: (-(v["avg_rating"] or 0), -v["review_count"], v["hourly_price"], v["name"])
    if sort == "name_asc":
        return lambda v: (v["name"].lower(), v["area"])
    return lambda v: (v["area"], v["sport"], v["name"])


def search(conn, sport="", area="", q="", sort="", min_price="", max_price="", date="", hour="", now=None):
    """Return the matching venues. An unknown sport or area is refused, not ignored (BR9)."""
    if sport and sport not in SPORTS:
        raise BusinessRuleError(400, "Please choose a sport from the list", "BR9", "sport")
    if area and area not in AREAS:
        raise BusinessRuleError(400, "Please choose an area from the list", "BR9", "area")
    if sort not in SORT_OPTIONS:
        raise BusinessRuleError(400, "Please choose a valid sort option", None, "sort")

    min_p = _parse_price_filter(min_price, "min_price")
    max_p = _parse_price_filter(max_price, "max_price")
    if min_p is not None and max_p is not None and min_p > max_p:
        raise BusinessRuleError(400, "Minimum price cannot exceed maximum price", None, "min_price")

    now_dt = now or vn_now()
    date_str = str(date).strip() if date is not None else ""
    target_day = parse_day(date_str, now_dt) if date_str else now_dt.date()
    hour_int = _parse_hour_filter(hour)

    rows = conn.execute(SEARCH_SQL, {"sport": sport, "area": area}).fetchall()
    day_iso = target_day.isoformat()
    booked_set = {
        (r[0], r[1])
        for r in conn.execute(
            "SELECT venue_id, slot_start FROM booking_slot WHERE date(slot_start) = ?",
            (day_iso,),
        )
    }
    blocked_set = {
        (r[0], r[1])
        for r in conn.execute(
            "SELECT venue_id, slot_start FROM blocked_slot WHERE date(slot_start) = ?",
            (day_iso,),
        )
    }

    query = _fold_search_text(q.strip())
    results = []
    for row in rows:
        v = dict(row)
        if query and query not in _fold_search_text(
            f"{v['name']} {v['sport']} {v['area']} {v['address']}"
        ):
            continue
        if min_p is not None and v["hourly_price"] < min_p:
            continue
        if max_p is not None and v["hourly_price"] > max_p:
            continue

        free_count = 0
        for h in range(v["open_hour"], v["close_hour"]):
            key = f"{day_iso} {h:02d}:00"
            if (
                (v["id"], key) not in booked_set
                and (v["id"], key) not in blocked_set
                and datetime(target_day.year, target_day.month, target_day.day, h) > now_dt
            ):
                free_count += 1
        v["free_slots_count"] = free_count

        if hour_int is not None:
            if not (v["open_hour"] <= hour_int < v["close_hour"]):
                continue
            hour_key = f"{day_iso} {hour_int:02d}:00"
            if (
                (v["id"], hour_key) in booked_set
                or (v["id"], hour_key) in blocked_set
                or datetime(target_day.year, target_day.month, target_day.day, hour_int) <= now_dt
            ):
                continue

        results.append(v)

    results.sort(key=_sort_key(sort))
    return results


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


def day_slots(conn, venue, day, now=None):
    """Every 1-hour slot of exactly `day` (BR10), each one free, booked, blocked or past.

    A slot is booked when a booking_slot row holds it - cancelled bookings have none (BR15) -
    and blocked when the owner closed it (BR16). An hour that has already started is past.
    """
    now = now or vn_now()
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
    s = (text or "").strip()
    if not re.fullmatch(r"-?(?:\d+|\d{1,3}(?:,\d{3})+|\d{1,3}(?:\.\d{3})+|\d{1,3}(?: \d{3})+)", s):
        return None
    return int(s.replace(",", "").replace(".", "").replace(" ", ""))


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
    """Store an uploaded photo under a random name - never the name the browser sent.

    Uses Cloudinary when CLOUDINARY_URL is configured, otherwise the local upload dir.
    """
    file_name = storage.save_photo(upload_dir, photo, venue_id)
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
    now = now or vn_now()
    if conn.in_transaction:
        conn.commit()
    conn.execute("BEGIN IMMEDIATE")
    try:
        venue = check_venue_owner(conn, venue_id, owner["id"])
        if not (venue["open_hour"] <= hour < venue["close_hour"]):
            raise BusinessRuleError(
                400,
                f"Hour must be within opening hours ({venue['open_hour']:02d}:00 - {venue['close_hour']:02d}:00)",
                "BR13",
            )
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
    except BaseException:
        conn.rollback()
        raise
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
    now = now or vn_now()
    if conn.in_transaction:
        conn.commit()
    conn.execute("BEGIN IMMEDIATE")
    try:
        venue = check_venue_owner(conn, venue_id, owner["id"])
        if start_day > end_day:
            raise BusinessRuleError(400, "Start date must be on or before end date", "BR13")
        if not (venue["open_hour"] <= start_hour < end_hour <= venue["close_hour"]):
            raise BusinessRuleError(
                400,
                f"Time range must be within opening hours ({venue['open_hour']:02d}:00 - {venue['close_hour']:02d}:00)",
                "BR13",
            )

        blocked_count = 0
        skipped = []
        cur_day = start_day
        while cur_day <= end_day:
            future_slots = []
            has_booking = False
            for hour in range(start_hour, end_hour):
                slot_dt = datetime(cur_day.year, cur_day.month, cur_day.day, hour)
                if slot_dt <= now:
                    continue
                slot_start = f"{cur_day.isoformat()} {hour:02d}:00"
                booked = conn.execute(
                    """
                    SELECT b.code FROM booking_slot bs
                    JOIN booking b ON b.id = bs.booking_id
                    WHERE bs.venue_id = ? AND bs.slot_start = ?
                    """, (venue_id, slot_start)).fetchone()
                if booked:
                    has_booking = True
                    break
                future_slots.append(slot_start)

            if has_booking:
                skipped.append(f"{cur_day.strftime('%d/%m/%Y')} {start_hour:02d}:00-{end_hour:02d}:00")
            else:
                for slot_start in future_slots:
                    conn.execute(
                        "INSERT OR REPLACE INTO blocked_slot (venue_id, slot_start, reason) VALUES (?, ?, ?)",
                        (venue_id, slot_start, reason or "Under maintenance"))
                    blocked_count += 1
            cur_day += timedelta(days=1)
    except BaseException:
        conn.rollback()
        raise
    conn.commit()
    return blocked_count, skipped

