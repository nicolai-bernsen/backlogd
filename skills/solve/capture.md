---
name: solve-capture
description: The deterministic STATUS-branch playbook for /backlogd:solve — read the developer's (or any specialist's) machine-readable STATUS line and map it, with no prose-heuristic parsing, to a Linear state transition, an orchestrator action, and a coarse-grained graph outcome. Loaded by skills/solve/dispatch.md step 7 (and consulted by walk.md for the parallel-group path). The four values are DONE, DONE_WITH_CONCERNS, BLOCKED, NEEDS_CONTEXT.
---

# solve — capture the STATUS and branch deterministically

Every specialist's final report **opens with a machine-readable `STATUS: <enum>` line**
(the contract is in `agents/developer.md` `<Output_Format>` and, canonically, in
[`docs/specialists.md`](../../docs/specialists.md) → *The STATUS contract*). This skill is
how the orchestrator turns that line into action. The whole point of the contract is that
the orchestrator **parses STATUS mechanically** — it reads the first line, matches it
against the four-value enum, and follows the row below. It does **not** scan the free-text
body for words like "blocked" or "done" to guess the transition; the prose under STATUS is
for humans, not for the dispatch loop.

> This skill is loaded from **`skills/solve/dispatch.md` step 7** ("Transition the unit").
> `skills/solve/walk.md` consults the same table for the parallel-group stop condition (a
> group stops the run when any unit returns a *non-terminal* STATUS — `BLOCKED` or
> `NEEDS_CONTEXT`). Keep the three coherent: this table is the single source of truth.

## Read the STATUS line

Take the **first line** of the captured final report. Strip the leading `STATUS:` and
trim. You must end up with **exactly one** of:

```text
DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
```

If the first line is **not** a `STATUS:` line, or the value is **not** one of the four,
treat it as a contract violation (see *Malformed STATUS* below) — do **not** fall back to
prose-heuristic parsing of the body.

## The branch table

| `STATUS` | Linear transition | Graph outcome (`dispatch-end --outcome`) | Orchestrator action |
| --- | --- | --- | --- |
| `DONE` | → the unit's **`completed`** (In Review) state | `solved` | Accept the unit. Continue the loop: quality gate (`gate.md`) → commit → next unit. On the last unit, handoff posts the solution brief and moves the **problem** to In Review. |
| `DONE_WITH_CONCERNS` | → the unit's **`completed`** (In Review) state | `solved` | Same as `DONE` — the increment is mergeable-pending-review — **and carry the developer's `Concerns:` text forward** so `skills/solve/handoff.md` surfaces it in the PO solution brief under *Needs your eyes*. (This rides the same forward-carry channel the gate uses for `untestable:` items.) |
| `BLOCKED` | **stay** in the unit's started (In Progress) state | `blocked` | Surface the developer's `Next:` blocker to the PO as a clear question — a genuine blocker, do not guess past it. **Stop the run** (sequential) or finish the parallel group then stop (see walk.md). |
| `NEEDS_CONTEXT` | **stay** in the unit's started (In Progress) state | `blocked` | Post the developer's `Next:` context gap as a **Linear comment** on the unit for the PO to fill. **Do not re-dispatch** the specialist — the spec must change first. **Stop the run** (or finish the parallel group then stop). |

> **Claim-lock release on a stop.** `BLOCKED` and `NEEDS_CONTEXT` (and a malformed STATUS,
> treated as `BLOCKED`) **stop the run** — a clean exit with a surfaced blocker. Before
> stopping, **`release` the claim-lock** (`skills/linear/claim-lock.md`) so the next
> `/backlogd:solve` (after the PO unblocks or sharpens the spec) re-acquires it cleanly
> rather than standing off against this finished run's stale claim. In a **parallel group**,
> release once after the whole group has been captured and the run is stopping (not per
> sibling). `DONE` / `DONE_WITH_CONCERNS` do **not** release here — the run continues to
> handoff and (on the happy path) ship-on-green, which own the release.

### Why the graph outcome is coarser than STATUS

`scripts/graph.py dispatch-end` accepts only `{solved, partial, blocked}` (a deliberately
small, stable telemetry vocabulary — do not widen it for this feature). The four-value
STATUS enum **folds onto** it:

