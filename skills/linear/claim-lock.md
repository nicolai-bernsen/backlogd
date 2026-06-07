---
name: linear-claim-lock
description: Reduces the concurrent-pickup race on a problem across concurrent /backlogd:solve and /backlogd:review sessions; the merge-time re-check is the decisive guard. A session-stamped marker comment is the signal — checked before the first state mutation (solve pickup, review pick) and re-checked immediately before merge, released at every clean exit, and aged out by a 2-hour TTL so a crashed session never deadlocks. The check→acquire over comment upserts is not atomic (see "Honest scope" below). Key-free and Linear-native (official mcp__linear__* only). Loaded by /backlogd:solve and /backlogd:review at the points they already pick up or merge a problem.
---

# Linear — claim-lock (cross-session race reduction + merge-time backstop)

`/backlogd:solve` and `/backlogd:review` never **claim** a problem on their own — moving it
to *In Progress* / *In Review* is a state *change*, not a *lock*, so two concurrent Claude
Code sessions can both pick up the same problem and do overlapping work: duplicate reviews,
duplicate retro/dogfood filings, overwritten reviewer rollups, near-or-actual
double-merges (observed live ≥3× — NB-414, NB-381, NB-346/NB-362). This skill
**reduces the concurrent-pickup race window** to near-simultaneous launches and makes the
**merge-time re-check the decisive guard**: when one session is actively working a problem,
a second session that runs `solve`/`review` on the same problem and sees the active claim
**stands off** instead of racing — and even when two near-simultaneous launches slip past
the pickup check, the merge-time live-claim re-check (below) still prevents the
double-merge.

It is the layer **above** NB-301's filesystem/git isolation (`skills/worktree-isolation/`):
NB-301 guards the worktree + git HEAD; this guards the *Linear work item + its PR*, so two
sessions are far less likely to pick up the same problem at once (near-simultaneous launches
are the residual window — see "Honest scope" below). It **composes with** — does not
duplicate — the two mechanisms already in place:

- **solve's resume/reconcile** (`skills/solve/resume.md`) — the claim becomes a **fifth
  source of truth** alongside Linear / git-remote / local-git / graph; it does **not** add a
  parallel reconcile pass.
- **the one base-race guard** (`commands/review.md` step 5, reused by ship-on-green via
  `skills/solve/ship.md`) — a **live-claim re-check is added to** the existing CI +
  mergeability re-check; it is **not** a second guard.

> **Prerequisite reads.** `skills/linear/SKILL.md` (operating model) and
> `skills/linear/references/linear-mcp.md` (exact `mcp__linear__*` calls). The claim
> comment is an **idempotent marker-upsert** in the exact shape of
> `skills/linear/references/documents-and-updates.md` § "Project health updates" — read it
> for the dedupe-by-marker procedure this skill reuses. Resolve workflow states by `type`,
> never display name; `save_*` is upsert (read → capture `id` → write); identity is cached
> in `.backlogd/identity.json`.

## Honest scope — this is not an atomic mutex

Be precise about what this buys: the claim is built on Linear **comment upserts**, so
`check` → `acquire` is **two MCP round-trips, not one atomic compare-and-swap**. There is an
inherent **TOCTOU window** between them: two sessions launched within the same few-second
window can both `check` and see "unclaimed", and both `acquire` — **last-writer-wins** on the
single claim comment, so they both proceed. This skill **dramatically narrows** that
window (any session that starts after another's claim comment has landed sees it and stands
off) but it **does not eliminate** the simultaneous-pickup race. Do not describe it as a hard
mutex.

The **decisive backstop** is the **merge-time live-claim re-check** — the base-race-guard
half wired into `commands/review.md` step 5 (reused by ship-on-green via
`skills/solve/ship.md`). That re-check happens immediately before the squash-merge, *after*
both racing sessions have run their full verdict, so by then exactly one claim comment has
won (last-writer-wins) and the other session's re-check sees `session != $SESSION` and
**bails without merging**. That is what actually prevents the **double-merge** — the most
damaging outcome of the race. The pickup-time `check` reduces wasted duplicate work; the
merge-time re-check is the guarantee against the irreversible failure. When the two seem to
promise different things, the merge-time re-check is the one that holds.

