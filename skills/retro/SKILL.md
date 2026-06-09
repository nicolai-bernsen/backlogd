---
name: retro
description: backlogd's Sprint Retrospective mechanism — over a completed milestone (or a cycle / date / count fallback) the retro reads the execution graph as objective evidence, detects cross-issue patterns no single review can see, classifies each learning, and files the load-bearing ones as candidate `kind:improvement` issues for the PO to prioritize. The retro proposes; the PO prioritizes. Use when implementing or modifying `/backlogd:retro`, or any caller that runs the read → detect → classify → file pipeline.
---

# The retrospective mechanism

backlogd runs on Scrum's three empirical pillars — **transparency, inspection,
adaptation**. The first two are wired (Linear is transparent; the execution graph and the
independent verdict review are inspection). **Adaptation is the thinnest pillar**: without
a retrospective that *acts* on the inspection data, the execution graph is just numbers
nobody reads and the loop never closes. This skill is the operating contract behind
`/backlogd:retro` — the Sprint Retrospective, which converts inspection into adaptation by
reading what happened over a scope, identifying the load-bearing improvements, and filing
them.

> **Read this file before** modifying `commands/retro.md` or any caller that runs the
> retro pipeline. The four properties below are load-bearing — break any one and the
> retro stops being an *empirical* loop and becomes vibes.

This is the Sprint Retrospective verbatim from the Scrum Guide: *the Scrum Team inspects
how the last Sprint went … identifies the most helpful changes to improve its
effectiveness … the most impactful improvements are addressed as soon as possible; they
may even be added to the Sprint Backlog.* backlogd's reading: the scope is a **milestone**
(not a fixed time-box), the evidence is the **execution graph** (not memory), and the
improvements are **filed as candidate issues** the PO prioritizes.

## Four properties — why each one matters

### 1. Trigger — milestone-primary, cycle-end safety-net, on-demand entry

backlogd has no time-box-for-sustainability need (an agent team does not burn out), so the
natural retro boundary is **scope, not the calendar**. The trigger is therefore
**milestone-primary**: completing a milestone — the PO's scope/direction marker, set at
project/problem creation — is the conceptual trigger for a retrospective over that scope.

A long-running milestone could still go un-retro'd for a long time, so **cycle-end is an
optional cadence safety-net**: a periodic look-back regardless of milestone state. And
because milestones aren't routine in every workspace yet, the command is **invocable on
demand** with explicit scope selectors so it can be dogfooded today:

| Invocation | Scope |
| --- | --- |
| `/backlogd:retro` | The most-recent completed milestone (fallback: `--last 10` if none). |
| `/backlogd:retro <milestone name>` | That specific milestone. |
| `/backlogd:retro --cycle N` | A time-boxed cycle window (the cadence safety-net). |
| `/backlogd:retro --since <ISO date>` | All problems completed on/after that date. |
| `/backlogd:retro --last N` | The last `N` completed problems. |

The milestone/cycle is the *conceptual* trigger; the command is the *entry point*. Both
are real — a milestone closing is the natural prompt, and the on-demand selectors mean a
retro is never blocked on milestones being set up.

### 2. Data-grounded — read the execution graph, do not self-assess

The retro's **primary evidence is the execution graph** — the agent-execution metadata the
loop records (rework, latency, blockers, partials). This is the property that makes the
retro *objective*. A retrospective that asks "how do we feel it went" reintroduces the
self-marking failure the independent reviewer exists to prevent — at the batch level. The
graph is what *actually happened*, recorded as the loop ran, not a memory or a vibe.

**Consume the existing reducer surface; never re-implement it.** The evidence interface is:

```bash
python scripts/graph.py report --json
```

It exits `0` and emits these documented top-level keys (`metrics()` in `scripts/graph.py`):

| Key | What the retro reads from it |
| --- | --- |
| `dispatches` | per-unit outcomes — `total` / `solved` / `partial` / `blocked` + `partial_rate` / `blocked_rate`. The coarse health of the work. |
| `rework` | problem-level rework — `events`, `problems_with_rework`, `rate`. The single strongest "this was hard" signal: how often work came back from review. |
| `dispatch_to_pr_ms` | dispatch→PR latency `p50` / `p90` — where the loop is slow. |
| `run_wall_time_ms` | end-to-end wall time `p50` / `p90`. |
| `by_area` | per-`area:*`-label aggregates (`dispatches` / `blocked` / `partial` / `rework`) + `by_area_note`. **The cross-issue lens** — which area of work blocks or reworks most. |

