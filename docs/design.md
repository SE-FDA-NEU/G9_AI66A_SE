=======

# Design - Sports Venue Booking System

**Milestone 2 · Team 09 · Sprint 2 (21/09/2026 - 04/10/2026)**

Milestone 1 ([`requirements.md`](requirements.md)) said what the product does. This
document says how it is built, and points at the walking skeleton that proves the layers
connect: a page, the Flask app, a real SQLite database, and back to the page.

To run it on a new machine, follow [`SETUP.md`](SETUP.md).

| Section                  | Owner          | Issue |
| ------------------------ | -------------- | ----- |
| 1. Architecture          | @htngochan2802 | #46   |
| 2. Data model            | @thunopro      | #44   |
| 3. API design            | @htngochan2802 | #47   |
| 4. Walking skeleton      | @peng543       | #45   |
| 5. Design decisions      | @htngochan2802 | #46   |
| 6. What changed since M1 | @thunopro      | #50   |

---

> > > > > > > 5c313234b6af5c9539df3aa23c8fb0ff024bdb09

## 1. Architecture

![Container diagram - Sports Venue Booking System](images/architecture.png)

The whole product runs as **one Python process** on one machine, with the database as a
file next to it. That is deliberate (see ADR 1 and ADR 3): the instructor must be able to
clone and run it in fifteen minutes on a machine we have never seen.

| Component       | Technology                                                                                | Where it runs           | Responsibility                                                                                                                                             |
| --------------- | ----------------------------------------------------------------------------------------- | ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Browser         | Any modern browser                                                                        | User's phone or laptop  | Renders HTML pages and submits forms. No business logic.                                                                                                   |
| Flask web app   | Python 3.11+, Flask 3, Jinja2 templates - `src/app.py`                                    | Host machine, port 5000 | Routes, form parsing, session cookie (BR8), role check before every owner/admin route (BR7, BR14), renders pages, serves the JSON API under `/api`.        |
| Service layer   | Plain Python modules - `src/auth.py`, `src/venues.py`, `src/booking.py`, `src/pricing.py` | Same process            | Every business rule BR1-BR19 lives here, not in routes and not in templates. Routes call it; it calls the database.                                        |
| SQLite database | SQLite 3 via the standard `sqlite3` module - `data/venues.db`                             | A file on the host      | Stores the 7 tables of section 2. `CHECK` and `UNIQUE` constraints are the last line of defence for BR1, BR3, BR11, BR13, BR18.                            |
| Seed script     | `src/init_db.py` + `data/venues.csv`                                                      | Run once by hand        | Creates every table and inserts 24 venues, 6 users, 5 bookings.                                                                                            |
| Email service   | SMTP (external)                                                                           | Outside our system      | Sends the verification link (BR4). **Sprint 2: a stub that prints the link to the console;** a real SMTP account is configured in Sprint 3 through `.env`. |

**What travels along each arrow**

| From → To                     | What travels                                                                                                       |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Browser → Flask               | HTTP `GET` (page loads, search filters as query string) and `POST` (HTML form data, or JSON for `/api/*`)          |
| Flask → Browser               | Rendered HTML pages, JSON responses, the signed session cookie                                                     |
| Flask → Service layer         | Python function calls with already-parsed input, e.g. `create_booking(user_id, venue_id, date, start_hour, hours)` |
| Service layer → Flask         | A result object, or a `BusinessRuleError` carrying the BR number, message and HTTP code                            |
| Service layer → SQLite        | SQL statements over `sqlite3`; every write that checks and then inserts runs in one transaction                    |
| Seed script → SQLite          | `CREATE TABLE` from `src/schema.py`, then `INSERT` rows read from `data/venues.csv`                                |
| Service layer → Email service | An SMTP message containing the verification link (BR4)                                                             |

**Sprint 2 status.** Browser, Flask app, SQLite and seed script exist and are connected
(section 4). The service-layer modules are created one per story from Sprint 3; the only
query in the walking skeleton lives in `src/app.py` and moves to `src/venues.py` when
US03 is implemented.

## 2.

## 5. Design decisions

### ADR 1 - Flask with server-rendered pages, not a JavaScript single-page app

