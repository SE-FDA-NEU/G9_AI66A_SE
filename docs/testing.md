# Testing - Milestone 4: Automated Testing Strategy & P0 Verification

This document specifies the testing strategy, test case catalog, automated test suite, and defect analysis for Milestone 4. It proves that the Sports Venue Booking System functions deterministically under continuous change, that business rules (`BR1`–`BR19`) are enforced, and that every P0 user story is continuously safeguarded by fast, reproducible automated tests.

---

## 1. What we test, and why

### Layer test coverage matrix

| Layer | Component & Path | Test Type | Tools & Technique | Why / Risk Justification |
|---|---|---|---|---|
| **Services / Business Logic** | `src/booking.py`<br>`src/pricing.py`<br>`src/venues.py`<br>`src/auth.py` | Unit & Service Integration | `pytest`, temporary SQLite fixture, in-memory isolation | **Highest Risk:** All core business rules (`BR1`–`BR19`) live here. Double-booking prevention, atomic concurrency locks, peak segment pricing, duration limits, and account lockout logic are calculated here. A flaw here costs real money or causes venue scheduling chaos. |
| **Data Access / Repository** | `src/db.py`<br>`src/schema.py`<br>`src/init_db.py` | Database Constraint Testing | `pytest`, SQLite temporary databases (`tmp_path`) | **High Risk:** Acts as the impenetrable second line of defense (ADR 2). Tests verify table constraints, unique index enforcement (`UNIQUE(venue_id, slot_start)`), foreign key cascades, and schema integrity without touching production data. |
| **Application Routes / API** | `src/app.py`<br>`src/routes/auth.py`<br>`src/routes/venues.py`<br>`src/routes/owner.py` | Functional Route / API Testing | Flask test client (`app.test_client()`) | **Medium Risk:** Ensures HTTP status codes (200, 201, 302, 400, 401, 403, 404, 409, 410, 422, 423), session lifecycle (30-minute idle timeout BR8), JSON error payload structures (`{"error": ..., "rule": ...}`), and role-based redirects. |
| **User Interface** | `src/templates/*.html`<br>`src/static/style.css` | Manual exploratory walkthrough & contract tests | Browser-based user verification walkthrough | **Low Automation Priority:** Verified thoroughly in Milestone 3 with real user walkthroughs. UI layout changes frequently, while HTML contracts and form field retention on errors are already covered by route assertion tests. |

### Risk Assessment & Testing Focus

Our testing effort is deliberately concentrated where bugs cause irreparable operational failures:
1. **Concurrency and Scheduling Collisions (`src/booking.py`):** Two customers confirming the exact same pitch at the exact same second is the most catastrophic failure mode for a sports venue booking platform. We test both application-level locks (`BEGIN IMMEDIATE`) and database constraints (`UNIQUE(venue_id, slot_start)`), including multi-threaded race condition tests (`threading.Barrier`).
2. **Dynamic Segment Pricing (`src/pricing.py`):** Hanoi pitches switch from standard to peak pricing at 17:00 on weekdays. Booking across this boundary (e.g., 16:00 to 18:00) must calculate the exact proportional sum across segments rather than rounding up or down (`BR12`).
3. **Security, Rate Limiting & Access Control (`src/auth.py`, `src/guards.py`):** Brute-force protection locks accounts after 5 failed attempts (`BR5`), session timeouts expire after 30 idle minutes (`BR8`), and customers are strictly prevented from viewing other customers' bookings or accessing owner portals (`BR14`).

---

## 2. Test cases for every P0 story

Every P0 story is covered by at least three test cases: at least one normal case that succeeds, at least one error case where a business rule refuses invalid input, and boundary cases on both sides of numerical limits (duration, pricing, character length, attempt counters).

