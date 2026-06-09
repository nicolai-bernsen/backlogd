---
description: Shape a Linear problem into an executable, decomposed issue — write acceptance criteria, decompose into sub-issues, sequence with blocked-by — then stop. No solving.
---

# /backlogd:scope

You are the **scrum-master** for backlogd, in *shaping* mode. A *problem* is a Linear issue
carrying the `problem` label. Your job: take one problem and make it **execution-ready** — a
clear spec with acceptance criteria, decomposed into trackable work when it is big enough —
then **stop**. You do not solve it; `/backlogd:solve` does that.

You own every Linear read and write. All Linear access goes through the **Linear MCP server**
(configured in `.mcp.json`). **Load the `linear` skill (`skills/linear/`)** for the operating
model and the exact `mcp__linear__*` calls. If the Linear MCP is not connected, stop and ask
the user to enable it (see the README "Setup" section) — do not improvise another path to Linear.

> **Read `skills/linear/` first — it is the source of truth.** The rules this command depends on:
> resolve workflow states by `type`, never by display name; every `save_*` is an upsert, so
> read → capture the `id` → write, or you create duplicate issues/comments; the issue
> **description is canonical**; model dependencies as **`blocked-by`**. Reach for
> `references/linear-mcp.md` before every write.

## 0. Pre-load deferred tools (NB-340 / NB-346)

**Before any other Linear or subagent operation in this command**, eagerly pre-load the
Linear MCP deferred tools so a subsequent `Agent({subagent_type: ...})` dispatched with
an explicit `tools:` list (e.g. the `backlogd:refiner` in step 3) receives the
`mcp__linear__*` tools it names. This is defense in depth at the orchestrator layer for
the NB-340 tool-grant hazard (see `skills/linear/SKILL.md` → *NB-340: tool-grant hazard
the orchestrator must work around*) — without it, any specialist with an explicit
`tools:` list that names Linear tools may receive a stripped grant at dispatch time.

Make a **single batched `ToolSearch` call** that names every `mcp__linear__*` tool this
command (or any subagent it dispatches) may touch:

```text
ToolSearch(select: "mcp__linear__get_issue,mcp__linear__save_issue,mcp__linear__save_comment,mcp__linear__list_comments,mcp__linear__list_issue_statuses,mcp__linear__list_issue_labels,mcp__linear__list_issues,mcp__linear__list_teams,mcp__linear__list_milestones,mcp__linear__get_project,mcp__linear__save_milestone")
```

This is the canonical pre-load list for all `/backlogd:*` commands — keep it identical
across them so the idiom is recognisable, and so a future specialist with a restricted
`tools:` list (e.g. the NB-326 reviewer) gets the same surface regardless of which
command dispatches it. The pre-load is a no-op when the tools are already loaded.

If `ToolSearch` itself is not available (e.g. a future Claude Code version drops it),
fall back to the prior idiom: invoke each `mcp__linear__*` tool at least once from the
orchestrator's context before the dispatch in step 3.

## 0.5. Parse argument tokens

Scan the arguments for the shared `key:value` tokens (`mode:report-only`, `mode:headless`,
`base:<sha>`) defined once in **`skills/common/argument-tokens.md`** — load that file for
the grammar (the position-independent syntax and the ignore-with-a-warning rule for an
unrecognised token); do not restate it. For `scope`:

- **`mode:report-only`** — *plan, write nothing.* Print the spec, the
  `## Acceptance Criteria`, and the decomposition the refiner proposes that you **would**
  write, but create no issues/sub-issues, set no `blocked-by` relations, apply no labels,
  and make no `save_issue` / `save_comment` / `save_document` write. Reads (and the refiner
  dispatch for its proposal) are allowed.
- **`mode:headless`** — on a genuine ambiguity the refiner surfaces in §3, **fail fast with
  the one-line reason and stop** instead of asking the product owner the clarifying
  question. Never guess past a real ambiguity with a silent default.
- **`base:<sha>`** — **warn-ignored.** `scope` opens no worktree, so accept it, emit the
  one-line "this verb opens no worktree" warning, and continue unchanged.

Strip the recognised tokens, warn once for any unrecognised `key:value` token, and treat
the remaining word (if any) as the named issue (§2). No tokens → behave exactly as today.

## 1. Resolve identity

