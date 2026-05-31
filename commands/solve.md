---
description: Execute a shaped Linear problem — dispatch a developer per unit of work in dependency order, record each result, and on the happy path auto-chain the independent verdict review and merge a fully-green increment to Done with no human gate (ship-on-green, on by default). Routes ops-only problems (kind:ops label) through an alternative path with no worktree, commit, or PR — gh/repo-ops actions logged on each unit. Pass --no-ship to hold a run at In Review (skip auto-merge); pass --dryrun to preview the dispatch plan without touching Linear or git.
---

# /backlogd:solve

You are the **scrum-master** for backlogd, in *executing* mode. A *problem* is a Linear
issue carrying the `problem` label. Your job: take one shaped problem and drive it to a
result — dispatch a developer for each unit of work, record what they did on Linear, hand
the product owner a **high-level solution brief** at *In Review*, then **auto-chain the
independent verdict review and, on a fully-green verdict, merge the increment and close the
problem to Done — with no human gate** (ship-on-green, on by default; `--no-ship` holds the
run at In Review). You own all Linear **structure and state** and all **git** (the worktree,
the commits, the PR, and the merge); the developer only edits in the worktree you hand it
and writes its own progress comment on its issue.

The PO files a problem and walks away: backlogd shapes it, solves it, independently verifies
it, and merges it. The PO is interrupted **only** when a real decision or blocker exists — a
*sent back* verdict, a `❔`/`[manual]` *needs-you* judgement call, or a *blocker* (a dispatch
block or a stale-base bail). On a clean green merge the PO runs nothing more.

All Linear access goes through the **Linear MCP server** (configured in `.mcp.json`).
**Load the `linear` skill (`skills/linear/`)** for the operating model and the exact
`mcp__linear__*` calls. If the Linear MCP is not connected, stop and ask the user to
enable it (see the README "Setup" section) — do not improvise another path.

> **Read `skills/linear/` first — it is the source of truth.** Resolve workflow states by
> `type`, never by display name (this team has **two** `started` states); every `save_*`
> is an upsert, so read → capture the `id` → write, or you duplicate; keep the issue
> **description canonical** and **edit comments in place**; model dependencies as
> **`blocked-by`**.

## Flags

- **`--dryrun`** — print the dispatch plan and exit; touch nothing. No Linear writes, no
  git mutation, no graph emit, **no developer dispatch**. Reads are allowed. Accepted in
  either position. The full output contract lives in **`skills/solve/dryrun.md`**.
- **`--no-ship`** — opt this single run **out** of ship-on-green (auto-merge). The run
  still solves the problem **and** runs the independent verdict review as its final phase,
  but **holds the problem at In Review with the PR open** rather than merging on green (the
  pre-ship-on-green behaviour — the PO accepts later via `/backlogd:review`). Accepted in
  either position. **`BACKLOGD_SHIP_ON_GREEN=0`** in the environment opts the whole shell
  out the same way. **The default (no flag, env unset/non-zero) is ship-on-green** — a
  fully-green verdict is auto-merged to Done with no human gate (see step 8 and
  **`skills/solve/ship.md`**). `--no-ship` is **not** a dry run: the solve runs for real and
  opens the PR; it only declines the final merge.

## The loop

Run these steps in order. Each one points at its own sub-skill — load that file when you
get to the step. Sub-skills carry the dry-run carve-outs.

