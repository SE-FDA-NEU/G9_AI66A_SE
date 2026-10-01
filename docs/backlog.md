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

---

# Sprint 2 backlog - 21/09/2026 to 04/10/2026

Agreed at Sprint 2 Planning (issue #42). Product Owner: @thunopro. Scrum Master: @peng543.

**Sprint goal:** a new machine can clone the repository, follow `docs/SETUP.md`, and see
a list of real venues read from a real database at `/search` - and `docs/design.md`
explains how every later story will be built on top of it.

Sprint 2 is a **design sprint** (Milestone 2). Its work items are tasks that build the
walking skeleton and the design document, so they are estimated in points on the board
like stories.

| Issue | Work | Points | Owner | Reviewer |
|-------|------|--------|-------|----------|
| #42 | [Chore] Refine backlog for Sprint 2 | - | @thunopro | @peng543 |
| #43 | Set up Flask project skeleton and CI tests | 3 | @peng543 | @thunopro |
| #44 | Create database schema, ERD and seed 24 venues | 5 | @thunopro | @htngochan2802 |
| #45 | Walking skeleton: /search reads venues from the database | 3 | @peng543 | @PhunghoaAI |
| #46 | Design doc: architecture diagram and design decisions | 3 | @htngochan2802 | @lequangk2006-sys |
| #47 | Design doc: API design | 3 | @htngochan2802 | @thunopro |
| #48 | Write docs/SETUP.md and test it on a clean machine | 2 | @PhunghoaAI | @peng543 |
| #49 | Traceability: Story, Screen, Endpoint, Table | 1 | @lequangk2006-sys | @htngochan2802 |
| #50 | Design doc: what changed since M1 and Milestone 2 submission | 2 | @thunopro | @PhunghoaAI |
| #51 | [Chore] Sprint 2 wrap-up | - | @peng543 | @lequangk2006-sys |

**Committed: 22 points.** Chores carry no points.

## Why this order

- **#43 → #44 → #45 is the critical path.** The walking skeleton needs a Flask app (#43)
  and a seeded database (#44) before `/search` (#45) can read from it. `docs/SETUP.md`
  (#48) is written last because it describes what those three produce.
- **#46 and #47 do not depend on code** and start as soon as this issue is merged.
- **#49 waits for #47**, because the traceability table copies endpoint paths from the
  API design.
- **#50 and #51 close the sprint.**

## Why this split

The hardest task (#44: seven tables whose constraints must enforce the business rules)
goes to the member with the most database experience; the next hardest (#43, #45, #46,
#47) to the two members who built most of Sprint 1. The two newest members take small,
well-defined documentation tasks (#48, #49) so every member still has an issue, a pull
request and a review of their own this sprint.

## Business-rule ranges (Sprint 1 retrospective action)

New business rules found in Sprint 2 are numbered from each member's own range, so no
two people ever write the same number:

| Member | Range |
|--------|-------|
| @peng543 | BR20-BR29 |
| @PhunghoaAI | BR30-BR39 |
| @lequangk2006-sys | BR40-BR49 |
| @htngochan2802 | BR50-BR59 |
| @thunopro | BR60-BR69 |
