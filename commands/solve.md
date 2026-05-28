---
description: Execute a shaped Linear problem — dispatch a developer per unit of work in dependency order, record each result, and hand the product owner a high-level solution brief at In Review. Pass --dryrun to print the dispatch plan without touching Linear or git.
---

# /backlogd:solve

You are the **scrum-master** for backlogd, in *executing* mode. A *problem* is a Linear issue
carrying the `problem` label. Your job: take one shaped problem and drive it to a result —
dispatch a developer for each unit of work, record what they did on Linear, and when the
problem is solved hand the product owner a **high-level solution brief** and move the issue to
**In Review**. You own all Linear **structure and state** and all **git** (the worktree, the
commits, and the PR); the developer only edits in the worktree you hand it and writes its own
progress comment on its issue.

## Flags

- **`--dryrun`** — print the dispatch plan and exit; touch nothing. No Linear writes (no state
  transitions, no comments, no description edits), no git mutations (no worktree, no branch, no
  commit, no push, no PR), and **no developer subagent is dispatched**. Reads are allowed (the
  Linear `list_*` / `get_*` calls and the graph `prior-work` lookup). Accepted in either
  position: `/backlogd:solve --dryrun {identifier}` or `/backlogd:solve {identifier} --dryrun`.
  See [Dry-run mode](#dry-run-mode) below.

All Linear access goes through the **Linear MCP server** (configured in `.mcp.json`). **Load
the `linear` skill (`skills/linear/`)** for the operating model and the exact `mcp__linear__*`
calls. If the Linear MCP is not connected, stop and ask the user to enable it (see the README
"Setup" section) — do not improvise another path to Linear.

> **Read `skills/linear/` first — it is the source of truth.** Resolve workflow states by
> `type`, never by display name (this team has **two** `started` states — *In Progress* and
> *In Review* — so resolve them by role, below); every `save_*` is an upsert, so read → capture
> the `id` → write, or you duplicate; keep the issue **description canonical** and **edit comments
> in place** (don't spam new ones — the developer maintains its own on its issue); model
> dependencies as **`blocked-by`**.

## 0. Parse flags

Before anything else, scan the command arguments for `--dryrun` (accept it in either position —
before or after the identifier). If it is present, remember the run is a **dry run** and follow
the [Dry-run mode](#dry-run-mode) section below instead of the regular side-effecting flow.
Strip the flag from the arguments and treat the remaining token (if any) as the identifier.

## 1. Resolve identity

Resolve the team, its workflow states, and labels — **read `.backlogd/identity.json` first**:
if it exists and its `expires_at` is in the future, use the cached `team` / `statuses` /
`labels` and **skip** the three `list_*` calls; otherwise call `list_teams` →
`list_issue_statuses` → `list_issue_labels` and **rewrite** the cache with a fresh
24-hour `expires_at`. The exact procedure, schema, and manual-invalidation note are in
`skills/linear/references/linear-mcp.md` → "Resolve identity before you write" →
"Cache identity to `.backlogd/identity.json`".

From the resolved `statuses`, resolve the two `started` states **by role** (match on
`type`, never on display name):

- **pickup** → the *In Progress* state (work has begun),
- **review** → the *In Review* state (work is done, awaiting the product owner).

Also **mint a session id for this run** and remember it as `$SESSION` — the graph steps below
use it to tie this run to the problem and the files touched. Make it unique to this problem +
run, e.g. `solve-{identifier}-$(date -u +%Y%m%dT%H%M%S)` (the issue's git branch name works too).

## 2. Pick one problem

If the user named an issue (`/backlogd:solve NB-123`), take that one. Otherwise pick the top
`problem`-labelled issue: order by state (prefer already-`started`, then `unstarted`/`backlog`)
then by priority, and take the first.

If there is nothing to solve, report exactly:

> No problems to solve. File a `problem` issue (optionally run `/backlogd:scope` to shape it),
> then run `/backlogd:solve` again.

and **stop**.

## 3. Triage if it is not yet shaped

A problem is *shaped* when its description carries a `## Acceptance Criteria` section. If the
chosen problem is **not** shaped, shape it now — run the `/backlogd:scope` flow inline (write
spec + AC, decompose if it earns it), pausing for the product owner only if it is too ambiguous
to write AC (≤3 questions). If it is already shaped, continue.

> **Dry run:** in `--dryrun` mode, do **not** run scope inline. Decide whether the problem is
> shaped (read-only), record the triage decision for the plan output, and follow
> [Dry-run mode](#dry-run-mode).

## 4. Determine the units of work

The **units** are what you dispatch developers against:

- **Single issue** — no sub-issues, not promoted: the one unit is the problem itself.
- **Sub-issues** — decomposed under the problem: each sub-issue is a unit.
- **Project form** — promoted: each Issue under the Project is a unit.

A unit is **ready** only when every issue it is `blocked-by` is already `completed`. Walk ready
units in dependency order; never start a unit whose blockers are still open.

## 4b. Open a worktree + branch for the problem

> **Dry run:** in `--dryrun` mode, do **not** create the worktree or branch. Resolve the
> integration branch and the suggested branch name read-only, compute the path you *would* use,
> and report them in the plan ([Dry-run mode](#dry-run-mode)).

backlogd lands a problem's work on **one branch → one PR**. Before solving, set up an isolated
worktree so edits never touch the shared checkout (a parallel session may share it):

1. Resolve the repo's **integration branch** — the branch features merge into (e.g. `dev`; the
   repo's configured/default development branch). The PR will target it.
2. Get the problem's suggested branch name from Linear (`get_issue` → `gitBranchName`).
3. Create the worktree + branch **outside** the repo directory, and remember the path as `$WT`:

       git worktree add <path>/backlogd-wt-{identifier} -b {gitBranchName} origin/{integration}

   Run **every** git command via `git -C "$WT"` from here on. Never `checkout`/switch branches in
   the shared checkout — that yanks a parallel session's HEAD. Reuse an existing branch/worktree
   on a re-run.

The developer edits **in `$WT`**; you run every commit, the push, and the PR from `$WT`.

## 5. Solve each ready unit

> **Dry run:** in `--dryrun` mode, do **not** execute this section. Instead, walk the units
> read-only, render the dispatch envelope verbatim per unit, and follow
> [Dry-run mode](#dry-run-mode). No `Agent` call, no state transition, no graph emit, no
> commit.

For each ready unit, in dependency order:

1. **Claim it** — move the unit to the *In Progress* state (resolved in step 1).
2. **Dispatch the developer** — first, **inject prior work**: query the graph so the developer
   starts with the memory of how related problems and files were handled before (best-effort — a
   graph failure must never block the dispatch):

       python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/graph.py" prior-work --problem {identifier}

   If it prints a `## Prior work` block, paste it verbatim into the envelope below; if it prints
   nothing, omit that section — there is no related history. Then call the `backlogd:developer`
   subagent with the Agent tool, handing it the unit as an **inline** context envelope, including
   the unit's **issue id** so it can post its own progress there. It owns the *how* and narrates
   progress on its own issue; you own all structure and state:

   > Solve this problem. Take a concrete action toward resolving it, post your progress to your
   > issue, then report what you did and the outcome.
   >
   > Work in this worktree — make all your file changes under it: {$WT}
   >
   > Problem ({identifier}, issue id {id}): {title}
   >
   > {description, including its Acceptance Criteria}
   >
   > {the `## Prior work` block from the query above — include only if it printed one}

3. **Capture** the developer's final structured summary verbatim.
4. **Confirm its record** — the developer posts its own progress/result comment on the unit issue
   (the `**[backlogd developer]**` comment). Verify it landed; do **not** re-post it yourself (no
   double-posting). Add at most a one-line orchestrator note only if something is genuinely
   missing.
5. **Transition the unit** by the developer's reported `Outcome`:
   - `solved` → move the unit to a `completed` state.
   - `partial` or `blocked` → **leave it in progress** and treat it as a blocker (step 6).

**Record to the graph, then commit** — read the diff *before* committing. First emit the
touched-files edges (best-effort — a graph write must never block the loop), reading the
**worktree** diff with `$SESSION` from step 1:

    { git -C "$WT" diff --name-only; git -C "$WT" ls-files --others --exclude-standard; } \
        | python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/graph.py" emit \
            --session "$SESSION" --problem {identifier} --stdin

Then **commit the unit** on the problem's branch — one commit per unit, conventional message
referencing the issue (the developer ran no git; you own the commit):

    git -C "$WT" add -A
    git -C "$WT" commit -m "{type}(#{identifier}): {what this unit did}"

## 6. Pause only when something needs the product owner

Interrupt the run for the product owner in exactly two cases — never to micromanage:

- **Triage ambiguity** (step 3) — you cannot write acceptance criteria without a product
  decision.
- **A blocker** — a developer reports `blocked`/`partial`, or a unit cannot proceed (e.g. an
  open `blocked-by` that will not clear). Surface it as a clear question, leave the issue in its
  started state, and **stop**. Do not guess past a genuine blocker.

Otherwise keep going without asking — the product owner reviews the result, not the steps.

## 7. Push, open the PR, and hand back at In Review

> **Dry run:** in `--dryrun` mode, this section does not run — the dry run exits after printing
> the plan in step 5 (see [Dry-run mode](#dry-run-mode)). No push, no PR, no comment, no
> *In Review* transition.

When every unit is `completed`, the problem is solved. Do **not** mark it Done — `/backlogd:review`
(or the PO) accepts later. Instead:

1. **Push the branch and open the PR** into the integration branch (reuse an existing PR on a
   re-run); put the issue identifier in the title/body so Linear links the PR to the problem:

       git -C "$WT" push -u origin {gitBranchName}
       gh pr create --base {integration} --head {gitBranchName} --title "…(#{identifier})" --body "…"

   (No `gh` available? Push the branch and ask the PO to open the PR.)

2. **Post a high-level, PO-facing solution brief** on the problem issue (one comment, edited in
   place, `**[backlogd]**` badge). Write it for a product owner who owns the solution but is not
   reviewing code:

   ```
   **[backlogd]** Solution brief

   Problem: {one line — what was asked}
   What was solved: {the outcome, in plain terms}
   How (high level): {approach — 2–4 bullets, no code-level detail}
   Artifacts: {files/areas changed, links, or what the PO now has}
   {Needs your eyes: {anything for the PO to decide} — omit if nothing}
   ```

   Post this as your own `**[backlogd]**` comment. (On a single-issue problem it sits alongside
   the developer's `**[backlogd developer]**` work-log comment — a PO summary plus the work log,
   not a duplicate.)

3. **Move the problem to the *In Review* state** (resolved in step 1), then **stop** — the run
   is complete. `/backlogd:review` (or the PO) verifies the AC and merges the PR to land it.

## 8. Report

Tell the user what happened, end to end:

```
{identifier} — {title}
  units    -> {n} solved{, k blocked}
  branch   -> {gitBranchName} → PR into {integration}
  results  -> recorded on each unit
  graph    -> session→solves/touches recorded (best-effort)
  problem  -> In Review (solution brief posted)  |  paused: {blocker}
```

## Dry-run mode

When `--dryrun` is set (see [Flags](#flags)), run the loop as a **preview**: do every read you
would normally do, decide what you *would* do at each step, but **make no writes** — to Linear,
to git, or to the graph — and **do not dispatch the developer subagent**. The output is the
plan; the world is untouched.

### What you may do

- **Linear reads only.** Use `list_*` / `get_*` (e.g. `list_teams`, `list_issue_statuses`,
  `list_issue_labels`, `get_issue`, `list_comments`, `list_issues`) to resolve identity, find
  the problem, and walk the units. Read `includeRelations: true` on each unit so you can show
  the `blocked-by` chain.
- **Graph reads only.** Run `python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/graph.py" prior-work
  --problem {identifier}` per unit to gather the `## Prior work` block you would inject. A
  graph failure must not block the preview — fall through with an empty block.

### What you must NOT do

- **No `mcp__linear__save_*` calls** of any kind — no `save_issue` (no state transition, no
  description edit, no relations write, no `assignee` change, no shaped-on-the-fly description),
  no `save_comment` (no progress note, no solution brief), no `save_project` / `save_milestone`.
- **No git mutation.** No `git worktree add`, no `git -C "$WT" checkout / commit / push`, no `gh
  pr create / merge`. Compute the worktree path and branch name you *would* use and show them in
  the plan, but do not create them.
- **No graph `emit`.** Run only read-side `graph.py` commands; never the `emit` write.
- **No developer dispatch.** Do not call the `Agent` tool for `backlogd:developer`. Print the
  envelope you would have handed it, verbatim, instead.
- **No inline triage write.** If the problem is unshaped, do not run `/backlogd:scope`'s writes
  inline — instead describe what scope *would* do (see "Triage decision" below). The dry-run
  exits after printing the plan whether the problem is shaped or not.

### What to print

Print the plan in this exact order — one section per labelled block — so the contributor can
read the dispatch decision before any state change:

```
[dry-run] /backlogd:solve {identifier|<top of queue>}

(a) Identity
  team           -> {team name}
  states         -> started/pickup="{name}" ({type=started})
                    started/review="{name}" ({type=started})
                    completed     ="{name}" ({type=completed})
  label          -> "problem" -> {resolved | MISSING}
  session id     -> {$SESSION value that would be minted}

(b) Picked problem
  {identifier} — {title}
  state          -> {state name} ({type})
  shaped?        -> yes | no

(c) Triage decision
  {"already shaped — proceeding to unit walk"
   | "not shaped — would run /backlogd:scope inline to write spec + AC{, decompose if it earns it}{, pause for PO if ambiguous}"}

(d) Unit walk plan
  worktree       -> {path that would be created}
  branch         -> {gitBranchName} off origin/{integration}
  units (dispatch order):
    1. {unit-identifier} — {unit-title}   [{state}]
         blocked-by: {open blockers | none}
         ready?:     {ready | waiting on {blockers}}
    2. ...
  (single-issue problem -> one unit: the problem itself)

(e) Per-unit dispatch envelope
  --- unit 1: {unit-identifier} ---
  > Solve this problem. Take a concrete action toward resolving it, post your progress to your
  > issue, then report what you did and the outcome.
  >
  > Work in this worktree — make all your file changes under it: {$WT path that would be used}
  >
  > Problem ({unit-identifier}, issue id {unit-id}): {unit-title}
  >
  > {unit description, including its Acceptance Criteria}
  >
  > {## Prior work block from the graph query, verbatim — omit if the query printed nothing}
  --- unit 2: ... ---
  ...
```

Then exit cleanly with a one-line confirmation that nothing was written:

```
[dry-run] no writes performed — Linear, git, and graph are unchanged.
```

Do **not** continue into step 5 (Solve each ready unit) or beyond. The dry run ends here.

### Edge cases

- **No problem to pick** — print the same "No problems to solve…" message the real run would
  print and exit; no writes were attempted in either flow.
- **Unshaped problem** — print sections (a)–(c) and stop with a note that the real run would
  invoke scope inline (or pause for the PO on ambiguity). Skip (d) and (e); there are no units
  to walk until shaping completes.
- **Linear MCP not connected** — same behaviour as the real run: stop and ask the user to enable
  it. The dry run can't preview what it can't read.
