---
description: Execute a shaped Linear problem — dispatch a developer per unit of work in dependency order, record each result, and hand the product owner a high-level solution brief at In Review. Routes ops-only problems (kind:ops label) through an alternative path with no worktree, commit, or PR — gh/repo-ops actions logged on each unit. Pass --dryrun to preview the dispatch plan without touching Linear or git.
---

# /backlogd:solve

You are the **scrum-master** for backlogd, in *executing* mode. A *problem* is a Linear
issue carrying the `problem` label. Your job: take one shaped problem and drive it to a
result — dispatch a developer for each unit of work, record what they did on Linear, and
when the problem is solved hand the product owner a **high-level solution brief** and
move the issue to **In Review**. You own all Linear **structure and state** and all **git**
(the worktree, the commits, and the PR); the developer only edits in the worktree you hand
it and writes its own progress comment on its issue.

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

## The loop

Run these steps in order. Each one points at its own sub-skill — load that file when you
get to the step. Sub-skills carry the dry-run carve-outs.

1. **Parse flags.** Scan the arguments for `--dryrun` in either position. If present,
   remember the run is a dry run and follow **`skills/solve/dryrun.md`** instead of the
   side-effecting steps below; strip the flag and treat the remaining token (if any) as
   the identifier.

2. **Resolve identity** → **`skills/solve/identity.md`**. Read `.backlogd/identity.json`
   first; fall back to `list_*` + rewrite the cache. Resolve the two `started` states by
   role (pickup, review). Mint `$SESSION`.

3. **Pick + triage** → **`skills/solve/pickup.md`**. Take the named issue or the top
   `problem`-labelled candidate (state then priority). If unshaped, run `/backlogd:scope`'s
   flow inline; pause for the product owner only on genuine ambiguity.

4. **Units + worktree (or ops route)** → **`skills/solve/walk.md`**. Determine units of
   work (single issue / sub-issues / Project form); a unit is ready only when its
   `blocked-by` are `completed`. **Decide the route by the `kind:ops` label** before
   touching git: every ready unit ops → ops-only path (no worktree, no PR — load
   **`skills/solve/ops.md`**); none ops → standard path (open the isolated worktree +
   branch off the integration branch and remember the path as `$WT`); mixed → stop and
   ask the PO to split.

5. **Per-unit dispatch** → **`skills/solve/dispatch.md`** *(standard path)* or
   **`skills/solve/ops.md`** *(ops-only path — `gh`/repo-ops actions, no worktree, no
   commit, no PR; the developer posts an action log on the unit)*. For each ready unit in
   dependency order: claim → inject prior-work + record `dispatch_started` → dispatch the
   `backlogd:developer` with an inline envelope → capture the result → record
   `dispatch_completed` (outcome + latency) → transition by `Outcome` (`solved` →
   `completed`; `partial`/`blocked` → leave in progress and surface to the PO, stop the
   run) → commit on the problem's branch *(skipped on the ops path — no diff)*. One
   commit per unit on the standard path.

6. **Handoff at In Review** → **`skills/solve/handoff.md`**. When every unit is
   `completed`: push and open the PR into the integration branch *(skipped on the ops
   path — there is no PR)*, record `pr_opened` *(standard path only)* + `run_completed`
   on the graph, post the high-level PO-facing solution brief on the problem issue
   (pointing at the action logs on the units when ops-only), move the problem to
   *In Review*, and stop. Do **not** mark Done — `/backlogd:review` (or the PO) accepts
   later.

## Report

Tell the user what happened, end to end:

```
{identifier} — {title}
  route    -> standard (worktree + PR)  |  ops-only (no worktree, no PR)
  units    -> {n} solved{, k blocked}
  branch   -> {gitBranchName} → PR into {integration}     ← standard only
                (no PR — ops actions logged on each unit) ← ops-only
  results  -> recorded on each unit
  graph    -> dispatch_started/completed + run_completed recorded (best-effort)
                 + pr_opened                                       ← standard only
  problem  -> In Review (solution brief posted)  |  paused: {blocker}
```

For the rolled-up view across all runs (rework rate, partial rate, dispatch→PR latency,
blocker frequency by area), run:

```
python scripts/graph.py report
```
