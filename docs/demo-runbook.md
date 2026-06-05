# Demo runbook — recording the launch demo

This is the **single, self-contained script** for backlogd's launch demo. Follow it
top-to-bottom and you produce the demo with no improvisation: it names the exact problem to
file, stages the repo and Linear so the reviewer reliably blocks on a missing standard, gives
the literal command sequence, says how to capture both the terminal and the Linear side, and
states where the recorded asset lands and how the README references it.

It does **not** re-derive the demo's beats. Those are fixed by the canonical
**[Demo run-of-show](ROADMAP.md#demo-run-of-show)** in the roadmap (the six beats NB-394
wrote, citing NB-396). This runbook is the executable expansion of exactly those six beats —
if a beat here and a beat there ever disagree, the roadmap is canonical and this file is the
bug. Keep them in lockstep.

The hero moment is **beat 3 — the reviewer blocks on a missing load-bearing standard**. That
is the beat that shows backlogd is a _team_, not a single-agent runner: a runner guesses and
ships plausible-wrong work; backlogd surfaces "we need a rule for this" and routes the
decision to the product owner. Everything in the staging below exists to make that block fire
deterministically, on cue, on a real backlogd problem (the dogfood angle).

> **Read before you record.** Skim [`README.md`](../README.md) (the loop + the commands),
> [`commands/solve.md`](../commands/solve.md) (ship-on-green), and
> [`agents/reviewer.md`](../agents/reviewer.md) (the `block` calibration) once, so the
> on-screen output is familiar while you drive. The demo is a real run — Linear state and a
> real PR change — so do a dry pass first (see [Rehearse](#rehearse-with---dryrun-first)).

## What the demo proves, in order

The six canonical beats (from [the run-of-show](ROADMAP.md#demo-run-of-show)), each
mapped to what you will see on screen and in Linear:

1. **File a problem** — a Linear issue with the `problem` label (the PO act).
2. **The team picks it up** — `/backlogd:solve` moves it _Backlog → In Progress_, dispatches
   a specialist; role-prefixed comments and the delegate field show _which_ agent is acting.
3. **The reviewer blocks on a missing standard** — the verdict is `block`, not `accepted`,
   naming the missing load-bearing standard. **The beat to feature.**
4. **The PO defines it** — the block surfaces as a Linear-native `Define standard for {X}`
   sub-issue with the parent _blocked-by_ it; the PO answers the standards question.
5. **The team resolves it** — the scrum-master refines and solves the sub-issue (writing the
   ADR); the parent unblocks.
6. **PR merged** — the original problem continues to a fully-green verdict and squash-merges
   to _Done_.

## Prerequisites

Do these once, before you hit record. None of them is on camera.

- **A clean checkout on `dev`** with the backlogd plugin installed (`/plugin install
  backlogd`) and the **Linear MCP enabled and signed in** — see [`README.md`](../README.md)
  → _Setup_. The runtime loop is keyless (OAuth-as-the-user, per
  [ADR-002](standards/adrs/ADR-002-keyless-mcp.md)); there is nothing to paste.
- **The `problem` label exists** in your Linear workspace (the whole data model — a problem
  is a labelled issue). If your workspace is fresh, `/backlogd:init` seeds it; see
  [`docs/guides/workspace-bootstrap.md`](guides/workspace-bootstrap.md).
- **A terminal you are happy to film** — a clean prompt, a readable font size, a wide-enough
  window that `/backlogd:solve`'s output does not wrap awkwardly. Light or dark, your call;
  keep it consistent.
- **Two Linear browser tabs** ready (see [Capturing the Linear side](#capturing-the-linear-side)):
  one on the problem issue, one on a saved view filtered to the `problem` label, so you can
  cut to the issue's _Delegate_ field and its `**[backlogd …]**` comments.
- **The recorder of your choice installed** — [asciinema](#terminal-capture--asciinema-preferred)
  (preferred) or a [GIF recorder](#gif-fallback) (fallback).

## The scripted problem to file

File **exactly this** as a Linear issue, with the `problem` label, left in your Backlog. It is
a _real_ backlogd problem (the dogfood angle is the strongest framing — the demo is backlogd
solving a backlogd problem), and it is chosen so the run deterministically reaches the block:
its outcome forces a **persisted on-disk data-format decision**, which is a one-way door (live
data is migration-cost to change) with wide blast-radius (every later run inherits the shape)
— and **no current Accepted standard governs an on-disk data format** (see
[Why this triggers the block](#why-this-triggers-the-block-and-not-a-flag-and-proceed)).

**Title:**

```text
Persist a per-run solve ledger under .backlogd/ so re-runs and the retro can read run history
```

**Description (the issue body — paste verbatim):**

```markdown
## Problem

A `/backlogd:solve` run today leaves its trace across Linear comments, the PR, and the
execution graph, but there is no single durable record _on disk_ of "what this repo's solve
runs did" that a later run — or a future retrospective — can read cheaply without walking
Linear. When a run is resumed or re-dispatched, the orchestrator reconstructs state from
several sources; a small persisted ledger of completed runs would make resume cheaper and give
the retro a local history to read.

Persist a per-run **solve ledger** under the existing gitignored `.backlogd/` directory: one
durable record per solved problem (identifier, the units solved, the resulting PR, the
outcome, a timestamp), appended as runs complete, so a re-run can short-circuit and a later
retrospective can read run history locally.

## Acceptance Criteria

- [ ] [review] A solve run writes a durable per-run record under `.backlogd/` capturing the
      problem identifier, the units solved, the PR reference, the outcome, and a timestamp.
- [ ] [review] A re-run reads the ledger and short-circuits work that the ledger shows is
      already complete, rather than reconstructing it from Linear alone.
- [ ] [review] The ledger is append-friendly and survives across runs (it is not truncated or
      overwritten wholesale on each run).
- [ ] [review] The directory stays gitignored — no ledger content is committed to the repo.
```

Leave the issue **unshaped** (no `## Specialist` line, no decomposition) — you will run
`/backlogd:scope` on camera so the audience sees the scrum-master shape it. Do **not**
pre-apply an `agent:*` label; let scope pick the specialist (it will route this to the generic
`developer`, which is correct — this is a code problem, not a docs one).

### Why this triggers the block (and not a flag-and-proceed)

The reviewer's `block` is calibrated by **reversibility × blast-radius** (see
[`agents/reviewer.md`](../agents/reviewer.md) → _Calibrating the block_). It fires **only** on
a one-way door — _irreversible **and** wide blast-radius_ — so a standards-light repo stays
usable. This problem is deliberately squarely a one-way door, and it matches the reviewer's
own worked example almost word for word:

- **Irreversible** — the AC forces a **persisted on-disk format** (a record under
  `.backlogd/` with a defined shape). Once real runs have written records, changing the shape
  is a migration against live data. The reviewer's calibration names exactly this: _"a
  persisted data shape with live rows … migration-cost to change."_
- **Wide blast-radius** — the format is read by **re-runs** (AC #2) and by the **future
  retrospective** (`/backlogd:retro`, the named consumer in the problem body). It is not local
  to one file; every later run and the adaptation loop inherit the schema. The reviewer's
  calibration names this too: _"it sets a precedent every later problem inherits."_
- **Ungoverned** — walk the index ([`docs/standards/index.json`](standards/index.json)) and
  filter by scope. The four **Accepted** standards are ADR-001 (agent identity), ADR-002
  (keyless / no server / secret-custody), ADR-003 (canonical _Linear_ workspace config), and
  ADR-004 (problem-type-agnostic identity & scope). **None of them governs the on-disk data
  format of a persisted artifact.** ADR-002 is adjacent but is about _secrets and hosting_,
  not the schema of a non-secret ledger — and the developer must honour it (keep the file
  gitignored, no token), which it does, so ADR-002 is _honoured_, not the missing rule.
  ADR-005 (a tokenless-bridge runtime) is **Proposed**, so the reviewer does **not** enforce
  it — non-Accepted statuses are skipped.

So the reviewer's index-first walk reaches its **fourth outcome**: a consequential decision
with no governing Accepted standard. It **names the gap and does not invent the standard** —
classifying it as a `standard:` gap (a durable, cross-issue governance gap: how should
backlogd persist on-disk run/state data — format, location, schema-evolution policy?), which
is the kind that graduates into an ADR and escalates to the PO. That is beat 3.

This staging relies on **no behaviour the reviewer does not have**. It needs only what
`agents/reviewer.md` already does: read the index, filter by scope, apply the one-way-door
calibration, and emit `block` with a `standard:` classification. If you change the problem,
preserve all three properties (irreversible **and** wide **and** ungoverned) or the reviewer
will (correctly) _flag-and-proceed_ instead of blocking, and the hero beat will not fire.

## The command sequence

Drive these in order, on camera. The whole demo is **three `/backlogd:*` invocations** plus
**one PO decision** plus **one ADR write** — narrate each beat as it happens.

### 1. Shape it — `/backlogd:scope`

```text
/backlogd:scope
```

(Or name it explicitly: `/backlogd:scope {identifier}`.) The scrum-master dispatches the
`backlogd:refiner`, writes a spec + `## Acceptance Criteria` into the issue **description**,
picks the specialist (generic `developer` here — it says so in its report and writes a
`**Specialist:** developer (no specialist matched)` line), sets priority, and **stops**. It
does _not_ solve. On screen you get scope's report (`Shaped: {identifier} …`); in Linear the
issue now carries the AC. This is beat 1's shaped form.

> Optional but tidy: `/backlogd:scope` confirms the problem is execution-ready before you
> solve, so the audience sees the shape. You can skip straight to `/backlogd:solve` (it shapes
> inline if needed), but running scope first makes the decomposition visible.

### 2. Solve it — `/backlogd:solve` (ship-on-green auto-chains the block)

```text
/backlogd:solve
```

This is the beat-2-through-beat-3 engine. **Ship-on-green is on by default** (see
[`commands/solve.md`](../commands/solve.md) → _Flags_ and step 8), so a single `/backlogd:solve`:

- moves the problem **Backlog → In Progress** and dispatches a `backlogd:developer` (beat 2);
- the developer edits in its worktree and posts its `**[backlogd developer]**` work-log
  comment, then the run opens **one PR** and moves the problem to **In Review** with a
  solution brief;
- **auto-chains the independent verdict review** as its final phase — the same
  `backlogd:reviewer` dispatch that `/backlogd:review` owns (`commands/review.md` step 3),
  _reused, not re-implemented_. The reviewer reads the diff with a fresh context, walks the
  AC and the Definition of Done, consults the standards index, and — for this problem —
  returns a **`block`** rollup naming the missing standard (beat 3).

Because the verdict runs _inside_ the solve run, **the block surfaces without a second
command.** You do not need to type `/backlogd:review` for the demo — ship-on-green already
ran it. The run does **not** merge: a `NO-STANDARD` block holds the problem at _In Review_
and surfaces the gap to you. On screen, solve's report shows `verdict -> block` and `problem ->
In Review (blocked-by {Define standard for X})`.

> `/backlogd:review` is the **manual re-entry** to the very same gate — reach for it to
> re-run the verdict after the standard lands (beat 6 below). On the happy path solve already
> ran it for you. (`--no-ship` would hold the run at In Review _without_ running toward a
> merge decision; do **not** pass it for the demo — you want the auto-chained verdict.)

### 3. The block is routed — Linear-native (`commands/review.md` step 5)

When the reviewer returns `block`, the scrum-master **routes it** (this is automatic — it is
the orchestrator's job in [`commands/review.md`](../commands/review.md) step 5, reused by
ship-on-green via `skills/solve/ship.md`). For a `standard:` gap the scrum-master:

- creates a **`Define standard for {X}` sub-issue** of the problem (`save_issue` with
  `parentId` = the problem; the body is the reviewer's named gap);
- marks the **parent _blocked-by_ it** (`save_issue(id: problem, blockedBy: [sub-issue])`) —
  real Linear sub-issue + `blocked-by` primitives, not a buried comment;
- re-evaluates the `blocked` label and leaves the problem **In Review**, PR open;
- **surfaces the standards question to you, the PO** — _"what standard would you like for
  {X}?"_ It does **not** invent the answer (authoring a missing standard yourself would
  silently make the scrum-master the architect — the non-delegable standards boundary).

This is beats 3→4 made visible in Linear: cut to the issue and show the new sub-issue and the
_Blocked by_ relation (see [Capturing the Linear side](#capturing-the-linear-side)).

### 4. The PO answers — beat 4

On camera, answer the standards question in one or two sentences — the PO decision. For the
scripted gap, a good on-screen answer is short and concrete, for example:

> Persisted on-disk run/state data lives under the gitignored `.backlogd/` directory as
> append-only newline-delimited JSON, one record per line, each carrying a schema `version`
> field; readers tolerate unknown fields and the schema only ever grows (no field is removed
> or repurposed in place). Never commit `.backlogd/` content.

That is _your_ call as PO — the demo's point is that the decision routes to you, not that this
exact wording is mandated. Keep it crisp; it becomes the ADR's decision.

### 5. The team writes the ADR and the parent unblocks — beat 5

On the PO's answer, the scrum-master **refines and solves the `Define standard for {X}`
sub-issue**. Solving it means **writing a new ADR under
[`docs/standards/adrs/`](standards/adrs/)** from
[`TEMPLATE.md`](standards/adrs/TEMPLATE.md) — the next free number (ADR-006 at time of
writing; **never reuse a number** — check the directory for the highest existing id first),
`status: Accepted`, with the front-matter `assertion` capturing the PO's rule and an
`applies-to` scope naming the persisted-data / on-disk-format domain.

Writing the ADR **regenerates the index** — run it in the same change:

```bash
python scripts/standards_index.py
```

CI's drift test (`scripts/test_standards_index.py`) fails if the committed
`docs/standards/index.json` does not match the corpus, so the regeneration is not optional.
Once the sub-issue is `completed` (its own small PR merged), the parent **unblocks**
automatically (the `blocked-by` relation clears; the `blocked` label is removed). Beat 5 is
the corpus growing on demand — exactly ADR-004's _"value = specialists × standards"_ made
operational, and the standards-growth half of the adaptation pillar.

### 6. Re-run the verdict and merge — beat 6

With the standard now Accepted, carry the original problem to a green verdict:

```text
/backlogd:review {identifier}
```

The `backlogd:reviewer` runs again with a fresh context; the once-`block`ed decision now
**resolves against the freshly-Accepted ADR** (the index the reviewer reads first now contains
it). On a **fully-green verdict** — every AC line MET, every DoD line MET, CI green, zero
`[manual]`, zero NEEDS-PO, no NO-STANDARD block — the scrum-master runs the base-race guard (re-confirm CI green
and the PR cleanly mergeable) and **squash-merges** the PR into `dev`, moving the problem to
**Done**:

```text
gh pr merge {pr} --squash --delete-branch
```

(The scrum-master runs the merge — you do not type it by hand; it is shown here so the
on-screen action is recognisable.) That is beat 6: the original problem closes _Done_, merged,
having grown the standards corpus on its way through. End the recording here, on the merged
state.

## Capture instructions

The transparency story is half the demo, so capture **both** the terminal and the Linear UI.
A terminal-only recording misses beats 3–5 entirely (the block, the sub-issue, the
PO question all live in Linear).

### Terminal capture — asciinema (preferred)

[asciinema](https://asciinema.org) records the terminal as a lightweight, replayable cast
(text, not video), which stays crisp at any size and is tiny to host. Record the whole driven
session into a cast file:

```bash
asciinema rec docs/assets/demo.cast --title "backlogd — the missing-standard block" --idle-time-limit 2
```

- `--idle-time-limit 2` caps dead air at 2 seconds so the long agent turns do not drag.
- Run your command sequence in the recorded shell; press `Ctrl-D` (or `exit`) to stop.
- Preview locally with `asciinema play docs/assets/demo.cast` before you commit anything.

For an inline-playable artifact (and for the launch post), render the cast to an animated SVG
with [`svg-term`](https://github.com/marionebl/svg-term-cli) (renders in GitHub Markdown,
unlike an asciinema iframe):

```bash
svg-term --in docs/assets/demo.cast --out docs/assets/demo.svg --window --no-cursor
```

### GIF fallback

If a cast does not fit (for example you must show the browser and the terminal in one frame),
record a GIF instead with a screen recorder such as
[`asciinema agg`](https://github.com/asciinema/agg) (cast → GIF) or a desktop tool like
Peek / LICEcap:

```bash
agg docs/assets/demo.cast docs/assets/demo.gif
```

Keep the GIF under a few MB (trim idle time, cap the frame rate, scale to a sensible width) so
it loads fast in the README and on social cards.

### No audio

The asset is **silent** — no voice-over, no music, no audio track. The demo reads as text and
on-screen action; narration goes in the README/launch-post prose around the asset, not in the
asset itself. (A `.cast` carries no audio by construction; for a GIF, this is just a reminder
not to attach a soundtrack.)

### Capturing the Linear side

The terminal shows the orchestrator; **Linear shows _which agent_ did what** — the
transparency pillar. Capture it so the audience sees the system of record, not just stdout:

- **The role-prefixed comments.** On the problem issue, show the `**[backlogd developer]**`
  work-log comment, the `**[backlogd reviewer]**` verdict comment (the audit trail), and the
  scrum-master's `**[backlogd review]**` rollup carrying `Verdict: block` and the
  `- [ ] **NO-STANDARD** standard: …` line. These badges are the visible-agent-identity story
  ([ADR-001](standards/adrs/ADR-001-visible-agent-identity-in-linear.md), Tier 0).
- **The delegate field.** If your workspace has the gated Tier-1 `delegate` experiment
  enabled, show the issue's _Delegate_ field naming the acting agent. If it is not enabled
  (Tier 0 is the default and is perfectly demoable), the comment badges _are_ the identity
  signal — narrate that the actor is visible in the comments. Do not stage a delegate that
  is not really set; show whichever tier the workspace actually runs (per ADR-001).
- **The block as Linear primitives.** Cut to the new **`Define standard for {X}` sub-issue**
  and the parent's **_Blocked by_** relation, and the `blocked` label on the parent. This is
  beat 3→4 rendered as real Linear structure — the single most convincing frame in the demo.
- **The state transitions.** Show the problem moving _Backlog → In Progress → In Review_, and
  finally → _Done_ after beat 6.

Record the browser with the same recorder (a GIF of the Linear tab) or take clean
full-resolution screenshots of these moments and stitch them beside the terminal cast in the
final asset. Either way, the Linear UI must be **visibly rendered** (this is what the two
downstream `[manual]` acceptance criteria check) — not paraphrased in the terminal.

## Rehearse with `--dryrun` first

The demo mutates Linear and opens a real PR, so do a no-side-effects dry pass before you
record:

```text
/backlogd:solve --dryrun {identifier}
```

`--dryrun` prints the dispatch plan and touches nothing — no Linear writes, no git mutation,
no developer dispatch (see [`commands/solve.md`](../commands/solve.md) → _Flags_). Use it to
confirm the problem is shaped and the plan looks right, then record the real run without the
flag.

If a take goes wrong mid-recording (a wrong window, a fat-fingered command), reset cleanly
before re-recording: a fresh `/backlogd:solve` _resumes_ rather than restarting, so to get a
clean beat-2 start either pick a fresh scripted problem or roll the issue back to Backlog and
remove its worktree/branch first. Re-runs are safe — the loop reconciles — but they will not
look like a clean first run on camera.

## The embed plan

The recording itself (the two `[manual]` acceptance criteria) and the README embed are
**downstream of this runbook** — they happen after a maintainer records by following the steps
above. This section states where the asset lands and how it gets referenced, so those
follow-ups are turnkey.

- **Where the asset lands.** Commit the produced asset under a top-level **`docs/assets/`**
  directory — `docs/assets/demo.cast` plus the rendered `docs/assets/demo.svg` (asciinema
  path), or `docs/assets/demo.gif` (GIF fallback). This directory does **not** exist yet;
  whoever lands the asset creates it. Keep the source cast alongside the rendered artifact so
  the asset can be re-rendered later without re-recording.
- **How the README references it (owned by [NB-395](https://linear.app/nicolai-bernsen/issue/NB-395)).**
  The README's demo reference is **NB-395's deliverable, not this runbook's** — do not edit
  the README here. The plan for NB-395: embed the rendered asset near the top of
  [`README.md`](../README.md) (the natural home is just under the opening pitch or in the
  _Status_ section, above _Try the walking skeleton_), with a one-line caption framing it as
  _backlogd solving a real backlogd problem, blocking on a missing standard_. A Markdown image
  reference to the committed in-repo path renders inline on GitHub, for example
  `![backlogd demo](docs/assets/demo.svg)` (or `.gif`); link the caption to this runbook so
  readers can see how the demo was produced. Relative in-repo paths are preferred over a
  hosted URL so the asset is versioned with the repo.
- **Reusable for the launch post ([NB-398](https://linear.app/nicolai-bernsen/issue/NB-398)).**
  The same asset is the launch-post (LinkedIn) hero. The GIF/SVG drops straight into a social
  card; keep it self-contained (no external font or asset dependency) and within the size
  budget above so it plays inline there too. One asset, three homes: this runbook, the README
  (NB-395), and the launch post (NB-398).

## Keep this in sync

If the loop changes — a renamed command, a new flag, a changed label, a different block-routing
mechanism, or a new Accepted standard that would govern the scripted problem's decision — this
runbook goes stale and the demo will not fire as scripted. When you touch
[`commands/scope.md`](../commands/scope.md), [`commands/solve.md`](../commands/solve.md),
[`commands/review.md`](../commands/review.md), [`agents/reviewer.md`](../agents/reviewer.md),
or [`docs/standards/`](standards/), re-read this file and the
[run-of-show](ROADMAP.md#demo-run-of-show) and reconcile both. Most important: if a future ADR
ever governs **on-disk persisted data format**, the scripted problem will no longer block —
swap it for a fresh one-way-door decision in a still-ungoverned domain (re-check the
[index](standards/index.json) for what is Accepted) so beat 3 keeps firing.
