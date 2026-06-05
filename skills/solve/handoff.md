---
name: solve-handoff
description: Hand a solved problem back to the product owner — push the branch and open the PR into the integration branch (skipped on ops-only runs — there is no PR), record pr_opened (standard path only) + run_completed on the graph, post a high-level PO-facing solution brief, and move the problem to In Review (the PO accepts via /backlogd:review).
---

# solve — handoff at In Review

> **Dry run:** in `--dryrun` mode, this section does not run — the dry run exits after
> printing the plan (see `skills/solve/dryrun.md`). No push, no PR, no graph write, no
> comment, no *In Review* transition.

When every unit is `completed`, the problem is solved. Do **not** mark it Done —
`/backlogd:review` (or the PO) accepts later. Instead:

## 1. Push the branch and open the PR

> **Ops-only run?** If this run took the **`kind:ops`** path (see `skills/solve/walk.md`
> and `skills/solve/ops.md`) there is no `$WT`, no commit, and **no PR to open** — skip
> this section and jump to *§2 Record run completion on the graph* (skipping just the
> `pr-opened` write), then continue to the solution brief in §3. The developer's
> `**[backlogd developer]**` action-log comments on the units are the auditable artifact
> in place of a PR diff.
>
> **Parallel walk?** If `skills/solve/walk.md` dispatched any group of ≥2 units in
> parallel, the per-unit sub-branches have already been collected into the problem
> branch (`$WT`) and the per-unit worktrees torn down — the collect step happens at the
> end of each parallel group, not here. The PR is still **one** PR off the problem
> branch. If you see any `backlogd-wt-{identifier}-unit-*` worktrees still present at
> this point, the run did not collect cleanly — stop and surface to the product owner.

Push the branch and open the PR into the integration branch (reuse an existing PR on a
re-run); put the issue identifier in the title/body so Linear links the PR to the problem:

    git -C "$WT" push -u origin {gitBranchName}
    gh pr create --base {integration} --head {gitBranchName} --title "…(#{identifier})" --body "…"

(No `gh` available? Push the branch and ask the PO to open the PR.)

## 2. Record the PR open + run completion on the graph and the ledger

Best-effort — neither write must ever block the handoff. Record the PR open time
immediately after the PR exists, and the run completion at the very end. The
`dispatch_started` edges from `skills/solve/dispatch.md` give both graph calls their
start clock automatically (so `dispatch_to_pr` latency and `run_wall_time` are derived
for you):

    python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/graph.py" pr-opened \
        --session "$SESSION" --problem {identifier}

    python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/graph.py" run-end \
        --session "$SESSION" --problem {identifier} \
        --fanout {peak-fanout from walk.md, 1 if the walk never parallelised}

