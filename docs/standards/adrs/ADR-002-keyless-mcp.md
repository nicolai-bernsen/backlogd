---
id: ADR-002
title: Keyless, OAuth-as-the-user, no server
status: Accepted
date: 2026-05-29
problem: NB-377
supersedes: ~
superseded-by: ~
assertion: The runtime loop holds no API key, no stored secret, and runs no backlogd-hosted server — Linear/GitHub are reached only via official OAuth-as-the-user paths (Linear MCP, gh CLI); the sole exception is the one-time, local, setup-only /backlogd:init admin key, never read by the orchestrator or any agent.
applies-to:
  domains: [auth, runtime, dependencies, linear]
  file-patterns: ["**"]
  decision-types: [secret-custody, runtime-loop, hosting, dependency]
---

**ADR-002 — Keyless, OAuth-as-the-user, no server**

- **Status:** Accepted _(2026-05-29)_ · **Problem:** NB-377
- **Decision (TL;DR):** backlogd reaches Linear/GitHub **only** through official
  OAuth-as-the-user paths (the Linear MCP, the `gh` CLI) — **no API keys, no stored secrets,
  no backlogd-run server**. The runtime loop holds no credential of its own.

> First reflex-rule promoted to an explicit, reconsiderable standard. It was enforced
> everywhere (README, conventions, ADR-001's Tier-2 rejection) before it was ever _written_
> as a decision that could be reopened. This ADR fixes that.

## Context

backlogd is a public, clean-room Claude Code plugin: you point it at your own Linear backlog
and it runs as **you**. From the start it has talked to Linear through the **official Linear
MCP** (OAuth handled by Claude Code) and to GitHub through the **`gh` CLI** (the user's own
auth) — never an embedded API client, never a pasted token, never a process backlogd hosts.

The principle is stated in [`README.md`](../../../README.md) (Setup) and
[`docs/conventions.md`](../../conventions.md), and it is the stated reason ADR-001 rejected
Tier-2 agent identity (a held `actor=app` token + webhook server). But it had never been
captured as its own decision — so it could be _invoked_ but not _revisited_. Open questions
about a CI/headless mode (NB-360, NB-379) make that gap material: the first time someone asks
"can backlogd run without a browser?", they need a decision to reopen, not a reflex to argue
with.

## Considered Options

Axes = the three legs the principle protects: **secret custody**, **who the actor is**, and
**operational surface** (does backlogd run infrastructure?).

| Option | Secret custody | Actor | Ops surface | Clean-room / IP-clean |
| --- | --- | --- | --- | --- |
| **A — Keyless / OAuth-as-user / no server** (today) | none held | the human user | none | ✅ nothing to leak |
| **B — Stored API keys** (per-user PAT in env/config) | backlogd holds a token | a bot, or ambiguous | none | ⚠️ secret in the tree/CI; custody burden |
| **C — Hosted service** (`actor=app` token + webhook server) | backlogd holds an app token | a backlogd app user | a running server | ❌ a different product to operate + secure |

- **A** — the runtime loop ships no API client and there is nothing to paste. Auth is the
  user's own OAuth session; backlogd never sees or stores a credential. This _is_ the
  current behaviour.
- **B** — buys headless/CI runs (no browser-OAuth step) but reintroduces secret custody into
  a public repo and muddies "who acted". Rejected for the runtime loop.
- **C** — the only path to first-class agent presence (see ADR-001 Tier 2), but it makes
  backlogd a hosted service with a held token and an exposed server. Out of scope by design.

## Decision

**Adopt Option A. The runtime loop is keyless, runs as the user via official OAuth paths,
and hosts no server.** Rationale:

- **No secret custody** — a public, clean-room repo with no stored token has nothing to leak
  and no key-rotation burden.
- **Runs as the user** — actions carry the user's own identity and permissions; backlogd
  grants itself nothing the user hasn't.
- **No ops surface** — nothing to deploy, monitor, or secure; the plugin is the whole system.

**Narrow, honest exception:** [`/backlogd:init`](../../guides/workspace-bootstrap.md)
(NB-371) — a **one-time, local** Linear Admin API key used by the setup engine to bootstrap a
fresh workspace (labels, states, templates). It is read only by that setup pass, never by the
orchestrator or any agent, and is **not** part of the runtime loop, which stays keyless after
setup. The exception is bounded precisely because the principle is otherwise absolute.

**Status: Accepted.** It is load-bearing and enforced today.

## Consequences

- **Enables:** the public, clean-room distribution model — install the plugin, sign in, go;
  no secret to provision, store, or rotate.
- **Forecloses:** anything needing a held credential or a daemon — notably Tier-2 agent
  identity (ADR-001) and any always-on background automation. Those require superseding this
  ADR, not working around it.
- **Constrains `/backlogd:init`:** the bootstrap key must stay one-time, local, setup-only —
  any drift toward the orchestrator reading it breaks this ADR.

**Conditions under which to reconsider (supersede, don't bend):**

1. A **CI / headless runner** with no interactive browser-OAuth path becomes a real
   requirement (open: NB-360, NB-379). A device-code or short-lived-token OAuth flow that
   keeps "runs as the user" while dropping the browser step would be the thing to evaluate —
   a stored long-lived PAT (Option B) would not, as it loses the actor and the custody win.
2. Official OAuth-as-user support is withdrawn from the Linear MCP or `gh`, forcing a
   different auth path.

Either trigger files a new ADR that sets `supersedes: ADR-002`; until then this stands.

---
_Refs: NB-377 · principle: [`README.md`](../../../README.md) + [`docs/conventions.md`](../../conventions.md) · related: [ADR-001](ADR-001-visible-agent-identity-in-linear.md) (Tier-2 rejection), `/backlogd:init` ([workspace-bootstrap](../../guides/workspace-bootstrap.md), NB-371) · open: NB-360, NB-379._
