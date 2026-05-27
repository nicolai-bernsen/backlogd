---
name: linear
description: backlogd's operating model for Linear via the official MCP. Use whenever a backlogd agent touches Linear — picking up a problem, deciding Issue-vs-Project structure, decomposing work into sub-issues, setting blocks/blocked-by, transitioning workflow state, reporting progress, or surfacing blockers. Pairs with references/linear-mcp.md (exact mcp__linear__* usage) and references/linear-model.md (Linear object model + terminology).
---

# Using Linear in backlogd

backlogd runs entirely on Linear through the **official Linear MCP** (`mcp__linear__*`,
OAuth — no API keys). This skill is the shared operating model every backlogd agent
follows: how a *problem* maps onto Linear, who reads and writes what, and the rules that
keep automated work correct.

It is **runtime guidance** for backlogd's own agents — the `/backlogd:pull` scrum-master
and the `backlogd:developer`.

> **Read this file first; reach for a reference when you act:**
>
> - **[`references/linear-model.md`](references/linear-model.md)** — what each Linear
>   primitive *is* (Issue, Project, Milestone, Cycle, relations, workflow-state
>   categories) and a backlogd→Linear terminology table. Read it when you're unsure what
>   a Linear concept means.
> - **[`references/linear-mcp.md`](references/linear-mcp.md)** — the exact `mcp__linear__*`
>   tools, their parameters, and the load-bearing call rules (state-by-type,
>   upsert/idempotency, git sync, markdown). **Read it before every write.**
>
> This file is the *what / why* (the model and the policy). The references are the *how*
> (concepts and mechanics). When they seem to disagree: the references win on mechanics,
> this file wins on policy.

## Current state vs target

This skill describes the **target** operating model. Some of it is not wired yet. Where
that's true, it is flagged inline:

> 🎯 **Target — not yet wired.** …

The biggest one: **developers writing to Linear.** In the target model the developer agent
manages its own work in Linear (sub-issues, progress, blockers). **Today the
`backlogd:developer` agent does not touch Linear at all** — the `/backlogd:pull`
scrum-master owns every Linear read and write (see `agents/developer.md`). Read the
developer-side actions below as the target a follow-on wires up, not current behaviour.

## The standing structure

- **One Team** (`Nicolai-bernsen`). Every Issue belongs to exactly one team.
- The team's **workflow**. Do not hardcode the display names — resolve them at runtime and
  match on the state *category* (`type`), see `references/linear-mcp.md`:

  | Display name | Category (`type`) |
  |---|---|
  | Backlog | `backlog` |
  | Todo | `unstarted` |
  | In Progress | `started` |
  | In Review | `started` |
  | Done | `completed` |
  | Canceled | `canceled` |
  | Duplicate | `duplicate` |

- The **`problem` label** is the opt-in pickup signal: an issue carrying `problem` is
  product-owner-filed work for backlogd. Nothing without the label is picked up.
- **Continuous flow — no Cycles.** Problems are pulled on demand; backlogd does not run
  time-boxed sprints in the core loop. Read progress from states (and, for Projects, the
  progress graph and health) — never a burndown.
- 🎯 **Target:** solved problems are grouped under **one Initiative** (placeholder name:
  **"backlogd — Solved Problems"**). Creating it is a follow-on — until it exists, refer to
  it by that name and don't fail if it's absent.

## Mapping a problem onto Linear — default-Issue, promote-on-discovery

You never have to predict "is this big?" up front. The rule is mechanical:

1. **Every problem starts as a single Issue** — the one already carrying the `problem`
   label.
