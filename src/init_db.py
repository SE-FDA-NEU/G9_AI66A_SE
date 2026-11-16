"""Create data/venues.db from src/schema.py and seed it.

Run from the repository root:  python src/init_db.py
Running it again drops every table and starts from the same seed - safe to repeat.
"""
import csv
from datetime import date, timedelta

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

from db import ROOT, connect, database_path
from hanoi_popular_venues import get_venue_coords
from schema import SCHEMA

load_dotenv()

# Seed accounts. Password for every one of them: sanbong1 (8 characters, letter + digit, BR2).
USERS = [
    ("lan.owner@example.com",  "Nguyen Thi Lan",  "0912345678", "owner",    True),
    ("hung.owner@example.com", "Tran Van Hung",   "0987654321", "owner",    True),
    ("son.owner@example.com",  "Le Hoang Son",    "0934567890", "owner",    True),
    ("minh@example.com",       "Pham Duc Minh",   "0901234567", "customer", True),
    ("trang@example.com",      "Do Thu Trang",    "0976543210", "customer", True),
    ("nam@example.com",        "Hoang Van Nam",   "0911223344", "customer", True),
    ("linh@example.com",       "Vu Thuy Linh",    "0922334455", "customer", False),
    ("admin@example.com",      "Admin",           "0900000000", "admin",    True),
]

# (venue name, weekday 0=Mon, start_hour, end_hour, price) - peak evenings, BR12
PRICING = [
    ("Thong Nhat Football Pitch",  1, 17, 20, 450000),
    ("Thong Nhat Football Pitch",  3, 17, 20, 450000),
    ("Lan Anh Badminton Court", 1, 17, 20, 120000),
    ("My Dinh Football Pitch",     5, 7, 11, 500000),
]

# Booking dates are counted from the day the script runs, so on any machine and any day
# the seeded bookings are in the future and the availability grid shows booked hours.
TODAY = date.today()


def next_weekday(weekday):
    """The first date after today that falls on `weekday` (0 = Monday)."""
    return TODAY + timedelta(days=(weekday - TODAY.weekday() - 1) % 7 + 1)


TUESDAY = next_weekday(1).isoformat()          # Thong Nhat has a peak rule on Tuesdays
SATURDAY = next_weekday(5).isoformat()         # My Dinh has a peak rule on Saturday mornings
WEDNESDAY = (next_weekday(1) + timedelta(days=1)).isoformat()

# (venue name, slot start) - maintenance, BR16
BLOCKS = [
    ("Thong Nhat Football Pitch", f"{WEDNESDAY} 06:00"),
    ("Thong Nhat Football Pitch", f"{WEDNESDAY} 07:00"),
]

# (code, customer email, venue name, date, start_hour, hours, status, refund_amount, cancelled_at)
# On TUESDAY, Thong Nhat has 3 of its 16 hours booked: 13 free + 3 booked (US04 criterion 2).
BOOKINGS = [
    ("BK-000101", "minh@example.com",  "Thong Nhat Football Pitch",   (TODAY - timedelta(days=30)).isoformat(), 18, 2, "completed", None, None),
    ("BK-000102", "trang@example.com", "Lan Anh Badminton Court",     (TODAY - timedelta(days=29)).isoformat(), 19, 1, "completed", None, None),
    ("BK-000103", "minh@example.com",  "Thong Nhat Football Pitch",   TUESDAY, 19, 2, "confirmed", None, None),
    ("BK-000104", "trang@example.com", "Chua Boc Badminton Court",    (TODAY + timedelta(days=2)).isoformat(), 20, 1, "confirmed", None, None),
    ("BK-000105", "minh@example.com",  "My Dinh Football Pitch",      SATURDAY, 8, 2, "confirmed", None, None),
    ("BK-000106", "trang@example.com", "Thong Nhat Football Pitch",   TUESDAY, 17, 1, "confirmed", None, None),
    ("BK-000107", "nam@example.com",   "Bach Khoa Tennis Court",      (TODAY - timedelta(days=20)).isoformat(), 16, 2, "completed", None, None),
    ("BK-000108", "trang@example.com", "Times City Pickleball Court", (TODAY - timedelta(days=14)).isoformat(), 18, 2, "completed", None, None),
    ("BK-000109", "nam@example.com",   "Royal City Tennis Court",     (TODAY - timedelta(days=5)).isoformat(), 16, 2, "cancelled", 500000, f"{(TODAY - timedelta(days=6)).isoformat()} 10:00:00"),
    ("BK-000110", "minh@example.com",  "Ha Dong Football Pitch",      (TODAY - timedelta(days=3)).isoformat(), 18, 1, "cancelled", 125000, f"{(TODAY - timedelta(days=3)).isoformat()} 09:00:00"),
]

