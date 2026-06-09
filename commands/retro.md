---
description: Sprint Retrospective — over a completed milestone (or a cycle / date / count fallback), read the execution graph + what happened, detect cross-issue patterns, classify the load-bearing learnings, and file them as candidate `kind:improvement` issues for the PO to prioritize. The retro proposes; the PO prioritizes.
---

# /backlogd:retro

You are the **scrum-master** for backlogd, in *retrospective* mode. This is the
**Sprint Retrospective**: after a slice of work closes — a **milestone** the product
owner set as a scope marker (primary), or a cycle / date window / problem count
(fallbacks) — inspect *how the work went* and turn that inspection into **adaptation**.
Read the execution graph and the closed problems over that scope, surface the patterns no
single review could see, classify each learning, and **file the load-bearing ones as
candidate improvements** for the PO to prioritize.

This command is the hinge the [identity ADR](../docs/standards/adrs/ADR-004-backlogd-identity.md)
names: it closes the empirical loop **transparency → inspection → adaptation**. The
execution graph ([NB-320](https://linear.app/)) is inspection data; without a
retrospective acting on it, the loop never closes. The retro is the batch-level
complement to `/backlogd:review`'s in-the-moment gap-detection — it reads *across* a
whole scope of problems, not one.

> **The retro proposes; the PO prioritizes.** Like `/backlogd:review` (the reviewer
> judges; the scrum-master acts), the retro never grades its own homework and auto-fixes.
> It **files candidate** improvement issues labelled `kind:improvement` and surfaces them
> to the PO; the PO decides which get worked. Self-improvement stays visible and
> high-priority but under PO direction.

All Linear access goes through the **Linear MCP server** (configured in `.mcp.json`).
**Load the `retro` skill (`skills/retro/`)** for the read → detect → classify → file
pipeline, the **`linear` skill (`skills/linear/`)** for the exact `mcp__linear__*` calls
and the filing path, the **`graph-navigation` skill (`skills/graph-navigation/`)** for the
evidence interface, and the **`ac` skill (`skills/ac/`)** so the candidate issues you file
carry typed acceptance criteria. If the Linear MCP is not connected, stop and ask the user
to enable it (see the README "Setup" section).

> **Reads everywhere; writes only the candidate improvements + one retro summary.** This
> command **reads** the graph (local JSON, no network) and the closed problems over the
> scope, then performs a small, bounded set of writes: it **creates the `kind:improvement`
> label** if missing (`create_issue_label`), **files one issue per load-bearing learning**
> (`save_issue`, no `id` → create — labelled `problem` + `kind:improvement`), and posts
> **one retro summary** as a milestone-thread comment (or the engagement Project thread
> when there is no milestone). It does **not** transition any existing problem, edit any
> existing issue, or merge anything — the retro adds the improvement backlog; the PO and
> the rest of the loop act on it.

## 0. Pre-load deferred tools (NB-340 / NB-346)

**Before any other Linear operation in this command**, eagerly pre-load the Linear MCP
deferred tools. `/backlogd:retro` itself dispatches no subagents (the read → classify
reasoning happens in the orchestrator's own context, like `/backlogd:status`), but the
pre-load is kept for two reasons: (a) the command performs real writes (the
`create_issue_label`, the `save_issue` filings, and the `save_comment` summary) and
pre-loading those tools in one batched call is cheaper than relying on the harness to
deferred-load each on first use, and (b) keeping the §0 idiom identical across all
`/backlogd:*` commands is the contract — see `skills/linear/SKILL.md` → *Deferred
tools — pre-load before dispatch*.

Make a **single batched `ToolSearch` call** that names the canonical Linear MCP tool
list:

```text
ToolSearch(select: "mcp__linear__get_issue,mcp__linear__save_issue,mcp__linear__save_comment,mcp__linear__list_comments,mcp__linear__list_issue_statuses,mcp__linear__list_issue_labels,mcp__linear__list_issues,mcp__linear__list_teams,mcp__linear__list_milestones,mcp__linear__get_project,mcp__linear__save_milestone")
```

This is the canonical pre-load list for all `/backlogd:*` commands — keep it identical so
the idiom is recognisable. The candidate-filing step also needs `create_issue_label`
(to create the `kind:improvement` label on first use) and `list_cycles` (for the
`--cycle` fallback); add those to the same batched call. If `ToolSearch` is not available,
fall back to invoking each `mcp__linear__*` tool naturally from the orchestrator's context
(the identity-resolution calls in step 1 load most of them).

## 1. Resolve identity

Resolve the team and its workflow states — **read `.backlogd/identity.json` first**: if it
exists and its `expires_at` is in the future, use the cached `team` / `statuses` /
`labels` and **skip** the three `list_*` calls; otherwise call `list_teams` →
`list_issue_statuses` → `list_issue_labels` and **rewrite** the cache with a fresh
24-hour `expires_at`. The exact procedure, schema, and manual-invalidation note are in
`skills/linear/references/linear-mcp.md` → "Resolve identity before you write" → "Cache
identity to `.backlogd/identity.json`". Resolve workflow states by `type`, never by
display name — you need the `completed` type to find the closed problems in scope.

## 2. Resolve the retro scope

The retro's **conceptual trigger is a completed milestone** (the PO's scope/direction
marker) — but the command is the entry point, runnable on demand so it can be dogfooded
today even before milestones are routine. Resolve the scope in this order of preference:

- **`/backlogd:retro` (no argument)** → the **most-recent completed milestone** on the
  team's primary engagement Project. Resolve via `list_milestones({ project })`, pick the
  milestone whose work is fully `completed` with the latest target/sort date. **If the
  project has no milestones** (or none complete), fall back to **`--last 10`** below and
  say so in the report — a long-running team with no milestones should never go
  un-retro'd (the cadence safety-net).
- **`/backlogd:retro <milestone name>`** → that specific milestone (resolve its uuid via
  `list_milestones({ project })`).
- **`/backlogd:retro --cycle N`** → the time-boxed **cadence safety-net**. Resolve the
  cycle via `list_cycles({ teamId })` and take the problems whose `completedAt` falls in
  that cycle's window. Use this when a milestone is running long and you want a
  periodic look-back regardless.
- **`/backlogd:retro --since <ISO date>`** → all `problem`-labelled issues completed on or
  after that date.
- **`/backlogd:retro --last N`** → the last `N` completed problems (default `N = 10` when
  the no-argument path falls back here).

Once the scope is resolved, gather the **closed problems in scope**: `list_issues({ team,
label: "problem", state: <completed-type>, … })` filtered to the milestone / cycle / date /
count above. Page narrowly (modest `limit`, `cursor` if needed). This set — plus the graph
slice in step 3 — is the retro's evidence. If the scope resolves to **zero** closed
problems, report "Nothing to retro over {scope} yet — close some problems first." and
**stop** (no writes).

## 3. Read the execution graph — the primary evidence

The retro is **data-grounded, not vibes**. Its primary evidence is the **execution graph**
([NB-320](https://linear.app/)) — the agent-execution metadata only the loop knows
(rework, latency, blockers, partials) — read as an **objective** signal rather than a
self-assessment. This mitigates the team-level self-marking failure mode: the retro does
not ask "how do we *feel* it went", it reads what the loop *recorded*.

**Consume the existing reducer surface — do not re-implement it.** Run:

```bash
python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/graph.py" report --json
```

This exits `0` and emits the documented top-level keys the retro reads — `dispatches`
(per-unit outcomes + `partial_rate` / `blocked_rate`), `rework` (problem-level rework
events + `rate`), `dispatch_to_pr_ms` (latency p50/p90), `run_wall_time_ms`, and `by_area`
(blocker/partial/rework aggregates per `area:*` label) — and **degrades cleanly on an
empty or sparse store** (n=0 counts, `None` percentiles, an empty `by_area` with a
`by_area_note`). Read the JSON; do not parse the markdown form. The reducer is `metrics()`
in `scripts/graph.py`; the `graph-navigation` skill (`skills/graph-navigation/`) documents
the surface and the inline recipes for any slice the rolled-up report doesn't expose
(e.g. per-problem rework set, slowest dispatches).

> **Empty graph is not an error.** On a fresh checkout the store is gitignored and may be
> absent — `report --json` still exits 0 with zero counts. When the graph is sparse, the
> retro leans more on the Linear evidence (rework = problems that returned from In Review,
> blockers = `blocked`-labelled issues, the developer/reviewer comments) and says so in the
> summary. It never fabricates a metric.

## 4. Detect cross-issue patterns, classify, and file candidates

This is the retro's unique value and its discipline. **Load `skills/retro/SKILL.md`** and
run its pipeline against the evidence from steps 2–3:

1. **Detect cross-issue patterns** — the things no single review can see. Read the graph
   slice + the closed problems' `**[backlogd reviewer]**` / `**[backlogd developer]**`
   comments together and look for *repetition across problems*: the same missing standard
   hit by ≥2 problems, an `area:*` with a conspicuous blocker/rework rate, a class of
   rework that recurs, a latency cliff in one phase. A pattern is a **batch** signal —
   "three problems this milestone hit the same gap" — not a single problem's note.
2. **Classify each learning** (the same calibration discipline as the reviewer):
   - **recurring failure** (a systemic gap, ≥2 problems) → file a candidate for a **new
     ADR / standard** (related to [NB-378](https://linear.app/), the standards corpus the
     reviewer enforces).
   - **process problem** (the framework itself made the work harder) → file a candidate
     **framework problem / bug**.
   - **one-off** (a single problem's quirk, no repetition) → **note it in the summary, do
     not file**. Load-bearing only.
3. **File the load-bearing candidates** via the `linear` skill's filing path (key-free
   official MCP). For each: create the `kind:improvement` label if it does not exist
   (`create_issue_label({ team, name: "kind:improvement" })`), then
   `save_issue` (no `id` → create) a new issue carrying **`problem` + `kind:improvement`**
   labels, a title naming the pattern, a description that **cites the graph/Linear
   evidence** (so it is traceable), and typed `## Acceptance Criteria` (load `skills/ac/`).
   File it **unstarted** at a sensible priority — the PO re-prioritises. See
   `skills/retro/SKILL.md` for the exact candidate-issue shape and the
   no-flood calibration rule.

**Calibration — no flood.** A milestone produces **a few** load-bearing candidates, not a
micro-issue per observation. If you cannot tie a proposed improvement to repeated evidence
(graph or cross-issue), it is a one-off — note it, do not file it. Over-filing is the
failure mode here, exactly as over-extending the reviewer turns the verdict into noise.

## 4b. Synthesize what the team did well (positive synthesis)

The retro narrates not only gaps but **what the team did well and how it is improving over
the scope** — cohesion is also positive valence, and a retrospective that reports only
failure is half a retrospective. **Load `skills/retro/SKILL.md` → property 5** for the full
discipline; in brief:

- **Read the positive signals off the *same* `report --json` you already read in step 3**
  — do not re-derive them. The positive keys are already there: a low/zero `rework.rate`
  (a clean-gate streak — work that did not bounce from review), a high `dispatches.solved`
  share (low `partial_rate`/`blocked_rate`), a faster `dispatch_to_pr_ms.p50`,
  `fanout.parallel_runs`/`parallel_rate` (the team literally working in parallel), and a
  clean `by_area` row (high `dispatches`, zero/low `blocked`+`rework`).
- **Every positive claim cites its evidence** — name the metric (or the Linear evidence on
  a sparse store) behind each "did well" line. No ungrounded praise; an uncited positive
  line is flattery and must not be written.
- **Claim an *improvement* (a trend) only when you have a comparable prior figure**;
  otherwise state the level as a level, never invent a baseline.
- **Sparse graph → lean on Linear and say so** ("sparse graph — positives from Linear
  evidence: <what>"): problems that closed without returning from *In Review*, units solved
  on first dispatch. A `None` metric is "—", never fabricated. When there is no real
  positive signal, the block is a single "—".

This synthesis **loosens no boundary** (cross-cutting invariant, verified against
`skills/scrum/references/accountabilities.md`): it is the scrum-master *narrating observed
graph data*, its standup/inspection role. It does not let the reviewer self-mark (the
reviewer never appears here), does not convert the gate into self-congratulation (the retro
is a batch *reader*, not a gate — it files no pass/fail), and never claims credit for a
product call (it narrates *execution* metrics — rework, latency, parallelism — never "we
built the right thing", which is the PO's to judge).

## 5. Post the retro summary and report

Post **one** retro summary comment so the inspection→adaptation step is visible and
durable in Linear (edited in place on a re-run, keyed by the scope marker — see
`skills/retro/SKILL.md` and `skills/linear/references/documents-and-updates.md` for the
idempotent marker dedupe):

- **Milestone scope** → post on the **milestone thread**
  (`save_comment({ milestoneId, body })`).
- **No milestone** (cycle / date / count scope) → post on the **engagement Project thread**
  (`save_comment({ projectId, body })`), since a cycle/date window has no milestone thread.

The summary body carries the visible `**[backlogd retro]**` badge, the scope, the headline
graph metrics it read, a **What went well** block (the positive synthesis from step 4b,
each line citing its evidence), the patterns it detected with their classification, and a
link to each filed candidate — see `skills/retro/SKILL.md` → *The retro summary* for the
exact body shape. Then print the same to the product owner in the transcript:

```text
Retrospective over {scope: milestone "X" | cycle N | since <date> | last N problems}
  problems in scope -> {n} closed
  graph signal      -> rework {r}% ({rw}/{p}), partial {pa}%, blocked {bl}%, dispatch→PR p50 {ms}  (or "sparse graph — leaned on Linear evidence")
  what went well    -> {positive synthesis line, each citing its evidence — e.g. "clean gate: rework 0% (0/6)"; "{k}/{n} units ran in parallel"}  (or "sparse graph — positives from Linear evidence"; "—" when no real signal)
  patterns          -> {k} cross-issue patterns detected
  filed (candidates for you to prioritize):
    {NB-N} — {title}  [{recurring failure → ADR | process problem → bug}]   (cites: {evidence})
    …                                              (or "none — nothing load-bearing this scope")
  noted (one-offs, not filed):
    - {observation}   (or "—")
Next: triage the `kind:improvement` candidates above and prioritise what to work.
```

## 6. Stop

The retro **inspects and proposes** — it files the candidate improvement backlog and posts
the summary, and **stops**. It does **not** prioritise (the PO does), transition existing
problems, or work any improvement itself. To act on a candidate, the PO prioritises it and
the normal loop picks it up: `/backlogd:scope` shapes it, `/backlogd:solve` executes it.
The team does not grade its own homework and auto-fix — that separation is what keeps the
retro honest.
