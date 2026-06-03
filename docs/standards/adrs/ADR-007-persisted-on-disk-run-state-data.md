---
id: ADR-007
title: Persisted on-disk run/state data — gitignored .backlogd/, append-only NDJSON, grow-only versioned schema
status: Accepted
date: 2026-06-03
problem: NB-427
supersedes: ~
superseded-by: ~
assertion: Persisted on-disk run/state data lives under the gitignored `.backlogd/` directory as append-only newline-delimited JSON (one record per line), each record carrying a schema `version` field; readers tolerate unknown fields and the schema only ever grows (no field is removed or repurposed in place); `.backlogd/` content is never committed.
applies-to:
  domains: [persistence, runtime, storage]
  file-patterns: ["scripts/**", ".backlogd/**", ".gitignore"]
  decision-types: [data-format, schema-evolution, persistence, storage-location]
---

**ADR-007 — Persisted on-disk run/state data: gitignored `.backlogd/`, append-only NDJSON, grow-only versioned schema**

- **Status:** Accepted _(2026-06-03)_ · **Problem:** NB-427
- **Decision (TL;DR):** any persisted on-disk run/state store lives under the **gitignored
  `.backlogd/`** as **append-only newline-delimited JSON** (one record per line), each record
  carrying a schema **`version`** field; **readers tolerate unknown fields**, the schema is
  **grow-only** (never remove or repurpose a field in place), and **`.backlogd/` content is
  never committed**.

> The governance rule for persisted run/state data — the missing standard the NB-426 verdict
> flagged. Shape per the [TEMPLATE](TEMPLATE.md): **Status · Context · Considered Options ·
> Decision · Consequences**. ADRs are immutable once Accepted — supersede, don't rewrite.

## Status

**Accepted** (2026-06-03). This is a **governance** ADR — it ships **no code** (only this ADR
and the regenerated [standards index](../index.json)). It codifies the format/location/schema
rule the [solve ledger](../../../scripts/ledger.py) (NB-426) already follows by a per-issue PO
ruling, so the **next** persisted-store decision has a standard to follow instead of a fresh
ruling. It defers to [ADR-002](ADR-002-keyless-mcp.md) on _secret custody / hosting_ — ADR-002
governs whether a store may hold a secret or run a server; this ADR governs only the _shape_ of
the data once a keyless store exists.

## Context

backlogd now persists **two** on-disk run/state stores, both under the gitignored
`.backlogd/`, and **no Accepted standard governs their format, location, or schema evolution**:

- **Execution graph** — [`scripts/graph.py`](../../../scripts/graph.py) (NB-320):
  `.backlogd/graph/`, **one JSON file per session, each a JSON array** of edge objects
  rewritten whole per session, versioned `backlogd/v1`. Session-keyed edge telemetry.
- **Solve ledger** — [`scripts/ledger.py`](../../../scripts/ledger.py) (NB-426, PR #133,
  merged `d5736fe`): `.backlogd/ledger.jsonl`, **append-only JSONL one record per line**,
  versioned `backlogd-ledger/v1`, readers preserve unknown fields. Problem-keyed durable run
  record.

The [NB-426 verdict](https://linear.app/nicolai-bernsen/issue/NB-426) named the gap from the
other side: the ledger's append-only-JSONL format was settled by a **per-issue PO ruling**, not
a cross-issue rule — so the next store has nothing to follow. That is a durable, cross-issue
governance gap of exactly the kind an ADR closes. The PO has since **ruled the standard**
(2026-06-03, recorded on NB-427); this ADR records it so the reviewer's index-first walk catches
future persisted-store decisions.

## Considered Options

The axis that decides it is the **on-disk format + schema-evolution contract** (location is
already settled — `.backlogd/`, gitignored). Append-only NDJSON is what the ledger already
proved; the alternatives are the realistic ways a future store could diverge.

| Option | Format | Append-only? | Schema evolution | Reader-tolerant? | Fits the constraint? |
| --- | --- | --- | --- | --- | --- |
| **A — Append-only NDJSON, per-record `version`, grow-only** (chosen) | one JSON object per line | ✅ yes — a write is one append, can't truncate prior records | grow-only, versioned | ✅ unknown fields tolerated | ✅ keyless, local, durable, diff-friendly |
| **B — Whole-array JSON rewritten per write** (graph today) | one JSON array per file | ❌ no — rewrites the file each time | versioned, ad hoc | ~ depends on reader | ~ fine for dedup/metrics, but a write can truncate; not the durable-record default |
| **C — Embedded DB / external store** (SQLite, a server) | binary / networked | n/a | migrations | n/a | ❌ breaks zero-dep + ADR-002 keyless/no-server |

- **A** — the ledger's proven shape. One append per record means a later write **cannot**
  truncate or rewrite earlier records (durability by construction); a per-record `version` lets
  a reader branch on schema; unknown-field tolerance + grow-only means old readers survive new
  writers and the format never needs a destructive migration.
- **B** — the graph's shape, and legitimate for its dedup semantics (re-emitting an edge
  overwrites the older one by `(src,tgt,type,session)`), but a whole-file rewrite is not
  append-only, so it is **not** the default for a new durable store. The graph is grandfathered
  (Decision), not blessed as the pattern to copy.
