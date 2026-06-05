---
name: solve-dryrun
description: The --dryrun output contract for /backlogd:solve — what may be read, what must never be written, and the exact labelled plan sections (identity / picked / triage / unit walk / per-unit envelope) to print before exiting.
---

# solve — dry-run mode

When `--dryrun` is set, run the loop as a **preview**: every read you would normally do,
but **no writes** — Linear, git, or graph — and **no developer dispatch**. The output is
the plan; the world is untouched.

> **`--dryrun` ≡ `mode:report-only` (NB-356 alias, one contract, no fork).** The shared
> verb token `mode:report-only` (`skills/common/argument-tokens.md`) is the cross-verb
> generalisation of NB-317's `--dryrun`. On `solve` the two are **the same contract**: when
> the run carries `mode:report-only` *or* `--dryrun`, follow this file verbatim. `solve`
> recognises both spellings and treats them identically — there is **no behavioural fork**
> between them. `--dryrun` is retained as a documented alias (NB-356 does not deprecate it).
> Read "`--dryrun`" throughout this file as "`--dryrun` or `mode:report-only`".

The **ship-on-green** final phase (`commands/solve.md` step 8 → `skills/solve/ship.md`)
**never runs under `--dryrun`** — the dry run exits after printing the plan, so there is no
reviewer dispatch and no merge. `--no-ship` is independent of `--dryrun`: parse it (and
`BACKLOGD_SHIP_ON_GREEN=0`) the same way and note in the plan whether the real run *would*
ship-on-green or hold at In Review (see the output contract below), but take no action either
way under dryrun.

## Allowed (reads only)

- **Linear:** `list_*` / `get_*` to resolve identity, find the problem, walk the units;
  use `includeRelations: true` per unit to show `blocked-by`. The Step 0 pre-load (see
  `commands/solve.md` → "Pre-load deferred tools") runs a **read-only** `ToolSearch`
  call across the canonical Linear MCP tool list — safe under dryrun and **recommended**
  even there so the dispatch-plan render proceeds normally. The fallback idiom's
  `save_comment` nudge (used only if `ToolSearch` is unavailable) is a write and
  **must not** run under dryrun.
- **Graph:** `python scripts/graph.py prior-work --problem {identifier}` per unit; a
  graph failure falls through with an empty block.
- **Resume reconcile reads** (`skills/solve/resume.md`): `python scripts/graph.py
  run-status --problem {unit}` per unit, `git ls-remote --heads origin
  {gitBranchName}`, `git branch --list {gitBranchName}`, `git worktree list
  --porcelain`, and (if a worktree at the expected path exists) `git -C "$WT" status
  --porcelain` / `rev-parse HEAD`. Pure reads — no `git worktree add`, no `checkout`.
  Render the classification in section (d) of the plan; never act on it.

## Forbidden

- **No `mcp__linear__save_*`** (state, description, relations, comments, projects).
- **No git mutation.** No `worktree add`, `checkout / commit / push`, `gh pr create / merge`.
  Compute the path + branch name you *would* use; do not create them.
- **No graph writes** — read-side `graph.py` only (`prior-work`, `report`).
  No `dispatch-start` / `dispatch-end` / `pr-opened` / `run-end` / `rework` /
  `labeled` / legacy `emit`.
- **No developer dispatch** — do not call `Agent`; print the envelope verbatim.
- **No ship-on-green phase** — do not dispatch the verdict reviewer and do not merge. The
  dry run exits after the plan; `skills/solve/ship.md` never runs under dryrun.
- **No inline triage write** — describe what `/backlogd:scope` *would* do in (c); the dry
  run exits whether shaped or not.

## Output contract — print in this exact order

```text
[dry-run] /backlogd:solve {identifier|<top of queue>}

(0) Pre-load plan (NB-340)
  pre-load would call: mcp__linear__get_issue, mcp__linear__list_comments, mcp__linear__save_comment
  load-bearing for the developer's [backlogd developer] comment on each unit

(a) Identity
  team / states (pickup, review, completed by type) / labels ("problem", "kind:ops" if present) / session id

(b) Picked problem
  {identifier} — {title} / state ({type}) / shaped? yes|no / kind:ops? yes|no

(c) Triage decision
  "already shaped — proceeding"
  | "not shaped — would run /backlogd:scope inline (spec + AC, decompose if earned, pause PO if ambiguous)"

(d) Unit walk plan
  route: standard (worktree + PR) | ops-only (no worktree, no PR) | mixed (would stop + ask PO)
  worktree path / branch off origin/{integration}      ← standard only; for ops-only print
                                                          "(no worktree — ops path)";
                                                          for resume-reuse print "(reuse existing)"
  concurrency_max: $BACKLOGD_CONCURRENCY_MAX (default 2, clamped to [1,4])
  parallel groups (computed read-only — for each group: unit ids, group size, per-unit
         sub-branch + worktree path the real run would create at
         backlogd-wt-{identifier}-unit-{unit}; size==1 groups print as "(sequential)").
         Show every group in dispatch order; the peak group size is the run's
         peak_fanout — note it explicitly.
  units (dispatch order, with blocked-by + ready? + kind:ops? + resolved subagent_type per
         unit + resume class: completed / in-progress-mine / untouched / inconsistent)

(e) Per-unit dispatch envelope — verbatim, for each unit
  (standard envelope from `skills/solve/dispatch.md` step 3 with `{$WT path}` for code
  units in a sequential group, or `{$WT_unit path}` for code units in a parallel group
  — i.e. the per-unit sub-worktree path the real run would use; ops envelope from
  `skills/solve/ops.md` step 3 — no `$WT` line — for `kind:ops` units; include the
  `## Prior work` block when the query printed one. Above the envelope for code units,
  print the resolved `subagent_type` for this unit — see `skills/solve/dispatch.md`
  step 2 for the resolution rule; in dry run, surface any ambiguity (multiple `agent:*`
  labels) or missing-specialist as a note **without** exiting — the run is read-only.
  When the unit is in a parallel group, also print a single-line annotation **above the
  envelope** noting "parallel group {n}/{total}, size {k}" so the preview makes the
  fanout obvious.)

(f) Ship-on-green plan
  ship-on-green: on (default) | off (--no-ship | BACKLOGD_SHIP_ON_GREEN=0)
  on a real run the happy path would: auto-chain the verdict review → on fully-green
       (every AC MET + every DoD MET + CI green + zero [manual]/needs-PO) run the base-race guard
       and squash-merge into origin/{integration} → Done; off → hold at In Review.
  (ops-only: no PR to merge — accept moves straight to Done.)
```

Exit with: `[dry-run] no writes performed — Linear, git, and graph are unchanged.`

## Edge cases

- **No problem to pick** — print the standard "No problems to solve…" message and exit.
- **Unshaped problem** — print (a)–(c), note the real run would invoke scope inline (or
  pause for the PO on ambiguity), skip (d) and (e).
- **Ops-only problem** — print all sections; in (d) note `route: ops-only (no worktree, no
  PR)` and skip the worktree-path line; in (e) print the ops envelope from
  `skills/solve/ops.md` per unit.
- **Mixed units** — print (a)–(c); in (d) note `route: mixed — would stop and ask PO to
  split or pick one path`; skip (e).
- **Resume `inconsistent`** — print sections (a)–(d), label the unit `inconsistent`, and
  print the pause message template from `skills/solve/resume.md` § 4 inside (d). Skip (e);
  a real run would not dispatch. The dry-run still exits cleanly (it acts on nothing).
- **Linear MCP not connected** — same as the real run: stop and ask the user to enable it.
