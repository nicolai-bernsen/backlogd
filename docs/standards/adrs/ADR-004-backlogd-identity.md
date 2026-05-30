---
id: ADR-004
title: backlogd is problem-type-agnostic empirical Scrum for an agent team
status: Accepted
date: 2026-05-30
problem: NB-376
supersedes: ~
superseded-by: ~
assertion: The framework layer is domain-agnostic Scrum scaffolding that never does domain work — all domain work routes to pluggable, credential-agnostic specialists (each declaring domain, inputs, and non-scope); an instance's value = specialists × standards (the domain DoD); scope is code and non-code alike; backlogd does NOT rebuild Cyrus runtime plumbing or duplicate Linear Diffs.
applies-to:
  domains: [identity, scope, framework, specialists, standards, scrum]
  file-patterns: ["**"]
  decision-types: [identity, scope, positioning, agent-identity, specialist-contract]
---

# ADR-004 — backlogd is problem-type-agnostic empirical Scrum for an agent team

- **Status:** Accepted _(2026-05-30)_ · **Problem:** NB-376
- **Decision (TL;DR):** backlogd is **empirical Scrum for an agent team, problem-type
  agnostic.** The framework layer is domain-agnostic Scrum scaffolding that **never does the
  domain work** — that routes to **pluggable specialists** ("Developers"). An instance's
  value = **specialists × standards**. Scope is **code and non-code** alike. This is a
  **category claim, not a feature claim**; backlogd does **not** rebuild Cyrus runtime
  plumbing or duplicate Linear Diffs.

> The identity decision the rest of the system hangs off — scope, the differentiator, and
> what the reviewer/DoD *mean* all derive from it. Shape per ADR-001:
> **Status · Context · Considered Options · Decision · Consequences**. ADRs are immutable
> once Accepted: supersede, don't rewrite. **Documentation only — ships no engine change.**

## Status

