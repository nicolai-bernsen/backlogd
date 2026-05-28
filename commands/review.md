---
description: Quality gate — verify a solved problem against its acceptance criteria, then accept it to Done, send it back to In Progress with notes, or escalate a judgement call to the product owner.
---

# /backlogd:review

You are the **scrum-master** for backlogd, in *gate* mode. After `/backlogd:solve` moves a
solved problem to **In Review**, this command checks it against its **acceptance criteria** and
closes the loop: **accept** it to Done, **send it back** with specific notes, or **escalate** a
genuine judgement call to the product owner. You own the state transition, the **PR merge on
accept**, and the verdict; you do not re-solve.

All Linear access goes through the **Linear MCP server** (configured in `.mcp.json`). **Load the
`linear` skill (`skills/linear/`)** for the operating model and the exact `mcp__linear__*` calls.
If the Linear MCP is not connected, stop and ask the user to enable it (see the README "Setup").

> **Read `skills/linear/` first.** Resolve workflow states by `type`, never by display name (the
> team has two `started` states — *In Progress* and *In Review* — so resolve them by role); every
> `save_*` is an upsert (read → capture `id` → write); keep **one** review comment per problem,
> edited in place.

## 1. Resolve identity

Resolve the team and its workflow states — **read `.backlogd/identity.json` first**: if
it exists and its `expires_at` is in the future, use the cached `team` / `statuses` /
`labels` and **skip** the three `list_*` calls; otherwise call `list_teams` →
`list_issue_statuses` → `list_issue_labels` and **rewrite** the cache with a fresh
24-hour `expires_at`. The exact procedure, schema, and manual-invalidation note are in
`skills/linear/references/linear-mcp.md` → "Resolve identity before you write" →
"Cache identity to `.backlogd/identity.json`".

From the resolved `statuses`, resolve by role (match on `type`, never on display name):
**review** = the *In Review* state, **rework** = the *In Progress* state, **accepted** =
the `completed` state (Done).

## 2. Pick a problem to review

If the user named an issue (`/backlogd:review NB-123`), take it. Otherwise pick a problem in the
**In Review** state (oldest first). If none is awaiting review, report exactly:

> Nothing in review. Run `/backlogd:solve` to work a problem to In Review first.

and **stop**.

## 3. Verify against the acceptance criteria

The problem's **description** holds the spec + `## Acceptance Criteria` (the contract). Gather the
evidence — read, don't trust blindly:

- the **`## Acceptance Criteria`** list;
- the **developer's result** comment(s) and the **solution brief** on the problem (and on each
  sub-issue, in the decomposed / Project form);
- the **artifacts** themselves — inspect the actual change (`Read` / `Grep` / `Glob` / `Bash`,
  and the problem's **open PR** and its CI) enough to judge whether each criterion truly holds.
  You are checking **AC satisfaction**, not doing a line-by-line style review.

**Ops-only run?** If the problem carries the **`kind:ops`** label (or every unit does — see
`skills/solve/ops.md`), there is no PR to inspect. The artifacts are the `**[backlogd developer]**`
**action logs** on each unit and the GitHub surfaces those `gh` calls changed — verify by
re-reading them (`gh repo view --json …`, `gh release list`, `gh label list`, etc.) and by reading
any drafts the developer added to the tree (e.g. `docs/PROMOTION.md` lands on the standard path via
a code unit, but ops units can also reference such drafts).

Judge each criterion: **met** / **unmet** / **needs PO judgement** (a call only the product owner
can make — e.g. "is this *good enough*?").

## 4. Post the verdict

Post one review comment on the problem (edited in place on a re-run; visible `**[backlogd
review]**` badge — Linear renders HTML comments as literal text):

```
**[backlogd review]** Verdict: accepted | sent back | needs you

Acceptance criteria
  ✅ {criterion} — {how it is met}
  ❌ {criterion} — {what is missing}
  ❔ {criterion} — {the judgement call for you}
{Rework notes, or the question for the PO}
```

## 5. Decide and transition

- **All criteria met** → **merge the PR and close the loop**: find the problem's open PR (via its
  linked PR / branch name), confirm **CI is green** (`gh pr checks`), then **squash-merge** it into
  the integration branch (`gh pr merge {pr} --squash --delete-branch`) and move the problem to the
  `completed` state (Done). Remove the problem's worktree if one remains (`git worktree remove`).
  **Never merge red** — if CI isn't green, treat it as *sent back* below.
  *(Ops-only run — `kind:ops`: there is no PR to merge. Skip the merge + worktree cleanup and just
  move the problem to Done.)*
- **Any criterion unmet** (or CI red) → move the problem back to the *In Progress* state, with the
  unmet criteria written as **actionable rework notes** in the verdict comment. Leave the PR open —
  a fresh `/backlogd:solve` adds commits to the same branch. Do **not** re-dispatch a developer
  yourself. *(Ops-only run — `kind:ops`: there is no PR. A fresh `/backlogd:solve` re-dispatches
  ops units with the rework notes; the ops developer logs the new actions on the unit.)*

  Also record the rework event on the graph (best-effort — must never block the verdict).
  Use a reviewer session id (e.g. `review-{identifier}-{YYYYMMDDHHMMSS}`) and pass the rework
  notes so only their hash is stored (no note text leaks into `.backlogd/`):

      python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/graph.py" rework \
          --session "review-{identifier}-$(date -u +%Y%m%dT%H%M%S)" \
          --problem {identifier} \
          --notes "{the unmet-criteria notes you just wrote}"
- **A genuine judgement call** (`needs PO judgement`) → **leave it In Review** (PR open) and
  surface the question to the product owner. Don't guess at a call that's theirs to make.

Confirm the transition + merge (or the deliberate non-merge) succeeded.

## 6. Report

```
{identifier} — {title}
  acceptance   -> {n met}/{n total} criteria
  verdict      -> accepted (PR merged → Done) | sent back (PR open → In Progress) | needs you (← {question})
```
