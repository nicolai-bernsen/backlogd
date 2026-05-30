---
description: Quality gate — dispatch an independent reviewer subagent against a solved problem's acceptance criteria, then act on its verdict — accept to Done, send back to In Progress, or escalate a judgement call. The reviewer judges; the orchestrator acts.
---

# /backlogd:review

You are the **scrum-master** for backlogd, in *gate* mode. After `/backlogd:solve` moves a
solved problem to **In Review**, this command closes the loop: dispatch the **independent
`backlogd:reviewer` subagent** to read the artifacts with a fresh context and produce a
per-AC verdict, then **act** on that verdict — accept it to Done, send it back to In
Progress with the reviewer's notes, or escalate a judgement call to the product owner.
**The reviewer judges; you act.** You own the state transition, the **PR merge on
accept**, and the user-facing rollup comment.

All Linear access goes through the **Linear MCP server** (configured in `.mcp.json`).
**Load the `linear` skill (`skills/linear/`)** for the operating model, and the
**`reviewer` skill (`skills/reviewer/`)** for the trust model behind the dispatched
reviewer (fresh context, restricted tool grant, mandatory machine-verifiable check
execution). If the Linear MCP is not connected, stop and ask the user to enable it (see
the README "Setup").

> **Read `skills/linear/` and `skills/reviewer/` first.** Resolve workflow states by
> `type`, never by display name; every `save_*` is an upsert (read → capture `id` →
> write); keep **one** review rollup comment per problem, edited in place. The reviewer
> subagent is a separate context — you cannot answer questions for it; you can only
> hand it a complete envelope and act on what it returns.

## 0. Pre-load deferred tools (NB-340 / NB-346)

**Before any other Linear or subagent operation in this command**, eagerly pre-load the
Linear MCP deferred tools so the `backlogd:reviewer` dispatch in step 3 — which carries
an explicit, deliberately-restricted `tools:` list (see `skills/reviewer/SKILL.md` →
*NB-340: tool-grant hazard*) — receives the `mcp__linear__*` tools it names. This is
defense in depth at the orchestrator layer for the NB-340 tool-grant hazard (see
`skills/linear/SKILL.md` → *NB-340: tool-grant hazard the orchestrator must work
around*).

Make a **single batched `ToolSearch` call** that names every `mcp__linear__*` tool this
command (or the reviewer it dispatches) may touch:

```
ToolSearch(select: "mcp__linear__get_issue,mcp__linear__save_issue,mcp__linear__save_comment,mcp__linear__list_comments,mcp__linear__list_issue_statuses,mcp__linear__list_issue_labels,mcp__linear__list_issues,mcp__linear__list_teams,mcp__linear__list_milestones,mcp__linear__get_project,mcp__linear__save_milestone")
```

This is the canonical pre-load list across all `/backlogd:*` commands — keep it
identical so the idiom is recognisable. `ToolSearch` is itself a deferred tool; if it
is not available (a future Claude Code version drops it), fall back to the prior
idiom: invoke each `mcp__linear__*` tool at least once from the orchestrator's context
before the dispatch in step 3 (`get_issue` + `list_comments` in step 2, and force
`save_comment` via a scratch nudge if no comment write has happened yet).

**For Project-form problems only**, also pre-load `mcp__linear__list_documents` and
`mcp__linear__get_document` so the orchestrator can read the Project's `Spec` and
`Solution brief` Documents in step 3 and paste their bodies into the reviewer's
envelope verbatim. These reads stay on the **orchestrator** side of the boundary — the
reviewer's restricted tool grant has no `get_document`, so nothing propagates.

If you skip this step and the reviewer reports it cannot post its
`**[backlogd reviewer]**` comment, that is the NB-340 tool-grant skew — re-run with
the pre-load done, do not silently accept a tool-grant failure as a reviewer issue.

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

## 3. Gather the evidence + dispatch the reviewer

