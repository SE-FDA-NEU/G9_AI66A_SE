## 1. Architecture

![Container diagram - Sports Venue Booking System](images/architecture.png)

The whole product runs as **one Python process** on one machine, with the database as a
file next to it. That is deliberate (see ADR 1 and ADR 3): the instructor must be able to
clone and run it in fifteen minutes on a machine we have never seen.

| Component | Technology | Where it runs | Responsibility |
|-----------|------------|---------------|----------------|
| Browser | Any modern browser | User's phone or laptop | Renders HTML pages and submits forms. No business logic. |
| Flask web app | Python 3.11+, Flask 3, Jinja2 templates - `src/app.py` | Host machine, port 5000 | Routes, form parsing, session cookie (BR8), role check before every owner/admin route (BR7, BR14), renders pages, serves the JSON API under `/api`. |
| Service layer | Plain Python modules - `src/auth.py`, `src/venues.py`, `src/booking.py`, `src/pricing.py` | Same process | Every business rule BR1-BR19 lives here, not in routes and not in templates. Routes call it; it calls the database. |
| SQLite database | SQLite 3 via the standard `sqlite3` module - `data/venues.db` | A file on the host | Stores the 7 tables of section 2. `CHECK` and `UNIQUE` constraints are the last line of defence for BR1, BR3, BR11, BR13, BR18. |
| Seed script | `src/init_db.py` + `data/venues.csv` | Run once by hand | Creates every table and inserts 24 venues, 6 users, 5 bookings. |
| Email service | SMTP (external) | Outside our system | Sends the verification link (BR4). **Sprint 2: a stub that prints the link to the console;** a real SMTP account is configured in Sprint 3 through `.env`. |

**What travels along each arrow**

| From → To | What travels |
|-----------|--------------|
| Browser → Flask | HTTP `GET` (page loads, search filters as query string) and `POST` (HTML form data, or JSON for `/api/*`) |
| Flask → Browser | Rendered HTML pages, JSON responses, the signed session cookie |
| Flask → Service layer | Python function calls with already-parsed input, e.g. `create_booking(user_id, venue_id, date, start_hour, hours)` |
| Service layer → Flask | A result object, or a `BusinessRuleError` carrying the BR number, message and HTTP code |
| Service layer → SQLite | SQL statements over `sqlite3`; every write that checks and then inserts runs in one transaction |
| Seed script → SQLite | `CREATE TABLE` from `src/schema.py`, then `INSERT` rows read from `data/venues.csv` |
| Service layer → Email service | An SMTP message containing the verification link (BR4) |

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
  means two toolchains (Python *and* Node 20, `pip` *and* `npm install`), two processes
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
  (b) only catches bookings that *start* at the same hour - A books 18:00-20:00, B books
  19:00-20:00, the start times differ and both are accepted. With (c) B's `INSERT` of the
  19:00 row fails with a constraint error however close together the requests are, and
  the service turns that error into **409 "This time slot is no longer available"**. The
  same rows carry each hour's price, which is exactly what BR12's per-segment split
  needs, and deleting them on cancel releases the hours (BR15).
- **What would change our mind:** if bookings stop being whole hours (for example the
  product owner asks for 30-minute badminton slots), one row per hour becomes one row per
  half-hour; if slots become arbitrary lengths, we would need a database with range
  exclusion constraints (PostgreSQL `EXCLUDE USING gist`).
