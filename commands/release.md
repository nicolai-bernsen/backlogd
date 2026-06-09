---
description: Cut a release — promote the integration branch to the release branch, bump the plugin version on a release branch, merge with a merge commit, tag vX.Y.Z, and back-merge so the two branches re-sync.
---

<!-- release-script-version: 1.3.1 -->

# /backlogd:release

You are the **scrum-master** for backlogd, in *release* mode. backlogd ships as a Claude Code
plugin; a release promotes the **integration branch** to the **release branch** so everyone
installing from the marketplace gets the bumped, tagged version. Your job: bump the plugin
version on a release branch cut from the integration branch, open a PR into the release branch,
merge it with a **merge commit** (never squash), **tag** `vX.Y.Z`, then **back-merge** the
release branch into the integration branch so they never drift. You own **all git** here; no
developer is dispatched and no Linear issue is required.

This command is **git-first**; after tagging it also posts the release to Linear (per-issue
"Shipped" comments + an Initiative/Project roll-up) via the MCP — see
[`skills/linear/references/documents-and-updates.md`](../skills/linear/references/documents-and-updates.md)
→ "Release Shipped summaries" for the verified call shapes and the idempotency rules.
(Releases aren't a `problem`; they promote work already merged into the integration branch —
**no developer is dispatched and no Linear *issue* is required**.) Use `git` for branches,
commits, tags and the back-merge, `gh` for the PR + merge + GitHub Release, and the Linear
MCP for the Shipped summaries. If `gh` is unavailable, do the version-bump commit and push
the release branch, then ask the product owner to open and merge the PR and report which
step they need to finish.

