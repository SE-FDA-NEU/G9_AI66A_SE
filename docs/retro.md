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

---

## Sprint 3 - 05/10/2026 to 18/10/2026

**Velocity:** 32 points completed of 32 committed.

| Keep | Stop | Try |
|------|------|-----|
| One issue per P0 story, each with its own tests - 88 tests by the end of the sprint | Waiting for the previous PR to merge before starting - #67, #68 and #69 queued behind each other | Start the next story on a branch from the open PR's branch, and rebase when it merges |
| `BusinessRuleError` - one place that turns a broken rule into the message on screen | Writing error messages after the code - three messages were changed during review | Write the exact message in the issue before writing the code |

**Action for Sprint 4 (owner: @lequangk2006-sys):** as the next Scrum Master, check on
Wednesday of each week that every open PR has a reviewer who has replied, and reassign the
review if not. Checked at the Sprint 4 retrospective.

---

## Sprint 4 - 19/10/2026 to 01/11/2026

**Velocity:** 25 points completed of 25 committed (five planned testing/documentation
issues at 5 points each, all closed with merged Pull Requests).

| Keep | Stop | Try |
|------|------|-----|
| Give each P0 story normal, error and boundary tests with traceable TC IDs; the PR #96 review recognized the risk-based coverage | Day-wide queries for slot-level booking uniqueness; dynamic seed data made the assertion flaky until PR #92 narrowed it to the exact slot | Refresh the documented full-suite result whenever test work is merged; the original 89-test output in `docs/testing.md` was no longer current after Sprint 4 additions |
| Use teammate reviews to challenge test assumptions; PR #95 asked whether owner venue listing should require email verification | Leaving test documentation's full-suite count stale as new cases are added | Keep the current `python -m pytest -q` result visible in both `docs/testing.md` and `docs/SETUP.md` |

**Action for Sprint 5 (owner: @lequangk2006-sys):** after each test-focused merge, rerun
the full suite and update the expected test count in `docs/testing.md` and `docs/SETUP.md`.
Check that both documents match the test run at the Sprint 5 retrospective.

**Sprint 3 action checked:** The five planned issue Pull Requests received reviews, but
the repository does not record the Wednesday checks or any reviewer reassignments;
completion of that specific action cannot be confirmed.

---

## Sprint 5 - 02/11/2026 to 15/11/2026

**Velocity:** 21 points completed of 21 committed (issues #101, #104, #105, #106 and chores #103, #107).

| Keep | Stop | Try |
|------|------|-----|
| Automated deployment verification in CI before auto-deploying to Vercel/Neon; catches configuration mismatches before production traffic hits them | Relying on local SQLite assumptions when deploying to PostgreSQL; schema compatibility adapters are essential for serverless hosts | Continuous end-to-end smoke testing against the live production URL as part of the PR definition of done |
| Instant platform rollback via Vercel deployments tab; enables recovery in under 30 seconds without code changes | Manual database migrations during sprint deadlines; automated idempotency in `pg_schema.py` and `init_db.py` saves hours | Maintain persistent staging environment mirroring production database configurations |

**Sprint 4 action checked:** Test counts updated to 268 passed tests across `docs/testing.md` and `docs/SETUP.md`. Verified at the Sprint 5 retrospective.

---

## Final Retrospective - What We Would Keep for Our Next Team

Reflections from the entire 15-week Software Engineering project (Milestones 1 through 5):

1. **One Issue = One Branch = One PR:**
   - Keeping PR scopes small and linked directly to a numbered GitHub issue prevented massive merge conflicts and made code reviews swift and thorough. We will use this convention on every future project.
2. **Explicit Business Rules Catalog (`BR1`–`BR19`):**
   - Having unambiguous, testable business rules established in Sprint 1 served as the north star for database schema design, UI error messages, and automated pytest assertions.
3. **Automated Subagent Review & CI Guardrails:**
   - Pairing peer code review with automated CI scans (detect stack, pytest coverage, secret scanning, credential guards) caught subtle edge cases and zero-leak security violations before code reached `main`.
4. **Decoupled Architecture for Cloud Deployment:**
   - Moving from SQLite to database-compatible abstraction (`db_compat.py`) and Cloudinary media storage allowed our Flask backend to run seamlessly in serverless environments without persistent local disks.
