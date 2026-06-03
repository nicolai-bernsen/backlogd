# Scrum → backlogd surface mapping

How each Scrum primitive — the **three accountabilities**, the **five events**, and the
**three artifacts** (with their commitments) — is embodied in backlogd. backlogd is a
deliberate, opinionated *interpretation* of Scrum: a key-free, problem-driven loop with
continuous flow instead of fixed-length sprints, and an LLM-shaped scrum-master /
developer split. This page is the canonical translation table.

The Scrum Guide column references the November 2020 edition — see
[`scrum-guide.md`](scrum-guide.md). Anything reading "follow-up sub-issue" below points
at later work in the parent initiative ([Linear NB-329](https://linear.app/) — Adopt
Scrum-true language and topology).

## Accountabilities (3)

The Scrum Guide defines three accountabilities inside one Scrum Team: Product Owner,
Scrum Master, and Developers. backlogd preserves all three but redistributes who plays
each role — humans, commands, and subagents.

| Scrum Guide concept | backlogd surface |
| --- | --- |
| **Product Owner** — accountable for maximising the value of the product; owns the Product Backlog ordering and the Product Goal; one person, not a committee (Scrum Guide → *Scrum Team › Product Owner*). | **The human you** — files problems and owns outcomes (ideation), not the verification or the merge. Files Linear issues with the `problem` label, sets priority. The **independent verdict review** verifies the increment and, on the happy path, `/backlogd:solve` auto-chains it and merges to Done with no human gate (ship-on-green) — the PO is interrupted **only** on a sent-back verdict, a `❔`/`[manual]` judgement call, or a blocker, and can re-verify any time via `/backlogd:review`. backlogd never speaks *as* the Product Owner. |
| **Scrum Master** — accountable for the team's effectiveness and for establishing Scrum as defined; serves the team, the Product Owner, and the organisation; removes impediments and ensures events take place (Scrum Guide → *Scrum Team › Scrum Master*). | **The `/backlogd:*` commands** — `scope`, `solve`, `status`, `review`, `release`. They own all orchestration: pickup, decomposition, state transitions, dispatch, gating, and release promotion. They surface blockers to the human PO instead of guessing past them. |
| **Developers** — accountable for creating any aspect of a usable Increment each Sprint; create the Sprint Backlog plan; instil quality by adhering to the Definition of Done (Scrum Guide → *Scrum Team › Developers*). | **The `backlogd:developer` subagent** — dispatched per unit of work by `/backlogd:solve`. Owns the *how* inside a single Linear issue: turns the problem into a concrete change, runs tests, posts one progress comment, reports a result or a blocker. Does not write structure or state. |

## Events (5)

The Scrum Guide defines five events: the Sprint (the container), Sprint Planning, the
Daily Scrum, the Sprint Review, and the Sprint Retrospective. backlogd maps all five —
the Retrospective lands as **`/backlogd:retro`**, a milestone-scoped, graph-grounded
look-back that files candidate improvements for the PO to prioritize.

See also [`../../skills/scrum/references/events.md`](../../skills/scrum/references/events.md)
for the agent-facing voice.

| Scrum Guide concept | backlogd surface |
| --- | --- |
| **Sprint** — fixed-length container of one month or less; "the heartbeat of Scrum, where ideas are turned into value" (Scrum Guide → *Scrum Events › The Sprint*). | **Continuous flow — no fixed-length sprint.** backlogd runs **one problem per loop**: pickup → solve → review → release. The "Sprint" container is the *single problem's loop* from `solve`-claim to `review`-accept. There is no calendar timebox. |
| **Sprint Planning** — initiates the Sprint by laying out the work; produces the Sprint Backlog (the *why* / *what* / *how*) (Scrum Guide → *Scrum Events › Sprint Planning*). | **`/backlogd:scope`** — shapes a problem: writes the spec + `## Acceptance Criteria` into the Linear issue description, decomposes on discovery (sub-issues + `blocked-by`, or promotes to a Project), sets priority. Produces the equivalent of a Sprint Backlog **for that one problem**. A problem must clear the **[Definition of Ready](definition-of-ready.md)** entry gate before it is solvable — symmetric to the [Definition of Done](definition-of-done.md) exit gate (entry mirrors exit: backlogd refuses to start an unready problem just as it refuses to ship an ungoverned increment). The gate is reached **Socratically — `scope` interrogates the idea into a crisp, falsifiable problem; it does not generate ideas or prioritize the backlog** (ordering stays the PO's call, per *Product Backlog* below). |
| **Daily Scrum** — 15-minute Developer event to inspect progress toward the Sprint Goal and adapt the plan (Scrum Guide → *Scrum Events › Daily Scrum*). | **`/backlogd:status`** — read-only standup. Surveys active `problem` issues, reads decomposition / states / `blocked-by`, reports progress + blockers to the PO. Writes nothing — same inspection function, no plan adaptation (that lives in `solve`). |
| **Sprint Review** — inspects the outcome of the Sprint; stakeholders decide what to do next (Scrum Guide → *Scrum Events › Sprint Review*). | **The independent verdict review** — verifies an *In Review* problem against its `## Acceptance Criteria` and the [Definition of Done](definition-of-done.md). All met (fully green) → merged → Done; gaps → back to In Progress with rework notes; genuine judgement call → asks the PO. On the happy path `/backlogd:solve` **auto-chains this verdict and merges with no human gate** (ship-on-green, on by default); `/backlogd:review` is the manual re-entry point. Closes the loop. |
| **Sprint Retrospective** — inspects how the last Sprint went; identifies improvements to process, tools, Definition of Done (Scrum Guide → *Scrum Events › Sprint Retrospective*). | **`/backlogd:retro`** — over a completed **milestone** (primary; cycle-end as a cadence safety-net, and on-demand `--cycle` / `--since` / `--last` selectors), reads the **execution graph** (`scripts/graph.py report --json`: rework, latency, blockers, partials) as objective evidence, detects **cross-issue patterns** no single review can see, classifies each learning (recurring failure → ADR/standard · process problem → framework bug · one-off → noted), and **files the load-bearing ones as candidate `kind:improvement` issues**. The retro proposes; the PO prioritizes — the team does not grade its own homework and auto-fix. Closes the empirical loop's adaptation pillar. |

> **Note on the release.** backlogd has a fifth command, **`/backlogd:release`**, that
> promotes the integration branch to a tagged release. It does not map to a Scrum event
> — releases in Scrum happen *within* the Sprint (an Increment may ship at any time).
> Treat `release` as the engineering counterpart to the Increment's "usable" property,
> not a separate ceremony.

<!-- two distinct notes; the comment separates the blockquotes (MD028) -->

> **Note on the Definition of Ready.** backlogd attaches a
> **[Definition of Ready](definition-of-ready.md)** to Sprint Planning (`/backlogd:scope`)
> as the **entry** gate symmetric to the [Definition of Done](definition-of-done.md)
> **exit** gate. The DoR is **not** in the November 2020 Scrum Guide — it is community
> practice — so backlogd adopts it to complete entry/exit symmetry, **not** as a
> Scrum-compliance fix, and does not claim it as one (consistent with *Interpretation, not
> certification* in [`../../skills/scrum/SKILL.md`](../../skills/scrum/SKILL.md)). The DoD
> *is* a canonical Scrum commitment (on the Increment); the DoR is backlogd's own mirror of
> it at the front of the loop.

## Artifacts (3) + their commitments

The Scrum Guide defines three artifacts, each carrying a single commitment: the Product
Backlog (Product Goal), the Sprint Backlog (Sprint Goal), and the Increment (Definition
of Done).

| Scrum Guide concept | backlogd surface |
| --- | --- |
| **Product Backlog** — emergent, ordered list of what is needed to improve the product; the single source of work for the Scrum Team (Scrum Guide → *Scrum Artifacts › Product Backlog*). | **The Linear backlog of `problem`-labelled issues**, ordered by state and priority. `/backlogd:scope` and `/backlogd:solve` consult it; the human PO files into it. The `problem` label is the opt-in pickup signal — nothing without it is picked up. |
| **Commitment: Product Goal** — the long-term objective the Scrum Team plans against; lives in the Product Backlog (Scrum Guide → *Product Backlog › Commitment: Product Goal*). | **The Linear Initiative** (in backlogd's model, a **consulting engagement**). Groups that engagement's problem-Projects. The official Linear MCP exposes `save_initiative` (create/update), so the engagement Initiative is a wired write path — the auto-attach *wiring* (init create + status-update roll-ups) is tracked separately. See `skills/linear/SKILL.md` → *Engagement = Initiative*. |
| **Sprint Backlog** — the Sprint Goal (why), the selected Product Backlog items (what), and an actionable plan (how); "a plan by and for the Developers" (Scrum Guide → *Scrum Artifacts › Sprint Backlog*). | **The shaped problem and its decomposition** — the `## Acceptance Criteria` section is canonical (in the issue **description** for single-Issue / sub-issue problems, in the Project's **"Spec" Document** for promoted Project-form problems) + any sub-issues / Project Milestones / `blocked-by` relations the `scope` command laid down. Held in Linear; consulted by `solve` and the developer. |
| **Commitment: Sprint Goal** — the single objective for the Sprint (Scrum Guide → *Sprint Backlog › Commitment: Sprint Goal*). | **The problem's `## Acceptance Criteria`** — the binding "done" contract for one loop. `/backlogd:review` verifies against it line-by-line (reading from the issue description for single-Issue, from the Project's "Spec" Document for Project-form). |
| **Increment** — a concrete, usable stepping stone toward the Product Goal; thoroughly verified; must meet the Definition of Done to count (Scrum Guide → *Scrum Artifacts › Increment*). | **The merged PR** (one branch → one PR per problem, into `dev`). `/backlogd:solve` opens the worktree and PR and — on the happy path — auto-chains the independent verdict and **merges a fully-green increment to Done with no human gate** (ship-on-green); `/backlogd:review` is the manual re-entry that accepts and merges. The PR *is* the Increment — usable, additive, verified. |
| **Commitment: Definition of Done** — a formal description of the state of the Increment when it meets the quality measures required for the product (Scrum Guide → *Increment › Commitment: Definition of Done*). | **[`definition-of-done.md`](definition-of-done.md)** — the repo-level DoD that every increment must meet: AC covered by tests, CI green, no orphan TODOs, no secrets, `/docs` and conventions updated where behaviour changed, one commit per unit with the issue ref, work-log + solution-brief comments posted on the Linear issues. |

> **Don't conflate the two commitments.** The **Sprint Goal (AC)** is *per-problem* — the
> "done" contract for one loop, written into the issue by `/backlogd:scope`. The
> **Definition of Done** is *standing* — the same floor every increment clears no matter
> which problem it solves. The reviewer gates each diff against **both**, and a red DoD
> line blocks the merge exactly like a red AC line. See
> [`definition-of-done.md`](definition-of-done.md) → *DoD vs AC*.

## A note on cadence

backlogd's **core loop** is continuous flow with no fixed time-box: the Scrum Guide
allows Sprints of one month or less, and backlogd takes "or less" to its limit (one loop
per problem), accepting the trade-off — less rhythm, more responsiveness. **Cycles are
not used to drive the core loop.** They surface in exactly one place: as the optional
*cadence safety-net* trigger for `/backlogd:retro` (`--cycle N`), so a long-running
milestone never goes un-retro'd. The retro's primary trigger remains a completed
**milestone** (a scope marker), not the calendar.

## See also

- [`scrum-guide.md`](scrum-guide.md) — the verbatim 2020 Scrum Guide (CC BY-SA 4.0).
- [`../../skills/scrum/SKILL.md`](../../skills/scrum/SKILL.md) — the agent-facing
  operating playbook.
- [`../../skills/scrum/references/values.md`](../../skills/scrum/references/values.md),
  [`events.md`](../../skills/scrum/references/events.md),
  [`accountabilities.md`](../../skills/scrum/references/accountabilities.md) — the
  concept references the SKILL reaches for.
- [`../../skills/linear/SKILL.md`](../../skills/linear/SKILL.md) — how the Linear side
  of the loop works (issues, states, relations, projects).
