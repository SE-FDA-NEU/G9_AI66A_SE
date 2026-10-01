"""The database itself refuses data that breaks a business rule."""
import sqlite3

import pytest

from db import connect


def count(db, table):
    with connect(db) as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_seed_row_counts(db):
    assert count(db, "venue") == 24
    assert count(db, "user") == 6
    assert count(db, "booking") == 5


def test_same_email_twice_is_rejected(db):
    # BR1 - case-insensitive
    with connect(db) as conn, pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO user (email, password_hash, full_name, phone)"
                     " VALUES ('MINH@example.com', 'x', 'Minh 2', '0912345678')")


def test_phone_must_be_ten_digits_starting_with_zero(db):
    # BR3
    with connect(db) as conn, pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO user (email, password_hash, full_name, phone)"
                     " VALUES ('new@example.com', 'x', 'New', '1912345678')")


def test_same_hour_cannot_be_booked_twice(db):
    # BR11 - BK-000103 already holds Thong Nhat Football Pitch (venue 1) at 19:00 on 06/10
    with connect(db) as conn, pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO booking_slot (booking_id, venue_id, slot_start, price)"
                     " VALUES (4, 1, '2026-10-06 19:00', 300000)")


@pytest.mark.parametrize("name, price", [("Sa", 250000), ("New Court", 0), ("New Court", 999)])
def test_venue_name_and_price_limits(db, name, price):
    # BR13
    with connect(db) as conn, pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO venue (owner_id, name, sport, area, address, hourly_price,"
                     " open_hour, close_hour) VALUES (1, ?, 'Football', 'Cau Giay', 'x', ?, 6, 22)",
                     (name, price))


def test_peak_hour_booking_is_priced_per_segment(db):
    # BR12 - BK-000103: Tuesday 19:00-21:00, peak 17-20 at 450,000 then standard 300,000
    with connect(db) as conn:
        total = conn.execute("SELECT total_price FROM booking WHERE code = 'BK-000103'").fetchone()[0]
        prices = [r[0] for r in conn.execute(
            "SELECT s.price FROM booking_slot s JOIN booking b ON b.id = s.booking_id"
            " WHERE b.code = 'BK-000103' ORDER BY s.slot_start")]
    assert prices == [450000, 300000]
    assert total == 750000


def test_rating_must_be_one_to_five(db):
    # BR18
    with connect(db) as conn, pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO review (booking_id, rating) VALUES (2, 6)")
