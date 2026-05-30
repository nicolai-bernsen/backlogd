# Workspace bootstrap — `/backlogd:init`

A one-time, opt-in setup pass that brings a fresh Linear workspace into the canonical shape
the backlogd loop expects: the `problem` / `kind:ops` / `blocked` labels, the workflow-state
categories the forecast math reads, and three templates (a `Problem` issue, a `backlogd
problem` project, and a `Spec` document). After it runs, the runtime loop stays **key-free /
MCP-only** — exactly as before.

This is the *only* place backlogd uses a Linear API key, and even here the key is read by a
local setup engine, never by the orchestrator or any agent. The walkthrough below covers
creating that key, placing it safely, and what `init` does with it.

## When you need this

You don't, strictly — the [walking skeleton](../../README.md#try-the-walking-skeleton) only
needs one hand-made `problem` label. Reach for `/backlogd:init` when you'd rather not set up
labels, states, and templates by hand, or when you want a new workspace to be
correct-by-construction before you start filing problems.

## 1. Create a Linear personal API key (Admin scope)

In Linear, open **Settings → Account → Security & access** and create a **personal API
key**. Give it **Admin** scope.

Admin scope is required because `init` writes workspace *settings*, not just issues: it
creates and renames labels, fills missing workflow states, and creates or updates templates.
A read-only or issues-only key authenticates but is rejected the moment the engine tries a
settings mutation — the `init` preflight catches that and stops with a pointer back here.

Copy the key when Linear shows it (it starts with `lin_api_`). You won't be able to read it
again.

## 2. Place the key at `~/.backlogd/credentials.env`

The setup engine reads the key from the `LINEAR_API_KEY` environment variable first, and
falls back to a credentials file at `~/.backlogd/credentials.env`. The file is a simple
`KEY=VALUE` list; add one line:

```text
LINEAR_API_KEY=lin_api_xxxxxxxxxxxxxxxxxxxxxxxx
```

A few rules keep this safe:

- **It lives outside the repo.** `~/.backlogd/` is in your home directory, not the checkout,
  so it can't be committed by accident. Never paste the key into a repo file.
- **Restrict the file's permissions** so only you can read it — e.g. `chmod 600
  ~/.backlogd/credentials.env` on macOS/Linux, or remove inherited access on Windows
  (`icacls "$env:USERPROFILE\.backlogd\credentials.env" /inheritance:r /grant:r "$env:USERNAME:R"`).
- **The orchestrator never reads this file.** `/backlogd:init` only checks that it *exists*;
  the key value is read solely inside the engine's network layer when it calls Linear.

If you'd rather not write a file at all, export `LINEAR_API_KEY` in the shell that launches
Claude Code instead — the engine prefers the environment variable when it's set.

## 3. Run `/backlogd:init`

Preview first, apply second.

```text
/backlogd:init --dryrun
```

`--dryrun` runs the preflight and the read-only audit, prints the plan grouped by safety,
and stops — nothing is created, renamed, or deleted. Use it to see exactly what `init` would
do to your workspace.

When the plan looks right, run it for real:

```text
/backlogd:init
```

### Approving the engine's writes

`init` makes its Linear *settings* writes (labels · states · templates) by shelling out to
the setup engine with your Admin key. In an **interactive** Claude Code session you'll be
**prompted to approve** each engine command (`python … scripts/linear_setup.py …`) — approve
them, or choose **"don't ask again"** to clear the rest of the run. That approval prompt is
the consent step; the key itself never appears in the prompt or in agent context (the engine
reads it internally).

Running **unattended** — headless, CI, or an auto-approval mode — an agent can't
self-authorize a live write to your shared workspace, by design. Pre-allow the engine once:
add a rule like `Bash(python … scripts/linear_setup.py:*)` to your Claude Code settings
(`/permissions` → **Allow** → Bash), or simply run `/backlogd:init` in a normal interactive
session and approve the prompts. Either path applies **only** to this one-time setup — the
runtime loop stays key-free and prompts you for nothing.

### What it configures

- **Labels.** Ensures the three canonical labels exist, all lowercase: `problem` (the
  product-owner-filed marker), `kind:ops` (an ops-only unit — no worktree, no PR), and
  `blocked` (auto-managed by the loop). If your workspace has a mis-cased `Problem` from
  Linear's defaults, `init` renames it to `problem` in place, preserving the label's id and
  every issue already tagged with it. (The runtime `agent:*` labels are created by the loop
  on demand and deliberately *not* seeded here.)
- **Workflow states.** Verifies the five Linear state categories the forecast and queue math
  depend on — `backlog`, `unstarted`, `started`, `completed`, `canceled` — and additively
  fills any category that has no live state. It never renames, reorders, or deletes an
  existing state. backlogd's loop also uses a second `started` state for In Review (so a
  typical board carries seven states across those categories) and a `duplicate` cancellation
  state; `init` won't auto-create those two — if they're missing it flags them for you to add
  in the Linear UI rather than guessing.
- **Templates.** Ensures the three canonical templates ADR-003 decides, all idempotent
  (re-running when they already match changes nothing):
  - a `Problem` **issue** template — pre-fills the `## Problem` and `## Acceptance Criteria`
    headings (typed-AC bullets) and **applies the `problem` label**, so a templated issue is
    pickup-eligible by construction;
  - a `backlogd problem` **project** template — carries backlogd's three milestones in order
    (Investigate → Implement → Verify) plus a one-line pointer to the Spec document;
  - a `Spec` **document** template — pre-fills `## Problem` / `## Approach` /
    `## Acceptance Criteria` with the `:memo:` icon, a scaffold for hand-authoring a spec.

  The designed bodies live in one place — `CANONICAL_TEMPLATES` in
  [`scripts/linear_setup.py`](../../scripts/linear_setup.py) — so the command never improvises
  the `templateData` and the content stays consistent with ADR-003. (No **project label** is
  seeded: nothing in the loop reads one and the engine has no project-label write verb, so
  ADR-003 deliberately ships none — a future project label would need a new verb first.)

### The cleanup offer is conservative and confirmation-gated

The audit also flags non-canonical labels, but it is deliberately cautious about deletion:

- It **recommends** removing only labels that clearly duplicate native Linear features —
  the `priority:*` family (Linear has a built-in Priority field) and unused default labels
  (`Feature` / `Bug` / `Improvement`) that carry **zero** issues.
- Every other non-canonical label goes in a *review* list with **no** recommendation —
  `init` will never touch those.
- Nothing is deleted automatically. `init` asks **per group**, with the default answer
  **No**, and deletes a group only on an explicit yes for that group. A blank or absent
  answer leaves everything in place. There is no blanket "delete all" path.

So the worst case of accepting the defaults is additive: labels created, a mis-cased label
recased, state gaps filled, templates ensured — and not a single deletion unless you said
yes to a specific group.

## 4. The runtime stays key-free

Once setup is done, put the key away — the loop never reads it again. The runtime commands
reach Linear exclusively through the official Linear MCP (OAuth):
[`/backlogd:scope`](../../commands/scope.md), [`/backlogd:solve`](../../commands/solve.md),
[`/backlogd:status`](../../commands/status.md), [`/backlogd:review`](../../commands/review.md),
and [`/backlogd:release`](../../commands/release.md) all use `mcp__linear__*` tools and none
of them read an API key. Only [`/backlogd:init`](../../commands/init.md) and its engine,
[`scripts/linear_setup.py`](../../scripts/linear_setup.py), ever touch the Admin key — and
the orchestrator shells out to the engine so the key value never enters agent context.
