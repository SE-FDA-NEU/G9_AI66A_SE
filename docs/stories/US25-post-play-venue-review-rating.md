# US25 - Post-Play Venue Review & Rating

- **Issue:** #25
- **Priority:** <P0 | P1 | P2>
- **Points:** 3
- **Owner:** @htngochan2802
- **Screen:** <venue review / venue detail>

## User story

As a **customer**, I want to **leave a review and rating for a venue after playing**, so that **I can share my experience with others**.

---

## Business context

Booking demand and customer experience can vary between venues. Allowing customers who have completed a booking to leave ratings and reviews provides feedback to other customers and helps venues understand customer experience.

The review system must ensure that only eligible customers can review a venue, prevent duplicate reviews, support moderation and reporting, and allow venue owners to respond to customer feedback.

---

## Confirmed policy decisions

| Item                          | Decision                                                                                          |
| ----------------------------- | ------------------------------------------------------------------------------------------------- |
| Eligibility to review         | Booking status `completed`, past `end_time`, payment successful                                   |
| Time window to review         | Unlimited                                                                                         |
| Edit window after posting     | Free, unlocked                                                                                    |
| Rating/comment editing policy | Rating and comment follow the same edit policy                                                    |
| Moderation                    | Automated filtering for sensitive keywords, phone numbers and emails, plus post-publish reporting |
| Public owner reply            | Yes, with no time limit                                                                           |
| Experience date               | Display the actual booking experience date                                                        |
| Edit history                  | Stored internally and never shown publicly                                                        |

---

## Scope

### In scope

- Submitting a review with rating and optional comment
- Linking a review to a completed booking
- Public display of reviews on the venue page
- Editing a review after posting
- Public venue owner reply
- Automated content filtering
- User reporting
- Updating the venue's aggregate rating
- Review moderation and hiding

### Out of scope

- Full manual pre-moderation of all reviews
- Review photos/videos
- Multi-turn customer/venue discussions
- Multi-criteria ratings such as cleanliness, price or staff attitude

---

## Business rules liên quan

| ID    | Rule                                          | Value / constraint                                                                        |
| ----- | --------------------------------------------- | ----------------------------------------------------------------------------------------- |
| BR-01 | Rating is required                            | Integer from 1–5 stars; comment optional, maximum 1000 characters                         |
| BR-02 | One review per completed booking              | Enforced with `UNIQUE(booking_id)`                                                        |
| BR-03 | Ineligible bookings cannot be reviewed        | `cancelled`, `no_show`, `pending`, and `refunded` bookings are not eligible               |
| BR-04 | Venue-cancelled bookings may receive feedback | Tagged "Cancelled by venue" and excluded from the average rating                          |
| BR-05 | Personal contact information is filtered      | Phone numbers and emails are automatically masked/flagged                                 |
| BR-06 | Blocklisted keywords require moderation       | Review enters manual moderation queue and is not auto-published                           |
| BR-07 | Report threshold                              | A review receiving 3 valid reports is automatically hidden pending admin review           |
| BR-08 | Reviews can be edited freely                  | No time or edit-count limit                                                               |
| BR-09 | Edit history is internal                      | Old value, new value and timestamp are logged                                             |
| BR-10 | Experience date is displayed publicly         | Uses `booking.end_time`, not post/edit date                                               |
| BR-11 | One owner reply per review                    | Owner may edit their own reply but cannot edit/delete customer reviews                    |
| BR-12 | Owners cannot review their own venue          | System blocks the action                                                                  |
| BR-13 | Average rating calculation                    | Mean of eligible published reviews, excluding venue-cancelled, hidden and pending reviews |

---

## Acceptance Criteria

### Group 1 — Review Submission Eligibility

gherkin

#### AC-01: Successfully submit a review after completing a booking

Given I have a completed booking (status = completed, past end_time, payment successful)
When I submit a 5-star rating with a comment
Then the review is saved and linked to that booking
And the review is publicly visible on the venue page immediately (unless auto-blocked by filtering)

#### AC-02: Block review if I've never booked the venue

Given I have no booking at this venue
When I attempt to submit a review
Then the system blocks it and displays "You need to complete a booking at this venue to leave a review"

#### AC-03: Block review for an incomplete booking

