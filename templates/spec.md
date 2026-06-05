<!--
backlogd Spec template — Project-form only.

`/backlogd:scope` writes this Document as the canonical spec + Acceptance Criteria
for a problem that was promoted to a Linear Project. The Project's container issue
description becomes a short summary + a link back here; this Document is the source
of truth `/backlogd:solve` and `/backlogd:review` read from.

Single-Issue and sub-issue problems do **not** get a Spec Document — their issue
description stays canonical. See `commands/scope.md` step 4.

Re-running `/backlogd:scope` updates this Document in place by `id` (one `Spec` per
Project — see `skills/linear/references/documents-and-updates.md`).
-->

# Spec

{One- to three-paragraph context lead: what the problem is, why it matters, and what
the world looks like after it is solved.}

## Goal

{A single sentence: the coherent objective this work serves — the *why* the developer,
tester, and reviewer all reason against. Distinct from the granular `## Goals` list below
(outcomes the PO is buying); this one shared sentence is the artifact the dispatch envelope
inlines and the reviewer's verdict reasons against. See `skills/ac/SKILL.md` and
`agents/refiner.md`.}

## Goals

- {Goal 1 — the outcome the product owner is buying.}
- {Goal 2 — keep the list short; each goal should be testable in principle.}

## Non-goals

- {Explicitly out of scope — protects against scope creep at solve time.}

**Specialist:** developer-{suffix} — {one-line because} *(or `developer (no specialist matched)` for the generic fallback)*

## Acceptance Criteria

- [ ] {AC item — write a verifiable statement. May carry an optional kind prefix immediately after the checkbox: `[test]` with a backticked exit-coded command, `[manual]` for a human check, `[review]` for Claude judgement. Untagged defaults to `[review]`. See `skills/ac/SKILL.md`.}
