---
name: solve-walk
description: Determine units of work for /backlogd:solve and open the problem's isolated worktree + branch — maps single-issue / sub-issues / Project form to units, walks ready ones in blocked-by order, and sets up one branch -> one PR.
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

## Open a worktree + branch for the problem

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
   existing branch/worktree on a re-run.

The developer edits **in `$WT`**; you run every commit, the push, and the PR from `$WT`.