The reducer **degrades cleanly on an empty/sparse store** — zero counts and `None`
percentiles, an empty `by_area` with an explanatory `by_area_note` — rather than raising.
So `report --json` is safe to read unconditionally. The `graph-navigation` skill
(`skills/graph-navigation/`) documents the full surface and the inline `load_edges()`
recipes for any slice the rolled-up report doesn't expose (the per-problem rework set,
the slowest dispatches by latency).

> **Why consume, not rebuild.** The reducer is the single source of these metrics — the
> same surface `/backlogd:status` reads for its forecast. A second implementation in the
> retro would drift from it. The retro is a *reader* of the graph, exactly like the
> `graph-navigation` skill; it never writes the graph and never re-derives the math.

### 3. Cross-issue pattern detection — the unique value

A single `/backlogd:review` sees one problem. It catches the gap *in that problem*. What it
**cannot** see is repetition: that the *same* gap showed up in three problems this
milestone, which makes it a **systemic** gap worth a standard, not three one-off notes. The
retro is the **batch-level complement** to the reviewer's in-the-moment gap-detection — it
reads *across* the whole scope.

Patterns to look for, by reading the graph slice and the closed problems' comments
*together*:

- **A recurring missing standard** — ≥2 problems whose `**[backlogd reviewer]**` verdicts
  flagged the same absent rule, or the same NEEDS-PO/UNMET theme. → a systemic gap → a
  high-priority **ADR / standard** candidate (the batch signal NB-378's reviewer can't
  raise alone).
- **A high-blocker or high-rework `area`** — `by_area` shows one `area:*` label with a
  conspicuous `blocked` / `rework` count relative to its `dispatches`. → either a missing
  standard governing that area or a framework friction there.
