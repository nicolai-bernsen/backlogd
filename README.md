# backlogd

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
- **A standards-enforcing quality gate.** An *independent* reviewer verifies every
  increment against its acceptance criteria, the [Definition of
  Done](docs/scrum/definition-of-done.md), and the standards corpus — and **blocks on a
  missing load-bearing standard instead of guessing.** Most plugins have no quality gate
  at all.
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

📹 *Demo recording coming soon.*

Until the cast lands, the exact beats it records against — file a problem, the team picks
it up, the reviewer **blocks on a missing standard**, the PO defines it, the team resolves
it, the PR merges — are written out as the **Demo run-of-show** in
[docs/ROADMAP.md](docs/ROADMAP.md#demo-run-of-show). The strongest framing: it is backlogd
solving a backlogd problem.

<!-- NB-396: embed the asciinema cast / GIF here once recorded. Drop it directly under the
     "Watch it work" heading and remove the "Demo recording coming" line above. -->

## The loop

Most AI coding workflows want you to hand over a spec — a precise description of what to
build, and often how to build it. backlogd flips that. You describe the *problem* and what
"better" looks like; the agents own the *solution*.

- **You (PO)** file a problem as a Linear issue (the `problem` label).
- **`/backlogd:scope`** shapes that problem into an executable, decomposed issue — it
  writes the `## Acceptance Criteria` and splits the work on discovery.
- **`/backlogd:solve`** executes it — dispatches a developer per unit of work (in
  parallel when the units are blocked-by-independent), opens **one** PR, hands back a
  solution brief at In Review, then **auto-chains the independent verdict review and, on a
  fully-green result, merges to Done with no human gate** (ship-on-green, on by default;
  `--no-ship` holds it at In Review). On ops-only problems (e.g. tweaking GitHub repo
  settings) it skips the worktree entirely — no PR, just an action log on the issue.
- **`/backlogd:review`** is the manual re-entry to the same gate: it dispatches an
  **independent reviewer agent** to verify the acceptance criteria against the diff (with
  a fresh context, running the checks itself), then accepts to Done (merging) or sends it
  back. On the happy path `/backlogd:solve` already ran this for you.
- **`/backlogd:status`** gives a read-only standup of progress and blockers, changing
  nothing.
- **`/backlogd:retro`** closes the adaptation loop: it reads the execution graph, detects
  cross-issue patterns, and files candidate improvements back into the backlog for you to
  prioritise.

Throughout, developer agents own the technical calls, blockers return to you as questions
rather than silent guesses, and everything — status, decisions, results — is recorded in
Linear, the single source of truth for the whole loop.

The methodology underneath — spec-driven development, small vertical slices, tests first —
is a tool the agents reach for, encouraged but not mandated. The contract is the problem
and the outcome, not the process.

## Status — honest, and on purpose

**`main` is v0.17.0.** The core loop works end to end, and backlogd is built by running it
on itself (dogfooded) — that is the strongest proof it works.

**Both 1.0 gates have shipped:**

- The independent reviewer **enforces the standards corpus and blocks on a missing
  load-bearing standard** — the moment that distinguishes a *team* from a single-agent
  runner.
- **`/backlogd:retro`**, the retrospective / adaptation loop, is shipped *and dogfooded*: a
  real retro run read the execution graph and filed a genuine improvement back into the
  backlog. The adaptation pillar is fully closed, not merely shipped.

So all three of Scrum's empirical pillars are real: **transparency** (Linear is the system
of record, with visible per-agent identity), **inspection** (the execution graph plus the
independent verdict review), and **adaptation** (standards growth, ADR supersession, and
the dogfooded retro).

**What works today:**

- The commands `/backlogd:scope` · `:solve` · `:status` · `:review` · `:retro` · `:init`.
- **Specialist dispatch** — `developer-<suffix>` agents pick the right craft per problem
  (see [docs/specialists.md](docs/specialists.md)).
- A **parallel walk** — independent units run concurrently.
- **Ship-on-green** — on a fully-green verdict, `solve` auto-merges and closes the issue
  (`--no-ship` holds at In Review).
- The **execution graph** ([`scripts/graph.py`](scripts/graph.py)).
- **Key-free Linear** via the official MCP, and per-session worktree isolation.

**What's explicitly *not* in 1.0** (on the roadmap, not shipped): the always-on / headless
tokenless runtime, the standards ↔ execution-graph join ("graph-DB v2"), and the full
Agent-Interaction-Protocol identity (1.0 ships the visible comment-badge identity, not the
full protocol).

What remains for the 1.0 *declaration* is the launch trio — this README, the demo
recording, and the announcement — plus the 1.0.0 version bump. The substance has shipped;
launch-readiness is what's left.

