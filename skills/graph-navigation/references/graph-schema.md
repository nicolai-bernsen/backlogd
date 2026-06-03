# Graph schema — reference

What the nodes and edges *are*, and how they sit on disk. This is the concept reference behind
[`../SKILL.md`](../SKILL.md); read it when you're unsure what a node id or edge means. For the
runnable lookups, see [`graph-queries.md`](graph-queries.md).

## The model in two lines

> **Primary signal:** a **session** dispatches a **problem**, completes it (with an
> outcome and latency), opens a PR, finishes the run; later, a reviewer may mark the
> problem for rework.
>
> **Low-signal aside (legacy / read-only on new runs):** a **session** `touches` the
> **modules** (files) it changed.

Every edge is rooted at a session. Problems, files, and outcomes connect *through* the
session that worked on them.

## Nodes — the `kind:backend:native_id` convention

Every node is an opaque **string id** of the form `kind:backend:native_id`. The `backend`
segment is omitted for kinds that aren't owned by an external system.

| Kind | Id form | Example | Notes |
| --- | --- | --- | --- |
| **session** | `session:<session id>` | `session:nicolaibernsen/nb-320-...` | The session id is the git branch name (or any session label). 2-part — a session is local, not backend-owned. |
| **problem** | `problem:linear:<identifier>` | `problem:linear:NB-320` | The native id is the Linear issue identifier (`NB-N`). The graph references Linear by id only — never by copying Linear's data. |
| **module** | `module:<file path>` | `module:scripts/graph.py` | The native id is the repo-relative file path; backslashes normalised to `/`. 2-part — a file isn't backend-owned. Used by *legacy* `touches` edges only. |

**Always construct and compare ids via this convention** — don't hand-assemble them ad hoc.
The shipped helper (`scripts/graph.py`) exposes `session_node()`, `problem_node()`,
`module_node()`, and the generic `node_id(kind, backend, native_id)` so callers stay
consistent. To go the other way (id → display), strip the known prefix: `module:` → file
path, `problem:linear:` → `NB-N`.

## Edges — agent-execution (primary) + legacy

### Agent-execution edges — what only the loop knows

All point from a session to a problem. They capture the dimension Linear and git can't
compute on their own.

| Type | Carries | Recorded by |
| --- | --- | --- |
| **`dispatch_started`** | `ts` | `skills/solve/dispatch.md` — when the orchestrator hands the unit to a developer subagent. |
| **`dispatch_completed`** | `outcome` (`solved` / `partial` / `blocked`), `latency_ms` | `skills/solve/dispatch.md` — when the developer returns. `latency_ms` is derived from the matching `dispatch_started`. |
| **`pr_opened`** | `ts` | `skills/solve/handoff.md` — immediately after `gh pr create`. |
| **`run_completed`** | `wall_time_ms`, `fanout` (peak parallel-group size — 1 sequential, ≥2 parallel walk) | `skills/solve/handoff.md` — at end of handoff. Wall time is derived from the earliest `dispatch_started` for the same problem/session; `fanout` comes from the orchestrator's parallel-walk bookkeeping (`skills/solve/walk.md`). |
| **`rework`** | `notes_hash` (sha256 prefix; the note text itself is **never stored**) | `commands/review.md` — when the reviewer sends a problem back to *In Progress*. Each event uses a per-event session suffix so multiple events accumulate. |
| **`labeled`** | `labels` (list of Linear label names, e.g. `["area:graph", "problem"]`) | `skills/solve/dispatch.md` — optional; lets `graph.py report` aggregate blocker frequency by `area:*` without re-reading Linear. |

### Legacy edges — kept readable, no longer emitted on new runs

| Type | Direction | Meaning |
| --- | --- | --- |
| **`solves`** | session → problem | This session worked on / resolved this problem. **Superseded** by `dispatch_completed`. The `prior_work` query treats both as "solve evidence". |
| **`touches`** | session → module | This session changed this file. **Low-signal** — `git log` already provides this. New runs do **not** emit it; the `emit` CLI is retained for back-compat. |

## Edge object shape (`backlogd/v1`)

