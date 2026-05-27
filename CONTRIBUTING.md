# Contributing

Thanks for taking a look. backlogd is early and opinionated, so a quick read first
will save us both time.

## The short version

- **Found a problem?** Open an issue describing the problem and what "better" would
  look like — not a prescribed fix. That mirrors how the tool itself works.
- **Want to change code?** Open a draft PR early and explain the reasoning. Small,
  focused changes land faster than large ones.
- **Keep it green.** CI runs on every push and pull request. Don't merge red.

## Working on the plugin

This repo is a Claude Code plugin. The pieces live in conventional directories:

- `agents/` — subagent definitions
- `commands/` — slash commands
- `skills/` — skill playbooks
- `hooks/` — lifecycle hooks
- `.claude-plugin/plugin.json` — the manifest

## Branching & releases

backlogd uses a **`feature → dev → main`** flow:

- **`main`** — the default branch and the **release** branch. It only moves through reviewed PRs and stays releasable at all times.
- **`dev`** — the integration branch. All feature work merges here first, gated by green CI.
- **Feature branches** — branch off **`dev`**, name them `nicolaibernsen/nb-<n>-<slug>` (`<n>` is the issue number), and open a PR **into `dev`**.

Enforced on the repo:

- PRs into `dev` require passing CI before merge.
- `main` requires a reviewed PR (maintainers release via an admin merge).
- Merges are **squash-only**; the feature branch is **auto-deleted** on merge.

### Releasing

Releases promote `dev → main`:

1. Open a PR from `dev` into `main`.
2. Bump `version` in `.claude-plugin/plugin.json` (semver) — required, or Claude Code's plugin cache hides the update.
3. Merge to `main` and tag the release (`vX.Y.Z`).

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