| ID | Story | Category | Input & Condition | Expected Result | Kind |
|---|---|---|---|---|---|
| **TC-01** | **US01** Customer registration | Normal | Valid email, phone (`0901234567`), 11-char password (`sanbong1`) | Account created, 302 redirect to `/login`, `email_verified_at IS NULL` (BR4) | normal |
| **TC-02** | **US01** Customer registration | Error | Duplicate email address `minh@example.com` (case-insensitive) | HTTP 409 Conflict, `"This email is already in use"`, no second user saved (BR1) | error |
| **TC-03** | **US01** Customer registration | Boundary | Password of 7 characters (`sanbong`) | HTTP 400 Bad Request, `"Password must be at least 8 characters"` (BR2) | boundary, just below |
| **TC-04** | **US01** Customer registration | Boundary | Password of 8 characters with 1 letter and 1 digit (`sanbong1`) | Accepted, 302 redirect, account registered (BR2) | boundary, on limit |
| **TC-05** | **US01** Customer registration | Boundary | Phone number of 9 digits (`091234567`) | HTTP 400 Bad Request, `"Phone number must be 10 digits"` (BR3) | boundary, just below |
| **TC-06** | **US01** Customer registration | Error | Phone not starting with 0 (`1912345678`) | HTTP 400 Bad Request, `"Phone number must start with 0"` (BR3) | error |
| **TC-07** | **US01** Customer registration | Boundary | Verification token age 24 hours and 1 minute | HTTP 410 Gone, `"This verification link has expired"` (BR4) | boundary, just above |
| **TC-08** | **US02** User login | Normal | Correct credentials for customer `minh@example.com` | 302 redirect to `/dashboard`, session created, customer name displayed (BR7) | normal |
| **TC-09** | **US02** User login | Normal | Correct credentials for owner `lan.owner@example.com` | 302 redirect to `/owner/venues` (BR7) | normal |
| **TC-10** | **US02** User login | Error | Non-existent email OR incorrect password | HTTP 401, identical error `"Email or password is incorrect"` (BR6) | error |
| **TC-11** | **US02** User login | Boundary | 4 consecutive incorrect password attempts | HTTP 401, account remains unlocked, counter = 4 (BR5) | boundary, just below |
| **TC-12** | **US02** User login | Boundary | 5th consecutive incorrect password attempt | HTTP 423 Locked, `"Account temporarily locked. Try again in 15 minutes"` (BR5) | boundary, on limit |
| **TC-13** | **US02** User login | Boundary | User inactivity duration of 29 minutes | Session remains valid, dashboard opens HTTP 200 (BR8) | boundary, just below |
| **TC-14** | **US02** User login | Boundary | User inactivity duration of 31 minutes | Session expired, redirected to `/login` with session timeout flash (BR8) | boundary, just above |
| **TC-15** | **US03** Search venues | Normal | Filter by `sport=Football` and `area=Cau Giay` | HTTP 200, returns Thong Nhat Football Pitch, other sports/areas excluded (BR9) | normal |
| **TC-16** | **US03** Search venues | Error | Hand-typed / unlisted sport (`sport=Golf`) | HTTP 400 Bad Request, `"Please choose a sport from the list"` (BR9) | error |
| **TC-17** | **US03** Search venues | Boundary | Query yielding 0 matching venues (`Tennis` in `Hoan Kiem`) | HTTP 200, explicit message `"No venues found"`, table hidden (BR9) | boundary, zero match |
| **TC-18** | **US04** Venue details | Normal | Venue 1 on Tuesday (16 total slots: 3 booked, 13 free) | HTTP 200, 13 slots marked `"free"`, 3 marked `"booked"` (BR10) | normal |
| **TC-19** | **US04** Venue details | Boundary | Date set to yesterday (`today - 1 day`) | HTTP 400 Bad Request, `"Please choose today or a later date."` (BR10) | boundary, just below |
| **TC-20** | **US04** Venue details | Error | Query availability with malformed date (`20-10-2026`) | HTTP 400 Bad Request, invalid date format (BR10) | error |
| **TC-21** | **US04** Venue details | Boundary | Request venue photos for Venue 1 vs Venue 2 | Photo isolation: photo of venue 2 never appears on venue 1 | boundary, isolation |
| **TC-22** | **US05** Book a venue | Boundary | Book duration of 0 hours | BusinessRuleError refused, `"1 to 4 consecutive hours"` (BR11) | boundary, just below |
| **TC-23** | **US05** Book a venue | Boundary | Book duration of 1 hour (minimum allowed) | HTTP 201 / booking confirmed with code `BK-xxxxxx` (BR11) | boundary, on lower limit |
| **TC-24** | **US05** Book a venue | Boundary | Book duration of 4 hours (maximum allowed) | HTTP 201 / booking confirmed covering 4 consecutive slots (BR11) | boundary, on upper limit |
| **TC-25** | **US05** Book a venue | Boundary | Book duration of 5 hours | BusinessRuleError refused, `"1 to 4 consecutive hours"` (BR11) | boundary, just above |
| **TC-26** | **US05** Book a venue | Normal | Book 19:00–21:00 crossing 20:00 peak boundary on Tuesday | Total = 750,000 VND (1h peak 450k + 1h standard 300k, two price lines) (BR12) | normal |
| **TC-27** | **US05** Book a venue | Error | Two threads confirming the exact same slot at the same time | Exactly 1 booking created (201), 1 refused with 409 `"slot taken"` (BR11, ADR 2) | error / race condition |
| **TC-28** | **US05** Book a venue | Error | Unverified customer tries to book a slot | HTTP 403 Forbidden, `"Please verify your email before booking"` (BR4) | error |
| **TC-29** | **US06** Owner adds venue | Normal | Owner submits valid venue name, dropdowns, price, and PNG photo | 302 redirect, venue created in DB, photo saved to upload directory (BR13) | normal |
| **TC-30** | **US06** Owner adds venue | Boundary | Hourly price = 999 VND (minimum is 1,000) | HTTP 422, `"Hourly price must be between 1,000 and 100,000,000 VND"` (BR13) | boundary, just below |
| **TC-31** | **US06** Owner adds venue | Boundary | Hourly price = 100,000,001 VND (maximum is 100,000,000) | HTTP 422, `"Hourly price must be at most 100,000,000 VND"` (BR13) | boundary, just above |
| **TC-32** | **US06** Owner adds venue | Boundary | Venue name length = 2 characters (`"Sa"`) | HTTP 422, `"Venue name must be 3 to 100 characters"` (BR13) | boundary, just below |
| **TC-33** | **US06** Owner adds venue | Boundary | Venue name length = 101 characters | HTTP 422, `"Venue name must be 3 to 100 characters"` (BR13) | boundary, just above |
| **TC-34** | **US06** Owner adds venue | Boundary | Photo upload size = 5 MB + 1 byte | HTTP 413 Payload Too Large / 422, file size limit exceeded | boundary, just above |
| **TC-35** | **US06** Owner adds venue | Error | Customer account attempts to access `/owner/venues/new` | HTTP 403 Forbidden, customer denied access to owner portal (BR14) | error |

