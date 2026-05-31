---
id: ADR-005
title: Tokenless bridge drives the local claude CLI; SDK is the swap-only fallback
status: Superseded by ADR-006
date: 2026-05-31
problem: NB-379
supersedes: ~
superseded-by: ADR-006
assertion: An always-on backlogd runtime is a tokenless bridge (plain TS/Python, zero Claude inference) that drives the official local `claude` CLI under subscription OAuth and writes transparency via the Linear MCP — never the Agent SDK / `claude -p`; the executor is a one-line config swap to an API-key backend so a ToS shift survives without a rewrite; the human stays trigger/cadence-setter (bounded batches, no 24/7 swarm) and this remains a GO-to-explore design that ships no runtime code and does not proceed to a build until NB-376/ADR-004 is honoured and the keyless constraint of ADR-002 holds.
applies-to:
  domains: [runtime, auth, dependencies, linear, agent-identity, scrum]
  file-patterns: ["**"]
  decision-types: [runtime-loop, hosting, dependency, secret-custody, executor]
---

**ADR-005 — Tokenless bridge drives the local `claude` CLI; SDK is the swap-only fallback**

- **Status:** Superseded by [ADR-006](ADR-006-tier2-locally-hosted-agent-identity.md) _(2026-05-31; proposed 2026-05-30)_ · **Problem:** NB-379
- **Decision (TL;DR):** an always-on backlogd loop is a **tokenless bridge** — plain
  TS/Python that holds **no key and calls no model** — which polls Linear for ready
  problems, owns git/worktree, and **dispatches the official local `claude` CLI** running
  the existing `/backlogd:*` commands under the user's **subscription OAuth**. The expensive
  inference stays on subscription via the CLI; the automation layer costs **zero tokens**
  because it calls no model. The executor is a **one-line config swap** to an API-key
  backend, so a moving ToS line survives without a rewrite. This is a **design spike → ADR**
  — it **ships no runtime code**.

> Spike output for NB-379, the always-on-runtime exploration that
> [ADR-004](ADR-004-backlogd-identity.md) greenlit (GO-to-explore) under
> [ADR-002](ADR-002-keyless-mcp.md)'s keyless flip-condition. Shape per the
> [TEMPLATE](TEMPLATE.md): **Status · Context · Considered Options · Decision ·
> Consequences**. ADRs are immutable once Accepted — supersede, don't rewrite.

## Status

**Superseded by [ADR-006](ADR-006-tier2-locally-hosted-agent-identity.md)** (2026-05-31).
ADR-006 lifts this ADR's **Tier-1.5 transparency ceiling** ("explicitly **not** Tier-2"):
the NB-419 PO/colleague diagnostic shows the `actor=app` listener runs **locally** (a local
daemon + tunnel, not a cloud server), so Tier-2 **run locally** — which this ADR's Option C
rejected only as a _hosted_ webhook service — is now the sanctioned identity. The
still-binding parts of this ADR — the **local-CLI executor**, the **executor-swap seam**
(one config line; `api-sdk` ⇒ ADR-002 supersession), the **subscription-legitimacy** framing
and the honest **"ordinary individual usage" / no-beach-mode-on-subscription** ceiling, and
deference to **ADR-002** — are **carried forward** into ADR-006, which is the local listener +
identity layer _on top of_ this bridge. Option C (the **hosted** webhook service) stays
rejected. Body retained unchanged for history per the TEMPLATE lifecycle.

**Proposed** (2026-05-30). This is a **design-only** spike awaiting PO accept; it ships **no
runtime code** (no bridge implementation, no `package.json`, no executable — only this ADR
and the regenerated standards index). It records a decision and a fork-vs-build
recommendation; it does **not** start the build.

It rests on two Accepted standards and one gate:

- [ADR-004](ADR-004-backlogd-identity.md) (identity) rendered **GO to _explore_** an
  always-on runtime, with a **binding flip condition**: a build proceeds **only if** it
  preserves the keyless / runs-as-the-user principle.
