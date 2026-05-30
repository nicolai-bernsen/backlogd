---
name: linear-blocked-label
description: Keep the team's `blocked` label in sync with each active problem's blocker state — the signal layer the PO Daily saved view filters on. Ensure-label idempotently, re-evaluate per-issue from `blocked-by` relations, and attach/detach with no console churn. Scope-guarded to issues carrying the `problem` label. Loaded by `/backlogd:scope`, `/backlogd:solve`, and `/backlogd:status` at the point they already inspect blockers.
---

# Linear — auto-managed `blocked` label

`/backlogd:scope`, `/backlogd:solve`, and `/backlogd:status` keep a `blocked` label on the
team in sync with each active problem's blocker state. The label is the **signal layer**
the PO Daily saved view filters on, so the product owner sees blockers at the top without
clicking into any issue.

This skill describes the algorithm — load it from the three commands at the point they
already inspect a problem's `blocked-by` relations.

> **Prerequisite reads.** `skills/linear/SKILL.md` (operating model) and
> `skills/linear/references/linear-mcp.md` (exact `mcp__linear__*` calls). Resolve workflow
> states by `type`, never display name; `save_*` is upsert (read → capture `id` → write);
> identity is cached in `.backlogd/identity.json`.

## Scope

- **Only `problem`-labelled issues.** Never touch an unrelated, non-`problem` issue.
- **Only active states.** Only re-evaluate when the target issue's state `type` is
  `unstarted` or `started`. Skip `backlog`, `completed`, `canceled`.

If either guard fails, **do nothing** — neither add nor remove `blocked`.

## Step 1 — Ensure the `blocked` label exists on the team (idempotent)

Resolve the label from the cached identity (`.backlogd/identity.json` → `labels[]`). If
`blocked` is not in the cache:

1. `list_issue_labels({ team, name: "blocked" })` to confirm absence (the cache may be
   stale).
2. If still absent, create it:

       create_issue_label({
         team,
         name: "blocked",
         color: "#EB5757",
         description: "Auto-applied by backlogd when an active issue has an open blocked-by."
       })

   `color` is suggested red; if the MCP rejects a specific shade, omit `color` and let
   Linear assign the default — the name is what matters.
3. The new label's `id` lands in the cache the next time the identity refreshes (24-hour
   TTL); a forced refresh is unnecessary for this run.

If `blocked` is already in the cache, **skip the calls above** — re-confirming on every
invocation costs GraphQL complexity for a value that almost never changes.

## Step 2 — Re-evaluate one issue

Given a target issue (the issue you are already reading in the calling command):

1. **Guard** — confirm the issue carries the `problem` label and its state `type` is
   `unstarted` or `started`. If not, return — leave the labels untouched.
2. **Read its `blocked-by` relations.** Use the relations you already have from the calling
   command's `get_issue(includeRelations: true)` read — do not re-fetch. Each blocker has
   a state `type`.
3. **Decide the desired state.** The issue is **blocked** iff at least one `blocked-by`
   relation points at an issue whose state `type` is **NOT** in `{completed, canceled}`.
4. **Read the current labels** off the issue you already have.
5. **Apply the delta — idempotent on both ends.** Decide by the desired state vs. the
   current `labels` array:

   | Desired | `blocked` in `labels`? | Action |
   | --- | --- | --- |
   | blocked | yes | no-op |
   | blocked | no | `save_issue({ id, labels: [...labels, "blocked"] })` |
   | not blocked | yes | `save_issue({ id, labels: labels.filter(l => l !== "blocked") })` |
   | not blocked | no | no-op |

   The `labels` parameter accepts names or ids; pass the existing labels back verbatim
   alongside the add/remove of `blocked` so the upsert does not drop unrelated labels.
   Reference the label by **name** (`"blocked"`) — Linear's MCP resolves it on the team
   you already pinned via identity.

## Idempotency contract

- Re-running any of the three commands on the same issue with the same blocker shape is a
  **no-op** — neither add nor remove fires.
- A blocker moving to `completed`/`canceled` (or being removed) triggers the **remove** path
  on the next invocation; nothing else changes.
- A new blocker landing on an already-blocked issue triggers no write (already labelled).
- A `problem` issue with no `blocked-by` at all is never labelled `blocked` — the desired
  state is "not blocked" and the no-op row applies.

## Where to call this from

- **`/backlogd:scope`** — after the issue is shaped and saved (step 5 sets priority), on
  the shaped issue. The refiner may have introduced or cleared `blocked-by` relations.
- **`/backlogd:solve`** — in the unit walk, when reading each unit's `blocked-by`
  relations to determine the ready set; and again when a unit's blocker transitions
  (`completed`/`canceled`) and the walk re-evaluates the ready set. Apply per-unit on every
  `problem`-labelled unit the walk inspects.
- **`/backlogd:status`** — in the survey, on every problem in scope at the point the
  command already reads its `blocked-by` relations. `status` is otherwise read-only; this
  is a deliberate carve-out for the *signal layer*. The console standup output is unchanged.

Each caller passes the issue (with its `labels` and the `blocked-by` relations it already
read) to this skill. The skill writes at most one `save_issue` per issue per invocation;
when the desired state already matches the current labels, no Linear write fires at all.
