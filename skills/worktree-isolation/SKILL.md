---
name: worktree-isolation
description: backlogd's per-session worktree isolation pattern — one isolated git worktree per concurrent agent session, the identity guard armed before any commit, the lock/no-prune convention, and the dedicated-clone escalation when the native pattern proves insufficient. Loaded when a worktree or parallel session is initiated (e.g. /backlogd:solve opening a problem's worktree, or its parallel walk fanning out one worktree per unit). Pairs with hooks/install-git-hooks.sh (the identity guard) and the skills/solve/* family that consumes it.
---

# Worktree isolation for backlogd

When backlogd runs concurrent work — two `/backlogd:solve` sessions in parallel, or one
session that fans out multiple developers across blocked-by-independent units — every
worker needs its own isolated workspace, or they corrupt each other's HEAD, index, and git
identity. This skill is the convention every part of the runtime follows when it opens or
re-enters a worktree.

> **Why this exists.** A *shared* checkout means one HEAD. Two sessions on one HEAD fight,
> a stray `checkout` yanks a sibling's HEAD, and `includeIf "gitdir:…"` silently falls back
> to the wrong identity when the worktree path doesn't match the personal glob. Slice A
> (#307) shipped the identity-guard hook; this slice formalises the rest of the pattern as
> first-class, loadable runtime guidance — the foundation parallel dispatch (#321) builds
> on.

## The pattern — one isolated workspace per session

A *session* is one Claude Code instance acting against this repo: one `/backlogd:solve`
run, one parallel-dispatch sub-developer, or one human-driven debugging window. The
contract for every session:

1. **Open a dedicated git worktree** off the integration branch (`dev`), in a path
   **outside** the main checkout so a sibling session's `checkout` can never touch it:

       git worktree add <path>/backlogd-wt-{identifier} -b {gitBranchName} origin/{integration}

   For backlogd's own runtime, `/backlogd:solve` does this once per problem; the parallel
   walk does it once more per parallel unit (see *Parallel dispatch* below). Run every
   subsequent git command via `git -C "$WT"` — never `cd` into the shared checkout to
   commit, and never `git checkout` to switch branches in a shared worktree.

2. **Always a new branch.** Never share a checkout *and* a branch with a sibling session.
   `git worktree add` refuses to share a branch by default — that refusal is the feature.
   When you must split a single PR across parallel workers (the #321 pattern), give each
   worker its own short-lived **sub-branch** (`{problem-branch}--unit-{unit}`) and have
   the orchestrator merge the sub-branches into the problem branch in a serial collect
   step (`git merge --ff-only` from the problem-branch worktree).

3. **Arm the identity guard before any commit.** The repo's pre-commit hook
   (`hooks/git/pre-commit`) hard-blocks a commit whose `user.email` doesn't match
   `git config backlogd.expectedEmail`. Wire it once per checkout:

       sh hooks/install-git-hooks.sh you@example.com

   That points `core.hooksPath` at `hooks/git/` and records your expected email.
   `git config` is **per-repo, shared across all worktrees of that repo**, so the guard
   applies in every linked worktree automatically — including a newly-added parallel
   worktree. **Verify `user.email` yourself before the first commit** in any new
   worktree:

       git -C "$WT" config --get user.email

   If it disagrees with `backlogd.expectedEmail`, set it locally before committing:

       git -C "$WT" config user.email "you@example.com"

   Do **not** rely on `includeIf "gitdir:…"` — for a linked worktree, git resolves the
   gitdir to `<main>/.git/worktrees/<id>/`, **not** the checkout path, so a personal-path
   `includeIf` glob silently misses the worktree and the global (work) email wins. Assert
   identity; don't trust path-based config to set it.

## Lifecycle conventions

- **Lock long-running worktrees** before walking away from a session:

      git -C "$WT" worktree lock --reason "active solve session"

  An unlocked worktree whose path becomes briefly unreachable (a sleep, a sibling tool's
  prune sweep) can be removed by `git worktree prune` / `git gc --prune`. The lock is
  cheap, reversible (`git worktree unlock`), and the only durable defence.

- **Never `git worktree prune` or `git gc --prune` while sessions are live.** Either runs
  blow away unlocked worktrees that look "missing" from the main checkout's perspective
  — even if the session inside them is happily editing. If you really must prune, lock
  every live worktree first, run the prune from the main checkout only, and re-list
  worktrees after to confirm none were lost.

- **Carry gitignored dev context via `.worktreeinclude`.** A new worktree is born without
  the maintainer's gitignored local files (`.dx/`, `.env.local`, `.claude/CLAUDE.md`).
  Claude Code's `.worktreeinclude` (at the repo root, `.gitignore` syntax) tells
  `claude --worktree` which gitignored paths to seed each new worktree with. Add what a
  session needs to be functional; leave secrets out of files that aren't already
  gitignored.

- **Tear down on success, not on failure.** Once a session's worktree is merged into the
  PR branch and the PR is closed, remove the worktree (`git worktree remove`) and prune.
  On failure — partial / blocked — **leave the worktree in place**: `/backlogd:solve`'s
  resume reconcile (`skills/solve/resume.md`) needs it to recover.

## Parallel dispatch — multiple worktrees on one branch (#321)

`/backlogd:solve`'s parallel walk fans out one developer per blocked-by-independent unit.
Each parallel developer needs its own worktree (so their edits don't collide) but all
their commits must land on the **same problem branch** that becomes one PR. Git refuses
to share a branch across worktrees by default, so the parallel walk uses a
**sub-branch + collect** mechanism:

1. For each unit in a parallel group, the orchestrator adds a worktree on a per-unit
   sub-branch off the problem branch:

       git worktree add <path>/backlogd-wt-{identifier}-unit-{unit} \
           -b {gitBranchName}--unit-{unit} {gitBranchName}

   The sub-branch name is `{gitBranchName}--unit-{unit-identifier}` (e.g.
   `nicolaibernsen/nb-321-parallel--unit-NB-322`). The worktree directory is named
   symmetrically (`...-unit-NB-322`). Both are deterministic — resume reconcile can
   recover the same paths on a re-run.

2. The orchestrator dispatches the developers in parallel (multiple `Agent()` calls in
   one response — Claude Code runs them concurrently). Each developer edits in its own
   `$WT_unit` and reports back.

3. After **all** parallel developers in the group return, the orchestrator commits each
   unit on its sub-branch (one commit per unit, as today), then in a serial **collect**
   step, fast-forward-merges each sub-branch into the problem branch from the
   problem-branch worktree (`$WT`):

       git -C "$WT" merge --ff-only {gitBranchName}--unit-{unit}

   If a fast-forward isn't possible (the problem branch advanced because the previous
   unit in this same group already collected), use a rebase-merge — the orchestrator
   serialises the collect, so conflicts are rare. If a true conflict surfaces, **stop**
   and ask the product owner; never auto-resolve.

4. Once the collect is clean, remove the per-unit worktree + delete the sub-branch:

       git worktree remove <path>/backlogd-wt-{identifier}-unit-{unit}
       git -C "$WT" branch -D {gitBranchName}--unit-{unit}

5. The PR is still **one** PR off `$WT`'s problem branch. Per-unit sub-branches never get
   pushed to origin — they're a local-only mechanism to satisfy git's worktree/branch
   constraint.

### Resume composition (in-flight parallel worktrees)

On a re-run, multiple in-flight per-unit worktrees may exist (a crash or Ctrl+C during a
parallel walk left them behind). `skills/solve/resume.md`'s reconcile lists worktrees via
`git worktree list --porcelain` and reuses what it finds. The orchestrator:

- detects each per-unit worktree at `backlogd-wt-{identifier}-unit-{unit}` and treats it
  as the resumable workspace for that unit (no fresh `worktree add` — re-use it),
- classifies the unit per the four-state table in `skills/solve/resume.md` (the graph's
  `dispatch_started` / `dispatch_completed` edges decide `completed` vs
  `in-progress-mine` vs `inconsistent`),
- if a per-unit sub-branch exists but the worktree is gone, recreates the worktree at
  the same path off the same sub-branch (`git worktree add <path> {gitBranchName}--unit-{unit}`),
- if multiple worktrees exist for the same unit from different sessions, classifies as
  `inconsistent` and pauses to surface to the product owner.

### Tool-context propagation (post-#345)

Each parallel `Agent()` dispatch inherits the parent orchestrator's loaded tools — there
is **no per-dispatch tool pre-load**. `agents/developer.md` no longer carries a `tools:`
frontmatter list (removed in #345), so each parallel sub-developer gets the same tool
grant the orchestrator has loaded. The worktree-isolation contract above governs the
*workspace*; the tool grant is governed by `agents/developer.md` + parent context.

## Dedicated-clone escalation (the stronger fallback)

The native-worktree pattern is the default. It is sufficient for backlogd's current
parallel surface (one orchestrator, ≤4 sub-developers per group). If worktree contention
recurs *despite* the conventions above — a stuck prune, a HEAD race, a config-scope
collision the locked worktree can't prevent — escalate to a **dedicated clone**:

- `git clone` the repo into a separate path *outside* this repo's filesystem
  (e.g. a sibling under `Private/Repos`), with its own `.git`.
- A dedicated clone is immune to the linked-worktree failure modes: its own HEAD, its
  own config, no shared `worktrees/<id>/` gitdir for `includeIf` to resolve.
- Treat the clone as a long-lived parallel checkout; arm the identity guard there too
  (`sh hooks/install-git-hooks.sh you@example.com`).
- Document the escalation in the run's work log — the dedicated clone is heavier and
  should not be the default; we only escalate when worktrees demonstrably fail.

## Rejected — third-party parallel orchestrators

The following were evaluated and **rejected** for backlogd's parallel-session needs:

- **claude-squad**, **Crystal / Nimbalyst**, **vibe-kanban**, **container-use** — they
  re-implement native Claude Code worktrees (no incremental capability), add a
  third-party dependency surface to a clean-room repo, and **none solve the git-identity
  problem** at the root of #301.
- **Container / devcontainer isolation** — overkill for a solo same-stack maintainer; the
  isolation native worktrees + the identity guard provide is sufficient.
- **`tmuxinator`-style runners** — orthogonal (terminal layout, not git isolation);
  Claude Code's native `Agent()` parallelism handles the dispatch dimension.

The native `git worktree` + Claude Code `Agent()` stack covers the cases backlogd hits
today, with no extra IP surface, and the dedicated-clone escalation is available when
the native pattern proves insufficient. Revisit the rejected tools only if a new failure
mode emerges that the native stack genuinely can't address.

## When to load this skill

- `/backlogd:solve` opens a worktree (`skills/solve/walk.md`) — load this skill to set
  `$WT` correctly the first time.
- `/backlogd:solve`'s parallel walk fans out (`skills/solve/walk.md` → parallel-group
  dispatch) — load this skill to add per-unit worktrees with the sub-branch +
  collect mechanism.
- A new contributor's first concurrent session — surfaced via CONTRIBUTING.md's
  "running concurrent sessions?" note, which points here.
- A failure mode emerges (a worktree pruned, a wrong-identity commit blocked) — load
  this skill to recover and to decide whether to escalate to a dedicated clone.

## References

- `hooks/install-git-hooks.sh` / `hooks/check-git-identity.sh` / `hooks/git/pre-commit`
  — the identity guard (#307 / Slice A).
- `skills/solve/walk.md`, `skills/solve/dispatch.md`, `skills/solve/resume.md`,
  `skills/solve/handoff.md` — the consumers of this skill inside `/backlogd:solve`.
- `CONTRIBUTING.md` § "Git identity guard" + the concurrent-sessions note — the
  human-facing entry point.
- Parent #301 (the parallel-session corruption that motivated this slice); Slice A
  shipped in #307; Slice B (`.worktreeinclude` + `worktree.baseRef`) is a sibling.
