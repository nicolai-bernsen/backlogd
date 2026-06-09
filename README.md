# backlogd

[![CI](https://img.shields.io/github/actions/workflow/status/nicolai-bernsen/backlogd/ci.yml?style=flat&logo=githubactions&logoColor=white&label=CI)](https://github.com/nicolai-bernsen/backlogd/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/nicolai-bernsen/backlogd?style=flat&logo=github&logoColor=white)](https://github.com/nicolai-bernsen/backlogd/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=flat&logo=opensourceinitiative&logoColor=white)](LICENSE)
[![Claude Code plugin](https://img.shields.io/badge/Claude_Code-plugin-d97757?style=flat&logo=claude&logoColor=white)](https://claude.com/claude-code)

**backlogd is an agent *team* that runs real Scrum — any problem type — on your Claude
subscription, not API tokens.**

It is not a single agent doing one task. The framework layer is domain-agnostic Scrum
scaffolding that *never does the domain work itself* — that routes to pluggable
**specialists**. You act as the Product Owner: you file *problems*, not specs. The slash
commands are the Scrum Master; the subagents are the Developers. An instance's value is
**specialists × standards**, and the scope is **code and non-code alike** — "fix the
failing pipeline," "write the Q3 board deck," and "restructure these docs" are all valid
problems. This is a **category claim, not a feature claim** (see
[ADR-004](docs/standards/adrs/ADR-004-backlogd-identity.md)).

## Why backlogd, not the other 9,000 plugins

- **A team, not a task runner.** Most Claude Code plugins are a single agent doing a
  single task. backlogd is a *team* running the empirical Scrum loop — scope, solve,
  review, adapt — around your work.
- **Two gates, not zero.** backlogd brackets every problem with symmetric hard-rules
  gates. At the *entry*, a [Definition of Ready](docs/scrum/definition-of-ready.md)
  **interrogates** a raw idea into a crisp, falsifiable problem — Socratic, never
  generative — and refuses to *start* an unready one. At the *exit*, an *independent*
  reviewer verifies every increment against its acceptance criteria, the [Definition of
  Done](docs/scrum/definition-of-done.md), and the standards corpus — and **blocks on a
  missing load-bearing standard instead of guessing.** Most plugins have no gate at all.
- **Runs on your subscription, not API tokens** — see [below](#runs-on-your-subscription-not-api-tokens).

**vs Cyrus specifically:** Cyrus is *an agent that does your coding task* — a capable
single-task coding agent. backlogd is *an agent team that works the way good teams work,
in any domain.* It is a category claim, not a feature race: backlogd deliberately does
**not** rebuild Cyrus's runtime plumbing or duplicate its Linear Diffs.

## Runs on your subscription, not API tokens

This is the genuinely novel part. backlogd's runtime loop **ships no API client and no API
keys.** All Linear I/O goes through the **official Linear MCP over OAuth — Claude Code
authenticates as you** — so you run it on your existing **Claude subscription**, with no
metered API tokens to buy and no key to paste anywhere.

The one optional exception is a *one-time* workspace bootstrap (`/backlogd:init`), which
reads a *local* Linear Admin key used only by the setup engine — **never** by the runtime
loop. After setup, backlogd stays key-free and MCP-only. This is the keyless principle
([ADR-002](docs/standards/adrs/ADR-002-keyless-mcp.md)).

## Watch it work

Two real, back-to-back runs from this repo's own backlog — backlogd building backlogd.
Every code artifact below is public: the PRs, the commit history, the standard.

**1 · The PO files a problem, not a spec.** *"Persist a per-run solve ledger under
`.backlogd/` so re-runs and the retro can read run history."* One paragraph of outcome,
four acceptance-criteria bullets, zero implementation detail.

**2 · The team pushes back before building.** `/backlogd:scope`'s refiner reads the code
first and challenges the problem: the execution graph *already* records run history — is
this a thin view over it, a separate artifact, or a duplicate to close? The call routes to
the PO as a three-option decision. The ruling — a separate durable artifact, because
telemetry and a durable run record are different contracts — goes into the issue, and only
then does anyone build.

![The problem in Linear — the refiner's shaping note and the PO's ruling, recorded in the
issue description](docs/assets/demo-1-ruling.png)

**3 · One command solves it.** `/backlogd:solve` dispatches a developer that owns the
*how* (it chose append-only JSONL with a per-record schema `version` field), a tester that
proves every `[test]` criterion with exit codes — and an independent pre-commit gate,
which **bounced round 1**: the spec's `git check-ignore .backlogd` command is
environment-dependent on a pristine checkout. The acceptance criterion was retyped to the
deterministic file-path form; round 2 passed. The team fixed its own spec before any human
saw the diff ([PR #133](https://github.com/nicolai-bernsen/backlogd/pull/133)).

![The pre-commit gate's comment in Linear — VERDICT: ok on round 2, after the round-1
acceptance-criterion retype](docs/assets/demo-2-gate.png)

**4 · An independent reviewer verifies with receipts, then ship-on-green merges.** A
fresh-context verdict re-ran every check itself — the full 606-test suite, lint, the
gitignore invariant on a checkout where `.backlogd/` doesn't even exist — and the run
merged on the green verdict with no human gate. The ledger's first record is its own
birth-run ([`scripts/ledger.py`](scripts/ledger.py)).

![The independent verdict on the ledger in Linear — accepted, with per-criterion cited
evidence](docs/assets/demo-3-verdict.png)

**5 · The standards corpus grows on demand.** The verdict's standards walk surfaced that
the ledger's format had only per-issue authority — the *next* persisted store would have
no rule to follow. The PO answered the open question once, and the loop turned that
sentence into
**[ADR-007](docs/standards/adrs/ADR-007-persisted-on-disk-run-state-data.md)**
(append-only NDJSON · per-record `version` · grow-only schema · never commit),
regenerated the standards index, pinned it with new tests, and merged
([PR #135](https://github.com/nicolai-bernsen/backlogd/pull/135)). The reviewer's closing
line on the second verdict: *"this unit closes the persisted-data governance gap NB-426
surfaced."*

![The verdict on ADR-007 in Linear — accepted; the standards walk that closes the
governance gap](docs/assets/demo-4-standard.png)

From filed problem to two merged PRs and a new Accepted standard, the product owner made
**one product ruling and one approval** — the challenge, the build, the catches, the
verification, and the governance were the team.

<!-- NB-396: static demo artifact — annotated walkthrough of the real NB-426 → NB-427
     runs (PR #133 + PR #135), with the Linear-side screenshots embedded above from
     docs/assets/. A recorded terminal cast (docs/demo-runbook.md, good-first-issue #42)
     can augment or replace this section post-1.0. -->

*(Want the recorded version? The [demo runbook](docs/demo-runbook.md) scripts a turnkey
cast — contributions welcome via good-first-issue #42.)*

## The loop

Most AI coding workflows want a spec. backlogd flips that: you file a *problem* as a
Linear issue (the `problem` label) and describe what "better" looks like; the agents own
the *solution*, and everything — status, decisions, results — is recorded in Linear, the
single source of truth.

- **`/backlogd:scope`** — shapes a problem through the [Definition of
  Ready](docs/scrum/definition-of-ready.md): a Socratic pressure-test that writes the
  `## Acceptance Criteria`, surfaces any one-way-door decision to you, decomposes on
  discovery, and picks the specialist.
- **`/backlogd:solve`** — executes it: a developer per unit (parallel when independent),
  one PR, then the **auto-chained independent verdict review — ship-on-green merges a
  fully-green result to Done with no human gate** (`--no-ship` holds at In Review;
  `--dryrun` previews and touches nothing).
- **`/backlogd:review`** — the manual re-entry to the same gate for held or sent-back
  work.
- **`/backlogd:status`** — a read-only standup: progress, blockers, forecast.
- **`/backlogd:retro`** — reads the execution graph and files improvement candidates back
  into the backlog for you to prioritise.

Blockers come back to you as questions, never silent guesses.

### Argument tokens (scripts, `/loop`, cron)

Every long-running verb accepts the same small set of `key:value` tokens, in any position,
composably — so you can drive any `/backlogd:*` verb from a script or `/loop` without side
effects or interactive hangs. A verb invoked with no tokens behaves exactly as today; an
unrecognised token is ignored with a warning. The grammar is defined once in
[`skills/common/argument-tokens.md`](skills/common/argument-tokens.md).

- **`mode:report-only`** — print the planned actions and write nothing to Linear or git.
  Honoured by **all five verbs** (`scope` prints the spec/AC/decomposition it would write;
  `solve` is identical to `--dryrun`; `status` prints the forecast and skips the project
  write; `review` prints the verdict and merge it would make; `release` prints the
  promote/bump/tag/back-merge plan). On `solve`, `--dryrun` is the documented alias.
- **`mode:headless`** — never raise an interactive prompt; where a verb would pause for a
  decision, it fails fast with a one-line reason and stops (no silent default). Honoured by
  the prompting verbs **`scope`**, **`solve`**, and **`review`**; a documented no-op on
  **`status`** and **`release`** (neither prompts).
- **`base:<sha>`** — scope the work against a specific git base instead of the
  integration-branch HEAD. Honoured by **`solve`** (the only verb that opens a worktree);
  accepted and warn-ignored by the other four.

## Status — honest, and on purpose

**backlogd is released and self-hosting.** The core loop works end to end, and backlogd is
built by running it on itself (dogfooded) — that is the strongest proof it works. (For the
exact current version, see the [releases](https://github.com/nicolai-bernsen/backlogd/releases).)

**Both team-defining gates shipped before 1.0 — and have anchored every release since.**
The independent reviewer **enforces the standards corpus and blocks on a missing
load-bearing standard** (the moment that distinguishes a *team* from a single-agent
runner), and **`/backlogd:retro`** closes the adaptation loop — both shipped *and
dogfooded*. All three of Scrum's empirical pillars are real:
**transparency** (Linear as the system of record, visible per-agent identity),
**inspection** (the execution graph + the independent verdict review), and **adaptation**
(standards growth + the retro).

**What works today:** the commands above plus `/backlogd:init`, the entry/exit gates
(Definition of Ready and Done), specialist dispatch ([docs/specialists.md](docs/specialists.md)),
a parallel walk for independent units, ship-on-green, the execution graph
([`scripts/graph.py`](scripts/graph.py)), key-free Linear via the official MCP, and
per-session worktree isolation. **Deliberately not built yet** (roadmap): the always-on
tokenless runtime, the standards ↔ graph join, the full Agent-Interaction-Protocol identity.

What's built and what's **deliberately out of scope** live in
[docs/ROADMAP.md](docs/ROADMAP.md) — see what's real before you install, and never
bounce off an unbuilt feature. File a problem, or pick up an open one, on the public
[issue tracker](https://github.com/nicolai-bernsen/backlogd/issues).

## Quickstart

### Prerequisites

- **Claude Code** with plugin support.
- **The official Linear MCP server** — backlogd talks to Linear through it, and there are
  no API keys to paste. The server is pre-configured in [`.mcp.json`](.mcp.json), so Claude
  Code offers to enable it when you open the repo. (Equivalent manual command:
  `claude mcp add --transport http linear https://mcp.linear.app/mcp`. Use the `/mcp`
  HTTP-stream endpoint — Linear removed the older `/sse` transport, so `/mcp` is now
  required.) First use opens a Linear OAuth login in your browser; auth is handled by
  Claude Code, nothing is committed.
- **A `problem` label** in your Linear workspace. backlogd treats any issue carrying the
  `problem` label as product-owner-filed work — that is the whole data model: a problem is
  a labelled issue, picked up while it is still in an unstarted state.

### Install

backlogd is a Claude Code plugin. Add the marketplace, then install it:

```text
/plugin marketplace add nicolai-bernsen/backlogd
/plugin install backlogd
```

### Your first loop

1. In Linear, create an issue describing a small problem — e.g. *"The README has no
   example of running the demo."* Add the `problem` label and leave it in your Backlog.
2. From a repo with the plugin installed, run:

   ```text
   /backlogd:solve
   ```

   (`solve` shapes an unshaped problem first; `--dryrun` previews the plan and touches
   nothing; `--no-ship` stops at In Review instead of auto-merging on green.)

3. Watch: **Backlog → In Progress** (a developer owns the *how*, its work-log lands as a
   comment) → **In Review** (solution brief posted) → the auto-chained verdict → **merged
   and Done on green, no second command**. You are interrupted only by a real blocker or
   a judgement call.

That's the contract: you described a problem; the result is visible on the issue. Run
**`/backlogd:status`** any time for a read-only standup.

### Bootstrap your workspace (optional)

**`/backlogd:init`** brings a fresh Linear workspace into backlogd's canonical shape —
labels, workflow states, templates — in one audited, idempotent pass (`--dryrun` previews
it). It is the *one* place a local Linear Admin key is ever read, by the setup engine and
never the runtime loop. Walkthrough:
[docs/guides/workspace-bootstrap.md](docs/guides/workspace-bootstrap.md). How backlogd
uses Linear — the operating model and the identity cache — lives in
[`skills/linear/`](skills/linear/SKILL.md).

## For Product Owners

The daily PO check fits in 60 seconds: two Linear saved views plus a `## 📊 Forecast`
block on your Project. Setup + routine:
[docs/guides/po-overview.md](docs/guides/po-overview.md).

## Roadmap / open questions

A few directions we'd love help with — see the [open
issues](https://github.com/nicolai-bernsen/backlogd/issues) and
[docs/ROADMAP.md](docs/ROADMAP.md):

- **A GitHub Action variant.** [claude-code-action][cca]'s `label_trigger:` maps ~1:1 onto
  backlogd's `problem` label — a natural "backlogd on CI" path where labelling an issue
  kicks off the loop on a runner.
- **Linear-on-CI auth (open question).** The OAuth MCP has no browser on a stateless
  runner, so the loop can't sign in the way it does locally. The honest options are: (a) a
  **GitHub Issues backend** (drop Linear), (b) **require a PAT** (which breaks the no-keys
  principle), or (c) **wait for CI-friendly auth**. We don't have a settled answer — input
  and prototypes welcome.

## Contributing

backlogd is early and opinionated. The best contribution is a *problem*: open an issue
describing what's wrong and what "better" looks like — not a prescribed fix — which mirrors
how the tool itself works. See [CONTRIBUTING.md](CONTRIBUTING.md) for the branching flow,
the Definition of Done human PRs ship to, and the git-identity guard.

## License

MIT — see [LICENSE](LICENSE).

[cca]: https://github.com/anthropics/claude-code-action