- **C** — an embedded DB or a server is the natural "grown-up" answer, and it is **out of scope
  by standard**: it breaks the repo's zero-third-party-dep `scripts/` rule and (for a server)
  [ADR-002](ADR-002-keyless-mcp.md). A store that needs it supersedes this ADR (and likely
  ADR-002) first.

## Decision

**Adopt Option A. Status: Accepted.** Persisted on-disk run/state data:

1. **Location — gitignored `.backlogd/`.** Every store lives under `.backlogd/` (already
   gitignored). **`.backlogd/` content is never committed** — it is local runtime data, not
   source.
2. **Format — append-only NDJSON, one record per line.** Recording a record is a **single
   append of one line**, which by construction cannot truncate or rewrite the records already on
   disk. (One JSON object per line; the file is read line-by-line, malformed lines skipped.)
3. **Versioned records.** Every record carries a schema **`version`** field (the ledger's `v:`
   `backlogd-ledger/v1` satisfies this — the key may be `v` or `version`, the requirement is a
   per-record schema stamp a reader can branch on).
4. **Grow-only schema, reader-tolerant.** **Readers tolerate unknown fields**, and the schema
   **only ever grows** — no field is removed or repurposed in place. A new writer adds fields; an
   old reader ignores what it doesn't know. A change that would break this is a **new schema
   version**, not an in-place edit.

Tie-back to the constraint named in Context: Option A is the **single** shape that is durable
(append-only ⇒ no truncation), forward/backward-compatible (versioned + grow-only + tolerant ⇒
no destructive migration), and keyless/zero-dep (plain text files, no DB, no server) — so the
_next_ persisted store has one rule to follow instead of re-litigating format per issue.

### The two existing stores — stated honestly

The standard binds **new and next-touched** stores; it is **not** a retroactive migration mandate.

- **Ledger — conforms.** [`scripts/ledger.py`](../../../scripts/ledger.py) is already
  append-only JSONL at `.backlogd/ledger.jsonl`, one record per line, each carrying a `v` schema
  field, readers preserving unknown fields. It **is** the reference implementation of this rule.
- **Graph — grandfathered until its next schema change.** [`scripts/graph.py`](../../../scripts/graph.py)
  predates the rule: it is a session-keyed **JSON array per file, rewritten whole** per session
  (not append-only NDJSON). It is **grandfathered** — it keeps working as-is, and **no
  retroactive migration is mandated**. The rule binds it only **when its schema next changes**;
  at that point the change is made to conform (or the divergence is recorded against this ADR).

## Consequences

What becomes true once this is in force (it adds a rule; it changes no code):

- **The next persisted store has a standard, not a fresh PO ruling.** A new run/state store is
  reviewed against this ADR's assertion (the reviewer's index-first walk now matches the
  `persistence` / `storage` domains and the `data-format` / `schema-evolution` decision-types).
- **Durability + compatibility are the default, not a per-store decision.** Append-only ⇒ a
  write can't corrupt history; versioned + grow-only + reader-tolerant ⇒ schema changes never
  need a destructive migration and old readers survive new writers.
- **The graph is honestly grandfathered**, not silently non-compliant — the divergence is named
  and bounded to "until its next schema change", so the index reflects the rule without
  pretending a migration happened.
- **Forecloses** an embedded DB or a server-backed store as the _default_ — that path is out of
  scope by standard and would require superseding this ADR (and, for a server, ADR-002).

**Follow-ups** (each a file-able problem — **none started by this ADR**):

1. **On the graph's next schema change**, conform it to append-only NDJSON (or record the
   reasoned divergence against this ADR). Not mandated now.
2. **Optional convergence helper** — a tiny shared read/write helper for `.backlogd/` NDJSON
   stores, if a third store appears. Deferred; the ledger + graph each having their own small
   module is fine at N=2.

If reversed (a future ADR supersedes this): a store could adopt a different format (e.g. an
embedded DB), which would also revisit the zero-dep and possibly the ADR-002 constraints. Until
then, this is the persisted-data standard of record.

---
_Refs: NB-427 · the ruled stores: [`scripts/ledger.py`](../../../scripts/ledger.py) (NB-426, PR #133 / `d5736fe` — conforms) + [`scripts/graph.py`](../../../scripts/graph.py) (NB-320 — grandfathered) · adjacency: [ADR-002](ADR-002-keyless-mcp.md) (keyless / no-server governs secret custody + hosting, NOT data shape — NOT superseded) · gap source: the NB-426 reviewer verdict + the NB-427 PO ruling (2026-06-03)._