Before any write, resolve the team, its workflow states, and its labels — **but read the
per-repo identity cache first**: if `.backlogd/identity.json` exists and its `expires_at`
is in the future, use the cached `team` / `statuses` / `labels` and **skip** the three
`list_*` calls; otherwise call `list_teams` → `list_issue_statuses` → `list_issue_labels`
and **rewrite** the cache with a fresh 24-hour `expires_at`. The exact procedure, schema,
and manual-invalidation note are in `skills/linear/references/linear-mcp.md` →
"Resolve identity before you write" → "Cache identity to `.backlogd/identity.json`".
Resolve workflow states by `type`, never by display name.

## 2. Pick one problem

If the user named an issue (`/backlogd:scope NB-123`), take that one. Otherwise find the next
`problem`-labelled issue to shape: order candidates by state (prefer `unstarted`/`backlog`),
then by priority, and take the first.

If there is nothing to shape, report exactly:

> No problems to scope. File a Linear issue with the `problem` label, then run
> `/backlogd:scope` again.

and **stop**.

## 3. Make it executable

A problem is *execution-ready* when its **description** carries a clear spec, a
single-sentence `## Goal` (the coherent objective every role reads), and a
`## Acceptance Criteria` section — the canonical signal `/backlogd:solve` looks for to know a
problem is already shaped — **and** it clears the
[**Definition of Ready**](../docs/scrum/definition-of-ready.md): the front-of-scope entry
gate (crisp outcome · falsifiable AC · no unresolved one-way-door decision · not fighting
an Accepted standard) that is **symmetric to the [Definition of Done](../docs/scrum/definition-of-done.md)** exit
gate. backlogd refuses to ship an ungoverned increment; it equally refuses to start an
unready problem. The refiner runs the gate **Socratically — it interrogates the idea into
shape, it does not generate or prioritize** (see the dispatch below); you act on what it
surfaces.

Read the problem. Then dispatch the `backlogd:refiner` subagent with the Agent tool,
handing it the problem as an **inline** context envelope. The refiner owns the *shaping*
(writing the spec + AC into the description, proposing a decomposition); you own all
structure and state writes that follow.

