---
id: ADR-009
title: Adopt selected superpowers craft skills by reference, excluding auto-trigger and run-to-completion
status: Accepted
date: 2026-06-04
problem: NB-412
supersedes: ~
superseded-by: ~
assertion: backlogd adopts three superpowers craft skills (test-driven-development, verification-before-completion, systematic-debugging) into its developer/tester/reviewer agents by reference (vendor-clean principle + credit obra/MIT, no new always-on plugin dependency), adapted to backlogd's gated model; it explicitly rejects two superpowers stances that fight that model — the aggressive 1%-chance auto-trigger and the run-to-completion ("execute all tasks without stopping") rule — and does not adopt superpowers' generic brainstorming or two-stage subagent review, which duplicate backlogd's Linear/standards-aware scope/refiner and its tester+reviewer split.
applies-to:
  domains: [craft, developer, tester, reviewer, verification, dependencies]
  file-patterns: ["agents/developer.md", "agents/tester.md", "agents/reviewer.md", "skills/develop/**", "skills/reviewer/**", "docs/specialists.md"]
  decision-types: [dependency, craft-skill, specialist-contract, agent-identity]
---

**ADR-009 — Adopt selected superpowers craft skills _by reference_, excluding auto-trigger and run-to-completion**

- **Status:** Accepted _(2026-06-04)_ · **Problem:** NB-412
- **Decision (TL;DR):** vendor three superpowers craft skills — **test-driven-development**,
  **verification-before-completion**, **systematic-debugging** — into the
  developer/tester/reviewer agents **by reference** (copy the _principle_, credit obra under
  MIT, take **no** new always-on plugin dependency), adapted to backlogd's gated model.
  **Reject** the two superpowers stances that fight that model: its **1%-chance
  auto-trigger** and its **run-to-completion** rule. **Do not adopt** superpowers'
  **brainstorming** or **two-stage subagent review** — backlogd already has
  Linear/standards-aware equivalents (scope/refiner; tester + reviewer).

> A **borrow-selected-skills** decision, not a depend-on-the-whole-plugin one. Shape per the
> [TEMPLATE](TEMPLATE.md): **Status · Context · Considered Options · Decision · Consequences**.
> ADRs are immutable once Accepted — supersede, don't rewrite. This is **decision-only**: it
> records _which_ skills to adopt and _which conflicts to exclude_; it does **NOT** edit
> `agents/*.md` to wire them in (that is a follow-up — see Consequences).

## Status

