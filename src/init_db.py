"""Create data/venues.db from src/schema.py and seed it.

Run from the repository root:  python src/init_db.py
Running it again drops every table and starts from the same seed - safe to repeat.
"""
import csv
from datetime import date

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

from db import ROOT, connect, database_path
from schema import SCHEMA

load_dotenv()

# Seed accounts. Password for every one of them: sanbong1 (8 characters, letter + digit, BR2).
USERS = [
    ("lan.owner@example.com",  "Nguyen Thi Lan",  "0912345678", "owner"),
    ("hung.owner@example.com", "Tran Van Hung",   "0987654321", "owner"),
    ("son.owner@example.com",  "Le Hoang Son",    "0934567890", "owner"),
    ("minh@example.com",       "Pham Duc Minh",   "0901234567", "customer"),
    ("trang@example.com",      "Do Thu Trang",    "0976543210", "customer"),
    ("admin@example.com",      "Admin",           "0900000000", "admin"),
]

# (venue name, weekday 0=Mon, start_hour, end_hour, price) - peak evenings, BR12
PRICING = [
    ("Thong Nhat Football Pitch",  1, 17, 20, 450000),
    ("Thong Nhat Football Pitch",  3, 17, 20, 450000),
    ("Lan Anh Badminton Court", 1, 17, 20, 120000),
    ("My Dinh Football Pitch",     5, 7, 11, 500000),
]

# (venue name, slot start) - maintenance, BR16
BLOCKS = [
    ("Thong Nhat Football Pitch", "2026-10-06 06:00"),
    ("Thong Nhat Football Pitch", "2026-10-06 07:00"),
]

# (code, customer email, venue name, date, start_hour, hours, status)
BOOKINGS = [
    ("BK-000101", "minh@example.com",  "Thong Nhat Football Pitch",   "2026-09-24", 18, 2, "completed"),
    ("BK-000102", "trang@example.com", "Lan Anh Badminton Court",  "2026-09-25", 19, 1, "completed"),
    ("BK-000103", "minh@example.com",  "Thong Nhat Football Pitch",   "2026-10-06", 19, 2, "confirmed"),
    ("BK-000104", "trang@example.com", "Chua Boc Badminton Court", "2026-10-07", 20, 1, "confirmed"),
    ("BK-000105", "minh@example.com",  "My Dinh Football Pitch",      "2026-10-10", 8,  2, "confirmed"),
]

REVIEWS = [("BK-000101", 5, "New turf, bright lights, friendly owner.")]


def seed(conn):
    conn.executescript(SCHEMA)
    pw = generate_password_hash("sanbong1")
    for email, name, phone, role in USERS:
        conn.execute(
            "INSERT INTO user (email, password_hash, full_name, phone, role, email_verified_at)"
            " VALUES (?, ?, ?, ?, ?, datetime('now'))",
            (email, pw, name, phone, role),
        )
    user_id = {r["email"]: r["id"] for r in conn.execute("SELECT id, email FROM user")}

    with open(ROOT / "data" / "venues.csv", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            conn.execute(
                "INSERT INTO venue (owner_id, name, sport, area, address, hourly_price,"
                " open_hour, close_hour) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id[row["owner_email"]], row["name"], row["sport"], row["area"],
                 row["address"], int(row["hourly_price"]), int(row["open_hour"]),
                 int(row["close_hour"])),
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

    for code, email, name, day, start, hours, status in BOOKINGS:
        vid, standard = venue[name]
        weekday = date.fromisoformat(day).weekday()
        # BR12: each hour is priced on its own - peak if a rule covers it, standard otherwise
        prices = [next((p for n, w, s, e, p in PRICING if n == name and w == weekday and s <= h < e),
                       standard) for h in range(start, start + hours)]
        cur = conn.execute(
            "INSERT INTO booking (code, customer_id, venue_id, start_at, end_at, total_price, status)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (code, user_id[email], vid, f"{day} {start:02d}:00", f"{day} {start + hours:02d}:00",
             sum(prices), status))
        for h, price in zip(range(start, start + hours), prices):
            conn.execute(
                "INSERT INTO booking_slot (booking_id, venue_id, slot_start, price) VALUES (?, ?, ?, ?)",
                (cur.lastrowid, vid, f"{day} {h:02d}:00", price))

    for code, rating, comment in REVIEWS:
        bid = conn.execute("SELECT id FROM booking WHERE code = ?", (code,)).fetchone()["id"]
        conn.execute("INSERT INTO review (booking_id, rating, comment) VALUES (?, ?, ?)",
                     (bid, rating, comment))
    conn.commit()


TABLES = ["user", "venue", "pricing_rule", "blocked_slot", "booking", "booking_slot", "review"]


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
