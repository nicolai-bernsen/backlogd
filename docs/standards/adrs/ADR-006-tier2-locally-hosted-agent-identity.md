---
id: ADR-006
title: Tier-2 locally-hosted agent identity — actor=app via a local listener spawning the local CLI
status: Accepted
date: 2026-05-31
problem: NB-419
supersedes: ~
superseded-by: ~
assertion: backlogd's sanctioned always-on identity is Tier-2 run LOCALLY — a local listener daemon (launchd/systemd, never a cloud server) registered as an `actor=app` agent that acks each AgentSession within 10s with an immediate `thought` activity then async-spawns the local `claude` CLI; `actor=app` is a Linear-auth identity that requires NO Anthropic API key, so attended/individual + local CLI stays subscription-legitimate while only fully-unattended 24/7 use draws the API-key executor (a one-line config swap, default ships subscription/attended); the Tier-1 delegate work (NB-390/391/388) REMAINS the shippable-now first rung (identity without autonomy, no daemon); and no daemon is built until ONE spawned local CLI session is proven to auth as the actor=app identity, post an AgentActivity inside the 10s ack window, and run on subscription.
applies-to:
  domains: [agent-identity, linear, runtime, auth, hosting]
  file-patterns: ["**"]
  decision-types: [agent-identity, runtime-loop, hosting, secret-custody, executor]
---

**ADR-006 — Tier-2 locally-hosted agent identity: `actor=app` via a local listener spawning the local CLI**

