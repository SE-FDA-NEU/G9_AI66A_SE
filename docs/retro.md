# Retrospectives

One section per sprint, written at the retrospective and merged through a Pull Request.
A retro that produces no action item is a complaint session - exactly one action, one
owner, checked at the next retro.

---

## Sprint 1 - 08/09/2026 to 20/09/2026

**Velocity:** not applicable (requirements sprint - the deliverable was
`docs/requirements.md`, not running software).

| Keep | Stop | Try |
|------|------|-----|
| One file per story in `docs/stories/` - no documentation merge conflict all sprint | Approving with the single word "ok" - the brief says such a review earns no marks | Every review raises at least one question or change request, pointed at a line |
| `scrum-check.yml` catching PRs with no linked issue immediately | Leaving the work to the last two days - 9 of 12 stories merged on 20/09 | Internal deadline two days before the real one; PO checks on Thursday of week 6 |
| Numbering business rules and citing them inside acceptance criteria | Everyone numbering their rules from BR1 inside their own file | PO hands out a business-rule range to each member at planning |
| One issue, one branch, one Pull Request | Taking a story and going quiet for a week | Short stand-up in `docs/daily.md` on Wednesday |

**Action for Sprint 2 (owner: @thunopro):** hand out a business-rule range to each member
at Sprint 2 Planning (e.g. @peng543 BR20-29, @PhunghoaAI BR30-39), and require every
review to carry at least one question or change request. Checked at the Sprint 2 retro.

**Also carried into Sprint 2 from the course rules:**

- Branch names must follow `<issue-number>-<short-description>`, not `feature/<n>-...`
- The board `Status` field needs an `In Review` option (exact spelling) between
  `In Progress` and `Done`
- `.github/workflows/board-in-review.yml` is missing from the repository
- The Scrum Master rotates each sprint; the Product Owner stays constant

---

## Sprint 2 - 21/09/2026 to 04/10/2026

**Velocity:** 22 points completed of 22 committed.

| Keep | Stop | Try |
|------|------|-----|
| Using CI and automated checks to catch PR issues early (scrum-check.yml caught missing issue links immediately) | Working in isolation without daily standups (some PRs had no activity for days, then all merged on the last day) | Daily standup messages in the group chat every Wednesday so anyone who is stuck says so in time to reassign |

**Action for Sprint 3 (owner: @PhunghoaAI):** as the new Scrum Master, post a short
Wednesday standup prompt in the group chat every week of Sprint 3, and ensure every
PR receives a review with at least one specific question or change request within 24 hours
of opening. Checked at the Sprint 3 retrospective.
