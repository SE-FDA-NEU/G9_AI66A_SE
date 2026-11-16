"""Seed a newly created venue-booking schema without touching other schemas."""
import csv
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

from db import ROOT
from hanoi_popular_venues import get_venue_coords, sync_popular_venues

USERS = [
    ("lan.owner@example.com", "Nguyen Thi Lan", "0912345678", "owner", True),
    ("hung.owner@example.com", "Tran Van Hung", "0987654321", "owner", True),
    ("son.owner@example.com", "Le Hoang Son", "0934567890", "owner", True),
    ("minh@example.com", "Pham Duc Minh", "0901234567", "customer", True),
    ("trang@example.com", "Do Thu Trang", "0976543210", "customer", True),
    ("nam@example.com", "Hoang Van Nam", "0911223344", "customer", True),
    ("linh@example.com", "Vu Thuy Linh", "0922334455", "customer", False),
    ("admin@example.com", "Admin", "0900000000", "admin", True),
]
PRICING = [
    ("Thong Nhat Football Pitch", 1, 17, 20, 450000),
    ("Thong Nhat Football Pitch", 3, 17, 20, 450000),
    ("Lan Anh Badminton Court", 1, 17, 20, 120000),
    ("My Dinh Football Pitch", 5, 7, 11, 500000),
]


def _next_weekday(weekday, today):
    return today + timedelta(days=(weekday - today.weekday() - 1) % 7 + 1)


def sync_missing_venues_postgres(conn):
    """Idempotently insert any venues from data/venues.csv not yet present in Postgres."""
    owner_rows = conn.execute('SELECT id, email FROM "user"').fetchall()
    owner_ids = {r[1]: r[0] for r in owner_rows}
    if not owner_ids:
        return

    existing_names = {r[0] for r in conn.execute("SELECT name FROM venue").fetchall()}
    inserted = False
    with (ROOT / "data" / "venues.csv").open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            if row["name"] in existing_names:
                continue
            owner_id = owner_ids.get(row["owner_email"])
            if not owner_id:
                continue
            lat, lng = get_venue_coords(row["area"])
            conn.execute(
                "INSERT INTO venue (owner_id, name, sport, area, address, hourly_price, open_hour, close_hour, latitude, longitude) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    owner_id,
                    row["name"],
                    row["sport"],
                    row["area"],
                    row["address"],
                    int(row["hourly_price"]),
                    int(row["open_hour"]),
                    int(row["close_hour"]),
                    lat,
                    lng,
                ),
            )
            existing_names.add(row["name"])
            inserted = True
    if inserted:
        conn.commit()


def seed_postgres(conn):
    """Populate only when this app's isolated schema has no users yet."""
    if conn.execute('SELECT COUNT(*) FROM "user"').fetchone()[0]:
        sync_missing_venues_postgres(conn)
        sync_popular_venues(conn)
        return

    hashed = generate_password_hash("sanbong1")
    user_ids = {}
    for email, name, phone, role, verified in USERS:
        if verified:
            cur = conn.execute(
                'INSERT INTO "user" (email, password_hash, full_name, phone, role, email_verified_at) '
                'VALUES (?, ?, ?, ?, ?, NOW())',
                (email, hashed, name, phone, role),
            )
        else:
            cur = conn.execute(
                'INSERT INTO "user" (email, password_hash, full_name, phone, role, email_verified_at) '
                'VALUES (?, ?, ?, ?, ?, NULL)',
                (email, hashed, name, phone, role),
            )
        user_ids[email] = cur.lastrowid

    venues = {}
    with (ROOT / "data" / "venues.csv").open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            lat, lng = get_venue_coords(row["area"])
            cur = conn.execute(
                "INSERT INTO venue (owner_id, name, sport, area, address, hourly_price, open_hour, close_hour, latitude, longitude) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user_ids[row["owner_email"]], row["name"], row["sport"], row["area"], row["address"],
                 int(row["hourly_price"]), int(row["open_hour"]), int(row["close_hour"]), lat, lng),
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
        ("BK-000101", "minh@example.com", "Thong Nhat Football Pitch", (today - timedelta(days=30)).isoformat(), 18, 2, "completed", None, None),
        ("BK-000102", "trang@example.com", "Lan Anh Badminton Court", (today - timedelta(days=29)).isoformat(), 19, 1, "completed", None, None),
        ("BK-000103", "minh@example.com", "Thong Nhat Football Pitch", tuesday, 19, 2, "confirmed", None, None),
        ("BK-000104", "trang@example.com", "Chua Boc Badminton Court", (today + timedelta(days=2)).isoformat(), 20, 1, "confirmed", None, None),
        ("BK-000105", "minh@example.com", "My Dinh Football Pitch", saturday, 8, 2, "confirmed", None, None),
        ("BK-000106", "trang@example.com", "Thong Nhat Football Pitch", tuesday, 17, 1, "confirmed", None, None),
        ("BK-000107", "nam@example.com", "Bach Khoa Tennis Court", (today - timedelta(days=20)).isoformat(), 16, 2, "completed", None, None),
        ("BK-000108", "trang@example.com", "Times City Pickleball Court", (today - timedelta(days=14)).isoformat(), 18, 2, "completed", None, None),
        ("BK-000109", "nam@example.com", "Royal City Tennis Court", (today - timedelta(days=5)).isoformat(), 16, 2, "cancelled", 500000, f"{(today - timedelta(days=6)).isoformat()} 10:00:00"),
        ("BK-000110", "minh@example.com", "Ha Dong Football Pitch", (today - timedelta(days=3)).isoformat(), 18, 1, "cancelled", 125000, f"{(today - timedelta(days=3)).isoformat()} 09:00:00"),
    ]
    for code, email, venue_name, day, start, hours, status, refund_amount, cancelled_at in bookings:
        venue_id, standard = venues[venue_name]
        weekday = date.fromisoformat(day).weekday()
        hourly_prices = [
            next((price for name, rule_day, lo, hi, price in PRICING
                  if name == venue_name and rule_day == weekday and lo <= hour < hi), standard)
            for hour in range(start, start + hours)
        ]
        cur = conn.execute(
            "INSERT INTO booking (code, customer_id, venue_id, start_at, end_at, total_price, status, refund_amount, cancelled_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (code, user_ids[email], venue_id, f"{day} {start:02d}:00", f"{day} {start + hours:02d}:00",
             sum(hourly_prices), status, refund_amount, cancelled_at),
        )
        if status != "cancelled":
            for hour, price in zip(range(start, start + hours), hourly_prices):
                conn.execute(
                    "INSERT INTO booking_slot (booking_id, venue_id, slot_start, price) VALUES (?, ?, ?, ?)",
                    (cur.lastrowid, venue_id, f"{day} {hour:02d}:00", price),
                )

    reviews = [
        ("BK-000101", 5, "New turf, bright lights, friendly owner.", 0, 0, "active"),
        ("BK-000107", 2, "Court surface was wet and staff were unhelpful.", 3, 1, "pending"),
        ("BK-000108", 4, "Good paddle court, slightly noisy on weekends.", 2, 0, "active"),
    ]
    for code, rating, comment, report_count, hidden, mod_status in reviews:
        review_booking = conn.execute("SELECT id FROM booking WHERE code = ?", (code,)).fetchone()["id"]
        conn.execute(
            "INSERT INTO review (booking_id, rating, comment, report_count, hidden, moderation_status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (review_booking, rating, comment, report_count, hidden, mod_status),
        )
    sync_missing_venues_postgres(conn)
    sync_popular_venues(conn)
