# G9_AI66A_SE - Sports Venue Booking System

A time-slot booking platform for amateur sports players in Hanoi: players see which pitch
is free at which hour and reserve it in minutes, instead of messaging venue owners one by
one and waiting for a reply; owners see the whole schedule of every venue they manage on
one screen instead of keeping it in a paper notebook.

## Team

| Name | GitHub username | Role |
| --- | --- | --- |
| Nguyen Khac Thu | [@thunopro](https://github.com/thunopro) | Leader · **Product Owner** |
| Hoang Thi Ngoc Han | [@htngochan2802](https://github.com/htngochan2802) | **Scrum Master (Sprint 1)** |
| Nguyen Khoi Nguyen | [@peng543](https://github.com/peng543) | Developer |
| Nguyen Phung Hoa | [@PhunghoaAI](https://github.com/PhunghoaAI) | Developer |
| Le Quang | [@lequangk2006-sys](https://github.com/lequangk2006-sys) | Developer |

- **Product Owner:** @thunopro
- **Scrum Master (Sprint 1):** @htngochan2802

## Project board

https://github.com/orgs/SE-FDA-NEU/projects/25


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
| [`docs/backlog.md`](docs/backlog.md) | Sprint 1 product backlog - priority, story points, prioritisation reasoning |
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
| Story (label `story`) | `feature/<issue>-<slug>` | `feature/14-customer-registration` |
| Chore (label `chore`) | `chore/<issue>-<slug>` | `chore/12-refine-backlog` |
| Consolidated document | `docs/<slug>` | `docs/m1-requirements` |

- PR title: `[#<issue>] <short imperative summary>`
- PR body follows [`.github/pull_request_template.md`](.github/pull_request_template.md)
  and must contain the line `Closes #<number>` and an AI-assistance declaration
- A **different** teammate must press **Review changes → Approve** with at least one
  substantive comment - a question or a change request, not "ok"
- Never self-approve, and never merge your own PR before someone has reviewed it

## Setup

Sprint 1 was a requirements sprint - the repository currently holds documentation only,
no source code. Setup steps will be added in Sprint 2 once the stack is decided.

```bash
git clone https://github.com/SE-FDA-NEU/G9_AI66A_SE.git
cd G9_AI66A_SE
```

Start with [`docs/requirements.md`](docs/requirements.md), then
[`docs/backlog.md`](docs/backlog.md).
