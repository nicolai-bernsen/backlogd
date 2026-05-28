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

## Mint a session id

Mint a session id for this run and remember it as `$SESSION` — the graph steps in
`skills/solve/dispatch.md` use it to tie this run to the problem and the files touched.
Make it unique to this problem + run, e.g.

    solve-{identifier}-$(date -u +%Y%m%dT%H%M%S)

(the issue's git branch name works too).
