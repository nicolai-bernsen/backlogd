---
name: linear
description: backlogd's operating model for Linear via the official MCP. Use whenever a backlogd agent touches Linear — picking up a problem, deciding Issue-vs-Project structure, decomposing work into sub-issues, setting blocks/blocked-by, transitioning workflow state, reporting progress, or surfacing blockers. Pairs with references/linear-mcp.md (exact mcp__linear__* usage) and references/linear-model.md (Linear object model + terminology).
---

# Using Linear in backlogd

backlogd runs entirely on Linear through the **official Linear MCP** (`mcp__linear__*`,
OAuth — no API keys). This skill is the shared operating model every backlogd agent
follows: how a *problem* maps onto Linear, who reads and writes what, and the rules that
keep automated work correct.

It is **runtime guidance** for backlogd's own agents — the `/backlogd:scope` +
`/backlogd:solve` scrum-master commands and the `backlogd:developer`.

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

It once was **developers writing to Linear** — now **wired, hybrid**: the `backlogd:developer`
writes **comments on its own assigned issue** (one progress/result comment edited in place, plus
a personal checklist and any blocker note) and nothing else. It does **not** create sub-issues,
set relations, or change state — the scrum-master commands (`/backlogd:scope` +
`/backlogd:solve`) own all structure and state. The boundary is enforced by the developer's tool
grant (`get_issue` / `list_comments` / `save_comment` only; see `agents/developer.md`).

## The standing structure

- **One Team — resolved at runtime.** Every Issue belongs to exactly one team. backlogd
  resolves the team from `list_teams` and caches it (along with workflow states and
  labels) to `.backlogd/identity.json` with a 24-hour TTL — see `references/linear-mcp.md`
  → "Resolve identity before you write" → "Cache identity to `.backlogd/identity.json`".
  Never hardcode a team name — every installer is on their own.
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
- **Engagement = Initiative.** A consulting engagement is a Linear **Initiative** that groups
  that engagement's problem-**Projects** (an Initiative is a hand-curated list of Projects).
  Name it for the engagement. **Create/attach the Initiative manually** — the official MCP has
  **no initiative-write tool** (Initiatives are only a *parent reference* on `save_comment` /
  `save_document`), so auto-attaching isn't possible via backlogd's key-free MCP path. Refer to
  it by name and don't fail if it's absent.

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

The scrum-master is a small set of commands: `scope`, `solve`, and `review` write to Linear
(structure and state); `status` only observes.

**`/backlogd:scope` (shape)** makes a problem execution-ready:

- **Pick** a `problem`-labelled issue (or an explicit id).
- **Write the spec + `## Acceptance Criteria`** into the description — the canonical "shaped"
  signal `/backlogd:solve` looks for.
- **Decompose on discovery** — sub-issues + `blocked-by`, or promote to a Project — only as
  much as the problem earns.
- **Set priority**, then stop. No solving, no state change.

**`/backlogd:solve` (execute)** drives a shaped problem to a result:

- **Pickup** — take the top `problem` (resolve identity first; order by state then priority),
  or triage-if-unshaped by running scope's flow inline.
- **Claim** — move each ready unit to the *In Progress* state.
- **Dispatch** the developer per unit in `blocked-by` order; record each result in place.
- **Hand back** — when solved, post a high-level PO-facing solution brief and move the problem
  to *In Review* (the PO accepts → `completed` on their own time). Surface blockers to the
  product owner; never guess past one.

**`/backlogd:status` (observe)** is **read-only** — it writes nothing:

- **Survey** the active `problem` issues (optionally scoped to one problem or engagement), read
  their decomposition, states, and `blocked-by`, and **report** progress + blockers to the
  product owner — enacting "Progress signals the scrum-master reads" and "Blockers & stall
  detection" below. It never transitions state or dispatches.

**`/backlogd:review` (gate)** closes a solved problem's loop:

- **Verify** an *In Review* problem against its `## Acceptance Criteria` — from the developer's
  result and the artifacts — and post a per-AC verdict.
- **Decide**: all met → `completed` (Done); gaps → back to *In Progress* with actionable rework
  notes (a fresh `solve` re-runs them); a genuine judgement call → leave it *In Review* and ask
  the product owner. It does not re-dispatch.

**Developer (`backlogd:developer`)** owns the *work inside one issue* — and writes **only
comments on its assigned issue**:

- **Progress** — keep **one** summary comment on its issue, edited in place (a
  `**[backlogd developer]**` badge), with a personal checklist of its steps.
- **Blockers** — name a blocker in that comment and report it back; the scrum-master models it
  structurally and surfaces it to the product owner.

The developer does **not** create sub-issues, set relations, move workflow state, mark
duplicates, or touch any other issue — these are **orchestrator-owned**: `scope` creates
sub-issues + `blocked-by` and promotes Projects; `solve` transitions state, posts the PO
solution brief, and sets `duplicateOf` / **Canceled**. The split is enforced by the developer's
tool grant (`get_issue` / `list_comments` / `save_comment` only).

## Git flow

backlogd lands a problem's work on **one branch → one PR**, and the **orchestrator owns all git**:

- **`solve`** opens an isolated **worktree + branch** per problem off the integration branch; the
  developer edits **in that worktree** (it runs no git); `solve` commits each unit, pushes, and
  opens the PR. **`review`** merges the PR on accept. Worktrees keep parallel sessions from
  fighting over the shared checkout's HEAD.
- **State follows git** where the integration is set up: branch push → In Progress, PR → In
  Review, merge → Done (see `references/linear-mcp.md`); set state via the API only when there is
  no git event.
- Promoting the integration branch to a release (`dev → main` + tag) is **`/backlogd:release`** —
  it bumps the plugin version, merges with a merge commit, tags `vX.Y.Z`, and back-merges to re-sync.

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
