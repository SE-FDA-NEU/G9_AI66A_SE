# Sprint log

One section per sprint. Fill it in **during** the sprint, not the night before the
milestone deadline - the commit timestamps on this file are part of the evidence that
the process was real.

---

## Sprint 1 - 08/09/2026 to 20/09/2026

<!-- Sprint 1: weeks 5-6 | Sprint 2: 7-8 | Sprint 3: 9-10 | Sprint 4: 11-12 | Sprint 5: 13-14 -->

### Sprint goal

The team agrees on what the product is: all 12 user stories carry acceptance criteria
that can be checked against a number, and the business rules are fixed so Sprint 2 can
design against them and Sprint 4 can test against them.

### Committed

Sprint 1 is a **requirements sprint**: the deliverable is `docs/requirements.md`, not
running software. No story was *implemented* in this sprint, so **committed = 0 points**.

The table below is the **estimate used to plan Sprints 2-3**, agreed at the Backlog
Refinement meeting (issue #12). Prioritisation reasoning and estimation notes:
`docs/backlog.md`.

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

**Total committed: 0 points** - the 51 points above are an estimate for later sprints,
not a Sprint 1 commitment.

### Result

What the team actually produced in Sprint 1 was the **specification** of those 12
stories: one file per story in `docs/stories/`, one branch and one Pull Request per file.

| Issue | Points | Status | If not done, why |
|-------|--------|--------|------------------|
| #12 [Chore] Refine backlog | - | Done - PR #26 | |
| #14 Customer registration | 3 | Specified - PR #27 | |
| #15 User login | 3 | Specified - PR #39 | |
| #16 Customer searches for venues | 5 | Specified - PR #30 | |
| #17 Customer views venue details | 5 | Specified - PR #31 | |
| #18 Customer books a venue | 8 | Specified - PR #29 | |
| #19 Customer cancels a booking | 3 | Specified - PR #36 | |
| #20 Customer views booking history | 3 | Specified - PR #35 | |
| #21 Venue owner adds a new venue | 5 | Specified - PR #32 | |
| #22 Venue owner manages availability | 5 | Specified - PR #37 | Owner unavailable in week 6; the PO wrote it instead so Milestone 1 would not slip. See the retrospective. |
| #23 Venue owner views list of bookings | 3 | Specified - PR #38 | As above. |
| #24 Venue owner sets peak-hour pricing | 5 | Specified - PR #28 | |
| #25 Customer leaves a review and rating | 3 | Specified - PR #33 | |
| #13 [Chore] Sprint 1 wrap-up | - | Done - PR #40 | |

**Completed: 0 points. Velocity this sprint: not applicable (requirements sprint).**

The first measurable velocity will be Sprint 3, when the team starts delivering running
software.

**Not finished: none.** All 12 stories were specified and merged into `main` before the
deadline, and every Sprint 1 issue is closed with a linked Pull Request.

### Sprint Review

- **What we demonstrated:** `docs/requirements.md` with all six required sections - 3
  personas, 2 scenarios, 12 user stories carrying 50 acceptance criteria, BR1-BR19, and
  14 screens with a flow diagram; 12 GitHub issues labelled `story`, each with acceptance
  criteria in its body; a project board with every Sprint 1 issue assigned to the
  `Sprint 1 (weeks 5-6)` milestone; `docs/backlog.md` with priorities and story points
  and the reasoning behind both.
- **Feedback received:** Automated review caught 8 genuine defects across PRs #26, #27
  and #30, including one factual error: `sanbong2026` was described as 12 characters when
  it is 11. Fixed in commit `c50cdfc` before merge. A reviewer inside the team pointed out
  that US03 declared `Screen: /venue` while its acceptance criteria used `/venues/{id}`;
  this was settled as `/venues/{id}` when `docs/requirements.md` was assembled.
- **Backlog changes as a result:** Writing the specification surfaced three constraints
  the refinement meeting had not considered - a failed sign-in message must not reveal
  whether an email exists (BR6), an owner must not be able to block a slot that already
  holds a booking (BR17), and a booking crossing a pricing boundary must be split per
  segment rather than rounded up (BR12). All three became business rules rather than new
  stories, so the point total did not change.

### Retrospective

| Keep doing | Stop doing | Start doing |
|------------|------------|-------------|
| One file per story in `docs/stories/` - the whole sprint passed without a single documentation merge conflict | Approving with the single word "ok". The brief states plainly that such a review **earns no marks** | Every review must raise at least one specific question or change request, pointed at a line |
| Using `.github/workflows/scrum-check.yml` to catch PRs with no linked issue immediately | Leaving the work to the last two days - 9 of 12 stories were merged on 20/09 | Set an internal deadline two days before the real one; the PO checks on the Thursday of week 6 |
| Numbering business rules and citing them inside the acceptance criteria | Letting everyone number their rules from BR1 inside their own file | The PO hands out a business-rule range to each member at planning |
| One issue, one branch, one Pull Request - clean traceability from issue to commit | Taking a story and then going quiet for a week | A short stand-up in the group chat on Wednesday, so anyone stuck says so in time to reassign |

**One concrete action for next sprint (with an owner):**

@thunopro (PO) will hand out a business-rule range to each member at Sprint 2 Planning
(for example @peng543 uses BR20-29, @PhunghoaAI uses BR30-39), and every review must
carry at least one question or change request. Checked at the Sprint 2 retrospective.

<!-- Why this action and not another: in Sprint 1 four stories all claimed BR1-BR5, so
     assembling requirements.md meant renumbering every rule by hand - slow, error-prone,
     and entirely avoidable by handing out ranges up front. -->

### Attendance

| Member | Planning | Review | Retro |
|--------|----------|--------|-------|
| @thunopro | x | x | x |
| @peng543 | x | x | x |
| @PhunghoaAI | x | x | x |
| @lequangk2006-sys | x | | |
| @htngochan2802 | x | x | x |

### SM Sprint 2

@peng543  <!-- SM rotates each sprint; the PO (@thunopro) stays constant -->

---

## Sprint 2 - 21/09/2026 to 04/10/2026

### Sprint goal

A new machine can clone the repository, follow `docs/SETUP.md`, and see a list of real
venues read from a real database at `/search` - and `docs/design.md` explains how every
later story will be built on top of it.

### Committed

Agreed at Sprint 2 Planning (#42). Details and reasoning: `docs/backlog.md`.

| Issue | Work | Points | Owner |
|-------|------|--------|-------|
| #43 | Set up Flask project skeleton and CI tests | 3 | @peng543 |
| #44 | Create database schema, ERD and seed 24 venues | 5 | @thunopro |
| #45 | Walking skeleton: /search reads venues from the database | 3 | @peng543 |
| #46 | Design doc: architecture diagram and design decisions | 3 | @htngochan2802 |
| #47 | Design doc: API design | 3 | @htngochan2802 |
| #48 | Write docs/SETUP.md and test it on a clean machine | 2 | @PhunghoaAI |
| #49 | Traceability: Story, Screen, Endpoint, Table | 1 | @lequangk2006-sys |
| #50 | Design doc: what changed since M1 and Milestone 2 submission | 2 | @thunopro |

**Total committed: 22 points.** Chores #42 and #51 carry no points.

### Result

| Issue | Points | Status | PR | If not done, why |
|-------|--------|--------|----|------------------|
| #42 [Chore] Refine backlog | - | Done | #52 | |
| #43 | 3 | Done | #53 | |
| #44 | 5 | Done | #54 | |
| #45 | 3 | Done | #56 | |
| #46 | 3 | Done | #55 | |
| #47 | 3 | Done | #59 | |
| #48 | 2 | Done | #57 | |
| #49 | 1 | Done | #61 | |
| #50 | 2 | Done | #60 | |
| #51 [Chore] Sprint 2 wrap-up | - | Done | this PR | |

**Completed: 22 points. Velocity: 22 points** (sum of the Points of every issue that is
Done on the board; an issue that is not merged counts 0 and is labelled `carried-over`).

### Sprint Review

- **What we demonstrated:** The `/search` page running from a fresh clone (following `docs/SETUP.md`), the full `docs/design.md` with all six sections (architecture, data model, API design, walking skeleton, design decisions, what changed since M1), and the ERD showing all seven tables.
- **Feedback received:** No feedback from the instructor yet; Milestone 1 feedback has not been returned. Inside the team, the review on #59 found leftover merge-conflict markers and a duplicated section 1 in docs/design.md; they were fixed before approval.
- **Backlog changes as a result:** No new issues added. #59 (#47) needed one round of changes - unresolved merge conflicts in docs/design.md - and was merged on 04/10, before the deadline.

### Retrospective

Full notes in `docs/retro.md`.

**Sprint 1 action checked:** business-rule ranges were handed out at planning (see
`docs/backlog.md`); every review carried at least one question or change request -
partially: most reviews raised specific questions (e.g. PR #56 review asked about the
`connect()` context-manager and the bound parameters in `SEARCH_SQL`), but not every
review did. The action carries over to Sprint 3.

### Attendance

| Member | Planning | Review | Retro |
|--------|----------|--------|-------|
| @thunopro | x | x | x |
| @peng543 | x | x | x |
| @PhunghoaAI | x | x | x |
| @lequangk2006-sys | x | x | x |
| @htngochan2802 | x | x | x |

### SM Sprint 3

@PhunghoaAI  <!-- SM rotates each sprint; the PO (@thunopro) stays constant -->

---

## Sprint 3 - 05/10/2026 to 18/10/2026

### Sprint goal

A person who has never seen the app can complete every P0 story (US01-US06) through the
interface, with real data from the database, and every broken business rule shows a
clear message on screen.

### Committed

Agreed at Sprint 3 Planning (#63). Details and reasoning: `docs/backlog.md`.

| Issue | Work | Points | Owner |
|-------|------|--------|-------|
| #64 | US02 User login: role routing, lockout and session timeout | 3 | @peng543 |
| #65 | US01 Customer registration with email verification | 3 | @htngochan2802 |
| #66 | US03 Search from fixed lists and narrowing while typing | 2 | @PhunghoaAI |
| #67 | US04 Venue detail page with availability for a chosen date | 5 | @peng543 |
| #68 | US05 Book a venue with per-segment pricing | 8 | @thunopro |
| #69 | US06 Owner adds a venue and sees their venue list | 5 | @htngochan2802 |
| #70 | docs/ui.md sections 1-3 | 3 | @lequangk2006-sys |
| #71 | docs/ui.md section 4 and design.md update | 2 | @thunopro |
| #72 | README first screen, SETUP.md test accounts and re-test | 1 | @PhunghoaAI |

**Total committed: 32 points.** Chores #63 and #73 carry no points.

### Result

| Issue | Points | Status | PR | If not done, why |
|-------|--------|--------|----|------------------|
| #63 [Chore] Refine backlog | - | Done | #74 | |
| #64 | 3 | Done | #76 | |
| #65 | 3 | Done | #79 | |
| #66 | 2 | Done | #77 | |
| #67 | 5 | Done | #80 | |
| #68 | 8 | Done | #75 | |
| #69 | 5 | Done | #81 | |
| #70 | 3 | Done | #83 | |
| #71 | 2 | Done | #78 | |
| #72 | 1 | Done | #82 | |
| #73 [Chore] Sprint 3 wrap-up | - | Done | this PR | |

**Completed: 32 points. Velocity: 32 points** (sum of the Points of every issue that is
Done on the board; an issue that is not merged counts 0 and is labelled `carried-over`).
Sprint 2 velocity was 22; Sprint 3 committed more because the P0 stories were already
specified in Sprint 1 and the walking skeleton was in place.

### Sprint Review

- **What we demonstrated:** a clean clone following `docs/SETUP.md`; then, through the
  interface only, searching for a venue, opening it, booking 19:00-21:00 across a peak
  boundary (two price lines), registering and verifying a new account, and an owner adding
  a venue. Rules broken on purpose: a 3-hour booking from 21:00, a price of `0`, an
  unverified account trying to book.
- **Feedback received:** No feedback from the instructor yet (Milestone 1 and Milestone 2 feedback have not been returned). Inside the team, PR reviews caught leftover merge-conflict markers in templates (#65), a duplicate route stub in `src/routes/owner.py` (#69), and checked how static requests interact with session timeout (#64) and how uploaded photo filenames are handled (#69); all issues were fixed before merge.
- **Backlog changes as a result:** No new P0 issues added. Sprint 4 will pick up the P1 stories already in `docs/backlog.md`: US07 cancel a booking (#19), US08 booking history (#20), US09 owner blocks slots for maintenance (#22), and US10 owner views bookings (#23).

### Retrospective

Full notes in `docs/retro.md`.

**Sprint 2 action checked:** Wednesday standup prompts were posted in the group chat each
week of Sprint 3, and every Pull Request received a review with at least one specific
question or change request pointed at a concrete line before approval.

### Attendance

| Member | Planning | Review | Retro |
|--------|----------|--------|-------|
| @thunopro | x | x | x |
| @peng543 | x | x | x |
| @PhunghoaAI | x | x | x |
| @lequangk2006-sys | x | x | x |
| @htngochan2802 | x | x | x |

### SM Sprint 4

@lequangk2006-sys

---

## Sprint 4 - 19/10/2026 to 01/11/2026

### Sprint goal

Build automated normal, error and boundary coverage for every P0 story, fix regressions
found while testing, and document the test strategy and setup for Milestone 4.

### Committed

Planned under Sprint 4 refinement issue #85. The project board assigns 5 points to each
of the five testing and documentation issues below. Chores #85 and #91 carry no points.

| Issue | Work | Points | Owner |
|-------|------|--------|-------|
| #86 | P0 tests for US01 registration and US02 login | 5 | @htngochan2802 |
| #87 | P0 tests for US03 search and US04 venue detail/availability | 5 | @peng543 |
| #88 | Fix date-dependent US05 test and add booking boundary tests | 5 | @thunopro |
| #89 | P0 tests for US06 owner venue management | 5 | @PhunghoaAI |
| #90 | Milestone 4 testing guide and setup instructions | 5 | @lequangk2006-sys |

**Total committed: 25 points.**

### Result

| Issue | Points | Status | PR | If not done, why |
|-------|--------|--------|----|------------------|
| #86 | 5 | Done | #99 | |
| #87 | 5 | Done | #97 | |
| #88 | 5 | Done | #92 | |
| #89 | 5 | Done | #95 | |
| #90 | 5 | Done | #96 | |

**Completed: 25 points. Velocity: 25 points** (all five planned issues are closed and
their linked Pull Requests are merged). The board does not have a Sprint iteration set
for these five issues; their points and scope are recorded in the Sprint 4 work items
under refinement issue #85. Sprint chores carry no points.

PR #94 also delivered the previously specified customer cancellation/history and owner
schedule/booking work (#19, #20, #22, #23), plus peak pricing and reviews (#24, #25).
Those issues have no Sprint 4 point commitments recorded, so they are not included in
the 25-point velocity.

### Sprint Review

- **What we demonstrated:** The test suite currently passes all 253 tests with
  `python -m pytest -q`; automated tests cover normal, error and boundary behavior across
  the P0 stories, and `docs/testing.md` describes the risk-based strategy and how to run
  them.
- **Feedback received:** The review on PR #96 praised the risk-based test strategy and
  the traceability of normal, error and boundary cases. No instructor feedback is
  recorded in the issue or Pull Request history.
- **What the tests found:** PR #92 fixed a date-dependent booking uniqueness test that
  had queried every booking on a day instead of the exact slot under test. The assertion
  now checks the precise slot, avoiding collisions with dynamic seed data.

### Retrospective

Full notes in `docs/retro.md`. The Sprint 3 action asked the Scrum Master to check open
Pull Requests each Wednesday for a reviewer response. The five planned issue Pull
Requests received reviews, but the repository does not record whether the Wednesday
checks or reassignments happened, so that part of the action cannot be verified.

---

## Sprint 5 - 02/11/2026 to 15/11/2026

### Sprint goal

Deploy the complete application to a public, secure `https://` address on Vercel with
managed PostgreSQL and persistent media storage; verify health checks and production error
handling; formalize operational procedures and CI pipeline verification; and prepare the
Week 15 final demonstration and Release v1.0.

### Committed

Planned under Sprint 5 backlog refinement issue #103. Product Owner: @thunopro. Scrum Master: @htngochan2802.

| Issue | Work | Points | Owner | Reviewer |
|-------|------|--------|-------|----------|
| #101 | Modernize commercial web UI, add PostgreSQL compatibility and Cloudinary storage | 8 | @thunopro | @peng543 |
| #103 | [Chore] Refine backlog for Sprint 5 | - | @thunopro | @htngochan2802 |
| #104 | [Ops] Health check resilience and production monitoring tests | 5 | @peng543 | @PhunghoaAI |
| #105 | [CI] Enhance CI pipeline with deployment verification and branch protection audit | 5 | @PhunghoaAI | @lequangk2006-sys |
| #106 | [Docs] Update README first screen with production URL, test accounts, and CI badge | 3 | @lequangk2006-sys | @htngochan2802 |
| #107 | [Chore] Sprint 5 wrap-up: operations guide, five-sprint velocity log, retrospective, and v1.0 release | - | @htngochan2802 | @thunopro |

**Total committed: 21 points.** Chores carry no points.

### Result

| Issue | Points | Status | PR | If not done, why |
|-------|--------|--------|----|------------------|
| #101 | 8 | Done | #102 | |
| #103 | - | Done | - | Backlog refinement chore |
| #104 | 5 | Done | #108 | |
| #105 | 5 | Done | #109 | |
| #106 | 3 | Done | #110 | |
| #107 | - | Done | #111 | Sprint 5 wrap-up chore |

**Completed: 21 points. Velocity: 21 points** (all committed issues resolved with merged PRs).

### Sprint Review

- **What we demonstrated:** The application is live and publicly accessible at
  `https://g9-venue-booking-demo.vercel.app` with real PostgreSQL persistence, Cloudinary
  media storage, and 24 seeded venues. Every P0 story (US01–US06) is fully executable in
  incognito mode by clicking only. The `/health` probe returns 200 OK when operational and
  503 on database drop. All 268 automated tests pass in CI.
- **Feedback received:** Peer review on PR #102 verified the dual English/Vietnamese
  language toggle, responsive grid cards, and session persistence across browser reloads.
- **Operational findings:** Initial serverless cold starts take ~3 seconds on Neon free-tier,
  after which responses execute in under 120ms. Rollback procedures verified using Vercel
  Instant Rollback.

### Retrospective

Full notes in `docs/retro.md`. The Sprint 4 action asked the Scrum Master to update test
counts in `docs/testing.md` and `docs/SETUP.md`. Test count updated from 253 to 268 tests
following the addition of monitoring and deployment verification suites.

---

## All Five Sprints Summary

Summary of team commitments, delivery, and velocity across the entire project semester:

| Sprint | Weeks | Focus / Milestone | Committed | Completed | Velocity | Key Deliverable |
|---|---|---|---|---|---|---|
| **Sprint 1** | Weeks 5–6 | Requirements & User Stories (M1) | 0 | 0 | 0 | `docs/requirements.md`, 12 user story specifications, BR1–BR19 |
| **Sprint 2** | Weeks 7–8 | Architecture & Walking Skeleton (M2) | 23 | 23 | 23 | `docs/design.md`, SQLite schema, walking skeleton, CI setup |
| **Sprint 3** | Weeks 9–10 | UI Implementation & 6 P0 Stories (M3) | 32 | 32 | 32 | `docs/ui.md`, US01–US06 full web interface, 88 tests |
| **Sprint 4** | Weeks 11–12 | Software Testing & Coverage (M4) | 25 | 25 | 25 | `docs/testing.md`, TC-01 to TC-76, 253 automated tests, regression fixes |
| **Sprint 5** | Weeks 13–14 | Deployment, Operations & Release (M5) | 21 | 21 | 21 | `docs/operations.md`, Live URL, CI deployment verification, Release v1.0 |
| **Total** | | **All 5 Milestones Completed** | **101** | **101** | **101** | **Production-ready Sports Venue Booking System** |

