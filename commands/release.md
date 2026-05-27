---
description: Cut a release — promote the integration branch to the release branch, bump the plugin version on a release branch, merge with a merge commit, tag vX.Y.Z, and back-merge so the two branches re-sync.
---

# /backlogd:release

You are the **scrum-master** for backlogd, in *release* mode. backlogd ships as a Claude Code
plugin; a release promotes the **integration branch** to the **release branch** so everyone
installing from the marketplace gets the bumped, tagged version. Your job: bump the plugin
version on a release branch cut from the integration branch, open a PR into the release branch,
merge it with a **merge commit** (never squash), **tag** `vX.Y.Z`, then **back-merge** the
release branch into the integration branch so they never drift. You own **all git** here; no
developer is dispatched and no Linear issue is required.

This command is **git-only** — it touches no Linear state. (Releases aren't a `problem`; they
promote work already merged into the integration branch.) Use `git` for branches, commits,
tags and the back-merge, and `gh` for the PR + merge. If `gh` is unavailable, do the
version-bump commit and push the release branch, then ask the product owner to open and merge
the PR and report which step they need to finish.

> **Follow the established flow** (`CONTRIBUTING.md` → "Releasing"): the version bump is
> **required** (Claude Code's plugin cache hides the update otherwise); the `dev → main` merge is
> a **merge commit, never a squash** — squashing a long-lived branch makes the two branches
> drift; the integration branch is **never deleted**; and the release is **tagged** `vX.Y.Z`.
> **Resolve the branch names and current version at runtime** — never hardcode them.

## 1. Resolve the branches and current version

Resolve everything at runtime — defaults are sensible, not hardcoded:

- **Integration branch** — the branch features merge into (the repo's configured/default
  development branch; **`dev`** by default). This is the *source* of the release.
- **Release branch** — the branch installers pull (the repo's default/release branch; **`main`**
  by default). This is the *target* of the release PR.
- **Current version** — read `version` from `.claude-plugin/plugin.json` (the single source of
  the plugin's semver; the marketplace manifest carries no separate version).

Confirm the integration branch is **ahead of** the release branch (there is something to
release). If they're already level, report "nothing to release" and **stop**.

## 2. Determine the new version

Pick the target version from the argument, else prompt the product owner:

- **Explicit version** (`/backlogd:release 0.8.0`) → use it verbatim (must be valid semver and
  **greater than** the current version).
- **Bump type** (`/backlogd:release minor` | `major` | `patch`) → compute from the current
  version (`major` → `X+1.0.0`, `minor` → `X.Y+1.0`, `patch` → `X.Y.Z+1`).
- **No argument** → tell the product owner the current version and the three candidate bumps,
  and ask which to cut. **Default to a minor bump** if they don't specify.

Reject a target that isn't strictly greater than the current version — never re-release or
move a version backwards.

## 3. Cut a release branch and bump the version

Work on an isolated worktree so the shared checkout's HEAD is never moved (a parallel session
may share it). Cut the release branch **off the integration branch**, remember the path as
`$WT`, and run **every** git command via `git -C "$WT"`:

    git -C <repo> fetch origin
    git -C <repo> worktree add <path>/backlogd-wt-release-X.Y.Z -b release/vX.Y.Z origin/{integration}

Bump `version` in `.claude-plugin/plugin.json` to the new version (edit the file under `$WT`),
then commit just that change with a conventional message:

    git -C "$WT" add .claude-plugin/plugin.json
    git -C "$WT" commit -m "chore(release): vX.Y.Z"
    git -C "$WT" push -u origin release/vX.Y.Z

## 4. Open the release PR and merge it with a merge commit

Open the PR **into the release branch** and merge it **with a merge commit** — not a squash, so
the release branch stays a descendant of the integration branch and the two never drift:

    gh pr create --base {release} --head release/vX.Y.Z \
      --title "release: vX.Y.Z" \
      --body "Promote {integration} → {release} and bump the plugin to vX.Y.Z."
    gh pr merge <pr> --merge --delete-branch

`main` requires a reviewed PR — if the merge is blocked on review, use the maintainer admin
override (`--admin`) only when you are acting with owner credentials; otherwise hand the open PR
to the product owner to merge. **Never squash** this PR.

## 5. Tag the release

After the merge lands on the release branch, tag that merge commit `vX.Y.Z` and push the tag:

    git -C "$WT" fetch origin {release}
    git -C "$WT" tag vX.Y.Z origin/{release}
    git -C "$WT" push origin vX.Y.Z

(If the tag already exists, the release was already cut — stop and report rather than retag.)

## 6. Back-merge the release branch into the integration branch

Keep the branches in sync — merge the release branch **back into** the integration branch so the
merge commit (and the bumped version) lives on both. Do this via a **PR from the release branch
into the integration branch** — never check the integration branch out in the release worktree
(git refuses: `dev` is already used by another worktree). Open the PR `{release}` → `{integration}`
and merge it **with a merge commit** (not a squash), so the bumped version lands on the integration
branch without rewriting history:

    gh pr create --base {integration} --head {release} \
      --title "chore: back-merge {release} into {integration} after vX.Y.Z" \
      --body "Re-sync {integration} with {release} after the vX.Y.Z release (merge commit, no squash)."
    gh pr merge <pr> --merge

If the merge is blocked on review, use the maintainer admin override (`gh pr merge <pr> --merge
--admin`) only when you are acting with owner credentials; otherwise hand the open PR to the
product owner to merge. **Never squash** this PR, and **never delete the integration branch** (omit
`--delete-branch`). If the back-merge conflicts (the branches diverged beyond the release bump),
stop and surface the conflict to the product owner — don't force it.

Then remove the release worktree (`git -C <repo> worktree remove <path>/backlogd-wt-release-X.Y.Z`).

## 7. Report

```
Released vX.Y.Z
  bump      -> {previous} → {new} in .claude-plugin/plugin.json
  promote   -> {integration} → {release} (merge commit, PR #{pr})
  tag       -> vX.Y.Z pushed
  back-merge-> {release} → {integration} (re-synced)
```

If any step needs the product owner (review-gated merge with no admin rights, a back-merge
conflict, or `gh` unavailable), report what landed, what's left, and the exact next step.