- `DONE` → `solved`
- `DONE_WITH_CONCERNS` → `solved` (the work landed; the concern is a PO note, not a run
  failure — recording it as anything but `solved` would distort the rework/partial rates)
- `BLOCKED` → `blocked`
- `NEEDS_CONTEXT` → `blocked` (the run did not complete the unit; the *reason* — a thin
  spec rather than an external blocker — lives in Linear, where the PO acts on it)

The richer four-way distinction lives in **Linear** (the transition + the comment the
orchestrator posts) and in the **PO-facing brief**; the graph keeps its coarse three-way
bucket. So step 6 of `dispatch.md` still calls `dispatch-end --outcome {solved|blocked}`
using the fold above, while the *transition* and *PO surface* in step 7 use the full enum.

## `DONE` / `DONE_WITH_CONCERNS` — the unit landed

Both are "the increment exists in the worktree and is mergeable pending review". Proceed
exactly as the pre-NB-348 `solved` path did:

1. Record `dispatch-end --outcome solved` (dispatch.md step 6 already ran the gate).
2. Move the unit to its `completed` state.
3. Commit the unit (dispatch.md step 8).

For `DONE_WITH_CONCERNS`, additionally **stash the developer's `Concerns:` block** in the
orchestrator's working context keyed by unit, and hand it to `skills/solve/handoff.md` so
the solution brief lists it under *Needs your eyes*. Do not block on a concern — a concern
is a flag for the PO, not a gate failure. (If a concern is severe enough that the unit
genuinely should not land, the **quality gate** in `gate.md` is the mechanism that catches
it as `needs-changes`; a `DONE_WITH_CONCERNS` that cleared the gate still lands.)

## `BLOCKED` — can't proceed

The specialist knows what to do but lacks the authority or access. Leave the unit in its
started state and surface the `Next:` blocker to the PO as a question. Stop the run (in a
parallel group: capture/transition this unit, let siblings finish, then stop after the
collect step — see `skills/solve/walk.md`). Record `dispatch-end --outcome blocked`.

On a **Project-form** run, post a project-thread health update with marker `blocked` per
`skills/linear/references/documents-and-updates.md` § "Project health updates" (single-issue
and sub-issue forms do not).

## `NEEDS_CONTEXT` — the spec is too thin

Distinct from `BLOCKED`: here the problem *as written* doesn't pin down a concrete action.
The fix is a **better spec**, not a PO decision or an access grant, so re-dispatching the
same specialist against the same thin spec would just loop. Therefore:

1. Leave the unit in its started state (do **not** transition).
2. **Post the developer's `Next:` context gap as a Linear comment** on the unit — a plain
   `**[backlogd]**`-badged comment addressed to the PO, quoting the gap the developer
   reported, so the PO can sharpen the AC/description. This is the orchestrator's comment
   (not the developer's work-log comment).
3. **Do not re-dispatch** the specialist on this run. Stop the run (or finish the parallel
   group then stop). The PO sharpens the spec and re-runs `/backlogd:solve` later;
   `skills/solve/resume.md` will pick the unit up as `untouched`/`in-progress` next time.
4. Record `dispatch-end --outcome blocked`.

On a **Project-form** run, post the same `blocked`-marker project-thread health update as
the `BLOCKED` path (a stalled unit is a stalled unit for health-derivation purposes).

## Malformed STATUS — the contract is broken

If the captured report's first line is **not** a `STATUS:` line, or the value is outside
the four-value enum, the specialist violated its `<Output_Format>` contract (see
`agents/developer.md` `<Failure_Modes_To_Avoid>`). Do **not** improvise a transition by
reading the prose body. Instead treat it like a `BLOCKED` outcome for safety — **leave the
unit In Progress and stop the run** — and surface to the PO that the dispatch returned a
malformed STATUS line (quote the offending first line). This is the NB-340-style "don't
silently paper over a broken contract" rule applied to STATUS: a missing/garbled STATUS is
a dispatch failure to be surfaced, not guessed around. Record `dispatch-end --outcome
blocked`.