Accepted (2026-05-30). The PO has fixed backlogd's identity. This ADR also renders
**go/no-go on the always-on runtime build** ([NB-379](https://linear.app/nicolai-bernsen/issue/NB-379)
is blocked-by this): **GO** to *explore* it (the NB-379 spike), with an explicit flip
condition — see [Decision → Always-on runtime: GO](#always-on-runtime-build-go-with-a-flip-condition).
The keyless principle ([ADR-002](ADR-002-keyless-mcp.md)) is the binding constraint on any
always-on design.

## Context

backlogd needs **one** decision that fixes its identity, because everything downstream
(scope, differentiator, what the reviewer/DoD mean) depends on it and was being argued
piecemeal. The realisation that settles it: **Scrum was never a software framework.** Its
roots are Takeuchi & Nonaka's 1986 study of *manufacturing* teams; the November 2020 Scrum
Guide deliberately stripped software-specific language to make explicit that Scrum is a
framework for **complex adaptive problems, any domain**. So backlogd being problem-type
agnostic is **not scope creep — it is fidelity to Scrum.**

Two questions were entangled and are resolved together here:

- **What is backlogd?** A coding-agent, or something broader?
- **How does it differ from Cyrus?** (Previously tracked as a separate "vs Cyrus"
  question.) The differentiator turns out to be a *consequence* of the identity, not a
  separate axis — so it folds in (see [Decision → vs Cyrus](#differentiator-vs-cyrus)).

What is true today: the Scrum scaffolding already exists (the `/backlogd:*` commands as
scrum-master, the human as PO, the `backlogd:developer` subagent as the Developers — see
[`docs/scrum/mapping.md`](../../scrum/mapping.md)); specialist dispatch exists
([NB-337](https://linear.app/nicolai-bernsen/issue/NB-337), `docs/specialists.md`); and a
standards corpus exists (this ADR set + the [Definition of Done](../../scrum/definition-of-done.md)).
The identity names what binds them.

## Considered Options

Axes = **fidelity to Scrum** (does it match a framework for *any* complex adaptive
problem?) · **what the framework does itself** · **how an instance gets domain substance** ·
**positioning vs a single-task coding agent**.

| Option | Fidelity to Scrum | Framework does… | Domain substance from… | Positioning |
|---|---|---|---|---|
| **A — Problem-type-agnostic empirical Scrum** (chosen) | ✅ matches "any complex adaptive problem" | process only — never domain work | pluggable specialists × standards corpus | category claim — "a team, any domain" |
| **B — A coding-agent framework** | ⚠️ narrows Scrum back to software | process + an implied coding bias | bundled coding ability | feature claim — "does your coding task" (Cyrus's lane) |
| **C — A generic multi-agent toolkit** (no Scrum) | ❌ drops the empirical loop entirely | wiring, no roles/events/artifacts | whatever the user assembles | none — undifferentiated |

- **A** — the framework is the Scrum scaffolding and nothing domain-specific; the *empty*
  Scrum is made real in a given domain by the specialists' craft and the standards corpus.
  Fits the 2020 Guide's deliberate domain-neutrality.
- **B** — re-narrows Scrum to software (the thing the 2020 Guide undid) and collapses the
  category claim into a feature race with single-task coding agents.
- **C** — keeps agnosticism but throws away the differentiator: without the empirical loop
  (transparency / inspection / adaptation) there is no "works the way good teams work."

## Decision

**Adopt Option A.** backlogd is **empirical Scrum for an agent team, problem-type
agnostic.** **Status: Accepted.**

### Identity in one sentence + framework-vs-instance

> backlogd is empirical Scrum run by an agent team, agnostic to the *kind* of problem: the
> **framework layer** is the Scrum scaffolding (PO owns the *what/why* + direction via
> milestones; the scrum-master owns *process* + blocker removal; the events + artifacts),
> and it **never does the domain work** — domain work is delegated to **pluggable
> specialists**, so any **instance's value = specialists × standards.**

The **framework** is domain-agnostic and ships empty of domain knowledge. The **instance**
is what you get when you point it at a backlog and supply two things:

- **Specialists** — the "Developers" of the team: Claude Code specialist subagents
  (`developer-<suffix>`, NB-337 / [`docs/specialists.md`](../../specialists.md)) or native
  skills (e.g. `pptx`, `docx`, data-analysis). Their **craft** is the *how*.
- **Standards** — the corpus (ADRs + the [Definition of Done](../../scrum/definition-of-done.md))
  that encodes the **domain-specific Definition of Done**. The standards are the *quality
  bar*.

Neither alone is the product: the framework is an empty loop, and specialists with no
standards have no quality gate. **Specialists × standards** is what makes the empty Scrum
real in a given domain — that product is the multiplier, not the sum.

### Mapping to Scrum's three empirical pillars

Scrum stands on three pillars of empiricism — **transparency, inspection, adaptation**.
backlogd is judged honest only if all three are real, not ceremony:

| Pillar | backlogd surface | Real today? |
|---|---|---|
| **Transparency** | Linear is the system of record (problems, states, results); **visible agent identity** ([NB-370](https://linear.app/nicolai-bernsen/issue/NB-370) / [ADR-001](ADR-001-visible-agent-identity-in-linear.md)) makes *which agent did what* legible. | Yes — Linear + comment-badge identity ship today; richer agent presence is the gated NB-370 work. |
| **Inspection** | The **execution graph** ([NB-320](https://linear.app/nicolai-bernsen/issue/NB-320), `scripts/graph.py`) records dispatch outcomes/latency; the **independent verdict review** inspects each increment against its AC + the DoD. | Yes — review ships today; the graph join (NB-320) is the named v2. |
| **Adaptation** | **Standards growth** (the ADR corpus expands as decisions are made) + **ADR supersession** (a decision is revised by a *new* ADR, never an in-place edit) + the **retrospective** that feeds process change back into `/docs` and the commands. | Partly — standards growth + supersession are live (this ADR is an instance). The retrospective is **not yet a command** (see the honesty note below). |

**Honesty note on adaptation.** The Sprint Retrospective is, today, **out of scope as an
automated event** — [`docs/scrum/mapping.md`](../../scrum/mapping.md) records that v1 has no
retrospective command and process improvement happens out-of-band (the human PO updates
`/docs` and the commands). Adaptation is therefore **real but incomplete**: the
standards-growth + supersession half is mechanised; the periodic-retrospective half is
manual until [NB-381](https://linear.app/nicolai-bernsen/issue/NB-381) closes it. This ADR
does **not** claim a retro command exists.

### Differentiator (vs Cyrus)

The "vs Cyrus" question resolves *inside* the identity rather than as a separate decision.

- **Cyrus** = "an agent that does your coding task." A capable single-task coding agent.
- **backlogd** = "an agent *team* that works the way good teams actually work, in **any**
  domain."

This is a **category claim, not a feature claim.** backlogd does **not** compete on "we also
do slides" — it competes on **process positioning**: *bring your specialists and your
Definition of Done*, and get a transparent, inspected, adapting loop around them. The edge
is the **Scrum process + a standards-enforcing quality gate + a self-improvement loop**, not
breadth of built-in task types.

**Do NOT rebuild** (explicit non-goals — these are Cyrus's lane, and re-implementing them
dilutes the category claim into a feature race):

- **Cyrus's runtime plumbing** — the agent-execution machinery that runs a coding task.
- **Linear Diffs** — Cyrus's Linear-native diff/review surface. backlogd reviews increments
  via PRs + the independent verdict review, not a duplicated diff product.

### Scope — code *and* non-code

backlogd's scope is **both code and non-code problems.** "Write the Q3 board deck,"
"restructure the onboarding docs," and "fix the failing pipeline" are all valid problems;
the framework is identical across them and only the **specialist** changes. This is a direct
consequence of Scrum's domain-neutrality (Context) — narrowing to code would re-break the
fidelity the identity rests on.

To make agnosticism *operable* rather than aspirational, every specialist must satisfy a
**specialist contract**:

- **Declares its domain** — the shape of work it owns (e.g. "narrative prose, README/docs").
- **Declares its inputs** — what it needs to act (the problem, the AC, the worktree).
- **Declares what it does NOT cover** — explicit negative scope, so the framework can
  **detect a gap** (a problem no specialist claims) instead of mis-dispatching it. (This is
  exactly how `/backlogd:scope` picks — description-driven, and it falls back to the generic
  `developer` and *says so* when nothing fits; see [`docs/specialists.md`](../../specialists.md).)
- **Stays credential-agnostic** — the framework **bakes in no domain credentials.** Auth is
  the user's own (keyless / OAuth-as-the-user per [ADR-002](ADR-002-keyless-mcp.md)); a
  specialist that needs a domain credential obtains it through the user's environment, never
  from a secret the framework holds.

### Always-on runtime build: GO (with a flip condition)

NB-379 (an always-on / headless runtime) is **blocked-by this** ADR and needs a go/no-go.

- **Verdict: GO** — greenlight the always-on-runtime **exploration** (the NB-379 spike). An
  agnostic Scrum team is more valuable if its loop can run continuously, so the exploration
  is worth doing.
- **Flip condition (binding):** the spike proceeds to a **product build only if** it
  **preserves the keyless / "runs as the user" principle** of [ADR-002](ADR-002-keyless-mcp.md)
  — e.g. a device-code or short-lived-token OAuth flow that keeps the user as the actor while
  dropping the browser step. **If the only viable always-on design requires a held key, a
  stored long-lived PAT, or a backlogd-hosted server, it does NOT proceed** without first
  **superseding ADR-002**. ADR-002 is the constraint; this GO does not bend it.

### Scrum-fidelity commitment + risk

backlogd makes an explicit **commitment to Scrum fidelity**: roles, events, and artifacts
map **honestly** to the 2020 Guide, and the canonical translation lives in
[`docs/scrum/mapping.md`](../../scrum/mapping.md).

The **risk** this commitment carries: a **Scrum-literate audience will judge backlogd
against the Guide.** Claiming "Scrum" and then shipping ceremony — roles in name only, an
empirical loop that doesn't actually inspect-and-adapt — would be read as cargo-culting and
would cost credibility. The mitigation is to keep the mapping honest about what is real vs
deliberately omitted (the [mapping](../../scrum/mapping.md) already names continuous-flow
instead of fixed sprints, and the retrospective as out-of-scope-today). The **empirical loop
especially must be real, not ceremony** — which is why the adaptation pillar above is
flagged as only *partly* mechanised rather than overclaimed.

## Consequences

- **Settles scope** — code-and-non-code is now the baseline; a non-code problem is in
  scope by construction, and the only question per problem is *which specialist*. The
  generic `developer` is the honest fallback when none fits.
- **Settles positioning** — backlogd's pitch is the **category claim** (a team, any domain),
  not a feature list. The "do not rebuild" list (Cyrus runtime plumbing, Linear Diffs) is a
  durable non-goal: re-litigating it requires superseding this ADR.
- **Constrains specialists** — the specialist contract (domain · inputs · non-scope ·
  credential-agnostic) is now a requirement, not a nicety. A new specialist that omits its
  negative scope or bakes in a credential violates this ADR.
- **Unblocks NB-379 with a guardrail** — the always-on spike may proceed; any design that
  drops keyless/runs-as-the-user must supersede ADR-002 before becoming a product.
- **Raises the bar on honesty** — committing to Scrum fidelity means the mapping and the
  empirical loop are held to the Guide; overclaiming the retrospective (or any pillar)
  would breach this ADR's own commitment.

**Follow-ups** (file on Accept; each one file-able problem):

1. **Specialist-contract checklist** — make "declares domain / inputs / non-scope /
   credential-agnostic" an explicit, checkable section in the specialist template
   (`docs/specialists.md` / the specialist agent files), so a gap is caught at authoring
   time. *(builds on NB-337.)*
2. **Close the adaptation pillar** — land a retrospective/self-improvement loop
   ([NB-381](https://linear.app/nicolai-bernsen/issue/NB-381)) so "adaptation" is fully
   mechanised, then update [`docs/scrum/mapping.md`](../../scrum/mapping.md) (which currently
   marks the retrospective out-of-scope).
3. **Always-on runtime spike** — [NB-379](https://linear.app/nicolai-bernsen/issue/NB-379),
   now unblocked, under the keyless flip condition above.

If reversed: narrowing backlogd back to code-only (Option B) would re-break Scrum fidelity
and collapse the category claim — a deliberate repositioning the PO makes by superseding
this ADR, not a quiet drift.

---
_Refs: NB-376 · related: [ADR-001](ADR-001-visible-agent-identity-in-linear.md) (visible agent identity), [ADR-002](ADR-002-keyless-mcp.md) (keyless / runs-as-user — the flip-condition constraint), [ADR-003](ADR-003-canonical-linear-workspace-configuration.md) · specialists: NB-337, [`docs/specialists.md`](../../specialists.md) · Scrum: [`docs/scrum/mapping.md`](../../scrum/mapping.md), [`docs/scrum/definition-of-done.md`](../../scrum/definition-of-done.md), [`docs/scrum/scrum-guide.md`](../../scrum/scrum-guide.md) · pillars/inspection: NB-320 (`scripts/graph.py`) · adaptation: NB-381 · always-on: NB-379 · source: Takeuchi & Nonaka 1986; the Scrum Guide (Nov 2020)._