- **A recurring class of rework** — the same kind of send-back across problems (e.g.
  "tests didn't actually run false-green", "markdownlint --fix broke load-bearing
  content"). → a process/tooling improvement.
- **A latency cliff** — one phase consistently slow in `dispatch_to_pr_ms` /
  `run_wall_time_ms`. → a process candidate, if it repeats.

A pattern is, by definition, **repetition** — "N problems hit X". A single problem's quirk
is not a pattern; it is a one-off (property 4).

### 4. Classify + calibrate — load-bearing only; propose, don't prioritize

Each learning is classified into exactly one of three buckets — the same calibration
discipline the reviewer applies to its verdict:

| Bucket | Trigger | Action |
| --- | --- | --- |
| **recurring failure** | a systemic gap, ≥2 problems | file a candidate **ADR / standard** (`kind:improvement`) |
| **process problem** | the framework itself made the work harder | file a candidate **framework problem / bug** (`kind:improvement`) |
| **one-off** | a single problem's quirk, no repetition | **note in the summary, do not file** |

Two discipline rules hold the output honest:

- **Load-bearing only — no flood.** A milestone produces **a few** filed candidates, not a
  micro-issue per observation. Over-filing is the failure mode: it buries the signal and
  trains the PO to ignore the `kind:improvement` queue. If a proposed improvement can't be
  tied to repeated evidence (graph or cross-issue), it is a one-off — note it, don't file
  it. Same instinct as "don't over-extend the reviewer until the verdict is noise".
- **The retro proposes; the PO prioritizes.** The retro files **candidate** improvements
  and surfaces them; it never decides what gets worked, and it **never works one itself**.
  Self-improvement stays visible and high-priority but **under PO direction** — the team
  does not grade its own homework and auto-fix. This mirrors the reviewer's judge/act
  split: the reviewer judges and the scrum-master acts; the retro proposes and the PO
  prioritizes.

### 5. Positive synthesis — what the team did well, data-derived and cited

Properties 1–4 are pure *gating*: patterns, gaps, rework, blockers — all negative
valence. But cohesion is also **what the team did well and how it is improving over the
scope**, and a retrospective that narrates only failure is half a retrospective. This is
where the *team that plays together* feeling lives for the watching PO. So the retro also
narrates a **positive synthesis** — and it is held to the **same data-grounded discipline
as everything else here**: it is the scrum-master narrating *observed graph data*, not
invented praise.

**Derive it from the same `report --json` you already read (property 2) — do not invent a
metric, and never re-derive the math.** The positive signals are already top-level keys of
that JSON; read them, do not recompute them:

| Positive signal | Read it from | What it shows the PO |
| --- | --- | --- |
| **Clean-gate streak** | `rework.rate` low/zero (`problems_with_rework`/`problems`) | work landing right the first time, not bouncing from review |
| **High solved share** | `dispatches.solved` vs `total` (low `partial_rate`/`blocked_rate`) | units finishing cleanly, few partials/blocks |
| **Faster dispatch→PR** | `dispatch_to_pr_ms.p50` (lower than a prior scope, when comparable) | the loop getting quicker to a PR |
| **The team working in parallel** | `fanout.parallel_runs` / `parallel_rate` | literally the team *playing together* — independent units run concurrently |
| **A clean area** | `by_area` row with high `dispatches`, zero/low `blocked`+`rework` | an area of work that ran smoothly this scope |

Three discipline rules hold the synthesis honest — they are the positive-valence twin of
the no-flood and no-self-marking rules above:

- **Every positive claim cites its evidence — no ungrounded praise.** Each "did well" line
  names the graph metric (or the specific Linear evidence) behind it, exactly as a filed
  candidate must cite its evidence. "Rework fell to 0% (0/6 problems)" is a claim; "the
  team did great" is not. An uncited positive line is indistinguishable from flattery and
  must not be written.
- **Improvement is a *delta*, claimed only when comparable.** "How it is improving" needs
  two points — this scope vs a prior one. Only claim a trend (falling rework, faster
  dispatch→PR) when you actually have the prior figure to compare against; otherwise state
  the level as a level ("rework was 0% this scope"), not a trend. Never invent a baseline.
- **Sparse graph → lean on Linear and say so; never fabricate.** On a sparse/empty store
  (`None` percentiles, zero counts) the positive synthesis leans on the Linear evidence it
  can read directly — problems that closed without returning from *In Review* (a clean
  gate), units solved on the first dispatch — and **says** "sparse graph — positives from
  Linear evidence", exactly as the negative side does. A `None` metric is "—", never a
  fabricated win.

**This synthesis loosens no boundary.** It is the scrum-master *narrating observed data*,
which is squarely the scrum-master's standup/inspection role (`skills/scrum/references/accountabilities.md`).
It does **not** let the reviewer self-mark (the reviewer never appears here; the retro
reads the graph the loop recorded), it does **not** convert the gate into
self-congratulation (the gate is `/backlogd:review` per problem; the retro is a batch
*reader*, not a gate, and files no pass/fail), and it does **not** let the scrum-master
claim credit for a product call (it narrates *execution* metrics — rework, latency,
parallelism — never "we built the right thing", which is the PO's to judge). Positive and
negative synthesis are the same act under the same discipline: observe the data, cite it,
do not invent.

## The candidate improvement issue — exact shape

Each filed candidate is a normal Linear issue, created via the `linear` skill's key-free
official-MCP filing path (`save_issue` with **no `id`** → create — see
`skills/linear/references/linear-mcp.md`). Shape:

- **Labels:** `problem` **and** `kind:improvement`. The `problem` label makes it pickup-able
  by the normal loop (`/backlogd:scope` → `/backlogd:solve`); `kind:improvement` marks it as
  retro-sourced self-improvement so the PO can filter the improvement backlog. **Create the
  `kind:improvement` label on first use** — `create_issue_label({ team, name:
  "kind:improvement" })` if `list_issue_labels` shows it missing (it does not exist in the
  workspace yet). This ensure-first step is **required**, not cosmetic: `save_issue` does
  **not** auto-create labels — an unknown name passed in `save_issue.labels` is silently
  dropped (no error, no label), so the label must exist before it can be applied.
- **Title:** names the *pattern*, not one problem — e.g. "Add an ADR for X — three problems
  this milestone hit the missing standard".
- **Description:** states the pattern, **cites the evidence** (the graph metric and/or the
  specific closed problems + their reviewer/developer comments) so the improvement is
  **traceable back to the inspection data**, and proposes the classification (ADR vs
  framework bug). Traceability is the point — an improvement no one can tie to evidence is
  indistinguishable from a hunch.
- **`## Acceptance Criteria`:** typed per `skills/ac/` (prefer `[review]` for "is this
  standard sound", `[test]` where a check is obvious; `[manual]` only for a fact no
  fresh-context agent can observe). The retro is *proposing* the work, so the AC can be
  thin — `/backlogd:scope` sharpens it when the PO prioritizes it.
- **State + priority:** file **unstarted** at a sensible priority (a systemic gap is
  typically High); the PO re-prioritizes. Do **not** file it started, and do **not**
  decompose it — that is `/backlogd:scope`'s job once prioritized.

## The retro summary — one comment, idempotent

The retro posts **one** summary comment so the inspection→adaptation step is durable and
visible in Linear (not just the terminal). Where it can dedupe, it is an idempotent upsert
keyed by a scope marker, like the project-health and Shipped-summary helpers in
`skills/linear/references/documents-and-updates.md`:

- **Milestone scope** → the **milestone thread** (`save_comment({ milestoneId, body })`),
  **deduped** by the scope marker (see below) — `list_comments({ milestoneId })` lists the
  thread, so a re-run updates in place.
- **No milestone** (cycle / date / count) → the **engagement Project thread**
  (`save_comment({ projectId, body })`), **deduped** by the scope marker (see below) —
  `list_comments({ projectId })` lists the thread, so a re-run updates in place.
  **Verified live 2026-06-03** ([ADR-008](../../docs/standards/adrs/ADR-008-live-surface-verification.md)):
  a probe `list_comments({ projectId })` returned the prior retro summary by its
  `<!-- marker: retro:<scope> -->`, so project-thread marker-dedupe works (the earlier
  "issues-only" reading off the stale 2026-05-28 snapshot was itself an unverified assumption).

Body shape (visible `**[backlogd retro]**` badge; Linear renders the HTML comment as
literal text):

```markdown
**[backlogd retro]** Retrospective — <scope: milestone "X" | cycle N | since <date> | last N>

Problems in scope: <n> closed.
Graph signal: rework <r>% (<rw>/<p>), partial <pa>%, blocked <bl>%, dispatch→PR p50 <ms>.
  (or: "Sparse graph — leaned on Linear evidence: <what>.")

What went well
- <positive synthesis line, each citing its graph/Linear evidence — e.g. "Clean gate: rework 0% (0/6) this scope" / "<k> of <n> units ran in parallel (fanout p50 <f>)" / "dispatch→PR p50 fell to <ms> from <prior>">
- …   (or "Sparse graph — positives from Linear evidence: <what>." / "—" when there is no real signal)

Patterns detected
- <pattern> → <recurring failure → ADR | process problem → bug> → filed <NB-N>
- …

Noted (one-offs, not filed)
- <observation>   (or "—")

Filed for prioritization: <NB-N>, <NB-M>, …   (or "none — nothing load-bearing this scope")

<!-- marker: retro:<milestone-name | cycle-N | since-<date> | last-N> -->
```

The **What went well** block is the positive synthesis (property 5): each line cites the
graph metric (or the Linear evidence on a sparse store) behind it — no ungrounded praise.
It sits **above** the patterns/gaps so the PO reads what the team did well before what it
must fix; on a scope with no real positive signal it renders a single "—", never invented.

The trailing `<!-- marker: retro:<scope> -->` is the dedupe key on **both** paths: on a
re-run over the same scope, `list_comments({ milestoneId })` (milestone scope) or
`list_comments({ projectId })` (no-milestone scope) → filter to bodies starting
`**[backlogd retro]**` → match the marker → capture the comment `id` →
`save_comment({ id, body })` to update in place. Never post a second summary for the same
scope. The `projectId` listing is **verified live 2026-06-03** (see the no-milestone bullet
above).

## Sparse-graph behaviour

On a fresh checkout the graph store is gitignored and may be absent or thin. `report
--json` still exits 0 with zero counts — **that is not an error**. When the graph is
sparse, the retro:

- leans more on the **Linear evidence** it can read directly — rework ≈ problems that
  returned from *In Review* (visible in state history / reviewer "sent back" comments),
  blockers ≈ `blocked`-labelled issues in scope, and the `**[backlogd developer]**` /
  `**[backlogd reviewer]**` comments on the closed problems;
- **says so in the summary** ("sparse graph — leaned on Linear evidence");
- **never fabricates a metric.** A `None` percentile is reported as "—" / "insufficient
  data", never invented.

A retro over a scope with real graph data is a stronger signal than one over a sparse
store — exactly as a verdict backed by `[test]` checks beats one backed by `[review]`
alone. The retro degrades gracefully; it does not pretend.

## How the retro fits the loop

```text
milestone closes  ──┐                  ┌── /backlogd:retro (on-demand, any scope)
(conceptual trigger)│                  │
                    ↓                  ↓
        read graph (report --json) + closed problems in scope
                    ↓
        detect cross-issue patterns → classify (recurring | process | one-off)
                    ↓
        file load-bearing candidates (problem + kind:improvement)  +  post retro summary
                    ↓
        PO prioritizes  →  /backlogd:scope shapes  →  /backlogd:solve executes
```

The retro is the **only** place backlogd reads *across* a scope of problems to adapt the
framework itself. It is the batch complement to `/backlogd:review` (one problem, in the
moment) and a reader of the same graph `/backlogd:status` reads for its forecast.

## Boundaries — what is **not** the retro's job

- **Prioritizing or working improvements.** The retro files candidates and stops. The PO
  prioritizes; the normal loop (`scope` → `solve`) works them. The retro never
  auto-fixes — that blows the propose/prioritize split, the batch-level twin of the
  reviewer's judge/act split.
- **Transitioning or editing existing problems.** The retro **adds** the improvement
  backlog; it does not touch the closed problems it read, does not re-open anything, and
  does not merge. Its only writes are the new candidate issues, the label, and the one
  summary comment.
- **Re-implementing the graph reducer.** It consumes `scripts/graph.py report --json`. If a
  metric the retro wants isn't in the reducer, that is a gap to fix in `scripts/graph.py`
  (a `kind:improvement` candidate in its own right), not a calculation to duplicate here.
- **Flooding the backlog.** Load-bearing only — a few candidates per milestone, each tied
  to repeated evidence. A micro-issue per observation is the failure mode.
- **Style or per-problem nitpicks.** The retro is about *systemic* patterns across the
  scope. A single problem's formatting note is a one-off — note it or drop it, don't file
  it.

## Pitfalls checklist

- ❌ Self-assessing ("the milestone felt rough") instead of reading the graph → reintroduces
  team-level self-marking. ✅ Read `report --json` first; cite the metric.
- ❌ Re-implementing `metrics()` in the retro → drifts from the source `/backlogd:status`
  reads. ✅ Consume `scripts/graph.py report --json`; never re-derive.
- ❌ Filing one improvement per observation → floods the `kind:improvement` queue, buries
  the signal. ✅ Load-bearing only; tie each to repeated evidence.
- ❌ A filed candidate with no cited evidence → indistinguishable from a hunch, untraceable.
  ✅ Every candidate cites the graph metric and/or the specific problems behind it.
- ❌ The retro working an improvement itself / auto-fixing → blows the propose/prioritize
  split. ✅ File the candidate; the PO prioritizes; the normal loop executes.
- ❌ Raising on an empty graph → a fresh checkout would crash the retro. ✅ `report --json`
  degrades to zeros; lean on Linear evidence and say so.
- ❌ Posting a new summary every run → noisy thread, broken history. ✅ One summary per
  scope, edited in place by the `retro:<scope>` marker — `list_comments({ milestoneId })`
  on the milestone path, `list_comments({ projectId })` on the no-milestone path (the
  `projectId` listing is verified live 2026-06-03, ADR-008).
