---
name: solve-walk
description: Determine units of work for /backlogd:solve, route by the kind:ops label (standard vs ops-only path), and — on the standard path only — open the problem's isolated worktree + branch. Maps single-issue / sub-issues / Project form to units, walks ready ones in blocked-by order, and sets up one branch -> one PR (or skips git entirely for ops-only).
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
  lands (see `skills/solve/handoff.md`).
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
   this step).

The developer edits **in `$WT`**; you run every commit, the push, and the PR from `$WT`.
