# Definition of Ready

backlogd's repo-level **Definition of Ready** — the entry gate at the *front* of
`/backlogd:scope`, symmetric to the [Definition of Done](definition-of-done.md) at the
exit. backlogd refuses to *ship* an ungoverned increment (the reviewer blocks it); it
equally refuses to *start* an unready problem. A problem cannot become solvable until it
clears every rule below.

This is a **hard-rules floor**, not a methodology essay: each line is observable by an
agent or reviewer without taste calls. The mechanism that gets a raw idea *to* this floor
is **Socratic, not generative** — `/backlogd:scope` interrogates the idea into shape, it
does not invent the idea or rank it (see *The shaping move* below).

> **Framing honesty — DoR is community practice, not canonical Scrum.** The Definition of
> Ready is **not** in the November 2020 Scrum Guide. It is a widely-used community
> convention. backlogd adopts it to complete **entry/exit symmetry** with its DoD — it is
> **not** a Scrum-compliance fix, and backlogd does not claim it as one. Sell it honestly:
> the DoD is the Scrum *commitment* on the Increment; the DoR is backlogd's own front-gate
> that mirrors it. See [`mapping.md`](mapping.md) → *Sprint Planning* for where it sits.

## The ready check

A problem is *ready* (solvable by `/backlogd:solve`) only when **all** of these hold:

- [ ] **Crisp outcome.** The description states the desired *outcome* in one or two plain
      sentences — what the PO gets when this is done — not a wish ("make it better") and
      not a step-by-step recipe.
- [ ] **Falsifiable acceptance criteria.** A `## Acceptance Criteria` section exists, and
      every item is **observable** — a reviewer or a test could call it met/unmet from the
      merged change. A criterion that cannot be falsified (no observation distinguishes
      pass from fail) is not ready. (Typing follows [`../../skills/ac/SKILL.md`](../../skills/ac/SKILL.md).)
- [ ] **No unresolved one-way-door decision.** Every *irreversible* choice the problem
      forces (a public-API shape, a data format, a destructive migration, a
      hard-to-reverse naming) is either already decided in the description, or explicitly
      deferred to a reversible first step. An open one-way door is a PO decision, not a
      developer guess — surface it and stop.
- [ ] **Not fighting an Accepted standard.** The idea has been tested against the ADR
      corpus ([`docs/standards/index.json`](../standards/index.json)): no
      `## Acceptance Criteria` item requires doing something a **current `Accepted`** ADR's
      `assertion` forbids. A genuine conflict is surfaced to the PO (either the problem
      changes, or it must supersede the ADR first) — it is not shaped around silently.

## The shaping move — Socratic, not generative

The DoR is reached by **interrogating** a raw idea, never by generating one. `/backlogd:scope`
(via the refiner) puts three questions to the PO and **records the PO's answers** — it does
not answer them for the PO. This is the discipline that keeps the PO's judgement sharp
instead of putting them back in the rubber-stamp seat the framework exists to avoid.

- **Socratic pressure-test (interrogate, don't generate).** Surface — never pre-fill:
  - *What is the real problem behind this request?* (the outcome, not the proposed solution)
  - *Who is the user — who fails if this ships wrong?*
  - *What would make this fail?*
- **Devil's-advocate / pre-mortem.** *"Assume this shipped and was wrong — why?"* Recorded
  as the **PO's input**, not the agent's invention. The question-then-criticism pairing
  (ask, then challenge the answer) is the load-bearing half — it is where weak problems
  break before they cost a loop.
- **Standards-conflict check.** *"ADR-00X says we don't do Y — is this idea fighting a
  standard you've already set?"* This fuses the Socratic front-end with the same
  **inspection layer** the reviewer runs at the exit: the corpus is a set of persistent,
  cross-issue acceptance criteria (see [`../../skills/ac/SKILL.md`](../../skills/ac/SKILL.md)
  → *Standards are persistent, cross-issue AC*), checked here at entry and again at the
  verdict.

## Out of scope (deliberately) — the line the gate must not cross

These are **not** what the DoR does — listed here so they are not added by accident,
because crossing this line is the failure mode the gate exists to prevent:

- **Idea generation.** The DoR does **not** invent problems, propose features, or fill in
  what the PO *should* want. It sharpens an idea the PO already has.
- **Prioritization / ranking.** The DoR does **not** order the backlog or decide what is
  worth doing — that is the PO's call (the Product Owner owns Product Backlog ordering;
  see [`mapping.md`](mapping.md) → *Product Backlog*).

The gate **interrogates a raw idea into a crisp, testable problem**; it never decides
*what to build* or *whether to build it*. Crossing into generation or prioritization puts
the PO back in the rubber-stamp seat — the exact anti-pattern backlogd exists to avoid
(this is also why [ADR-004](../standards/adrs/ADR-004-backlogd-identity.md) keeps the
framework domain-agnostic scaffolding that never does the PO's product thinking for them).

## Symmetry — DoR (entry) mirrors DoD (exit)

backlogd brackets every problem with two symmetric hard-rules gates:

- **Definition of Ready** (this file) — the **entry** gate at the front of
  `/backlogd:scope`. A problem cannot start until it has a crisp outcome, falsifiable AC,
  no open one-way door, and no standards conflict.
- **[Definition of Done](definition-of-done.md)** — the **exit** gate the independent
  reviewer enforces before the Increment merges. A change cannot ship until every AC is
  met, CI is green, and the hygiene rules hold.

Same shape, opposite ends: both are observable hard-rules floors; both refuse to let an
underspecified thing through; both surface judgement calls to the PO rather than guessing.
The **standards-conflict** rule is the seam — the ADR corpus is inspected at *both* gates,
so a problem that fights a standard is caught at entry, and a change that violates one is
caught at exit.

## See also

- [`definition-of-done.md`](definition-of-done.md) — the symmetric exit gate (the Scrum
  *commitment* on the Increment).
- [`mapping.md`](mapping.md) → *Sprint Planning* — where the DoR sits in backlogd's Scrum
  interpretation, and the note that DoR is community practice, not canonical Scrum.
- [`../../skills/ac/SKILL.md`](../../skills/ac/SKILL.md) — the AC grammar the
  *falsifiable AC* rule depends on, and *Standards are persistent, cross-issue AC* (the
  inspection layer the standards-conflict rule fuses with).
- [`../../commands/scope.md`](../../commands/scope.md) → §3 and
  [`../../agents/refiner.md`](../../agents/refiner.md) — where the gate runs.