You do **not** walk the AC inline — **dispatch the `backlogd:reviewer` subagent** in
**`verdict`** mode to walk both the **Acceptance Criteria** and the
[**Definition of Done**](../docs/scrum/definition-of-done.md), and to produce the
verdict. Gather the evidence first so the reviewer has a complete envelope (it gets
a fresh context and cannot see anything you haven't put in the envelope):

- the **problem id** (so the reviewer can read the issue + post its progress comment there),
- the problem's **title** and **`## Acceptance Criteria`** list — **AC source depends
  on the problem's form**:
  - **Single-Issue / sub-issue form** — read AC from the issue **description**
    (unchanged from before).
  - **Project-form** — the canonical spec + AC lives in the Project's **`Spec`
    Document**, *not* the container description. Resolve it via
    `list_documents({ projectId }) → match title === "Spec"` → `get_document(<id>)`
    and use that body's `## Acceptance Criteria` block. The container description is
    a summary + link and is **not** the AC source. See
    [`skills/linear/references/documents-and-updates.md`](../skills/linear/references/documents-and-updates.md)
    for the lookup (note the `project` / `projectId` parameter asymmetry).

  Because the reviewer's restricted tool grant has **no `get_document`** by default,
  the orchestrator supplies the AC text **verbatim in the envelope** (the
  `{description, including its Acceptance Criteria}` line in the dispatch template
  below) — fresh-context discipline: anything not in the envelope is invisible to the
  reviewer. Paste the Spec Document body in place of the description for Project-form,
  or paste the description as-is for single-Issue / sub-issue form.
- every per-unit **`**[backlogd developer]**`** progress comment on the problem (and
  every **`**[backlogd tester]**`** comment that landed alongside it) — single-issue:
  one of each; decomposed / Project: one set per sub-issue,
- the **solution brief** — **single-Issue: the `**[backlogd]** Solution brief` comment
  on the problem**; **Project-form: the `Solution brief` Document attached to the
  Project** (resolve via `list_documents({ projectId }) → match title === "Solution
  brief"` → `get_document(<id>)`, and paste its body in the envelope below — the
  reviewer cannot read Documents on its own),
- the problem's **open PR url** (from the issue's linked attachments / branch name) and
  the **CI signal** rollup (`gh pr checks {pr-url}` → green / red / pending),
- the **worktree path** for the problem's branch (if it still exists on this host) — so
  the reviewer can read the diff locally; otherwise it relies on `gh pr diff`.

**Ops-only run?** If the problem carries the **`kind:ops`** label (or every unit does —
see `skills/solve/ops.md`), there is no PR to inspect. The artifacts are the
`**[backlogd developer]**` **action logs** on each unit and the GitHub surfaces those
`gh` calls changed. Pass the action logs to the reviewer in place of the PR diff and tell
it the PR url is `(none — ops-only)` and the CI signal is `(none — ops-only)`. The
reviewer's machine-verifiable checks then become `gh repo view --json …`, `gh release
list`, `gh label list`, etc.

Then call the **`backlogd:reviewer` subagent** with the Agent tool, handing it the
problem as an **inline** context envelope. The envelope is the reviewer's entire
world — anything not in it is invisible to it. Mirror the developer envelope's
no-implicit-context discipline. The reviewer reads the contract (its agent prompt loads
**`skills/ac/SKILL.md`** for the typed-AC grammar so it can branch per kind on each
`## Acceptance Criteria` bullet), walks every AC + every DoD line, and returns both its
rollup (`accepted` / `sent back` / `needs PO` / **`block`**) **and** a **drafted verdict
body** (markdown) you will post verbatim as the `**[backlogd review]**` comment in step 4.
The fourth rollup, **`block`**, fires when a consequential decision in the change has **no
governing Accepted standard** — the reviewer names the gap and classifies it `standard:`
or `fact:` (it does **not** invent the standard); you route it in step 5:

