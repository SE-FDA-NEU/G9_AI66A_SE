# User interface - Sports Venue Booking System

**Milestone 3 · Team 09 · Sprint 3 (05/10/2026 - 18/10/2026)**

Milestone 2 ([`design.md`](design.md)) proved that the system runs. This document shows
that people can use it: every P0 story works from start to finish through the interface,
with real data from the database, and every broken business rule gives a clear message.

To run it on a new machine, follow [`SETUP.md`](SETUP.md).

| Section                       | Owner             | Issue |
| ----------------------------- | ----------------- | ----- |
| 1. P0 stories and status      | @lequangk2006-sys | #70   |
| 2. Wireframes                 | @lequangk2006-sys | #70   |
| 3. Error messages             | @lequangk2006-sys | #70   |
| 4. What changed since M2      | @thunopro         | #71   |

---

## 1. P0 stories and status

_Not written yet - owner @lequangk2006-sys, issue #70._

---

## 2. Wireframes

_Not written yet - owner @lequangk2006-sys, issue #70._

---

## 3. Error messages

_Not written yet - owner @lequangk2006-sys, issue #70._

---

## 4. What changed since M2

Drawing the wireframes in section 2 and then building the screens showed four places where
[`design.md`](design.md) did not match what the interface needs. Each change below is
already made in `design.md` in this same pull request, so the two documents agree.

### Change 1 - New table `venue_photo` (data model)

US04 criterion 3 shows a photo gallery on the venue page and US06 criterion 1 lets the
owner upload a photo, but the M2 ERD had **nowhere to store a photo** - `venue` had no
photo column and no table pointed at it. We only noticed when we drew the venue-detail
wireframe (section 2.4) and had to say where the `[photo]` boxes come from.

We added `venue_photo (id, venue_id → venue, file_name UNIQUE, created_at)` rather than a
`photo` column on `venue`, because a venue can have several photos (multiplicity
1 - 0..\*). The file itself is saved in `data/uploads/` under a random name and that folder
is git-ignored, like the database. Updated: `design.md` section 2 (table, relationships and
`images/erd.png`), `src/schema.py`.

### Change 2 - Two new endpoints: `GET /api/owner/venues` and `POST /api/auth/logout` (API)

The My venues wireframe (section 2.7) lists the owner's venues, but M2 had only
`POST /api/owner/venues` to **create** one - no way to **list** them. And every page has a
**Sign out** button in the top bar, but M2 had no endpoint to end a session. Added as rows
15 and 16 of `design.md` section 3, with their error codes (401 when nobody is signed in,
403 when a customer asks for the owner list - BR14).

### Change 3 - Forms post to their page, not to `/api` from JavaScript (architecture)

M2 said each page's data "comes from, or is submitted to, the endpoints". Building the
Create an account screen showed the cost: US01 criterion 3 wants every message next to its
field **and** everything already typed kept in the form. With JavaScript calling
`POST /api/auth/register`, every form would need code to put the values and messages back.
So each form now posts to its own page route (`POST /register`, `POST /booking/{venueId}`,
`POST /owner/venues/new`), which calls **the same service function** as the API endpoint
and re-renders the form with the message. The JSON API stays, unchanged, for the same
rules; only the free-hour grid on `/venues/{id}` calls it from JavaScript, because it is the
one part of a page that reloads without the rest (the four states in section 2.4). This
keeps ADR 1 (server-rendered pages) true. Updated: `design.md` sections 1 and 3.

### Change 4 - The verification email stays a stub and the link is shown on screen (architecture)

M2 planned a real SMTP account "in Sprint 3 through `.env`". The Create an account
wireframe made us follow US01 to its end: after registering, the user must open the link
from the email to be allowed to book (BR4). On the instructor's clean machine there is no
SMTP password - and there must never be a real one in `SETUP.md` - so the story could not
be finished without help. The link is now printed in the terminal **and** shown on the
login page in a blue box (*"No email server is set up on this machine, so here is the link
we just sent: Verify my email"*) while `SHOW_VERIFICATION_LINK=1` in `.env`. The 24-hour
expiry (BR4) still applies to the link. Updated: `design.md` section 1 (Email service row,
`images/architecture.png`), `.env.example`. This is also why US01 is marked
**partly works** in section 1.
