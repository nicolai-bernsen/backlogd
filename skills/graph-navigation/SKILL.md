---
name: graph-navigation
description: Query backlogd's local agent-execution + memory graph (.backlogd/graph/) — read-only. Records what only the loop knows (dispatch outcomes, latency, rework events) plus a low-signal aside of which files past problems touched. Use when a backlogd agent wants prior context before acting (problem-history / module-history / find-similar) or when a maintainer wants framework-effectiveness metrics (graph.py report). Local JSON only, no Linear/MCP — safe inside the developer's solve-only boundary. Pairs with references/graph-schema.md (nodes/edges/IDs) and references/graph-queries.md (copy-paste recipes).
---

# Navigating backlogd's memory graph

backlogd keeps a small **knowledge graph** of its own work. Its **primary signal** is the
*agent-execution* dimension — what only the scrum loop knows: when a unit was dispatched,
the recorded outcome (`solved` / `partial` / `blocked` — the coarse graph bucket the
orchestrator folds the developer's richer `STATUS` onto; see `skills/solve/capture.md`),
how long it took, when the PR opened, how long the whole run took, and how often a problem
was sent back for rework.
That's the data the maintainer asks framework-effectiveness questions of: *"where do we
rework, where do we block, how fast does the loop close?"*

Alongside the agent-execution edges, the graph also retains a small **low-signal aside**:
which **files** ("modules") past problems touched, so an agent can ask *"have we been here
before, and what did it touch?"* before acting. The file dimension duplicates `git log`
and is **no longer emitted on new runs**, but historical edges remain readable and
`prior_work` still surfaces them when present.

This skill is **read-only navigation**. It answers questions from the local store; it
never writes it. (Writing is the scrum-master's job — see `skills/solve/dispatch.md`,
`skills/solve/handoff.md`, and `commands/review.md` for the orchestrator hooks.)

> **Read this file first; reach for a reference when you act:**
>
> - **[`references/graph-schema.md`](references/graph-schema.md)** — what the nodes and edges
>   *are*: the `kind:backend:native_id` ID convention, every edge type, the on-disk store
>   layout, and the edge object shape. Read it when you're unsure what a node id or edge means.
> - **[`references/graph-queries.md`](references/graph-queries.md)** — the exact, copy-paste
>   query recipes (a tiny `load_edges()` loader + the lookups). **Copy from here when you
>   actually run a query.**

## What this graph is — and is not

- It owns the dimension **Linear and git can't compute**: the agent-execution metadata
  (dispatch outcomes, latency, rework) plus the residual session→file aside. It
  deliberately does **not** duplicate Linear's hierarchy/relations/comments/PRs, nor
  git's file-authorship history.
- It is **complementary to the `linear` skill**. When you need work-item facts (status,
  parent/child, blockers, comments) → use Linear via the MCP. When you need *"how often
  do we rework? how fast does the loop close?"* → run `graph.py report`. When you need
  *"what's been solved near this code?"* → use the lookups below.
- It is **local JSON, no network**. Reading it needs no Linear, no MCP, no API key — which is
  exactly why a `backlogd:developer` can use it **within its solve-only boundary**.
- It may be **empty or sparse** (early days, or a fresh checkout — the store is gitignored).
  Every lookup must tolerate "nothing found" and move on; never treat an empty graph as an
  error.

## When to use it

**Scrum-master (`/backlogd:solve`)** — *during the loop*:

- *Before dispatching* a developer, run **problem-history** / **find-similar** on the
  problem so you can fold a short "prior work" note into the developer's brief.
- The orchestrator hooks (`dispatch_started` / `dispatch_completed` / `pr_opened` /
  `run_completed` / `rework`) are wired in the skill prose; you don't query those — they
  feed `graph.py report`.

**Developer (`backlogd:developer`)** — *while solving, within the solve-only boundary*:

- About to edit a file? Run **module-history** to see which problems last touched it and why.
- Tackling something that feels familiar? Run **find-similar** to surface the closest past
  problems by shared touch-set, then read their Linear issues for context.

**Maintainer / product owner** — *measuring the framework*:

- `python scripts/graph.py report` prints a markdown table: rework rate, partial rate,
  p50/p90 dispatch→PR latency, blocker frequency by `area:*` label.

## The three lookups

All three read every session file under `.backlogd/graph/` and filter the edges. Full,
runnable versions (with the loader) live in
[`references/graph-queries.md`](references/graph-queries.md) — the sketches below show the
shape. Each treats both legacy `solves` edges and new `dispatch_completed` edges as
evidence that a session worked on a problem.

### 1. problem-history — *which files did a problem touch?* (low-signal aside)

Sessions that solved the problem → the modules those sessions `touches`.

```python
problem = "problem:linear:NB-241"
solve_like = {"solves", "dispatch_completed"}
sessions = {e["src"] for e in edges if e["type"] in solve_like and e["tgt"] == problem}
files    = sorted({e["tgt"] for e in edges if e["type"] == "touches" and e["src"] in sessions})
```

### 2. module-history — *which problems touched a file?* (low-signal aside)

Sessions that `touches` the file → the problems those sessions solved.

```python
module   = "module:scripts/graph.py"
solve_like = {"solves", "dispatch_completed"}
sessions = {e["src"] for e in edges if e["type"] == "touches" and e["tgt"] == module}
problems = sorted({e["tgt"] for e in edges if e["type"] in solve_like and e["src"] in sessions})
```

### 3. find-similar — *which past problems share a touch-set with this one?* (low-signal aside)

Build each problem's touch-set (the union of files its sessions touched), then rank
other problems by overlap with the target's set (shared count / Jaccard). See the
reference for the full ranking recipe.

> **Note.** The three lookups above rely on `touches` edges, which are no longer emitted
> on new runs. They keep working against historical data; on a fresh graph they'll return
> nothing. The **primary signal** of the graph is now the agent-execution edges — query
> them via `graph.py report` or the recipes in `references/graph-queries.md`.

## Boundaries — read before you query

- **Read-only, always.** This skill never writes `.backlogd/graph/`. If you think an edge is
  missing, that's a gap in the orchestrator's emission step (see `skills/solve/`), not
  something to patch here.
- **Local only.** No Linear, no MCP, no network. Resolve work-item details (titles, status)
  by taking the `NB-N` a lookup returns and reading it in Linear *separately* — keep the graph
  query itself offline.
- **Best-effort.** A missing/empty store, or a malformed session file, yields fewer results —
  never an exception. Degrade quietly.
- **IDs are opaque strings.** Always build/compare node ids via the documented convention
  (`problem:linear:NB-N`, `module:<path>`, `session:<id>`) — see `references/graph-schema.md`.
