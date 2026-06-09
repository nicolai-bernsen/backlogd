---
name: solve-walk
description: Determine units of work for /backlogd:solve, route by the kind:ops label (standard vs ops-only path), and — on the standard path only — open the problem's isolated worktree + branch. Maps single-issue / sub-issues / Project form to units, walks ready ones in blocked-by order (sequentially when width=1, in parallel groups when blocked-by-independent and the standard path is in effect), and sets up one branch → one PR (or skips git entirely for ops-only).
---

# solve — units + worktree

## Determine the units of work

The **units** are what you dispatch developers against:

- **Single issue** — no sub-issues, not promoted: the one unit is the problem itself.
- **Sub-issues** — decomposed under the problem: each sub-issue is a unit.
- **Project form** — promoted: each Issue under the Project is a unit.

A unit is **ready** only when every issue it is `blocked-by` is already `completed`. Walk
ready units in dependency order; never start a unit whose blockers are still open. If
units remain but none are ready (an open `blocked-by` that will not clear), surface that
to the product owner as a clear question and **stop** — do not guess past a blocker.

## Route ops-only problems before the worktree

Before opening a worktree, decide whether this run is on the **ops-only path**. Check the
**`kind:ops` label** on each ready unit:

- **All ready units carry `kind:ops`** → ops-only run. **Skip the worktree section
  below**, leave `$WT` unset, and follow **`skills/solve/ops.md`** instead of
  `skills/solve/dispatch.md`. There is no commit, no push, and no PR — only `gh` /
  repo-ops actions logged on each unit. The PO solution brief on the parent problem still
  lands (see `skills/solve/handoff.md`). **Ops-only runs do not enter the parallel walk
  below** — every ops unit is dispatched sequentially per `skills/solve/ops.md`.
- **No ready units carry `kind:ops`** → standard run. Open the worktree as below and
  follow `skills/solve/dispatch.md`.
- **Mixed** (some ops units, some code units) → **stop** and ask the product owner to
  split the problem in two or pick one path; do not guess. (Out of scope for v1.)

See **`skills/solve/ops.md`** for the ops-only details — detection signal, dispatch
envelope, and the graph-emit/no-PR carve-outs.

## Open a worktree + branch for the problem

> **Resume:** if `skills/solve/resume.md` already reused an existing worktree, `$WT` is
> set — **skip this whole section** and continue. The reconcile step in step 4 of
> `commands/solve.md` handles all reuse paths; this section runs only when reconcile
> classifies *every* unit as `untouched` (the first-ever path).
>
> **Dry run:** in `--dryrun` mode, do **not** create the worktree or branch. Resolve the
> integration branch and the suggested branch name read-only, compute the path you *would*
> use, and report them in the plan (`skills/solve/dryrun.md`).

backlogd lands a problem's work on **one branch → one PR**. Before solving, set up an
isolated worktree so edits never touch the shared checkout (a parallel session may share it):

1. Resolve the repo's **integration branch** — the branch features merge into (e.g. `dev`;
   the repo's configured/default development branch). The PR will target it.
2. Get the problem's suggested branch name from Linear (`get_issue` → `gitBranchName`).
3. Create the worktree + branch **outside** the repo directory, and remember the path as `$WT`:

       git worktree add <path>/backlogd-wt-{identifier} -b {gitBranchName} origin/{integration}

   Run **every** git command via `git -C "$WT"` from here on. Never `checkout`/switch
   branches in the shared checkout — that yanks a parallel session's HEAD. Reuse an
   existing branch/worktree on a re-run via `skills/solve/resume.md` (which runs before
   this step). The worktree + identity-guard contract is documented in
   **`skills/worktree-isolation/SKILL.md`** — load it here for the lifecycle conventions
   (lock long-running worktrees, never prune while live, carry gitignored dev context).

The developer edits **in `$WT`**; you run every commit, the push, and the PR from `$WT`.

## Walk the units — parallel groups, then sequential blockers

`/backlogd:solve` walks ready units in `blocked-by` order. When two or more units are
ready **at the same time** and share no `blocked-by` between them, dispatch them **in
parallel** through the worktree-isolation pattern; when the DAG is linear (or only one
unit is ready), the walk collapses to today's sequential behaviour automatically.

### Configure the parallel ceiling

The maximum number of units dispatched concurrently in a single group is controlled by
the **`BACKLOGD_CONCURRENCY_MAX`** environment variable:

- **Default `2`** when unset.
- **Clamp to `[1, 4]`** — values below 1 are treated as 1, values above 4 are clamped to
  4. The clamp is a guardrail against runaway fanout; raising it past 4 needs evidence
  the orchestrator + the host can sustain it.
- **`1` disables parallelism** — the walk is byte-identical to today's sequential walk.
  Single-unit problems and width=1 linear DAGs already exercise this path implicitly
  (only one unit is ever ready per group), so the regression surface is the same shape
  as the existing sequential walk.

Read it once at the top of the walk and remember it as `$CONCURRENCY_MAX`. Do **not**
re-read it per group — a mid-run change is confusing and not worth supporting.

### Build the next parallel group

A **parallel group** is the set of currently-ready units (in `blocked-by` order) that
share no `blocked-by` between them — i.e. units that could legitimately run at the same
time. Build the group:

1. From the units list, take the subset whose `blocked-by` are all `completed` (the
   ready set).
2. Reduce the ready set to units that have **no `blocked-by` on any other unit in the
   ready set** — they truly are mutually independent right now.
3. Cap the group at `$CONCURRENCY_MAX`. If the ready set is larger, take the first
   `$CONCURRENCY_MAX` in `blocked-by` order; the rest stay in the ready set for the next
   group.