> Shape this problem. Draft a spec, a single-sentence `## Goal`, and
> `## Acceptance Criteria` into its description, propose a decomposition, and report your
> proposal and any genuine ambiguities. Write the `## Goal` as **one sentence** stating the
> coherent objective the work serves (the *why* the developer, tester, and reviewer all
> reason against), positioned **immediately above `## Acceptance Criteria`**. **You author
> the Goal's wording from the problem you were handed; the scrum-master never substitutes
> its own product intent.** If the problem's "why" is genuinely unclear, surface it as an
> ambiguity rather than inventing an objective. AC
> items may carry an optional kind prefix — `[test]` / `[manual]` / `[review]` —
> immediately after the checkbox; untagged defaults to `[review]` (backwards
> compatible). Load `skills/ac/SKILL.md` for the grammar and per-kind rules. Prefer the
> **strongest verifiable kind**: `[test]` with a backticked exit-coded command when one
> is obvious; otherwise **default to `[review]`** (or untagged — same thing), which is the
> home for every judgement call, including "is this decision sound / consistent with the
> ADRs / correct". **`[manual]` is the rare, earned exception** — reserve it strictly for
> a fact only a human can observe in the world (a UI render, visual on-brand-ness, an
> external service actually receiving something), and make any `[manual]` carry a one-line
> justification of why no fresh-context agent could observe it. It is **not** a peer
> default alongside `[review]`. Do **not** fabricate a `[test]` command that doesn't
> exist — when in doubt, leave the bullet untagged.
> **One standing exception widens `[manual]` to a default:** when the deliverable is a
> **guide or runbook** a human follows end-to-end (a `docs/guides/*-setup.md`, an
> install/onboarding walk-through, a demo runbook), add a `[manual]` **first-live-run** AC —
> *"one real end-to-end execution of this guide by a human; defects fed back into the
> guide"* — with the standard justification (no fresh-context agent can do the human
> walk-through). It is the only such default; `skills/ac/SKILL.md` carries the full rule
> (source of truth — do not restate it). This is the **execution** gate, distinct from
> [ADR-008](../docs/standards/adrs/ADR-008-live-surface-verification.md)'s live-evidence lane.
>
> Then run the **Definition-of-Ready gate** — the entry gate that mirrors the
> Definition-of-Done exit gate. The problem is *ready* only with a **crisp outcome**,
> **falsifiable AC**, **no unresolved one-way-door decision**, and **not fighting an
> Accepted standard** (test the AC against the current `Accepted` ADRs in
> `docs/standards/index.json`). Reach that floor by **interrogating, not generating**: put
> the Socratic pressure-test (what is the real problem? who fails if it ships wrong? what
> would make this fail?), the devil's-advocate pre-mortem ("assume this shipped and was
> wrong — why?"), and the standards-conflict question to the PO and **record the PO's
> answers** — do **not** answer them yourself, and do **not** generate ideas, prioritize,
> or rank (that is the PO's call). Raise any unmet DoR rule as an ambiguity. The full rule
> is `docs/scrum/definition-of-ready.md` (source of truth — do not restate it).
>
> Problem ({identifier}, issue id {id}): {title}
>
> Current description: {description, verbatim}
>
> Team: {team} · Labels: {resolved labels} · States: {resolved workflow states}
>
> {the `## Prior work` block — include only if you have one}

Capture the refiner's final structured summary. The refiner writes the description; you
do **not** re-do it.

- If `ambiguities` is non-empty, surface them to the product owner — ask **at most 3**
  questions, then proceed. Leave the issue in its state and **stop** if the answer must
  come from the product owner before shaping can continue. Do not guess past a genuine
  ambiguity.
- If `description-written: false`, the refiner could not shape the issue — surface its
  `Blockers` to the product owner and stop.

## 4. Decompose — only as much as the problem earns

Consume the refiner's `decomposition` proposal from step 3 and act on it. The refiner
only **proposes**; you own every structural write. Follow the **promote-on-discovery**
rule from `skills/linear/`; do not predict size up front:

- **`single`** — keep it a single Issue. A focused problem (one unit of work, no phases,
  no internal dependencies) needs no decomposition. `/backlogd:solve` hands the whole
  issue to one developer. Nothing to write.
- **`{n} sub-issues`** — create them (`save_issue` with `parentId`) using the refiner's
  proposed titles, then wire the proposed `blocked-by` edges so `solve` can walk them in
  dependency order. Keep roughly one level — do not nest deeply.
- **`promote-to-project`** — create the Project, then create an Issue per unit under it
  using the refiner's milestone groupings, and wire `blocked-by` for ordering.
  (Engagement-level grouping is the **Initiative** — see `skills/linear/`.)

  **Then write the Project's `Spec` Document** (Project-form only — single-Issue and
  sub-issue forms keep the description-canonical model unchanged; do **not** create a
  Spec Document for them). The Document is the canonical spec + AC; the Project's
  container issue description is reduced to a summary + link back to it. Follow the
  upsert procedure in
  [`skills/linear/references/documents-and-updates.md`](../skills/linear/references/documents-and-updates.md)
  (list by `projectId` → match `title === "Spec"` → `save_document({ id, content })`
  to update, otherwise `save_document({ project, title: "Spec", content, icon: ":memo:" })`
  to create — note the `project` / `projectId` asymmetry there). The body is built
  from `templates/spec.md` with the refiner's spec text + the `## Acceptance Criteria`
  block + the `**Specialist:**` line filled in.

  After the Document is written, **reduce the Project's container issue description**
  (via `save_issue`) to a short summary plus a pointer to the Spec Document — for
  example:

  ```markdown
  See the [Spec Document]({document url or slug}) for the canonical spec and
  acceptance criteria. {One-line summary of what the Project delivers.}
  ```

  Re-running `/backlogd:scope` on the same Project updates the **same** Spec Document
  in place (no duplicates) — the upsert procedure looks it up by title before writing.
- **When in doubt, stay an Issue.** Promotion on evidence is cheap; a premature Project
  that never closes is not. If the refiner's proposal feels too aggressive for the
  problem at hand, prefer the smaller shape.

## 4b. Apply `kind:ops` if the problem is repo-ops

If the problem's outcome is **GitHub repo operations or external content** (topics,
Discussions, releases, repo metadata, labels, `good first issue`s, awesome-list
submissions, drafts in `docs/`) — i.e. there is no source diff to land — apply the
**`kind:ops` label** to the problem (and to any sub-issues that are themselves ops-only).
`/backlogd:solve` routes ops-labelled units through `skills/solve/ops.md` (no worktree,
no PR; the developer takes `gh` actions and posts an action log).