- **Options:** (a) Flask + Jinja2 templates · (b) FastAPI backend + React frontend ·
  (c) Node.js / Express + EJS.
- **Chose:** (a) Flask + Jinja2.
- **Why:** The instructor runs our project from `SETUP.md` on a clean machine. Option (b)
  means two toolchains (Python _and_ Node 20, `pip` _and_ `npm install`), two processes
  and CORS - roughly double the steps that can fail. Every member has written Python in
  earlier courses; only one has used React. None of our 14 screens needs client-side
  state beyond a form - the richest one, the slot grid on `/venues/{id}`, is a table of
  at most 18 cells that can be re-rendered by the server.
- **What would change our mind:** if the owner's schedule screen (US09) needs drag-to-block
  across many days and a full page reload per click tests as too slow at the Sprint 3
  review, we add a small script (or htmx) to that one page - not a framework for the
  whole site.

### ADR 2 - Prevent double booking with one row per booked hour, not a check in code

- **Options:** (a) In `create_booking`, `SELECT` for an overlapping booking, then
  `INSERT` if none · (b) `UNIQUE (venue_id, start_at)` on `booking` · (c) a
  `booking_slot` table with one row per booked hour and `UNIQUE (venue_id, slot_start)`.
- **Chose:** (c).
- **Why:** BR11 is the rule the whole product stands on: customer A at 14:00:00 and
  customer B at 14:00:03 must end with one booking, not two. Option (a) has a gap
  between the `SELECT` and the `INSERT` where both requests see the hour as free. Option
  (b) only catches bookings that _start_ at the same hour - A books 18:00-20:00, B books
  19:00-20:00, the start times differ and both are accepted. With (c) B's `INSERT` of the
  19:00 row fails with a constraint error however close together the requests are, and
  the service turns that error into **409 "This time slot is no longer available"**. The
  same rows carry each hour's price, which is exactly what BR12's per-segment split
  needs, and deleting them on cancel releases the hours (BR15).
- **What would change our mind:** if bookings stop being whole hours (for example the
  product owner asks for 30-minute badminton slots), one row per hour becomes one row per
  half-hour; if slots become arbitrary lengths, we would need a database with range
  exclusion constraints (PostgreSQL `EXCLUDE USING gist`).

### ADR 3 - SQLite file, not PostgreSQL or MySQL

- **Options:** SQLite file · PostgreSQL in Docker · MySQL installed locally.
- **Chose:** SQLite.
- **Why:** Nothing to install - `sqlite3` ships with Python. Our largest realistic
  dataset (a few hundred venues, tens of thousands of booking hours) is far below
  SQLite's limits. It supports every constraint ADR 2 relies on: `UNIQUE`, `CHECK`,
  foreign keys (switched on per connection in `src/db.py`).
- **What would change our mind:** SQLite allows one writer at a time. If the concurrency
  test planned for Sprint 4 (20 simultaneous bookings of one hour) shows `database is
locked` errors reaching users, we move to PostgreSQL; the SQL is standard, so the move
  is the connection code plus Docker in `SETUP.md`.
  =======

# Design - Sports Venue Booking System

**Milestone 2 · Team 09 · Sprint 2 (21/09/2026 - 04/10/2026)**

Milestone 1 ([`requirements.md`](requirements.md)) said what the product does. This
document says how it is built, and points at the walking skeleton that proves the layers
connect: a page, the Flask app, a real SQLite database, and back to the page.

To run it on a new machine, follow [`SETUP.md`](SETUP.md).

| Section                  | Owner          | Issue |
| ------------------------ | -------------- | ----- |
| 1. Architecture          | @htngochan2802 | #46   |
| 2. Data model            | @thunopro      | #44   |
| 3. API design            | @htngochan2802 | #47   |
| 4. Walking skeleton      | @peng543       | #45   |
| 5. Design decisions      | @htngochan2802 | #46   |
| 6. What changed since M1 | @thunopro      | #50   |

---

## 1. Architecture

_Not written yet - owner @htngochan2802, issue #46._

=======

> > > > > > > 5c313234b6af5c9539df3aa23c8fb0ff024bdb09

---

