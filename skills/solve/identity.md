---
name: solve-identity
description: Resolve the Linear team, workflow states, and labels for /backlogd:solve — read .backlogd/identity.json first, fall back to list_* + rewrite the cache, then resolve the two started states by role (pickup vs review) and mint a per-run session id.
---

# solve — identity resolution

Resolve the team, its workflow states, and labels — **read `.backlogd/identity.json`
first**: if it exists and its `expires_at` is in the future, use the cached `team` /
`statuses` / `labels` and **skip** the three `list_*` calls; otherwise call
`list_teams` → `list_issue_statuses` → `list_issue_labels` and **rewrite** the cache with
a fresh 24-hour `expires_at`. The exact procedure, schema, and manual-invalidation note
are in `skills/linear/references/linear-mcp.md` → "Resolve identity before you write" →
"Cache identity to `.backlogd/identity.json`".

## Resolve the two started states by role

This team has **two** `started` states — *In Progress* and *In Review*. From the resolved
`statuses`, resolve them **by role** (match on `type`, never on display name):

- **pickup** → the *In Progress* state (work has begun),
- **review** → the *In Review* state (work is done, awaiting the product owner).

## Set the delegate on pickup (best-effort, Tier 1)

When `skills/solve/dispatch.md` step 1 moves a unit to *In Progress*, it sets the issue's
`delegate` to the installed `backlogd` agent app user **in the same `save_issue` call** as
the state transition — one MCP write, zero extra round-trips, no server:

```text
save_issue(id:"<unit>", state:"<In Progress state>", delegate:"backlogd")
```

This is backlogd's first first-class **transparency** signal — *"an agent picked this
up"*, visible on the issue and filterable by *Delegate* — and it stays inside the
key-free / serverless principle (the write goes through the same plain user-OAuth MCP as
every other call; no `actor=app` token, no webhook, no daemon). Verified live under
ADR-001's Tier-1 / [ADR-006](../../docs/standards/adrs/ADR-006-tier2-locally-hosted-agent-identity.md)
AC#7 (NB-390, 2026-06-02). The PO's *delegated-to-agent* saved view (NB-388) filters on it.

Three rules govern the write:

- **Name the agent by its configured name (`"backlogd"`), never a hardcoded uuid.** The
  MCP resolves the name to the installed app user; an installer who named the agent
  differently changes only this one string. Do not paste an app-user uuid here.
- **Best-effort — never fail a pickup on it.** The `backlogd` agent app user is an
  **optional**, admin-only, one-time install (see
  [`docs/guides/agent-identity-setup.md`](../../docs/guides/agent-identity-setup.md)). On a
  workspace where it is **not** installed, `delegate:"backlogd"` errors or no-ops — that is
  expected and harmless. **Attempt the write, then swallow-and-note on failure** (a one-line
  orchestrator note is enough) and carry on with the pickup. The optional agent identity
  being absent must **never** block the In Progress transition or the dispatch. Practically:
  if combining it into the state `save_issue` would abort the whole call on an
  uninstalled workspace, fall back to setting state first and attempting the `delegate`
  write separately so the state transition still lands — the combined single call is the
  happy path, not a hard requirement.
- **Leave it set on completion (the default, stated explicitly).** When the unit completes,
  the default is to **leave** `delegate` set — do **not** clear it. Leaving it is additive
  and harmless, and it **preserves the "an agent worked this" audit signal** that NB-388's
  saved view filters on. (Clearing on completion is a deliberate non-default; we keep the
  signal.)

## Mint a session id

Mint a session id for this run and remember it as `$SESSION` — the graph steps in
`skills/solve/dispatch.md` use it to tie this run to the problem and the files touched.
Make it unique to this problem + run, e.g.

```text
solve-{identifier}-$(date -u +%Y%m%dT%H%M%S)
```

(the issue's git branch name works too).
