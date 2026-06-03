---
id: ADR-008
title: Live-surface verification — external-surface claims are specified from and verified against the live surface
status: Accepted
date: 2026-06-03
problem: NB-423
supersedes: ~
superseded-by: ~
assertion: Any new or changed claim about how an external surface behaves (the Linear MCP tool surface, the Linear REST/GraphQL API, the Linear UI, or an OAuth/install flow) requires live evidence before the problem is Done — a live probe's output, a screenshot, or a real round-trip against the live surface, explicitly NOT a mocked test or an API call merely returning `created`/`200`; an external-surface claim lacking live evidence is marked as an unverified assumption, never stated as fact.
applies-to:
  domains: [linear, external-surface, verification, docs]
  file-patterns: ["skills/linear/**", "commands/**", "scripts/linear_setup.py", "docs/guides/*-setup.md", "skills/retro/**"]
  decision-types: [external-surface-claim, live-evidence, mcp-behavior, api-behavior, ui-behavior, oauth-flow]
---

**ADR-008 — Live-surface verification: external-surface claims are specified _from_ and verified _against_ the live surface**

- **Status:** Accepted _(2026-06-03)_ · **Problem:** NB-423
- **Decision (TL;DR):** a new or changed claim about how an **external surface** behaves —
  the **Linear MCP tool surface**, the **Linear REST/GraphQL API**, the **Linear UI**, or an
  **OAuth/install flow** — requires **live evidence** (a live probe's output, a screenshot,
  or a real round-trip against the live surface) **before the problem is Done**. A **mocked
  test** or an API call merely returning **`created`/`200`** is **not** sufficient evidence. An
  external-surface claim with no live evidence is **marked as an unverified assumption**, never
  stated as fact.

> The evidence/specification standard the reviewer enforces so an assumption about an
> external surface can't pass as fact. Shape per the [TEMPLATE](TEMPLATE.md): **Status ·
> Context · Considered Options · Decision · Consequences**. ADRs are immutable once
> Accepted — supersede, don't rewrite. This is **docs/decision-only** — no runtime code ships.

## Status

**Accepted** (2026-06-03). This is a **governance** ADR — it ships **no code** (only this ADR,
a bounded prose reconciliation of the known false assumptions, and the regenerated
[standards index](../index.json)). It **supersedes nothing**: it adds a verification rule
orthogonal to the existing corpus. It is **complementary to NB-424** (the first-live-run
_execution_ gate for guides/runbooks) — that ADR governs **running** a deliverable end-to-end;
this one governs the **evidence behind a claim**. Where they meet (a `*-setup.md` guide that
asserts external behavior), the guide's
[`docs/guides/agent-identity-setup.md`](../../guides/agent-identity-setup.md) "Verified — first
live run" blockquote is the **exemplar** of the live evidence this ADR requires.

## Context

A recurring failure crossed **≥4 Done problems**: work was specified from **docs / mocks /
assumptions** about an external surface, **passed every check**, and then **broke on the live
surface** — caught only by a live probe, a `[manual]` check, or the PO's own run. The defects
are not careless; they are the gap between _what the surface is documented (or assumed) to do_
and _what it actually does_.