Each stored edge is a JSON object. Base fields:

```json
{
  "v": "backlogd/v1",
  "src": "session:demo",
  "tgt": "problem:linear:NB-320",
  "type": "dispatch_completed",
  "ts": "2026-05-28T10:05:00Z",
  "session": "demo"
}
```

- `v` — schema version (`backlogd/v1`).
- `src` / `tgt` — node ids (above).
- `type` — one of the edge types in the tables above.
- `ts` — ISO-8601 UTC emit time.
- `session` — the owning session id (also the `src`'s native part); part of the dedup key.

Some edge types carry **extra fields** beyond the base. They're added at the top level
(not nested) so old readers can ignore them and new readers see them directly:

| Field | On edge types | Type | Meaning |
| --- | --- | --- | --- |
| `outcome` | `dispatch_completed` | `"solved"` / `"partial"` / `"blocked"` | Developer's reported result. |
| `latency_ms` | `dispatch_completed` | integer | Wall time from `dispatch_started` to completion. |
| `wall_time_ms` | `run_completed` | integer | Total wall time from the earliest `dispatch_started` to the run end. |
| `fanout` | `run_completed` | integer ≥1 | Peak parallel-group size observed during the run. `1` for a sequential / single-unit run; `≥2` when the parallel walk fanned out (#321). |
| `notes_hash` | `rework` | string (12-char sha256 prefix) | Stable handle for the rework notes; **never** the notes themselves. |
| `labels` | `labeled` | list of strings | Linear label names attached to the problem at dispatch time. |

Unknown extras are passed through as-is — the schema is **additive**.

## On-disk store

- Location: **`.backlogd/graph/`**, relative to the repo being worked on (the consumer repo).
  Overridable with the `BACKLOGD_GRAPH_DIR` environment variable.
- One file per session: `<sanitised session id>.json`, where `/` and `\` in the session id
  become `__` (so a branch name is filesystem-safe). Each file is a JSON **array of edges**.
- **Append-only & deduplicated.** New edges are merged into the session file; duplicates
  collapse on the key **`(src, tgt, type, session)`**. Reading the whole graph unions every
  session file and de-dupes on the same key. Re-runs naturally overwrite the older edge for
  the same key (e.g. a retried dispatch updates its latency).
- **Rework events use a session suffix** (`<session>#rework-<ts>`) so multiple rework
  events on the same problem don't collapse into one.
- **Gitignored** (`.backlogd/`). The store is local memory, not committed source — so on a
  fresh checkout it's absent, and lookups simply return nothing.

## Why it's separate from Linear and git

Linear (via the official MCP) already owns work-item hierarchy, relations, comments, and PR
links — all readable on demand. Git owns file-authorship history. This graph stores only
what neither can compute: the **behaviour of the agent loop itself** (dispatch outcomes,
latencies, rework rate). A lookup returns Linear `NB-N` ids; resolve their titles/status in
Linear **separately** (see the `linear` skill). Keep the graph query itself offline.

## The solve ledger — a sibling store, not part of the graph

The graph is **session-keyed, edge-level telemetry** with an evolving internal schema,
optimised for metrics. Beside it lives a deliberately separate store (NB-426): the **solve
ledger** at `.backlogd/ledger.jsonl` (`scripts/ledger.py`) — a compact, **problem-keyed,
append-only durable run record** with a **stable read contract**. One JSONL line per
completed `/backlogd:solve` run names the problem, the units solved with their outcomes,
the PR reference, and the run timestamp.

It is **not** an edge type and **not** read by `metrics()` — it answers a different
question. The graph answers *"how is the loop behaving across sessions?"* (the metrics
source of truth); the ledger answers *"what did this problem's runs do?"* in one cheap
problem-first lookup, so resume can short-circuit and the retro can read local run history
without a Linear round-trip. To keep the two from silently disagreeing, the orchestrator
appends the ledger record at the **same lifecycle point** the graph records `run_completed`
(`skills/solve/handoff.md` §2). Both are gitignored under `.backlogd/` and absent on a
fresh checkout. Read the ledger with `python scripts/ledger.py read --problem {id}`.