## 2. Data model

![Entity-relationship diagram](images/erd.png)

Seven tables. Types are SQLite storage classes; `DATETIME` columns are stored as `TEXT`
in the form `YYYY-MM-DD HH:MM`, and money is always an `INTEGER` number of VND - never a
float, so 250,000 + 150,000 is exactly 400,000 (BR12). The DDL is
[`src/schema.py`](../src/schema.py).

| Table          | Purpose                                               | Columns (type)                                                                                                                                                                                                                                  | PK   | FK                                                   | Constraint · M1 rule it enforces                                                                                                                                                                                                                                                                           |
| -------------- | ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ---------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `user`         | Every account: customer, venue owner or administrator | `id` INTEGER · `email` TEXT · `password_hash` TEXT · `full_name` TEXT · `phone` TEXT · `role` TEXT · `email_verified_at` DATETIME NULL · `failed_login_count` INTEGER · `locked_until` DATETIME NULL · `created_at` DATETIME                    | `id` | -                                                    | `email` UNIQUE, case-insensitive · **BR1**. `phone` CHECK 10 digits starting with 0 · **BR3**. `email_verified_at` NULL = cannot book · **BR4**. `failed_login_count`, `locked_until` · **BR5**. `role` CHECK IN (customer, owner, admin) · **BR7**                                                        |
| `venue`        | A pitch or court that can be booked                   | `id` INTEGER · `owner_id` INTEGER · `name` TEXT · `sport` TEXT · `area` TEXT · `address` TEXT · `hourly_price` INTEGER · `open_hour` INTEGER · `close_hour` INTEGER · `active` BOOL · `created_at` DATETIME                                     | `id` | `owner_id` → `user.id`                               | `name` CHECK 3-100 characters, `hourly_price` CHECK 1,000-100,000,000 · **BR13**. `sport` CHECK IN a fixed list so search can match exactly · **BR9**. `owner_id` is what "owners act only on their own venues" is checked against · **BR14**                                                              |
| `pricing_rule` | A peak-hour price for one venue on one weekday        | `id` INTEGER · `venue_id` INTEGER · `weekday` INTEGER · `start_hour` INTEGER · `end_hour` INTEGER · `price_per_hour` INTEGER                                                                                                                    | `id` | `venue_id` → `venue.id`                              | CHECK `start_hour < end_hour`, half-open `[start, end)` · **BR12**. "Rules must not overlap" is checked in `src/pricing.py` - SQLite has no range-exclusion constraint · **BR12**                                                                                                                          |
| `blocked_slot` | One hour an owner has closed for maintenance          | `id` INTEGER · `venue_id` INTEGER · `slot_start` DATETIME · `reason` TEXT · `created_at` DATETIME                                                                                                                                               | `id` | `venue_id` → `venue.id`                              | UNIQUE (`venue_id`, `slot_start`); a blocked hour is excluded from search and booking · **BR16**. Blocking an hour that has a `booking_slot` row is refused in `src/booking.py` · **BR17**                                                                                                                 |
| `booking`      | One reservation by one customer                       | `id` INTEGER · `code` TEXT · `customer_id` INTEGER · `venue_id` INTEGER · `start_at` DATETIME · `end_at` DATETIME · `total_price` INTEGER · `status` TEXT · `refund_amount` INTEGER NULL · `created_at` DATETIME · `cancelled_at` DATETIME NULL | `id` | `customer_id` → `user.id`, `venue_id` → `venue.id`   | `code` UNIQUE (e.g. `BK-000148`). `total_price` is written once at confirmation and never recalculated · **BR12**. `refund_amount` records the 100% / 50% tier · **BR15**. `customer_id` is checked on every read · **BR14**                                                                               |
| `booking_slot` | One booked hour of one booking                        | `id` INTEGER · `booking_id` INTEGER · `venue_id` INTEGER · `slot_start` DATETIME · `price` INTEGER                                                                                                                                              | `id` | `booking_id` → `booking.id`, `venue_id` → `venue.id` | **UNIQUE (`venue_id`, `slot_start`)** - the database itself refuses a second booking of the same hour · **BR11** (see ADR 2). `price` keeps the per-segment price, so a 19:00-21:00 booking stores 250,000 + 150,000 as two rows · **BR12**. Cancelling deletes these rows, releasing the hours · **BR15** |
| `review`       | A customer's rating of a completed booking            | `id` INTEGER · `booking_id` INTEGER · `rating` INTEGER · `comment` TEXT NULL · `report_count` INTEGER · `hidden` BOOL · `created_at` DATETIME                                                                                                   | `id` | `booking_id` → `booking.id`                          | `booking_id` UNIQUE, one review per booking; `rating` CHECK 1-5; `comment` CHECK ≤ 1,000 characters · **BR18**. `report_count` ≥ 3 sets `hidden` · **BR19**                                                                                                                                                |