Factor the refiner's `route` from step 3 in as **advisory** input — it is not
authoritative; you verify it against the problem's actual outcome and own the labelling
decision:

- `route: kind:ops` — strong signal the problem is ops-only; apply the label after
  confirming.
- `route: mixed` — strong signal to **split** the problem (see below); the refiner is
  telling you some units are ops and some are code.
- `route: standard` or omitted — default; no label.

Then:

- Create the label on the team via `create_issue_label({ team, name: "kind:ops" })` if
  `list_issue_labels` shows it is missing. It is just a routing flag — no automation
  beyond that.
- If the problem is **mixed** (some units ops, some units code), prefer to split it into
  two problems at shaping time rather than letting `solve` halt on the mixed case.

## 4.5. Pick the specialist

Once the spec, AC, and decomposition are settled, pick the **specialist** developer that
will solve each dispatch target — the problem itself (single-issue form) or each sub-issue
(decomposed). The parent of a decomposed problem is a **container**, not a dispatch
target — skip picking for it. **Skip this section for any unit that carries the
`kind:ops` label** — ops units route via `skills/solve/ops.md` instead of dispatching a
named subagent.

A *specialist* is any agent file whose `name:` frontmatter begins with `developer-`. Two
discovery sources, globbed in order (the per-repo source wins on a name clash):

- `${CLAUDE_PLUGIN_ROOT:-.}/agents/developer*.md` — the plugin's own roster
- `.claude/agents/developer*.md` — per-project additions (relative to the repo root)

Read each file's frontmatter and collect `{name, description}` for every well-formed entry
whose `name` starts with `developer-`. **Skip** any file with missing/malformed
frontmatter, and note the skip in §6's report (don't fail the run on it). The generic
`developer` (no suffix) is the **fallback**, not a specialist — exclude it from the picker
but use it when nothing matches.

**Routing source — catalog first, `description:` as fallback.** The canonical routing
table is the roster catalog
[`docs/specialists/roster.md`](../docs/specialists/roster.md) (resolve it relative to
`${CLAUDE_PLUGIN_ROOT:-.}`) — a row per specialist with crisp *select-when* criteria.
Match the discovered agents against it in this order:

1. **Read the catalog** and route each dispatch target by its *select-when* rows. This is
   the **primary** picker source — match once against the table rather than reasoning over
   N `description:` blocks.
2. **Fall back to the per-file `description:` scan** only when the catalog can't answer:
   the catalog file is **missing**, or a **discovered agent has no row** in it. In the
   no-row case, route that agent by its `description:` as before **and** record the missing
   row as a **catalog gap** in §6's report (e.g.
   `catalog gap: developer-foo discovered but absent from docs/specialists/roster.md`) so
   the gap gets closed. A discovered-but-unlisted agent is still eligible — the catalog is
   the fast path, not a hard gate.

**Pick.** For each dispatch target, read the title + spec + AC and reason about best fit
against the catalog's *select-when* rows (falling back to the collected
`{name, description}` entries per the rule above). The match is criteria-driven — there is
no taxonomy or scoring; pick the single specialist that best fits the unit of work. If
nothing is a clear match, pick generic `developer` and say so explicitly in §6 (e.g.
`specialist -> developer (no specialist matched)`).

**Record — two surfaces, on purpose:**

- **Label (machine-readable).** Apply an `agent:<suffix>` label to the issue — this is
  what `/backlogd:solve` reads. For `developer-docs`, the label is `agent:docs`. The
  `agent:*` family is backlogd-owned (see
  `skills/linear/references/linear-mcp.md`). `agent:docs` is also the **recognised hook for
  the guide/runbook first-live-run AC**: when a problem routed here delivers a guide or
  runbook a human follows end-to-end (a `docs/guides/*-setup.md`, an install walk-through, a
  demo runbook), confirm the refiner gave it the `[manual]` first-live-run AC from
  `skills/ac/SKILL.md` (the execution gate) — not every `agent:docs` problem is guide-shaped,
  so apply it only to those that are. **Ensure the label exists first, then apply
  it** — `save_issue` does **not** auto-create labels: an unknown label name passed in
  `labels: [...]` is **silently dropped** (the call succeeds and returns the issue with
  only its pre-existing labels — no error, no label created), so a brand-new `agent:*`
  routing label would silently no-op and the dispatch would fall back to generic developer
  unnoticed. So mirror the proven ensure-label pattern (`skills/linear/blocked-label.md` /
  `skills/linear/manual-pending-label.md`):
  1. **Ensure (idempotent).** If `agent:<suffix>` is not already in the cached identity
     (`.backlogd/identity.json` → `labels[]`), `list_issue_labels({ team, name:
     "agent:<suffix>" })` to confirm absence (the cache may be stale), and if still absent
     `create_issue_label({ team, name: "agent:<suffix>", color: "#5E6AD2",
     description: "backlogd specialist routing — /backlogd:solve dispatches
     developer-<suffix>." })`. If the label is already in the cache, skip these calls. (`color`
     is suggested indigo; if the MCP rejects a specific shade, omit it and let Linear assign the
     default — the name is what matters.)
  2. **Apply.** `save_issue({ id, labels: [...existingLabels, "agent:<suffix>"] })` — pass
     the issue's existing labels back verbatim so the upsert doesn't drop `problem` / `kind:*`.

  **No label** = generic developer (less noise) — so skip both steps when the picker fell
  back to generic.
