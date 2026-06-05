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

**Developers writing to Linear is wired**, with the NB-340 workaround documented below.
The `backlogd:developer` writes **comments on its own assigned issue** (one progress/result
comment edited in place, plus a personal checklist and any blocker note) and nothing else.
It does **not** create sub-issues, set relations, or change state — the scrum-master commands
(`/backlogd:scope` + `/backlogd:solve`) own all structure and state. The boundary is enforced by
the developer's tool grant (`get_issue` / `list_comments` / `save_comment` only; see
`agents/developer.md`).

## NB-340: tool-grant hazard the orchestrator must work around

A finding from a parallel run (NB-340, closed; investigation note at
`docs/notes/subagent-mcp-tool-grant.md`) documents that subagent runtime tool grants
behave as `frontmatter ∩ parent's currently-loaded deferred tools`. In plain English:
even if a subagent's frontmatter lists `mcp__linear__save_comment`, **the subagent
may not actually have it at runtime unless the orchestrator has loaded it first**.
The same hazard applies to every `mcp__linear__*` tool and to `ToolSearch` itself.

This is a Claude Code platform behaviour — not a backlogd bug — but every command that
dispatches a subagent has to work around it. backlogd uses **two complementary
mitigations**:

1. **Defense at the dispatched agent (NB-345).** `agents/developer.md` carries **no
   `tools:` line** — it inherits the full tool surface from the orchestrator,
   sidestepping the intersection entirely. The boundary moves into the system prompt
   ("you have these tools at runtime, but the contract forbids their use except for
   `save_comment` on your own issue"). Trade-off: lose harness-enforced tool
   restriction, gain the functional capability the contract requires.

2. **Defense at the orchestrator (NB-346).** Every `/backlogd:*` command begins with
   a **§0 pre-load step** that calls `ToolSearch` once with the canonical Linear MCP
   tool list — see *Deferred tools — pre-load before dispatch* below. This loads the
   deferred tools into the parent's context **before** any subagent dispatch, so a
   future specialist with an explicit `tools:` list (e.g. the NB-326 reviewer that
   deliberately wants a restricted grant) receives the tools it names.

   **Verified working (NB-368, 2026-05-29)** — not asserted: after the §0 pre-load, a
   dispatched `backlogd:reviewer` (explicit `tools:` list, no `ToolSearch` of its own)
   received `mcp__linear__save_comment` as a *directly-callable* tool and posted its
   comment end-to-end. See `docs/notes/subagent-mcp-tool-grant.md` §8.

The two are complementary, not alternatives. NB-345 keeps today's developer working
even if a session forgets the §0 pre-load; NB-346 means a future restricted-grant
specialist works without dropping back to the NB-345 workaround.

`agents/developer.md`'s missing `tools:` line (NB-345) is a **deliberate exception**,
not an inconsistency: the developer needs a broad grant (`Edit`/`Write`/`Bash`/git
*and* Linear) for end-to-end code writes, whereas the restricted specialists
(`reviewer`/`tester`/`refiner`) keep their explicit lists — boundary preserved —
because §0 makes that path work (verified, NB-368).

If a subagent still reports it could not post its `**[backlogd developer]**` (or
`**[backlogd reviewer]**`) comment, treat that as a tool-grant skew, not a subagent
failure. Re-dispatch from a fresh session; do not silently accept a missing work-log
comment as a "developer issue", and do not substitute an orchestrator-authored
work-log comment for the developer's — that loses the audit trail the comment exists
to record.

NB-340 closed as the platform-side root cause investigation; backlogd ships both
mitigations and re-evaluates if the upstream behaviour changes.

## Specialist-grant contract (NB-413)

NB-340 above covers the *Linear MCP* tools a subagent may not have at runtime. Its sibling,
NB-413, covers the **runnable checks an AC requires** (markdownlint, an index regen +
`--check`, a drift test, a label/issue create) that a specialist on a narrow grant cannot
execute — which used to fall **silently** to the orchestrator or the gate, relocating the
trust boundary upward with nobody deciding it should (instances: NB-379, NB-381). The
contract closes that gap without widening the restricted grants:

- **Enumerated hand-off** — a specialist runs every AC-required check its grant *can* run
  and **enumerates** each one it *cannot* in a machine-readable `Deferred-checks:` line in
  its STATUS report (`agents/developer.md`); the gate is **obligated to run each**
  (`skills/solve/gate.md`). Replaces silent deferral.
- **markdownlint folded into the gate** — the reviewer (which holds `Bash`) runs
  `markdownlint-cli2` on every changed `.md` **the way CI does** (pinned `v0.22.1` +
  `.markdownlint-cli2.jsonc`, trusting the error count over the exit code) in every
  pre-commit gate, so the most common docs check never silently defers (NB-417).

The full decision + the rejected alternatives (widen every grant; the NB-353
`disallowedTools:` inverted grant) live in `skills/reviewer/SKILL.md` →
*Specialist-grant contract*, the home of the trust model this extends.

## Deferred tools — pre-load before dispatch

Every `/backlogd:*` command begins with a **§0 "Pre-load deferred tools" step** that
makes a single batched `ToolSearch` call naming the canonical Linear MCP tool list.
This is the NB-346 orchestrator-layer mitigation for the NB-340 tool-grant hazard
above — defense in depth so a subagent dispatched with an explicit `tools:` list that
names Linear tools receives them at runtime, not a stripped intersection. **This is
verified, not asserted** (NB-368, 2026-05-29): behind §0 the named tools are
materialised as *directly-callable* for the explicit-list child — see
`docs/notes/subagent-mcp-tool-grant.md` §8.

**Canonical pre-load list** (write-capable verbs use the full set; read-only verbs
may use the read-only subset but for idiom consistency every command uses the full
list):

```text
mcp__linear__get_issue
mcp__linear__save_issue
mcp__linear__save_comment
mcp__linear__list_comments
mcp__linear__list_issue_statuses
mcp__linear__list_issue_labels
mcp__linear__list_issues
mcp__linear__list_teams
mcp__linear__list_milestones
mcp__linear__get_project
mcp__linear__save_milestone
```

**The call** (identical across every `/backlogd:*` command's §0):

```text
ToolSearch(select: "mcp__linear__get_issue,mcp__linear__save_issue,mcp__linear__save_comment,mcp__linear__list_comments,mcp__linear__list_issue_statuses,mcp__linear__list_issue_labels,mcp__linear__list_issues,mcp__linear__list_teams,mcp__linear__list_milestones,mcp__linear__get_project,mcp__linear__save_milestone")
```

The §0 step is the **first** step of each command, visible to anyone reading the
file — never buried mid-flow. Inspiration: EveryInc/compound-engineering-plugin's
`ce-code-review` SKILL.md uses the same Phase-0 pre-load idiom for `AskUserQuestion`.

**Fallback.** `ToolSearch` is itself a deferred tool; if a future Claude Code version
removes it, fall back to the prior idiom — invoke each `mcp__linear__*` tool at least
once from the orchestrator's context before the first subagent dispatch. The
identity-resolution path in each command already invokes `list_teams`,
`list_issue_statuses`, and `list_issue_labels`, so the fallback is mostly free for
the read-only tools; `save_comment` is the one a `/backlogd:solve` run may need to
force via a scratch-comment nudge before its first developer dispatch.

## The standing structure

- **One Team — resolved at runtime.** Every Issue belongs to exactly one team. backlogd
  resolves the team from `list_teams` and caches it (along with workflow states and
  labels) to `.backlogd/identity.json` with a 24-hour TTL — see `references/linear-mcp.md`
  → "Resolve identity before you write" → "Cache identity to `.backlogd/identity.json`".
  Never hardcode a team name — every installer is on their own.
- The team's **workflow**. Do not hardcode the display names — resolve them at runtime and
  match on the state *category* (`type`), see `references/linear-mcp.md`:

  | Display name | Category (`type`) |
  | --- | --- |
  | Backlog | `backlog` |
  | Todo | `unstarted` |
  | In Progress | `started` |
  | In Review | `started` |
  | Done | `completed` |
  | Canceled | `canceled` |
  | Duplicate | `duplicate` |

- The **`problem` label** is the opt-in pickup signal: an issue carrying `problem` is
  product-owner-filed work for backlogd. Nothing without the label is picked up.
- The **`kind:ops` label** is the optional *route signal*: an issue (problem or unit)
  carrying `kind:ops` is **ops-only** — its solution is GitHub repo-ops or external
  content drafts, not a code diff. `/backlogd:solve` reads the label per-unit and routes
  ops units through `skills/solve/ops.md` (no worktree, no commit, no PR; the developer
  takes `gh`/repo-ops actions and posts an action log on the unit). `/backlogd:scope`
  applies the label when shaping a problem that is clearly repo-ops; it creates the
  label on the team via `create_issue_label` if it does not yet exist. The label is *just
  a routing flag* — no priority, no automation beyond this path. Mixed problems (some ops
  units, some code units) are out of scope for v1 — `solve` stops and asks the PO to
  split.
- **Continuous flow — no Cycles.** Problems are pulled on demand; backlogd does not run
  time-boxed sprints in the core loop. Read progress from states (and, for Projects, the
  progress graph and health) — never a burndown.
- **Engagement = Initiative.** A consulting engagement is a Linear **Initiative** that groups
  that engagement's problem-**Projects** (an Initiative is a hand-curated list of Projects).
  Name it for the engagement. The official MCP **does** expose an initiative-write tool —
  `save_initiative` (create/update) — so the engagement Initiative is reachable on backlogd's
  key-free MCP path; `save_status_update({ type: "initiative" })` posts initiative-level health.
  See `references/linear-mcp.md` for both. Auto-creating/attaching the Initiative on pickup is a
  *wiring* task tracked separately (init create + status-update roll-ups); until that lands,
  refer to the Initiative by name and don't fail if it's absent.

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
  signal `/backlogd:solve` looks for. AC items declare *how they are verifiable* via an
  optional kind prefix (`[test]` / `[manual]` / `[review]`; untagged defaults to
  `[review]`) — load **`skills/ac/`** before writing AC.
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
  result and the artifacts — and post a per-AC verdict. Per-kind branching: `[test]` items
  must point at a backticked command that exits 0; `[manual]` items batch into a
  PO-confirmation question; `[review]` items remain Claude judgement. Load
  **`skills/ac/`** for the grammar and contract.
- **Decide**: all met → `completed` (Done); gaps → back to *In Progress* with actionable rework
  notes (a fresh `solve` re-runs them); a genuine judgement call (or unanswered manual
  check) → leave it *In Review* and ask the product owner. It does not re-dispatch.

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
  *Agents platform's* **agent sessions and webhooks** (the full Agent Interaction
  Protocol — `actor=app` token + a webhook server) stay **out of scope**: they breach the
  key-free / serverless principle. The MCP **`delegate` field** is **now wired into the
  solve pickup** — the scrum-master sets `delegate:"backlogd"` on the In Progress
  transition (`skills/solve/dispatch.md` step 1; the write shape, best-effort contract, and
  leave-on-completion default live in `skills/solve/identity.md`). The Tier-1 gate has
  passed: it was verified live (NB-390, 2026-06-02) and
  [ADR-006](../../docs/standards/adrs/ADR-006-tier2-locally-hosted-agent-identity.md) AC#7
  carried Tier-1 forward as the first rung (delegate to one installed agent app user, no
  server). The write is **best-effort** — on a workspace without the agent app user
  installed it errors or no-ops and the pickup carries on. The broader Agents-platform
  surface (agent sessions, webhooks, `actor=app`) remains out of scope here per the Tier-2
  guard above.
