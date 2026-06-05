# backlogd — overview

backlogd turns Claude Code into a problem-driven scrum team. You file *problems*; agents own
the *solutions*.

## The loop

1. **You (the product owner)** file a *problem* — a Linear issue carrying the `problem`
   label — describing what is wrong or what "better" looks like, not a step-by-step solution.
2. **The scrum-master** (`/backlogd:pull`) picks up one unstarted problem, moves it to In
   Progress, and dispatches a developer.
3. **A developer agent** owns the *how*: it turns the problem into a concrete change, working
   to the practices in this `/docs` (the living spec) and the work item (the static spec).
4. **The result** is recorded back on the Linear issue, which then moves to Done — or stays
   In Progress if the developer hit a blocker worth a human decision.

## Roles

- **Product owner (human)** — files problems, makes product decisions, unblocks.
- **Scrum-master** — reads the backlog, dispatches work, and records results; owns the
  orchestration and all Linear writes.
- **Developer agents** — implement, test, and report; they own the technical calls.

For the full Scrum Guide concept map — every accountability, event, and artifact mapped
to a backlogd surface — see [`docs/scrum/mapping.md`](scrum/mapping.md). Two symmetric
hard-rules gates bracket every problem: the **[Definition of Ready](scrum/definition-of-ready.md)**
entry gate at the front of `/backlogd:scope` (a problem cannot start until it has a crisp
outcome, falsifiable AC, no open one-way-door decision, and no standards conflict), and the
**[Definition of Done](scrum/definition-of-done.md)** exit gate the independent verdict
review enforces before merge — auto-chained by `/backlogd:solve` on the happy path
(ship-on-green), or run manually via `/backlogd:review`.

## The two specifications

backlogd treats **Linear as the static spec** (the problem and its acceptance criteria) and
**`/docs` as the living spec** (how the system works). Every developer follows the
[living-spec contract](living-spec-contract.md).

## Source of truth

Linear is the system of record for the loop — status, decisions, and results live on the
issue. This `/docs` directory is the source of truth for how the system is built.
