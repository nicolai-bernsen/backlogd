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
- **The scrum-master** reads the backlog, plans, and dispatches the work.
- **Developer agents** implement, test, and report back — owning the technical calls.
- **Blockers** return to you as questions, not silent guesses.
- **Everything** is recorded in Linear: status, decisions, results.

The methodology underneath — spec-driven development, small vertical slices, tests
first — is a tool the agents reach for, encouraged but not mandated. The contract is
the problem and the outcome, not the process.

## Status

Early. This repository currently holds the public-repo foundation and plugin
scaffolding. The first working slice — pull a problem from Linear, dispatch a
developer agent, write the result back — is in progress. Expect rough edges and
breaking changes.

## Install

backlogd is a Claude Code plugin. Once the first slice lands:

```
/plugin marketplace add nicolai-bernsen/backlogd
/plugin install backlogd
```

For now, clone the repo and explore.

## Layout

```
.claude-plugin/   plugin + marketplace manifests
agents/           subagent definitions (scrum-master, developers)
commands/         slash commands
skills/           reusable skill playbooks
hooks/            lifecycle hooks
.github/          continuous integration
```

## License

MIT — see [LICENSE](LICENSE).