- **Status:** Accepted _(2026-05-31)_ · **Problem:** NB-419
- **Decision (TL;DR):** adopt **Tier-2 run LOCALLY**. A **local listener daemon**
  (launchd/systemd on the user's own machine, **not** a cloud server) registers as an
  `actor=app` Linear agent, **acks each AgentSession within Linear's 10-second window** with
  an immediate `thought` activity, then **asynchronously spawns the local `claude` CLI** to
  do the work. `actor=app` is a **Linear-auth** identity and requires **no Anthropic API
  key** — so the **default** ships **subscription / attended** (subscription-legitimate);
  the API-key executor is the **one-line swap** for fully-unattended 24/7. This **supersedes
  [ADR-001](ADR-001-visible-agent-identity-in-linear.md) and
  [ADR-005](ADR-005-tokenless-bridge-local-cli-executor.md)** — both rejected Tier-2 on the
  premise that it required a _cloud_ server; the new evidence (a colleague's `actor=app`
  agent runs on a **local** listener) removes that premise. **Decision-only — ships no
  daemon, no OAuth registration, no runtime module; the build is gated on a proof
  (Consequences).**

> The identity decision that lifts the Tier-2 ban once the "cloud server" premise is shown
> false. Shape per [TEMPLATE](TEMPLATE.md): **Status · Context · Considered Options ·
> Decision · Consequences**. ADRs are immutable once Accepted — supersede, don't rewrite.
> This ADR is **docs/decision-only**: no build code ships here.

## Status

**Accepted** (2026-05-31). This is a **decision record** — it ships **no build code** (no
listener daemon, no `actor=app` OAuth registration, no webhook handler, no runtime module);
only this ADR, the two supersession edits to ADR-001/005, a light structural test, and the
regenerated [standards index](../index.json). It is Accepted (not Proposed) for one reason:
**marking ADR-001 and ADR-005 `Superseded by ADR-006` requires an Accepted superseder** (the
TEMPLATE lifecycle: a Proposed ADR cannot supersede an Accepted one). The PO has decided
**proceed** (see the Context's PO-decision finding); the PO **ratifies the two `[manual]`
framings** — the **billing split** (Decision → Billing split, AC#5) and the
**verify-before-build precondition** (Consequences → Build precondition, AC#8) — **at
review**.

It rests on, and revises, three standards:

- **[ADR-001](ADR-001-visible-agent-identity-in-linear.md)** (visible agent identity) —
  **superseded by this ADR.** It rejected Tier-2 because Tier-2 was read as requiring _a held
  `actor=app` token + a running **server**_ that "turns backlogd into a hosted service." The
  still-binding parts (Tier-0 comment badges; delegation is additive; the human stays
  `assignee`) are **carried forward** below.
- **[ADR-005](ADR-005-tokenless-bridge-local-cli-executor.md)** (tokenless bridge → local
  CLI) — **superseded by this ADR.** Its rejected Option C was a _hosted_ `actor=app` webhook
  service; that rejection stands for the **cloud** shape. Its still-binding parts (the
  **executor-swap seam**; the **subscription-legitimacy** framing of the local CLI; the
  honest 24/7 ceiling; deference to ADR-002) are **carried forward** below — Tier-2-local is
  the bridge's **local listener + identity layer**, not a contradiction of its executor.
- **[ADR-002](ADR-002-keyless-mcp.md)** (keyless / OAuth-as-the-user / no server) — **NOT
  superseded; it remains the binding constraint** and this ADR is engineered to stay inside
  it (see Decision → Reconciling ADR-002). The `actor=app` registration is a one-time,
  local, OAuth-as-the-user install (the same exception class as the `/backlogd:init` admin
  key), and the listener runs **on the user's own machine**, not as a backlogd-hosted public
  server.

## Context

The PO wants backlogd's agents to be **first-class, visible actors in Linear** — the "Kato"
experience: an agent that is **delegated** issues (human keeps `assignee`), narrates its work
through **AgentSessions / AgentActivities**, and shows up as a named app user. ADR-001
mapped that to **Tier 2** (full Agent Interaction Protocol) and **rejected it**, on the
explicit premise that Tier-2 needs _"a held `actor=app` token + a webhook **server**"_ that
breaks backlogd's **keyless / serverless / MCP-only** principle and "turns backlogd into a
hosted service." ADR-005 echoed the same rejection for its Option C ("hosted `actor=app`
webhook service").

**Both rejections rested on one assumption: that the `actor=app` listener must be a _cloud_
server.** That is the assumption this ADR re-examines.

### Verified finding — the PO/colleague diagnostic (AC#1, `[manual]`)

The deciding fact is a **PO-confirmed diagnostic**, recorded on this issue **before**
dispatch as the `**[backlogd]**` PO-decision comment (2026-05-31). Stated as a finding with
its in-repo locator (no web tools in this unit; the source is the PO's own comment, not a
fabricated URL):

- **Finding.** A colleague's `actor=app` agent ("Kato") runs its listener on **his own
  machine** — a laptop / local daemon plus a tunnel — **not** a hosted/cloud endpoint.
- **Source a reader can check.** The `**[backlogd]**` **PO-decision comment on NB-419**
  (2026-05-31): _"Kato's `actor=app` listener runs on his own machine (laptop / local daemon
  - tunnel), NOT a hosted/cloud endpoint. The load-bearing premise holds: a local listener
  is not a cloud server."_
- **As of.** 2026-05-31, PO-confirmed.

**Why this is the anchor.** It falsifies the single premise on which ADR-001 and ADR-005
rejected Tier-2. A **local listener is not a cloud server**: it runs on the user's machine,
under the user's control, like the local `claude` CLI ADR-005 already sanctions and the
local `/backlogd:init` install ADR-002 already allows as a setup-only exception. Tier-2 was
rejected as "a hosted service"; run **locally** it is not one. So the rejection no longer
holds, and Tier-2-local becomes reachable **without** breaking the principle — which is why
the PO decided **proceed**.

### The two-token distinction the rejection conflated (AC#2)

ADR-001's rejection silently bundled **two independent things** under "Tier 2 needs a key,"
and separating them is what unlocks the decision. There are **two distinct credentials**,
and Tier-2-local needs only the first:

- **Linear auth identity — `actor=app`.** The credential that makes the agent a **named app
  user** in Linear (so it can be a `delegate` target and drive AgentSessions/Activities).
  This is a **Linear OAuth `actor=app`** registration. It is **not** an Anthropic credential
  and has **nothing to do with model billing.**
- **Anthropic billing identity — subscription vs API key.** The credential that pays for
  **model inference**: either the user's **Pro/Max subscription** (via the local `claude`
  CLI, the first-party harness) **or** an **Anthropic API key** (the Agent SDK / `claude -p`,
  metered).

**`actor=app` does NOT require an Anthropic API key.** The `actor=app` token authenticates
the agent **to Linear**; the model is still run by the **local CLI under subscription OAuth**
(per ADR-005's still-binding executor). ADR-001 conflated "Tier-2 identity" with "Agent SDK
billing" and so read Tier-2 as inescapably off-subscription. It is not: the **identity**
(`actor=app`, Linear) and the **executor** (local CLI, subscription) are **orthogonal axes**.
This separation is what lets Tier-2 ship on subscription.

### What already exists in-repo (prior art this design reuses, does not rebuild)

- **[ADR-001](ADR-001-visible-agent-identity-in-linear.md)** — Tier-0 comment badges (live
  today) and the Tier-1 `delegate` analysis. The **transparency primitives** Tier-2 builds on.
- **[ADR-005](ADR-005-tokenless-bridge-local-cli-executor.md)** — the **local-CLI executor**,
  the **executor-swap seam**, the **"ordinary individual usage" ceiling**, and the
  idempotent-resume / batch-DAG / quota-guard machinery. Tier-2-local is the **listener +
  identity layer on top of that bridge**, not a replacement for it.
- **`scripts/graph.py`** — the keyless execution graph (dispatch outcomes/latency). Unchanged;
  still the inspection-pillar artifact.
- **[`skills/solve/capture.md`](../../../skills/solve/capture.md)** — the `STATUS:`-branch
  contract the spawned CLI still returns. The listener parses that same first line.
- **The Tier-1 work — [NB-390 / NB-391 / NB-388](https://linear.app/nicolai-bernsen/issue/NB-390)**
  (delegate pickup + the PO "delegated-to-agent" view). The **first rung**, shippable now,
  no daemon — reconciled in the Decision (AC#7), **not** discarded.

## Considered Options

The axis that decides it is **where the `actor=app` listener runs** (and therefore whether
Tier-2 breaks the keyless/serverless principle). The executor (local CLI vs API key) is a
**separate, orthogonal** axis already settled by ADR-005 and preserved here via the swap seam.

| Option | Identity | Where the listener runs | Subscription-legitimate (default)? | Honours ADR-002 (keyless / no _cloud_ server)? | Answers all of A1–A4 (pickup/review/route/blocker)? |
| --- | --- | --- | --- | --- | --- |
| **0 — Comment badges only** (ADR-001 Tier 0, today) | the human PO | n/a | ✅ yes | ✅ yes — _is_ the principle | ❌ informational only; no agent face |
| **1 — MCP `delegate`, no listener** (ADR-001 Tier 1; NB-390/391/388) | one installed app user, set via user-OAuth MCP | n/a (no daemon) | ✅ yes | ✅ yes — pure user-OAuth MCP | ~ partial — A1 pickup first-class; no Sessions/Activities |
| **2-cloud — hosted `actor=app` + webhook server** (ADR-001/005 rejected) | `actor=app` app user | a **cloud** server backlogd hosts | ❌ no (server-side SDK is API-billed) | ❌ no — held token **+ a hosted public server** | ✅ yes |
| **2-local — `actor=app` + LOCAL listener spawning the local CLI** (chosen) | `actor=app` app user | the **user's own machine** (launchd/systemd + tunnel) | ✅ **yes** — identity is Linear-auth; executor is the local CLI on subscription | ✅ **yes** — no cloud server; local install is the ADR-002 setup-only exception class | ✅ yes |

- **Tier 0 / Tier 1** — exactly as ADR-001 framed them. Tier 1 (the NB-390/391/388 work)
  buys A1 (pickup) as a first-class, filterable signal **with no daemon** — it remains the
  shippable-now first rung (AC#7).
- **Tier 2-cloud** — the shape ADR-001 and ADR-005 (Option C) rejected, and that rejection
  **stands**: a backlogd-hosted public server breaks ADR-002, and a server-side executor is
  API-billed. **Out of scope by standard.**
- **Tier 2-local** — the new option the PO diagnostic unlocks. Same protocol-complete
  identity as 2-cloud (answers A1–A4: pickup, review, route, blocker), but the listener runs
  **locally** (so no cloud server → no ADR-002 break) and the **executor is the local CLI**
  (so subscription-legitimate by default → no API key required for identity). The cost is a
  **local daemon to operate** and the **10-second AgentSession ack** the protocol demands
  (handled in the Decision), plus the honest **"ordinary individual usage" ceiling** carried
  forward from ADR-005.

## Decision

**Adopt Option 2-local. Status: Accepted.** backlogd's sanctioned always-on identity is
**Tier-2 run locally**: an `actor=app` agent whose listener runs on the **user's own
machine**, acking each AgentSession inside Linear's 10-second window and then spawning the
**local `claude` CLI** to do the work.

Tie-back to the constraint named in Context: 2-local is the **single** option that answers
**all four** transparency asks (A1 pickup · A2 review · A3 route · A4 blocker) **and** stays
inside ADR-002 — because the premise that forced "Tier-2 = hosted service" (a _cloud_ server)
is **false** for a local listener, and because the **identity** (`actor=app`, Linear-auth)
and the **executor** (local CLI, subscription) are **orthogonal**, so adopting the identity
does **not** drag in an API key.

The 8 ACs are facets of this one decision; each is addressed in a pointable section.

### Architecture — local listener daemon, 10s ack, async CLI spawn (AC#4)

The runtime shape:

1. **Local listener daemon — not cloud.** A long-lived process on the **user's own machine**,
   started by the OS service manager (**launchd** on macOS, **systemd** on Linux; the
   Windows-service equivalent where applicable). It receives Linear agent webhooks via a
   **tunnel** (e.g. an outbound tunnel that exposes a local port — the colleague's shape), so
   there is **no backlogd-hosted public cloud endpoint**. This is the load-bearing
   distinction: a daemon on your laptop is **not** a hosted service.
2. **Registered as `actor=app`.** The listener authenticates to Linear as a **Linear OAuth
   `actor=app`** agent (a one-time, local, OAuth-as-the-user install — see Reconciling
   ADR-002). This is what makes the agent a **delegate target** and lets it drive
   **AgentSessions / AgentActivities**. It is a **Linear** credential only (AC#2).
3. **Acks the AgentSession within 10 seconds.** Linear's Agent Interaction Protocol requires
   an AgentSession to receive an activity **within ~10 seconds** of being created, or it goes
   `stale`. The listener therefore **posts an immediate `thought` activity** (e.g. "picking
   this up…") **synchronously** on session create — cheap, no model call — to hold the
   session open, **then** does the slow work asynchronously. The ack is **decoupled** from
   the spawn.
4. **Async-spawns the local `claude` CLI.** After acking, the listener **asynchronously
   shells out to the official local `claude` CLI** (ADR-005's executor) running the existing
   `/backlogd:*` commands under the user's **subscription OAuth**. The CLI does the thinking;
   the listener narrates progress as AgentActivities and parses the returned `STATUS:` line
   (per [`skills/solve/capture.md`](../../../skills/solve/capture.md)) to transition Linear
   and write the graph edge. The listener itself **calls no model** (zero token cost), exactly
   as ADR-005's bridge.

**Single vs per-role agent identity — decision: ship ONE `actor=app` agent ("backlogd") for
v1; per-role is a deferred follow-up.** A single named agent answers all of A1–A4 (the
activity text and the role-prefixed comment already say _which role_ acted — scrum-master vs
developer vs reviewer), keeps the install to **one** OAuth registration, and is the smallest
shape that proves the protocol. **Per-role app users** (a `backlogd-developer`,
`backlogd-reviewer`, …) are a legitimate richer presence but multiply the install/operate
cost; they are **deferred** (Consequences → Follow-ups) until the single-agent shape is
proven. The decision today is **one agent**; revisiting it is a follow-up, not a new ADR.

### The two tokens, stated explicitly (AC#2)

To prevent the conflation ADR-001 made from recurring, the binding statement:

- **`actor=app` = Linear auth identity.** It authenticates the agent **to Linear** as a named
  app user. **It does NOT require an Anthropic API key.** It says nothing about who pays for
  inference.
- **Subscription vs API key = Anthropic billing identity.** A **separate** credential, on a
  **separate** axis, that decides **how model inference is paid for** — the local CLI's
  **subscription OAuth** (default) or an **Anthropic API key** (the swap target).

Tier-2-local holds the **`actor=app` Linear token** and runs the model on the **subscription
CLI**. The API key enters **only** if the operator deliberately swaps the executor (next two
sections).

### Billing split — stated honestly (AC#5, `[manual]`)

The honest position on what is subscription-legitimate and what is not:

- **Attended / individual + local CLI = subscription-legitimate.** A human is in the loop
  (triggering bounded batches, present at the cadence ADR-005's "ordinary individual usage"
  guard describes), and the executor is the **local `claude` CLI** on the user's **Pro/Max
  subscription**. This is the **default** Tier-2-local ships. The `actor=app` identity does
  **not** change the billing here — it is a Linear credential; the model still runs on
  subscription.
- **Fully-unattended 24/7 = the API-key executor.** A continuously-running, no-human-in-the-
  trigger-seat loop is **precisely the pattern that trips the "ordinary individual usage"
  ceiling and the abuse classifier** (ADR-005's carried-forward finding). True 24/7 autonomy
  therefore belongs to the **API-key executor** — with its **metered billing** and, because
  that backend reintroduces a held key in the loop, **an ADR-002 supersession** (carried
  forward from ADR-005). backlogd does **not** market beach-mode it cannot legitimately
  deliver on a subscription.
- **Default ships subscription / attended.** Out of the box, Tier-2-local is attended +
  local-CLI + subscription. The API-key / 24/7 path is an opt-in the operator chooses with
  full knowledge of its cost and its ADR-002 consequence. _(PO ratifies this framing at
  review.)_

### Executor-swap seam — preserved from ADR-005, one config line (AC#6)

The **executor-swap seam from ADR-005 is preserved unchanged**: the executor remains an
interface with one method ("run problem `X` in worktree `W`, return a `STATUS:`-shaped
result"), selected by **one config value**:

```yaml
# backlogd Tier-2-local listener config (illustrative — no runtime code ships in this issue)
executor: local-cli      # subscription-legitimate (default): listener spawns `claude`
# executor: api-sdk      # one-line swap → Agent SDK / API key, for fully-unattended 24/7
```

Swapping `local-cli` → `api-sdk` is a **one-line change**; the listener, the `actor=app`
identity, the AgentSession ack, the worktree ownership, the graph writes, and the Linear
transparency are **executor-agnostic** and do **not** change. The seam matters for the same
reason ADR-005 gave: the Anthropic ToS line **moved twice in Q1 2026** and a metered-credit
change is scheduled (2026-06-15), so if the subscription-CLI position shifts the framework
**survives without a rewrite**. As in ADR-005, selecting `api-sdk` in the always-on loop is a
**user choice with cost consequences** and **requires superseding
[ADR-002](ADR-002-keyless-mcp.md)** (the seam exists so the _code_ survives, not so the
_keyless principle_ is quietly bent). Crucially: the swap is on the **executor (billing)**
axis only — it does **not** touch the **`actor=app` identity** axis, which stays put.

### Reconciling Tier-1 — it REMAINS the first rung (AC#7)

The Tier-1 `delegate` work — **[NB-390 / NB-391 / NB-388](https://linear.app/nicolai-bernsen/issue/NB-390)**
(delegate pickup + the PO "delegated-to-agent" view) — **remains the first rung and is NOT
superseded as work to do.** Recommendation: **keep it.**

- **Tier 1 = identity without autonomy, shippable now, no daemon.** It buys A1 (first-class,
  filterable pickup signal) through **pure user-OAuth MCP**, with **no listener, no
  `actor=app` token, no server**. It ships today and is valuable on its own.
- **Tier 2 = the listener + autonomy on top.** Tier-2-local **adds** the `actor=app` listener
  (full Sessions/Activities → A2/A3/A4) and the async CLI spawn (autonomy) **on top of** the
  Tier-1 foundation. Tier 1 is the **identity** floor; Tier 2 adds **presence + autonomy**.
- They are **complementary rungs of one ladder, not competing options.** Shipping Tier 1 now
  is the right move; Tier-2-local is the next rung, gated on the build proof below. This ADR
  does **not** halt or rewind NB-390/391/388.

### Reconciling ADR-002 — why this stays inside keyless/serverless

Tier-2-local is engineered to honour **[ADR-002](ADR-002-keyless-mcp.md)**, which is **not**
superseded:

- **No backlogd-hosted server.** The listener runs on the **user's own machine** (launchd/
  systemd + tunnel). ADR-002 forbids a _backlogd-hosted_ server; a daemon on the user's own
  laptop, under the user's control, is **not** that — it is the same locality as the local
  `claude` CLI ADR-005 already sanctions.
- **The `actor=app` install is the setup-only exception class.** Registering the `actor=app`
  agent is a **one-time, local, OAuth-as-the-user** install — the same exception class
  ADR-002 already carves out for the `/backlogd:init` admin key (local, setup-only, never
  read by the orchestrator at runtime). The runtime loop still holds **no Anthropic key**
  (default executor = subscription CLI), reaches Linear via official OAuth-as-the-user, and
  the inference cost stays on subscription.
- **The keyless principle is preserved on the executor axis.** Because identity and executor
  are orthogonal, adopting `actor=app` does **not** introduce an Anthropic API key. The only
  thing that would (the `api-sdk` swap) **explicitly requires superseding ADR-002** —
  unchanged from ADR-005.

If a future build discovers the **only** viable local-listener registration requires a
**held long-lived key in the runtime loop** or a **backlogd-hosted public server**, it does
**not** proceed without **superseding ADR-002** first. ADR-002 is the constraint; this
decision does not bend it.

### Superseding ADR-001 and ADR-005 — what changed (AC#3)

Per the TEMPLATE lifecycle, this ADR **explicitly supersedes** both, stating **what changed**
and **carrying forward what still binds** (supersede, don't silently contradict; don't drop a
live rule):

- **ADR-001 → `Superseded by ADR-006`.** **What changed:** ADR-001 rejected Tier-2 on the
  premise that it requires a _cloud_ server + held token that "turns backlogd into a hosted
  service." The PO/colleague diagnostic (Context) shows the listener runs **locally**, so
  that premise is false and the rejection no longer holds. **Carried forward (still binding):**
  Tier-0 comment badges and **role-prefixed `**[backlogd <role>]**` comments** remain the
  baseline transparency surface; **delegation is additive — the human stays `assignee`**, the
  agent is only the `delegate`; Tier-2-**cloud** stays rejected.
- **ADR-005 → `Superseded by ADR-006`.** **What changed:** ADR-005's Tier-1.5 transparency
  ceiling ("explicitly **not** Tier-2") is lifted to **Tier-2-local**, now that the local
  listener is shown not to be the hosted server its Option C rejected. **Carried forward
  (still binding):** the **local-CLI executor** (the listener spawns `claude`, not the SDK);
  the **executor-swap seam** (one config line; `api-sdk` ⇒ ADR-002 supersession); the
  **subscription-legitimacy** framing and the honest **"ordinary individual usage" / no-
  beach-mode-on-subscription** ceiling; deference to **ADR-002** as the binding constraint.
  ADR-005's Option C (**hosted** webhook service) **stays rejected** — Tier-2-local is its
  **local** sibling, not Option C.

Mechanically: each old ADR's front-matter `status:` flips to `Superseded by ADR-006`, its
`superseded-by:` is set to `ADR-006`, and a one-line reason (the local-listener evidence) is
added to its `## Status` — **bodies otherwise unchanged** (superseding is additive history,
not a rewrite). This ADR's `supersedes:` stays `~` only because the front-matter schema holds
a single value; both supersessions are recorded here in prose and in each old ADR's
`superseded-by:`. _(See Consequences for the index regeneration that reflects the new
statuses.)_

## Consequences

What becomes true once this is in force (it changes a decision + two statuses, not runtime
behaviour):

- **Tier-2 is no longer banned — run locally.** A protocol-complete, A1–A4-answering agent
  identity is **sanctioned** as the always-on target, provided its listener runs **locally**.
  Tier-2-**cloud** (a backlogd-hosted server) remains **rejected**; the ban narrowed from
  "Tier 2" to "Tier 2 hosted in the cloud."
- **ADR-001 and ADR-005 are Superseded** (kept for history); the **standards index reflects
  both as `Superseded`** and adds ADR-006. A reviewer reading the index now sees ADR-006 as
  the live identity standard and ADR-001/005 as superseded history.
- **The default stays subscription/attended and keyless** — `actor=app` adds a **Linear**
  credential only; the runtime loop holds no Anthropic key by default; the API-key/24/7 path
  is an explicit opt-in carrying an ADR-002 supersession.
- **Tier 1 (NB-390/391/388) is unaffected as work** — it remains the shippable-now first rung;
  Tier-2-local builds on top of it, it does not replace it.

### Build precondition — prove ONE session before building the daemon (AC#8, `[manual]`)

**No daemon, no `actor=app` registration code, and no runtime module is built by this issue,
and none is built downstream until a one-session proof passes first.** This is the
**NB-368 verify-before-build discipline**, stated as a hard gate (this ADR _states_ it; the
proving happens in the downstream build issues, **not** here):

> **Precondition for any BUILD.** Prove that **ONE** spawned local `claude` CLI session can:
> **(a)** authenticate as the **`actor=app`** identity (the listener can register and act as
> the named Linear app user); **(b)** post an **AgentActivity within Linear's 10-second ack
> window** (the immediate-`thought`-then-async-spawn shape actually holds the session open);
> and **(c)** run on **subscription** (the executor is the local CLI on Pro/Max, no API key) —
> **BEFORE** building the listener daemon. If any of (a)/(b)/(c) fails, the daemon is **not**
> built on this design; the finding is recorded and the decision is revisited (a new ADR if
> needed). _(PO ratifies this gate at review.)_

**Follow-ups** (file on Accept; each a file-able problem — **none started by this ADR**):

1. **The one-session proof (AC#8 gate)** — a thin spike proving (a) `actor=app` auth, (b) a
   sub-10s AgentActivity ack, (c) subscription execution, for a **single** spawned CLI
   session. **Blocks all daemon work.**
2. **Build the local listener daemon** — launchd/systemd service + tunnel + the
   immediate-`thought`-ack + async CLI spawn + `STATUS:` parse + graph write. **Blocked by #1**;
   reuses ADR-005's bridge (executor, swap seam, resume, quota guard).
3. **Single → per-role agent identity** — revisit whether to register per-role `actor=app`
   app users once the single-agent shape is proven. _(deferred decision, not a new ADR yet.)_
4. **Keep / ship Tier 1 (NB-390/391/388)** — unchanged by this ADR; the first rung proceeds on
   its own track.

If reversed (a future ADR supersedes this): the sanctioned identity would revert toward
Tier-0/Tier-1, or to Tier-2-cloud under an ADR-002 supersession. Until then, Tier-2-local is
the identity of record — **un-built**, gated on the one-session proof.

---
_Refs: NB-419 · supersedes [ADR-001](ADR-001-visible-agent-identity-in-linear.md) (Tier-2 rejected on the cloud-server premise) + [ADR-005](ADR-005-tokenless-bridge-local-cli-executor.md) (Tier-1.5 ceiling; local-CLI executor + swap seam carried forward) · binding constraint: [ADR-002](ADR-002-keyless-mcp.md) (keyless / no hosted server — NOT superseded) · Tier-1 first rung: NB-390 / NB-391 / NB-388 · prior art: [`scripts/graph.py`](../../../scripts/graph.py), [`skills/solve/capture.md`](../../../skills/solve/capture.md) · discipline: NB-368 (verify-before-build) · source: the PO-decision comment on NB-419 (2026-05-31, Kato local-listener diagnostic — local daemon + tunnel, not cloud); Linear Agent Interaction Protocol (AgentSession 10-second ack, AgentActivities, actor=app delegation — verify the live ack window before relying on it)._
