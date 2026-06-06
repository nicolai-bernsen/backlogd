---
name: solve-ops
description: Ops-only execution path for /backlogd:solve — dispatch a developer to run safe `gh`/repo-ops actions for a non-code unit (no worktree, no commit, no PR), capture the action log on the unit, and continue the loop. The PO solution brief on the parent problem still lands.
---

# solve — ops-only path

Some problems target the **backlogd repo's ops surface** (GitHub settings, releases,
labels, repo metadata) or **external content drafts** rather than code in the tree. They
have no diff and no PR. Run them through this path instead of `skills/solve/dispatch.md`.

> **Narrow scope.** This path exists for ops-only units that target the backlogd repo —
> the kind that landed inline on **NB-312** (topics, Discussions, Releases, `good first
> issue`s, homepage). It is **not** a generic "agents that don't touch code" surface.

## Detection — the `kind:ops` label

A unit is on the ops path **iff** its Linear issue carries the **`kind:ops` label**. The
signal is:

- **Per-unit** — a parent problem may carry the label too (`/backlogd:scope` applies it
  when the problem is clearly repo-ops), but the routing decision is made on the **unit
  being dispatched**, not the parent.
- **Resolved at runtime** — the label is already in the identity cache
  (`.backlogd/identity.json`); resolve it by name (`kind:ops`) once and reuse it.
- **Created on demand** — if the label does not yet exist on the team, `/backlogd:scope`
  (or a `solve` triage pass) creates it via `create_issue_label({ team, name: "kind:ops" })`
  before applying it. The label is **just a routing flag** — no priority, no automation
  beyond this path.

> **Why a label, not a description marker.** Labels are first-class on Linear, already in
> the identity cache, applied per-issue, and queryable on `list_issues`. A description
> marker would be invisible at pickup and brittle to free-form prose edits.

## When walk routes here

From `skills/solve/walk.md`, after units are determined and their `blocked-by` are
resolved:

- **All ready units carry `kind:ops`** → run the ops path: **skip `git worktree add`**,
  set `$WT` to *unset*, and dispatch each unit via the envelope below.
- **No ready units carry `kind:ops`** → continue with the standard
  `skills/solve/dispatch.md` (worktree + commits + PR).
- **Mixed (some ops units, some code units)** — out of scope for v1. **Stop** and surface
  this to the product owner as a clear question: *"This problem mixes ops-only units with
  code units — split into two problems, or pick one path?"* Leave the issue in its state;
  do not guess.

## Per-unit ops dispatch

The dispatch lifecycle is the same as `skills/solve/dispatch.md` — same graph writes
(`dispatch_started` → developer → `dispatch_completed`) so `graph.py report` aggregates
ops runs alongside code runs. The only differences are: **no worktree** in the envelope,
the allowed-actions block, the action-log contract, and **no commit** at the end.

For each ready ops unit, in `blocked-by` order:

1. **Claim it** — move the unit to the *In Progress* state (resolved in
   `skills/solve/identity.md`).

2. **Inject prior work + record dispatch start** — best-effort; a graph failure must
   never block the dispatch. First query for prior work:

       python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/graph.py" prior-work --problem {identifier}

   Then record the dispatch start so the `dispatch_completed` edge later can derive its
   latency:

       python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/graph.py" dispatch-start \
           --session "$SESSION" --problem {identifier}

   If the unit's Linear labels are at hand, record them too (so the metrics report can
   break ops-blocker frequency down by `area:*`; `kind:ops` itself will surface naturally):

       python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/graph.py" labeled \
           --session "$SESSION" --problem {identifier} --labels kind:ops {other labels}