**Relationships and multiplicity** (same as the ERD):

| Relationship                         | Multiplicity | Meaning                                                         |
| ------------------------------------ | ------------ | --------------------------------------------------------------- |
| `user` owns `venue`                  | 1 - 0..\*    | An owner has zero or more venues; a venue has exactly one owner |
| `user` makes `booking`               | 1 - 0..\*    | A customer has zero or more bookings                            |
| `venue` is booked in `booking`       | 1 - 0..\*    |                                                                 |
| `booking` holds `booking_slot`       | 1 - 1..\*    | A booking always covers at least one hour                       |
| `venue` hour taken by `booking_slot` | 1 - 0..\*    |                                                                 |
| `venue` has `pricing_rule`           | 1 - 0..\*    | No rule = standard `hourly_price` all day                       |
| `venue` has `blocked_slot`           | 1 - 0..\*    |                                                                 |
| `booking` is reviewed by `review`    | 1 - 0..1     | At most one review per booking (BR18)                           |

Rules that are **not** a database constraint, and where they are enforced instead: BR2
(password strength - checked before hashing, `src/auth.py`), BR6 (same error message -
`src/auth.py`), BR8 (session timeout - Flask session), BR10 (availability for one date -
query), BR12 overlap of pricing rules, BR15 refund tier, BR17 (`src/booking.py`).

---

## 3. API design

Pages are rendered by Flask; each page's data comes from, or is submitted to, the
endpoints below. Errors return JSON `{"error": "<message>", "rule": "BR<n>"}` with the
code listed; the message is exactly the sentence in the acceptance criterion.

**Authentication:** a signed session cookie set by `POST /api/auth/login`. An endpoint
marked *customer*, *owner* or *any user* returns **401** without a valid session and
**403** for the wrong role (BR14).

| # | Method | Path | Who | Input | Success | Error codes | Story |
|---|--------|------|-----|-------|---------|-------------|-------|
| 1 | POST | `/api/auth/register` | guest | `email`, `password`, `full_name`, `phone` | **201** `{user_id}`; verification link sent | **400** "Password must be at least 8 characters" (BR2) or "Phone number must be 10 digits" (BR3) · **409** "This email is already in use" (BR1) | US01 #14 |
| 2 | GET | `/api/auth/verify` | guest | `token` (query) | **200** account verified | **410** link older than 24 h (BR4) · **404** unknown token | US01 #14 |
| 3 | POST | `/api/auth/login` | guest | `email`, `password` | **200** `{role, redirect}`: `/dashboard`, `/owner/venues` or `/admin` (BR7) | **401** "Email or password is incorrect" - same text whether or not the email exists (BR6) · **423** "Account temporarily locked. Try again in 15 minutes" (BR5) | US02 #15 |
| 4 | GET | `/api/venues` | anyone | `sport`, `area` (query, both optional) | **200** list of `{id, name, sport, area, hourly_price}`; empty list plus `message: "No venues found"` (BR9) | **400** unknown sport or area | US03 #16 |
| 5 | GET | `/api/venues/{id}` | anyone | `date` (query, `YYYY-MM-DD`) | **200** venue detail plus 1-hour slots for that date, each `free` / `booked` / `blocked` (BR10, BR16) | **400** date malformed or in the past · **404** venue not found | US04 #17 |
| 6 | POST | `/api/bookings` | customer | `venue_id`, `date`, `start_hour`, `hours` | **201** `{code, total_price, segments:[{from, to, price}]}` (BR12) | **401** not signed in · **403** "Please verify your email before booking" (BR4) · **409** "This time slot is no longer available" (BR11) · **422** outside opening hours or blocked (BR16) | US05 #18 |
| 7 | POST | `/api/owner/venues` | owner | `name`, `sport`, `area`, `address`, `hourly_price`, `open_hour`, `close_hour` | **201** `{venue_id}` | **403** "You do not have permission to access this page" (BR14) · **422** "Hourly price must be at least 1,000 VND" or name length (BR13) | US06 #21 |

