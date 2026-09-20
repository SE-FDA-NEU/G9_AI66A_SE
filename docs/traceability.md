# Traceability

Every screen traces back to a feature and forward to the issue that built it. This table
is the single source of truth for Milestone 1 section 6 and for the Milestone 4 report.
Keep it current - a PR that adds a route and does not update this file should not be
approved.

| Route | Purpose | Access | Priority | Feature | Story issue | PR | Status |
|-------|---------|--------|----------|---------|-------------|-----|--------|
| `/` | Home page, search by sport and area, entry to sign in and register | G | P0 | F1 Access | #16 | #30 | Spec done |
| `/register` | Create a customer account | G | P0 | F1 Access | #14 | #27 | Spec done |
| `/login` | Sign in, route by role | G | P0 | F1 Access | #15 | #<TBD> | Spec done |
| `/search` | Search results, filter by sport, area, time slot and price | G | P0 | F2 Discovery | #16 | #30 | Spec done |
| `/venues/{id}` | Venue detail: photos, price, facilities, free-slot grid, reviews | G | P0 | F2 Discovery | #17, #25 | #31, #33 | Spec done |
| `/booking/{venueId}` | Confirm a booking: pick a slot, see the segmented price, confirm | U | P0 | F3 Booking | #18, #24 | #29, #28 | Spec done |
| `/dashboard` | The customer's page after signing in | U | P1 | F4 Booking management | #15 | #<TBD> | Spec done |
| `/my-bookings` | My bookings: upcoming, history, cancel, review after playing | U | P1 | F4 Booking management | #19, #20, #25 | #36, #35, #33 | Spec done |
| `/owner/venues` | The owner's list of venues | U | P0 | F5 Venue management | #21 | #32 | Spec done |
| `/owner/venues/new` | Add a new venue | U | P0 | F5 Venue management | #21 | #32 | Spec done |
| `/owner/venues/{id}/schedule` | Venue schedule: block and unblock hours for maintenance | U | P1 | F5 Venue management | #22 | #37 | Spec done |
| `/owner/venues/{id}/pricing` | Configure peak and off-peak pricing | U | P2 | F6 Pricing | #24 | #28 | Spec done |
| `/owner/bookings` | Day-by-day list of bookings across the owner's venues | U | P1 | F5 Venue management | #23 | #38 | Spec done |
| `/admin` | Moderate reported reviews, suspend offending accounts | A | P2 | F7 Administration | - | - | Not started |

**Access codes:** G = guest (not signed in) · U = authenticated user · A = administrator

**Status:** Not started / Spec done (specified in Sprint 1, no code yet) / In progress / Done

> Sprint 1 was a requirements sprint. Every screen above is at **Spec done**: it has
> acceptance criteria that can be checked, but no implementation. The PR column points at
> the Pull Request that merged the specification. A screen moves to **Done** when it runs
> and passes all 8 items of the Definition of Done.

## Business rules

Numbered so that issues and tests can cite them. This is the **single project-wide
sequence**. The full list with worked examples in real numbers is section 5 of
[`docs/requirements.md`](requirements.md).

| # | Rule | Enforced where | Story issue |
|---|------|----------------|-------------|
| BR1 | One email address maps to exactly one account | `/register` | #14 |
| BR2 | Password is at least 8 characters with at least one letter and one digit | `/register` | #14 |
| BR3 | Phone number is exactly 10 digits and starts with 0 | `/register` | #14 |
| BR4 | An unverified account cannot book; the verification link expires after 24 hours | `/register`, `/booking/{venueId}` | #14 |
| BR5 | Five consecutive wrong passwords lock the account for 15 minutes | `/login` | #15 |
| BR6 | A failed sign-in message must not reveal whether the email exists | `/login` | #15 |
| BR7 | Where a user lands after signing in depends on their role | `/login` | #15 |
| BR8 | A session expires after 30 minutes of inactivity | system-wide | #15 |
| BR9 | Search matches sport and area at the same time; no match returns an explicit message | `/search` | #16 |
| BR10 | Availability is shown for exactly the date the customer selected | `/venues/{id}` | #17 |
| BR11 | A slot holds exactly one active booking; availability is re-checked before confirming | `/booking/{venueId}` | #18 |
| BR12 | Prices are per hour in VND, slots are half-open `[start, end)`, crossings are split per segment, rules must not overlap, confirmed bookings keep their price | `/booking/{venueId}`, `/owner/venues/{id}/pricing` | #24 |
| BR13 | Hourly price is 1,000-100,000,000 VND; venue name is required and 3-100 characters | `/owner/venues/new` | #21 |
| BR14 | A user may only view and act on their own data; a violation returns 403 | `/my-bookings`, `/owner/bookings`, `/owner/venues/new` | #19, #20, #21, #23 |
| BR15 | Cancellation tiers: >= 24 h refunds 100%, 2-24 h refunds 50%, < 2 h is refused | `/my-bookings` | #19 |
| BR16 | A blocked slot is hidden from search; unblocking takes effect within 5 seconds | `/owner/venues/{id}/schedule`, `/search` | #22 |
| BR17 | A slot that already holds an uncancelled booking cannot be blocked | `/owner/venues/{id}/schedule` | #22 |
| BR18 | Only a completed booking can be reviewed; one review per booking; 1-5 stars; comment <= 1,000 characters | `/my-bookings`, `/venues/{id}` | #25 |
| BR19 | A review with 3 valid abuse reports is hidden automatically pending moderation | `/venues/{id}`, `/admin` | #25 |
