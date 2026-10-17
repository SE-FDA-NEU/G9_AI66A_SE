# G9_AI66A_SE - Sports Venue Booking System

A time-slot booking platform for amateur sports players in Hanoi: players see which pitch
is free at which hour and reserve it in minutes, instead of messaging venue owners one by
one and waiting for a reply; owners see the whole schedule of every venue they manage on
one screen instead of keeping it in a paper notebook.

## Team

| Name | GitHub username | Role |
| --- | --- | --- |
| Nguyen Khac Thu | [@thunopro](https://github.com/thunopro) | Leader · **Product Owner** |
| Nguyen Khoi Nguyen | [@peng543](https://github.com/peng543) | Developer · Scrum Master (Sprint 2) |
| Hoang Thi Ngoc Han | [@htngochan2802](https://github.com/htngochan2802) | Developer · Scrum Master (Sprint 1) |
| Nguyen Phung Hoa | [@PhunghoaAI](https://github.com/PhunghoaAI) | Developer · **Scrum Master (Sprint 3)** |
| Le Quang | [@lequangk2006-sys](https://github.com/lequangk2006-sys) | Developer |

- **Product Owner:** @thunopro
- **Scrum Master (Sprint 3):** @PhunghoaAI
- Scrum Master (Sprint 2): @peng543
- Scrum Master (Sprint 1): @htngochan2802

## Project board

https://github.com/orgs/SE-FDA-NEU/projects/25

**New machine? Start with [`docs/SETUP.md`](docs/SETUP.md).**

## Core Features & P0 Stories

Every P0 story is implemented and testable in the browser interface:

| Story | What it does | Starting screen | Test account |
|---|---|---|---|
| **US01** Customer registration (#14) | Register account, receive on-screen verification link (BR4) | [`/register`](http://localhost:5000/register) | Guest / New user |
| **US02** User login (#15) | Sign in with role-based routing (customer → `/dashboard`, owner → `/owner/venues`) | [`/login`](http://localhost:5000/login) | Any test account below |
| **US03** Customer searches for venues (#16) | Search & filter venues by sport, district area, or keyword | [`/search`](http://localhost:5000/search) (or `/`) | Guest / Anyone |
| **US04** Customer views venue details (#17) | View venue photos, pricing, amenities, and hourly availability grid | [`/venues/1`](http://localhost:5000/venues/1) | Guest / Anyone |
| **US05** Customer books a venue (#18) | Reserve time slots with segmented pricing & booking code confirmation | [`/booking/1`](http://localhost:5000/booking/1) | `minh@example.com` (Customer) |
| **US06** Venue owner adds a new venue (#21) | View owned venues, manage venue schedule, add a new venue | [`/owner/venues`](http://localhost:5000/owner/venues) | `lan.owner@example.com` (Owner) |

### Test Accounts

All pre-seeded test accounts share the test password **`sanbong1`** (8 characters, letter + digit, enforcing BR2).

| Role | Email | Name | Status / Purpose |
|---|---|---|---|
| Customer (verified) | `minh@example.com` | Pham Duc Minh | Verified customer; holds bookings `BK-000101`, `BK-000103`. Ready to book. |
| Customer (verified) | `trang@example.com` | Do Thu Trang | Verified customer; holds bookings `BK-000102`, `BK-000104`. |
| Customer (unverified) | `khoa@example.com` | Vu Minh Khoa | Unverified customer (`email_verified_at` NULL); verifies BR4 booking refusal. |
| Venue owner | `lan.owner@example.com` | Nguyen Thi Lan | Owns *Thong Nhat Football Pitch*, *Lan Anh Badminton Court*. Lands on `/owner/venues`. |
| Venue owner | `hung.owner@example.com` | Tran Van Hung | Owns *My Dinh Football Pitch*. |
| Venue owner | `son.owner@example.com` | Le Hoang Son | Owns *Chua Boc Badminton Court*. |
| Administrator | `admin@example.com` | Admin | Administrative role (`admin`). |

## Definition of Done

A story is Done when **all** of the following are true. Not "mostly true". If one box is
unticked, the story stays in the sprint and is labelled `carried-over`.

| # | Criterion | Who checks |
|---|-----------|------------|
| 1 | Every acceptance criterion on the issue passes | Reviewer, by hand |
| 2 | The feature works from a clean clone with only the README steps | Reviewer |
| 3 | At least one automated test covers the new behaviour | CI |
| 4 | CI is green on the PR branch | CI |
| 5 | Code reviewed and approved by a teammate who did not write it | GitHub |
| 6 | Merged into `main` | GitHub |
| 7 | No secrets, `.env`, or database dumps in the diff | CI |
| 8 | `docs/traceability.md` updated if a screen or route changed | Reviewer |

Full version, including what Done is **not**:
[`docs/definition-of-done.md`](docs/definition-of-done.md)

## Documentation

| File | Contents |
|------|----------|
| [`docs/requirements.md`](docs/requirements.md) | **Milestone 1** - vision, 3 personas, 2 scenarios, 12 user stories, BR1-BR19, 14 screens and the flow diagram |
| [`docs/design.md`](docs/design.md) | **Milestone 2** - architecture, data model, API design, walking skeleton, design decisions, changes since M1 |
| [`docs/ui.md`](docs/ui.md) | **Milestone 3** - P0 stories and their status, wireframes, error messages, changes since M2 |
| [`docs/backlog.md`](docs/backlog.md) | Product backlog per sprint - priority, story points, owners, reasoning |
| [`docs/stories/`](docs/stories/) | One specification file per user story |
| [`docs/sprint-log.md`](docs/sprint-log.md) | Committed / completed / velocity, review and retrospective per sprint |
| [`docs/traceability.md`](docs/traceability.md) | Every screen traced back to the feature and issue that built it |
| [`docs/definition-of-done.md`](docs/definition-of-done.md) | Full Definition of Done |
| [`docs/process.md`](docs/process.md) | The development process the team chose and why |
| [`docs/images/`](docs/images/) | Flow diagram and project board screenshots |

## How we work in this repository

**One issue = one branch = one Pull Request.** Never combine two issues in one branch.

| Issue type | Branch pattern | Example |
|---|---|---|
| Any issue (story, task, chore) | `<issue>-<short-english-slug>` | `44-database-schema-seed` |

Sprint 1 branches used `feature/` and `chore/` prefixes; from Sprint 2 the team follows
the course convention above.

- **Everything on GitHub is written in English**: issues, branch names, commit messages
  (subject and body), pull requests, review comments, code, comments and documentation
- Commits: `<type>: <summary>` with type `feat`, `fix`, `test`, `docs`, `refactor` or
  `chore`; 3-4 small commits per issue, committed on the day the work is done
- PR title: `[#<issue>] <short imperative summary>`
- PR body follows [`.github/pull_request_template.md`](.github/pull_request_template.md)
  and must contain the line `Closes #<number>` and an AI-assistance declaration
- A **different** teammate must press **Review changes → Approve** with at least one
  substantive comment - a question or a change request, not "ok"
- Never self-approve, and never merge your own PR before someone has reviewed it

## Setup

**To run the project on a new machine, follow [`docs/SETUP.md`](docs/SETUP.md)** - it
lists the prerequisites, the commands for Windows and macOS/Linux, and how to check that
it worked. In short:

```bash
git clone https://github.com/SE-FDA-NEU/G9_AI66A_SE.git
cd G9_AI66A_SE
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
cp .env.example .env                                 # Windows: copy .env.example .env
pip install -r requirements.txt
python src/init_db.py      # creates data/venues.db with 24 venues
python src/app.py          # open http://localhost:5000/search
```

Start reading with [`docs/requirements.md`](docs/requirements.md), then
[`docs/design.md`](docs/design.md).
