---
name: solve-dispatch
<<<<<<< HEAD
description: Per-unit dispatch loop for /backlogd:solve — claim the unit, resolve the specialist from its agent:* label (or fall back to generic developer), inject prior work from the graph, hand the developer an inline envelope, capture the result, transition state by outcome, and emit graph edges + commit per unit.
=======
description: Per-unit dispatch loop for /backlogd:solve — claim the unit, inject prior work from the graph, record dispatch_started, hand the developer an inline envelope, capture the result, record dispatch_completed with outcome + latency, transition state by outcome, and commit per unit.
>>>>>>> origin/dev
---

# solve — per-unit dispatch

> **Dry run:** in `--dryrun` mode, do **not** execute this section. Instead, walk the
> units read-only, render the dispatch envelope verbatim per unit, and follow
> `skills/solve/dryrun.md`. No `Agent` call, no state transition, no graph write, no commit.
>
> **Resume:** for each unit, check what `skills/solve/resume.md` classified it as. **Skip
> any unit reconcile marked `completed`** — no claim, no envelope, no graph write, no
> commit; the prior run already handled it (its `dispatch_completed` edge is on the graph
> and Linear already says `Done`). Process `in-progress-mine` and `untouched` units below
> exactly as you would in a fresh run. If reconcile surfaced an `inconsistent` unit the
> orchestrator already paused — this skill is not reached.

> **Ops-only run?** If `skills/solve/walk.md` routed this run to the ops-only path (every
> ready unit carries the **`kind:ops`** label), **do not run this section** — follow
> **`skills/solve/ops.md`** instead. There is no worktree, no commit, and no PR; the
> developer takes `gh` / repo-ops actions and posts an action log on the unit. The two
> paths are mutually exclusive per run.

For each ready unit, in dependency order:

1. **Claim it** — move the unit to the *In Progress* state (from `skills/solve/identity.md`).
<<<<<<< HEAD
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
=======
2. **Inject prior work + record dispatch start** — both are best-effort; a graph failure
   must never block the dispatch. First query for prior work:
>>>>>>> origin/dev

       python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/graph.py" prior-work --problem {identifier}

   If it prints a `## Prior work` block, paste it verbatim into the envelope below;
<<<<<<< HEAD
   otherwise omit that section. Then call the **resolved subagent** (`$AGENT` from
   step 2 — `developer` or `developer-<suffix>`) with the Agent tool, handing it the unit
=======
   otherwise omit that section. Then record the dispatch start on the graph so the
   `dispatch_completed` edge later can derive its latency from it:

       python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/graph.py" dispatch-start \
           --session "$SESSION" --problem {identifier}

   If you can resolve the unit's Linear labels at this point, also record them so the
   metrics report can break blockers down by `area:*` (skip if you don't have them — the
   area aggregate will simply note "no label data"):

       python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/graph.py" labeled \
           --session "$SESSION" --problem {identifier} --labels {label1} {label2} ...

   Then call the `backlogd:developer` subagent with the Agent tool, handing it the unit
>>>>>>> origin/dev
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
<<<<<<< HEAD
=======
5. **Record dispatch completion on the graph** — write the per-unit outcome with the
   latency the CLI derives automatically from the `dispatch_started` edge above
   (best-effort — never block the loop):

       python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/graph.py" dispatch-end \
           --session "$SESSION" --problem {identifier} \
           --outcome {solved|partial|blocked}

>>>>>>> origin/dev
6. **Transition the unit** by the developer's reported `Outcome`:
   - `solved` → move the unit to a `completed` state.
   - `partial` or `blocked` → **leave it in progress** and surface it to the product owner
     as a clear question (a genuine blocker — do not guess past it); leave the issue in its
     started state and **stop** the run.

7. **Commit the unit** on the problem's branch — one commit per unit, conventional message
   referencing the issue (the developer ran no git; you own the commit):

       git -C "$WT" add -A
       git -C "$WT" commit -m "{type}(#{identifier}): {what this unit did}"

## Note on file-edge writes (low-signal)

The graph used to also record `touches` edges (one per changed file) at this step. That
signal is **derivable from `git log`** and is now a *low-priority aside* — the new flow
above does **not** emit it. `prior_work` still surfaces historical `touches` data when
present, so the loop benefits from old graphs without recreating them. If you have a
specific need to record file edges, `scripts/graph.py emit ...` still works, but the
default loop intentionally skips it.
