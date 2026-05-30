---
id: ADR-NNN
title: <short imperative title>
status: Proposed
date: <YYYY-MM-DD>
problem: NB-<n>
supersedes: ~        # ADR-NNN this one replaces, or ~ (none)
superseded-by: ~     # filled in when a later ADR replaces this one
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
parsing prose ([NB-380](https://linear.app/nicolai-bernsen/issue/NB-380) consumes it). The
front-matter `title` is the canonical document title — the body opens with the same title as
a **bold lead-in** (not an `#` heading, which would duplicate the front-matter title), then
the first `##` section.

| Key | Required | Meaning |
| --- | --- | --- |
| `id` | yes | `ADR-NNN`, matching the filename and the bold title line. |
| `title` | yes | Short imperative title, matching the bold title line. |
| `status` | yes | Lifecycle value — see below. Keep in sync with the `## Status` section. |
| `date` | yes | Date of the current status (accepted / superseded), `YYYY-MM-DD`. |
| `problem` | rec. | The `NB-<n>` problem this ADR came from. |
| `supersedes` | opt. | The `ADR-NNN` this one replaces, or `~`. |
| `superseded-by` | opt. | The `ADR-NNN` that later replaced this one, or `~`. |

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
