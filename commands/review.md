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

### Typed AC — read the kind on each item and branch per kind

**Load the `ac` skill (`skills/ac/`)** before walking the AC list. It is the source of
truth for the AC grammar and the per-kind verification contract. The summary:

Each `## Acceptance Criteria` bullet may carry an optional kind prefix right after the
checkbox: `[test]`, `[manual]`, or `[review]`. Untagged → `[review]` (backwards
compatible — every existing problem keeps its current behaviour).

**Parsing rule.** For each `- [ ]` bullet, strip the leading checkbox + space, then apply
`^\[(test|manual|review)\] ` (case-sensitive, single trailing space) against the rest.
If it matches, the captured token is the kind and the remainder is the body; otherwise
kind is `review` and the whole text is the body. Apply the rule once — only the first
`[…]` qualifies; later bracketed tokens in the body are body text.

**Branch per kind on every bullet:**

- **`[test]`** — extract the **first backticked span** (`` `…` ``) from the body and
  treat it as a shell command. Run it with **Bash** from the worktree root (read-only —
  no `git add`, `commit`, or `push`):
  - exit code `0` → `✅ met` — cite the command and the exit code (or last line of
    output).
  - non-zero → `❌ unmet` — cite the command and the last few lines of stderr.
  - **no backticked command** in the body → `❔ needs PO judgement: no runnable check
    found` — do not invent one.
- **`[manual]`** — do **not** try to verify. Add the bullet (its body, verbatim) to a
  **"Manual checks for the PO"** section in the verdict comment, one bullet per item.
  Mark it `📝 awaiting PO confirmation` in the per-AC walk. The reviewer **drafts** the
  batched question; the **orchestrator** (you, running this command) actually asks the
  PO and waits for the answer before transitioning state.
- **`[review]`** — judge from the artifacts (current behaviour). `✅ met` / `❌ unmet` /
  `❔ needs PO judgement` (the last for a genuine product-owner judgement call, not for
  "I didn't run a test").

**Rollup:**

- **accepted** — every item `✅ met`, every `📝` confirmed by the PO, **and** CI green.
- **sent back** — any `❌` or CI red.
- **needs you** — any `❔`, or any `📝` left unconfirmed and no `❌` overrides.

See `skills/ac/SKILL.md` for the full grammar, the rationale for each kind, and worked
examples.

## 4. Post the verdict

Post one review comment on the problem (edited in place on a re-run; visible `**[backlogd
review]**` badge — Linear renders HTML comments as literal text):

```
**[backlogd review]** Verdict: accepted | sent back | needs you

Acceptance criteria
  ✅ [{kind}] {criterion} — {how it is met, with the cited command + exit code for [test]}
  ❌ [{kind}] {criterion} — {what is missing, with stderr snippet for a failed [test]}
  ❔ [{kind}] {criterion} — {the judgement call for you, or "no runnable check found" for a tagless [test]}
  📝 [manual] {criterion} — awaiting PO confirmation (see batch below)

Manual checks for the PO   ← only if there are [manual] items
  - {body of each [manual] bullet, verbatim}

{Rework notes, or the question for the PO}
```

Include the parsed kind in square brackets at the start of each AC line so the PO can
see, at a glance, *how* each item was checked. Items that were originally untagged
appear as `[review]` (the default).

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
- **Unconfirmed `[manual]` items** (`📝 awaiting PO confirmation`) → **leave it In Review**
  (PR open) and ask the product owner the batched **"Manual checks for the PO"** question
  from the verdict comment. Each `[manual]` bullet needs a yes/no from the PO before the
  verdict can close — `accepted` requires every `📝` resolved to a `✅`, otherwise the
  unconfirmed ones drop the verdict to `sent back` (PO answered no on at least one) or
  hold it at `needs you` (PO hasn't answered yet). Treat unanswered manual checks as a
  blocker, not a silent pass.

Confirm the transition + merge (or the deliberate non-merge) succeeded.

## 6. Report

```
{identifier} — {title}
  acceptance   -> {n met}/{n total} criteria ({t} [test], {m} [manual], {r} [review])
  verdict      -> accepted (PR merged → Done) | sent back (PR open → In Progress) | needs you (← {question})
```

The kind breakdown lets the PO see, at a glance, how teeth the AC had — a verdict
backed by `[test]` checks is a stronger signal than one backed by `[review]` alone.