The full **Definition of 1.0**, the minimal end-to-end loop, and the complete *what is
explicitly out* list live in [docs/ROADMAP.md](docs/ROADMAP.md) — so you can see what's
built before you install and never bounce off an unbuilt feature. You can file a problem,
or pick up an open one, on the public
[issue tracker](https://github.com/nicolai-bernsen/backlogd/issues).

## Quickstart

### Prerequisites

- **Claude Code** with plugin support.
- **The official Linear MCP server** — backlogd talks to Linear through it, and there are
  no API keys to paste. The server is pre-configured in [`.mcp.json`](.mcp.json), so Claude
  Code offers to enable it when you open the repo. (Equivalent manual command:
  `claude mcp add --transport http linear https://mcp.linear.app/mcp`.) First use opens a
  Linear OAuth login in your browser; auth is handled by Claude Code, nothing is committed.
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

The first slice proves the whole loop with one command. From a clean checkout, with the
prerequisites above in place:

1. In Linear, create an issue describing a small problem — e.g. *"The README has no example
   of running the demo."* Add the `problem` label and leave it in your Backlog.
2. From this repo, with the plugin installed, run:

   ```text
   /backlogd:solve
   ```

   (`solve` shapes the problem first if it isn't already; run `/backlogd:scope` yourself
   when you want to review the shape and decomposition before solving. Add `--dryrun` —
   `/backlogd:solve --dryrun {identifier}` — to preview the dispatch plan without touching
   Linear or git, or `--no-ship` to stop at In Review instead of auto-merging on green.)

3. Watch the loop:
   - the issue moves **Backlog → In Progress**,
   - a `backlogd:developer` agent picks up the problem and takes a concrete action,
   - its result is recorded as a **comment** on the issue,
   - the issue moves to **In Review** with a high-level solution brief,
   - and `/backlogd:solve` **auto-chains the independent verdict review and, on a
     fully-green result, merges the PR and moves the issue to Done — no second command**
     (ship-on-green). You are interrupted only if it is sent back, needs a judgement call
     from you, or hits a blocker. (Ran with `--no-ship`, or want to re-check a held
     problem? Run **`/backlogd:review`** to verify it against its acceptance criteria and
     accept or send it back.)

That's the contract: you described a problem, an agent owned the solution, and the result
is visible on the issue — no spec, no step-by-step.

Run **`/backlogd:status`** any time for a read-only standup — progress and blockers across
your active problems, with nothing changed.

### Bootstrap your workspace (optional)

The `problem` label is the only thing the loop strictly needs, but a fresh Linear workspace
can be brought fully into backlogd's canonical shape — the `problem` / `kind:ops` /
`blocked` labels, the workflow-state categories the forecast reads, and the issue/project
templates — in one pass with **`/backlogd:init`**. It runs the audit first (try
`/backlogd:init --dryrun` to preview the plan and change nothing), applies only additive,
idempotent fixes by default, and never deletes anything without an explicit per-group yes.

This is the *one* place backlogd uses a local Linear Admin API key — read by a setup
engine, never by the orchestrator or any agent. The runtime loop stays key-free / MCP-only
after setup. See [docs/guides/workspace-bootstrap.md](docs/guides/workspace-bootstrap.md)
for the key-creation walkthrough and exactly what `init` configures.

> **Identity cache.** On first use, the scrum-master commands resolve your Linear team,
> its workflow states, and its labels, and snapshot them to `.backlogd/identity.json` with
> a 24-hour TTL — subsequent runs short-circuit the three `list_*` calls. The directory is
> gitignored. If you rename a workflow state or add a label backlogd should know about
> inside the 24-hour window, **delete `.backlogd/identity.json`** to force a refresh on the
> next run.
>
> **How backlogd uses Linear** — the operating model (how a problem maps to issues,
> sub-issues, projects, and milestones) and the exact Linear MCP usage live in the
> [`skills/linear/`](skills/linear/SKILL.md) skill.

## For Product Owners

The PO's daily job in backlogd is small: notice blockers, glance at what's in flight, trust
the forecast. Two Linear saved views and one `## 📊 Forecast` block on your engagement
Project make the whole check fit in 60 seconds, click-free.

See [docs/guides/po-overview.md](docs/guides/po-overview.md) for the exact filter specs,
sort and grouping setup, and the daily routine.

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

## Layout

```text
.claude-plugin/   plugin + marketplace manifests
agents/           subagent definitions (refiner / developer / tester / reviewer)
commands/         slash commands — scope + solve + status + review + retro + release + init
skills/           reusable skill playbooks (see skills/linear — how backlogd uses Linear;
                  skills/reviewer — the independent-review trust model;
                  skills/solve — the executing loop; skills/retro — the adaptation loop;
                  skills/worktree-isolation — the per-session worktree pattern that lets
                  the loop dispatch in parallel)
docs/             living spec — how backlogd works and the conventions for working in it
docs/scrum/       scrum guide + mapping + DoD (the Scrum operating model)
docs/standards/   the standards corpus (ADRs) the reviewer enforces
hooks/            lifecycle hooks (incl. the git-identity guard — see CONTRIBUTING.md)
.github/          continuous integration
```

## Contributing

backlogd is early and opinionated. The best contribution is a *problem*: open an issue
describing what's wrong and what "better" looks like — not a prescribed fix — which mirrors
how the tool itself works. See [CONTRIBUTING.md](CONTRIBUTING.md) for the branching flow,
the Definition of Done human PRs ship to, and the git-identity guard.

## License

MIT — see [LICENSE](LICENSE).

[cca]: https://github.com/anthropics/claude-code-action