# (booking_code, rating, comment, report_count, hidden, moderation_status)
REVIEWS = [
    ("BK-000101", 5, "New turf, bright lights, friendly owner.", 0, 0, "active"),
    ("BK-000107", 2, "Court surface was wet and staff were unhelpful.", 3, 1, "pending"),
    ("BK-000108", 4, "Good paddle court, slightly noisy on weekends.", 2, 0, "active"),
]


def seed(conn):
    conn.executescript(SCHEMA)
    pw = generate_password_hash("sanbong1")
    for email, name, phone, role, verified in USERS:
        if verified:
            conn.execute(
                "INSERT INTO user (email, password_hash, full_name, phone, role, email_verified_at)"
                " VALUES (?, ?, ?, ?, ?, datetime('now'))",
                (email, pw, name, phone, role),
            )
        else:
            conn.execute(
                "INSERT INTO user (email, password_hash, full_name, phone, role, email_verified_at)"
                " VALUES (?, ?, ?, ?, ?, NULL)",
                (email, pw, name, phone, role),
            )
    user_id = {r["email"]: r["id"] for r in conn.execute("SELECT id, email FROM user")}

    with open(ROOT / "data" / "venues.csv", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            lat, lng = get_venue_coords(row["area"])
            conn.execute(
                "INSERT INTO venue (owner_id, name, sport, area, address, hourly_price,"
                " open_hour, close_hour, latitude, longitude) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id[row["owner_email"]], row["name"], row["sport"], row["area"],
                 row["address"], int(row["hourly_price"]), int(row["open_hour"]),
                 int(row["close_hour"]), lat, lng),
            )
    venue = {r["name"]: (r["id"], r["hourly_price"])
             for r in conn.execute("SELECT id, name, hourly_price FROM venue")}

    for name, weekday, start, end, price in PRICING:
        conn.execute(
            "INSERT INTO pricing_rule (venue_id, weekday, start_hour, end_hour, price_per_hour)"
            " VALUES (?, ?, ?, ?, ?)", (venue[name][0], weekday, start, end, price))

    for name, slot in BLOCKS:
        conn.execute("INSERT INTO blocked_slot (venue_id, slot_start) VALUES (?, ?)",
                     (venue[name][0], slot))

    for code, email, name, day, start, hours, status, refund_amount, cancelled_at in BOOKINGS:
        vid, standard = venue[name]
        weekday = date.fromisoformat(day).weekday()
        # BR12: each hour is priced on its own - peak if a rule covers it, standard otherwise
        prices = [next((p for n, w, s, e, p in PRICING if n == name and w == weekday and s <= h < e),
                       standard) for h in range(start, start + hours)]
        cur = conn.execute(
            "INSERT INTO booking (code, customer_id, venue_id, start_at, end_at, total_price, status, refund_amount, cancelled_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (code, user_id[email], vid, f"{day} {start:02d}:00", f"{day} {start + hours:02d}:00",
             sum(prices), status, refund_amount, cancelled_at))
        if status != "cancelled":
            for h, price in zip(range(start, start + hours), prices):
                conn.execute(
                    "INSERT INTO booking_slot (booking_id, venue_id, slot_start, price) VALUES (?, ?, ?, ?)",
                    (cur.lastrowid, vid, f"{day} {h:02d}:00", price))

    for code, rating, comment, report_count, hidden, mod_status in REVIEWS:
        bid = conn.execute("SELECT id FROM booking WHERE code = ?", (code,)).fetchone()["id"]
        conn.execute(
            "INSERT INTO review (booking_id, rating, comment, report_count, hidden, moderation_status)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (bid, rating, comment, report_count, hidden, mod_status),
        )
    conn.commit()


TABLES = ["user", "venue", "venue_photo", "pricing_rule", "blocked_slot", "booking", "booking_slot", "review"]


def main():
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as conn:
        seed(conn)
        print(f"Created {path.relative_to(ROOT)}")
        for t in TABLES:
            n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"  {t:<13} {n:>3} rows")


if __name__ == "__main__":
    main()