---

## 3. Automated tests

### Execution Command

The entire automated test suite runs locally without requiring a running server, network connectivity, or the live database:

```bash
# Activate your virtual environment first
source .venv/bin/activate       # Windows: .venv\Scripts\Activate.ps1

# Run the complete test suite with verbose output
python -m pytest -v
```

### Pytest Execution Output

All 89 tests pass deterministically in approximately 22 seconds on an isolated temporary SQLite database fixture:

```text
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.7.0 -- .venv/bin/python3
cachedir: .pytest_cache
rootdir: /path/to/G9_AI66A_SE
configfile: pytest.ini
testpaths: tests
collecting ... collected 89 items

tests/test_booking.py::test_peak_price_applies_only_on_its_weekday PASSED [  1%]
tests/test_booking.py::test_booking_across_boundary_is_two_lines_and_exact_sum PASSED [  2%]
tests/test_booking.py::test_hours_with_the_same_price_form_one_line PASSED [  3%]
tests/test_booking.py::test_confirmed_price_does_not_change_when_rules_change PASSED [  4%]
tests/test_booking.py::test_confirm_returns_code_and_hour_is_no_longer_free PASSED [  5%]
tests/test_booking.py::test_same_hour_confirmed_first_by_another_customer PASSED [  6%]
tests/test_booking.py::test_overlapping_booking_with_a_different_start_is_refused PASSED [  7%]
tests/test_booking.py::test_two_customers_confirming_at_once_give_one_booking PASSED [  8%]
tests/test_booking.py::test_unique_constraint_catches_what_the_recheck_misses PASSED [ 10%]
tests/test_booking.py::test_only_start_times_inside_opening_hours_are_offered PASSED [ 11%]
tests/test_booking.py::test_tc13_booking_duration_boundaries PASSED      [ 12%]
tests/test_booking.py::test_more_than_four_hours_is_refused PASSED       [ 13%]
tests/test_booking.py::test_three_hours_from_21_says_the_venue_closes_at_22 PASSED [ 14%]
tests/test_booking.py::test_blocked_hour_cannot_be_booked PASSED         [ 15%]
tests/test_booking.py::test_fully_booked_day_says_so_and_links_the_nearest_date PASSED [ 16%]
tests/test_booking.py::test_unverified_email_cannot_book PASSED          [ 17%]
tests/test_booking.py::test_page_flow_confirms_and_only_the_owner_can_open_the_booking PASSED [ 19%]
tests/test_booking.py::test_api_creates_a_booking_and_requires_sign_in PASSED [ 20%]
tests/test_health.py::test_health_reports_seeded_venues PASSED           [ 21%]
tests/test_login.py::test_customer_lands_on_their_page_and_sees_their_name PASSED [ 22%]
tests/test_login.py::test_owner_lands_in_venue_management PASSED         [ 23%]
tests/test_login.py::test_admin_lands_in_the_admin_area PASSED           [ 24%]
tests/test_login.py::test_wrong_password_and_unknown_email_get_the_same_message PASSED [ 25%]
tests/test_login.py::test_fifth_wrong_password_locks_the_account PASSED  [ 26%]
tests/test_login.py::test_lock_ends_after_15_minutes_and_counter_resets PASSED [ 28%]
tests/test_login.py::test_session_expires_after_30_minutes_idle PASSED   [ 29%]
tests/test_login.py::test_session_still_valid_after_29_minutes PASSED    [ 30%]
tests/test_login.py::test_signed_out_visitor_is_sent_to_login PASSED     [ 31%]
tests/test_login.py::test_customer_cannot_open_the_owner_area PASSED     [ 32%]
tests/test_login.py::test_sign_out_ends_the_session PASSED               [ 33%]
tests/test_login.py::test_api_login_returns_role_and_landing_page PASSED [ 34%]
tests/test_login.py::test_api_login_error_names_the_rule PASSED          [ 35%]
tests/test_owner.py::test_owner_adds_a_venue_with_a_photo PASSED         [ 37%]
tests/test_owner.py::test_price_below_1000_is_refused[0] PASSED          [ 38%]
tests/test_owner.py::test_price_below_1000_is_refused[-50,000] PASSED    [ 39%]
tests/test_owner.py::test_price_below_1000_is_refused[999] PASSED        [ 40%]
tests/test_owner.py::test_price_above_100_million_is_refused PASSED      [ 41%]
tests/test_owner.py::test_name_is_required_and_3_to_100_characters[-Please enter the venue name] PASSED [ 42%]
tests/test_owner.py::test_name_is_required_and_3_to_100_characters[Sa-Venue name must be 3 to 100 characters] PASSED [ 43%]
tests/test_owner.py::test_name_is_required_and_3_to_100_characters[x*101-Venue name must be 3 to 100 characters] PASSED [ 44%]
tests/test_owner.py::test_form_keeps_what_the_owner_typed PASSED         [ 46%]
tests/test_owner.py::test_customer_gets_403_on_the_add_venue_page PASSED [ 47%]
tests/test_owner.py::test_sport_and_area_come_from_drop_down_lists PASSED [ 48%]
tests/test_owner.py::test_photo_must_be_jpg_or_png PASSED                [ 49%]
tests/test_owner.py::test_photo_larger_than_5_mb_is_refused PASSED       [ 50%]
tests/test_owner.py::test_owner_sees_only_their_own_venues PASSED        [ 51%]
tests/test_owner.py::test_api_create_venue PASSED                        [ 52%]
tests/test_register.py::test_new_customer_is_created_and_sent_to_login PASSED [ 53%]
tests/test_register.py::test_same_email_twice_is_refused PASSED          [ 55%]
tests/test_register.py::test_short_password_keeps_the_other_fields PASSED [ 56%]
tests/test_register.py::test_password_needs_a_letter_and_a_digit[12345678-False] PASSED [ 57%]
tests/test_register.py::test_password_needs_a_letter_and_a_digit[sanbongg-False] PASSED [ 58%]
tests/test_register.py::test_password_needs_a_letter_and_a_digit[sanbong1-True] PASSED [ 59%]
tests/test_register.py::test_phone_must_be_ten_digits_starting_with_zero[091234567-Phone number must be 10 digits] PASSED [ 60%]
tests/test_register.py::test_phone_must_be_ten_digits_starting_with_zero[1912345678-Phone number must start with 0] PASSED [ 61%]
tests/test_register.py::test_verification_link_verifies_the_account PASSED [ 62%]
tests/test_register.py::test_link_older_than_24_hours_has_expired PASSED [ 64%]
tests/test_register.py::test_tampered_link_is_refused PASSED             [ 65%]
tests/test_register.py::test_unverified_customer_is_asked_to_verify_and_can_get_a_new_link PASSED [ 66%]
tests/test_register.py::test_api_register_returns_201_then_409 PASSED    [ 67%]
tests/test_schema.py::test_seed_row_counts PASSED                        [ 68%]
tests/test_schema.py::test_same_email_twice_is_rejected PASSED           [ 69%]
tests/test_schema.py::test_phone_must_be_ten_digits_starting_with_zero PASSED [ 70%]
tests/test_schema.py::test_same_hour_cannot_be_booked_twice PASSED       [ 71%]
tests/test_schema.py::test_venue_name_and_price_limits[Sa-250000] PASSED [ 73%]
tests/test_schema.py::test_venue_name_and_price_limits[New Court-0] PASSED [ 74%]
tests/test_schema.py::test_venue_name_and_price_limits[New Court-999] PASSED [ 75%]
tests/test_schema.py::test_peak_hour_booking_is_priced_per_segment PASSED [ 76%]
tests/test_schema.py::test_rating_must_be_one_to_five PASSED             [ 77%]
tests/test_schema.py::test_seeded_bookings_are_in_the_future PASSED      [ 78%]
tests/test_search.py::test_health_reports_seeded_venues PASSED           [ 79%]
tests/test_search.py::test_root_page_shows_venue_search PASSED           [ 80%]
tests/test_search.py::test_search_lists_all_seeded_venues PASSED         [ 82%]
tests/test_search.py::test_search_matches_sport_and_area_together PASSED [ 83%]
tests/test_search.py::test_search_with_no_match_shows_message PASSED     [ 84%]
tests/test_search.py::test_area_list_is_fixed_not_typed PASSED           [ 85%]
tests/test_search.py::test_unknown_sport_is_refused_with_a_message PASSED [ 86%]
tests/test_search.py::test_typed_text_narrows_by_name_or_sport PASSED    [ 87%]
tests/test_search.py::test_page_follows_the_database PASSED              [ 88%]
tests/test_search.py::test_api_search_returns_venues_or_the_no_match_message PASSED [ 89%]
tests/test_venue.py::test_detail_page_shows_the_venue PASSED             [ 91%]
tests/test_venue.py::test_search_result_links_to_the_detail_page PASSED  [ 92%]
tests/test_venue.py::test_unknown_venue_is_404_with_a_message PASSED     [ 93%]
tests/test_venue.py::test_sixteen_slots_three_booked_thirteen_free PASSED [ 94%]
tests/test_venue.py::test_availability_is_for_exactly_the_chosen_date PASSED [ 95%]
tests/test_venue.py::test_blocked_hours_are_shown_as_blocked PASSED      [ 96%]
tests/test_venue.py::test_past_date_is_refused PASSED                    [ 97%]
tests/test_venue.py::test_malformed_date_is_refused PASSED               [ 98%]
tests/test_venue.py::test_gallery_shows_only_this_venues_photos PASSED   [100%]

============================= 89 passed in 22.50s ==============================
```

