---
id: ADR-003
title: Canonical Linear workspace configuration
status: Accepted
date: 2026-05-29
problem: NB-382
supersedes: ~
superseded-by: ~
assertion: A fresh backlogd workspace seeds exactly the canonical set and nothing more — issue labels problem, kind:ops, blocked (agent:* is owned but runtime-created, never seeded), no project labels, and three templates (a Problem issue, a backlogd-problem project with Investigate/Implement/Verify milestones, and a Spec document); kind:* beyond kind:ops and the area:* family are dogfood/per-repo only and are never seeded or adopter-facing.
applies-to:
  domains: [linear, workspace-config, init]
  file-patterns: ["scripts/linear_setup.py", "commands/init.md", "docs/guides/workspace-bootstrap.md"]
  decision-types: [workspace-config, labels, templates, seed]
---

**ADR-003 — Canonical Linear workspace configuration**

- **Status:** Accepted _(2026-05-29)_ · **Problem:** NB-382
- **Decision (TL;DR):** ship a **small opinionated seed** — issue labels `problem` · `kind:ops` · `blocked` (+ `agent:*` owned but runtime-created, never seeded); **no project labels** (nothing in the loop reads one); **two templates** — a `problem` **issue** template and a `backlogd problem` **project** template (Investigate → Implement → Verify) — **plus one `Spec` document template**. `kind:*` (beyond `kind:ops`) and `area:*` are **dogfood/per-repo only**, never adopter-facing.