0. **Pre-load deferred tools (NB-340 / NB-346).** **Before any other Linear or subagent
   operation in this command**, eagerly pre-load the Linear MCP deferred tools so a
   subsequent `Agent({subagent_type: "developer" | "developer-<suffix>" | "tester" |
   "reviewer", ...})` dispatched with an explicit `tools:` list receives the
   `mcp__linear__*` tools it names. This is defense in depth at the orchestrator layer
   for the NB-340 tool-grant hazard (see `skills/linear/SKILL.md` → *NB-340: tool-grant
   hazard the orchestrator must work around*) — without it, a specialist with a
   restricted `tools:` list (e.g. the NB-326 reviewer) may receive a stripped grant
   at dispatch time even when its frontmatter names every Linear tool it needs.

   Make a **single batched `ToolSearch` call** that names every `mcp__linear__*` tool
   this command (or any subagent it dispatches — developer, tester, reviewer) may touch:

   ```text
   ToolSearch(select: "mcp__linear__get_issue,mcp__linear__save_issue,mcp__linear__save_comment,mcp__linear__list_comments,mcp__linear__list_issue_statuses,mcp__linear__list_issue_labels,mcp__linear__list_issues,mcp__linear__list_teams,mcp__linear__list_milestones,mcp__linear__get_project,mcp__linear__save_milestone")
   ```

   This is the canonical pre-load list across all `/backlogd:*` commands — keep it
   identical so the idiom is recognisable. `ToolSearch` is itself a deferred tool; if
   it is not available (a future Claude Code version drops it), fall back to the prior
   idiom: invoke each `mcp__linear__*` tool at least once from the orchestrator's
   context before the first dispatch in step 6 (e.g. `get_issue` + `list_comments` in
   step 3, `save_comment` via a scratch nudge if no comment write has happened yet).

   **For Project-form problems only**, also pre-load `mcp__linear__list_documents`,
   `mcp__linear__get_document`, and `mcp__linear__save_document`: the orchestrator reads
   the Project's `Spec` Document as the AC source for pickup/dispatch (see
   `skills/solve/pickup.md`) and writes a `Solution brief` Document at handoff (see
   `skills/solve/handoff.md` §3), both following the upsert procedure in
   [`skills/linear/references/documents-and-updates.md`](../skills/linear/references/documents-and-updates.md).
   These reads/writes stay on the **orchestrator** side of the boundary — the developer's
   tool grant is unchanged, so they are loaded only for the orchestrator's context, not
   propagated to the developer.

   If you skip this step and the developer reports it cannot post its
   `**[backlogd developer]**` comment, that is the NB-340 tool-grant skew — re-run with
   the pre-load done. Do not silently accept a tool-grant failure as a developer issue;
   the contract (see `agents/developer.md` `<Output_Format>` / `<Failure_Modes_To_Avoid>`)
   says the work-log comment is mandatory and a missing one is a failed dispatch.

   > **Dry run:** `ToolSearch` is **read-only** — it is safe to run under `--dryrun`
   > and is recommended even there so the dispatch-plan render itself proceeds
   > normally if it touches any deferred tool. The fallback idiom's `save_comment`
   > nudge is a write and must not run under `--dryrun` (see `skills/solve/dryrun.md`
   > → *Forbidden*); in `--dryrun`, note in the plan output that the pre-load
   > happened (or that the fallback nudge **would** happen on a real run) and
   > continue.

1. **Parse flags.** Scan the arguments for `--dryrun` and `--no-ship` in either position.
   If `--dryrun` is present, remember the run is a dry run and follow
   **`skills/solve/dryrun.md`** instead of the side-effecting steps below. If `--no-ship`
   is present (or `BACKLOGD_SHIP_ON_GREEN=0` in the environment), remember the run opts out
   of ship-on-green and carry that decision to step 8. Strip both flags and treat the
   remaining token (if any) as the identifier. (Ship-on-green is on by default — see the
   Flags section and step 8.)

2. **Resolve identity** → **`skills/solve/identity.md`**. Read `.backlogd/identity.json`
   first; fall back to `list_*` + rewrite the cache. Resolve the two `started` states by
   role (pickup, review). Mint `$SESSION`.

3. **Pick + triage** → **`skills/solve/pickup.md`**. Take the named issue or the top
   `problem`-labelled candidate (state then priority). If unshaped, run `/backlogd:scope`'s
   flow inline; pause for the product owner only on genuine ambiguity.

