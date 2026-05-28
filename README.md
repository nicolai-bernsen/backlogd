# backlogd

Turn Claude Code into a problem-driven scrum team.

You file *problems*, not solutions. A scrum-master orchestrator picks them up from
Linear, dispatches developer agents that figure out the *how*, and surfaces blockers
back to you when it needs a decision. Linear is the single source of truth for the
whole loop.

## The idea

Most AI coding workflows want you to hand over a spec — a precise description of what
to build, and often how to build it. backlogd flips that. You act as the product
owner: you describe the problem and what "better" looks like. The agents own the
solution.

- **You (PO)** file a problem as a Linear issue.
- **`/backlogd:scope`** shapes that problem into an executable, decomposed issue.
- **`/backlogd:solve`** executes it — dispatches a developer that owns the *how*, opens a
  PR, and hands back a solution brief at In Review.
- **`/backlogd:status`** gives a read-only standup of progress and blockers, changing nothing.
- **`/backlogd:review`** verifies the acceptance criteria, then accepts to Done or sends it back.

Throughout, developer agents own the technical calls, blockers return to you as questions
rather than silent guesses, and everything — status, decisions, results — is recorded in Linear.

The methodology underneath — spec-driven development, small vertical slices, tests
first — is a tool the agents reach for, encouraged but not mandated. The contract is
the problem and the outcome, not the process.

## Status

Early, but the core loop works: `/backlogd:scope` shapes a problem into an executable issue,
then `/backlogd:solve` dispatches a developer agent that owns the *how* and hands back a
high-level solution brief at In Review (see [Try the walking skeleton](#try-the-walking-skeleton)).
Expect rough edges and breaking changes as the agent roster and blocker-surfacing flow grow.

## Install

backlogd is a Claude Code plugin. Add the marketplace, then install it:

```
/plugin marketplace add nicolai-bernsen/backlogd
/plugin install backlogd
```

## Setup

backlogd talks to Linear through the **official Linear MCP server** — it doesn't ship
its own API client, and there are no API keys to paste anywhere. The orchestrator owns
all Linear reads and writes; developer agents just solve and report.

1. **Enable the Linear MCP.** The server is pre-configured in [`.mcp.json`](.mcp.json),
   so Claude Code offers to enable it when you open the repo. (Equivalent manual command:
   `claude mcp add --transport http linear https://mcp.linear.app/mcp`.) First use opens
   a Linear OAuth login in your browser — auth is handled by Claude Code, nothing is
   committed to the repo.
2. **Create a `problem` label** in your Linear workspace. backlogd treats any issue
   carrying the `problem` label as product-owner-filed work. That's the whole data model:
   a problem is a labelled issue, picked up when it's still in an unstarted state.

That's the prerequisite surface for the walking skeleton. File a problem, then point the
orchestrator at your backlog.

> **How backlogd uses Linear** — the operating model (how a problem maps to issues,
> sub-issues, projects, and milestones) and the exact Linear MCP usage live in the
> [`skills/linear/`](skills/linear/SKILL.md) skill.

## Try the walking skeleton

The first slice proves the whole loop with one command. From a clean checkout:

1. Finish [Setup](#setup) — enable the Linear MCP, sign in, and create a `problem` label.
2. In Linear, create an issue describing a small problem — e.g. *"The README has no example
   of running the demo."* Add the `problem` label and leave it in your Backlog.
3. From this repo, with the plugin installed, run:

   ```
   /backlogd:solve
   ```

   (`solve` shapes the problem first if it isn't already; run `/backlogd:scope` yourself when
   you want to review the shape and decomposition before solving. Add `--dryrun`
   — `/backlogd:solve --dryrun {identifier}` — to preview the dispatch plan without touching
   Linear or git.)

4. Watch the loop:
   - the issue moves **Backlog → In Progress**,
   - a `backlogd:developer` agent picks up the problem and takes a concrete action,
   - its result is recorded as a **comment** on the issue,
   - and the issue moves to **In Review** with a high-level solution brief — accept it to
     **Done** yourself, or run **`/backlogd:review`** to check it against its acceptance criteria
     and accept or send it back (it pauses for you if the developer hits a blocker).

That's the contract: you described a problem, an agent owned the solution, and the result
is visible on the issue — no spec, no step-by-step.

Run **`/backlogd:status`** any time for a read-only standup — progress and blockers across your
active problems, with nothing changed.

## Layout

```
.claude-plugin/   plugin + marketplace manifests
agents/           subagent definitions (the developer)
commands/         slash commands — scope + solve + status + review + release (the scrum-master)
skills/           reusable skill playbooks (see skills/linear — how backlogd uses Linear)
docs/             living spec — how backlogd works and the conventions for working in it
hooks/            lifecycle hooks
.github/          continuous integration
```

## License

MIT — see [LICENSE](LICENSE).
