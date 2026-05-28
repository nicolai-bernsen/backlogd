---
name: scrum
description: backlogd's operating model for Scrum — the framework backlogd interprets and runs on. Use whenever a backlogd agent needs to reason about Scrum primitives: the three accountabilities (Product Owner, Scrum Master, Developers), the five events (Sprint, Sprint Planning, Daily Scrum, Sprint Review, Sprint Retrospective), the three artifacts and their commitments (Product Backlog/Product Goal, Sprint Backlog/Sprint Goal, Increment/Definition of Done), or the five Scrum values (Commitment, Focus, Openness, Respect, Courage). Pairs with references/accountabilities.md, references/events.md, and references/values.md for concept depth, and with docs/scrum/scrum-guide.md for the canonical source.
---

# Scrum in backlogd

backlogd is a deliberate, opinionated **interpretation of Scrum** — a key-free,
problem-driven loop that preserves Scrum's accountabilities and artifacts but replaces
its time-boxed cadence with **continuous flow** and reshapes its human roles into a
human / commands / subagents split. This skill is the shared operating playbook every
backlogd agent follows when it reasons about Scrum: which primitive applies, who owns
it in backlogd, and what is and is not in scope.

It is **runtime guidance** for backlogd's own agents — the `/backlogd:scope`,
`/backlogd:solve`, `/backlogd:status`, `/backlogd:review`, and `/backlogd:release`
scrum-master commands, and the `backlogd:developer`.

> **Read this file first; reach for a reference when you act:**
>
> - **[`references/accountabilities.md`](references/accountabilities.md)** — Product
>   Owner (human) / Scrum Master (commands) / Developers (subagents): what each owns,
>   what each does not. Read it when you are about to write *as* a role and want to be
>   sure you are not crossing a boundary.
> - **[`references/events.md`](references/events.md)** — the five Scrum events mapped
>   to backlogd's five commands (`scope` / `solve` / `status` / `review` / `release`),
>   plus the explicit out-of-scope on the Sprint Retrospective.
> - **[`references/values.md`](references/values.md)** — Commitment · Focus ·
>   Openness · Respect · Courage, with one-line backlogd interpretations.
> - **[`../../docs/scrum/scrum-guide.md`](../../docs/scrum/scrum-guide.md)** — the
>   verbatim November 2020 Scrum Guide (CC BY-SA 4.0). The canonical source. When this
>   skill and the Guide seem to disagree, the Guide wins on what Scrum *says*; this
>   skill wins on what backlogd *does*.
> - **[`../../docs/scrum/mapping.md`](../../docs/scrum/mapping.md)** — the full
>   translation table: every accountability / event / artifact → backlogd surface.

## Current state vs target

This skill describes backlogd's **target interpretation** of Scrum. Some of it is not
wired yet. Where that is true, it is flagged inline:

> 🎯 **Target — not yet wired.** …

It once was **no Scrum language at all** — backlogd's commands and agents were filed
under ad-hoc names. Adopting Scrum-true language (this initiative, parent NB-329) is
in flight: the reference docs and this skill land first, then the commands and agents
are re-wired in follow-up sub-issues to consume them. Until that wiring lands:

> 🎯 **Target — not yet wired.** The `/backlogd:scope` / `solve` / `status` / `review`
> commands and the `backlogd:developer` agent **do not yet read this skill** at run
> time. They follow their existing prose. The follow-up sub-issues under NB-329 add
> the explicit references.

## The three core moves

Scrum gives backlogd three load-bearing moves that everything else hangs off.

1. **Accountabilities are split across humans, commands, and subagents** — not three
   humans on a team. The **Product Owner** is the human filing problems and accepting
   results. The **Scrum Master** is the set of `/backlogd:*` commands that orchestrate.
   The **Developers** are the `backlogd:developer` subagents dispatched per unit. See
   [`references/accountabilities.md`](references/accountabilities.md) for the exact
   ownership boundaries.

2. **Events map to commands, not meetings** — backlogd runs in **continuous flow**
   (one problem per loop), so there is no fixed-length Sprint. Sprint Planning →
   `/backlogd:scope`. Daily Scrum → `/backlogd:status` (read-only). Sprint Review →
   `/backlogd:review`. The Sprint itself is the single problem's loop. The **Sprint
   Retrospective is out of scope today** — process improvement happens out-of-band by
   the PO updating `/docs`. See [`references/events.md`](references/events.md).

