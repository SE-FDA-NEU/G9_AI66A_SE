# US02 - Venue owner sets peak/off-peak hour pricing

- **Issue:** #24
- **Priority:** P2
- **Points:** 5
- **Owner:** @htngochan2802
- **Screen:** TBD

# Story

As a venue owner,
I want to set different prices for peak and off-peak hours,
so that I can optimize revenue based on actual demand throughout the day.

Business Context

Booking demand is uneven throughout the day. The 17:00–21:00 window on weekdays, and most of the weekend, is usually fully booked, while mornings and early afternoons sit largely empty. A flat rate means the venue both loses revenue during peak hours and has no lever to stimulate demand during off-peak hours.

Terminology & Design Decisions
Term Definition
Default price The per-hour rate configured at venue or resource level, applied when no rule matches
Pricing rule A record defining a per-hour rate for a time block + set of weekdays + effective date range
Resource A specific bookable unit (Court 1, Court 2, Room A, etc.)
Price segment The portion of a booking that falls entirely within a single price tier

Decisions already made:

Price is always entered and calculated as VND/hour, not per booking.
Time blocks are half-open [start, end) — a 17:00–20:00 rule does not include the 20:00 instant.
Bookings spanning a boundary are prorated per segment, not rounded up to the higher rate.
Overlapping rules are not allowed on the same resource + same weekday + same effective range.
Deleting a rule is a soft delete (is_active = false), not a hard delete.
Confirmed bookings retain their locked-in price, unaffected by later rule changes.
Scope

In scope

CRUD for pricing rules at venue and resource level
Applicability by day of week (Mon–Sun)
Optional effective date range (for seasonal/holiday surcharges)
Prorated price calculation with a breakdown shown to the customer
Overlap validation and input validation

Out of scope (separate stories)

Dynamic/occupancy-based pricing
Discount codes / vouchers
Membership tier pricing
Booking-lead-time pricing (early bird)
Business Rules
ID Rule
BR-01 Price per hour must be a positive integer, min 1,000 VND, max 100,000,000 VND
BR-02 start_time must differ from end_time; if end_time < start_time, treat it as a rule crossing midnight
BR-03 The minimum time unit for proration is 15 minutes
BR-04 Resource-level rules take priority over venue-level rules
BR-05 If no rule matches, apply the resource's default price, falling back to the venue's default price
BR-06 All calculated prices round up to the nearest 1,000 VND
BR-07 Every pricing rule action is logged (who, when, old value → new value)
BR-08 Only accounts with role venue_owner or venue_manager may create/edit/delete pricing rules
Acceptance Criteria
Group 1 — Creating Rules
gherkin
AC-01: Successfully create a peak-hour rule
Given I am a venue owner and the default price is 300,000 VND/hour
When I create a pricing rule of 500,000 VND/hour for 17:00-20:00, applied Mon-Fri
Then the rule is saved and appears in the pricing rules list
And the booking calendar shows 500,000 VND/hour for 17:00-20:00 slots from Mon to Fri

AC-02: A booking in the peak window is priced correctly
Given a rule of 500,000 VND/hour exists for 17:00-20:00
When a customer books 18:00-19:00 on a Wednesday
Then the total is 500,000 VND
And the price breakdown shows "18:00-19:00 · Peak hour · 500,000 VND"

AC-03: Create an off-peak rule
Given the default price is 300,000 VND/hour
When I create a rule of 180,000 VND/hour for 06:00-09:00
Then bookings within 06:00-09:00 are charged 180,000 VND/hour

AC-04: Rule with an effective date range
Given I create a rule of 700,000 VND/hour for 17:00-20:00, effective 14/02 to 20/02
When a customer books 18:00-19:00 on 16/02
Then the applied price is 700,000 VND
When a customer books 18:00-19:00 on 25/02
Then the applied price falls back to the standing peak rule of 500,000 VND
Group 2 — Time Boundaries
gherkin
AC-05: Half-open boundary at the end time
Given a peak rule of 500,000 VND/hour exists for 17:00-20:00
When a customer books 20:00-21:00
Then the default price of 300,000 VND/hour applies

AC-06: Half-open boundary at the start time
Given a peak rule of 500,000 VND/hour exists for 17:00-20:00
When a customer books 17:00-18:00
Then the peak price of 500,000 VND applies

AC-07: Booking spanning a boundary — prorated per segment
Given the default price is 300,000 VND/hour and a peak rule of 500,000 VND/hour exists for 17:00-20:00
When a customer books 16:00-18:00
Then the total is 800,000 VND
And the breakdown shows:
| 16:00-17:00 | Standard | 1.0 hr | 300,000 VND |
| 17:00-18:00 | Peak hour | 1.0 hr | 500,000 VND |
| Total | | 2.0 hr | 800,000 VND |

AC-08: Booking spanning multiple price tiers
Given default 300,000, off-peak rule 180,000 for 06:00-09:00, peak rule 500,000 for 17:00-20:00
When a customer books 19:00-22:00
Then the total is 1,100,000 VND (1h peak + 2h standard)

