---
name: solve-dispatch
description: Per-unit dispatch loop for /backlogd:solve — claim the unit, resolve the specialist from its agent:* label (or fall back to generic developer), inject prior work from the graph, hand the developer an inline envelope, capture the result, transition state by outcome, and emit graph edges + commit per unit.
---

# solve — per-unit dispatch

> **Dry run:** in `--dryrun` mode, do **not** execute this section. Instead, walk the
> units read-only, render the dispatch envelope verbatim per unit, and follow
> `skills/solve/dryrun.md`. No `Agent` call, no state transition, no graph emit, no commit.

For each ready unit, in dependency order:

1. **Claim it** — move the unit to the *In Progress* state (from `skills/solve/identity.md`).
2. **Resolve the specialist for this unit.** Read the unit issue's `labels` and look for
   exactly one `agent:<suffix>` label (the `agent:*` family is backlogd-owned — see
   `skills/linear/references/linear-mcp.md`). Map that label to a subagent name with the
   rule **`agent:<suffix>` → `developer-<suffix>`**, then verify the specialist is
   discoverable — its agent file lives at either
   `${CLAUDE_PLUGIN_ROOT:-.}/agents/developer-<suffix>.md` or
   `.claude/agents/developer-<suffix>.md` (per-repo wins on clash). Decide the
   `subagent_type` to dispatch:
   - **No `agent:*` label** → dispatch generic `developer` (the fallback —
     `agents/developer.md`). This preserves today's behaviour.
   - **One `agent:*` label and the specialist is discoverable** → dispatch
     `developer-<suffix>`.
   - **One `agent:*` label but `developer-<suffix>.md` is not discoverable** → **stop the
     run cleanly.** Surface to the PO: the label, the expected file path, and a short
     list of available specialists (names collected from the two discovery globs). Do
     not guess past a missing specialist; the PO fixes the label and re-runs.
   - **Multiple `agent:*` labels on the unit** → **stop the run cleanly.** Surface the
     ambiguity to the PO with the labels found and ask them to leave exactly one.

   Remember the resolved `subagent_type` (call it `$AGENT`) for the dispatch in step 3.

3. **Dispatch the developer** — first, **inject prior work** (best-effort — a graph
   failure must never block the dispatch):

       python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/graph.py" prior-work --problem {identifier}

   If it prints a `## Prior work` block, paste it verbatim into the envelope below;
   otherwise omit that section. Then call the **resolved subagent** (`$AGENT` from
   step 2 — `developer` or `developer-<suffix>`) with the Agent tool, handing it the unit
   as an **inline** context envelope, including the unit's **issue id** so it can post
   its own progress there. It owns the *how*; you own all structure and state:

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

4. **Capture** the developer's final structured summary verbatim.
5. **Confirm its record** — the developer posts its own progress/result comment on the
   unit issue (the `**[backlogd developer]**` comment). Verify it landed; do **not**
   re-post it yourself (no double-posting). Add at most a one-line orchestrator note only
   if something is genuinely missing.
6. **Transition the unit** by the developer's reported `Outcome`:
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