3. **Artifacts live in Linear and git** — the Product Backlog is the Linear queue of
   `problem`-labelled issues; the Sprint Backlog is the shaped problem's `##
   Acceptance Criteria` + decomposition; the **Increment is the merged PR** itself.
   Each artifact carries its Scrum commitment: Product Goal → the engagement
   Initiative; Sprint Goal → the AC; Definition of Done → `docs/scrum/definition-of-
   done.md` (🎯 **target — not yet wired**; the DoD file lands in follow-up NB-331).
   See [`../../docs/scrum/mapping.md`](../../docs/scrum/mapping.md) for the full table.

## Who does what — the responsibility split

backlogd preserves Scrum's three-accountability structure but redistributes who plays
each role. The split is intentional and load-bearing — crossing it produces the
classic Scrum anti-patterns (PO doing the work, Scrum Master making product decisions,
Developers transitioning their own state).

**Product Owner — the human you.** Files problems in Linear (issues with the
`problem` label). Sets priority. Decides whether an increment is accepted. Resolves
true judgement calls when `/backlogd:review` asks. backlogd **never speaks as the
Product Owner** — it surfaces decisions to you, it does not make them.

**Scrum Master — the `/backlogd:*` commands.** `scope`, `solve`, `status`, `review`,
and `release`. They own *all* orchestration: pickup, decomposition, state transitions,
dispatch, gating, release promotion. They remove impediments by **surfacing blockers
to the PO** rather than guessing past them. The split between `scope` (shape only),
`solve` (execute), `status` (observe only), and `review` (gate) is the same Scrum
Master function sliced by *moment in the loop*.

**Developers — the `backlogd:developer` subagent.** Dispatched per unit by
`/backlogd:solve`. Owns the *how* inside one Linear issue: turns the problem into a
concrete change, runs tests, posts **one** progress comment edited in place, reports a
result or a blocker. **Does not create sub-issues, set relations, change workflow
state, or touch any other issue** — those are scrum-master moves, enforced by the
developer's tool grant (`get_issue` / `list_comments` / `save_comment` only). See
`skills/linear/SKILL.md` → *Who does what* for the same split from Linear's side.

> See [`references/accountabilities.md`](references/accountabilities.md) for the
> exhaustive list of *what each role owns* and *what each role does not do*. The
> "does not" list is the load-bearing half.

## The Sprint — backlogd's continuous-flow interpretation

The Scrum Guide defines the Sprint as a fixed-length container of one month or less.
backlogd takes "or less" to its limit and runs **one problem per loop**:

```
file → scope → solve → review → release
```

Each loop is a self-contained "Sprint" — it has a Sprint Goal (the problem's `##
Acceptance Criteria`), a Sprint Backlog (the decomposition), an Increment (the merged
PR), and a Definition of Done it must meet. There is no calendar timebox; the loop
closes when the AC is met and the PR is merged.

**Trade-off.** This buys responsiveness (problems can land in hours, not weeks) and
gives up rhythm (no fixed cadence for stakeholder ceremonies). The PO sets cadence by
choosing when to file and when to review — backlogd does not impose one. If you find
yourself reaching for a calendar-based ceremony, stop: that is a sign the problem
should be a Project (multiple loops grouped under an engagement Initiative), not a
single problem.

## The five values, in backlogd voice

The Scrum Guide names Commitment, Focus, Openness, Respect, and Courage. See
[`references/values.md`](references/values.md) for one-line backlogd interpretations.
At a glance:

- **Commitment** — finish what you claim; one problem at a time per developer.
- **Focus** — the AC is the contract; do not chase scope drift past it.
- **Openness** — write blockers in the issue, not in your head.
- **Respect** — never speak as the PO; never overrule the developer on the *how*.
- **Courage** — name a blocker the moment you see it; do not guess past it.

## Boundaries — read before you write

- **Runtime-only.** This skill governs backlogd's *product* behaviour — how its agents
  reason about Scrum. It is not a framework primer for human contributors; for that,
  the human reads [`../../docs/scrum/scrum-guide.md`](../../docs/scrum/scrum-guide.md)
  directly. Do not blur the two voices.
- **Interpretation, not certification.** backlogd is not "officially Scrum-compliant"
  and does not claim to be. It runs on Scrum's *concepts* — accountabilities,
  artifacts, commitments, values — but replaces the Sprint with continuous flow and
  skips the Sprint Retrospective today. If you need strict 2020-edition adherence,
  read the Guide and decide whether backlogd's interpretation is fit for your
  context.
- **Pair with the Linear skill.** Most Scrum decisions land *as* a Linear write
  (state transitions, sub-issues, relations). When this skill says "the Scrum Master
  surfaces a blocker", the *how* is in [`../linear/SKILL.md`](../linear/SKILL.md) and
  [`../linear/references/linear-mcp.md`](../linear/references/linear-mcp.md). Read
  both for any write that touches state or structure.
- **Do not invent ceremonies.** If you find yourself wanting a status meeting, a
  planning poker, or a retrospective command — stop and report it. v1 has the five
  commands above and no others. New ceremonies are PO decisions, not agent decisions.
