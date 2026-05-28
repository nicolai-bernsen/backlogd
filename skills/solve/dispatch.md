---
name: solve-dispatch
description: Per-unit dispatch loop for /backlogd:solve — claim the unit, inject prior work from the graph, hand the developer an inline envelope, capture the result, transition state by outcome, and emit graph edges + commit per unit.
---

# solve — per-unit dispatch

> **Dry run:** in `--dryrun` mode, do **not** execute this section. Instead, walk the
> units read-only, render the dispatch envelope verbatim per unit, and follow
> `skills/solve/dryrun.md`. No `Agent` call, no state transition, no graph emit, no commit.

> **Ops-only run?** If `skills/solve/walk.md` routed this run to the ops-only path (every
> ready unit carries the **`kind:ops`** label), **do not run this section** — follow
> **`skills/solve/ops.md`** instead. There is no worktree, no commit, and no PR; the
> developer takes `gh` / repo-ops actions and posts an action log on the unit. The two
> paths are mutually exclusive per run.

For each ready unit, in dependency order:

1. **Claim it** — move the unit to the *In Progress* state (from `skills/solve/identity.md`).
2. **Dispatch the developer** — first, **inject prior work** (best-effort — a graph
   failure must never block the dispatch):

       python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/graph.py" prior-work --problem {identifier}

   If it prints a `## Prior work` block, paste it verbatim into the envelope below;
   otherwise omit that section. Then call the `backlogd:developer` subagent with the Agent
   tool, handing it the unit as an **inline** context envelope, including the unit's
   **issue id** so it can post its own progress there. It owns the *how*; you own all
   structure and state:

   > Solve this problem. Take a concrete action toward resolving it, post your progress to
   > your issue, then report what you did and the outcome.
   >
   > Work in this worktree — make all your file changes under it: {$WT}
   >
   > Problem ({identifier}, issue id {id}): {title}
   >
   > {description, including its Acceptance Criteria}
   >
   > {the `## Prior work` block from the query above — include only if it printed one}

3. **Capture** the developer's final structured summary verbatim.
4. **Confirm its record** — the developer posts its own progress/result comment on the
   unit issue (the `**[backlogd developer]**` comment). Verify it landed; do **not**
   re-post it yourself (no double-posting). Add at most a one-line orchestrator note only
   if something is genuinely missing.
5. **Transition the unit** by the developer's reported `Outcome`:
   - `solved` → move the unit to a `completed` state.
   - `partial` or `blocked` → **leave it in progress** and surface it to the product owner
     as a clear question (a genuine blocker — do not guess past it); leave the issue in its
     started state and **stop** the run.

**Record to the graph, then commit** — read the diff *before* committing. First emit the
touched-files edges (best-effort — a graph write must never block the loop), reading the
**worktree** diff with `$SESSION` from `skills/solve/identity.md`:

    { git -C "$WT" diff --name-only; git -C "$WT" ls-files --others --exclude-standard; } \
        | python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/graph.py" emit \
            --session "$SESSION" --problem {identifier} --stdin

Then **commit the unit** on the problem's branch — one commit per unit, conventional
message referencing the issue (the developer ran no git; you own the commit):

    git -C "$WT" add -A
    git -C "$WT" commit -m "{type}(#{identifier}): {what this unit did}"
