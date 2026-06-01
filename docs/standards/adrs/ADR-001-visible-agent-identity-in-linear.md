---
id: ADR-001
title: Visible agent identity in Linear
status: Superseded by ADR-006
date: 2026-05-31
problem: NB-370
supersedes: ~
superseded-by: ADR-006
assertion: Agent identity in Linear stays comment-badge based (Tier 0); Tier 1 (MCP delegate, no server) is a gated experiment only; Tier 2 (held actor=app token + webhook server) is rejected and may not be built without superseding this ADR.
applies-to:
  domains: [agent-identity, linear, runtime]
  file-patterns: [skills/linear/**, commands/**, agents/**, docs/guides/po-overview.md]
  decision-types: [agent-identity, runtime-loop, hosting]
---

**ADR-001 — Visible agent identity in Linear**

- **Status:** Superseded by [ADR-006](ADR-006-tier2-locally-hosted-agent-identity.md) _(2026-05-31; accepted 2026-05-29)_ · **Problem:** NB-370
- **Decision (TL;DR):** default **Tier 0** (today's comment badges) · authorise a **gated Tier-1 experiment** (MCP `delegate`, no server) · **reject Tier 2** (full Agent Interaction Protocol — breaks the key-free/serverless principle).

> First ADR — establishes `docs/standards/adrs/`. Shape: **Status · Context · Considered Options · Decision · Consequences**. ADRs are immutable once Accepted: supersede, don't rewrite.

## Status

**Superseded by [ADR-006](ADR-006-tier2-locally-hosted-agent-identity.md)** (2026-05-31).
ADR-006 lifts the **Tier-2 rejection** below: this ADR rejected Tier 2 on the premise that it
requires _a held `actor=app` token + a webhook **server**_ that "turns backlogd into a hosted
service," but the NB-419 PO/colleague diagnostic shows the `actor=app` listener runs
**locally** (a local daemon + tunnel, not a cloud server), so the premise is false and Tier-2
**run locally** is now the sanctioned identity. The still-binding parts of this ADR — Tier-0
comment badges, the role-prefixed comment baseline, and **delegation-is-additive (the human
stays `assignee`)** — are **carried forward** into ADR-006; Tier-2-**cloud** stays rejected.
Body retained unchanged for history per the TEMPLATE lifecycle (supersede, don't rewrite).

Accepted (2026-05-29). Research spike (NB-370) — ships no runtime behaviour itself; the recommendation below is now binding. Follow-ups in [Consequences](#consequences) to be filed as problems.

## Context

The PO wants agents to be **visible actors** in Linear (like a colleague's "Kato" agent), not work hidden behind comment badges under the PO's own name. Four transparency asks:

**A1** which agent picked up · **A2** which closed/reviewed · **A3** when the scrum-master routed · **A4** when an agent surfaced a blocker.

"Kato" runs on Linear's **Agent Interaction Protocol**: an `actor=app` OAuth app becomes a named app user; issues are **delegated** to it (human keeps `assignee`); **AgentSessions/AgentActivities** narrate the work, driven by **webhooks**. That needs a held app token + a running server — colliding with backlogd's core principle: **official MCP only · OAuth-as-user · no keys · no server.** Crack of light: the MCP already exposes a `delegate` field, so a partial, server-free tier may be reachable.

## Verified finding — the MCP `delegate` parameter

Checked live (read-only, `Nicolai-bernsen` workspace) + Linear docs; no state mutated.

- **Q1 — custom vs built-in target?** `delegate` is a **read filter, not a validated target**: `list_issues(delegate:"Linear"|"backlogd"|"Kato"|garbage)` all returned `[]`, no error; `list_users` shows only the PO + a built-in `Linear` app user (no custom agent installed). Docs: a custom agent _can_ be a `delegate` target **once installed via `actor=app`** — but installing it is Tier-2 work, not something the MCP grants. _(Whether `save_issue(delegate:…)` writes cleanly is untested — a write the spike must not make.)_
- **Q2 — drive activities/sessions?** **No.** `delegate` is only an issue field (`list_issues`/`save_issue`). `agentActivityCreate`/`agentSessionUpdate`/AgentSession are protocol-only GraphQL, absent from the MCP toolset (verified vs live schemas). A session opened with no backend just goes `stale`.
- **Q3 — must the human `assignee` remain?** **Yes — delegation is additive** (docs: "issues can only be assigned to humans, and only delegated to agents"; the human "remains the primary assignee"). So `delegate` never disturbs the "PO owns the problem" model.

**Synthesis:** the MCP gives the `delegate` **field**, never the **agent** — no install, no activities, no session lifecycle. Real "Kato-style" presence is **Tier 2**.

## Considered Options

Columns = the AC's per-tier requirement: **(a)** which PO asks (A1–A4) it satisfies · **(b)** key-free/serverless conflict · **(c)** cost.

| Tier | A1 pickup | A2 review | A3 route | A4 blocker | (b) Key-free / serverless | (c) Cost |
| --- | --- | --- | --- | --- | --- | --- |
| **0** Comment badges (today) | comment only | comment only | comment only | comment only | ✅ none — _is_ the principle | none |
| **1** MCP `delegate`, one installed agent, no server | ✅ first-class | ❌ | ~ partial | ❌ | ⚠️ field-write clean; **token-free install must be verified (gate)** | low — 1 admin install + 1 field-write/pickup |
| **2** Full Agent Interaction Protocol (`actor=app` + webhook server + Sessions/Activities) | ✅ | ✅ | ✅ | ✅ | ❌ breaks all three legs | high + ongoing ops |

- **Tier 0** — current behaviour; A1–A4 are _discoverable in comments_ but the actor is always the human PO (no agent face, no per-agent filter).
- **Tier 1** — install one `backlogd` agent app user; scrum-master sets `delegate` via user-OAuth MCP (PO stays `assignee`). Buys A1 as first-class signal (shows on the issue, filterable by _Delegate_). Open risk: can the app user be installed **without backlogd holding an `actor=app` token**? → gate, follow-up #1.
- **Tier 2** — the full "Kato" experience; the only tier answering all of A1–A4 (per-role app users + `elicitation` activities), but needs a held `actor=app` token (breaks key-free), a webhook server (breaks serverless), and direct GraphQL off the MCP (breaks MCP-only) → turns backlogd into a hosted service.

## Decision

**Default Tier 0; authorise a gated Tier-1 experiment; reject Tier 2.** Tied to the **MCP-only / OAuth-as-user / no-key / no-server** principle:

- **Reject Tier 2** — the only tier that fully answers A1–A4, but it costs all three principle legs (held token, server, off-MCP). A different product; a deliberate principle change the PO makes later (superseding this ADR), not now.
- **Keep Tier 0** as baseline — perfect principle fit, A1–A4 covered informationally, zero cost.
- **Tier 1** is the only first-class signal reachable without obviously costing the principle (the `delegate` write is pure user-OAuth MCP, Q1–Q3). Its one residual risk — token-free install — is **untested**, so it is a **gated experiment**, switched on only after follow-up #1 confirms it.

**Status: Accepted.**

## Consequences

- **graph vs identity:** the execution-metadata graph (`scripts/graph.py`, NB-263/NB-320) records _dispatch outcomes/latency_ as private analytics — it is **not** visible Linear actor identity, so it doesn't overlap with any tier as a transparency answer.
- **`skills/linear/SKILL.md` boundary → softened** (edited in this change): agent **sessions + webhooks** stay out of scope (Tier-2 guard holds); the blanket `delegate` ban **lifts** per this ADR's gated Tier-1; `delegate` left unset by default until Accepted.
- **No runtime change from this ADR** — documentation only; behaviour changes only when a follow-up is filed + solved.

**Follow-ups** (file on Accept; each is one file-able problem):

1. **Verify token-free Tier-1 `delegate`** — install one `backlogd` agent app user (`app:assignable`); confirm `save_issue(delegate:"backlogd")` sets the field under user-OAuth, PO stays `assignee`, **no `actor=app` token held**. Gates Tier 1. _(blocks #2)_
2. **Wire `delegate` pickup into `/backlogd:solve`** — scrum-master sets `delegate` on dispatch (A1). _(blocked by #1)_
3. **PO-overview _Delegated-to-agent_ view** — extend `docs/guides/po-overview.md` with a _Delegate_-filtered saved view. _(blocked by #2)_
4. **AC parser: tolerate Linear's `\[…\]` escaping** — unrelated, surfaced here: the AC kind regex `^\[…\] ` misses Linear's stored `\[test\]`, silently defaulting tagged ACs to `[review]`. File standalone. <!-- markdownlint-disable-line MD038 -->

If rejected/deferred: Tier 0 stands; the SKILL boundary edit only _permits_ Tier 1 (revert or keep — PO's call); no follow-ups filed.

---
_Refs: NB-370 · principle: `README.md` + `docs/conventions.md` · Linear docs: agents-in-linear, assigning-issues, mcp, developers/agents, agent-interaction, oauth-actor-authorization · live read-only probes 2026-05-29 (`list_users`, `list_issues(delegate:…)` ×4, no mutation)._