The claim lives in **one** `**[backlogd]** Claim` comment per problem, upserted in place
(never a second claim comment) following the marker-dedupe precedent in
`documents-and-updates.md`. It is richer than a bare `claimed` label — it identifies **which
session** holds the claim and **when** it was taken, which is what makes both ownership
(only the holder releases / refreshes it) and the TTL (a timestamp to age against) possible.
It also avoids overloading `assignee`, which is a PO-facing field.

```markdown
**[backlogd]** Claim — held by `<session>` since <UTC-ISO-8601 timestamp>

<!-- claim: session=<session>; at=<UTC-ISO-8601 timestamp> -->
```

- **`<session>`** is the run's session id — the `$SESSION` minted in
  `skills/solve/identity.md` (e.g. `solve-NB-414-20260531T071648`), or, for a manual
  `/backlogd:review`, the reviewer session id (`review-{identifier}-<UTC-timestamp>`). It
  identifies the holder so a *different* session can tell "someone else holds this" from "I
  hold this".
- **`at=<timestamp>`** is the UTC instant the claim was acquired or last refreshed (emit with
  `date -u +%Y%m%dT%H%M%SZ`). It is the TTL clock.
- The **`<!-- claim: ... -->` HTML marker** is the machine-readable line — parse it, not the
  human lead line. (Linear renders the comment lead text and escapes the badge to literal
  text; the marker is the stable parse target, exactly as health/shipped comments work.)

### The `claimed` companion label (optional at-a-glance layer)

A team `claimed` label MAY be attached as the at-a-glance signal so the PO / a human can see
"a session is on this" in a board view without opening the issue. It is **the signal layer,
not the source of truth** — the marker comment always wins. Manage it idempotently exactly
like `skills/linear/blocked-label.md` manages `blocked`: ensure the label exists on the team
once (`create_issue_label({ team, name: "claimed", color: "#5E6AD2", description: "Auto-applied
by backlogd while a solve/review session holds an active claim on this problem." })`),
attach it when this session acquires the claim, and detach it on release. It is a **no-op
when it already matches**. If you skip the label, the lock still works — the comment is
authoritative. Do not gate any standoff decision on the label; always read the comment.

## TTL — 2 hours

A claim is **stale** when `now - at > 2h` (UTC). A stale claim is treated as **absent**: the
new claimant overwrites it (upsert the same comment with a fresh `session`/`at`) and
proceeds. This is what guarantees a crashed or abandoned session never deadlocks a
problem — its claim simply ages out and the work becomes reclaimable on the next pickup.

- **Value:** `2h`. Chosen as comfortably longer than a normal solve/review run (minutes to
  low tens of minutes, even with the gate + verdict chain) yet short enough that an
  abandoned problem frees within one working session. If you change it, change it **here** —
  this line is the single documented source of the TTL.
- **Refresh**, don't just acquire: a long-running holder re-stamps `at` at each natural
  checkpoint it already touches the claim (re-acquire/refresh on pickup and on resume) so an
  in-flight run that legitimately runs long does not let its own claim expire mid-flight.

## The three operations

All three go through the official `mcp__linear__*` MCP only — **no external store, no API
key, no new service** (ADR-004; see `skills/linear/SKILL.md` → *Boundaries*). Each is built
on the read-→capture-`id`-→write upsert from `linear-mcp.md`.

### `check` — is there a live claim, and whose?

Run this **before the first state mutation** on a problem (solve pickup; review pick) and
again **immediately before merge** (the base-race guard). It is read-only.

