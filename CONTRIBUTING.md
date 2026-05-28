# Contributing

Thanks for taking a look. backlogd is early and opinionated, so a quick read first
will save us both time.

## The short version

- **Found a problem?** Open an issue describing the problem and what "better" would
  look like — not a prescribed fix. That mirrors how the tool itself works.
- **Want to change code?** Open a draft PR early and explain the reasoning. Small,
  focused changes land faster than large ones.
- **Keep it green.** CI runs on every push and pull request. Don't merge red.
- **Play by the same rules as the agent loop.** Human contributions ship to the same
  [Definition of Done](docs/scrum/definition-of-done.md) that `/backlogd:review` enforces on agent PRs.

## Working on the plugin

This repo is a Claude Code plugin. The pieces live in conventional directories:

- `agents/` — subagent definitions
- `commands/` — slash commands
- `skills/` — skill playbooks (e.g. [`skills/linear/`](skills/linear/SKILL.md) — how backlogd navigates Linear)
- `hooks/` — lifecycle hooks
- `.claude-plugin/plugin.json` — the manifest

### Git identity guard (run once)

backlogd ships a git **identity guard** so a commit never lands under the wrong identity —
the failure mode behind #301, where a worktree whose path doesn't match a personal
`includeIf` silently falls back to a global/work email. Arm it once per checkout:

```sh
sh hooks/install-git-hooks.sh you@example.com
```

That points `core.hooksPath` at the committed `hooks/git/` and records your address in
`git config backlogd.expectedEmail`. From then on a commit whose `user.email` doesn't
match is **hard-blocked** by `hooks/git/pre-commit`, and each Claude Code session **warns**
on a mismatch via the plugin's SessionStart hook. The guard is a no-op until
`backlogd.expectedEmail` is set, so it never interferes with other repos.

> Running concurrent Claude Code sessions? Give each its **own checkout** (a dedicated
> `git clone`), never a shared one — see #301.

## Branching & releases

backlogd uses a **`feature → dev → main`** flow:

- **`main`** — the default branch and the **release** branch. It only moves through reviewed PRs and stays releasable at all times.
- **`dev`** — the integration branch. All feature work merges here first, gated by green CI.
- **Feature branches** — branch off **`dev`**, name them `nicolaibernsen/nb-<n>-<slug>` (`<n>` is the issue number), and open a PR **into `dev`**.

Enforced on the repo:

- PRs into `dev` require passing CI before merge.
- `main` requires a reviewed PR (maintainers release via an admin merge).
- **`feature → dev`** PRs are **squash-merged**, and the feature branch is **auto-deleted** on merge.
- **`dev → main`** releases use a **merge commit** (never squash), so `main` stays a descendant of `dev` and the two never drift; **`dev` is never deleted**.

### Releasing

Releases promote `dev → main`:

1. Open a PR from `dev` into `main`.
2. Bump `version` in `.claude-plugin/plugin.json` (semver) — required, or Claude Code's plugin cache hides the update.
3. Merge to `main` with a **merge commit** (not squash — squashing a long-lived branch makes `dev` and `main` drift apart), then tag the release (`vX.Y.Z`). Leave `dev` in place.

This keeps `main` clean and versioned for everyone installing from the marketplace.

## Commits

Conventional Commits style, present tense:

```
feat: add scrum-master dispatch loop
fix: handle empty Linear backlog
docs: clarify install steps
```

## Code of conduct

Be decent. Assume good faith. That's the whole policy.
