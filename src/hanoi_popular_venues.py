"""Real Hanoi sports venues catalog and district coordinate helpers.

Provides district centroid coordinates (`AREA_COORDS`), 22 real high-traffic
Hanoi sports venues (`POPULAR_HANOI_VENUES`), coordinate fallback helpers, and
an idempotent sync function (`sync_popular_venues`) for both SQLite and Postgres.
"""

AREA_COORDS = {
    "Ba Dinh": (21.0338, 105.8142),
    "Bac Tu Liem": (21.0715, 105.7634),
    "Cau Giay": (21.0362, 105.7906),
    "Dong Da": (21.0181, 105.8292),
    "Ha Dong": (20.9718, 105.7772),
    "Hai Ba Trung": (21.0091, 105.8548),
    "Hoan Kiem": (21.0285, 105.8542),
    "Hoang Mai": (20.9756, 105.8549),
    "Long Bien": (21.0451, 105.8902),
    "Nam Tu Liem": (21.0169, 105.7544),
    "Tay Ho": (21.0695, 105.8240),
    "Thanh Xuan": (20.9937, 105.8058),
}

DEFAULT_HANOI_COORDS = (21.0285, 105.8542)

# (name, sport, area, address, hourly_price, open_hour, close_hour, latitude, longitude)
POPULAR_HANOI_VENUES = [
    # Football (7) — varied early-morning & late-night hours
    ("San Bong C500 (Hoc vien An Ninh)", "Football", "Ha Dong", "125 Tran Phu, Van Quan, Ha Dong", 350000, 5, 23, 20.9806, 105.7885),
    ("Cum San Bong Phong Khong - Khong Quan", "Football", "Thanh Xuan", "3 Le Trong Tan, Khuong Mai, Thanh Xuan", 400000, 6, 24, 20.9998, 105.8293),
    ("San Bong Dai hoc Thuy Loi", "Football", "Dong Da", "Ngo 165 Chua Boc, Trung Liet, Dong Da", 350000, 7, 22, 21.0076, 105.8247),
    ("Cum San Bong Son Trang", "Football", "Cau Giay", "1 Hoang Minh Giam, Trung Hoa, Cau Giay", 420000, 6, 24, 21.0038, 105.7995),
    ("San Bong Thanh Lam Green Park", "Football", "Cau Giay", "8 Duong Dinh Nghe, Yen Hoa, Cau Giay", 380000, 7, 23, 21.0235, 105.7897),
    ("San Bong Trinh Cong Son", "Football", "Tay Ho", "Duong Trinh Cong Son, Nhat Tan, Tay Ho", 350000, 5, 22, 21.0748, 105.8214),
    ("San Bong Xuan La", "Football", "Tay Ho", "101 Xuan La, Xuan Tao, Tay Ho", 320000, 6, 21, 21.0668, 105.8029),
    # Badminton (6)
    ("San Cau Long Quan Thanh", "Badminton", "Ba Dinh", "115 Quan Thanh, Quan Thanh, Ba Dinh", 100000, 5, 22, 21.0413, 105.8406),
    ("San Cau Long Duy Hung", "Badminton", "Ba Dinh", "120 Doc Ngu, Lieu Giai, Ba Dinh", 90000, 6, 23, 21.0398, 105.8147),
    ("Nha Thi Dau Cau Giay", "Badminton", "Cau Giay", "35 Tran Quy Kien, Dich Vong, Cau Giay", 110000, 7, 22, 21.0387, 105.7924),
    ("San Cau Long Dai hoc Su Pham Ha Noi", "Badminton", "Cau Giay", "136 Xuan Thuy, Dich Vong Hau, Cau Giay", 85000, 7, 21, 21.0369, 105.7829),
    ("San Cau Long Tien Dinh Sport", "Badminton", "Hai Ba Trung", "488 Minh Khai, Vinh Tuy, Hai Ba Trung", 100000, 6, 24, 20.9964, 105.8698),
    ("San Cau Long HK Sport Chuong Duong", "Badminton", "Hoan Kiem", "Ngo 46 Chuong Duong Do, Chuong Duong, Hoan Kiem", 110000, 8, 22, 21.0289, 105.8594),
    # Tennis (5)
    ("San Tennis Quan Hoa", "Tennis", "Cau Giay", "20 Ngo 165 Cau Giay, Quan Hoa, Cau Giay", 220000, 6, 21, 21.0342, 105.7991),
    ("Cum San Tennis Ciputra (FLTA Vietnam)", "Tennis", "Tay Ho", "Khu do thi Ciputra, Phu Thuong, Tay Ho", 300000, 7, 22, 21.0785, 105.8022),
    ("San Tennis Phong Khong - Khong Quan", "Tennis", "Thanh Xuan", "3 Le Trong Tan, Khuong Mai, Thanh Xuan", 250000, 5, 22, 20.9994, 105.8289),
    ("San Tennis Bach Khoa", "Tennis", "Hai Ba Trung", "Ngo 42 Ta Quang Buu, Bach Khoa, Hai Ba Trung", 240000, 7, 21, 21.0031, 105.8473),
    ("San Tennis Thap Ha Noi (Hanoi Towers)", "Tennis", "Hoan Kiem", "49 Hai Ba Trung, Tran Hung Dao, Hoan Kiem", 350000, 8, 22, 21.0247, 105.8466),
    # Pickleball (4)
    ("San Pickleball Bach Khoa", "Pickleball", "Hai Ba Trung", "42 Ta Quang Buu, Bach Khoa, Hai Ba Trung", 180000, 7, 23, 21.0033, 105.8476),
    ("San Pickleball SportsHub My Dinh", "Pickleball", "Nam Tu Liem", "40 Pham Hung, My Dinh 2, Nam Tu Liem", 200000, 6, 24, 21.0282, 105.7785),
    ("San Pickleball Lang Viet Kieu Chau Au", "Pickleball", "Ha Dong", "KDT Lang Viet Kieu Chau Au, Mo Lao, Ha Dong", 170000, 8, 23, 20.9854, 105.7834),
    ("Hoang Chop Pickleball Trung Van", "Pickleball", "Nam Tu Liem", "Chung cu Bac Ha C14 Trung Van, Nam Tu Liem", 180000, 7, 24, 20.9968, 105.7929),
]

