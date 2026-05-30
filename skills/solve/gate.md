---
name: solve-gate
description: Per-unit quality gate — dispatch the tester after the developer, then the reviewer in pre-commit-gate mode (both skipped on kind:ops runs), with a formal 2-round hard cap on combined re-dispatches. Surface failing tests + needs-changes verdicts as rework notes back through dispatch.md.
---

# solve — per-unit quality gate

This skill loads from `skills/solve/dispatch.md` **between step 5 ("Confirm its record")
and step 6 ("Record dispatch completion on the graph")** on the
standard path. It owns the developer↔tester↔reviewer loop: dispatch the tester against
the unit, then the reviewer to gate the diff before commit, and either return `ok`
(continue) or `needs-changes` with rework notes so dispatch.md can re-dispatch the
developer — subject to a 2-round hard cap.

It is **skipped on `kind:ops` runs** — `skills/solve/walk.md` routes those through
`skills/solve/ops.md`, which never loads this skill. Both the tester and the reviewer's
`pre-commit-gate` mode share this skip rule — there is no diff to test or gate.

> **Dry run:** in `--dryrun` mode this skill does not run. Render the planned tester
> and reviewer envelopes read-only as part of the per-unit dispatch plan and follow
> `skills/solve/dryrun.md`. No `Agent` call, no comment.
>
> **Resume:** the gate is **idempotent** — on resume, re-dispatch the tester and
> reviewer from scratch against the unit's latest state. `gate_round` resets to 0 per
> unit on resume.

## 1. Dispatch the tester

Call the `backlogd:tester` subagent with the Agent tool, handing it the unit as an
**inline** envelope. Include the unit's issue id and point it at the developer's
`**[backlogd developer]**` progress comment:

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
`untestable:` lists. Verify the `**[backlogd tester]**` evidence comment landed; do
**not** re-post it. Add at most a one-line orchestrator note if the comment is missing.

## 2. Dispatch the reviewer (pre-commit-gate)

Call the `backlogd:reviewer` subagent with the Agent tool in **`pre-commit-gate`** mode,
handing it the same unit as an **inline** envelope. Include the unit's issue id, the
worktree path, and pointers to both the developer's and tester's progress comments:

> Gate this unit's pre-commit diff against its acceptance criteria and the Definition of
> Done. Mode: **pre-commit-gate**. Inspect the worktree diff, judge each AC + DoD line,
> roll up to `ok` / `needs-changes`, post your progress to your issue, then report.
>
> Worktree to inspect: {$WT}
>
> Unit ({identifier}, issue id {id}): {title}
>
> Acceptance Criteria:
> {the `## Acceptance Criteria` block from the unit description}
>
> Developer's progress comment (what they changed):
> {body of the `**[backlogd developer]**` comment on this unit}
>
> Tester's progress comment (what they proved):
> {body of the `**[backlogd tester]**` comment on this unit}

Capture the reviewer's final structured summary verbatim, including its `verdict:`
(`ok` / `needs-changes`) and any `notes:`. Verify the `**[backlogd reviewer]**` comment
landed; do **not** re-post it.

## 3. Act on gate verdicts (unified)

Combine the tester's `failing:` + `untestable:` lists and the reviewer's `verdict:` +
`notes:` into a single decision:

- **Both `ok`** (tester `failing: []` and reviewer `verdict: ok`) — gate returns
  **`ok`**. If the tester captured `untestable:` items, carry them forward so
  `skills/solve/handoff.md` can surface them in the PO-facing solution brief under
  *"Needs your eyes"*. Untestable items do **not** auto-block.
- **Either is red** (tester `failing:` non-empty **or** reviewer `verdict:
  needs-changes`) — gate returns **`needs-changes`** with combined rework notes:
  failing-test names (and the AC each one proves) plus the reviewer's notes —
  **subject to the cap below**.

## 4. Enforce the 2-round hard cap

Combined across tester-failure re-dispatches **and** reviewer needs-changes
re-dispatches, the gate caps re-dispatches at **2 rounds** per unit. Use a small
explicit counter:

- `gate_round` starts at **0** when the gate first runs for a unit.
- On every `needs-changes` outcome that would re-dispatch the developer, **increment
  `gate_round`** before handing back to dispatch.md.
- On the **3rd would-be re-dispatch** (i.e. when incrementing would push `gate_round`
  past 2), return **`blocked`** (not `needs-changes`) with the accumulated notes from
  all rounds. dispatch.md's step 7 treats a gate `blocked` exactly like a developer
  `STATUS: BLOCKED` (it routes through `skills/solve/capture.md`'s `BLOCKED` branch):
  leave the unit in progress, surface to the product owner via the orchestrator's pause
  path (see `commands/solve.md` step 6 + dispatch.md step 7), and stop the run.

The counter is per-unit and lives in the scrum-master's working context across the
loop; nothing is persisted.

## 5. Hand back to dispatch.md

Return one of:

- **`ok`** — continue to dispatch.md step 6. Carry any `untestable:` items forward for
  the handoff brief.
- **`needs-changes`** — return combined rework notes; dispatch.md re-enters its step 3
  (resolved-specialist dispatch) with those notes prepended, then re-enters this skill.
  `gate_round` has been incremented.
- **`blocked`** — the 2-round cap is exhausted; return accumulated notes. dispatch.md
  step 7 treats this like a developer `STATUS: BLOCKED` (the `BLOCKED` branch in
  `skills/solve/capture.md`), the orchestrator pauses, and the run stops.