> **Follow the established flow** (`CONTRIBUTING.md` → "Releasing"): the version bump is
> **required** (Claude Code's plugin cache hides the update otherwise); the `dev → main` merge is
> a **merge commit, never a squash** — squashing a long-lived branch makes the two branches
> drift; the integration branch is **never deleted**; and the release is **tagged** `vX.Y.Z`.
> **Resolve the branch names and current version at runtime** — never hardcode them.

## 0. Pre-load deferred tools (NB-340 / NB-346)

**Before any other operation in this command**, eagerly pre-load the Linear MCP
deferred tools. `/backlogd:release` is **git-only today** — it touches no Linear state
and dispatches no subagents — so this step is effectively a no-op on the current
flow. It is kept here for two reasons: (a) consistency across every `/backlogd:*`
command (the §0 idiom is the contract — see `skills/linear/SKILL.md` → *Deferred
tools — pre-load before dispatch*), and (b) safety against drift — if a future
release flow ever posts a release-note comment on a Linear issue, files a release
problem, or dispatches a release-notes subagent, the pre-load is already in place
and the command does not silently regress on the NB-340 tool-grant hazard.

Make a **single batched `ToolSearch` call** that names the canonical Linear MCP tool
list (identical across all `/backlogd:*` commands):

```text
ToolSearch(select: "mcp__linear__get_issue,mcp__linear__save_issue,mcp__linear__save_comment,mcp__linear__list_comments,mcp__linear__list_issue_statuses,mcp__linear__list_issue_labels,mcp__linear__list_issues,mcp__linear__list_teams,mcp__linear__list_milestones,mcp__linear__get_project,mcp__linear__save_milestone")
```

If `ToolSearch` is not available (a future Claude Code version drops it), this is a
no-op for `/backlogd:release` on the current flow — skip the fallback rather than
forcing a `mcp__linear__*` invocation the command doesn't need.

## 0.4 Parse argument tokens

Scan the arguments for the shared `key:value` tokens (`mode:report-only`, `mode:headless`,
`base:<sha>`) defined once in **`skills/common/argument-tokens.md`** — load that file for
the grammar (the position-independent syntax and the ignore-with-a-warning rule for an
unrecognised token); do not restate it. The leftover non-token argument (if any) is the
explicit version or bump type (§2). For `release`:

- **`mode:report-only`** — *plan, write nothing.* Resolve the branches + the target
  version, then **print** the promote / version-bump / tag / back-merge / Linear-write plan
  the run would execute — but touch nothing: no `worktree add`, no `plugin.json` edit, no
  `commit` / `push`, no `gh pr create` / `merge`, no `tag`, no `gh release create`, and no
  Shipped `save_comment`. Reads (resolving the version and the included-issue set) are
  allowed.
- **`mode:headless`** — documented **no-op**: `release`'s only prompt is the bump type,
  which is supplied as an argument in an unattended run; nothing else prompts. Note it and
  continue.
- **`base:<sha>`** — **warn-ignored.** `release` cuts its release branch off the
  integration branch by design, not an arbitrary base; accept it, emit the one-line "this
  verb opens no worktree base" warning, and continue unchanged.

Strip the recognised tokens, warn once for any unrecognised `key:value` token, and carry
the leftover word (if any) into §2. No tokens → behave exactly as today.

## 0.5 Preflight — confirm the release script is current

> **Stale-cache safeguard.** Claude Code loads `/backlogd:release` from your installed plugin
> cache, which can lag the repo if `/plugin update` hasn't run since the last release. A script
> that pre-dates a shipped fix (e.g. NB-311's §6 back-merge, fixed in v0.8.1) will silently run
> the broken flow. This check refuses to proceed in that state.

The `<!-- release-script-version: X.Y.Z -->` HTML comment near the top of *this* file records the
`.claude-plugin/plugin.json` version the script was released with. Compare it to the working
tree's current `plugin.json` version — strict semver compare:

1. **Read the working-tree `plugin.json` version.** From the repo root: `Read` the file
   `.claude-plugin/plugin.json`, extract the `version` field. Call it `$REPO_VERSION`.
2. **Read this script's tag.** Find the first line in this file matching
   `<!-- release-script-version: X.Y.Z -->`. Extract `X.Y.Z`. Call it `$SCRIPT_VERSION`. If the
   tag is missing or malformed, treat the script as untrusted and bail per step 3's "older" path
   — unknown age is more dangerous than known-stale.
3. **Compare** with semver order (lexicographic over numeric components, not string compare):
   - If **`$SCRIPT_VERSION < $REPO_VERSION`** (strictly older): **stop immediately** — do not
     fetch, do not open a worktree, do not touch git. Report exactly:

     > Your `/backlogd:release` script is from cache version **`$SCRIPT_VERSION`** but the repo
     > is at **`$REPO_VERSION`**. Run `/plugin update` and re-invoke `/backlogd:release`.
     > Releases require the latest release script to ensure shipped fixes (e.g. NB-311's §6
     > back-merge) are in effect.

   - Otherwise (`$SCRIPT_VERSION >= $REPO_VERSION` — cache is at least as fresh as the repo):
     log one line `release script v$SCRIPT_VERSION (cache matches repo at v$REPO_VERSION) —
     proceeding.` and continue to §1.

Bumping the tag is a manual maintenance task — any PR that modifies `/backlogd:release`'s body
must also bump `release-script-version` to the next intended release version. The release flow
itself is the natural place to remember (the `chore(release): vX.Y.Z` commit can include a tag
bump in the same change if needed).

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

```bash
git -C <repo> fetch origin
git -C <repo> worktree add <path>/backlogd-wt-release-X.Y.Z -b release/vX.Y.Z origin/{integration}
```

Bump `version` in `.claude-plugin/plugin.json` to the new version (edit the file under `$WT`),
then commit just that change with a conventional message:

```bash
git -C "$WT" add .claude-plugin/plugin.json
git -C "$WT" commit -m "chore(release): vX.Y.Z"
git -C "$WT" push -u origin release/vX.Y.Z
```

## 4. Open the release PR and merge it with a merge commit

Open the PR **into the release branch** and merge it **with a merge commit** — not a squash, so
the release branch stays a descendant of the integration branch and the two never drift:

```bash
gh pr create --base {release} --head release/vX.Y.Z \
  --title "release: vX.Y.Z" \
  --body "Promote {integration} → {release} and bump the plugin to vX.Y.Z."
gh pr merge <pr> --merge --delete-branch
```

`main` requires a reviewed PR — if the merge is blocked on review, use the maintainer admin
override (`--admin`) only when you are acting with owner credentials; otherwise hand the open PR
to the product owner to merge. **Never squash** this PR.

## 5. Tag the release

After the merge lands on the release branch, tag that merge commit `vX.Y.Z` and push the tag:

```bash
git -C "$WT" fetch origin {release}
git -C "$WT" tag vX.Y.Z origin/{release}
git -C "$WT" push origin vX.Y.Z
```

(If the tag already exists, the release was already cut — stop and report rather than retag.)

## 6. Back-merge the release branch into the integration branch

Keep the branches in sync — merge the release branch **back into** the integration branch so the
merge commit (and the bumped version) lives on both. Do this via a **PR from the release branch
into the integration branch** — never check the integration branch out in the release worktree
(git refuses: `dev` is already used by another worktree). Open the PR `{release}` → `{integration}`
and merge it **with a merge commit** (not a squash), so the bumped version lands on the integration
branch without rewriting history:

```bash
gh pr create --base {integration} --head {release} \
  --title "chore: back-merge {release} into {integration} after vX.Y.Z" \
  --body "Re-sync {integration} with {release} after the vX.Y.Z release (merge commit, no squash)."
gh pr merge <pr> --merge
```

If the merge is blocked on review, use the maintainer admin override (`gh pr merge <pr> --merge
--admin`) only when you are acting with owner credentials; otherwise hand the open PR to the
product owner to merge. **Never squash** this PR, and **never delete the integration branch** (omit
`--delete-branch`). If the back-merge conflicts (the branches diverged beyond the release bump),
stop and surface the conflict to the product owner — don't force it.

Then remove the release worktree (`git -C <repo> worktree remove <path>/backlogd-wt-release-X.Y.Z`).

## 6.5. Post the release to Linear

This is the **Linear-write** half of the release. The tag is pushed, the branches are
re-synced — now record *which problems shipped in vX.Y.Z* so Linear (which doesn't see
git) carries the same audit trail. Call shapes and idempotency markers live in
[`skills/linear/references/documents-and-updates.md`](../skills/linear/references/documents-and-updates.md)
→ "Release Shipped summaries" (Unit 0). Don't restate the mechanics here — *use* them.

### a. Compute the included-issue set

Walk **all** commits from the previous tag to the new one (not only merge commits) and
feed them to the tested pure module `scripts/release_scan.py`. This supersedes the prior
merge-only walk: on backlogd's `feature → dev → main` flow the release-branch merge commits
are `Merge pull request #N from nicolai-bernsen/main` / `… /release/vX.Y.Z`, which carry
**no Linear identity at all** — the commits that *do* carry issue identity are the
squash-merges onto the integration branch (`feat(#413): …`, `fix(#418): …`), exactly the
ones a merge-only walk skips. So gather every commit in the range and let the module
classify them:

```bash
git -C "$WT" log <prev-tag>..vX.Y.Z \
  --format="%s$(printf '\x1f')%b$(printf '\x1e')" | python scripts/release_scan.py
```

The module reads that delimited stream (subject and body per commit; the field separator
is ASCII Unit Separator `\x1f`, the record separator is Record Separator `\x1e`) and prints
two lines — the **included** set and the **advisory** set:

```text
included: NB-413, NB-418, NB-420
advisory: NB-315, NB-340, NB-398
```

It recognises every identifier form backlogd actually emits, and distinguishes a
**structural inclusion** (the commit *is* this issue's work) from an **incidental
reference**. The logic lives in the module (and its `scripts/test_release_scan.py` suite)
so it cannot drift from this prose; do **not** restate the regexes here. The contract it
implements:

- **Included** — a conventional-commit scope `feat(#N)` / `fix(#N)` / `docs(#N)` etc. (a
  bare `#N`, **no** `NB-` prefix — this is the form the old bare-`NB-N` pattern missed); a
  bare `NB-N` in the subject; a `closes` / `fixes` / `resolves` directive before an `NB-N`
  or `#N` (in the subject **or** body); and an `nb-N` segment in the head-branch name (PRs
  cut by `/backlogd:solve` follow `nicolaibernsen/nb-<n>-<slug>`, case-insensitive).
- **Advisory, not included** — an `NB-N` that appears **only** in a commit body (an
  incidental mention of a prior, already-shipped issue), reported on its own line so the
  maintainer can eyeball near-misses but never counted as shipped.
- **Dropped entirely** — the trailing GitHub PR number a squash-merge appends to the
  subject (`… (#129)`) is a PR number, not an issue; it enters **neither** set.

The module already deduplicates; the printed `included` line is the set of `NB-N` ids the
rest of §6.5 uses.

> The head-branch name is not on the commit itself, so the `git log` stream above leaves
> that field empty and the scan relies on the subject / body signals (which carry issue
> identity on backlogd's squash-merge convention). If you have the head-branch names to
> hand (e.g. from `gh pr list`), you may supply them as the third `\x1f`-delimited field
> per commit to light up the branch-segment rule too.

**Degrade gracefully.** If the range yields no Linear identifiers at all (e.g. a release
built from external contributions only, so the module prints `included: none`), fall back
to issues *completed* in the tag range — this degrade path is unchanged:

```text
list_issues({ team: "<team>", filter: { completedAt: { gte: <prev-tag date>, lte: <vX.Y.Z date> }, labels: { name: { eq: "problem" } } } })
```

(If the `problem`-label filter returns nothing, retry without it — the AC accepts "issues
completed in range" as the fallback; be explicit in the §7 report about which path was
taken.)

### b. Generate grouped release notes

Group the included issues by label / kind for the notes body — features, fixes, docs,
tech-debt (use the issue's labels via `get_issue` or the already-fetched `list_issues`
payload; default any unlabelled issue to "Other"). Render a Markdown body and write it to
a temp file the next step can hand to `gh`:

```bash
NOTES_FILE="$(mktemp -t backlogd-release-vX.Y.Z-XXXXXX).md"
cat > "$NOTES_FILE" <<'EOF'
## Features
- NB-N — <title>
…

## Fixes
- NB-N — <title>
…
EOF
```

Keep the file path; the next step needs it.

### c. Create the GitHub Release

Cut the GitHub Release on the just-pushed tag and capture its URL:

```bash
REL_URL="$(gh release create vX.Y.Z --title "vX.Y.Z" --notes-file "$NOTES_FILE")"
```

`gh release create` prints the release URL on success — capture it as `$REL_URL` for the
Linear writes below. **If `gh` is unavailable**, surface to the product owner and
**stop §6.5** here. The git tag is already pushed, so the release exists at the git level;
without a real GitHub Release URL there's nothing to link to, and the Linear writes below
must not happen with a placeholder URL — that would corrupt the audit record. Report
what's left (`gh release create` + the Linear writes) and hand off.

### d. Per-included-issue Shipped comment (idempotent)

For each `NB-N` in the included set, post the one-line marker comment — but only after
checking it isn't already there:

1. `list_comments({ issueId: "NB-N" })`.
2. If any returned body contains the substring `Shipped in vX.Y.Z` **for this exact
   version** → skip (already posted, do not edit).
3. Otherwise `save_comment({ issueId: "NB-N", body: "**[backlogd]** Shipped in vX.Y.Z — <$REL_URL>" })`.

See `documents-and-updates.md` → "Release Shipped summaries" for the verified call shape.
Real newlines in the body, never literal `\n`.

### e. Initiative / Project roll-up

For each **Initiative** or **Project** that groups one or more of the included issues
(resolve via `get_issue` → `project` / via the project's initiative link), post a single
roll-up comment so the container records the release too. Same idempotency check as the
per-issue comment — list first, skip if a `Shipped in vX.Y.Z` body already exists, else
create:

```text
save_comment({ projectId: "<project id>",     body: "**[backlogd]** Shipped in vX.Y.Z — <n> issues — <$REL_URL>" })
save_comment({ initiativeId: "<initiative id>", body: "**[backlogd]** Shipped in vX.Y.Z — <n> issues — <$REL_URL>" })
```

`save_comment` accepts exactly one parent at a time, so an Initiative and its Project each
get their own call.

### f. Idempotency note

Re-running `/backlogd:release` for an existing tag **must not duplicate comments**. The
literal substring `Shipped in vX.Y.Z` (for the exact version being cut) is the dedupe key
on every target — issue, project, initiative. List first, match the marker, skip on hit.
Shipped comments are immutable audit records; if the URL was wrong, fix it by hand — do
not let a re-run silently rewrite it.

## 7. Report

```text
Released vX.Y.Z
  bump       -> {previous} → {new} in .claude-plugin/plugin.json
  promote    -> {integration} → {release} (merge commit, PR #{pr})
  tag        -> vX.Y.Z pushed
  back-merge -> {release} → {integration} (re-synced)
  gh-release -> vX.Y.Z (<url>)
  linear     -> {n} "Shipped" comments + roll-up
  advisory   -> (not shipped-in-range): NB-315, NB-340, NB-398   # omit the line if none
```

Surface the **advisory** ids (the incidental body references the scan reported separately)
on their own line so the maintainer can eyeball near-misses against what actually shipped.
Omit the line when the advisory set is empty.

If any step needs the product owner (review-gated merge with no admin rights, a back-merge
conflict, or `gh` unavailable), report what landed, what's left, and the exact next step.
