---
id: ADR-NNN
title: <short imperative title>
status: Proposed
date: <YYYY-MM-DD>
problem: NB-<n>
supersedes: ~        # ADR-NNN this one replaces, or ~ (none)
superseded-by: ~     # filled in when a later ADR replaces this one
assertion: <one crisp, checkable rule — the decision as an enforceable sentence, not prose rationale>
applies-to:
  domains: [<domain>, ...]            # e.g. auth, runtime, docs, linear — the area(s) this governs
  file-patterns: [<glob>, ...]        # e.g. scripts/**, docs/**, *.md — files a change touches to be in scope
  decision-types: [<type>, ...]       # e.g. dependency, runtime-loop, agent-identity — kinds of decision this gates
---

**ADR-NNN — <short imperative title>**

- **Status:** Proposed _(YYYY-MM-DD)_ · **Problem:** NB-N
- **Decision (TL;DR):** one sentence — the call, front-loaded, readable in isolation.

> Copy this file to `ADR-NNN-<slug>.md` (next free number — never reuse one), fill the
> front-matter + sections below, delete this guidance block. Shape:
> **Status · Context · Considered Options · Decision · Consequences**. ADRs are not rewritten
> once Accepted; to change a decision you **supersede** it with a new ADR.

## Front-matter keys

Every ADR opens with a `---`-fenced YAML block so an index can enumerate ADRs without
parsing prose. The front-matter `title` is the canonical document title — the body opens
with the same title as a **bold lead-in** (not an `#` heading, which would duplicate the
front-matter title), then the first `##` section. [NB-380](https://linear.app/nicolai-bernsen/issue/NB-380)
consumes the front-matter: `python scripts/standards_index.py` regenerates the compact
[`docs/standards/index.json`](../index.json) (id · title · assertion · applies-to · status)
from these keys, `--check` fails if any required key is missing, and
`scripts/test_standards_index.py` fails if the committed index has drifted from the corpus.
So **front-matter is the single source of truth** — edit it, then regenerate the index in
the same change (CI's drift test enforces it).

| Key | Required | Meaning |
| --- | --- | --- |
| `id` | yes | `ADR-NNN`, matching the filename and the bold title line. |
| `title` | yes | Short imperative title, matching the bold title line. |
| `status` | yes | Lifecycle value — see below. Keep in sync with the `## Status` section. |
| `date` | yes | Date of the current status (accepted / superseded), `YYYY-MM-DD`. |
| `assertion` | yes | One crisp, **checkable** rule — the decision stated as a single enforceable sentence (e.g. "No new runtime dependency lands without an ADR"), _not_ prose rationale. This is the line a reviewer reads first from the index. |
| `applies-to` | yes | Scope that decides whether this ADR is relevant to a given change. A mapping of three lists — `domains`, `file-patterns`, `decision-types` (see below). A reviewer filters the index by this before loading the full ADR. |
| `problem` | rec. | The `NB-<n>` problem this ADR came from. |
| `supersedes` | opt. | The `ADR-NNN` this one replaces, or `~`. |
| `superseded-by` | opt. | The `ADR-NNN` that later replaced this one, or `~`. |

### `applies-to` — the selective-loading scope

`applies-to` is what lets a reviewer load **only the relevant standards** into context
instead of the whole prose corpus. Each of its three lists is an axis a change can match on
— a standard is _applicable_ to a change if the change touches any listed domain, matches
any file-pattern, or is any listed decision-type. Use lower-case kebab tokens; keep them
small and reusable across ADRs so the vocabulary stays a usable filter.

| Sub-key | Meaning | Examples |
| --- | --- | --- |
| `domains` | The area(s) of the system this ADR governs. | `auth`, `runtime`, `docs`, `linear`, `agent-identity`, `dependencies` |
| `file-patterns` | Globs for files whose change brings this ADR into scope. | `scripts/**`, `docs/**`, `pyproject.toml`, `**/*.md` |
| `decision-types` | Kinds of decision this ADR gates. | `dependency`, `runtime-loop`, `agent-identity`, `secret-custody`, `hosting` |

An axis with no relevant entries may be an empty list (`[]`), but at least one of the three
must be non-empty — a standard that applies to nothing is dead weight.

## Status

State the current status here in one line, e.g. `Accepted (2026-05-29).` plus a sentence of
context, and keep it in sync with the `status:` front-matter key.

**Lifecycle.** ADRs are **agile, not permanent**: an Accepted ADR is a hard rule today, but
it can be reopened and superseded when technology or circumstances change — record the
decision, not dogma.

```text
Proposed  ──►  Accepted  ──►  Superseded by ADR-NNN
                   │
                   └────────►  Deprecated
```

| Status | Meaning |
| --- | --- |
| `Proposed` | Under discussion; not yet binding. |
| `Accepted` | Binding now. Do not edit the decision in place — supersede it instead. |
| `Superseded by ADR-NNN` | Replaced by a newer ADR; kept for history. Set `superseded-by`. |
| `Deprecated` | No longer in force and not replaced (the need went away). |

To supersede: write a **new** ADR with the next number, set its `supersedes:`, and flip the
old one's `status:` to `Superseded by ADR-NNN` + its `superseded-by:`. The old ADR's body
stays as written — superseding is additive history, not a rewrite.

## Context

What forces the decision — the problem, the constraints, the asks. State what is true today
and why a choice is needed now. (Add a **Verified finding** section here if the ADR rests on
a live probe or experiment; cite what was checked and that nothing was mutated.)

## Considered Options

The realistic options, compared on the axes that actually decide it. A table is preferred —
front-load the trade-off, then one short bullet per option for nuance the table can't hold.

| Option | Pro | Con | Fits the constraint? |
| --- | --- | --- | --- |
| **A** … | … | … | … |
| **B** … | … | … | … |

## Decision

The option chosen and **why** — tie it back to the constraint named in Context. State the
status explicitly here too: **Status: Accepted.**

## Consequences

What becomes true once this is in force: what it enables, what it forecloses, what follow-up
work it implies. List follow-ups as file-able problems if any. Be honest about the cost and
about what happens if the decision is later reversed.

---
_Refs: NB-N · related ADRs, principle docs, and any external sources or live probes._