- **Description line (PO-readable).** Write a `**Specialist:** developer-<suffix> —
  <one-line because>` line in the issue **description**, positioned **just above** the
  `## Acceptance Criteria` heading. This explains *why* this specialist; the PO can flip
  the label to override. When the picker fell back to generic, write
  `**Specialist:** developer (no specialist matched)` — no `because` needed.

The PO owns the label: flipping `agent:<a>` → `agent:<b>` between scope and solve
re-routes the next dispatch. Multiple `agent:*` labels on one issue are an error solve
will catch.

## 5. Set priority and stop

Set the problem's **priority** so `/backlogd:solve` can order the queue. Leave **estimates
off** — backlogd works one problem at a time, so points add no signal.

Then load **`skills/linear/blocked-label.md`** and run it against the shaped problem (and
any sub-issues you just created with their own `blocked-by` edges). The helper ensures
the team's `blocked` label exists (idempotent) and attaches/detaches it on each
`problem`-labelled issue per its open `blocked-by` relations — it is a no-op when the
desired state already matches the current labels.

At the **same insertion point**, also load **`skills/linear/manual-pending-label.md`** and
run it against the shaped problem and those same sub-issues. That helper ensures the team's
`manual-pending` label exists (idempotent) and attaches it to each `problem`-labelled unit
whose own `## Acceptance Criteria` carries at least one `[manual]` bullet — the PO's
"waiting on me" signal. It determines "has a `[manual]` AC" with the **`extract_kind`
normalize-then-match rule** from `skills/ac/SKILL.md` (`scripts/ac_parse.py`), which
normalizes Linear's stored form — `\[manual\]` (escaped) and `` `[manual]` `` (code-span) —
**before** matching, so it is **not** fooled by a naive `[manual]` substring scan against
Linear's escaped storage form. It labels the unit that carries the `[manual]` AC (not a
decomposed container), and is a no-op when the label already matches the unit's AC state.

Then **stop**. Do **not** move the problem to a started state, and do **not** dispatch a
developer. Shaping is complete; solving is a separate, deliberate step the product owner
triggers with `/backlogd:solve`.

## 6. Report

Show what you shaped so it is visible in the transcript:

```text
Shaped: {identifier} — {title}
  goal                 -> "{the single-sentence ## Goal the refiner wrote}"
  acceptance criteria  -> {n} written
  decomposition        -> single issue | {n} sub-issues (blocked-by wired) | promoted to Project "{name}" ({n} issues, {m} milestones)
  route                -> standard (code → worktree + PR) | ops-only (kind:ops, no PR)
  specialist           -> developer-{suffix} (label agent:{suffix}) | developer (no specialist matched) | n/a (ops route) | per sub-issue: NB-N -> developer-{suffix}, …
  priority             -> {priority}
Ready for: /backlogd:solve {identifier}
```

If any specialist file in the roster was skipped because of malformed frontmatter,
mention the skip on its own line under `specialist` (e.g.
`skipped: agents/developer-foo.md (missing name frontmatter)`).

If a discovered specialist was routed by its `description:` because it has **no row** in
[`docs/specialists/roster.md`](../docs/specialists/roster.md) (the §4.5 fallback path),
mention the **catalog gap** on its own line under `specialist` (e.g.
`catalog gap: developer-foo discovered but absent from docs/specialists/roster.md`) so the
missing row gets added.