---

## 4. Walking skeleton

_Not written yet - owner @peng543, issue #45._

---

## 5. Design decisions

### ADR 1 - Flask with server-rendered pages, not a JavaScript single-page app

- **Options:** (a) Flask + Jinja2 templates · (b) FastAPI backend + React frontend ·
  (c) Node.js / Express + EJS.
- **Chose:** (a) Flask + Jinja2.
- **Why:** The instructor runs our project from `SETUP.md` on a clean machine. Option (b)
  means two toolchains (Python _and_ Node 20, `pip` _and_ `npm install`), two processes
  and CORS - roughly double the steps that can fail. Every member has written Python in
  earlier courses; only one has used React. None of our 14 screens needs client-side
  state beyond a form - the richest one, the slot grid on `/venues/{id}`, is a table of
  at most 18 cells that can be re-rendered by the server.
- **What would change our mind:** if the owner's schedule screen (US09) needs drag-to-block
  across many days and a full page reload per click tests as too slow at the Sprint 3
  review, we add a small script (or htmx) to that one page - not a framework for the
  whole site.

### ADR 2 - Prevent double booking with one row per booked hour, not a check in code

- **Options:** (a) In `create_booking`, `SELECT` for an overlapping booking, then
  `INSERT` if none · (b) `UNIQUE (venue_id, start_at)` on `booking` · (c) a
  `booking_slot` table with one row per booked hour and `UNIQUE (venue_id, slot_start)`.
- **Chose:** (c).
- **Why:** BR11 is the rule the whole product stands on: customer A at 14:00:00 and
  customer B at 14:00:03 must end with one booking, not two. Option (a) has a gap
  between the `SELECT` and the `INSERT` where both requests see the hour as free. Option
  (b) only catches bookings that _start_ at the same hour - A books 18:00-20:00, B books
  19:00-20:00, the start times differ and both are accepted. With (c) B's `INSERT` of the
  19:00 row fails with a constraint error however close together the requests are, and
  the service turns that error into **409 "This time slot is no longer available"**. The
  same rows carry each hour's price, which is exactly what BR12's per-segment split
  needs, and deleting them on cancel releases the hours (BR15).
- **What would change our mind:** if bookings stop being whole hours (for example the
  product owner asks for 30-minute badminton slots), one row per hour becomes one row per
  half-hour; if slots become arbitrary lengths, we would need a database with range
  exclusion constraints (PostgreSQL `EXCLUDE USING gist`).

### ADR 3 - SQLite file, not PostgreSQL or MySQL

- **Options:** SQLite file · PostgreSQL in Docker · MySQL installed locally.
- **Chose:** SQLite.
- **Why:** Nothing to install - `sqlite3` ships with Python. Our largest realistic
  dataset (a few hundred venues, tens of thousands of booking hours) is far below
  SQLite's limits. It supports every constraint ADR 2 relies on: `UNIQUE`, `CHECK`,
  foreign keys (switched on per connection in `src/db.py`).
- **What would change our mind:** SQLite allows one writer at a time. If the concurrency
  test planned for Sprint 4 (20 simultaneous bookings of one hour) shows `database is
locked` errors reaching users, we move to PostgreSQL; the SQL is standard, so the move
  is the connection code plus Docker in `SETUP.md`.

---

## 6. What changed since M1

_Not written yet - owner @thunopro, issue #50._
<<<<<<< HEAD

> > > > > > > # 56280decc947d0cb8c4df810fe2e32dee17d5643
> > > > > > >
> > > > > > > 5c313234b6af5c9539df3aa23c8fb0ff024bdb09
