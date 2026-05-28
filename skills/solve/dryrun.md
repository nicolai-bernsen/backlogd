---
name: solve-dryrun
description: The --dryrun output contract for /backlogd:solve — what may be read, what must never be written, and the exact labelled plan sections (identity / picked / triage / unit walk / per-unit envelope) to print before exiting.
---

# solve — dry-run mode

When `--dryrun` is set, run the loop as a **preview**: every read you would normally do,
but **no writes** — Linear, git, or graph — and **no developer dispatch**. The output is
the plan; the world is untouched.

## Allowed (reads only)

- **Linear:** `list_*` / `get_*` to resolve identity, find the problem, walk the units;
  use `includeRelations: true` per unit to show `blocked-by`.
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
- **No inline triage write** — describe what `/backlogd:scope` *would* do in (c); the dry
  run exits whether shaped or not.

## Output contract — print in this exact order

```
[dry-run] /backlogd:solve {identifier|<top of queue>}

(a) Identity
  team / states (pickup, review, completed by type) / label "problem" / session id

(b) Picked problem
  {identifier} — {title} / state ({type}) / shaped? yes|no

(c) Triage decision
  "already shaped — proceeding"
  | "not shaped — would run /backlogd:scope inline (spec + AC, decompose if earned, pause PO if ambiguous)"

(d) Unit walk plan
  worktree path / branch off origin/{integration}   (or "reuse existing" if resume found one)
  units (dispatch order, with blocked-by + ready? + resume class:
         completed / in-progress-mine / untouched / inconsistent)

(e) Per-unit dispatch envelope — verbatim, for each unit
  (same envelope `skills/solve/dispatch.md` step 2 hands the developer, with the {$WT
  path} and the `## Prior work` block — omit the block if the query printed nothing)
```

Exit with: `[dry-run] no writes performed — Linear, git, and graph are unchanged.`

## Edge cases

- **No problem to pick** — print the standard "No problems to solve…" message and exit.
- **Unshaped problem** — print (a)–(c), note the real run would invoke scope inline (or
  pause for the PO on ambiguity), skip (d) and (e).
- **Resume `inconsistent`** — print sections (a)–(d), label the unit `inconsistent`, and
  print the pause message template from `skills/solve/resume.md` § 4 inside (d). Skip (e);
  a real run would not dispatch. The dry-run still exits cleanly (it acts on nothing).
- **Linear MCP not connected** — same as the real run: stop and ask the user to enable it.
