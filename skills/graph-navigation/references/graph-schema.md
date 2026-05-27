# Graph schema — reference

What the nodes and edges *are*, and how they sit on disk. This is the concept reference behind
[`../SKILL.md`](../SKILL.md); read it when you're unsure what a node id or edge means. For the
runnable lookups, see [`graph-queries.md`](graph-queries.md).

## The model in one line

> A **session** `solves` a **problem**, and a **session** `touches` the **modules** (files) it
> changed.

That's the whole graph. Everything a lookup does is: pivot through sessions to connect problems
and files.

## Nodes — the `kind:backend:native_id` convention

Every node is an opaque **string id** of the form `kind:backend:native_id`. The `backend`
segment is omitted for kinds that aren't owned by an external system.

| Kind | Id form | Example | Notes |
|---|---|---|---|
| **session** | `session:<session id>` | `session:nicolaibernsen/nb-264-graph-core-…` | The session id is the git branch name (or any session label). 2-part — a session is local, not backend-owned. |
| **problem** | `problem:linear:<identifier>` | `problem:linear:NB-264` | The native id is the Linear issue identifier (`NB-N`). This is the one place the graph references Linear — by id only, never by copying Linear's data. |
| **module** | `module:<file path>` | `module:scripts/graph.py` | The native id is the repo-relative file path; backslashes are normalised to `/`. 2-part — a file isn't backend-owned. |

**Always construct and compare ids via this convention** — don't hand-assemble them ad hoc.
The shipped helper (`scripts/graph.py`) exposes `session_node()`, `problem_node()`,
`module_node()`, and the generic `node_id(kind, backend, native_id)` so callers stay
consistent. To go the other way (id → display), strip the known prefix: `module:` →
file path, `problem:linear:` → `NB-N`.

## Edges — two types, both rooted at a session

| Type | Direction | Meaning |
|---|---|---|
| **`solves`** | session → problem | This session worked on / resolved this problem. |
| **`touches`** | session → module | This session changed this file. |

Both edges start at a `session` node. Problems and files are **never linked directly** — they
connect only *through* the session that worked on both. That's why every lookup pivots through
sessions (see the recipes).

## Edge object shape (`backlogd/v1`)

Each stored edge is a JSON object:

```json
{
  "v": "backlogd/v1",
  "src": "session:nicolaibernsen/nb-264-graph-core-stdlib-emit-helper-json-store",
  "tgt": "problem:linear:NB-264",
  "type": "solves",
  "ts": "2026-05-27T15:10:00Z",
  "session": "nicolaibernsen/nb-264-graph-core-stdlib-emit-helper-json-store"
}
```

- `v` — schema version (`backlogd/v1`).
- `src` / `tgt` — node ids (above).
- `type` — `solves` or `touches`.
- `ts` — ISO-8601 UTC emit time.
- `session` — the owning session id (also the `src`'s native part); part of the dedup key.

## On-disk store

- Location: **`.backlogd/graph/`**, relative to the repo being worked on (the consumer repo).
  Overridable with the `BACKLOGD_GRAPH_DIR` environment variable.
- One file per session: `<sanitised session id>.json`, where `/` and `\` in the session id
  become `__` (so a branch name is filesystem-safe). Each file is a JSON **array of edges**.
- **Append-only & deduplicated.** New edges are merged into the session file; duplicates
  collapse on the key **`(src, tgt, type, session)`**. Reading the whole graph unions every
  session file and de-dupes on the same key.
- **Gitignored** (`.backlogd/`). The store is local memory, not committed source — so on a
  fresh checkout it's absent, and lookups simply return nothing.

## Why it's separate from Linear

Linear (via the official MCP) already owns work-item hierarchy, relations, comments, and PR
links — all readable on demand. This graph stores only what Linear *can't* see: the
session→file dimension. A lookup returns Linear `NB-N` ids; resolve their titles/status in
Linear **separately** (see the `linear` skill). Keep the graph query itself offline.
