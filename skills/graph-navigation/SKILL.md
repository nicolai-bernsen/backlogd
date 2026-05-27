---
name: graph-navigation
description: Query backlogd's local code<->Linear memory graph (.backlogd/graph/) — read-only. Use when a backlogd agent wants prior context before acting: which files a problem touched (problem-history), which problems touched a file (module-history), or which past problems share a touch-set with the current one (find-similar). Local JSON only, no Linear/MCP — safe inside the developer's solve-only boundary. Pairs with references/graph-schema.md (nodes/edges/IDs) and references/graph-queries.md (copy-paste recipes).
---

# Navigating backlogd's memory graph

backlogd keeps a small **knowledge graph** of its own work: which **sessions** solved which
**problems**, and which **files** ("modules") those sessions touched. It is the institutional
memory the agent team uses to avoid blind re-solves — *"have we been here before, and what
did it touch?"*

This skill is **read-only navigation**. It answers questions from the local store; it never
writes it. (Writing — emitting `solves`/`touches` edges at report-time — is the
scrum-master's job, wired separately.)

> **Read this file first; reach for a reference when you act:**
>
> - **[`references/graph-schema.md`](references/graph-schema.md)** — what the nodes and edges
>   *are*: the `kind:backend:native_id` ID convention, the two edge types, the on-disk store
>   layout, and the edge object shape. Read it when you're unsure what a node id or edge means.
> - **[`references/graph-queries.md`](references/graph-queries.md)** — the exact, copy-paste
>   query recipes (a tiny `load_edges()` loader + the three lookups). **Copy from here when you
>   actually run a query.**

## What this graph is — and is not

- It owns the dimension **Linear can't see**: the link between *agent sessions*, the
  *problems* they solved, and the *files* they changed. It deliberately does **not** duplicate
  Linear's hierarchy/relations/comments/PRs.
- It is **complementary to the `linear` skill**. When you need work-item facts (status,
  parent/child, blockers, comments) → use Linear via the MCP. When you need *"who touched what,
  and what's been solved near this code"* → use this graph.
- It is **local JSON, no network**. Reading it needs no Linear, no MCP, no API key — which is
  exactly why a `backlogd:developer` can use it **within its solve-only boundary**.
- It may be **empty or sparse** (early days, or a fresh checkout — the store is gitignored).
  Every lookup must tolerate "nothing found" and move on; never treat an empty graph as an
  error.

## When to use it

**Scrum-master (`/backlogd:pull`)** — *before dispatching a developer*:
- Run **problem-history** / **find-similar** on the problem you're about to hand off, so you
  can fold a short "prior work" note into the developer's brief (which files prior solves
  touched, which past problems are nearby).

**Developer (`backlogd:developer`)** — *while solving, within the solve-only boundary*:
- About to edit a file? Run **module-history** to see which problems last touched it and why.
- Tackling something that feels familiar? Run **find-similar** to surface the closest past
  problems by shared touch-set, then read their Linear issues for context.

## The three lookups

All three read every session file under `.backlogd/graph/` and filter the edges. Full,
runnable versions (with the loader) live in
[`references/graph-queries.md`](references/graph-queries.md) — the sketches below show the
shape.

### 1. problem-history — *which files did a problem touch?*

Sessions that `solves` the problem → the modules those sessions `touches`.

```python
problem = "problem:linear:NB-241"
sessions = {e["src"] for e in edges if e["type"] == "solves" and e["tgt"] == problem}
files    = sorted({e["tgt"] for e in edges if e["type"] == "touches" and e["src"] in sessions})
```

### 2. module-history — *which problems touched a file?*

Sessions that `touches` the file → the problems those sessions `solves`.

```python
module   = "module:scripts/graph.py"
sessions = {e["src"] for e in edges if e["type"] == "touches" and e["tgt"] == module}
problems = sorted({e["tgt"] for e in edges if e["type"] == "solves" and e["src"] in sessions})
```

### 3. find-similar — *which past problems share a touch-set with this one?*

Build each problem's touch-set (the union of files its solving sessions touched), then rank
other problems by overlap with the target's set (shared count / Jaccard). See the reference
for the full ranking recipe.

## Boundaries — read before you query

- **Read-only, always.** This skill never writes `.backlogd/graph/`. If you think an edge is
  missing, that's a gap in emission (the scrum-master's report-time job), not something to
  patch here.
- **Local only.** No Linear, no MCP, no network. Resolve work-item details (titles, status)
  by taking the `NB-N` a lookup returns and reading it in Linear *separately* — keep the graph
  query itself offline.
- **Best-effort.** A missing/empty store, or a malformed session file, yields fewer results —
  never an exception. Degrade quietly.
- **IDs are opaque strings.** Always build/compare node ids via the documented convention
  (`problem:linear:NB-N`, `module:<path>`, `session:<id>`) — see `references/graph-schema.md`.
