---
name: solve-dispatch
description: Per-unit dispatch envelope for /backlogd:solve — claim the unit, resolve the specialist from its agent:* label (or fall back to generic developer), inject prior work from the graph, record dispatch_started, hand the developer a curated-context inline envelope (the issue's title + full description + AC inlined verbatim under a labeled ## Issue context block so the developer never re-reads Linear), capture the result, record dispatch_completed with outcome + latency, transition state by reading the developer's machine-readable STATUS line (DONE / DONE_WITH_CONCERNS / BLOCKED / NEEDS_CONTEXT — see skills/solve/capture.md), and commit per unit. Callable once per unit either sequentially (single-unit group, default) or concurrently (parallel group — multiple Agent() calls in one response, each with its own per-unit worktree). The envelope is single-unit; the orchestrator in skills/solve/walk.md decides whether to call it once or N-way in parallel.
---

# solve — per-unit dispatch

## The curated-context pattern

backlogd dispatches developers with **curated context**: the orchestrator already read
the unit's issue (to pick it, shape it, and decide it was ready), so it **inlines that
issue's title + full description + `## Acceptance Criteria` verbatim into the dispatch
envelope** under a clearly-labeled `## Issue context` block. The developer reads its spec
**from the envelope**, not from a Linear round-trip — only its *writes* (the
`**[backlogd developer]**` progress comment) still need the Linear MCP.

This is the same shape obra/superpowers' `subagent-driven-development` skill names
explicitly — *"extract all tasks with full text up front; paste task body into subagent
prompt; never make the subagent re-read the plan file"* — and that
EveryInc/compound-engineering uses with its `<context>` envelope tag.

Why backlogd does this:

- **No per-dispatch Linear round-trip.** The orchestrator's existing `get_issue` result
  (from pickup/identity — reuse the NB-318 identity cache where available) is reused; the
  developer does not spend a `get_issue` call re-loading a spec the orchestrator already
  has in hand.
- **Decouples the dispatch from MCP-grant fragility (NB-340).** If the developer's Linear
  grant is skewed at dispatch time, it can still read its full spec from the envelope and
  do the work; only the progress-comment write depends on the grant.
- **Per-unit by construction.** This skill is single-unit (see below): `skills/solve/walk.md`
  calls it once per ready unit, so in a multi-unit / sub-issue walk **each child's own
  body is inlined into its own envelope** — never the parent's, never a shared blob.

The developer contract mirrors this: `agents/developer.md` reads its spec from the
envelope by default and treats `mcp__linear__get_issue` as **optional — a fresh-state
refresh only** (e.g. if it suspects the issue changed mid-flight).

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
>
> **Ops-only run?** If `skills/solve/walk.md` routed this run to the ops-only path (every
> ready unit carries the **`kind:ops`** label), **do not run this section** — follow
> **`skills/solve/ops.md`** instead. There is no worktree, no commit, and no PR; the
> developer takes `gh` / repo-ops actions and posts an action log on the unit. The two
> paths are mutually exclusive per run.

## Single-unit envelope (called once per unit)

This skill is **single-unit**: it describes the work of one dispatch. `skills/solve/walk.md`
calls it once per ready unit. When the walk has built a **parallel group** of ≥2 units,
it issues multiple `Agent()` calls **in one response** (Claude Code's native concurrency
seam) so all dispatches in the group run concurrently — each one consumes this skill
independently. Per-parallel-unit, the worktree handed to the developer is the unit's own
`$WT_unit` (the path the walk created at `backlogd-wt-{identifier}-unit-{unit}`); per
sequential-unit, it is the shared `$WT` (the problem-branch worktree). Substitute the
correct one into the envelope below.

For each ready unit (in a parallel group: each unit in the group; in a sequential walk:
each unit in `blocked-by` order):

<!-- markdownlint-disable MD029 -->
<!-- Step numbers are load-bearing identifiers: the 5b insertion is deliberate so steps
     6/7/8 stay valid where they are referenced in-file and from gate.md and
     commands/solve.md. Do not renumber this list. -->

1. **Claim it.** First ensure the **claim-lock** is held under `$SESSION`
   (**`skills/linear/claim-lock.md`**): `skills/solve/pickup.md` already `check`ed it and
   `acquire`d on first pickup, so here just confirm/`refresh` it — and if a *different* live
   session has taken it since pickup (e.g. a parallel run started in the gap), **stand off**
   per the claim-lock skill (stop, surface held-by) rather than transitioning. This claim
   `check`/`acquire` is **before the first state mutation below** — the cross-session lock
   (NB-414) guards the Linear work item one layer above the worktree/git isolation.

   Then move the unit to the *In Progress* state (from `skills/solve/identity.md`), and
   **in the same `save_issue` call set `delegate:"backlogd"`** — one MCP write, no extra
   round-trip. This is the **Tier-1 visible-agent-identity** signal (ADR-001 → carried
   forward by [ADR-006](../../docs/standards/adrs/ADR-006-tier2-locally-hosted-agent-identity.md)
   AC#7): the issue then shows the agent as its `delegate` while the product owner stays
   `assignee` (delegation is additive — it never displaces the human owner), so *"an agent
   picked this up"* is a first-class, filterable signal rather than only a comment badge.
   See `skills/solve/identity.md` → "Set the delegate on pickup (best-effort, Tier 1)" for
   the write shape, the best-effort contract, and the leave-on-completion default.
   On a **Project-form** run, post a project-thread health update immediately after the
   claim with marker `claim` — the body shape, dedupe-by-marker procedure, and health
   derivation rules live in
   **`skills/linear/references/documents-and-updates.md` § "Project health updates"**.
   Health is `on track` at first claim unless an existing blocker already pushes it to `at
   risk` / `off track` per the derivation rules. **Single-issue and sub-issue forms do
   NOT post this update** — Project-form only.

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

3. **Inject prior work + record dispatch start** — both are best-effort; a graph failure
   must never block the dispatch. First query for prior work:

       python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/graph.py" prior-work --problem {identifier}

   If it prints a `## Prior work` block, paste it verbatim into the envelope below;
   otherwise omit that section. Then record the dispatch start on the graph so the
   `dispatch_completed` edge later can derive its latency from it:

       python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/graph.py" dispatch-start \
           --session "$SESSION" --problem {identifier}

   If you can resolve the unit's Linear labels at this point, also record them so the
   metrics report can break blockers down by `area:*` (skip if you don't have them — the
   area aggregate will simply note "no label data"):

       python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/graph.py" labeled \
           --session "$SESSION" --problem {identifier} --labels {label1} {label2} ...

   Then call the **resolved subagent** (`$AGENT` from step 2 — `developer` or
   `developer-<suffix>`) with the Agent tool, handing it the unit as a **curated-context
   inline** envelope. **Inline this unit's own issue context verbatim** — its title, its
   **full** description (which carries the single-sentence `## Goal` and the
   `## Acceptance Criteria`), exactly as they read in Linear — under a clearly-labeled
   `## Issue context` block, and include the unit's **issue id** so the developer can post
   its own progress there. Because the description is inlined verbatim, the unit's `## Goal`
   (the coherent objective the work serves) travels with the AC — so the developer, the
   tester, and the reviewer all read the **same "why"**, not just the AC. Do not trim or
   summarise the `## Goal` out; it is part of the verbatim description. Reuse the `get_issue`
   result you already have from pickup/identity (the NB-318 identity cache) rather than
   re-fetching. The developer reads its spec from this envelope; it owns the *how*, you own
   all structure and state:

   > Solve this problem. Take a concrete action toward resolving it, post your progress to
   > your issue (the `**[backlogd developer]**` comment, edited in place), then report what
   > you did and the outcome.
   >
   > Work in this worktree — make all your file changes under it: {$WT or $WT_unit for this unit}
   >
   > ## Issue context
   >
   > **Problem ({identifier}, issue id {id}): {title}**
   >
   > {the unit's full description verbatim — including its `## Acceptance Criteria` section}
   >
   > {the `## Prior work` block from the query above — include only if it printed one}

   The `## Issue context` block is the developer's spec — inline it **verbatim** (do not
   summarise or trim the description or AC). In a **multi-unit / sub-issue walk** this
   substitution is per-unit by construction: each unit's *own* `{id}` / `{title}` /
   description is inlined into *its* envelope (never the parent's), because this skill is
   called once per ready unit (see `skills/solve/walk.md`).

   For a **parallel group** call, substitute the unit's own `$WT_unit` (the path
   `skills/solve/walk.md` created at `backlogd-wt-{identifier}-unit-{unit}`) into the
   worktree line. Each parallel sub-developer inherits the orchestrator's loaded tool
   grant — `agents/developer.md` carries no `tools:` frontmatter (removed in #345), so
   the runtime propagates parent context per dispatch. No per-dispatch pre-load is
   needed.

   <details>
   <summary><strong>Worked envelope example</strong> (single unit NB-512, sequential — on <code>$WT</code>)</summary>

   The literal envelope text sent to the developer (shown verbatim):

       Solve this problem. Take a concrete action toward resolving it, post your progress to
       your issue (the **[backlogd developer]** comment, edited in place), then report what
       you did and the outcome.

       Work in this worktree — make all your file changes under it: C:/Users/.../backlogd-wt-NB-512

       ## Issue context

       **Problem (NB-512, issue id NB-512): Dedupe the status forecast block**

       Today /backlogd:status appends a fresh 7-day forecast to the Project description on
       every run, so the description grows without bound.

       ## Goal

       The status forecast stays a single, current block the PO can trust at a glance.

       ## Acceptance Criteria

       - [ ] The forecast block is replaced in place (matched by a stable marker), not appended.
       - [ ] Running /backlogd:status twice leaves exactly one forecast block.

       ## Prior work

       - NB-341 (PO daily overview) last touched skills/status/forecast.md.

   For a **parallel** unit, the only difference is the worktree line points at the unit's
   own `$WT_unit` (e.g. `.../backlogd-wt-NB-512-unit-NB-514`) and the `## Issue context`
   carries **that child's** id/title/description — its sibling gets a separate envelope with
   *its* body.
   </details>

4. **Capture** the developer's final structured summary verbatim — including its first-line
   `STATUS:` value **and its `Deferred-checks:` line** (the AC-required checks its grant
   could not run, enumerated for the gate; `none` if it ran everything — see
   `agents/developer.md` → *The `Deferred-checks:` line*). **In a parallel group, do not
   abort sibling dispatches when one returns a non-terminal `STATUS`
   (`BLOCKED`/`NEEDS_CONTEXT`/`DISPUTES_AC`) — let every dispatch in the group finish, then
   process each per step 7 below.** (See `skills/solve/walk.md` § "Dispatch a parallel
   group" for the wait-and-collect contract.)

5. **Confirm its record** — the developer posts its own progress/result comment on the
   unit issue (the `**[backlogd developer]**` comment). Verify it landed; do **not**
   re-post it yourself (no double-posting). Add at most a one-line orchestrator note only
   if something is genuinely missing.

5b. **Run the quality gate** → **`skills/solve/gate.md`**. Load it; it dispatches the
   tester and the reviewer (`pre-commit-gate` mode) against the unit the resolved
   specialist just edited. **Pass the developer's `Deferred-checks:` line (captured in step
   4) into the gate** so the reviewer runs each enumerated check (the gate also always runs
   markdownlint on changed `.md`). If the gate returns **`needs-changes`**, re-enter **step 3**
   above (re-dispatch the resolved specialist with the gate's rework notes prepended to
   the envelope), then re-enter this gate stage. Bounded by a 2-round hard cap inside
   `gate.md` — on the 3rd would-be re-dispatch the gate returns `blocked`, which step 7
   handles on its **`BLOCKED`** branch (leave the unit in progress, surface to the PO, stop
   the run). If the gate returns **`ok`**, continue to step 6; carry any `untestable:`
   items the gate captured forward so `skills/solve/handoff.md` can surface them in the PO
   solution brief.

6. **Record dispatch completion on the graph** — write the per-unit outcome with the
   latency the CLI derives automatically from the `dispatch_started` edge above
   (best-effort — never block the loop). The graph keeps a coarse `{solved|partial|blocked}`
   vocabulary, so **fold the developer's five-value `STATUS` onto it** per
   `skills/solve/capture.md` (`DONE`/`DONE_WITH_CONCERNS` → `solved`; `BLOCKED`/
   `NEEDS_CONTEXT`/`DISPUTES_AC` → `blocked`):

       python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/graph.py" dispatch-end \
           --session "$SESSION" --problem {identifier} \
           --outcome {solved|blocked}

7. **Transition the unit by its `STATUS`** → **`skills/solve/capture.md`**. Load it; it
   owns the deterministic branch. Read the **first line** of the developer's captured
   report (the `STATUS:` line), match it against the five-value enum **mechanically** (no
   prose-heuristic parsing of the body), and follow `capture.md`'s branch table:
   - `DONE` / `DONE_WITH_CONCERNS` → move the unit to a `completed` state (the increment is
     mergeable-pending-review). For `DONE_WITH_CONCERNS`, **carry the developer's
     `Concerns:` forward** so `skills/solve/handoff.md` surfaces it in the PO solution brief
     under *Needs your eyes* (same forward-carry channel as the gate's `untestable:` items).
   - `BLOCKED` → **leave it in progress** and surface the developer's `Next:` blocker to the
     PO as a clear question (a genuine blocker — do not guess past it).
   - `NEEDS_CONTEXT` → **leave it in progress** and post the developer's `Next:` context gap
     as a **Linear comment** on the unit for the PO to fill (the orchestrator's
     `**[backlogd]**` comment, distinct from the developer's work-log comment); **do not
     re-dispatch** the specialist — the spec must change first.
   - `DISPUTES_AC` → **leave it in progress** and log the developer's `Disputed-AC:`
     challenge as a **Linear comment** on the unit, addressed to scope / the PO who own the
     AC (the orchestrator's `**[backlogd]**` comment, distinct from the developer's work-log
     comment); **do not re-dispatch** the specialist and **do not edit the AC yourself** —
     the AC owner keeps or sharpens the AC first. See `capture.md` → *`DISPUTES_AC`* for the
     boundary (the developer only emits the challenge; it never sets state, overrules scope,
     or merges).
   - A malformed/missing STATUS first line → treat as `BLOCKED` for safety and surface the
     malformed contract to the PO (see `capture.md` → *Malformed STATUS*).

   **Stop conditions are unchanged in shape, only keyed off STATUS now.** On `DONE` /
   `DONE_WITH_CONCERNS` continue the loop. On `BLOCKED` / `NEEDS_CONTEXT` / `DISPUTES_AC`:
   **in a sequential single-unit group** stop the run immediately; **in a parallel group**
   still capture/transition this unit, but let the sibling dispatches in the group finish
   first — once every dispatch in the group has returned and been transitioned (and after
   the walk's collect step in `skills/solve/walk.md`), stop the run if any unit in the group
   returned `BLOCKED` / `NEEDS_CONTEXT` / `DISPUTES_AC`. Never start the next parallel group
   on a non-terminal STATUS (`BLOCKED` / `NEEDS_CONTEXT` / `DISPUTES_AC`).

   On a **Project-form** run, when a unit returns `BLOCKED` or `NEEDS_CONTEXT` or
   `DISPUTES_AC`, post a project-thread health update with marker `blocked` per
   **`skills/linear/references/documents-and-updates.md` § "Project health updates"** —
   health is `at risk` for a single blocker / first stall, `off track` when multiple
   blockers are open or rework is repeating (the derivation rules in that reference are
   the source of truth). **Single-issue and sub-issue forms do NOT post this update.**

8. **Commit the unit** on the problem's branch (or, in a parallel group, on the unit's
   sub-branch) — one commit per unit, conventional message referencing the issue (the
   developer ran no git; you own the commit). Use `$WT` for a sequential single-unit
   group and `$WT_unit` for a unit in a parallel group:

       git -C "$WT_or_WT_unit" add -A
       git -C "$WT_or_WT_unit" commit -m "{type}(#{identifier}): {what this unit did}"

   In a parallel group, the per-unit commit lands on the unit's sub-branch
   (`{gitBranchName}--unit-{unit-identifier}`); `skills/solve/walk.md`'s collect step
   fast-forward-merges that sub-branch into the problem branch after every dispatch in
   the group has returned. Identity-guard checks (`backlogd.expectedEmail` /
   `hooks/git/pre-commit`) apply automatically — `git config` is per-repo and shared
   across all linked worktrees of the same repo.

<!-- markdownlint-enable MD029 -->

## Note on file-edge writes (low-signal)

The graph used to also record `touches` edges (one per changed file) at this step. That
signal is **derivable from `git log`** and is now a *low-priority aside* — the new flow
above does **not** emit it. `prior_work` still surfaces historical `touches` data when
present, so the loop benefits from old graphs without recreating them. If you have a
specific need to record file edges, `scripts/graph.py emit ...` still works, but the
default loop intentionally skips it.