**Accepted** (2026-06-04). This is a **governance / craft** ADR — it ships **no runtime
code** (only this ADR + the regenerated [standards index](../index.json) + the docs/README
ADR-list refresh). It **supersedes nothing**: it adds a craft layer _under_ backlogd's
process, orthogonal to the existing corpus. It is **complementary** to
[ADR-004](ADR-004-backlogd-identity.md) (don't dilute the differentiator — the framework is
the process layer; craft skills are the _how_, they don't replace it) and to
[ADR-002](ADR-002-keyless-mcp.md) (by-reference takes no new dependency, so keyless/serverless
holds).

## Context

[Superpowers](https://github.com/obra/superpowers) (obra / Jesse Vincent) is a
**craft-of-execution** methodology layer: composable skills for _how_ to do a task well —
TDD, systematic-debugging, verification-before-completion, subagent-driven-development with
two-stage review, using-git-worktrees, brainstorming. It deliberately does **not** touch
issue tracking (no Linear, no backlog), so it **complements** rather than competes with
backlogd: backlogd is the **process + system-of-record** layer (Scrum roles, Linear,
standards); superpowers is the **craft** of doing a task well. backlogd's
developer/tester/reviewer agents are the natural consumers.

This problem is a **borrow-selected-skills evaluation, NOT a depend-on-the-whole-plugin
decision** (the Notes tie it to [NB-376](https://linear.app/nicolai-bernsen/issue/NB-376) —
don't dilute the differentiator — and [NB-378](https://linear.app/nicolai-bernsen/issue/NB-378)
— the reviewer/standards layer these skills sit under). The craft skills layer _under_
backlogd's process; they don't replace it.

**Verified finding (read the real source, not the README).** Superpowers **5.1.0** is
installed locally; each skill below was read from its `SKILL.md`. Two stances **conflict**
with backlogd's orchestration and are quoted verbatim so the exclusion is checkable:

- **Aggressive auto-trigger** — `using-superpowers/SKILL.md`: _"If you think there is even a
  1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill.
  … YOU DO NOT HAVE A CHOICE. YOU MUST USE IT."_ A skill that self-fires on a 1% guess fights
  backlogd's deterministic dispatch (scope → solve → review), where _which_ skill loads is
  decided by the orchestrator and the standards index, not by an agent's self-assessment.
- **Run-to-completion** — `subagent-driven-development/SKILL.md` (line 14): _"Do not pause to
  check in with your human partner between tasks. Execute all tasks from the plan without
  stopping. … 'Should I continue?' prompts and progress summaries waste their time."_
  (Echoed in `executing-plans/SKILL.md`.) This is in **direct tension** with backlogd's
  **PO-gates and standards-blocks** model — the developer's `STATUS` contract is designed to
  **stop** at `BLOCKED` / `NEEDS_CONTEXT`, the reviewer **blocks** on an unmet standard, and
  the PO gates `[manual]` ACs. backlogd _wants_ the check-in superpowers suppresses.

Crucially, the skills' **craft content is separable from these stances.** TDD,
verification-before-completion, and systematic-debugging are each a self-contained discipline
(an Iron Law + a cycle) that carries no dependency on the auto-trigger or run-to-completion
rules. backlogd can take the discipline and leave the stance.

## Considered Options

Two axes decide it: **(1) how to take the skills** (by-reference vs depend-on-plugin) and
**(2) which skills** to take.

**Axis 1 — adoption mechanism.**

| Option | What it is | Pro | Con | Fits the constraint? |
| --- | --- | --- | --- | --- |
| **A — Adopt by reference** (chosen) | Copy the _principle_ into backlogd's own agent/skill files; credit obra (MIT) | No new runtime dependency (ADR-002 holds); principle-clean; adapt freely to the gated model; can't break on an upstream superpowers change | Manual re-sync if obra improves a skill (low — these are stable disciplines) | ✅ keyless/serverless; the AC's explicit default |
| **B — Depend on the plugin** | Declare a runtime dependency on the superpowers plugin; invoke its skills live | Auto-updates; less to maintain | New always-on dependency; **pulls in the auto-trigger + run-to-completion stances wholesale** (the very conflicts to exclude); couples backlogd's loop to an external plugin's evolution | ❌ violates the borrow-selected-skills framing and risks the differentiator (NB-376) |

**Axis 2 — which skills.**

| Skill | backlogd already has? | Verdict | Why |
| --- | --- | --- | --- |
| **test-driven-development** | A TDD-_ish_ gate (tester proves AC after the developer) | **Adopt** | Adds the **failing-test-first discipline** (_"If you didn't watch the test fail, you don't know if it tests the right thing"_) the tester's after-the-fact proof lacks. |
| **verification-before-completion** | The `STATUS` + `Final_Checklist` "evidence + exit code" contract | **Adopt** | Sharpens it with the **Gate Function** (_"NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE"_) — names "ran it _this message_" as the bar; reinforces ADR-008's live-evidence rule. |
| **systematic-debugging** | Nothing explicit | **Adopt** | **Net-new**: root-cause-before-fix (_"NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST"_), four phases, the 3-fixes-then-question-architecture rule. Pure craft gap. |
| **two-stage subagent review** (spec-compliance then code-quality) | The **tester** (proves AC) + the **reviewer** (gates the DoD/standards) split | **Don't adopt** (assessed) | backlogd's split **is** the two-stage review, and it's **better-fitted**: stage 1 = tester proving the typed ACs, stage 2 = reviewer gating the **standards corpus** (index-first). superpowers' generic version is Linear/standards-_unaware_. Running both = two competing review systems. |
| **brainstorming** | `/backlogd:scope` + the refiner (Linear/standards-aware shaping) | **Don't adopt** | superpowers' brainstorming is the **generic** shaping skill (with a `<HARD-GATE>` blocking work until a design is approved); backlogd's scope/refiner is the Linear/standards-aware equivalent. Two competing brainstorm systems = exactly what the AC warns against. |
| **using-git-worktrees** | `skills/worktree-isolation` + `skills/solve/walk.md` | **Don't adopt** (overlap noted) | backlogd already has its own worktree isolation. No gap. |

## Decision

**Adopt Option A (by reference) for exactly three skills, with two explicit exclusions and
two explicit non-adoptions. Status: Accepted.**

### (a) Adopt — three craft skills, by reference, adapted to the gated model

| Skill | The principle backlogd takes | Consumer agent(s) | Adaptation to backlogd |
| --- | --- | --- | --- |
| **test-driven-development** | Write the failing test **first**, watch it fail, then minimal code (Iron Law: _"NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST"_). | developer (writes the test that earns its keep), tester (proves AC) | Honour backlogd's developer/tester split — the developer writes the proving test for its own change; the tester owns the wider coverage sweep. **Not** a blanket "delete all code written before a test" mandate where it fights the split. |
| **verification-before-completion** | Evidence before claims; _"NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE"_ — run the command **in this message**, read the exit code, _then_ claim. | developer, tester, reviewer | Folds into the existing `STATUS` + `Final_Checklist` "evidence + exit code per box" contract and **reinforces ADR-008** (live evidence for external-surface claims). |
| **systematic-debugging** | Root cause before fix; four phases (investigate → pattern → hypothesis → implement); after 3 failed fixes, **question the architecture**, don't fix again. | developer (when a dispatch is a bug), reviewer (judging a fix) | A bug dispatch reproduces + roots-causes before patching; pairs with TDD (write the failing test that reproduces the bug first). |

**By reference means:** the principle is copied into backlogd's own files and **credited**
(see (d)); backlogd takes **no new runtime dependency** on the superpowers plugin, so
[ADR-002](ADR-002-keyless-mcp.md) (keyless / serverless / no new dependency) holds.

### (b) Exclude — explicitly, the two conflicting stances

These are adopted-out **by name**, so a reviewer can verify the exclusion from the text and
the PO can ratify the _stance_:

1. **Aggressive auto-triggering.** backlogd does **not** adopt superpowers' _"even a 1%
   chance … you ABSOLUTELY MUST invoke the skill … YOU DO NOT HAVE A CHOICE"_ rule. Which
   craft skill applies is decided by **backlogd's orchestration** (the dispatch + the
   standards index's `applies-to`), **not** by an agent self-firing on a 1% guess. The craft
   skills are referenced as **disciplines a dispatched agent follows when its work calls for
   them**, never as always-on auto-triggers competing with the orchestrator.
2. **Run-to-completion.** backlogd does **not** adopt _"Do not pause to check in … Execute
   all tasks from the plan without stopping."_ It is in **direct tension** with backlogd's
   gated model: the developer **must** stop and report `BLOCKED` / `NEEDS_CONTEXT` (it does
   not guess past a blocker), the reviewer **blocks** on an unmet standard, and the PO gates
   `[manual]` ACs. backlogd's check-in points are **load-bearing**, not waste — the opposite
   of superpowers' stance. The adopted skills are taken **shorn of this rule**.

### (c) Do not adopt — the generic duplicates

- **brainstorming** — `/backlogd:scope` + the refiner are the **Linear/standards-aware**
  shaping layer; superpowers' brainstorming is the **generic** one. Avoid two competing
  brainstorm systems.
- **two-stage subagent review** — backlogd's **tester (proves AC) + reviewer (gates the
  standards corpus)** split **is** the two-stage review, and it is standards-aware where
  superpowers' is not. Avoid two competing review systems.
- **using-git-worktrees** — overlaps `skills/worktree-isolation` (no gap; noted for
  completeness).

### (d) License / attribution

Superpowers is **MIT** (Copyright (c) 2025 Jesse Vincent). By-reference adoption copies
_principles_, but where backlogd vendors skill **text/structure** the follow-up MUST
**credit obra (Jesse Vincent) and note the MIT license** at the point of use (a one-line
attribution in the referencing file, or a `CREDITS`/`NOTICE` entry). The MIT permission and
copyright notice are satisfied by that attribution.

Tie-back to the constraint named in Context: Option A is the **only** mechanism that takes
the craft benefit while keeping backlogd **keyless/serverless** (ADR-002), **principle-clean
/ un-coupled** from an external plugin's evolution, and — critically — lets backlogd **strip
the two conflicting stances** (a plugin dependency would pull them in wholesale). Adopting
exactly the three discipline-skills (and **not** the generic brainstorm/review) avoids
running two competing systems and protects the differentiator (NB-376).

## Consequences

What becomes true once this is in force (it adds a craft layer + records exclusions; it
changes no runtime behavior yet):

- **There is a sanctioned craft layer _under_ backlogd's process.** The three disciplines are
  the agreed _how_; the two stances are explicitly out; the generic duplicates are explicitly
  not adopted. A reviewer can check a future wiring-in change against this ADR's `applies-to`.
- **No new dependency, keyless intact.** By-reference adoption means ADR-002 holds and
  backlogd cannot break on an upstream superpowers change.
- **An attribution obligation exists** — vendored skill text must credit obra (MIT) at the
  point of use.
- **Re-sync is manual** — if obra materially improves an adopted skill, backlogd updates its
  own copy deliberately. Low cost: these are stable disciplines.

**Follow-ups** (each a file-able problem — **none started by this ADR**; this ADR is
decision-only and does **not** edit the agent files):

1. **Wire TDD + verification-before-completion into `agents/developer.md` and
   `agents/tester.md`** — reference the disciplines in the `Investigation_Protocol` /
   `Final_Checklist`, with obra/MIT credit at the point of use. (Coordinate with
   [NB-430](https://linear.app/nicolai-bernsen/issue/NB-430)'s index-first standards load —
   a craft skill is referenced the same index-first way.)
2. **Add a `systematic-debugging` reference for bug dispatches** in `agents/developer.md`
   (root-cause-before-fix + the 3-fixes-then-question-architecture rule).
3. **Note in `agents/reviewer.md`** that verification-before-completion + systematic-debugging
   are the craft lens for judging a fix (without duplicating the tester's role).

If reversed (a future ADR supersedes this): backlogd would lose the sanctioned craft layer
and the explicit exclusions, reopening the risk of importing the auto-trigger /
run-to-completion stances or running competing brainstorm/review systems. Until then, this is
the craft-skills-adoption standard of record.

---
_Refs: NB-412 · source read live: superpowers 5.1.0 `SKILL.md` files (using-superpowers, test-driven-development, verification-before-completion, systematic-debugging, subagent-driven-development, requesting-code-review, receiving-code-review, brainstorming, executing-plans) · upstream: [obra/superpowers](https://github.com/obra/superpowers) (MIT, © 2025 Jesse Vincent) · related: [NB-376](https://linear.app/nicolai-bernsen/issue/NB-376) (don't dilute the differentiator) · [NB-378](https://linear.app/nicolai-bernsen/issue/NB-378) (reviewer/standards layer) · [NB-430](https://linear.app/nicolai-bernsen/issue/NB-430) (index-first standards load) · constraints: [ADR-002](ADR-002-keyless-mcp.md) (keyless / no new dependency — NOT superseded) · [ADR-004](ADR-004-backlogd-identity.md) (the process-layer differentiator) · [ADR-008](ADR-008-live-surface-verification.md) (live-evidence, reinforced by verification-before-completion)._
