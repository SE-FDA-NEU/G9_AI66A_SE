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

<!-- TODO @thunopro: check this table against what actually happened before merging. -->

### SM Sprint 2

@peng543  <!-- SM rotates each sprint; the PO (@thunopro) stays constant -->

---

## Sprint 2 - weeks 7-8

<!-- Fill this in during the sprint, not before it. -->