The `--fanout` field is the **peak parallel-group size observed during this run** (from
`skills/solve/walk.md`'s parallel-walk bookkeeping): `1` for a sequential / single-unit
run (the byte-identical-to-today case), `≥2` when at least one parallel group ran. The
`/backlogd:metrics` aggregate reads this to break out parallel-vs-sequential effects on
`run_wall_time` and `dispatch_to_pr`. Omitting `--fanout` (or passing `1`) yields the
legacy behaviour — the field is additive on the `run_completed` edge.

Then, **at the same lifecycle point** (right after `run-end`), append one durable record
to the **solve ledger** (`scripts/ledger.py` → `.backlogd/ledger.jsonl`, gitignored). The
ledger is the problem-keyed, append-only durable run record that complements the
session-keyed graph telemetry (NB-426): resume short-circuits off it and the retro reads
it as local run history, without a Linear round-trip. Co-locating the append with the
graph's `run_completed` is what keeps the two stores from silently disagreeing — the graph
stays the metrics source of truth, the ledger the problem-first durable record:

    python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/ledger.py" record-run \
        --problem {identifier} \
        --units-json '[{"identifier":"{unit}","outcome":"{solved|partial|blocked}"}, ...]' \
        --pr {PR url, or omit on an ops-only run} \
        --outcome {run-level outcome, e.g. solved}

Pass each solved unit and its outcome (the per-unit STATUS captured in
`skills/solve/capture.md`); for a single-issue problem the one unit is the problem itself.
The record names the problem, the units solved with their outcomes, the PR reference, and
the run timestamp (defaulted to now). The ledger write is append-only — it never rewrites
the file — so it cannot truncate a prior run's record.

> **Ops-only run?** Skip the `pr-opened` call — there is no PR, so the `dispatch_to_pr`
> latency is undefined for this run. Still call `run-end` (with `--fanout 1` — ops-only
> runs are sequential); the run completed, and `run_wall_time` (earliest
> `dispatch_started` → run end) remains meaningful. Still call `ledger record-run` too —
> just **omit `--pr`** (the record's `pr` is then `null`); the durable run record is as
> useful for an ops-only run as a standard one.

## 3. Post a high-level, PO-facing solution brief

Where the brief lives depends on the problem's **form** (set at `/backlogd:scope` time
— see `commands/scope.md` §4):

- **Single-Issue / sub-issue form** — post the brief as a **comment** on the problem
  issue (unchanged behaviour).
- **Project-form** — write the brief as a `Solution brief` **Document** attached to
  the Project, seeded from `templates/solution-brief.md`. **Single-Issue keeps the
  brief-as-comment with the `**[backlogd]**` badge unchanged.**

### Single-Issue / sub-issue form — brief as a comment

Post one comment on the problem issue, edited in place, with the `**[backlogd]**` badge.
Write it for a product owner who owns the solution but is not reviewing code. This is a
Linear comment the PO reads, so render it per
[`../../output-styles/linear-comment.md`](../../output-styles/linear-comment.md) (no
markdown tables, no status or checkmark emoji, language-tagged fences, max two-level
nesting; show any state with a `- [x]` / `- [ ]` checkbox or a bold label, never an emoji):

    **[backlogd]** Solution brief

    Problem: {one line, what was asked}
    What was solved: {the outcome, in plain terms}
    How (high level): {approach, 2-4 bullets, no code-level detail}
    Artifacts: {files/areas changed, links, or what the PO now has}
    {Needs your eyes: {anything for the PO to decide}, omit if nothing}

**Surface `DONE_WITH_CONCERNS` concerns under *Needs your eyes*.** When any unit returned
`STATUS: DONE_WITH_CONCERNS`, `skills/solve/dispatch.md` step 7 (via
`skills/solve/capture.md`) carried that unit's `Concerns:` text forward. List each concern
here as a *Needs your eyes* bullet (alongside any `untestable:` items the gate carried
forward) so the PO sees the caveat without reading the work log. The increment still
landed — these are flags, not blockers. (`BLOCKED` / `NEEDS_CONTEXT` units never reach
handoff: the run stops before In Review when any unit returns a non-terminal STATUS — see
`skills/solve/capture.md`.)

(On a single-issue problem it sits alongside the developer's `**[backlogd developer]**`
work-log comment — a PO summary plus the work log, not a duplicate.)

### Project-form — brief as a Document

Write **one** `Solution brief` Document attached to the Project, edited in place by
`id` on a re-run (no duplicates — there is one `Solution brief` Document per Project).
Seed the body from `templates/solution-brief.md` — at minimum it carries `## What
changed` and `## How it was verified` headings (and optionally `## Follow-ups`).

Follow the upsert procedure in
[`skills/linear/references/documents-and-updates.md`](../linear/references/documents-and-updates.md)
(`list_documents({ projectId }) → match title === "Solution brief" → save_document({
id, content })` to update; otherwise `save_document({ project, title: "Solution
brief", content, icon: ":white_check_mark:" })` to create — note the `project` /
`projectId` parameter asymmetry there). The Document sits alongside the per-unit
`**[backlogd developer]**` work-log comments on each sub-issue — a PO summary plus
the work logs, not a duplicate of either.

`/backlogd:review` reads this Document at verdict time (see `commands/review.md` §3)
and may append accept/sent-back notes to it on a verdict.

**Ops-only runs:** the brief is the same shape, but `What changed` / `How it was
verified` (or `Artifacts` on the single-Issue comment form) points at the **action
logs on each unit** (the `**[backlogd developer]**` comments listing the `gh` calls),
the GitHub surface(s) those calls changed (Topics, Discussions, Releases, labels, repo
metadata), and any external content drafted in the tree (e.g. `docs/PROMOTION.md`) —
not a PR link, because there isn't one.

## 4. Move the problem to In Review

Move the problem to the *In Review* state (resolved in `skills/solve/identity.md`). On a
**Project-form** run, post a project-thread health update alongside the transition with
marker `handback` — typically `on track` because the slice is complete and unblocked
(see **`skills/linear/references/documents-and-updates.md` § "Project health updates"**
for the body shape and dedupe-by-marker procedure). **Single-issue and sub-issue forms do
NOT post this update.** The handoff is then complete.

This is **not** the end of the run on the happy path: `/backlogd:solve` continues to its
**ship-on-green** final phase (`commands/solve.md` step 8 → **`skills/solve/ship.md`**),
which auto-chains the same independent verdict review `/backlogd:review` owns and, on a
fully-green verdict, merges the PR and moves the problem to *Done* with no human gate. Under
`--dryrun` the run already exited before this skill; under `--no-ship` the ship phase still
runs the verdict but **holds the problem at In Review with the PR open** — and `/backlogd:review`
(or the PO) verifies the AC and merges the PR to land it then. On ops-only runs there is no PR
to merge: the verdict (auto-chained, or via a manual `/backlogd:review`) verifies the AC
against the action logs on the units and the GitHub surfaces they changed, and on accept the
problem moves straight to *Done*.

> **Claim-lock at handoff.** The claim-lock (**`skills/linear/claim-lock.md`**) is **not**
> released here on the happy path — ship-on-green's verdict + base-race guard + merge run
> next and the base-race guard **re-checks the live claim immediately before merge**, so the
> claim must still be ours through the merge (which `release`s it). Release at this In Review
> handback **only when the run will actually stop here** — i.e. under `--no-ship` /
> `BACKLOGD_SHIP_ON_GREEN=0`, where the problem is deliberately held at In Review and nothing
> further merges in this run. In that opted-out case, `release` the claim now so a later
> `/backlogd:review` (or another solve) re-acquires cleanly. On the ship-on-green path,
> `skills/solve/ship.md` owns the release (at merge, or on sent-back / blocker).
