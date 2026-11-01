"""Seed a newly created venue-booking schema without touching other schemas."""
import csv
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

from db import ROOT


USERS = [
    ("lan.owner@example.com", "Nguyen Thi Lan", "0912345678", "owner"),
    ("hung.owner@example.com", "Tran Van Hung", "0987654321", "owner"),
    ("son.owner@example.com", "Le Hoang Son", "0934567890", "owner"),
    ("minh@example.com", "Pham Duc Minh", "0901234567", "customer"),
    ("trang@example.com", "Do Thu Trang", "0976543210", "customer"),
    ("admin@example.com", "Admin", "0900000000", "admin"),
]
PRICING = [
    ("Thong Nhat Football Pitch", 1, 17, 20, 450000),
    ("Thong Nhat Football Pitch", 3, 17, 20, 450000),
    ("Lan Anh Badminton Court", 1, 17, 20, 120000),
    ("My Dinh Football Pitch", 5, 7, 11, 500000),
]


def _next_weekday(weekday, today):
    return today + timedelta(days=(weekday - today.weekday() - 1) % 7 + 1)


def seed_postgres(conn):
    """Populate only when this app's isolated schema has no users yet."""
    if conn.execute('SELECT COUNT(*) FROM "user"').fetchone()[0]:
        return

    hashed = generate_password_hash("sanbong1")
    user_ids = {}
    for email, name, phone, role in USERS:
        cur = conn.execute(
            'INSERT INTO "user" (email, password_hash, full_name, phone, role, email_verified_at) '
            'VALUES (?, ?, ?, ?, ?, NOW())',
            (email, hashed, name, phone, role),
        )
        user_ids[email] = cur.lastrowid

    venues = {}
    with (ROOT / "data" / "venues.csv").open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            cur = conn.execute(
                "INSERT INTO venue (owner_id, name, sport, area, address, hourly_price, open_hour, close_hour) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (user_ids[row["owner_email"]], row["name"], row["sport"], row["area"], row["address"],
                 int(row["hourly_price"]), int(row["open_hour"]), int(row["close_hour"])),
            )
            venues[row["name"]] = (cur.lastrowid, int(row["hourly_price"]))

    for name, weekday, start, end, price in PRICING:
        conn.execute(
            "INSERT INTO pricing_rule (venue_id, weekday, start_hour, end_hour, price_per_hour) "
            "VALUES (?, ?, ?, ?, ?)", (venues[name][0], weekday, start, end, price),
        )

    today = date.today()
    tuesday = _next_weekday(1, today).isoformat()
    saturday = _next_weekday(5, today).isoformat()
    wednesday = (date.fromisoformat(tuesday) + timedelta(days=1)).isoformat()
    conn.execute(
        "INSERT INTO blocked_slot (venue_id, slot_start) VALUES (?, ?)",
        (venues["Thong Nhat Football Pitch"][0], f"{wednesday} 06:00"),
    )
    conn.execute(
        "INSERT INTO blocked_slot (venue_id, slot_start) VALUES (?, ?)",
        (venues["Thong Nhat Football Pitch"][0], f"{wednesday} 07:00"),
    )

    bookings = [
        ("BK-000101", "minh@example.com", "Thong Nhat Football Pitch", (today - timedelta(days=30)).isoformat(), 18, 2, "completed"),
        ("BK-000102", "trang@example.com", "Lan Anh Badminton Court", (today - timedelta(days=29)).isoformat(), 19, 1, "completed"),
        ("BK-000103", "minh@example.com", "Thong Nhat Football Pitch", tuesday, 19, 2, "confirmed"),
        ("BK-000104", "trang@example.com", "Chua Boc Badminton Court", (today + timedelta(days=2)).isoformat(), 20, 1, "confirmed"),
        ("BK-000105", "minh@example.com", "My Dinh Football Pitch", saturday, 8, 2, "confirmed"),
        ("BK-000106", "trang@example.com", "Thong Nhat Football Pitch", tuesday, 17, 1, "confirmed"),
    ]
    for code, email, venue_name, day, start, hours, status in bookings:
        venue_id, standard = venues[venue_name]
        weekday = date.fromisoformat(day).weekday()
        hourly_prices = [
            next((price for name, rule_day, lo, hi, price in PRICING
                  if name == venue_name and rule_day == weekday and lo <= hour < hi), standard)
            for hour in range(start, start + hours)
        ]
        cur = conn.execute(
            "INSERT INTO booking (code, customer_id, venue_id, start_at, end_at, total_price, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (code, user_ids[email], venue_id, f"{day} {start:02d}:00", f"{day} {start + hours:02d}:00",
             sum(hourly_prices), status),
        )
        for hour, price in zip(range(start, start + hours), hourly_prices):
            conn.execute(
                "INSERT INTO booking_slot (booking_id, venue_id, slot_start, price) VALUES (?, ?, ?, ?)",
                (cur.lastrowid, venue_id, f"{day} {hour:02d}:00", price),
            )

    review_booking = conn.execute("SELECT id FROM booking WHERE code = ?", ("BK-000101",)).fetchone()["id"]
    conn.execute(
        "INSERT INTO review (booking_id, rating, comment) VALUES (?, ?, ?)",
        (review_booking, 5, "New turf, bright lights, friendly owner."),
    )
