# ADR-001 — Visible agent identity in Linear

> This is **ADR-001** — the first entry in backlogd's Architecture Decision Record
> convention. There was no `docs/standards/adrs/` directory before NB-370; this file
> establishes both the directory and the shape every later ADR follows:
> **Status · Context · Considered Options · Decision · Consequences**. ADRs are
> immutable once Accepted — supersede, do not rewrite.

- **ADR:** 001
- **Title:** Visible agent identity in Linear — Agent Interaction Protocol (`delegate` + Agent Sessions) vs MCP-only transparency
- **Status:** **Proposed** _(this spike recommends; the Product Owner flips it to `Accepted` on greenlight)_
- **Date:** 2026-05-29
- **Problem:** NB-370 (research/feasibility spike)
- **Deciders:** Product Owner (Nicolai)

---

## Status

**Proposed.**

A research spike (NB-370). It maps the option space for *visible agent identity* in
Linear and recommends a path; it ships **no runtime behaviour**. The recommendation
(Tier 0 today, with a flagged path to Tier 1) becomes binding only when the PO moves
this ADR to `Accepted` and files the follow-ups under [Consequences](#consequences).

---

## Context

A colleague runs a locally-launched Claude session that appears in Linear as a
**named agent** (their example: "Kato"): it picks up issues and whole problems, walks
through them, and surfaces questions — the agent itself is the **visible actor** in
Linear, not a comment badge under a human's name.

backlogd today is the inverse. The Product Owner is the `assignee` on every problem,
and Claude's work shows up only as comment prefixes — `**[backlogd developer]**`,
`**[backlogd reviewer]**`, `**[backlogd]**`. The PO cannot see, as **first-class Linear
signal**, any of these four things (the "four PO transparency asks", referenced
throughout this ADR as **A1–A4**):

- **A1** — which agent **picked up** an issue/problem;
- **A2** — which agent **closed / reviewed** it;
- **A3** — when the **scrum-master assigned / routed** a problem;
- **A4** — when an agent **surfaced a blocker / question** for the PO.

The mechanism the colleague's agent uses is Linear's **Agent Interaction Protocol**
(Developer Preview): an OAuth app installed with `actor=app` becomes a dedicated *app
user* (the named actor); issues are **delegated** to it (the `delegate` field; the
human keeps `assignee`); each engagement opens an **AgentSession** carrying
**AgentActivities** (`thought` / `action` / `elicitation` / `response` / `error`); the
agent backend is driven by `AgentSessionEvent` **webhooks** with a ~10-second
acknowledgement window.

That protocol collides head-on with backlogd's **core principle**, stated in the
README and `docs/conventions.md`:

> **Official Linear MCP only · OAuth-as-the-user · no API keys · no server.**

The Agent Interaction Protocol needs an OAuth app registration, an `actor=app`
**token the integrator holds**, and a **running webhook server** — all three breach
the principle. The crack of light: the official Linear MCP *already* exposes a
`delegate` parameter on `list_issues` / `save_issue`. So a **partial** tier —
delegating to one installed agent app user, **no server, no held token** — might be
reachable without breaking the principle. Pinning down exactly what the MCP `delegate`
can and cannot do is the heart of this spike, recorded under
[Verified finding](#verified-finding-the-mcp-delegate-parameter) below.

This ADR also re-opens a boundary the codebase currently draws — see
[the SKILL.md boundary decision](#decision-3--the-skillslinearskillmd-boundary-line).

---

## Verified finding: the MCP `delegate` parameter

The spike's central job was to make this finding **verified, not assumed**. Each
question below records *how* it was checked — a live read-only MCP call attempted
against backlogd's own Linear workspace (the `Nicolai-bernsen` team), and/or the
specific published Linear doc. No Linear state was mutated; all probes were reads.

### Q1 — Can MCP `delegate` target a *custom* installed agent app user, or only the built-in "Linear" agent?

**Finding: in this workspace, neither resolves to anything — because no agent app
user is installed, and the MCP `delegate` parameter is a silent filter, not a
validated target.**

- **How verified (live MCP, read-only):**
  - `mcp__linear__list_users` returns exactly **two** users: `Nicolai Bernsen`
    (human admin) and a built-in **`Linear`** app user
    (`linear-…@linear.linear.app`). **No custom agent app user exists** in the
    workspace — nothing has been installed via `actor=app`.
  - `mcp__linear__list_issues(delegate:"Linear")` → `{"issues":[],"hasNextPage":false}`.
  - `mcp__linear__list_issues(delegate:"backlogd")` (a name with no matching app
    user) → `{"issues":[],"hasNextPage":false}`.
  - `mcp__linear__list_issues(delegate:"Kato")` (the colleague's agent, foreign to
    this workspace) → `{"issues":[],"hasNextPage":false}`.
  - `mcp__linear__list_issues(delegate:"zzz-nonexistent-agent-xyz-9876")` (deliberate
    garbage) → `{"issues":[],"hasNextPage":false}`.
  - **Interpretation:** every name — valid built-in, plausible custom, foreign, and
    garbage — returned an empty set with **no error**. The `delegate` parameter on
    `list_issues` is a **read filter** that matches issues already delegated to that
    agent; with nothing delegated to anything in this workspace it matches nothing,
    and it does **not** validate the name against a registry. So the *read* path
    cannot, on its own, prove whether a custom agent would be a valid `delegate`
    **write** target. That requires an installed agent app user — which is a Tier-2
    prerequisite, see below.
- **How verified (docs):** Linear's "AI Agents" doc
  (<https://linear.app/docs/agents-in-linear>) — "Agents, also known as **app
  users** … are installed and managed by workspace admins." Custom agents are built
  on "Linear's developer platform" with "agent APIs, authentication, and behavior"
  documented separately from the MCP. So a custom agent app user **can** be a
  `delegate` target **once installed via the developer platform / `actor=app`** — but
  installing one is exactly the Tier-2 work this ADR is weighing, not something the
  MCP grants by itself.
- **Untested — would require a write, pending PO:** whether
  `mcp__linear__save_issue(delegate:"<agent>")` *sets* the delegate for the built-in
  `Linear` agent. The spike is read-only by mandate and must not delegate a real
  issue, so this is recorded as untested rather than guessed. The empty-read evidence
  plus the docs make the **shape** clear; the live write is deferrable to the Tier-1
  follow-up.

### Q2 — Can MCP `delegate` emit/stream AgentActivities or drive AgentSession lifecycle, or does it only set the `delegate` field?

**Finding: the MCP can only ever set the `delegate` field. AgentActivities and
AgentSession lifecycle are protocol surface, not MCP surface — unreachable through
`mcp__linear__*`.**

- **How verified (MCP tool surface):** the official Linear MCP exposes tools for
  "finding, creating, and updating objects in Linear like issues, projects, and
  comments" (<https://linear.app/docs/mcp>). `delegate` appears **only** as a
  parameter on `list_issues` and `save_issue` (an issue field). There is **no**
  `agentActivityCreate`, no `agentSessionUpdate`, and no AgentSession object anywhere
  in the MCP toolset — confirmed against the live tool schemas loaded this session.
- **How verified (docs):** AgentActivities and AgentSessions are defined only in the
  developer platform docs (<https://linear.app/developers/agent-interaction>):
  sessions are "created automatically when an agent is mentioned or delegated an
  issue"; activities are posted via the **`agentActivityCreate`** /
  **`agentSessionUpdate`** GraphQL mutations; lifecycle (`pending` / `active` /
  `error` / `awaitingInput` / `complete` / `stale`) is tracked "automatically based
  on the last emitted activity." None of these mutations is exposed by the MCP.
- **Conclusion:** delegating via the MCP would set the `delegate` field and (per the
  docs) auto-create an AgentSession — but **nothing would ever drive it**: no
  `thought`/`action`/`response` activities, no lifecycle progression, because the
  mutations that emit them live behind a custom OAuth app + webhook backend, not the
  MCP. A session opened with no backend goes **`stale`** (the 10-second-ack rule,
  Q3-adjacent). The MCP gives the *field*, never the *conversation*.

### Q3 — Does delegating require the human `assignee` to remain set?

**Finding: yes — delegation is explicitly additive to (never a replacement for) the
human assignee. This is the most principle-friendly fact in the whole protocol.**

- **How verified (docs, two sources):**
  - "Agents are not traditional assignees. Assigning an issue to an agent triggers
    delegation — the agent acts on the issue, but **the human teammate remains
    responsible** for its completion." (<https://linear.app/docs/agents-in-linear>)
  - "You **remain the primary assignee** and the agent is added as an additional
    contributor working on your behalf … issues can only be assigned to humans, and
    only delegated to agents." (<https://linear.app/docs/assigning-issues>)
  - Developer platform: "Assigning an issue to your app now sets it as the
    `delegate`, **not the `assignee`** — so humans maintain ownership while agents
    act on their behalf." (<https://linear.app/developers/agents>)
- **Implication for backlogd:** the PO **stays** the assignee on every problem in
  every tier. `delegate` is purely an *additive visibility signal* — adopting it (in
  any tier) does not disturb backlogd's "PO owns the problem" model. This is what
  makes Tier 1 conceptually clean even though, per Q1–Q2, the MCP can only set the
  field and not run a real agent session.

### One-paragraph synthesis

The official MCP `delegate` is a **single issue field with a read filter** — nothing
more. It can (subject to a deferred write-probe, Q1) point an issue's `delegate` at an
**installed** agent app user while the human stays `assignee` (Q3), but it **cannot**
install that app user, emit AgentActivities, or drive AgentSession lifecycle (Q2).
Real "Kato-style" visible-agent presence — a named actor that picks up, narrates, and
asks questions — is **Tier 2** and needs the full protocol (app registration +
`actor=app` token + webhook server). The MCP gets you the *field*, not the *agent*.

---

## Considered Options

Three tiers, lowest cost / least principle-cost first. For each: **(a)** which of the
four PO asks (A1 pickup · A2 close/review · A3 route · A4 blocker) it satisfies;
**(b)** its conflict (or not) with the key-free / serverless principle; **(c)** a
rough one-time setup + ongoing cost.

### Tier 0 — Per-role comment badges only (status quo)

backlogd's current behaviour: PO is `assignee`; each agent posts a single comment
prefixed with its role badge (`**[backlogd developer]**` / `**[backlogd reviewer]**`
/ `**[backlogd]**`), edited in place; the scrum-master drives all state transitions.

- **(a) PO asks satisfied:** **A1–A4 partially, via comments — none as first-class
  Linear actor signal.** Who picked up (A1), who reviewed (A2), routing (A3), and
  blockers (A4) are all *discoverable by reading the comment thread and the activity
  feed of the state changes*, but the **actor** on every event is the human PO. There
  is no agent face on the timeline, no per-agent filter, no Insights-by-delegate.
- **(b) Principle conflict:** **none.** Pure `mcp__linear__*`, OAuth-as-user, no key,
  no server. This *is* the principle.
- **(c) Cost:** **zero** — already shipped and proven across many runs.

### Tier 1 — MCP-only `delegate` to one installed agent app user (no server)

Install **one** agent app user (a single "backlogd" agent) once, via Linear's
developer platform with `app:assignable`. Thereafter the scrum-master uses
`mcp__linear__save_issue(delegate:"backlogd")` to mark a problem as picked up by the
agent — the PO stays `assignee` (Q3). **No webhook server, no held `actor=app` token
in backlogd's loop** — the loop keeps talking to Linear only through the user-OAuth
MCP; `delegate` is just one more field it writes.

- **(a) PO asks satisfied:** **A1 (pickup) — yes, as first-class signal:** the
  `delegate` field shows the agent on the issue, surfaces in My-Issues, in custom
  views filtered by *Delegate*, and in Insights-by-delegate (per
  <https://linear.app/docs/agents-in-linear>). **A3 (routing) — partially:** the moment
  of delegation is itself a routing signal in the activity feed, attributed to the
  agent if the write is made under the agent identity (caveat below). **A2 (review) /
  A4 (blocker) — no:** these need *distinct* actors and *narrated* activity, which a
  single shared agent + a bare field cannot express. There is one agent face, not a
  developer-vs-reviewer distinction, and no `elicitation`/`response` activity stream.
- **(b) Principle conflict:** **small and bounded — must be verified before
  shipping.** The *field write* itself is pure MCP (no server, no key) ✅. The open
  risks, each a Tier-1 follow-up acceptance gate:
  1. **Installing the agent app user** is a one-time admin action on Linear's
     developer platform. Whether that can be done **without backlogd ever holding an
     `actor=app` token** (i.e. the app is registered + installed, but the *runtime*
     keeps using user-OAuth MCP and only sets the `delegate` field) is the make-or-
     break check. Per Q1–Q3 the field is writable over user-OAuth MCP, so this looks
     reachable — but it is **untested (deferred write)** and gates Tier 1.
  2. **Attribution:** a `delegate` set via the user-OAuth MCP is an action *by the
     PO* (the OAuth user), not *by the agent*. So the timeline reads "Nicolai
     delegated to backlogd", not "backlogd picked this up". That still satisfies A1
     (the agent is now visibly on the issue) but is weaker than a true agent-actor
     event for A3.
- **(c) Cost:** **low** — one-time app registration + install (admin, minutes); then
  one extra MCP field-write per pickup in `/backlogd:solve`. No infrastructure, no
  ongoing ops. A dormant AgentSession may be auto-created and go `stale` with no
  backend (Q2) — cosmetically odd, harmless.

### Tier 2 — Full Agent Interaction Protocol (`actor=app` + webhook server + Sessions/Activities)

The "Kato" mechanism in full. Register an OAuth app (or several — one per role to get
A1≠A2), install with `actor=app` + `app:assignable` + `app:mentionable`, hold the
`actor=app` token, **stand up a webhook server** that receives `AgentSessionEvent`
(`created` / `prompted`), acknowledges within ~10 s, and posts AgentActivities
(`thought` / `action` / `elicitation` / `response` / `error`) to narrate each
engagement and `agentSessionUpdate` to set `externalUrls`.

- **(a) PO asks satisfied:** **A1, A2, A3, A4 — all, as first-class first-party
  signal.** Distinct app users per role give A1 (developer picked up) vs A2 (reviewer
  closed). Delegation/mention events give A3. `elicitation` activities + the
  `awaitingInput` session state give A4 as a real, surfaced "the agent is asking you
  something" signal. This is the only tier that fully answers all four.
- **(b) Principle conflict:** **direct and total — breaks all three legs.** It
  requires (i) an **`actor=app` OAuth token the integrator holds** — i.e. a
  credential/secret outside the user-OAuth MCP flow ("actions performed with the
  received OAuth token will come from the app itself",
  <https://linear.app/developers/oauth-actor-authorization>); (ii) a **running
  webhook server** with <5 s response + <10 s activity ack
  (<https://linear.app/developers/agent-interaction>); (iii) leaving the **MCP-only**
  surface for direct GraphQL mutations. backlogd is a key-free, serverless Claude Code
  plugin — this tier turns it into a hosted service.
- **(c) Cost:** **high and ongoing.** App registration + admin install; secret
  storage + rotation for the `actor=app` token; a deployed, monitored webhook
  endpoint (hosting, uptime, the 10-second SLA); per-role apps multiply this; plus the
  build of the activity-emitting backend. One-time setup is days, not minutes, and it
  adds **permanent operational surface** backlogd has none of today.

### At-a-glance

| Tier | A1 pickup | A2 review | A3 route | A4 blocker | Key-free / serverless | Cost |
|---|---|---|---|---|---|---|
| **0** Badges (today) | comment only | comment only | comment only | comment only | ✅ no conflict | none |
| **1** MCP `delegate`, no server | ✅ first-class | ❌ | ~ partial | ❌ | ⚠️ field-write clean; **install step must be token-free (gate)** | low |
| **2** Full AIP | ✅ | ✅ | ✅ | ✅ | ❌ breaks all three legs | high + ongoing |

---

## Decision

**Adopt Tier 0 (status quo) as the standing answer, and authorise a thin, gated
Tier-1 experiment — explicitly reject Tier 2.**

Rationale, tied directly to the **official-MCP-only / OAuth-as-user / no-key /
no-server** principle:

- **Tier 2 is rejected because it costs the principle outright.** It demands an
  `actor=app` token backlogd would have to *hold* (breaks key-free), a *running
  webhook server* (breaks serverless), and direct GraphQL mutations *off* the MCP
  surface (breaks MCP-only). It is the only tier that fully satisfies A1–A4, but it
  converts backlogd from a key-free Claude Code plugin into a hosted, secret-bearing
  service. That is a different product. Not now.
- **Tier 0 keeps the principle perfectly** and already covers A1–A4 *informationally*
  (in comments + the state-change activity feed). What it lacks is **agent-as-actor
  signal** — the gap the PO named. It costs nothing and stays the baseline.
- **Tier 1 is the only tier that buys real first-class signal (A1, partial A3)
  without obviously costing the principle** — the `delegate` write is pure user-OAuth
  MCP (Q1–Q3). Its one residual principle-risk is whether the agent app user can be
  *installed* without backlogd ever holding an `actor=app` token; the live read
  probes plus Linear's docs make this look reachable, but it is **untested (a write
  the spike must not make)**. So Tier 1 is **recommended as a gated experiment**, not
  switched on by this ADR: the follow-up below must first confirm the token-free
  install and the delegate write under user-OAuth, against the live workspace.

In short: **default Tier 0; pursue Tier 1 only if the token-free install check
passes; never Tier 2 under the current principle.** If the PO ever decides full
"Kato-style" presence (A2 + A4 as first-class signal) is worth more than the
key-free/serverless principle, that is a deliberate **principle change** the PO makes
— and it would supersede this ADR, not amend it.

**Status: Proposed.**

---

## Consequences

### If accepted

- backlogd's transparency story is, on the record: **Tier 0 today; Tier 1 is the
  sanctioned next step; Tier 2 is out of bounds while the key-free/serverless
  principle holds.** Future "why don't the agents show up as actors in Linear?"
  questions resolve to this ADR instead of being re-litigated.
- The `skills/linear/SKILL.md` boundary softens (see Decision 3 below) so a Tier-1
  experiment is *allowed* without lifting the guard against the full protocol.
- No runtime behaviour changes from this ADR itself — it is documentation. Behaviour
  changes only when a follow-up below is filed, accepted, and solved.

### Decision 2 — graph-vs-Linear-identity boundary

The execution-metadata graph (`scripts/graph.py`, NB-263 / NB-320) records *dispatch
outcomes and latency* — when a developer was dispatched, what it returned
(`solved`/`partial`/`blocked`), and how long that took — as **local agent-execution
memory**, and is **not** a substitute for visible Linear actor identity: it is a
private analytics store that answers "did the framework help?", invisible to the PO in
Linear and silent on *which named agent* acted, so it and the tiers above do not
overlap as a transparency answer.

### Decision 3 — the `skills/linear/SKILL.md` boundary line

The current "Boundaries" line reads: *"the Linear Agents platform (agent `delegate`,
agent sessions, webhooks) is out of scope for v1 — ignore the `delegate` parameter."*

**Decision: soften to allow Tier 1.** The blanket "ignore the `delegate` parameter"
is now wrong-for-intent — Tier 1 deliberately uses it. The line is edited (in this
same change) to: keep **agent *sessions* and *webhooks*** (the Tier-2 protocol
surface) out of scope, while **allowing the MCP `delegate` field per ADR-001's gated
Tier-1 experiment**. The guard against the full protocol stays; the specific blanket
ban on `delegate` lifts. (Edit applied in `skills/linear/SKILL.md` Boundaries section
alongside this ADR.)

### Follow-ups — file these if the PO accepts the recommended tier

Each is precise enough to file directly as a Linear problem (or convert to a Project):

1. **"Verify token-free Tier-1 `delegate`: install one backlogd agent app user and
    confirm the MCP can set `delegate` under user-OAuth"** — Spike/ops. Register +
    admin-install a single `backlogd` agent app user (`app:assignable`) on the dev
    workspace; confirm `mcp__linear__save_issue(delegate:"backlogd")` sets the field
    while the PO stays `assignee` and **without backlogd holding an `actor=app`
    token**. Resolves the one open principle-risk gating Tier 1. *(Blocks #2.)*

2. **"Wire `delegate` pickup into `/backlogd:solve` (Tier 1, A1)"** — When a developer
    is dispatched for a unit, the scrum-master sets the issue's `delegate` to the
    backlogd agent (PO stays `assignee`); clears or leaves it on completion per the
    decision in #1. Documentation + the one MCP field-write; no server. *(Blocked by
    #1.)*

3. **"Tier-1 PO-overview: add a *Delegated to agent* saved view / Insights slice"** —
    Extend `docs/guides/po-overview.md` so the PO can see agent-picked-up problems at a
    glance (custom view filtered by *Delegate*, optional Insights-by-delegate). Makes
    the A1 signal from #2 actually visible in the daily routine. *(Blocked by #2.)*

4. **(Parser bug, already noted on NB-370) "AC parser: tolerate Linear's bracket-
    escaping of `\[test\]`/`\[manual\]`/`\[review\]`"** — Unrelated to identity but
    surfaced here: the AC kind regex `^\[…\] ` does not match Linear's stored
    `\[test\]`, so tagged ACs silently fall back to `[review]`. File as its own
    problem.

### If rejected / deferred

Tier 0 remains the answer and the SKILL.md boundary edit (Decision 3) can stand on its
own (it only *permits* Tier 1, it does not require it) or be reverted — the PO's call.
No follow-ups are filed. This ADR stays as the record of why the option space was
explored and parked.

---

## References

- Problem: **NB-370** — *Spike: visible agent identity in Linear*.
- Sibling decision-note (evidence-depth model): [`docs/notes/subagent-mcp-tool-grant.md`](../../notes/subagent-mcp-tool-grant.md).
- Principle source: top-level `README.md`; [`docs/conventions.md`](../../conventions.md) → *Linear*.
- Boundary touched: [`skills/linear/SKILL.md`](../../../skills/linear/SKILL.md) → *Boundaries*.
- Graph: [`scripts/graph.py`](../../../scripts/graph.py) (NB-263 / NB-320).
- Linear docs (cited inline): [AI Agents](https://linear.app/docs/agents-in-linear) · [Assign and delegate](https://linear.app/docs/assigning-issues) · [MCP server](https://linear.app/docs/mcp) · [Developers › Agents](https://linear.app/developers/agents) · [Agent interaction](https://linear.app/developers/agent-interaction) · [OAuth actor authorization](https://linear.app/developers/oauth-actor-authorization) · [Webhooks](https://linear.app/developers/webhooks).
- Live read-only MCP probes (this spike, 2026-05-29): `list_users`, `list_issues(delegate:…)` ×4. No Linear state mutated.
