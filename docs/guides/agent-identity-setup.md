# Agent identity setup — install the `backlogd` agent in Linear

backlogd can run as a visible **agent** in your Linear workspace: problems it picks up show
a `backlogd` **delegate** (you stay the `assignee`), so "an agent did this" is a first-class,
filterable signal rather than a comment badge under your own name.

This is a **one-time, admin-only** setup, and it is **optional** — backlogd works without it
(the default is comment-badge transparency). It implements the identity decision in
[ADR-006](../standards/adrs/ADR-006-tier2-locally-hosted-agent-identity.md) while staying
inside the keyless / no-hosted-server constraint of
[ADR-002](../standards/adrs/ADR-002-keyless-mcp.md).

## Two rungs (pick where you stop)

Per [ADR-006](../standards/adrs/ADR-006-tier2-locally-hosted-agent-identity.md) — and
carried forward from [ADR-001](../standards/adrs/ADR-001-visible-agent-identity-in-linear.md):

- **Tier 1 — `delegate` only.** The `backlogd` agent exists so `delegate:"backlogd"`
  resolves; the scrum-master sets it on pickup via your normal user-OAuth MCP. **No daemon,
  no server, no key in the runtime loop.** Identity without autonomy — the shippable-now rung.
- **Tier 2 — `actor=app` + local listener.** A local daemon (launchd/systemd + tunnel, on
  *your* machine, never a hosted cloud server) acks Linear AgentSessions and spawns the local
  `claude` CLI. Adds presence + autonomy. The next rung, gated on a proof.

**Both rungs start from the same OAuth application — create it once (steps 1–3).** Tier 1
needs nothing more; Tier 2 adds the webhook + the daemon later.

> **Secret custody — [ADR-002](../standards/adrs/ADR-002-keyless-mcp.md).** The app's
> `client_id`, `client_secret`, and access token are **setup-only** secrets — the same
> exception class as the `/backlogd:init` admin key. Keep them **out of the repo** (a
> password manager, or a gitignored local env). backlogd's runtime holds **no** Anthropic
> key, and on Tier 1 it does not use the agent token at all.

## 1. Create the OAuth application

As a workspace **admin**, open **Settings → API → Applications → "Create new application"**
(`https://linear.app/settings/api/applications/new`) and fill in:

| Field | What to put |
| --- | --- |
| **Application icon** | any image ≥ 256×256 — this becomes the agent's avatar in Linear |
| **Application name** | `backlogd` (user-visible — how the agent shows in the delegate menu) |
| **Developer name** | you / your org |
| **Developer URL** | your repo, e.g. `https://github.com/<you>/backlogd` |
| **Description** | e.g. "backlogd — a problem-driven scrum team for Claude Code." |
| **Redirect URIs** | `http://localhost:3000/oauth/callback` — localhost is allowed, so **no public server is needed**. (Newline-separate if you add more.) |
| **GitHub username** | leave blank (only for attributing `actor=app` commits in GitHub) |

Toggles:

- **Public** — **off** (keep the app private to your workspace; don't let other workspaces install it).
- **Client credentials** — **off** (we use the authorization-code flow, not the `client_credentials` grant).
- **Webhooks** — **off for Tier 1.** Tier 1 has no listener, so it needs no Webhook URL and
  no event subscriptions. Turn webhooks **on only for Tier 2**, where you also set a Webhook
  URL and tick **App events → Agent session events**.

Save. Linear then shows the **`client_id`** and **`client_secret`** — copy both somewhere
safe (not the repo).

> The create form has **no scope checkboxes** — scopes are requested in the authorization URL
> (step 2), not here.

## 2. Install the agent (`actor=app` authorization)

Installing the agent is a one-time OAuth authorization you approve **as admin**. Open this
URL in a browser (signed in as the admin), substituting `<client_id>` and a random `<state>`:

```text
https://linear.app/oauth/authorize?client_id=<client_id>&redirect_uri=http://localhost:3000/oauth/callback&response_type=code&scope=read,app:assignable&state=<random>&actor=app
```

- **`actor=app`** installs it as an *agent* (not as you) — this is the admin-only step that
  creates the `backlogd` user in your workspace.
- **`scope=read,app:assignable`** (comma-separated). `app:assignable` is what lets the agent
  be a **delegate** target. Add `app:mentionable` to allow @-mentions, and `write` if the
  agent token itself will mutate Linear (Tier 2).

Approve, and pick the team(s) the agent can access. The browser then redirects to
`http://localhost:3000/oauth/callback?code=…`; since nothing is listening there you'll see a
connection error — **that's expected. Copy the `code` value out of the address bar.**

## 3. Exchange the code for the agent token

Run this yourself so the secret never leaves your machine:

```bash
curl -X POST https://api.linear.app/oauth/token \
  -d "code=<code>" \
  -d "redirect_uri=http://localhost:3000/oauth/callback" \
  -d "client_id=<client_id>" \
  -d "client_secret=<client_secret>" \
  -d "grant_type=authorization_code"
```

Store the returned `access_token` alongside the client id/secret — **out of the repo**. On
**Tier 1 you set this token aside**; the runtime does not use it. (Tier 2's listener will.)

Optionally confirm the agent's identity:

```bash
curl https://api.linear.app/graphql \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ viewer { id name } }"}'
```

## 4. Verify Tier 1 — the `delegate` write

With the agent installed, `backlogd` should be a valid delegate target. The scrum-master sets
it on pickup through the **normal user-OAuth MCP** — no agent token in the loop:

```text
mcp__linear__save_issue(id:"<issue>", delegate:"backlogd")
```

Confirm with `get_issue` that `delegate` is now `backlogd` **and** you remain the `assignee`
(delegation is additive — it never displaces the human owner).

> **Verification status.** The OAuth install above is the documented, solid path. Whether the
> `delegate` field-write succeeds under *plain user-OAuth MCP* — i.e. whether Tier 1 is truly
> key-free at runtime — is the empirical question the spike **NB-390** confirms; record the
> result there. If the write turns out to require the agent's own `actor=app` token, Tier 1 is
> not key-free and the realistic choice narrows to comment badges (Tier 0) vs the Tier-2
> listener.

## What this is *not*

- **Not an Anthropic key.** `actor=app` is a *Linear* auth identity; model inference still
  runs on your `claude` CLI subscription. The only thing that introduces an Anthropic API key
  is the deliberate Tier-2 `api-sdk` executor swap, which itself requires superseding
  [ADR-002](../standards/adrs/ADR-002-keyless-mcp.md).
- **Not a hosted service.** Tier 1 has no server. Tier 2's listener runs **locally** on your
  own machine, not a backlogd-hosted cloud endpoint — that locality is the whole basis of
  [ADR-006](../standards/adrs/ADR-006-tier2-locally-hosted-agent-identity.md).
