---
name: solve-ship
description: Ship-on-green — solve's final phase. After the In Review handoff, auto-chain the SAME independent verdict review /backlogd:review owns and, on a fully-green verdict (every AC MET + every DoD MET + CI green + zero [manual] + zero needs-PO), merge the PR and close the problem to Done with no human gate. On by default; --no-ship (or BACKLOGD_SHIP_ON_GREEN=0) opts a single run out, holding it at In Review. Surfaces to the PO only on sent-back / needs-you / blocker.
---

# solve — ship-on-green (final phase)

> **The PO files a problem and walks away.** This phase is what lets the loop reach a
> **merged + Done** increment without the PO running a second command. It runs **after**
> `skills/solve/handoff.md` has moved the problem to *In Review* — it does **not** replace
> the In Review handback; it chains on top of it. The independent fresh-context verdict pass
> is **preserved** (and non-negotiable — see `skills/reviewer/SKILL.md`): ship-on-green
> removes the human *trigger* and the human *merge click*, never the independent
> *verification*.

## When this phase runs — and when it is skipped

Ship-on-green is **ON by default**. Run this phase as the last step of `/backlogd:solve`
**unless** any of these opt-outs applies, in which case **stop after the In Review handoff**
(the pre-ship-on-green behaviour — problem held at *In Review*, PR open, PO accepts later via
`/backlogd:review`):

- **`--dryrun`** — the dry run already exited after printing the plan (see
  `skills/solve/dryrun.md`); this phase never runs under it. No reviewer dispatch, no merge.
- **`--no-ship` flag** (or **`BACKLOGD_SHIP_ON_GREEN=0`** in the environment) — the run
  opted out of auto-merge. It **still completes the independent verdict review** below (so
  the PO gets the verdict rollup), but **holds the problem at In Review with the PR open**
  and merges nothing — identical to running `/backlogd:review` manually and getting
  `accepted` without the merge. The flag scopes a single run; the env var scopes the shell.
  When both the flag is absent and the env var is unset/non-zero, the default is
  **ship-on-green** (auto-merge on green).

> Carry the parsed `--no-ship` decision forward from `commands/solve.md` step 1 (the same
> place `--dryrun` is parsed). `--no-ship` is **not** a dry run — the solve still runs for
> real, opens the PR, and runs the verdict; it only declines the final merge.

## What this phase does — reuse `/backlogd:review`, do not re-implement

This phase runs the **same** mechanism `/backlogd:review` already owns — there is one
reviewer dispatch path and one merge-decision path in backlogd, and this is the auto-chained
caller of it. **Do not copy-paste the merge logic; reuse it:**

1. **Dispatch the independent verdict reviewer** exactly as **`commands/review.md` step 3**
   does — the `backlogd:reviewer` subagent in **`verdict`** mode, with the full inline
   envelope (problem id, title, `## Acceptance Criteria`, every `**[backlogd developer]**`
   and `**[backlogd tester]**` comment, the solution brief, the open PR url, the `gh pr
   checks` CI signal, and the worktree path). The reviewer walks every AC + every DoD line
   with a **fresh context** and returns its rollup (`accepted` / `sent back` / `needs PO` /
   **`block`**) plus the drafted verdict body. The deferred-tool pre-load from `commands/solve.md` step 0
   already covers the reviewer's Linear tool grant — no extra pre-load is needed here.
2. **Post the rollup verdict** exactly as **`commands/review.md` step 4** does — one
   `**[backlogd review]**` comment on the problem, the reviewer's drafted body verbatim.
3. **Decide and transition** exactly as **`commands/review.md` step 5** does — act on the
   reviewer's rollup, **gated on the independent reviewer's `accepted` rollup** (not the
   in-session pre-commit gate from `skills/solve/gate.md`, which is a *distinct, earlier*
   pass). The happy-path merge condition and the **base-race guard** (re-confirm CI green on
   the live PR head + PR mergeable into the integration branch + **this session still holds
   the claim-lock** — `skills/linear/claim-lock.md` — immediately before merging; bail to a
   surfaced blocker if stale/conflicted/claim-taken; **never auto-rebase**) live in
   `commands/review.md` step 5 — apply them there, do not restate them. The claim-lock
   re-check is the live-claim half of that **one** guard (added, not a second guard); on a
   clean merge the same step `release`s the claim after the merge succeeds, and on *sent
   back* it `release`s on the handback.

