"""Postgres schema for Vercel deployment.

Idempotent DDL: every statement uses IF NOT EXISTS / DROP IF EXISTS where safe so the
application can run it on every cold start without destroying existing data.
"""

PG_SCHEMA = """
-- Idempotent extensions and cleanup
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
        CREATE TYPE user_role AS ENUM ('customer', 'owner', 'admin');
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'booking_status') THEN
        CREATE TYPE booking_status AS ENUM ('confirmed', 'cancelled', 'completed');
    END IF;
END$$;

CREATE TABLE IF NOT EXISTS "user" (
    id                  SERIAL PRIMARY KEY,
    email               TEXT    NOT NULL UNIQUE,
    password_hash       TEXT    NOT NULL,
    full_name           TEXT    NOT NULL,
    phone               TEXT    NOT NULL
                        CHECK (length(phone) = 10 AND substring(phone, 1, 1) = '0'
                               AND phone ~ '^[0-9]+$'),
    role                user_role NOT NULL DEFAULT 'customer',
    email_verified_at   TIMESTAMP,
    failed_login_count  INTEGER NOT NULL DEFAULT 0 CHECK (failed_login_count >= 0),
    locked_until        TIMESTAMP,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Case-insensitive email uniqueness (matches SQLite NOCASE).
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_email_lower ON "user" (lower(email));

CREATE TABLE IF NOT EXISTS venue (
    id            SERIAL PRIMARY KEY,
    owner_id      INTEGER NOT NULL REFERENCES "user"(id),
    name          TEXT    NOT NULL CHECK (length(name) BETWEEN 3 AND 100),
    sport         TEXT    NOT NULL
                  CHECK (sport IN ('Football', 'Badminton', 'Tennis', 'Pickleball')),
    area          TEXT    NOT NULL,
    address       TEXT    NOT NULL,
    hourly_price  INTEGER NOT NULL CHECK (hourly_price BETWEEN 1000 AND 100000000),
    open_hour     INTEGER NOT NULL CHECK (open_hour BETWEEN 0 AND 23),
    close_hour    INTEGER NOT NULL CHECK (close_hour BETWEEN 1 AND 24),
    active        INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at    TIMESTAMP NOT NULL DEFAULT NOW(),
    CHECK (open_hour < close_hour)
);

CREATE TABLE IF NOT EXISTS venue_photo (
    id          SERIAL PRIMARY KEY,
    venue_id    INTEGER NOT NULL REFERENCES venue(id),
    file_name   TEXT    NOT NULL UNIQUE,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pricing_rule (
    id              SERIAL PRIMARY KEY,
    venue_id        INTEGER NOT NULL REFERENCES venue(id),
    weekday         INTEGER NOT NULL CHECK (weekday BETWEEN 0 AND 6),
    start_hour      INTEGER NOT NULL CHECK (start_hour BETWEEN 0 AND 23),
    end_hour        INTEGER NOT NULL CHECK (end_hour BETWEEN 1 AND 24),
    price_per_hour  INTEGER NOT NULL CHECK (price_per_hour BETWEEN 1000 AND 100000000),
    CHECK (start_hour < end_hour)
);

CREATE TABLE IF NOT EXISTS blocked_slot (
    id          SERIAL PRIMARY KEY,
    venue_id    INTEGER NOT NULL REFERENCES venue(id),
    slot_start  TIMESTAMP NOT NULL,
    reason      TEXT    NOT NULL DEFAULT 'Under maintenance',
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (venue_id, slot_start)
);

CREATE TABLE IF NOT EXISTS booking (
    id             SERIAL PRIMARY KEY,
    code           TEXT    NOT NULL UNIQUE,
    customer_id    INTEGER NOT NULL REFERENCES "user"(id),
    venue_id       INTEGER NOT NULL REFERENCES venue(id),
    start_at       TIMESTAMP NOT NULL,
    end_at         TIMESTAMP NOT NULL,
    total_price    INTEGER NOT NULL CHECK (total_price >= 0),
    status         booking_status NOT NULL DEFAULT 'confirmed',
    refund_amount  INTEGER CHECK (refund_amount IS NULL OR refund_amount >= 0),
    created_at     TIMESTAMP NOT NULL DEFAULT NOW(),
    cancelled_at   TIMESTAMP,
    CHECK (end_at > start_at)
);

CREATE TABLE IF NOT EXISTS booking_slot (
    id          SERIAL PRIMARY KEY,
    booking_id  INTEGER NOT NULL REFERENCES booking(id) ON DELETE CASCADE,
    venue_id    INTEGER NOT NULL REFERENCES venue(id),
    slot_start  TIMESTAMP NOT NULL,
    price       INTEGER NOT NULL CHECK (price >= 0),
    UNIQUE (venue_id, slot_start)
);

CREATE TABLE IF NOT EXISTS review (
    id            SERIAL PRIMARY KEY,
    booking_id    INTEGER NOT NULL UNIQUE REFERENCES booking(id),
    rating        INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment       TEXT    CHECK (comment IS NULL OR length(comment) <= 1000),
    report_count  INTEGER NOT NULL DEFAULT 0 CHECK (report_count >= 0),
    hidden        INTEGER NOT NULL DEFAULT 0 CHECK (hidden IN (0, 1)),
    created_at    TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_venue_sport_area ON venue (sport, area);
CREATE INDEX IF NOT EXISTS idx_booking_customer ON booking (customer_id);
"""