1. `list_comments({ issueId, orderBy: "updatedAt", limit: <small> })`.
2. Filter to bodies starting with `**[backlogd]** Claim` carrying a `<!-- claim: ... -->`
   marker. Take the most recent.
3. **No claim comment** → `absent`. Proceed (and `acquire` if this is a pickup).
4. **Claim present** → parse `session` and `at` from the marker:
   - `now - at > 2h` (TTL) → **stale**, treat as `absent` (reclaimable — overwrite on
     `acquire`).
   - `session == $SESSION` (mine) → **own** — I already hold it; refresh `at` and proceed.
     This is the normal re-run / resume case and must never stand off against itself.
   - `session != $SESSION` and not stale → **held by another live session** → **stand off**
     (see below). Capture `session` and `at` for the standoff message.

### `acquire` / `refresh` — take or re-stamp the claim under `$SESSION`

Run at solve pickup (before the In Progress transition) and on resume; refresh on each
re-entry. Upsert the **one** claim comment (mirrors the health-comment upsert):

1. `list_comments({ issueId })` → filter to the `**[backlogd]** Claim` comment (the
   `<!-- claim: ... -->` marker is the dedupe key).
2. **Matched** → capture its `id` → `save_comment({ id, body })` with a fresh
   `session=$SESSION; at=<now>` — overwrites a stale / handed-back claim in place.
3. **Not matched** → `save_comment({ issueId, body })` to create it.
4. If using the companion label, attach `claimed` (idempotent, per `blocked-label.md`).

Acquiring is a single upserted comment — re-running never spawns a second claim comment.

### `release` — drop the claim at a clean exit

Run at **every clean exit** so a normally-finishing run leaves **no lingering claim**:

- solve handoff to *In Review* (`skills/solve/handoff.md` §4),
- merge to *Done* (`commands/review.md` step 5 / `skills/solve/ship.md`, after the merge
  succeeds),
- a surfaced blocker / context gap / AC challenge / *sent back* (`skills/solve/capture.md`
  BLOCKED / NEEDS_CONTEXT / DISPUTES_AC branches; `commands/review.md` step 5 *sent back*).

Release is **release-if-mine**:

1. `list_comments({ issueId })` → find the `**[backlogd]** Claim` comment.
2. If its `session == $SESSION`, **edit it in place** to a released tombstone (do **not**
   leave a live-looking claim, and do **not** delete — keep the audit trail):

   ```markdown
   **[backlogd]** Claim — released by `<session>` at <UTC timestamp>

   <!-- claim: released; by=<session>; at=<UTC timestamp> -->
   ```

   A `<!-- claim: released ... -->` marker reads as **absent** to `check` (it carries no
   live `session=`/`at=` pair), so the next pickup acquires cleanly.
3. If the claim is held by a **different** session (e.g. a `--steal` took it from under a
   crashed run, or the TTL already expired and another session reclaimed), **do not
   overwrite it** — leave it alone and note it; releasing someone else's live claim would
   re-introduce the race. Detach the `claimed` label only if you still hold it.

An **abandoned** run (crash, killed terminal) never reaches `release`; that case is covered
by the TTL, not by release.

## Standing off — what a second session does when the claim is held

When `check` returns **held by another live session**, the second session **stands off** —
it does **not** transition Linear state, does **not** dispatch a developer/reviewer, and does
**not** merge. The behaviour depends on how the problem was selected:

- **Auto-pick** (no explicit id — `/backlogd:solve` / `/backlogd:review` with no argument):
  **skip this problem and pick the next** candidate. The held problem is simply not eligible
  while another session owns it — the loop moves on, which is exactly the parallel-sessions
  design goal (multiple sessions work *different* problems concurrently without colliding).