> Review this problem in `verdict` mode. Read its `## Acceptance Criteria` and walk the
> Definition of Done (`docs/scrum/definition-of-done.md`); load `skills/ac/SKILL.md` for
> the typed-AC grammar and branch per kind on each bullet (`[test]` runs the backticked
> command, `[manual]` batches into "Manual checks for the PO", `[review]` is Claude
> judgement; untagged → `[review]`); run every machine-verifiable check yourself (do not
> trust the developer's report — the whole point of an independent review is to verify);
> inspect the PR diff and CI rollup; and return a per-AC + per-DoD verdict. Post your
> progress and verdict draft to your issue's `**[backlogd reviewer]**` comment. Touch
> only this one issue.
>
> Problem ({identifier}, issue id {id}): {title}
>
> {description, including its `## Acceptance Criteria`}
>
> Per-unit developer + tester progress comments (gathered from this problem and any sub-issues):
> {paste each `**[backlogd developer]**` and `**[backlogd tester]**` progress comment
> verbatim, labelled by unit identifier}
>
> Solution brief on the problem:
> {paste the orchestrator's solution-brief comment verbatim}
>
> Open PR: {pr url, or "(none — ops-only)"}
> CI signal: {green | red | pending — from `gh pr checks`, or "(none — ops-only)"}
> Worktree path: {$WT if still present, else "(removed — read via gh pr diff)"}

Capture the reviewer's final structured summary verbatim — specifically the rollup
(`accepted` / `sent back` / `needs PO` / `block`), its `AC:` + `DoD:` glyph counts, the
`Standards:` line (and, on a `block`, the named missing standard + its `standard:`/`fact:`
classification), and the `drafted-verdict-body` markdown block. Verify the reviewer's `**[backlogd reviewer]**`
comment landed on the issue (`list_comments`); do **not** re-post it yourself. If the
comment is missing, this is most likely the NB-340 tool-grant hazard (step 0 above) —
surface it as a tool-grant failure, not a reviewer failure.

## 4. Post the rollup verdict — orchestrator-owned

Post **one** rollup comment on the problem (edited in place on a re-run; visible
`**[backlogd review]**` badge — Linear renders HTML comments as literal text). This is
**your** PO-facing rollup; it is **not** the reviewer's `**[backlogd reviewer]**`
comment (which stays on the issue as the audit trail). The reviewer agent **drafts**
the body in step 3; you **post** it — do not delegate posting. Use the reviewer's
`drafted-verdict-body` verbatim; the template it follows is:

```
**[backlogd review]** Verdict: accepted | sent back | needs you | block

Acceptance criteria
  ✅ [{kind}] {criterion} — {how it is met, with cited evidence (command + exit code for [test])}
  ❌ [{kind}] {criterion} — {what is missing, with stderr snippet for a failed [test]}
  ❔ [{kind}] {criterion} — {the judgement call for you, or "no runnable check found" for a tagless [test]}
  📝 [manual] {criterion} — awaiting PO confirmation (see batch below)

Manual checks for the PO   ← only if there are [manual] items
  - {body of each [manual] bullet, verbatim}

Definition of Done
  ✅ {DoD line} — {how it is met}
  ❌ {DoD line} — {what is missing}
  ❔ {DoD line} — {the judgement call for you}

Applicable standards (filtered from docs/standards/index.json by scope)
  ✅ {ADR-NNN} {assertion} — {how the diff honours it}
  ❌ {ADR-NNN} {assertion} — {how the diff violates it}
  🚫 {decision X} — no Accepted standard governs X (see Missing standard / fact below)
  (or: "none applicable to this diff")

Missing standard / fact   ← only on a block (one line per gap)
  🚫 standard: {decision X} — durable cross-issue gap → graduate to an ADR, escalate to the PO
  🚫 fact: {lookup Y} — one-time lookup → answer once, no ADR, no PO

Evidence the reviewer ran
  - `{command}` → {what it showed}
  - {…}

CI signal: {green | red | pending}

{Rework notes (if sent back), the question (if needs you), the gap to route (if block), or empty (if accepted)}
```

The parsed AC `[{kind}]` tag (one of `[test]` / `[manual]` / `[review]`) appears in
square brackets at the start of each AC line so the PO can see, at a glance, *how*
each item was checked. Untagged AC items appear as `[review]` (the default). The
**Applicable standards** section lists the index-filtered ADRs the reviewer judged the
diff against (or states none applied); the **Missing standard / fact** section appears
**only on a `block`** — one `🚫` line per gap, tagged `standard:` or `fact:` so you can
route it in step 5.

You may **not** override the reviewer's per-AC or per-DoD judgement without surfacing
the override explicitly (e.g. "PO override: accepted despite ❌ — see comment below").
That keeps the audit trail honest: the reviewer's draft is the independent verdict;
your rollup is the action. A red DoD line is treated identically to a red AC line —
the floor is non-negotiable; the scrum-master will not merge an increment that fails
the floor.

## 5. Decide and transition — orchestrator-owned

Act on the reviewer's rollup. This step is the **single source of the merge decision** —
both this manual `/backlogd:review` invocation and `/backlogd:solve`'s ship-on-green
auto-chain (see `skills/solve/ship.md`) act on it, so the merge condition and the
base-race guard below live here once and are reused, never re-derived.

**The happy-path merge condition (exact):** auto-merge **only** when **every AC `✅` AND
every DoD line `✅` AND CI green AND zero `[manual]` AND zero `❔`** (and **no `🚫`
block**). Any `❌`, any `❔`, any unconfirmed `📝`/`[manual]`, any `🚫` block, or red CI
does **not** merge — it routes to *sent back*, *needs PO*, or *block* below. A red DoD
line weighs the same as a red AC line; the floor is non-negotiable, and a `block` parks
the problem blocked-by a new sub-issue until the gap is governed.

- **`accepted`** (every AC `✅` AND every DoD `✅` AND CI green AND zero `[manual]`/`❔`) →
  **merge the PR and close the loop**. First run the **base-race guard** — immediately
  before merging, re-confirm the live PR is still safe to merge (it may have gone stale or
  conflicted while the review ran — this is the NB-382 / concurrent-review race):

      gh pr checks {pr}                                   # CI still green on the live head?
      gh pr view {pr} --json mergeable,mergeStateStatus   # mergeable into the integration branch?

  Proceed to merge **only** if CI is still green **and** `mergeable` is `MERGEABLE` (and
  `mergeStateStatus` is not `BEHIND` / `DIRTY` / `BLOCKED`). If the head went red or the PR
  is no longer cleanly mergeable, **bail to a surfaced blocker** (surface to the PO, leave
  the problem In Review, PR open) — **do not auto-rebase and do not merge on a stale or
  conflicted state** (PO decision). Otherwise find the problem's open PR (via its linked PR
  / branch name) and **squash-merge** it into the integration branch (`gh pr merge {pr}
  --squash --delete-branch`), then move the problem to the `completed` state (Done) and
  remove the problem's worktree if one remains (`git worktree remove`). **Never merge red.**
  *(Ops-only run — `kind:ops`: there is no PR to merge. Skip the merge + base-race guard +
  worktree cleanup and just move the problem to Done.)*
- **`sent back`** (any AC `❌` OR any DoD `❌` OR CI red) → move the problem back to
  the *In Progress* state, with the reviewer's `❌` notes (AC and DoD alike) carried
  into your rollup comment as **actionable rework notes**. Leave the PR open — a fresh
  `/backlogd:solve` adds commits to the same branch. Do **not** re-dispatch a developer
  yourself.
  *(Ops-only run — `kind:ops`: there is no PR. A fresh `/backlogd:solve` re-dispatches
  ops units with the rework notes; the ops developer logs the new actions on the unit.)*

  Also record the rework event on the graph (best-effort — must never block the
  verdict). Use a reviewer session id (e.g. `review-{identifier}-{YYYYMMDDHHMMSS}`)
  and pass the rework notes so only their hash is stored (no note text leaks into
  `.backlogd/`):

      python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/graph.py" rework \
          --session "review-{identifier}-$(date -u +%Y%m%dT%H%M%S)" \
          --problem {identifier} \
          --notes "{the unmet-criteria notes you just wrote}"
- **`needs PO`** (any AC `❔` without `❌`, **or** any `[manual]` items left as
  `📝 awaiting PO confirmation`) → **leave it In Review** (PR open) and surface the
  question(s) to the product owner. For `❔` items, don't guess at a call that's theirs
  to make. For the `[manual]` batch, lift the reviewer's drafted "Manual checks for the
  PO" section verbatim into the question you ask — each `📝` bullet needs a yes/no from
  the PO before the verdict can close. Treat unanswered manual checks as a blocker, not
  a silent pass: `accepted` requires every `📝` confirmed `✅`; an answered-no drops the
  verdict to `sent back`; unanswered holds it at `needs you`.
- **`block`** (a `🚫` line — a consequential decision with **no governing Accepted
  standard**) → **the problem does NOT merge.** It **parks blocked-by a new sub-issue**
  until the gap is governed. Route it by the reviewer's classification — the
  **non-delegable standards boundary**: you may clear a `fact:` lookup yourself **only**
  when an existing ADR/precedent already answers it; you must **never author a missing
  `standard:` yourself** (that silently makes the scrum-master the de-facto architect).
  See [`../skills/scrum/references/accountabilities.md`](../skills/scrum/references/accountabilities.md)
  → *The non-delegable standards boundary*.
  - **`🚫 standard:` (durable, cross-issue gap) → the Linear-native missing-standard
    flow.** Create a **`Define standard for {X}` sub-issue** of the problem
    (`save_issue` with `parentId` = the problem; `title` = `Define standard for {X}`,
    body = the reviewer's named gap), then mark the **parent blocked-by it**
    (`save_issue(id: problem, blockedBy: [sub-issue])`) — Linear sub-issue + blocked-by
    primitives, **not** a buried comment. Leave the problem **In Review**, PR open;
    re-evaluate the `blocked` label (`skills/linear/blocked-label.md`). **Surface to the
    PO** the question *"what standard would you like for {X}?"* — a genuine judgement
    call; do **not** invent the answer. On the PO's answer, **refine + solve the
    sub-issue** (write the ADR from the ADR template under `docs/standards/adrs/`, which
    regenerates `docs/standards/index.json`); once it is `completed` the parent
    **unblocks** and the original story continues — re-run `/backlogd:review`, and the
    once-`block`ed decision now resolves against the freshly-Accepted ADR.
  - **`🚫 fact:` (one-time lookup) → answer once and continue.** No ADR, no PO, no
    sub-issue. Clear it **only** by citing the existing ADR/precedent that already
    answers it; record the answer in your rollup comment and re-run the verdict. If no
    existing standard settles it, it is not a `fact:` — treat it as a `standard:` gap
    above.

Confirm the transition + merge (or the deliberate non-merge / the blocked-by park) succeeded.

## 6. Report

```
{identifier} — {title}
  reviewer    -> {accepted | sent back | needs PO | block}, evidence cited
  acceptance  -> {n met}/{n total} criteria ({t} [test], {m} [manual], {r} [review]), {k} needs-PO
  standards   -> {m} applicable of {n} indexed, {b} missing (🚫)
  CI          -> {green | red | pending}
  verdict     -> accepted (PR merged → Done) | sent back (PR open → In Progress) | needs you (← {question}) | block (PR open → blocked-by {Define standard for X} sub-issue, asked the PO)
```

The kind breakdown on the `acceptance` line lets the PO see, at a glance, how *teeth*
the AC had — a verdict backed by `[test]` checks is a stronger signal than one backed
by `[review]` alone.
