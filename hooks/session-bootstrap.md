## backlogd — session bootstrap

You are in a **backlogd** checkout — a problem-driven scrum team driven from Linear.

**Verb surface** (`/backlogd:*`):

- **`/backlogd:scope`** — shape a Linear *problem* into an executable, decomposed issue:
  write acceptance criteria, split into sub-issues, sequence with blocked-by. Then stop —
  no solving.
- **`/backlogd:solve`** — execute a shaped problem: dispatch a developer per unit of work
  in dependency order, record each result, hand off a solution brief at In Review.
  `kind:ops` problems route to a no-worktree gh/repo-ops path. `--dryrun` previews the
  dispatch plan without touching Linear or git.
- **`/backlogd:review`** — quality gate: dispatch an independent reviewer against the
  solved problem's acceptance criteria, then act on the verdict (accept to Done, send
  back to In Progress, or escalate).
- **`/backlogd:status`** — scrum-master standup: survey active problems, report
  progress + blockers, refresh the rolling-7-day forecast on the engagement Project.
- **`/backlogd:release`** — cut a release: promote the integration branch to the release
  branch, bump the plugin version, tag `vX.Y.Z`, and back-merge to re-sync.

**Linear access — official MCP only.** Everything that touches Linear goes through the
official Linear MCP (`mcp__linear__*`, OAuth via Claude Code). There is **no API key** and
**no Linear/ADO CLI** in this repo — key-free, official MCP only is a core design
principle. If a command's instructions reference a CLI, substitute the equivalent
`mcp__linear__*` tool.

> New `/backlogd:*` commands take effect only after a plugin update + reload — a running
> session loads the installed plugin, not the working tree.