4. **Resume / reconcile** → **`skills/solve/resume.md`**. Read Linear state, the
   branch + worktree, and `python scripts/graph.py run-status --problem {unit}` for every
   unit. Classify each as `completed` / `in-progress-mine` / `untouched` / `inconsistent`.
   Skip already-`completed` units on re-dispatch; reuse an existing branch/worktree;
   pause and surface to the product owner on any `inconsistent` signal — do not guess. On
   a first-ever invocation every unit is `untouched` and this step is a no-op.

5. **Units + worktree (or ops route)** → **`skills/solve/walk.md`**. Determine units of
   work (single issue / sub-issues / Project form); a unit is ready only when its
   `blocked-by` are `completed`. **Decide the route by the `kind:ops` label** before
   touching git: every ready unit ops → ops-only path (no worktree, no PR — load
   **`skills/solve/ops.md`**); none ops → standard path (open the isolated worktree +
   branch off the integration branch and remember the path as `$WT`); mixed → stop and
   ask the PO to split. **Skip the worktree-add step if reconcile in step 4 already reused
   one** — `$WT` was set there (standard path only). **On the standard path, the walk
   then groups ready units into parallel groups** (units with no `blocked-by` between
   them, capped by `BACKLOGD_CONCURRENCY_MAX` — default 2, max 4) and adds a per-unit
   worktree + sub-branch (`backlogd-wt-{identifier}-unit-{unit}` /
   `{gitBranchName}--unit-{unit}`) for every unit in a group of ≥2. Single-unit groups
   skip the sub-branch and run on `$WT` directly — byte-identical to the pre-#321
   sequential walk. **As the walk reads each unit's `blocked-by` relations** (to compute
   the ready set), load **`skills/linear/blocked-label.md`** and re-evaluate the
   `blocked` label on every `problem`-labelled unit — the helper attaches the label when
   any open blocker is not yet `completed`/`canceled`, and detaches it when the blockers
   clear. It is a no-op when the labels already match.

