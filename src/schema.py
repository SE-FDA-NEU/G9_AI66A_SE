"""Database schema (SQLite DDL).

Kept in a .py file, not schema.sql: the CI job "No .env or database dumps" rejects any
committed *.sql file. Every CHECK / UNIQUE names the business rule from
docs/requirements.md that it enforces.
"""

SCHEMA = """

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS review;
DROP TABLE IF EXISTS booking_slot;
DROP TABLE IF EXISTS booking;
DROP TABLE IF EXISTS blocked_slot;
DROP TABLE IF EXISTS pricing_rule;
DROP TABLE IF EXISTS venue;
DROP TABLE IF EXISTS user;

CREATE TABLE user (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    email               TEXT    NOT NULL UNIQUE COLLATE NOCASE,              -- BR1
    password_hash       TEXT    NOT NULL,                                    -- BR2 checked before hashing
    full_name           TEXT    NOT NULL,
    phone               TEXT    NOT NULL
                        CHECK (length(phone) = 10 AND substr(phone, 1, 1) = '0'
                               AND phone NOT GLOB '*[^0-9]*'),               -- BR3
    role                TEXT    NOT NULL DEFAULT 'customer'
                        CHECK (role IN ('customer', 'owner', 'admin')),      -- BR7
    email_verified_at   TEXT,                                                -- BR4: NULL = cannot book
    failed_login_count  INTEGER NOT NULL DEFAULT 0 CHECK (failed_login_count >= 0), -- BR5
    locked_until        TEXT,                                                -- BR5
    created_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE venue (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id      INTEGER NOT NULL REFERENCES user(id),                      -- BR14
    name          TEXT    NOT NULL CHECK (length(name) BETWEEN 3 AND 100),   -- BR13
    sport         TEXT    NOT NULL
                  CHECK (sport IN ('Football', 'Badminton', 'Tennis', 'Pickleball')), -- BR9
    area          TEXT    NOT NULL,                                          -- BR9
    address       TEXT    NOT NULL,
    hourly_price  INTEGER NOT NULL CHECK (hourly_price BETWEEN 1000 AND 100000000), -- BR12, BR13
    open_hour     INTEGER NOT NULL CHECK (open_hour BETWEEN 0 AND 23),
    close_hour    INTEGER NOT NULL CHECK (close_hour BETWEEN 1 AND 24),
    active        INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    CHECK (open_hour < close_hour)
);

CREATE TABLE pricing_rule (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    venue_id        INTEGER NOT NULL REFERENCES venue(id),
    weekday         INTEGER NOT NULL CHECK (weekday BETWEEN 0 AND 6),        -- 0 = Monday
    start_hour      INTEGER NOT NULL CHECK (start_hour BETWEEN 0 AND 23),
    end_hour        INTEGER NOT NULL CHECK (end_hour BETWEEN 1 AND 24),
    price_per_hour  INTEGER NOT NULL CHECK (price_per_hour BETWEEN 1000 AND 100000000), -- BR12
    CHECK (start_hour < end_hour)                                            -- BR12 half-open [start, end)
    -- "rules must not overlap on the same venue and weekday" (BR12) is checked in
    -- src/pricing.py: SQLite cannot express an exclusion constraint on ranges.
);

CREATE TABLE blocked_slot (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    venue_id    INTEGER NOT NULL REFERENCES venue(id),
    slot_start  TEXT    NOT NULL,                                            -- 'YYYY-MM-DD HH:00'
    reason      TEXT    NOT NULL DEFAULT 'Under maintenance',                -- BR16
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (venue_id, slot_start)
);

CREATE TABLE booking (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    code           TEXT    NOT NULL UNIQUE,                                  -- e.g. BK-000148
    customer_id    INTEGER NOT NULL REFERENCES user(id),                     -- BR14
    venue_id       INTEGER NOT NULL REFERENCES venue(id),
    start_at       TEXT    NOT NULL,
    end_at         TEXT    NOT NULL,
    total_price    INTEGER NOT NULL CHECK (total_price >= 0),                -- BR12: frozen at confirm time
    status         TEXT    NOT NULL DEFAULT 'confirmed'
                   CHECK (status IN ('confirmed', 'cancelled', 'completed')),
    refund_amount  INTEGER CHECK (refund_amount IS NULL OR refund_amount >= 0), -- BR15
    created_at     TEXT    NOT NULL DEFAULT (datetime('now')),
    cancelled_at   TEXT,
    CHECK (end_at > start_at)
);

-- One row per booked hour. UNIQUE (venue_id, slot_start) is what makes a double booking
-- impossible at the database level (BR11). Cancelling a booking deletes its rows, which
-- releases the hours to other customers (BR15). price keeps the per-segment price (BR12).
CREATE TABLE booking_slot (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id  INTEGER NOT NULL REFERENCES booking(id) ON DELETE CASCADE,
    venue_id    INTEGER NOT NULL REFERENCES venue(id),
    slot_start  TEXT    NOT NULL,                                            -- 'YYYY-MM-DD HH:00'
    price       INTEGER NOT NULL CHECK (price >= 0),
    UNIQUE (venue_id, slot_start)                                            -- BR11
);

CREATE TABLE review (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id    INTEGER NOT NULL UNIQUE REFERENCES booking(id),            -- BR18 one per booking
    rating        INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),           -- BR18
    comment       TEXT    CHECK (comment IS NULL OR length(comment) <= 1000),-- BR18
    report_count  INTEGER NOT NULL DEFAULT 0 CHECK (report_count >= 0),      -- BR19
    hidden        INTEGER NOT NULL DEFAULT 0 CHECK (hidden IN (0, 1)),       -- BR19
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_venue_sport_area ON venue (sport, area);                    -- BR9 search
CREATE INDEX idx_booking_customer ON booking (customer_id);
"""
