---
name: solve-resume
description: Reconcile worktree + branch HEAD + Linear state + graph for /backlogd:solve on a re-run — read all four sources of truth, classify each unit as completed / in-progress-mine / untouched / inconsistent, and either resume cleanly from the first un-completed unit or pause and surface the conflict to the product owner.
---

# solve — resume (reconcile)

Runs **before** `skills/solve/walk.md` creates the worktree. The job: figure out
whether a previous `/backlogd:solve` run on this problem crashed or is still
live, and decide where to pick up. **No writes here** — this step only reads,
classifies, and either continues into the rest of the loop or stops with a
clear question.

> **Dry run:** in `--dryrun` mode this step still runs (all reads), but its
> output goes into the plan instead of acting on it — see `skills/solve/dryrun.md`.

## 1. Read all five sources of truth

For the problem you've just picked up (`{identifier}` / `gitBranchName` from
`get_issue`):

- **Linear** — `get_issue(includeRelations: true)` for the problem and each
  unit (single-issue / sub-issues / Project form, per `skills/solve/walk.md`).
  Capture each unit's state `type` (`backlog` / `unstarted` / `started` /
  `completed`). The state `name` (In Progress vs In Review) matters too —
  resolve via the cached `statuses` from `skills/solve/identity.md`.
- **Git remote** — `git ls-remote --heads origin {gitBranchName}` (read-only,
  no fetch). Records whether the branch exists upstream.
- **Local git** — `git branch --list {gitBranchName}` and `git worktree list
  --porcelain`. If a worktree at `backlogd-wt-{identifier}` exists, capture its
  HEAD (`git -C "$WT" rev-parse HEAD`) and its working-tree state
  (`git -C "$WT" status --porcelain`). Also list any **per-unit worktrees** at
  `backlogd-wt-{identifier}-unit-{unit-identifier}` (left behind by an interrupted
  parallel walk — see `skills/solve/walk.md` and `skills/worktree-isolation/SKILL.md`).
  Per-unit sub-branches `{gitBranchName}--unit-{unit-identifier}` likewise. These are
  the recovery surface for an in-flight parallel group.
- **Graph** — per unit:

      python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/graph.py" run-status \
          --problem {unit-identifier}

  The JSON returns `state` (`completed` / `in-progress` / `untouched`),
  `sessions`, `last_started`, `last_completed`, and the most recent
  `outcome`.
- **Ledger** (a cheap **problem-first** corroborating read — `scripts/ledger.py` →
  `.backlogd/ledger.jsonl`) — for the **problem** identifier:

      python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/ledger.py" read \
          --problem {identifier}

  Returns the durable record(s) of any **completed** run on this problem (the units
  solved with their outcomes, the PR reference, the run timestamp — see NB-426). This is
  the problem-keyed short-circuit the graph's session-keyed per-unit reconcile can't give
  cheaply: a non-empty result is a strong signal the whole problem already ran to handoff,
  so the all-units-`completed` fast path (§3) is the expected classification. It is a
  **corroborating** read, **not** a replacement — the per-unit classification below is
  still driven by the graph `run-status` + Linear + worktree signals (the ledger does not
  change the 4-state table), so the existing graph-based reconcile is unchanged when the
  ledger is empty (a fresh checkout, or a problem that never reached handoff).
- **Claim-lock** (the fifth source of truth — **`skills/linear/claim-lock.md`**) — `check`
  the problem's `**[backlogd]** Claim` comment. It tells you whether *another live session*
  is actively working this problem right now — the signal Linear state alone can't give you
  (In Progress is a state, not a lock). Capture its `session` and `at`: a claim held by a
  session **other than** this run's `$SESSION`, **unexpired** (within the 2-hour TTL), is the
  decisive "a parallel session owns this" signal; a **stale** claim (older than the TTL) or
  **own-session** claim is reclaimable. Read it on the **problem** (the claim is per-problem,
  not per-unit).

## 2. Classify each unit (4-state decision table)

For every unit (in dependency order), reduce the four signals to **one** of:

| State | Linear | Graph | Worktree / branch | Action |
| --- | --- | --- | --- | --- |
| **`completed`** | `completed` | `completed` (`outcome:solved`) | branch exists; commit for the unit on it (best-effort grep — see below) | **Skip** the unit. `skills/solve/dispatch.md` does **not** re-dispatch. |
| **`in-progress-mine`** | `started` (In Progress) | `in-progress` (a `dispatch_started` from this repo's previous session, no matching `dispatch_completed`) | worktree at the expected path **or** absent; branch exists | **Resume**: leave Linear state, do not re-claim, dispatch fresh for this unit. |
| **`untouched`** | `backlog` / `unstarted` | `untouched` | branch may or may not exist | **Normal first dispatch** — fall through to `skills/solve/walk.md` for worktree creation and on into `dispatch.md`. |
| **`inconsistent`** | anything else | anything else | anything else | **Pause and surface** to the product owner. Leave Linear state unchanged. Do **not** guess. |

Cases that classify as `inconsistent` and must be surfaced (non-exhaustive):

- **The claim-lock is held by another live session** (a `**[backlogd]** Claim` comment
  with a `session` ≠ this run's `$SESSION`, within the 2-hour TTL) — a parallel session is
  actively working this problem. This is the decisive cross-session signal: classify
  `inconsistent`, **stand off**, and surface to the product owner per §4 (do not transition
  state, do not dispatch, do not merge). A **stale** claim or this run's **own** claim is
  *not* inconsistent — `refresh` it under `$SESSION` and continue (own/stale claims are
  reclaimable; see `skills/linear/claim-lock.md`). `--steal` (from `commands/solve.md` step
  1) overrides this for a known-dead claim on an explicitly-named problem.
- Linear says **In Progress** but the graph has no `dispatch_started` for the
  unit (a parallel session may have claimed it manually) — corroborated by the claim-lock
  signal above when present.
- The graph shows multiple sessions with `dispatch_started` and no
  `dispatch_completed` for the same unit (concurrent runs likely fighting).
- A worktree exists at `backlogd-wt-{identifier}` but its HEAD is on a
  **different** branch, or `git status` shows uncommitted work attributable
  to a different run.
- The branch exists but its HEAD has commits **not** corresponding to any
  graph `dispatch_completed` for this problem (someone hand-edited).
- Linear says **Done** but no commit on the branch ties to the unit.

The "commit for the unit" check is best-effort: `git -C "$WT" log --grep
"#{unit-identifier}" --oneline`. A missing match alone isn't conclusive — pair
it with the graph signal before declaring inconsistency.

## 3. Worktree handling (deferred from `walk.md`)

The reconcile decision drives whether `skills/solve/walk.md` creates a new
worktree, reuses an existing one, or stops:

- **All units `completed`** — every unit has run; jump straight to
  `skills/solve/handoff.md` (the PR may already exist — `gh pr view` is
  idempotent). The worktree/branch are reused as-is.
- **Mix of `completed` and `in-progress-mine` / `untouched`** — reuse the
  worktree (don't `worktree add -b` again):

      git worktree add <path>/backlogd-wt-{identifier} {gitBranchName}

  (no `-b`, because the branch already exists). If the branch exists but no
  worktree at the expected path does, this is the recovery path. If both
  exist and HEAD is consistent, just remember the path as `$WT` and move on.
- **All `untouched`** — the normal first-time path; `walk.md` runs unchanged.
- **Any `inconsistent`** — pause; do not touch the worktree, do not touch
  Linear, do not dispatch.

### Per-unit worktrees from an interrupted parallel walk

If `git worktree list` surfaced any `backlogd-wt-{identifier}-unit-{unit-identifier}`
worktrees (a parallel group was interrupted mid-walk — see
`skills/worktree-isolation/SKILL.md` § "Parallel dispatch"), classify each per the
4-state table above against its **unit**'s identifier (not the parent problem):

- A per-unit worktree whose unit is `completed` on the graph + Linear is **stale** —
  remove it (`git worktree remove`) and delete its sub-branch
  (`{gitBranchName}--unit-{unit}`); the unit's commit is already on the problem branch
  via the prior run's collect. Skip the unit on re-dispatch (`dispatch.md` does too).
- A per-unit worktree whose unit is `in-progress-mine` is the recovery surface — reuse
  the worktree (`$WT_unit = <path>`), reuse the sub-branch, and dispatch the unit
  fresh through `skills/solve/dispatch.md` with that `$WT_unit`. The walk's collect
  step picks up from there.
- A per-unit worktree whose unit is `untouched` is a stray — remove the worktree and
  delete the sub-branch, then let the walk recreate them on the normal first-dispatch
  path.
- **Two per-unit worktrees for the same unit from different sessions** (or a per-unit
  HEAD that doesn't match any graph `dispatch_started`) is `inconsistent` — pause and
  surface to the product owner.

## 4. The pause message

When you pause for inconsistency, post one clear question to the product owner
(stdout; the orchestrator does not write a Linear comment for this — leaving
state untouched also means leaving Linear alone). Template:

    Resume reconcile paused on {identifier}.

    Conflict: {short description — e.g. "NB-329 is In Progress in Linear but the
    graph shows no dispatch_started from this repo. A parallel session may have
    claimed it."}

    Signals:
      Linear: {state names per unit}
      Graph:  {run-status JSON summary per unit}
      Git:    {branch exists? worktree exists at <path>? HEAD on which branch?}

    What I need from you: {a binary question — e.g. "Should I take over NB-329, or
    is another session still working it?"}

Then stop. The product owner unblocks by either cleaning up the conflict (and
re-running `/backlogd:solve`) or telling you which side of the conflict to
respect; the next run is a fresh reconcile.

## 5. What the rest of the loop sees

After reconcile finishes without an `inconsistent`:

- `skills/solve/walk.md` skips worktree creation if reconcile already reused
  one (it remembers the path as `$WT`).
- `skills/solve/dispatch.md` iterates the units in dependency order and
  **skips** any unit reconcile classified as `completed` (no claim, no
  envelope, no graph write). It dispatches the first `in-progress-mine` and
  every subsequent `untouched` exactly as today.

A *first-ever* `/backlogd:solve` on a fresh problem still works unchanged —
every unit is `untouched`, the claim-lock holds this run's own `$SESSION`
(acquired at pickup), reconcile is a no-op, `walk.md` creates the worktree,
`dispatch.md` runs through the units normally. The claim is folded in as **one
more source of truth**, not a separate reconcile pass: it only changes the
outcome when *another* live session holds the problem.

## Manual test recipe (AC 5)

Verify the resume path end-to-end by hand:

1. File a `problem`-labelled issue with **two sub-issues** (`A` blocked-by
   nothing, `B` blocked-by `A`) and shape it (`/backlogd:scope`).
2. Run `/backlogd:solve {parent-identifier}` and **kill the process** (Ctrl+C
   or close the terminal) right after the first sub-issue's
   `dispatch_completed` edge lands — i.e. after Linear marks `A` `Done` and
   `dispatch_completed{outcome:solved}` is in the graph for `A`, but **before**
   any work on `B`.
3. Re-run `/backlogd:solve {parent-identifier}` from the same machine.

Expected:

- Reconcile reports `A` as `completed`, `B` as `untouched`.
- The worktree at `backlogd-wt-{identifier}` is **reused** (no duplicate
  `worktree add -b`).
- `dispatch.md` skips `A` (no envelope, no claim, no graph write) and
  dispatches `B`.
- The final PR carries one commit per sub-issue (the original `A` commit plus
  the new `B` commit).

If reconcile instead surfaces an inconsistency (e.g. the kill happened mid-
`dispatch_completed` write), the pause message is the expected outcome —
clean up by deleting the orphaned `dispatch_started` from
`.backlogd/graph/<session>.json` (or finishing the write manually) and re-run.