AC-09: A 30-minute booking crossing a boundary
Given a peak rule of 500,000 VND/hour exists for 17:00-20:00
When a customer books 16:30-17:30
Then the total is 400,000 VND (0.5h × 300,000 + 0.5h × 500,000)
Group 3 — Validation & Error Handling
gherkin
AC-10: Block overlapping rules
Given a rule exists for 17:00-20:00 applied Mon-Fri
When I create a new rule for 19:00-21:00 applied Wed-Sat
Then the system rejects the save
And displays the error "This time block overlaps with an existing rule (17:00-20:00, Mon-Fri)"

AC-11: Allow the same time block on different days
Given a rule exists for 17:00-20:00 applied Mon-Fri
When I create a rule of 650,000 VND/hour for 17:00-20:00 applied Sat-Sun
Then the rule is saved successfully

AC-12: Block invalid prices
When I enter a price of 0, a negative number, or a non-numeric value
Then the system rejects the save and shows "Price must be a positive integer of at least 1,000 VND"

AC-13: Block invalid time blocks
When I enter a start time equal to the end time
Then the system rejects the save and shows "Start time and end time cannot be the same"

AC-14: Rule crossing midnight
Given the venue is open until 02:00 the next day
When I create a rule of 400,000 VND/hour for 22:00-02:00
Then the rule is saved and correctly applies to 22:00-23:59 and 00:00-01:59
And a booking for 23:00-01:00 is charged 800,000 VND

AC-15: Permissions
Given I am logged in as front-desk staff
When I access the pricing configuration screen
Then I can only view rules; Create/Edit/Delete buttons are hidden or disabled
Group 4 — Editing & Deleting Rules
gherkin
AC-16: Deleting a rule reverts price to the default
Given a peak rule of 500,000 VND/hour exists for 17:00-20:00 and the default price is 300,000 VND/hour
When I delete that peak rule
Then new bookings for 17:00-20:00 are charged 300,000 VND/hour
And the booking calendar again shows 300,000 VND/hour for this block

AC-17: Confirmed bookings are unaffected when a rule is deleted
Given customer A has a confirmed booking for 18:00-19:00 at 500,000 VND
When I delete the peak rule
Then customer A's booking still shows 500,000 VND
And the invoice/receipt for this booking is unchanged

AC-18: Confirmed bookings are unaffected when a rule is edited
Given customer A has a confirmed booking for 18:00-19:00 at 500,000 VND
When I change the peak rule to 600,000 VND/hour
Then customer A's booking remains 500,000 VND
And bookings created after this change are charged 600,000 VND/hour

AC-19: Warning when editing/deleting a rule with pending bookings
Given there are 3 bookings in "pending confirmation" status within 17:00-20:00
When I delete the peak rule
Then the system shows a warning: "3 pending bookings fall within this time block. Their price will be recalculated using the default rate."
And I must confirm before the action is executed

AC-20: Soft delete and audit trail
Given I have deleted a pricing rule
When an admin views the pricing change history
Then the deleted rule still appears in the log with who deleted it and when
And past bookings can still be traced back to the rule that priced them
Group 5 — Customer-Facing Display
gherkin
AC-21: Prices shown on the booking calendar
Given multiple price tiers exist across the day
When a customer views the booking calendar
Then each slot shows its corresponding per-hour price
And peak slots are visually distinguished (color or "Peak hour" label)

AC-22: Price breakdown shown before checkout
Given a customer selects a time block spanning multiple price tiers
When the customer reaches the booking confirmation step
Then the system displays a breakdown of each price segment plus the total
And a single total figure is never shown without this breakdown
Proposed Data Model
sql
CREATE TABLE pricing_rule (
id UUID PRIMARY KEY,
venue_id UUID NOT NULL REFERENCES venue(id),
resource_id UUID NULL REFERENCES resource(id), -- NULL = applies to whole venue
name VARCHAR(100), -- "Weekday evening peak"
days_of_week SMALLINT[] NOT NULL, -- {1,2,3,4,5}
start_time TIME NOT NULL,
end_time TIME NOT NULL,
price_per_hour BIGINT NOT NULL, -- VND, integer
effective_from DATE NULL,
effective_to DATE NULL,
priority SMALLINT NOT NULL DEFAULT 0,
is_active BOOLEAN NOT NULL DEFAULT TRUE,
created_by UUID NOT NULL,
created_at TIMESTAMPTZ NOT NULL,
updated_at TIMESTAMPTZ NOT NULL,
deleted_at TIMESTAMPTZ NULL
);

The booking table needs these additions:

sql
price_total BIGINT NOT NULL, -- locked-in price, snapshotted
price_breakdown JSONB NOT NULL, -- per-segment detail + rule_id applied
priced_at TIMESTAMPTZ NOT NULL

Pricing algorithm: split the requested interval at every boundary of active rules → for each segment, select the matching rule with the highest priority (resource-level before venue-level) → if none match, fall back to the default price → multiply by hours and sum → round per BR-06.

Non-Functional Requirements
Pricing API response time under 200ms at p95
Price calculation must be deterministic: same input always yields the same output
Fixed timezone Asia/Ho_Chi_Minh, stored in the venue's local time
Support at least 50 pricing rules per venue without performance degradation
Definition of Done
AC-01 through AC-22 all pass
Unit tests for the pricing engine reach ≥ 90% coverage, including boundary and midnight-crossing cases
Integration tests for a booking flow spanning multiple price tiers
DB migration and rollback script tested
API documentation updated
Demoed with at least one real venue owner, feedback captured
Audit logging works correctly for create, edit, and delete