The only thing this phase adds over a manual `/backlogd:review` is the **trigger**: the PO
did not have to run the command, and on green does not have to click merge.

## Outcomes — interrupt the PO only when a real decision or blocker exists

Branch on the reviewer's rollup (the `commands/review.md` step 5 branches), and report which
one happened:

- **`accepted` → fully green → merged + Done (the happy path).** Every AC MET, every DoD
  MET, CI green, zero `[manual]`, zero NEEDS-PO, and the base-race guard passed → the PR is
  squash-merged into the integration branch and the problem is moved to *Done*. **The PO is
  not interrupted** — no command to run, no merge to click. This is the outcome ship-on-green
  exists for.
- **`sent back` (any AC line UNMET OR any DoD line UNMET OR CI red).** The problem moves back
  to *In Progress* with the reviewer's UNMET notes as actionable rework (PR left open) —
  exactly the `commands/review.md` step 5 *sent back* path, including the best-effort
  `graph.py rework` record. **Surface to the PO** that the increment was sent back.
- **`needs you` (any NEEDS-PO without an UNMET, or unconfirmed AWAITING-PO/`[manual]`).** The
  problem stays *In Review* (PR open) and the judgement call / the "Manual checks for the
  PO" batch is surfaced to the PO — the `commands/review.md` step 5 *needs PO* path.
  **Interrupt the PO** with the question; do not guess past it and do not merge.
- **`block` (a NO-STANDARD line — a consequential decision with no governing Accepted
  standard).** The
  problem does **not** merge — it **parks blocked-by a new sub-issue** until the gap is
  governed (the `commands/review.md` step 5 *block* path). Route by the reviewer's
  classification, honouring the **non-delegable standards boundary** (`skills/scrum/references/accountabilities.md`):
  a **`standard:`** gap opens a `Define standard for {X}` sub-issue, marks the parent
  blocked-by it (Linear sub-issue + blocked-by primitives), holds the problem *In Review*
  (PR open), and **surfaces the "what standard would you like for {X}?" question to the
  PO** — the scrum-master never authors the standard itself; a **`fact:`** gap is answered
  once from an existing ADR/precedent and the verdict re-runs (no PO, no merge yet).
  **Interrupt the PO** on a `standard:` gap.
- **Base-race blocker.** If the base-race guard in `commands/review.md` step 5 bails (head
  went red or PR no longer cleanly mergeable), **surface it as a blocker** — problem held at
  *In Review*, PR open, nothing merged, no auto-rebase. **Interrupt the PO.**

In short: on a **clean green merge the PO is never interrupted**; the PO is surfaced to
**only** on *sent back*, *needs you*, a *block* (`standard:` gap), or a *blocker*.

**Claim-lock release on terminal outcomes.** Every terminal outcome of this phase is a
clean exit for the solve run, so it **`release`s the claim-lock** (`skills/linear/claim-lock.md`)
— merged + Done and *sent back* release in `commands/review.md` step 5 (above); the
*needs you* / *block* / *base-race blocker* cases hold the problem at In Review but the
solve run is done, so release the claim there too, so the PO's follow-up `/backlogd:review`
re-acquires it cleanly instead of standing off against this finished run's stale claim. An
abandoned run that never reaches a terminal outcome relies on the 2-hour TTL, not release.

> **Ops-only run (`kind:ops`).** There is no PR and no worktree (see `skills/solve/ops.md`).
> The verdict still runs against the action logs + GitHub surfaces (as in `commands/review.md`
> step 3's ops carve-out), and on `accepted` the problem moves straight to *Done* with **no
> merge step** (there is nothing to merge); the base-race guard is skipped. `sent back` /
> `needs you` surface to the PO as above.

## Report line

`commands/solve.md`'s Report block carries the ship outcome (see its `ship`/`problem` lines).
Make the terminal state unambiguous: **`Done (merged)`** on the happy path, **`In Review
(held — --no-ship)`** when opted out, or the surfaced **sent back / needs you / blocker** with
its reason.