2. **Promote it to its own Project** (Linear's *Convert to project*) the moment
   decomposition reveals **any** of:
   - **≥2 independently-committable units** of work, or
   - distinct **phases** (e.g. Investigate → Implement → Verify), or
   - **cross-issue dependencies** (one piece must land before another).
3. **When in doubt, stay an Issue.** Promotion on evidence is cheap; a premature Project
   that never closes is not.

Why mechanical: you cannot know the task count before you decompose, so don't pretend to.
Start small and promote on evidence. This matches Linear's own guidance — sub-issues are
for work "too big for an issue, too small for a project"; when an issue outgrows that,
convert it. **Phases are always Project Milestones**, never a nest of epic/feature/story
issue-types.

### Worked example A — stays an Issue

> *Problem:* "The README install snippet is stale."
>
> One file, one change, one unit of work — no phases, no dependencies. **Keep it a single
> Issue.** The developer makes the edit, reports the result in a comment, and the issue
> moves to Done. No Project, no milestones.

### Worked example B — promoted to a Project

> *Problem:* "Make the app usable offline."
>
> Decomposition reveals several units (a sync layer, a local cache, conflict resolution, a
> UI status indicator), real **phases** (investigate the data model → implement sync →
> verify under a flaky network), and a **dependency** (the indicator needs the sync layer
> first). That trips the rule → **promote to a Project.** Create an Issue per unit, group
> the work under Milestones for the phases, set `blocked-by` for the ordering, and report
> progress with **Project Updates + a health value**.

See `references/linear-model.md` for what Projects, Milestones, and relations *mean*, and
`references/linear-mcp.md` for the exact calls.

## Who does what — the responsibility split

**Scrum-master (`/backlogd:pull`)** owns the *problem boundary*:

- **Pickup** — find the next `problem`-labelled issue; resolve identity (team, states,
  labels) first; order candidates by state (prefer `started`/`unstarted` over `backlog`)
  then priority.
- **Claim** — move the problem to a `started` state and assign it.
- **Dispatch** the developer.
- **Problem-level state** — move the problem to `completed` when solved; surface blockers
  to the product owner for a decision.

**Developer (`backlogd:developer`)** owns the *work inside the problem*:

> 🎯 **Target — not yet wired.** Today the scrum-master performs any Linear writes on the
> developer's behalf; the developer agent itself does not call Linear.

- **Decompose visibly** — create sub-issues (or, in the Project form, issues) via
  `save_issue` with `parentId`, so the breakdown is real in Linear rather than only in the
  agent's head.
- **Dependencies** — set `blocks` / `blocked-by` between those issues.
- **Progress** — move its issues through the workflow; keep **one** agent-owned summary
  comment, edited in place; in the Project form, post **Project Updates with a health
  value**.
- **Blockers** — model a real blocker as `blocked-by`, and name it in the summary comment.
- **Duplicates** — mark with `duplicateOf` (never delete the rediscovered work).

**Canceled** is set by the scrum-master / product owner when a problem is abandoned — not
by the developer.

## Blockers & stall detection

A problem is **blocked or stalled** when any of these hold:

- an issue in an `unstarted`/`started` state has an **open `blocked-by`** pointing at an
  issue that is not yet `completed`/`canceled`, or
- *(Project form)* **health ≠ "On track"** — At risk, Off track, or Update-missing, or
- there is **no `completed` movement** and the Project Update is missing or stale.

The scrum-master surfaces these to the product owner as a question. It never silently
guesses past a blocker.

## Progress signals the scrum-master reads

In priority order: **project status category → health → open `blocked-by` relations →
state-category counts → latest Project Update → milestone completion %.**

Drive every judgement off the state **`type`** (category), never the display name — see
`references/linear-mcp.md` for why and how.

## Boundaries — read before you write

- **Runtime-only, MCP-only.** This skill governs backlogd's *product* behaviour via the
  official Linear MCP. It is not about any development or framework tooling. If you've seen
  a separate "Linear via a CLI" skill elsewhere, that is unrelated dev tooling — do not
  import its conventions here, and keep this skill clean (no framework references).
- **Pure MCP client.** backlogd talks to Linear only through `mcp__linear__*`. The Linear
  *Agents platform* (agent `delegate`, agent sessions, webhooks) is **out of scope** for
  v1 — ignore the `delegate` parameter.