- [ADR-002](ADR-002-keyless-mcp.md) (keyless / OAuth-as-user / no server) is **the binding
  constraint** on any always-on design; this ADR is engineered to stay inside it (no held
  key in the runtime loop, no backlogd-hosted server).
- **NB-376 differentiator gate.** Build-vs-no-build defers to ADR-004; this spike does
  **not** start runtime implementation until ADR-004 (which fixed the NB-376 decision and is
  now Accepted) is honoured — and it is, as a _GO-to-explore_, not a GO-to-build. See
  the Decision's **Scope & gating** section (AC #1, #13).

## Context

backlogd wants the loop **"PO brainstorms → the team picks up new problems → works
independently → visible in Linear"** to run **without a paid SaaS** and **without API-rate
billing**. That needs an always-on-ish bridge. The naive build — fork
[Cyrus](https://github.com/ceedaragents/cyrus) and reuse its runtime — embeds the **Claude
Agent SDK**, and the Agent SDK **requires an API key**: subscription (Pro/Max) OAuth is
**prohibited** with the SDK, and that prohibition was **enforced** in Feb 2026. So the build
that looks easiest is the one that takes backlogd off-subscription and onto metered API
billing — exactly what this design must avoid.

The deciding question is therefore **not** "poll or webhook" or "TS or Python" — those are
secondary. It is **what executes the work**: an **SDK-embedded** runner (API key) versus the
**official local `claude` CLI** (subscription-legitimate). Everything else hangs off that.

### Verified finding — the ToS constraint that anchors the design (AC #3, #4)

These are the subscription-legitimacy facts the whole design rests on. They are stated as
findings with **named, checkable sources** (this spike has **no web tools**; sources are
named with date + locator so a reader can verify them — no fabricated URLs). Where a source
moves, the **executor-swap seam** (in the Decision below) is the mitigation.

| Finding (the claim the design rests on) | Source a reader can check | As of |
| --- | --- | --- |
| **The Agent SDK / `claude -p` headless mode requires an API key.** Programmatic SDK use authenticates with an Anthropic **API key**, not a Pro/Max subscription session. | Anthropic developer docs: **"Claude Agent SDK" / "Claude Code SDK"** (authentication / getting-started — API-key setup); Anthropic **Commercial Terms of Service** (API products). | 2026-05-30 |
| **Subscription OAuth is _prohibited_ with the SDK**, and the prohibition was **enforced** — third-party tools relaying Pro/Max OAuth tokens into SDK/headless flows were **blocked**. | The **Feb 2026 enforcement reports** on the OpenClaw / OpenCode / Goose subscription-token blocks (community + tool changelogs documenting the cut-off); Anthropic **Usage Policy** / **Consumer Terms** (subscription is for interactive first-party use). | Feb 2026 |
| **An _announced/scheduled_ change: from June 15 2026, even subscription programmatic use draws from a _separate metered Agent-SDK credit_** (i.e. SDK use is metered, distinct from the interactive subscription allowance). **Today is 2026-05-30 — this is not yet in effect.** | Anthropic's **announced June 15 2026 Agent-SDK metered-credit change** (Anthropic announcement / changelog; verify the live date + terms before relying on it). | announced; effective **2026-06-15** |
| **The official Claude Code CLI on your own machine is subscription-legitimate, including scripted use** — it is the official first-party harness — **but bounded by "ordinary individual usage"** (the subscription's 5-hour rolling + weekly caps; an unattended swarm trips the abuse classifier). | Anthropic **Help Center: "Using Claude Code with a Pro/Max subscription"** (what the subscription covers); Anthropic **Usage Policy** ("ordinary individual usage", anti-abuse). | 2026-05-30 |

**Why this is the anchor.** The first two findings make the SDK path **off-subscription by
construction** — it cannot run on Pro/Max without violating the terms that were actively
enforced. The fourth makes the **local CLI** path subscription-legitimate **for scripted
use**, with a real ceiling. The third is the reason the design must not over-fit to today's
exact line: the terms have **moved twice in Q1 2026** and a metered-credit change is already
scheduled, so the executor must be **swappable** (AC #5).

### What already exists in-repo (prior art the design reuses, does not rebuild)

- **`scripts/graph.py`** — the keyless, zero-dep **execution graph** (NB-263/NB-320): records
  `dispatch_started` / `dispatch_completed{outcome}` edges and answers `run-status` per
  problem. The bridge's "record outcome → execution graph" requirement is **this**, not a new
  store.
- **[`skills/solve/resume.md`](../../../skills/solve/resume.md)** — the four-source reconcile
  (Linear + remote git + local git/worktree + graph) with a 4-state decision table. The
  bridge's idempotent-resume requirement (AC #10) **is** this reconcile, lifted to bridge
  start-up.
- **[`skills/solve/capture.md`](../../../skills/solve/capture.md)** — the deterministic
  `STATUS:`-branch table (`DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT`). The bridge
  parses **that same first line**; `DONE_WITH_CONCERNS` already carries the
  developer's surfaced-assumptions/concerns forward (AC #9).
- **[ADR-001](ADR-001-visible-agent-identity-in-linear.md)** — Tier-0 comment badges today;
  **Tier-1** (MCP `delegate`, no server) is the gated experiment; **Tier-2** (`actor=app`
  token + webhook server) is rejected. Transparency (AC #11) lives at **Tier 1.5** — Tier-0
  badges plus the gated Tier-1 `delegate` — and explicitly **not** Tier 2.
- **[ADR-002](ADR-002-keyless-mcp.md)** + **[ADR-004](ADR-004-backlogd-identity.md)** — the
  keyless constraint and the GO-to-explore that bound this entire spike.

## Considered Options

The axis that decides it is **what executes the work** (and therefore which auth applies).
Secondary axes — poll vs webhook, hosted vs local — are settled in the **Decision** once the
executor is chosen.

| Option | Executor | Auth | Subscription-legitimate? | Token cost of automation | Honours ADR-002 (keyless/no-server)? |
| --- | --- | --- | --- | --- | --- |
| **A — Tokenless bridge → local `claude` CLI** (chosen) | official local `claude` CLI | the user's **subscription OAuth** (already on the machine) | ✅ yes — official first-party harness, scripted use allowed, bounded by "ordinary individual usage" | **zero** — the bridge calls no model | ✅ no held key in the loop, no backlogd server |
| **B — Fork Cyrus / embed the Agent SDK** | Agent SDK in-process | an **Anthropic API key** | ❌ no — subscription OAuth prohibited with the SDK (enforced Feb 2026); metered from 2026-06-15 | n/a (metered API billing) | ❌ requires a held key — would have to **supersede ADR-002** |
| **C — Hosted `actor=app` webhook service** | server-side runner | a held **app token** + API key | ❌ no — server-side SDK is API-billed | n/a | ❌ held token **+ a running server** — the Tier-2 thing ADR-001/002 reject |

- **A** — the bridge is plain code; the model only ever runs inside the **official CLI**
  the user already authenticates interactively. Subscription stays the billing path;
  automation is free. The cost is the **"ordinary individual usage" ceiling** (handled by
  the guard, AC #6) and that scripted-CLI legitimacy is a documented-but-evolving position
  (handled by the swap seam, AC #5).
- **B** — the easy fork, and the trap: the SDK's API-key requirement takes backlogd
  **off-subscription** and reintroduces the secret custody ADR-002 forbids. It is kept only
  as the **swap target** (AC #5) for the day someone _chooses_ API billing.
- **C** — the "Kato" hosted-agent shape; already rejected by ADR-001 (Tier 2) and ADR-002
  (no server). Out of scope by standard.

## Decision

**Adopt Option A. Status: Proposed** (this spike recommends A; the PO accepts it). The
always-on runtime is a **tokenless bridge driving the official local `claude` CLI**. Tie-back
to the constraint named in Context: only Option A keeps backlogd **on subscription** (the
local CLI is the legitimate first-party harness) **and** inside [ADR-002](ADR-002-keyless-mcp.md)
(no held key in the loop, no server) — A is the **single** option that satisfies both at once.

The 13 ACs are all facets of this one decision. Each is addressed in a pointable section
below.

### The tokenless bridge — plain code, zero inference (AC #2)

The bridge is a **plain TS/Python process** with **no Claude inference** — it calls **no
model** and holds **no key**. Its loop:

1. **Detect ready problems.** Read Linear for issues that are `problem`-labelled **and**
   ready (unblocked, in the pickup state) — via the official Linear MCP / Linear's read API
   under the **user's** OAuth. Default to **polling** (simple, keyless, no inbound surface);
   a **tunnelled webhook** is an optional latency optimisation, never a backlogd-hosted
   public server (that would be the ADR-001/002 Tier-2 line). Polling is the
   ADR-002-safe default.
2. **Own git / worktree-per-issue.** One worktree + branch per problem
   (`backlogd-wt-{identifier}`, branch `nicolaibernsen/nb-<n>-<slug>`), exactly the isolation
   `skills/solve/walk.md` + `skills/worktree-isolation/SKILL.md` already define. The bridge
   owns the filesystem plumbing; it does not own the _thinking_.
3. **Dispatch the executor** (next section) — hand the picked problem to the local `claude`
   CLI running the existing `/backlogd:*` commands.
4. **Record the outcome → state + execution graph.** Parse the executor's `STATUS:` line
   (per [`skills/solve/capture.md`](../../../skills/solve/capture.md)), transition Linear
   accordingly, and write a `dispatch_completed{outcome}` edge to the existing
   **`scripts/graph.py`** execution graph. **No new store** — the graph is the
   inspection-pillar artifact ADR-004 already names.

Because every step is "read Linear / run git / shell out to a CLI / write a JSON edge / call
the Linear MCP", **the bridge itself spends zero Claude tokens**. All inference cost is on
the subscription, inside the CLI.

### Local-CLI executor, not the SDK (AC #3) — the binding rationale (AC #4)

The work runs by the bridge **shelling out to the official `claude` CLI** under the user's
subscription OAuth (the session already on the machine), running the same `/backlogd:*`
commands a human runs interactively. It does **not** embed the Agent SDK and does **not**
call `claude -p` headless.

The **binding rationale** is the cited finding in the Context's **Verified finding** table:
the **SDK / `claude -p` requires an API key and prohibits subscription OAuth** (enforced Feb
2026; metered from the announced 2026-06-15 change), whereas the **official local CLI is the
subscription-legitimate first-party harness, scripted use included**. That single ToS
finding is _why_ the executor is the CLI and not the SDK — not a preference, a terms
constraint.

### Executor-swap seam — one line (AC #5)

The executor is an **interface with one method** ("run problem `X` in worktree `W`, return a
`STATUS:`-shaped result"), selected by **one config value**:

```yaml
# backlogd bridge config (illustrative — no runtime code ships in this issue)
executor: local-cli      # subscription-legitimate (default): shells out to `claude`
# executor: api-sdk      # one-line swap → Agent SDK / API key, if the user CHOOSES API billing
```

Swapping `local-cli` → `api-sdk` is a **one-line change**; the bridge, the worktree
ownership, the graph writes, and the Linear transparency are **executor-agnostic** and do not
change. This matters because the ToS line **moved twice in Q1 2026** and a metered-credit
change is already scheduled (2026-06-15): if the subscription-CLI position shifts, the
framework **survives without a rewrite** — the user flips one value and accepts API billing,
rather than backlogd being rebuilt. Note the swap is a **user choice with cost
consequences**, and the `api-sdk` backend reintroduces a held key — so **selecting it in the
always-on loop requires superseding [ADR-002](ADR-002-keyless-mcp.md)** (the swap seam exists
so the _code_ survives, not so the _keyless principle_ is quietly bent).

### "Ordinary individual usage" guard — human as trigger (AC #6, `[manual]`)

The honest ceiling, stated plainly: the subscription covers **"ordinary individual usage"**
(the 5-hour rolling + weekly caps; an unattended swarm trips the **abuse classifier** — see
the cited Help Center / Usage Policy finding). So the design keeps the **human as the
trigger and cadence-setter**: the human **hits go on a bounded batch** (e.g. "work these N
ready problems now"), and the bridge processes that batch and **stops**. It is **always-on-ish**
(ready to run when triggered), **not** an unattended 24/7 swarm.

**Beach-mode auto-resolve — explicitly out of scope on subscription.** A continuously-running
loop that picks up and resolves problems with no human in the trigger seat is **out of
scope** for the subscription executor: it is precisely the pattern that trips the
"ordinary individual usage" ceiling and the abuse classifier. The honest position is that
true 24/7 autonomy belongs to the **API-key executor** (Option B, the swap target) **with
its metered billing and an ADR-002 supersession** — not to a subscription pretending to be a
server. Stating this ceiling honestly is the point: backlogd does not market beach-mode it
cannot legitimately deliver on a subscription.

### Batch DAG before dispatch — improvement 2 (AC #7)

Before dispatching a triggered batch, the scrum-master **builds the inter-problem dependency
graph across the whole new batch** — not just within a single problem. It reads `blocked-by`
/ `blocks` relations across the ready set, topologically orders them, and **surfaces
load-bearing architectural choices up front** (e.g. "problems 3, 5, 7 all touch the auth
seam — decide it once before any of them dispatch"). This lifts the existing per-problem
decomposition (`/backlogd:scope`) to **batch scope**, so a cross-cutting decision is made
**once, before** N agents each invent a divergent answer. The DAG also feeds dispatch order
(respect `blocked-by`) and the **idempotent-resume** reconcile (below).

### Quota / budget guard — improvement 3 (AC #8 → numbered #3)

The bridge **checks remaining quota before and during a batch** (e.g. reading the
subscription usage signal that the CLI's `/usage` view reflects) and **throttles or refuses**
rather than blowing a weekly cap. Two reasons, both real: **cost/limit** (don't exhaust the
window mid-batch and strand work) and **classifier safety** (a sudden burst is exactly the
abuse signal the **"ordinary individual usage" guard** (above) warns about). The guard is a
pre-dispatch gate per unit: if projected usage would breach the
cap, the bridge **pauses the batch and surfaces it to the PO** rather than pushing through.
This is plain bridge logic — reading a usage signal is **not** model inference, so it adds
**zero** token cost.

### Confidence + assumptions channel — improvement 4 (AC #9 → numbered #4)

The developer returns **more than solved/blocked/partial**: it **surfaces the assumptions it
made** ("assumed X because the problem didn't say") as a first-class **elicitation** back to
the PO. This is the partial-close on **confidently-wrong-but-passing** work — the increment's
tests are green, but it rested on an unstated assumption the PO should confirm. The
mechanism **already exists** in [`skills/solve/capture.md`](../../../skills/solve/capture.md):
`DONE_WITH_CONCERNS` carries the developer's `Concerns:` block forward into the PO solution
brief under _Needs your eyes_. This ADR records that the bridge **must preserve and surface**
that channel (the surfaced-assumption is a PO elicitation, not a silent pass), so an
always-on batch never buries a confidently-wrong increment behind a green check.

### Idempotent resume — improvement 5 (AC #10 → numbered #5)

On start-up the bridge **reconciles before it dispatches**: it reads **Linear state + branch
HEAD + worktree (+ the execution graph)** and resumes from the first un-completed unit,
rather than re-running completed work or stranding in-flight work. This **is** the
four-source reconcile already specified in
[`skills/solve/resume.md`](../../../skills/solve/resume.md) (the 4-state table:
`completed` / `in-progress-mine` / `untouched` / `inconsistent`), lifted from a `/backlogd:solve`
re-run to **bridge start-up**. A unit the graph + Linear both mark done is **skipped**; an
in-flight unit is **resumed** in its existing worktree; an inconsistency **pauses and
surfaces** rather than guessing. This is the explicit guard against the **daily.dev
CWD-session-key failure** (a fixed session key that mis-resumes the wrong working dir):
backlogd keys resume on **issue id + worktree path + graph edges**, never an ambient CWD.

### Transparency via MCP — NB-370 Tier 1.5 (AC #11)

Visible agent identity uses the **MCP `delegate` field + role-prefixed comments** — and
**no `actor=app` webhook server** (which would force the SDK/server billing this whole ADR
avoids). This is **Tier 1.5**: **Tier-0** comment badges (live today —
`**[backlogd <role>]**`-prefixed comments) **plus** the **gated Tier-1** `delegate` write
([ADR-001](ADR-001-visible-agent-identity-in-linear.md)), and explicitly **not Tier-2**.
That aligns exactly with NB-370 / ADR-001's recommendation: the `delegate` write is pure
user-OAuth MCP, the human stays `assignee`, and there is no held token and no server. The
transparency story is therefore **fully inside ADR-002** — the bridge writes who-did-what via
the same official MCP a human uses, holding nothing.

### Fork-vs-build call (AC #12)

Recommendation: **reuse Cyrus's _ideas_, write the bridge _fresh_, and do NOT fork its SDK
runtime.**

| Cyrus element | Call | Why |
| --- | --- | --- |
| **Worktree-per-issue** | **Reuse the idea** | Sound isolation model; backlogd already implements its own (`skills/solve/walk.md`, `skills/worktree-isolation/SKILL.md`). |
| **Session continuity** (resume an interrupted unit) | **Reuse the idea** | Maps onto backlogd's existing four-source reconcile ([`skills/solve/resume.md`](../../../skills/solve/resume.md)); take the concept, not the code. |
| **EdgeWorker-style routing** (issue-event → handler) | **Reuse the idea** | The poll/route shape is useful; backlogd's router is the scrum-master + `/backlogd:scope` dispatch, not Cyrus's. |
| **The Agent SDK runtime** (the in-process executor) | **Do NOT fork** | This is the off-subscription, API-key trap (Option B). Forking it is what NB-379 exists to **avoid**. |

This is consistent with [ADR-004](ADR-004-backlogd-identity.md)'s explicit non-goal — backlogd
**does not rebuild Cyrus's runtime plumbing**. The fresh-written part is exactly the
**tokenless CLI-driving bridge**; everything reusable is an _idea_ already realised in
backlogd's own keyless code.

### Scope & gating — no runtime code this issue (AC #1, #13)

- **AC #1 — ADR artifact lands.** The spike output is **this committed ADR**
  (`docs/standards/adrs/ADR-005-tokenless-bridge-local-cli-executor.md`), recording the
  decision (tokenless bridge + local-CLI executor), the binding rationale (the cited
  SDK-vs-CLI ToS finding), the ToS citations, and the fork-vs-build recommendation. **Design
  only — no runtime code is shipped by this issue.**
- **AC #13 — respects the NB-376 differentiator decision (`[manual]`).** Build-vs-no-build
  defers to [ADR-004](ADR-004-backlogd-identity.md) (which fixed the NB-376 decision). This
  spike is a **GO-to-explore**, **not** a GO-to-build: it **does not start runtime
  implementation**. No bridge code, no `package.json`, no executable ships here — only this
  ADR + the regenerated [standards index](../index.json). A build proceeds **only** under
  ADR-004's flip condition (keyless preserved) and, if it ever selects the `api-sdk`
  executor in the always-on loop, **only after superseding [ADR-002](ADR-002-keyless-mcp.md)**.

## Consequences

What becomes true once this is Accepted (it changes a decision, not code):

- **A subscription-legitimate, keyless always-on design exists to build against** — the
  tokenless bridge + local-CLI executor is the sanctioned shape; the SDK fork (Option B) and
  the hosted webhook service (Option C) are recorded as **rejected for the runtime loop**
  (B reusable only as the swap target, behind an ADR-002 supersession).
- **Honesty is preserved on two fronts** — the "ordinary individual usage" ceiling is stated
  plainly (no beach-mode auto-resolve claim on subscription), and the spike does **not**
  overclaim by shipping code: it is a design, gated on NB-376/ADR-004 and ADR-002.
- **The swap seam future-proofs the framework** — a ToS shift (the line moved twice in Q1
  2026; a metered-credit change is scheduled 2026-06-15) is a **one-line config change**, not
  a rewrite — but flipping to the key-holding `api-sdk` backend in the always-on loop is
  itself an ADR-002 supersession, not a quiet bypass.
- **Reuses, does not duplicate** — the bridge stands on existing keyless artifacts
  (`scripts/graph.py`, `skills/solve/resume.md`, `skills/solve/capture.md`, ADR-001's
  Tier-0/1 identity), honouring ADR-004's "don't rebuild Cyrus runtime plumbing" non-goal.

**Follow-ups** (file on Accept; each a file-able problem — **none started by this spike**):

1. **Build the tokenless bridge** (the watcher + executor-swap interface + the batch-DAG /
   quota guard / idempotent-resume wiring) — **only after** this ADR is Accepted **and**
   under ADR-004's keyless flip condition. The default executor is `local-cli`.
2. **Wire the batch-DAG pre-dispatch pass** into `/backlogd:scope` (lift per-problem
   decomposition to batch scope) — AC #7.
3. **Wire the quota/budget guard** as a pre-dispatch gate reading the subscription usage
   signal — AC #8(#3).
4. **Verify the gated Tier-1 `delegate` write** (the ADR-001 follow-up #1 dependency) before
   the bridge relies on it for transparency — AC #11.

If reversed (a future ADR supersedes this): the only sanctioned always-on path would change —
e.g. accepting the API-key executor as default, which would **also** require superseding
ADR-002. Until then, this stands as the design of record, **un-built**, awaiting PO accept.

---
_Refs: NB-379 · binding standards: [ADR-004](ADR-004-backlogd-identity.md) (GO-to-explore + identity/non-goals), [ADR-002](ADR-002-keyless-mcp.md) (keyless flip-condition), [ADR-001](ADR-001-visible-agent-identity-in-linear.md) (Tier-0/1 identity; Tier-2 rejected) · prior art: [`scripts/graph.py`](../../../scripts/graph.py) (execution graph), [`skills/solve/resume.md`](../../../skills/solve/resume.md) (four-source reconcile), [`skills/solve/capture.md`](../../../skills/solve/capture.md) (STATUS contract + DONE_WITH_CONCERNS forward-carry), [`docs/notes/subagent-mcp-tool-grant.md`](../../notes/subagent-mcp-tool-grant.md) (NB-340/NB-368 tool-grant) · related: NB-370 (transparency), NB-368 (tool-grant trust), NB-376 (differentiator) · external (named, date-locatable — verify before relying): Anthropic Claude Agent SDK / Claude Code SDK docs (API-key auth); Anthropic Usage Policy + Commercial/Consumer Terms; Anthropic Help Center "Using Claude Code with a Pro/Max subscription"; the Feb 2026 OpenClaw/OpenCode/Goose subscription-token enforcement reports; Anthropic's announced June 15 2026 Agent-SDK metered-credit change._