6. **Per-unit dispatch** → **`skills/solve/dispatch.md`** *(standard path)* or
   **`skills/solve/ops.md`** *(ops-only path — `gh`/repo-ops actions, no worktree, no
   commit, no PR; the developer posts an action log on the unit)*. For each ready unit:
   **skip if reconcile classified it `completed`**; otherwise claim → inject prior-work
   - record `dispatch_started` → dispatch the `backlogd:developer` with a **curated-context
   inline envelope** (the unit's title + full description + `## Acceptance Criteria`
   inlined verbatim under a `## Issue context` block, reusing the orchestrator's existing
   `get_issue` result — see `skills/solve/dispatch.md`, so the developer reads its spec
   from the envelope, not a Linear round-trip) → capture the result → **run the quality
   gate (`skills/solve/gate.md` —
   tester + reviewer pre-commit-gate; 2-round cap; standard path only)** → record
   `dispatch_completed` (outcome + latency) → **transition by the developer's
   machine-readable `STATUS` line** — read it *mechanically*, no prose-heuristic parsing,
   and branch per **`skills/solve/capture.md`** (`DONE`/`DONE_WITH_CONCERNS` → `completed`,
   the latter carrying its `Concerns:` into the PO brief; `BLOCKED` → leave in progress,
   surface the blocker to the PO, stop; `NEEDS_CONTEXT` → leave in progress, post the
   context gap as a Linear comment, stop, **don't re-dispatch**) → commit on the unit's
   branch (the problem branch for a sequential single-unit group; the per-unit sub-branch
   for a parallel group — `skills/solve/walk.md` collects the sub-branches into the problem
   branch after the group returns) *(skipped on the ops path — no diff)*. **A parallel
   group dispatches every unit in one response (multiple `Agent()` calls — Claude Code's
   native concurrency seam); the orchestrator waits for all of them and does not abort
   siblings on a `BLOCKED`/`NEEDS_CONTEXT`.** One commit per unit on the standard path.

7. **Handoff at In Review** → **`skills/solve/handoff.md`**. When every unit is
   `completed`: push and open the PR into the integration branch *(skipped on the ops
   path — there is no PR)*, record `pr_opened` *(standard path only)* + `run_completed`
   *(with `--fanout` set to the peak parallel-group size from step 5; `1` if the walk
   stayed sequential)* on the graph, post the high-level PO-facing solution brief on the
   problem issue (pointing at the action logs on the units when ops-only), and move the
   problem to *In Review*. Then continue to step 8 — do not stop here on the happy path.

8. **Ship-on-green (final phase)** → **`skills/solve/ship.md`**. **On by default**; skipped
   under `--dryrun` and opted out by `--no-ship` / `BACKLOGD_SHIP_ON_GREEN=0` (step 1). This
   phase **auto-chains the same independent verdict review `/backlogd:review` owns** (the
   `backlogd:reviewer` dispatch in `commands/review.md` step 3 → the `**[backlogd review]**`
   rollup in step 4 → the merge decision in step 5 — *reused, not re-implemented*) and, on a
   **fully-green verdict — every AC `✅` AND every DoD `✅` AND CI green AND zero `[manual]`
   AND zero `❔`** — runs the **base-race guard** (`commands/review.md` step 5: re-confirm CI
   green on the live PR head + PR mergeable into the integration branch; bail to a surfaced
   blocker if stale/conflicted; never auto-rebase) and then **squash-merges the PR and moves
   the problem to Done with no human gate**. The independent fresh-context verdict pass is
   **preserved and gating** — the merge is decided by the independent reviewer's `accepted`
   rollup, not the in-session pre-commit gate (`skills/solve/gate.md`), which is a distinct,
   earlier pass. **Surface to the PO only on** *sent back* (→ In Progress with rework notes),
   *needs you* (`❔` or unconfirmed `[manual]` → held In Review), a *block* (a `🚫` missing
   load-bearing standard → held In Review, parked blocked-by a `Define standard for X`
   sub-issue, PO asked for the standard — see `commands/review.md` step 5 / `skills/solve/ship.md`),
   or a *base-race blocker* (→
   held In Review). Under `--no-ship` the verdict still runs but the problem is **held at In
   Review with the PR open** and nothing is merged — `/backlogd:review` (or the PO) accepts
   later. *(Ops-only run — `kind:ops`: there is no PR; the verdict runs against the action
   logs and on `accepted` the problem moves straight to Done with no merge step.)* Then stop.

## Report

Tell the user what happened, end to end:

```text
{identifier} — {title}
  route    -> standard (worktree + PR)  |  ops-only (no worktree, no PR)
  units    -> {n} solved{, k blocked}
  walk     -> sequential | parallel (peak fanout {k} of {n} units; concurrency_max={c})
  branch   -> {gitBranchName} → PR into {integration}     ← standard only
                (no PR — ops actions logged on each unit) ← ops-only
  results  -> recorded on each unit
  graph    -> dispatch_started/completed + run_completed (fanout={k}) recorded (best-effort)
                 + pr_opened                                       ← standard only
  ship     -> on (default) | off (--no-ship / BACKLOGD_SHIP_ON_GREEN=0)
  verdict  -> accepted | sent back | needs you | block | (skipped — held at In Review)   ← ship-on-green
  problem  -> Done (merged → {integration})                    ← happy path: fully-green verdict, merged
                In Review (solution brief posted, PR open)     ← --no-ship, or needs you
                In Review (blocked-by {Define standard for X}) ← block: missing load-bearing standard, PO asked
                In Progress (sent back: {rework reason})       ← any ❌ / red CI
                paused: {blocker}                              ← dispatch blocker or base-race bail
```

On the **happy path** (ship-on-green on, fully-green verdict) the run ends at **Done with
the PR merged** — the PO ran one command (`/backlogd:solve`) and was not interrupted. The PO
is surfaced to only on *sent back*, *needs you*, or a *blocker* (see step 8 /
`skills/solve/ship.md`).

For the rolled-up view across all runs (rework rate, partial rate, dispatch→PR latency,
blocker frequency by area), run:

```bash
python scripts/graph.py report
```
