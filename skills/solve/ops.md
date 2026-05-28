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

For each ready ops unit, in `blocked-by` order:

1. **Claim it** — move the unit to the *In Progress* state (resolved in
   `skills/solve/identity.md`).
2. **Inject prior work** — same as the standard path, best-effort:

       python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/graph.py" prior-work --problem {identifier}

3. **Dispatch the developer** with an inline **ops envelope** (note: no `$WT` line, an
   explicit allowed-actions block, and the action-log contract):

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
   > **Stop and report `blocked`** before any irreversible or destructive op (deleting a
   > release, force-pushing, archiving the repo, rotating secrets, paid integrations). The
   > product owner approves those out of band.
   >
   > Your Linear surface is unchanged: read your own issue, post **one** progress/result
   > comment on it (edited in place, `**[backlogd developer]**` badge), and report a
   > structured `Outcome: solved | partial | blocked` summary. Your comment must include an
   > **action log** — the exact `gh` commands you ran and their effect — so the PO can
   > audit what changed without inspecting the repo by hand.
   >
   > Problem ({identifier}, issue id {id}): {title}
   >
   > {description, including its Acceptance Criteria}
   >
   > {the `## Prior work` block from the query above — include only if it printed one}

4. **Capture** the developer's final structured summary verbatim.

5. **Confirm its record** — the developer posts its own `**[backlogd developer]**`
   action-log comment on the unit. Verify it landed; do not re-post (no double-posting).
   Add at most a one-line orchestrator note only if the action log is genuinely missing.

6. **Transition the unit** by reported `Outcome`:
   - `solved` → move the unit to a `completed` state.
   - `partial` / `blocked` → leave it in progress, surface to the product owner, **stop**.

## Graph emit — no diff, so emit problem→session only

There is no worktree diff to scan for touched files. Still emit the session edge so the
graph records that this problem ran (best-effort — never block the loop on a graph
failure). Omit `--stdin` / `--files` — `emit` defaults to no touches and just writes the
`solves` edge:

    python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/graph.py" emit \
        --session "$SESSION" --problem {identifier}

(If the developer's action log names a file it touched on GitHub — e.g. an uploaded
social-preview image — and that path also lives in the local tree, feed it explicitly via
`--files path1 path2 …`. Do **not** scrape arbitrary paths out of free-form text.)

## No commit, no push, no PR

Skip the commit, the push, and the PR for an ops-only run. The unit's outcome is the `gh`
ops the developer logged on its issue — there is no diff to land. The standard
`skills/solve/handoff.md` step that opens the PR is **bypassed for ops-only runs**; the
solution brief + *In Review* transition still fire (see `handoff.md` for the carve-out).
