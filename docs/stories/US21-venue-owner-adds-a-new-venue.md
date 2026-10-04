# US21 - Venue owner adds a new venue

- **Issue:** #21
- **Priority:** P0
- **Points:** 5
- **Owner:** @PhunghoaAI
- **Screen:** `/owner/venues/new`

> This file is the detailed version of **US06** in [`requirements.md`](../requirements.md).
> Business rule numbers (BR9, BR13, BR14) are the ones in `requirements.md` section 5.

## User story

As a **venue owner**, I want **to add a new venue with its name, sport, area, address,
hourly price and photos** so that **customers can find and book my venue**.

## Acceptance criteria

1. Given I am signed in as the venue owner `owner@example.com`, when I open
   `/owner/venues/new`, enter the name `Thong Nhat Football Pitch`, the address
   `12 Tran Thai Tong, Cau Giay`, the price `250,000` VND per hour, upload 1 photo
   (`thong_nhat.jpg`) and press **Add venue**, then the system shows exactly **"Venue added
   successfully!"**, redirects to `/owner/venues`, and **Thong Nhat Football Pitch**
   appears in my list at `250,000` VND per hour.

2. Given I am on `/owner/venues/new`, when I enter a price of `0` or `-50,000` VND, or leave
   the price empty, and press **Add venue**, then the system refuses, outlines the price
   field in red and shows exactly **"Hourly price must be at least 1,000 VND"** (BR13).

3. Given I am on `/owner/venues/new`, when I enter the price `250,000` but **leave the venue
   name empty** and press **Add venue**, then the system refuses and shows exactly
   **"Please enter the venue name"**; the name must be **3 to 100 characters** (BR13).

4. Given I am signed in as the customer `customer@example.com` (role `customer`), when I
   open `/owner/venues/new` directly, then the system returns **403** with **"You do not
   have permission to access this page"** (BR14).

5. Given I add a venue, when I choose its sport and area, then both come from drop-down
   lists (Football / Badminton / Tennis / Pickleball; the districts of Hanoi) and cannot
   be typed (BR9). *Added in Milestone 2 - see `design.md` section 6, change 2.*

## Related business rules

| ID | Rule | Example with concrete values |
|----|------|------------------------------|
| BR9 | Search matches sport and area at the same time; sport and area are chosen from fixed lists, never typed | The owner picks `Football` and `Cau Giay` → the venue appears when Minh searches "Football" + "Cau Giay". |
| BR13 | The hourly price is an integer from 1,000 to 100,000,000 VND; the venue name is required and 3 to 100 characters long | Price `0` or `-50,000` → rejected. Price `250,000` → accepted. Name `Sa` (2 characters) → rejected. |
| BR14 | A user may only view and act on data that belongs to them; owners act on their own venues; a violation returns 403 | A `customer` account opening `/owner/venues/new` → 403. |

## Tasks

- [ ] `/owner/venues/new` form: name, sport (drop-down), area (drop-down), address, hourly price, photo upload
- [ ] Server-side validation of the required fields and the price range (BR13)
- [ ] `POST /api/owner/venues` (design.md section 3) checks the `owner` role and saves the venue with `active = 1` (BR14)
- [ ] Store and display the venue photo
- [ ] Automated tests: venue created, invalid price, missing name, customer gets 403

## Note

This story is a P0 prerequisite: without venues in the system, search (#16), venue
details (#17) and booking (#18) cannot work. A new venue is `active` by default, so it
shows in search immediately.
