---
name: solve-gate
description: Per-unit quality gate — dispatch the tester after the developer reports solved (skipped on kind:ops runs), surface failing tests as re-dispatch notes back through dispatch.md. NB-335 extends this with the reviewer pre-commit-gate and a formal 2-round cap.
---

# solve — per-unit quality gate

This skill loads from `skills/solve/dispatch.md` **between step 4 ("Confirm the
developer's record") and step 5 ("Record dispatch completion on the graph")** on the
standard path. It owns the developer↔tester loop: dispatch the tester against the unit
the developer just edited, read its evidence report, and either return `ok` (continue
the dispatch) or `needs-changes` with rework notes so dispatch.md can re-dispatch the
developer.

It is **skipped on `kind:ops` runs** — `skills/solve/walk.md` routes those through
`skills/solve/ops.md`, which never loads this skill. There is no diff to test.

> **Dry run:** in `--dryrun` mode this skill does not run. Render the planned tester
> envelope read-only as part of the per-unit dispatch plan and follow
> `skills/solve/dryrun.md`. No `Agent` call, no comment.

> **Resume:** the gate is **idempotent** — on resume, re-dispatch the tester from
> scratch against the unit's latest state. The developer↔tester loop is cheap relative
> to the developer; no separate resume state is needed.

<!-- TODO(NB-335): formal 2-round cap when the reviewer pre-commit-gate joins the loop. -->

## 1. Dispatch the tester

Call the `backlogd:tester` subagent with the Agent tool, handing it the unit as an
**inline** envelope. Include the unit's issue id so it can post its progress there, and
point it at the developer's `**[backlogd developer]**` progress comment so it knows what
to test:

> Test this unit against its acceptance criteria. Prove each testable AC with an
> automated test, name the untestable ones, post your progress to your issue, then
> report.
>
> Work in this worktree — write your tests under it: {$WT}
>
> Unit ({identifier}, issue id {id}): {title}
>
> Acceptance Criteria:
> {the `## Acceptance Criteria` block from the unit description}
>
> Developer's progress comment (what they changed):
> {body of the `**[backlogd developer]**` comment on this unit}

Capture the tester's final structured summary verbatim, including its `failing:` and
`untestable:` lists.

## 2. Confirm its record

The tester posts its own `**[backlogd tester]**` evidence comment on the unit issue.
Verify it landed; do **not** re-post it yourself. Add at most a one-line orchestrator
note only if the comment is genuinely missing.

## 3. Act on the tester report

Read the tester's `failing:` and `untestable:` lists and decide:

- **`failing: []` and `untestable: []`** — full evidence; gate returns **`ok`**.
- **`failing: []` and `untestable:` non-empty** — the testable AC are covered, the
  untestable items are named. Gate returns **`ok`**; capture the `untestable:` list so
  `skills/solve/handoff.md` can surface it in the PO-facing solution brief under
  *"Needs your eyes"*. Untestable items do **not** auto-block.
- **`failing:` non-empty** — gate returns **`needs-changes`** with the failing-test
  names (and the AC each one proves) as rework notes. `dispatch.md` re-dispatches the
  developer with those notes prepended to the envelope, then re-enters this skill
  fresh. Re-dispatch is informal for now; the formal 2-round hard cap lands with the
  reviewer pre-commit-gate in NB-335.

## 4. Hand back to dispatch.md

Return one of:

- **`ok`** — continue to dispatch.md step 5 (`Record dispatch completion`). Carry any
  captured `untestable:` items forward for the handoff brief.
- **`needs-changes`** — return the failing-test names + the AC each one proves as
  rework notes. dispatch.md re-enters its step 3 (developer dispatch) with those notes
  prepended to the envelope, then re-enters this skill.
