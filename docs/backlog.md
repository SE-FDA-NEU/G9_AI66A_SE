# Product Backlog - Sprint 1

Agreed at the Backlog Refinement meeting (issue #12). Product Owner: @thunopro.

Scale: Fibonacci (1, 2, 3, 5, 8, 13). Points are **relative complexity**, not hours.

Priority: **P0** = the product is meaningless without it · **P1** = should have ·
**P2** = nice to have.

## Sprint 1 backlog

| Issue | Story | Priority | Points | Owner |
|-------|-------|----------|--------|-------|
| #14 | Customer registration | P0 | 3 | @thunopro |
| #15 | User login | P0 | 3 | @thunopro |
| #16 | Customer searches for venues | P0 | 5 | @peng543 |
| #17 | Customer views venue details and availability | P0 | 5 | @peng543 |
| #18 | Customer books a venue | P0 | 8 | @peng543 |
| #21 | Venue owner adds a new venue | P0 | 5 | @PhunghoaAI |
| #19 | Customer cancels a booking | P1 | 3 | @PhunghoaAI |
| #20 | Customer views booking history | P1 | 3 | @PhunghoaAI |
| #22 | Venue owner manages venue availability schedule | P1 | 5 | @lequangk2006-sys |
| #23 | Venue owner views list of bookings | P1 | 3 | @lequangk2006-sys |
| #24 | Venue owner sets peak-hour pricing | P2 | 5 | @htngochan2802 |
| #25 | Customer leaves a review and rating | P2 | 3 | @htngochan2802 |

**Total: 51 points · 6 stories at P0** (the brief asks for 4-6).

## Why these priorities

- **#14 through #18 are the shortest path to a customer actually booking a pitch.** Drop
  any one of them and nobody can book anything, so all five are P0.
- **#21 is P0** because with no venues in the system there is nothing to search for and
  nothing to book. It is the precondition that makes #16, #17 and #18 meaningful.
- **#19, #20, #22 and #23 are P1.** The system still works if cancelling means phoning
  the owner and the owner checks the schedule by hand - it is merely unpleasant, not
  fatal.
- **#24 and #25 are P2.** Peak-hour pricing and reviews make the product better; they are
  not what makes it work.

## Why these estimates

| Points | Stories | Reason |
|--------|---------|--------|
| 3 | #14, #15, #19, #20, #23, #25 | One form or one list, simple rules, little state |
| 5 | #16, #17, #21, #22, #24 | Conditional queries, or managing a schedule of time slots |
| 8 | #18 | The hardest piece: checking availability, preventing double-booking, calculating the price, confirming |

## Note on velocity

Sprint 1 is a **requirements sprint**: the deliverable is `docs/requirements.md`, not
running software. The points in the table above are therefore an **estimate used to plan
Sprints 2-3**, and Sprint 1 records `Committed 0 · Completed 0 · Velocity: not
applicable` in `docs/sprint-log.md`.
