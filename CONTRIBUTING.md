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

### MCP tools in subagent frontmatter — pre-load required (NB-340)

If you add a new subagent that needs an `mcp__*` tool in its frontmatter, **add a
pre-load step to the orchestrating command** that calls that tool from the
orchestrator's context **before** the first `Agent({subagent_type: ...})` dispatch.
Subagents inherit only the deferred MCP tools the parent has already loaded — a tool
listed in the frontmatter is not guaranteed to be granted at runtime otherwise. See
`commands/solve.md` step 0 and `skills/linear/SKILL.md` → *NB-340: tool-grant hazard
the orchestrator must work around* for the pattern. Skipping the pre-load is the
single most likely reason a "tools-look-right" subagent silently can't write to
Linear.

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

> Running concurrent Claude Code sessions? Give each its own isolated **git worktree** (or,
> as a stronger fallback, its own dedicated `git clone`) — never a shared checkout. The
> pattern (worktree per session, identity-guard arm step, `git worktree lock` /
> no-prune-while-live, the dedicated-clone escalation, and the rejected third-party
> orchestrators) is in
> [`skills/worktree-isolation/SKILL.md`](skills/worktree-isolation/SKILL.md) — load that
> skill in any session that opens or re-enters a worktree. Background: #301.

### Linting & checks

Style and hygiene are enforced by [`pre-commit`](https://pre-commit.com). Install the
hooks once, then let them run on every commit:

```sh
pip install pre-commit && pre-commit install
pre-commit run --all-files   # run every hook over the whole tree once
```

A single [`.pre-commit-config.yaml`](.pre-commit-config.yaml) drives both the local hooks
and the CI `pre-commit/action` step, so what passes locally is what CI runs.

**What gates `dev` (blocking — these run in CI on every pull request):**

| Check | What it catches |
| ----- | --------------- |
| markdownlint (`markdownlint-cli2`) | Markdown style across the docs-dense tree |
| File hygiene | Final newline, trailing whitespace, mixed line endings (normalised to LF) |
| `check-json` / `check-yaml` | Malformed JSON / YAML |
| `claude plugin validate .` | Plugin manifest is valid (with a Python JSON-manifest parse as a fallback) |
| `actionlint` | Errors in the GitHub Actions workflows |
| Internal links (`lychee --offline`) | Dead relative/internal links — offline, no network calls |
| Plugin / template / test-suite / witness checks | Required hygiene files, template headings, the Python test suite, and shipped-fix markers |

A red result on any of the above blocks the merge into `dev`.

**What's advisory (never gates):** external-link checking runs in a *separate* weekly
[scheduled workflow](.github/workflows/links-external.yml) (plus manual dispatch), reaching
the live internet. It has no pull-request trigger, so a flaky or transient external link
can never fail a PR — instead it opens (or refreshes) a tracking issue when a link rots.

A `ruff` (Python lint) hook is also **wired but non-gating**: it carries
`stages: [manual]`, so `pre-commit run --all-files` (and therefore CI) skips it and it is
*not* one of the checks that gate `dev`. Run it on demand with
`pre-commit run --hook-stage manual ruff-check`. Turning ruff into an enforced gate is
deferred to a future change.

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

**Before you start:** run `/plugin update` so your local `/backlogd:release` cache matches the repo. Releases require the latest release script to ensure shipped fixes (e.g. NB-311's §6 back-merge — fixed in v0.8.1) are in effect; the script itself bails via the **§0 preflight** if the cached version is older than the repo's `plugin.json`. See `commands/release.md` for the check.

1. Open a PR from `dev` into `main`.
2. Bump `version` in `.claude-plugin/plugin.json` (semver) — required, or Claude Code's plugin cache hides the update.
3. Merge to `main` with a **merge commit** (not squash — squashing a long-lived branch makes `dev` and `main` drift apart), then tag the release (`vX.Y.Z`). Leave `dev` in place.

This keeps `main` clean and versioned for everyone installing from the marketplace.

## Commits

Conventional Commits style, present tense:

```text
feat: add scrum-master dispatch loop
fix: handle empty Linear backlog
docs: clarify install steps
```

## Code of conduct

Be decent. Assume good faith. That's the whole policy.