_POPULAR_BY_NAME = {
    row[0]: row for row in POPULAR_HANOI_VENUES
}
_POPULAR_COORDS_BY_NAME = {
    row[0]: (row[7], row[8]) for row in POPULAR_HANOI_VENUES
}


def get_venue_coords(area, latitude=None, longitude=None):
    """Return (lat, lng) for a venue, falling back to its district centroid."""
    if latitude is not None and longitude is not None:
        return (float(latitude), float(longitude))
    return AREA_COORDS.get(area, DEFAULT_HANOI_COORDS)


def _resolve_owner_id(conn, owner_id=None):
    if owner_id is not None:
        return owner_id
    row = conn.execute(
        'SELECT id FROM "user" WHERE role = \'owner\' ORDER BY id LIMIT 1'
    ).fetchone()
    if row is None:
        row = conn.execute('SELECT id FROM "user" ORDER BY id LIMIT 1').fetchone()
    return row[0] if row is not None else None


def sync_popular_venues(conn, owner_id=None):
    """Idempotently insert missing popular Hanoi venues and backfill NULL coordinates."""
    resolved_owner_id = _resolve_owner_id(conn, owner_id=owner_id)
    existing_rows = conn.execute(
        "SELECT id, name, area, latitude, longitude FROM venue"
    ).fetchall()
    existing_names = {r[1] for r in existing_rows}

    inserted = 0
    updated = 0

    if resolved_owner_id is not None:
        for name, sport, area, address, price, open_hour, close_hour, lat, lng in POPULAR_HANOI_VENUES:
            if name in existing_names:
                continue
            conn.execute(
                "INSERT INTO venue (owner_id, name, sport, area, address, hourly_price, "
                "open_hour, close_hour, latitude, longitude) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (resolved_owner_id, name, sport, area, address, price, open_hour, close_hour, lat, lng),
            )
            existing_names.add(name)
            inserted += 1

    for row in existing_rows:
        vid, name, area, lat, lng = row[0], row[1], row[2], row[3], row[4]
        pop = _POPULAR_BY_NAME.get(name)
        if pop is not None:
            conn.execute(
                "UPDATE venue SET open_hour = ?, close_hour = ? WHERE id = ?",
                (pop[5], pop[6], vid),
            )
        if lat is None or lng is None:
            fallback_lat, fallback_lng = _POPULAR_COORDS_BY_NAME.get(
                name, get_venue_coords(area)
            )
            conn.execute(
                "UPDATE venue SET latitude = ?, longitude = ? WHERE id = ?",
                (fallback_lat, fallback_lng, vid),
            )
            updated += 1

    # Seed realistic peak/off-peak pricing rules for popular venues with no rules yet
    popular_rows = conn.execute(
        "SELECT id, name, hourly_price, open_hour, close_hour FROM venue"
    ).fetchall()
    for vrow in popular_rows:
        vid, vname, base_price, open_h, close_h = vrow[0], vrow[1], vrow[2], vrow[3], vrow[4]
        if vname not in _POPULAR_BY_NAME:
            continue
        has_rules = conn.execute(
            "SELECT 1 FROM pricing_rule WHERE venue_id = ? LIMIT 1", (vid,)
        ).fetchone()
        if has_rules is not None:
            continue
        peak_price = int(round((base_price * 1.3) / 1000.0) * 1000)
        weekend_peak = int(round((base_price * 1.4) / 1000.0) * 1000)
        offpeak_price = max(1000, int(round((base_price * 0.85) / 1000.0) * 1000))
        peak_end = min(21, close_h)
        for wd in range(7):
            if open_h < 9:
                conn.execute(
                    "INSERT INTO pricing_rule (venue_id, weekday, start_hour, end_hour, price_per_hour) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (vid, wd, open_h, 9, offpeak_price),
                )
            if 17 < peak_end:
                conn.execute(
                    "INSERT INTO pricing_rule (venue_id, weekday, start_hour, end_hour, price_per_hour) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (vid, wd, 17, peak_end, weekend_peak if wd >= 5 else peak_price),
                )
        updated += 1

    if inserted or updated:
        conn.commit()
    return {"inserted": inserted, "updated": updated}
