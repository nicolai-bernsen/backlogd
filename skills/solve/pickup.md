---
name: solve-pickup
description: Pick one Linear problem for /backlogd:solve and triage it inline if it is not yet shaped — chooses the named issue or the top problem-labelled candidate, then either continues or runs /backlogd:scope's flow inline.
---

# solve — pick + triage

## Pick one problem

If the user named an issue (`/backlogd:solve NB-123`), take that one. Otherwise pick the
top `problem`-labelled issue: order by state (prefer already-`started`, then
`unstarted`/`backlog`) then by priority, and take the first.

If there is nothing to solve, report exactly:

> No problems to solve. File a `problem` issue (optionally run `/backlogd:scope` to shape
> it), then run `/backlogd:solve` again.

and **stop**.

## Triage if it is not yet shaped

A problem is *shaped* when the canonical spec carries a `## Acceptance Criteria`
section. Where the canonical spec lives depends on the problem's **form** (set at
`/backlogd:scope` time):

- **Single-Issue / sub-issue form** — the canonical spec is the **issue description**.
  A `## Acceptance Criteria` heading in the description is the shaped signal.
- **Project-form** — the canonical spec is the Project's **`Spec` Document**. The
  shaped signal is `list_documents({ projectId }) → match title === "Spec"` returning
  a hit; the AC source is `get_document(<spec doc id>)`'s body. The container issue's
  description is just a summary + link to that Document and is **not** the AC source.
  See [`skills/linear/references/documents-and-updates.md`](../linear/references/documents-and-updates.md)
  for the upsert procedure (note the `project` / `projectId` parameter asymmetry).

If the chosen problem is **not** shaped, shape it now — run the `/backlogd:scope` flow
inline (write spec + AC, decompose if it earns it), pausing for the product owner only
if it is too ambiguous to write AC (≤3 questions). (This dispatches the `refiner`
subagent — see `commands/scope.md` step 3.) If it is already shaped, continue.

> **Dry run:** in `--dryrun` mode, do **not** run scope inline. Decide whether the problem
> is shaped (read-only), record the triage decision for the plan output, and follow
> `skills/solve/dryrun.md`.

## Pause only on genuine triage ambiguity

Interrupt the run for the product owner here when you cannot write acceptance criteria
without a product decision. Surface it as a clear question, leave the issue in its state,
and **stop**. Do not guess past a genuine ambiguity. (A `BLOCKED` / `NEEDS_CONTEXT`
developer `STATUS` is handled later — see `skills/solve/dispatch.md` step 7 and
`skills/solve/capture.md`.)