Given I have an upcoming booking (end_time hasn't passed yet)
When I attempt to submit a review
Then the system blocks it and displays "You can review after your session ends"

#### AC-04: Block review for a booking cancelled by the customer or marked no-show

Given my booking has status cancelled or no_show due to my absence
When I attempt to submit a review
Then the system blocks submission for this booking

#### AC-05: Allow feedback when the venue cancels the booking

Given the venue proactively cancelled my booking
When I submit a rating and comment
Then the feedback is saved and shown publicly tagged "Cancelled by venue"
And this rating is excluded from the venue's average rating

#### AC-06: Block duplicate reviews for the same booking

Given I have already submitted a review for a booking
When I attempt to submit another review for the same booking
Then the system blocks it and offers to edit my existing review instead

### Group 2 — Editing Reviews

gherkin

#### AC-07: Edit a review at any time

Given I submitted a review 8 months ago
When I open that review to edit the rating and/or comment
Then the system allows the edit, with no time limit or edit-count limit

#### AC-08: Public display date doesn't change after editing

Given I edit the content of a posted review
When the review is updated
Then the date shown publicly on the venue page remains the original experience date (booking.end_time), not the edit date

#### AC-09: Edit history is stored internally, never public

Given I change a rating from 2 stars to 5 stars
When the change is saved
Then the system logs it internally (old value, new value, timestamp of edit)
And this log is never exposed to customers or on the public venue page

#### AC-10: Average rating updates immediately when a review is edited

Given the venue has an average rating based on its current reviews
When a customer edits their rating
Then the venue's average rating recalculates immediately to reflect the new value

### Group 3 — Moderation

gherkin

#### AC-11: Automatically mask phone numbers/emails in comments

Given my comment contains a phone number or email address
When I submit the review
Then the system automatically masks/redacts that information before public display
And the review is still published with the rest of the content intact

#### AC-12: Reviews with sensitive keywords go into a moderation queue

Given my comment contains a word on the blocked keyword list
When I submit the review
Then the review is not shown publicly right away
And the review is placed in a manual moderation queue for admin review

#### AC-13: Report an inappropriate review

Given I see a review with inappropriate content
When I report that review
Then the report is recorded against that review

#### AC-14: Auto-hide once the report threshold is reached

Given a review has received 3 valid reports
When the 3rd report is recorded
Then the review is automatically hidden from the public page
And the review moves into a queue for admin review

#### AC-15: Admin restores a review wrongly hidden by reports

Given a review is currently hidden due to reaching the report threshold
When an admin reviews it and determines the reports were invalid
Then the admin can restore the review to public visibility

### Group 4 — Venue Owner Reply

gherkin

#### AC-16: Venue owner publicly replies to a review

Given there is a public review on my venue's page
When I (the venue owner) write a reply to that review
Then the reply appears publicly directly under the review, tagged "Reply from venue"

#### AC-17: Venue owner can only reply once per review

Given I have already replied to a review
When I attempt to submit another reply to the same review
Then the system blocks it and only allows me to edit my existing reply

#### AC-18: Venue owner can edit their own reply with no time limit

Given I replied to a review 5 months ago
When I edit the content of that reply
Then the system allows the edit and updates it immediately

#### AC-19: Venue owner cannot edit or delete a customer's review

Given I am a venue owner viewing a review
Then I have no permission to edit or delete that review's content
And I can only report the review through the normal reporting mechanism

#### AC-20: Block venue owners from reviewing their own venue

Given I am the owner of Venue X
When I attempt to submit a review for Venue X
Then the system blocks it and displays "You cannot review your own venue"

### Group 5 — Display & Aggregate Rating

gherkin

#### AC-21: Show the experience date clearly on each review

Given a review is displayed on the venue page
Then the review shows the actual experience date (the booking's end date), not the post date or edit date

#### AC-22: Sort/filter reviews by recency

Given the venue page has reviews spanning multiple years
When I select "Newest first"
Then the review list sorts by experience date in descending order

#### AC-23: Average rating excludes hidden/pending reviews

Given a venue has 10 public reviews, 1 review hidden due to reports, and 1 review pending moderation
When the average rating is calculated
Then only the 10 public reviews are included in the average

## Proposed Data Model

sql
CREATE TABLE review (
id UUID PRIMARY KEY,
booking_id UUID NOT NULL UNIQUE REFERENCES booking(id),
customer_id UUID NOT NULL REFERENCES customer(id),
venue_id UUID NOT NULL REFERENCES venue(id),
rating SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
comment VARCHAR(1000),
is_venue_cancelled BOOLEAN NOT NULL DEFAULT FALSE, -- BR-04: excluded from average rating
status VARCHAR(20) NOT NULL DEFAULT 'published',
-- published | pending_moderation | hidden_by_report | removed
report_count INT NOT NULL DEFAULT 0,
experience_date TIMESTAMPTZ NOT NULL, -- = booking.end_time, used for display & sort
owner_reply VARCHAR(1000),
owner_reply_at TIMESTAMPTZ,
created_at TIMESTAMPTZ NOT NULL,
updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE review_edit_log ( -- internal only, never public — mitigation for "free editing"
id UUID PRIMARY KEY,
review_id UUID NOT NULL REFERENCES review(id),
field_changed VARCHAR(20), -- 'rating' | 'comment'
old_value TEXT,
new_value TEXT,
edited_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE review_report (
id UUID PRIMARY KEY,
review_id UUID NOT NULL REFERENCES review(id),
reported_by UUID NOT NULL,
reason VARCHAR(200),
created_at TIMESTAMPTZ NOT NULL
);

### Average rating calculation: AVG(rating) WHERE status = 'published' AND is_venue_cancelled = FALSE, recalculated (or cached + invalidated) whenever a review is created, edited, or its status changes.

## Definition of Done

AC-01 through AC-23 pass
UNIQUE(booking_id) constraint tested to confirm duplicate reviews are blocked at the DB layer, not just the app layer
Keyword/phone/email filter has unit tests covering edge cases (spaced-out phone numbers, emails written as "abc [at] gmail")
Average rating updates correctly and consistently across create/edit/hide operations
review_edit_log is not exposed through any public API
Demoed with at least one real venue owner to validate the reply UX

## Known & Accepted Risks

Risk Severity Notes
Venue owners may pressure customers to change their rating at any time (due to free, unlocked editing) Medium–High Mitigated via the internal review_edit_log, which can surface unusual patterns (e.g. multiple reviews changing stars in a short window)
Old reviews (years old) may no longer reflect current venue quality Medium Mitigated by showing the experience date and allowing sort-by-recency
Keyword blocklist may both over- and under-catch (false positives/negatives) Low–Medium Requires periodic review of the keyword list post-launch, based on actual report data
