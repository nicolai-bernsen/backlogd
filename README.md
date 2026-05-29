# backlogd

Turn Claude Code into a problem-driven scrum team.

You file *problems*, not solutions. A scrum-master orchestrator picks them up from
Linear, dispatches developer agents that figure out the *how* — one at a time when the
problem is sequential, in parallel when the work earns it — and surfaces blockers back
to you when it needs a decision. Linear is the single source of truth for the whole
loop.

## The idea

Most AI coding workflows want you to hand over a spec — a precise description of what
to build, and often how to build it. backlogd flips that. You act as the product
owner: you describe the problem and what "better" looks like. The agents own the
solution.

- **You (PO)** file a problem as a Linear issue.
- **`/backlogd:scope`** shapes that problem into an executable, decomposed issue.
- **`/backlogd:solve`** executes it — dispatches a developer per unit of work (in
  parallel when the units are blocked-by-independent), opens **one** PR, and hands back
  a solution brief at In Review. On ops-only problems (e.g. tweaking GitHub repo
  settings) it skips the worktree entirely — no PR, just an action log on the issue.
- **`/backlogd:status`** gives a read-only standup of progress and blockers, changing nothing.
- **`/backlogd:review`** dispatches an **independent reviewer agent** to verify the
  acceptance criteria against the diff (it runs the checks itself, with a fresh context),
  then accepts to Done or sends it back.

Throughout, developer agents own the technical calls, blockers return to you as questions
rather than silent guesses, and everything — status, decisions, results — is recorded in Linear.

The methodology underneath — spec-driven development, small vertical slices, tests
first — is a tool the agents reach for, encouraged but not mandated. The contract is
the problem and the outcome, not the process.

The framework backlogd embodies is **Scrum**: you are the Product Owner, the slash
commands are the Scrum Master, and the team-skill subagents — `refiner`, `developer`,
`tester`, `reviewer` — are the Developers. `/backlogd:review` gates every problem against
the [Definition of Done](docs/scrum/definition-of-done.md) alongside its acceptance criteria.

## Status

Early, but the core loop works: `/backlogd:scope` shapes a problem into an executable issue,
then `/backlogd:solve` dispatches a developer agent that owns the *how* and hands back a
high-level solution brief at In Review (see [Try the walking skeleton](#try-the-walking-skeleton)).
Expect rough edges and breaking changes as the agent roster and blocker-surfacing flow grow.

## For Product Owners

The PO's daily job in backlogd is small: notice blockers, glance at what's in flight,
trust the forecast. Two Linear saved views and one `## 📊 Forecast` block on your
engagement Project make the whole check fit in 60 seconds, click-free.

See **[docs/guides/po-overview.md](docs/guides/po-overview.md)** for the exact filter
specs, sort and grouping setup, and the daily routine.

## Install

backlogd is a Claude Code plugin. Add the marketplace, then install it:

```
/plugin marketplace add nicolai-bernsen/backlogd
/plugin install backlogd
```

## Setup

backlogd talks to Linear through the **official Linear MCP server** — the runtime loop
ships no API client, and there are no API keys to paste anywhere. Auth is OAuth, handled
by Claude Code; the orchestrator owns all Linear reads and writes, and developer agents
just solve and report. (One optional, one-time exception — workspace bootstrap — is
covered [below](#bootstrap-your-workspace-optional); it never touches the runtime loop.)

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

### Bootstrap your workspace (optional)

Step 2 is the only thing the loop strictly needs, but a fresh Linear workspace can be
brought fully into backlogd's canonical shape — the `problem` / `kind:ops` / `blocked`
labels, the workflow-state categories the forecast reads, and the issue/project templates —
in one pass with **`/backlogd:init`**. It runs the audit first (try `/backlogd:init --dryrun`
to preview the plan and change nothing), applies only additive, idempotent fixes by default,
and never deletes anything without an explicit per-group yes.

This is the *one* place backlogd uses a local Linear Admin API key — read by a setup engine,
never by the orchestrator or any agent. The runtime loop stays key-free / MCP-only after
setup. See **[docs/guides/workspace-bootstrap.md](docs/guides/workspace-bootstrap.md)** for
the key-creation walkthrough and exactly what `init` configures.

> **Identity cache.** On first use, the scrum-master commands resolve your Linear team,
> its workflow states, and its labels, and snapshot them to `.backlogd/identity.json` with
> a 24-hour TTL — subsequent runs short-circuit the three `list_*` calls. The directory is
> gitignored. If you rename a workflow state or add a label backlogd should know about
> inside the 24-hour window, **delete `.backlogd/identity.json`** to force a refresh on
> the next run.

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
agents/           subagent definitions (refiner / developer / tester / reviewer)
commands/         slash commands — scope + solve + status + review + release (the scrum-master)
skills/           reusable skill playbooks (see skills/linear — how backlogd uses Linear;
                  skills/reviewer — the independent-review trust model;
                  skills/solve — the executing loop; skills/worktree-isolation — the
                  per-session worktree pattern that lets the loop dispatch in parallel)
docs/             living spec — how backlogd works and the conventions for working in it
docs/scrum/       scrum guide + mapping + DoD (the Scrum operating model)
hooks/            lifecycle hooks (incl. the git-identity guard — see CONTRIBUTING.md)
.github/          continuous integration
```

## License

MIT — see [LICENSE](LICENSE).