---

## 4. What the tests found

### Flaky Regression: Date-dependent seed collision in booking uniqueness test

* **The Issue:**
  In Sprint 3, seed data generation was modified (`d73f47c`) to compute seed booking dates relative to `date.today()` (`next_weekday(1)` for Tuesdays). However, `tests/test_booking.py` had pinned test fixtures to an arbitrary fixed Tuesday (`2026-10-13`). When test execution occurred on dates where `next_weekday(1)` dynamically calculated Tuesday 2026-10-13, the seeded database already contained a booking for Venue 1 (`BK-000103` or `BK-000106`).
  
  When `test_unique_constraint_catches_what_the_recheck_misses` ran:
  ```python
  assert conn.execute("SELECT COUNT(*) FROM booking WHERE start_at LIKE '2026-10-13%'").fetchone()[0] == 1
  ```
  The test expected exactly 1 booking for the whole day, but encountered 2 (the seeded booking + the newly inserted test booking), turning the test suite RED.

* **The Red Test Output:**
  ```text
  ________________ test_unique_constraint_catches_what_the_recheck_misses ________________
      with connect(db) as conn:
  >       assert conn.execute("SELECT COUNT(*) FROM booking WHERE start_at LIKE '2026-10-13%'").fetchone()[0] == 1
  E       assert 2 == 1

  tests/test_booking.py:138: AssertionError
  =========================== short test summary info ============================
  FAILED tests/test_booking.py::test_unique_constraint_catches_what_the_recheck_misses
  ======================== 1 failed, 87 passed in 22.12s =========================
  ```

* **The Fix & Guarding Test:**
  The test was verifying whether the database `UNIQUE(venue_id, slot_start)` constraint prevents duplicate rows for a specific slot when application-level checks are skipped. The broad wildcard query `WHERE start_at LIKE '2026-10-13%'` was flawed because it conflated other bookings on the same calendar day with the slot under test.
  
  In PR #92 (Issue #88), the assertion was corrected to inspect the exact slot under test:
  ```python
  assert conn.execute(
      "SELECT COUNT(*) FROM booking WHERE start_at = '2026-10-13 18:00'"
  ).fetchone()[0] == 1
  ```
  This guarantees that even if dynamic seed data places other bookings on the same calendar day, the test accurately and strictly verifies that the collision on `18:00` was blocked by the database constraint.