3. **Dispatch the developer** with an inline **ops envelope** (no `$WT` line, an explicit
   allowed-actions block, and the action-log contract):

   > Solve this problem. Take a concrete action toward resolving it, post your progress to
   > your issue, then report what you did and the outcome.
   >
   > **This is an ops-only unit — there is no worktree and no PR.** Do **not** edit files
   > in the repo. Take action through repo-ops tooling (the `gh` CLI is available via
   > Bash) and any read-only inspection you need.
   >
   > Allowed actions (the safe, reversible ops surface — extend only if the problem
   > clearly calls for it and the action is reversible):
   > - `gh repo edit ...` (topics, description, homepage, enable Discussions / Issues)
   > - `gh release create ...` / `gh release edit ...` (publish notes against existing tags)
   > - `gh label create / edit` (repo labels, e.g. `good first issue`)
   > - `gh issue create / edit` on the backlogd GitHub repo (e.g. `good first issue`s
   >   — distinct from Linear; do not touch Linear from the developer side)
   > - read-only inspection (`gh repo view`, `gh api …`)
   >
   > **Stop and report `STATUS: BLOCKED`** before any irreversible or destructive op
   > (deleting a release, force-pushing, archiving the repo, rotating secrets, paid
   > integrations). The product owner approves those out of band.
   >
   > Your Linear surface is unchanged: read your own issue, post **one** progress/result
   > comment on it (edited in place, `**[backlogd developer]**` badge), and report a
   > structured summary whose first line is `STATUS: <DONE|DONE_WITH_CONCERNS|BLOCKED|
   > NEEDS_CONTEXT|DISPUTES_AC>`. Your comment must include an **action log** — the exact
   > `gh` commands you ran and their effect — so the PO can audit what changed without
   > inspecting the repo by hand.
   >
   > ## Issue context
   >
   > **Problem ({identifier}, issue id {id}): {title}**
   >
   > {the unit's full description verbatim — including its `## Acceptance Criteria` section}
   >
   > {the `## Prior work` block from the query above — include only if it printed one}

   This is the same **curated-context** envelope as the standard path (see
   `skills/solve/dispatch.md` → "The curated-context pattern"): the ops developer reads its
   spec from the inlined `## Issue context` block, not a Linear round-trip.

4. **Capture** the developer's final structured summary verbatim.

5. **Confirm its record** — the developer posts its own `**[backlogd developer]**`
   action-log comment on the unit. Verify it landed; do not re-post (no double-posting).
   Add at most a one-line orchestrator note only if the action log is genuinely missing.

6. **Record dispatch completion on the graph** — write the per-unit outcome with the
   latency the CLI derives automatically from the matching `dispatch_started` edge above
   (best-effort — never block the loop). Fold the developer's five-value `STATUS` onto the
   graph's coarse vocabulary per `skills/solve/capture.md` (`DONE`/`DONE_WITH_CONCERNS` →
   `solved`; `BLOCKED`/`NEEDS_CONTEXT`/`DISPUTES_AC` → `blocked`):

       python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/graph.py" dispatch-end \
           --session "$SESSION" --problem {identifier} \
           --outcome {solved|blocked}

7. **Transition the unit by its `STATUS`** — read the first line of the developer's report
   mechanically and branch per **`skills/solve/capture.md`** (no prose-heuristic parsing):
   - `DONE` / `DONE_WITH_CONCERNS` → move the unit to a `completed` state (the latter
     carries its `Concerns:` into the PO brief — see `handoff.md`).
   - `BLOCKED` → leave it in progress, surface the blocker to the product owner, **stop**.
   - `NEEDS_CONTEXT` → leave it in progress, post the context gap as a Linear comment for
     the PO, **stop**, and do not re-dispatch.
   - `DISPUTES_AC` → leave it in progress, log the developer's `Disputed-AC:` challenge as a
     Linear comment for scope / the PO who own the AC, **stop**, and do not re-dispatch or
     edit the AC (see `skills/solve/capture.md` → *`DISPUTES_AC`*).

## No commit, no push, no PR

Skip the commit, the push, and the PR for an ops-only run. The unit's outcome is the `gh`
ops the developer logged on its issue — there is no diff to land. The standard
`skills/solve/handoff.md` `pr-opened` graph write is **also bypassed** (no PR → no
`dispatch_to_pr` latency to record); `run-end` still fires so `run_wall_time` and the
solution brief + *In Review* transition still land. See `handoff.md` for the carve-out.
