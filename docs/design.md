# Design - Sports Venue Booking System

**Milestone 2 · Team 09 · Sprint 2 (21/09/2026 - 04/10/2026)**

Milestone 1 ([`requirements.md`](requirements.md)) said what the product does. This
document says how it is built, and points at the walking skeleton that proves the layers
connect: a page, the Flask app, a real SQLite database, and back to the page.

To run it on a new machine, follow [`SETUP.md`](SETUP.md).

| Section | Owner | Issue |
|---------|-------|-------|
| 1. Architecture | @htngochan2802 | #46 |
| 2. Data model | @thunopro | #44 |
| 3. API design | @htngochan2802 | #47 |
| 4. Walking skeleton | @peng543 | #45 |
| 5. Design decisions | @htngochan2802 | #46 |
| 6. What changed since M1 | @thunopro | #50 |

---

## 1. Architecture

_Not written yet - owner @htngochan2802, issue #46._

---

## 2. Data model

![Entity-relationship diagram](images/erd.png)

Seven tables. Types are SQLite storage classes; `DATETIME` columns are stored as `TEXT`
in the form `YYYY-MM-DD HH:MM`, and money is always an `INTEGER` number of VND - never a
float, so 250,000 + 150,000 is exactly 400,000 (BR12). The DDL is
[`src/schema.py`](../src/schema.py).

| Table | Purpose | Columns (type) | PK | FK | Constraint · M1 rule it enforces |
|-------|---------|----------------|----|----|----------------------------------|
| `user` | Every account: customer, venue owner or administrator | `id` INTEGER · `email` TEXT · `password_hash` TEXT · `full_name` TEXT · `phone` TEXT · `role` TEXT · `email_verified_at` DATETIME NULL · `failed_login_count` INTEGER · `locked_until` DATETIME NULL · `created_at` DATETIME | `id` | - | `email` UNIQUE, case-insensitive · **BR1**. `phone` CHECK 10 digits starting with 0 · **BR3**. `email_verified_at` NULL = cannot book · **BR4**. `failed_login_count`, `locked_until` · **BR5**. `role` CHECK IN (customer, owner, admin) · **BR7** |
| `venue` | A pitch or court that can be booked | `id` INTEGER · `owner_id` INTEGER · `name` TEXT · `sport` TEXT · `area` TEXT · `address` TEXT · `hourly_price` INTEGER · `open_hour` INTEGER · `close_hour` INTEGER · `active` BOOL · `created_at` DATETIME | `id` | `owner_id` → `user.id` | `name` CHECK 3-100 characters, `hourly_price` CHECK 1,000-100,000,000 · **BR13**. `sport` CHECK IN a fixed list so search can match exactly · **BR9**. `owner_id` is what "owners act only on their own venues" is checked against · **BR14** |
| `pricing_rule` | A peak-hour price for one venue on one weekday | `id` INTEGER · `venue_id` INTEGER · `weekday` INTEGER · `start_hour` INTEGER · `end_hour` INTEGER · `price_per_hour` INTEGER | `id` | `venue_id` → `venue.id` | CHECK `start_hour < end_hour`, half-open `[start, end)` · **BR12**. "Rules must not overlap" is checked in `src/pricing.py` - SQLite has no range-exclusion constraint · **BR12** |
| `blocked_slot` | One hour an owner has closed for maintenance | `id` INTEGER · `venue_id` INTEGER · `slot_start` DATETIME · `reason` TEXT · `created_at` DATETIME | `id` | `venue_id` → `venue.id` | UNIQUE (`venue_id`, `slot_start`); a blocked hour is excluded from search and booking · **BR16**. Blocking an hour that has a `booking_slot` row is refused in `src/booking.py` · **BR17** |
| `booking` | One reservation by one customer | `id` INTEGER · `code` TEXT · `customer_id` INTEGER · `venue_id` INTEGER · `start_at` DATETIME · `end_at` DATETIME · `total_price` INTEGER · `status` TEXT · `refund_amount` INTEGER NULL · `created_at` DATETIME · `cancelled_at` DATETIME NULL | `id` | `customer_id` → `user.id`, `venue_id` → `venue.id` | `code` UNIQUE (e.g. `BK-000148`). `total_price` is written once at confirmation and never recalculated · **BR12**. `refund_amount` records the 100% / 50% tier · **BR15**. `customer_id` is checked on every read · **BR14** |
| `booking_slot` | One booked hour of one booking | `id` INTEGER · `booking_id` INTEGER · `venue_id` INTEGER · `slot_start` DATETIME · `price` INTEGER | `id` | `booking_id` → `booking.id`, `venue_id` → `venue.id` | **UNIQUE (`venue_id`, `slot_start`)** - the database itself refuses a second booking of the same hour · **BR11** (see ADR 2). `price` keeps the per-segment price, so a 19:00-21:00 booking stores 250,000 + 150,000 as two rows · **BR12**. Cancelling deletes these rows, releasing the hours · **BR15** |
| `review` | A customer's rating of a completed booking | `id` INTEGER · `booking_id` INTEGER · `rating` INTEGER · `comment` TEXT NULL · `report_count` INTEGER · `hidden` BOOL · `created_at` DATETIME | `id` | `booking_id` → `booking.id` | `booking_id` UNIQUE, one review per booking; `rating` CHECK 1-5; `comment` CHECK ≤ 1,000 characters · **BR18**. `report_count` ≥ 3 sets `hidden` · **BR19** |

**Relationships and multiplicity** (same as the ERD):

| Relationship | Multiplicity | Meaning |
|--------------|--------------|---------|
| `user` owns `venue` | 1 - 0..* | An owner has zero or more venues; a venue has exactly one owner |
| `user` makes `booking` | 1 - 0..* | A customer has zero or more bookings |
| `venue` is booked in `booking` | 1 - 0..* | |
| `booking` holds `booking_slot` | 1 - 1..* | A booking always covers at least one hour |
| `venue` hour taken by `booking_slot` | 1 - 0..* | |
| `venue` has `pricing_rule` | 1 - 0..* | No rule = standard `hourly_price` all day |
| `venue` has `blocked_slot` | 1 - 0..* | |
| `booking` is reviewed by `review` | 1 - 0..1 | At most one review per booking (BR18) |

Rules that are **not** a database constraint, and where they are enforced instead: BR2
(password strength - checked before hashing, `src/auth.py`), BR6 (same error message -
`src/auth.py`), BR8 (session timeout - Flask session), BR10 (availability for one date -
query), BR12 overlap of pricing rules, BR15 refund tier, BR17 (`src/booking.py`).

---

## 3. API design

_Not written yet - owner @htngochan2802, issue #47._

---

## 4. Walking skeleton

_Not written yet - owner @peng543, issue #45._

---

## 5. Design decisions

_Not written yet - owner @htngochan2802, issue #46._

---

## 6. What changed since M1

_Not written yet - owner @thunopro, issue #50._