If the resulting group has **one** unit, the walk runs that unit through the standard
`skills/solve/dispatch.md` flow with no per-unit sub-branch — exactly today's behaviour.
If the group has **two or more** units, dispatch them in parallel per the next section.

### Dispatch a parallel group (≥2 units)

Use the **sub-branch + collect** mechanism from `skills/worktree-isolation/SKILL.md`. For
each unit in the group:

1. **Add a per-unit worktree on a per-unit sub-branch off the problem branch:**

       git worktree add <path>/backlogd-wt-{identifier}-unit-{unit-identifier} \
           -b {gitBranchName}--unit-{unit-identifier} {gitBranchName}

   Both names are deterministic (resume reconcile depends on this — see below). Remember
   the per-unit worktree path as `$WT_unit` and the per-unit sub-branch name as
   `$BRANCH_unit`. The main problem worktree `$WT` remains untouched.

2. **Run `skills/solve/dispatch.md` per unit in parallel.** Issue all the parallel
   `Agent()` calls in **one** response so Claude Code dispatches them concurrently. Each
   parallel dispatch consumes `skills/solve/dispatch.md` with its own `$WT_unit` in place
   of `$WT` — the dispatch envelope's worktree line points at the per-unit path. Step 8
   of `dispatch.md` (the commit) runs against `$WT_unit` and lands on `$BRANCH_unit`.

3. **Do not abort siblings on failure.** If any parallel dispatch returns a non-terminal
   `STATUS` (`BLOCKED`, `NEEDS_CONTEXT`, or `DISPUTES_AC`), the orchestrator captures that
   result but **lets the other dispatches in the group finish**. After all of them return,
   process each per its `STATUS` (step 7 of `dispatch.md`, which loads
   `skills/solve/capture.md`). If any unit returned `BLOCKED` / `NEEDS_CONTEXT` /
   `DISPUTES_AC`, **stop the run after the collect step below** and surface every
   non-terminal outcome to the product owner (a `BLOCKED` blocker as a question; a
   `NEEDS_CONTEXT` gap as the context-gap comment; a `DISPUTES_AC` challenge as the
   AC-challenge comment to scope / the PO) — do not start the next parallel group.

4. **Collect the parallel commits serially.** Once every dispatch in the group has
   returned and committed on its sub-branch, fast-forward-merge each sub-branch into the
   problem branch from `$WT`, in `blocked-by` order, one at a time:

       git -C "$WT" merge --ff-only {gitBranchName}--unit-{unit-identifier}

   A fast-forward works as long as the problem branch hasn't advanced since the
   sub-branch was created — which is the common case here (every sub-branch in the group
   was created off the same problem-branch tip). If the previous unit in this same group
   has already collected, the problem branch has advanced by exactly that unit's commit,
   so a sub-branch created off the *original* tip will not fast-forward; rebase that
   sub-branch onto the problem-branch tip first:

       git -C "$WT_unit" rebase {gitBranchName}
       git -C "$WT" merge --ff-only {gitBranchName}--unit-{unit-identifier}

   If a true conflict surfaces (two parallel units edited the same lines), **stop** and
   surface to the product owner with the conflicting files — never auto-resolve. The
   problem branch is left in a clean state (no half-collected sub-branches); resume
   reconcile picks up where the orchestrator paused.

5. **Tear down per-unit worktrees + sub-branches after a clean collect.** Per unit, once
   its sub-branch is merged into `$WT`:

       git worktree remove <path>/backlogd-wt-{identifier}-unit-{unit-identifier}
       git -C "$WT" branch -D {gitBranchName}--unit-{unit-identifier}

   On a `BLOCKED` / `NEEDS_CONTEXT` / `DISPUTES_AC` outcome, **leave the unit's worktree +
   sub-branch in place** so resume reconcile (`skills/solve/resume.md`) can recover it on
   the next run.

### Record fanout on the graph (best-effort)

When dispatching a parallel group of ≥2 units, the orchestrator records the group's
fanout on the run for the `/backlogd:metrics`-style aggregate (NB-266 extension). The
`dispatch_started` / `dispatch_completed` edges already carry per-unit timestamps; the
fanout is recorded on the **run-end** edge for the parent problem at handoff time. See
`skills/solve/handoff.md` → "Record the PR open + run completion on the graph" for the
write — the walk only needs to remember the **peak fanout** observed across all groups
in this run (e.g. `peak_fanout = 3` if the largest parallel group had three units) and
hand it to handoff.

### Post a milestone-completion health update (Project-form only)

After a group has been dispatched and collected, check whether the just-completed units
closed out a **Project Milestone** — i.e. every unit assigned to that milestone is now
`completed`. If so, post a milestone-scoped health update with marker
`milestone:<milestone-name>` via `save_comment({ milestoneId, body })` — resolve the
milestone UUID with `list_milestones({ project })` first if you don't already have it
cached. The body shape, dedupe-by-marker procedure, and health derivation rules live in
**`skills/linear/references/documents-and-updates.md` § "Project health updates" →
"Milestone-completion variant"**. **Single-issue, sub-issue, and ops-only runs do NOT
post this update** — Project-form only.

### Iterate until every unit has run

After a group has been dispatched and (cleanly) collected, advance the walk: re-evaluate
which units are ready (the just-completed group may have unblocked others), build the
next parallel group, and continue until every unit is `completed` or the run has paused
on a non-terminal `STATUS` (`BLOCKED` / `NEEDS_CONTEXT` / `DISPUTES_AC`) / collect
conflict. Single-unit groups remain the default shape for linear DAGs — the parallel path
activates only when
the DAG genuinely earns it.