> Builds on [NB-371](https://linear.app/nicolai-bernsen/issue/NB-371) (the `/backlogd:init` mechanism). Shape per ADR-001: **Status · Context · Considered Options · Decision · Consequences**. ADRs are immutable once Accepted: supersede, don't rewrite. **Documentation only — ships no engine change and re-seeds nothing**; the build is a follow-up (see [Consequences](#consequences)).

## Status

Accepted (2026-05-29). Decides backlogd's canonical _workspace configuration_ (labels · project labels · templates) — **not** the operating model, which stays in `skills/linear/`. NB-371 shipped the engine + command and applied an improvised seed; this ADR makes the canonical shape an explicit, durable decision. The engine extension + re-seed is a [follow-up](#consequences).

## Context

`/backlogd:init` brings a fresh workspace into "canonical shape" by driving `scripts/linear_setup.py` (verbs: `audit` · `ensure-label` · `recase-label` · `delete-label` · `ensure-state` · `ensure-template`). NB-371 seeded labels `problem`/`kind:ops`/`blocked`, a stub `Problem` issue template and a description-only `backlogd problem` project template — but _what the canonical config should be_ was never decided.

backlogd is a **public adopter-facing plugin**: a fresh install should receive a _small, coherent, opinionated_ set — not the dogfood team's accumulated history. The dogfood workspace currently carries ~40 labels; only a handful are loop-critical, the rest are dev-history (`dx-*`, `sdd-ado`, `area:*`, most `kind:*`, `release-pipeline`, …).

**What the loop actually reads** (the discriminator for "canonical"):

| Signal | Read by | Source of truth |
| --- | --- | --- |
| `problem` label | pickup queue — only `problem` issues are picked up | `skills/linear/SKILL.md` |
| `kind:ops` label | per-unit route flag → ops path (no worktree/PR) | `skills/linear/SKILL.md`, `skills/solve/ops.md` |
| `blocked` label | auto-managed signal layer for the PO Daily view | `skills/linear/blocked-label.md` |
| `agent:<suffix>` label | specialist routing → `developer-<suffix>` | `skills/solve/dispatch.md` |
| workflow-state **categories** | forecast/queue math (reasoned by `type`, never name) | `linear_setup.py` `CANONICAL_STATE_CATEGORIES` |

Nothing in the loop reads a **project label**, a `kind:*` value other than `kind:ops`, or any `area:*` label. Health/progress derive from `blocked-by` relations, state categories, and project status — never a label.

**Two engine gaps this decision must name** (confirmed in `scripts/linear_setup.py`):

1. **Issue labels only.** Writes go through `issueLabelCreate`/`issueLabelUpdate` (`_LABEL_CREATE_MUTATION`). Linear **project labels are a separate GraphQL type** with no verb in the engine — it cannot write one today.
2. **`templateData` is freeform `JSON!`.** `ensure-template` forwards whatever JSON it is handed (`plan_ensure_template` → `templateCreate`). "Created" ≠ "renders usefully in the Linear UI" — NB-371's issue template was unverified JSON.

## Considered Options

### Item 1 — issue-label taxonomy

| Option | What adopters get | Verdict |
| --- | --- | --- |
| **A. Minimal loop-critical set** (`problem`, `kind:ops`, `blocked`; `agent:*` owned-but-runtime-created) | Exactly the labels a signal reads; everything else is the adopter's own | ✅ **chosen** |
| B. Rich shipped taxonomy (full `kind:*` + a starter `area:*`) | A "batteries-included" board | ❌ imposes dogfood structure; `area:*` is per-repo, `kind:*` (beyond ops) is unread → dead labels |
| C. `problem` only | Smallest possible | ❌ drops `kind:ops` (a real route signal) and `blocked` (the PO Daily signal) — under-seeds the loop |

`agent:*` is **backlogd-owned but deliberately not seeded** — the scrum loop _creates_ `agent:<suffix>` on demand when routing a unit to a specialist (`dispatch.md`), and the suffix set is open-ended per install. Seeding a fixed list would be wrong (and the engine docstring already says so). `kind:*` beyond `kind:ops` and the whole `area:*` family are **dogfood/per-repo conventions**, not backlogd's contract.

### Item 2 — project labels

| Option | Verdict |
| --- | --- |
| **A. Define none** | ✅ **chosen** — no loop logic reads a project label; defining one creates a write the engine can't perform and a signal nothing consumes |
| B. Define a small set (e.g. `engagement`, `internal`) | ❌ speculative; needs the missing project-label verb _and_ invents a taxonomy with no reader. Revisit only when a feature needs it |

### Item 3 — templates

| Type | Option | Verdict |
| --- | --- | --- |
| **Issue** | `Problem`: pre-fill `## Problem` + `## Acceptance Criteria`, apply `problem` label | ✅ **chosen** — mirrors how every problem is shaped (`skills/ac/`) |
| **Project** | `backlogd problem`: milestones **Investigate → Implement → Verify** | ✅ **chosen** — matches the phase model in `skills/linear/SKILL.md` (worked example B) and what `init.md` already promises |
| **Document** | One `Spec` template _vs_ none | ✅ **one `Spec` template** — `Spec` is already a canonical Project Document role (`documents-and-updates.md`); a scaffold gives a PO hand-authoring a spec a coherent start. `Solution brief` is machine-authored (solve/review) → **no template** for it |

## Decision

Ship a **small, opinionated seed** — the loop-critical set plus the two templates already promised, plus one document template — and explicitly scope everything else out of the adopter contract.

### 1. Canonical issue labels (exactly these three are seeded)

The set the engine seeds is **`problem` · `kind:ops` · `blocked`** — unchanged from `CANONICAL_LABELS`. Names lowercase; colours/descriptions as the engine already defines them:

| Label | Colour | Description |
| --- | --- | --- |
| `problem` | `#5e6ad2` | A problem for the backlogd scrum team to solve. |
| `kind:ops` | `#bec2c8` | An ops-only unit — no worktree, no PR; gh/repo-ops only. |
| `blocked` | `#eb5757` | Auto-managed: this problem is blocked by an open dependency. |

**`agent:*` is canonical-but-not-seeded.** It is a backlogd-owned family, created at runtime by `/backlogd:solve` when a unit routes to a specialist (`agent:<suffix>` → `developer-<suffix>`). `init` must **not** seed any `agent:*` label — the suffix set is open per install. (Documented as owned so adopters don't treat `agent:docs`, `agent:tests`, … as cruft.)

**Not adopter-facing** (never seeded; flagged `review`, never `cruft`, by `audit`): the `kind:*` family **other than `kind:ops`** (`kind:research`/`feature`/`bug`/`tech-debt`) and the entire `area:*` family — these are **dogfood / per-repo-local** conventions an adopter may adopt for their own repo but backlogd does not ship. (`area:testing` vs `area:tests` on the dogfood board is one such local near-duplicate — out of scope here.)

### 2. Project labels — none

backlogd defines **no project labels**. No runtime signal reads one, so seeding one would be a label nothing consumes. This is a deliberate "ship nothing" call, not an oversight — see the engine gap in [Consequences](#consequences).

### 3. Templates

**Issue template — `Problem`** (applies the `problem` label; description body verbatim below):

```markdown
## Problem

<!-- One paragraph: what outcome the product owner wants, and why. State the
problem, not a solution. -->

## Acceptance Criteria

- [ ] [review] <criterion — a verifiable "done" statement>
- [ ] [manual] <a check only a human can confirm, if any>
```

- The AC bullets use the typed-AC grammar (`skills/ac/`): `[test]` / `[manual]` / `[review]`, untagged defaults to `[review]`.
- The template **applies the `problem` label** so a templated issue is pickup-eligible by construction.
- Default issue **title**: empty (the PO names the problem). No assignee, no priority preset.

**Project template — `backlogd problem`** — three milestones in order, no issues pre-created:

| # | Milestone | Meaning |
| --- | --- | --- |
| 1 | **Investigate** | Understand the problem; decompose; identify units & dependencies |
| 2 | **Implement** | Build the units (one committable slice each) |
| 3 | **Verify** | Check against AC; review; close |

Description body: a one-line pointer — `backlogd problem project — phases as milestones; see the Spec document for the shaped spec + Acceptance Criteria.`

**Document template — `Spec`** (one template; `Solution brief` gets none):

```markdown
## Problem

<!-- The shaped problem statement (intent). For a promoted Project this replaces
the issue description's spec. -->

## Approach

<!-- How the work is decomposed — units, phases (milestones), dependencies. -->

## Acceptance Criteria

- [ ] [review] <criterion>
```

Suggested icon `:memo:` (matching the canonical `Spec` document role in `documents-and-updates.md`).

**Status: Accepted.** These names + bodies are precise enough for the engine to seed without further product judgement; the PO ratifies the _content_ at review (the `[manual]` AC).

## Consequences

- **Engine gaps the build must close** (this ADR changes no code):
  1. **Project-label write verb.** `scripts/linear_setup.py` writes only _issue_ labels (`issueLabelCreate`); project labels are a separate Linear type with **no verb**. The "none" decision means the verb is **not needed for v1** — but the follow-up should note that any future project-label needs the verb first.
  2. **`templateData` must be UI-verified.** `ensure-template` forwards freeform `JSON!`; the follow-up must confirm each template's `templateData` actually **renders** in the Linear UI (issue body + applied label; project milestones; document body) — "created" is not "renders". The exact `templateData` key shape (e.g. how the description markdown and the label id are encoded) is to be **verified against a live create**, not assumed.
- **`audit` policy unchanged.** The non-canonical families (`kind:*` ≠ `kind:ops`, `area:*`, `dx-*`, `sdd-ado`) stay in `audit`'s `review` bucket with **no delete recommendation** — the conservative cruft policy (`priority:*` + unused defaults only) is correct and is **not** widened by this ADR.
- **Docs already aligned.** `docs/guides/workspace-bootstrap.md` and `commands/init.md` already describe the three labels + the two templates; only the **document template** is newly decided here. No doc rewrite is required by _this_ ADR beyond noting the `Spec` template when the follow-up ships it.
- **No runtime change from this ADR** — the seed the loop sees is unchanged until the follow-up re-seeds.

**Follow-up** (file on Accept; one file-able problem):

1. **Extend `/backlogd:init` to the canonical config decided here** — (a) add a **project-label verb** to the engine _only if_ a project label is later wanted (not for v1; capture the gap); (b) add the **`Spec` document template** (`--type document`); (c) replace the improvised issue/project `templateData` with the **designed bodies above** and **UI-verify** each renders; (d) re-seed the dogfood workspace via `/backlogd:init`. _(blocked by this ADR being Accepted.)_

If rejected/deferred: the NB-371 improvised seed stands; no engine change, no document template, no re-seed.

---
_Refs: NB-382 · builds on NB-371 · engine: `scripts/linear_setup.py` (`CANONICAL_LABELS`, `plan_ensure_template`) · `commands/init.md` · `docs/guides/workspace-bootstrap.md` · skills: `skills/linear/SKILL.md`, `skills/linear/blocked-label.md`, `skills/solve/dispatch.md`, `skills/ac/SKILL.md`, `skills/linear/references/documents-and-updates.md` · live workspace inventory 2026-05-29 (orchestrator-provided; not enumerated by this ADR)._