| Problem | The assumed behavior | What the live surface actually did | What caught it |
| --- | --- | --- | --- |
| [NB-421](https://linear.app/nicolai-bernsen/issue/NB-421) | `save_issue` auto-creates an unknown label | the label is **silently dropped** (call succeeds, no error, no label) | a live run during the NB-417 solve |
| [NB-392](https://linear.app/nicolai-bernsen/issue/NB-392) | `templateData` = the MCP create-args | `templateData` is Linear's **draft-entity** shape; the API reports `created`, the UI **doesn't render** | a `[manual]` UI check (383 mocked tests + the API all passed) |
| [NB-371](https://linear.app/nicolai-bernsen/issue/NB-371) | the admin `audit` call's param types | the live call **400'd** (`String!` vs `ID`) | a live admin run (43 mocked tests green) |
| [NB-390](https://linear.app/nicolai-bernsen/issue/NB-390) | the app-config form + authorize URL (from API docs) | the form fields were wrong; the URL broke on unencoded `,`/`:`; the install 500'd yet succeeded | the PO's live install run |

Found while shaping this very problem — and a worked example of the standard in **both**
directions: the retro skill's idempotent summary upsert assumed project-thread comments were
**not** listable (`list_comments` "issues only", read off the stale 2026-05-28
[`linear-mcp.md`](../../../skills/linear/references/linear-mcp.md) snapshot). The reconciliation
treated that as an unverified claim rather than asserting its opposite, and a **live probe
(2026-06-03)** then showed `list_comments({ projectId })` **does** list the project thread and
return prior comments by marker. So the assumed-missing capability was actually **present** —
exactly the gap this ADR closes, caught the moment its own rule was applied.

**The common root.** A check that runs against a mock, or an API response that merely says
`created`/`200`, proves the _call shape_, not the _behavior a human or a downstream reader
will observe_. The surfaces here are all **outside the repo's control** and change upstream,
so "the docs say" and "the test passes" are both insufficient evidence for a behavioral claim.

## Considered Options

The axis that decides it is **what counts as sufficient evidence for an external-surface
behavioral claim** — and therefore what a reviewer may pass.

| Option | Evidence accepted | Catches the NB-421/392/371/390 class? | Cost | Fits the constraint? |
| --- | --- | --- | --- | --- |
| **A — Status quo: docs + mocked tests** | a doc citation or a green mocked test | ❌ no — every defect above passed this | low | ❌ the failure this ADR exists to close |
| **B — Live evidence required; unverified claims marked as such** (chosen) | a live probe's output, a screenshot, or a real round-trip; else marked unverified | ✅ yes — each defect needed exactly one of these | a live probe / screenshot per new claim | ✅ keyless (the existing MCP/OAuth-as-the-user surface), reviewer-checkable |
| **C — Forbid all external-surface claims unless re-probed every change** | live re-probe of every touched claim, always | ✅ yes, but over-broad | high — re-probes unchanged, stable claims | ❌ too costly; punishes correct, unchanged docs |

- **A** — what the corpus did implicitly. A mocked test and an API `created` are real signals
  about _call shape_, but the evidence above proves they say nothing about live _behavior_.
- **B** — the ledger of evidence the reviewer can judge. It binds **new or changed** claims
  only (so a stable, already-verified claim isn't re-litigated), and it gives an honest escape
  hatch: a claim you _can't_ yet verify live is **labelled an assumption**, not asserted as
  fact — so a reader (and the reviewer) sees the risk instead of inheriting a hidden one.
- **C** — sound in spirit but over-broad: re-probing every unchanged claim on every change
  burns effort on correct docs and trains reviewers to wave it through. Scope to _new/changed_.

## Decision

**Adopt Option B. Status: Accepted.** The rule has three parts a reviewer reads off the
assertion:

### (a) What is an external surface

A surface **outside the repo's control**, whose behavior the repo cannot guarantee from its
own source. At minimum:

| Surface | Examples in this repo |
| --- | --- |
| **Linear MCP tool surface** | which `mcp__linear__*` tools exist and their parameters — e.g. `save_issue.labels` silently drops unknown names; which filters `list_comments` actually accepts |
| **Linear REST/GraphQL API** | mutation/field shapes and scalar types — e.g. `audit`'s `String!` vs `ID`; `templateData: JSON!` accepting a non-rendering shape |
| **Linear UI** | what actually **renders** — e.g. whether a created template/issue/project shows up for a human |
| **OAuth / install flows** | the app-config form fields, the authorize-URL encoding, the install/redirect behavior |

### (b) What counts as live evidence

| Counts as live evidence | Does **NOT** count |
| --- | --- |
| a **live probe's output** (a real call against the live surface, its result recorded) | a **mocked test** passing |
| a **screenshot** of the live UI / form / render | an API call merely returning **`created`** or **`200`** |
| a **real round-trip** against the live surface (write → read-back → observe) | "the docs say" / an assumption from API documentation |

The distinction is **behavior a reader will observe**, not **call shape**. `created`/`200`
proves the call was accepted; it does **not** prove the row renders, the label stuck, or the
param type was right (NB-392/421/371 each returned success and were still wrong).

### (c) When live evidence is required

For **any new or changed claim about external-surface behavior**, **before the problem is
Done**. Not for unchanged, already-verified claims (those carry their prior evidence). A claim
that **cannot** be verified live within the slice is **explicitly marked an unverified
assumption** (e.g. "_assumed, not verified against the live surface_") — never written as a
flat fact. Marking is the honest fallback; silence is the failure.

Tie-back to the constraint named in Context: Option B is the **single** rule that catches the
≥4-problem failure class (each defect needed exactly one live probe / screenshot / round-trip),
stays **keyless** (it reuses the existing OAuth-as-the-user MCP and the local OAuth install —
no new credential), and is **reviewer-checkable** off one assertion: _is there live evidence,
or is the claim marked unverified?_

### How the reviewer applies it

The reviewer's index-first walk matches this ADR on a change touching `skills/linear/**`,
`commands/**`, `scripts/linear_setup.py`, `docs/guides/*-setup.md`, or `skills/retro/**` (the
`applies-to`). For such a change that **asserts external-surface behavior**, the reviewer
checks for live evidence (or an explicit unverified-assumption marker) and **names the gap**
(`met`/`unmet`) rather than passing the change. The exemplar to point at is the
[agent-identity guide](../../guides/agent-identity-setup.md)'s "Verified — first live run"
blockquote.

## Consequences

What becomes true once this is in force (it adds a rule + reconciles known false claims; it
changes no runtime behavior):

- **An external-surface assumption can no longer pass as fact.** The reviewer has a checkable
  assertion: live evidence, or an explicit "unverified assumption" marker — anything else is
  `unmet`. This closes the NB-421/392/371/390 class at the **specification** step.
- **The known false claims are reconciled** (this change): `commands/scope.md` §4.5 and
  `skills/linear/references/linear-mcp.md` already carry the NB-421 silently-dropped-label
  correction (verified present); `docs/guides/agent-identity-setup.md` already carries the
  2026-06-02 URL-encoding + harmless-redirect corrections (verified present);
  `scripts/linear_setup.py` already states the NB-392 `templateData` real-shape honestly
  (verified); and `skills/retro/SKILL.md`'s project-thread dedupe assumption is **corrected** —
  a live probe (2026-06-03) confirmed `list_comments({ projectId })` lists the project thread,
  so the no-milestone summary does **reliable marker-dedupe** (and `documents-and-updates.md` /
  `linear-mcp.md` are flipped to that verified-live finding).
- **Live evidence has a small standing cost** — a probe or screenshot per _new_ external-surface
  claim. Scoped to new/changed claims, it does not re-litigate stable docs.
- **It is honest about its own limits.** A surface that genuinely can't be probed in-slice is
  labelled, not asserted — so the risk is visible, not hidden.

**Follow-ups** (each a file-able problem — **none started by this ADR**):

1. **A reusable "Verified — live" blockquote convention** across guides/skills (the
   agent-identity guide has one; generalize the shape) if a third surface needs it.
2. **Coordinate with [NB-424](https://linear.app/nicolai-bernsen/issue/NB-424)** so the
   first-live-run _execution_ gate and this _evidence_ standard reference each other without
   overlap.

If reversed (a future ADR supersedes this): external-surface claims would revert to
docs/mocked-test evidence, reopening the gap this closed. Until then, this is the
live-surface verification standard of record.

---
_Refs: NB-423 · evidence: NB-421 (label silently dropped) · NB-392 (`templateData` draft-entity shape, non-rendering) · NB-371 (`audit` `String!` vs `ID`) · NB-390 + [`docs/guides/agent-identity-setup.md`](../../guides/agent-identity-setup.md) (app-config / authorize-URL / redirect) · live-evidence exemplar: the "Verified — first live run" blockquote in the agent-identity guide · complementary: NB-424 (first-live-run execution gate — distinct lane) · binding constraint: [ADR-002](ADR-002-keyless-mcp.md) (keyless / OAuth-as-the-user — NOT superseded; the live probes reuse it)._