- **Explicitly named** (`/backlogd:solve NB-414` / `/backlogd:review NB-414`): **surface a
  held-by message and stop** — do not silently skip a problem the operator named. Template:

  ```text
  {identifier} is claimed by another session.

    Held by: {session}
    Since:   {at} ({age})

  Standing off — not transitioning state, not dispatching, not merging.
  If that session is dead, re-run with --steal to force-take the claim, or wait for it to
  age out (TTL 2h) and re-run.
  ```

  Then stop. Uniform stand-off applies **regardless of who holds it** (solve or review,
  automated or human) — there is no human-review-preempts-automated special case (PO
  decision, NB-414): the TTL handles a crashed holder, so a special case would add
  complexity for a near-moot case. A human running `/backlogd:review` while a solve session
  holds the claim stands off the same as any other holder.

## `--steal` — the operator override

`--steal` is the explicit escape hatch to **force-take a known-dead claim before its TTL**
(e.g. you know the holding session crashed and you don't want to wait 2h). When `--steal` is
passed:

- `check` treats an existing claim as `absent` **regardless of `session` or `at`**, and
  `acquire` overwrites it under `$SESSION`.
- Note in the run output that a claim was stolen, quoting the prior `session`/`at` it
  overwrote, so the audit trail records the force-take.
- `--steal` only applies to an **explicitly named** problem — stealing during an auto-pick
  makes no sense (auto-pick already skips a claimed problem and moves on).

Both `/backlogd:solve` and `/backlogd:review` parse `--steal` in their flag-parse step (solve
already parses `--dryrun` / `--no-ship` in step 1; review parses it alongside).

## Where to call this from

| Caller | Site | Operation |
| --- | --- | --- |
| `/backlogd:solve` | pickup (`skills/solve/pickup.md`) / dispatch step 1 (`skills/solve/dispatch.md`), **before** the first In Progress transition | `check` → stand off if held by another live session; else `acquire` under `$SESSION` |
| `/backlogd:solve` | resume reconcile (`skills/solve/resume.md`) | `check` folded in as a fifth source of truth: another live session's claim ⇒ `inconsistent` (surface + stand off); stale / own-session claim ⇒ reclaimable, `refresh` and continue |
| `/backlogd:solve` | handoff to In Review (`skills/solve/handoff.md` §4) | `release` |
| `/backlogd:solve` | ship-on-green merge (`skills/solve/ship.md` → `commands/review.md` step 5) | re-`check` in the base-race guard before merge; `release` after merge |
| `/backlogd:solve` | BLOCKED / NEEDS_CONTEXT / DISPUTES_AC stop (`skills/solve/capture.md`) | `release` (the run ends cleanly with a surfaced blocker, context gap, or AC challenge; the claim must not linger) |
| `/backlogd:review` | pick (`commands/review.md` step 3), **before** the reviewer dispatch | `check` → stand off if held by another live session; else `acquire` under the reviewer session id |
| `/backlogd:review` | merge / sent-back (`commands/review.md` step 5) | re-`check` in the base-race guard before merge; `release` after merge **or** on *sent back* |

Each caller already reads the problem issue at these points — pass that `get_issue` /
`list_comments` result in rather than re-fetching, and write at most one `save_comment` per
operation.

## Single-session happy path — unchanged

A **first-ever** solve on a fresh, unclaimed problem behaves exactly as before plus one
acquire: `check` returns `absent`, the session `acquire`s the claim, solves, and `release`s
at handoff/merge. No standoff ever fires, reconcile stays a no-op on a fresh problem, and the
base-race guard's extra re-check passes trivially (the session still holds its own claim).
There is **no behaviour regression** on the single-session path — the only added write is the
one claim comment, upserted and tombstoned within the same run.

## Idempotency contract

- Re-running `check` is read-only and side-effect-free.
- Re-running `acquire` within the same session updates the one claim comment in place
  (refreshes `at`); it never creates a second claim comment.
- `release` is release-if-mine; running it twice is a no-op the second time (the comment is
  already a `released` tombstone, or held by someone else and left alone).
- A stale claim (`at` older than the TTL) is reclaimed by the next `acquire`, never requiring
  manual cleanup.
