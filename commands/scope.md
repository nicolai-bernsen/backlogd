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

A problem is *execution-ready* when its **description** carries a clear spec and a
`## Acceptance Criteria` section — the canonical signal `/backlogd:solve` looks for to know a
problem is already shaped.

- Read the problem. If it already has a spec and `## Acceptance Criteria`, refine only what is
  unclear.
- Otherwise write them: a short spec of the desired *outcome*, then `## Acceptance Criteria` as
  a checklist of observable, testable statements.
- **Only pause for the product owner** if the problem is too ambiguous to write acceptance
  criteria, or a decision only they can make blocks shaping. Ask at most **3** questions, then
  proceed. Do not guess at a genuine product decision.

Write the spec and AC into the issue **description** with `save_issue` — pass the existing
issue `id` so you update in place, never create a duplicate.

## 4. Decompose — only as much as the problem earns

Follow the **promote-on-discovery** rule from `skills/linear/`; do not predict size up front:

- **Default — keep it a single Issue.** A focused problem (one unit of work, no phases, no
  internal dependencies) needs no decomposition. `/backlogd:solve` hands the whole issue to one
  developer.
- **Create sub-issues** (`save_issue` with `parentId`) when the problem breaks into **≥2
  independently-solvable units**. Sequence them with **`blocked-by`** so `solve` can walk them
  in dependency order. Keep roughly one level — do not nest deeply.
- **Promote to a Project** when the problem reveals distinct **phases**, or enough scope that
  sub-issues stop conveying progress. Create an Issue per unit under the Project, group phases
  as **Milestones**, and wire `blocked-by` for ordering. (Engagement-level grouping is the
  **Initiative** — see `skills/linear/`.)
- **When in doubt, stay an Issue.** Promotion on evidence is cheap; a premature Project that
  never closes is not.

<<<<<<< HEAD
## 4.5. Pick the specialist

Once the spec, AC, and decomposition are settled, pick the **specialist** developer that
will solve each dispatch target — the problem itself (single-issue form) or each sub-issue
(decomposed). The parent of a decomposed problem is a **container**, not a dispatch
target — skip picking for it.

A *specialist* is any agent file whose `name:` frontmatter begins with `developer-`. Two
discovery sources, globbed in order (the per-repo source wins on a name clash):

- `${CLAUDE_PLUGIN_ROOT:-.}/agents/developer*.md` — the plugin's own roster
- `.claude/agents/developer*.md` — per-project additions (relative to the repo root)

Read each file's frontmatter and collect `{name, description}` for every well-formed entry
whose `name` starts with `developer-`. **Skip** any file with missing/malformed
frontmatter, and note the skip in §6's report (don't fail the run on it). The generic
`developer` (no suffix) is the **fallback**, not a specialist — exclude it from the picker
but use it when nothing matches.

**Pick.** For each dispatch target, read the title + spec + AC and reason about best fit
against the collected roster of `{name, description}` entries. The match is description-
driven — there is no taxonomy or scoring; pick the single specialist whose description
best fits the unit of work. If nothing is a clear match, pick generic `developer` and say
so explicitly in §6 (e.g. `specialist -> developer (no specialist matched)`).

**Record — two surfaces, on purpose:**

- **Label (machine-readable).** Apply an `agent:<suffix>` label to the issue — this is
  what `/backlogd:solve` reads. For `developer-docs`, the label is `agent:docs`. The
  `agent:*` family is backlogd-owned (see
  `skills/linear/references/linear-mcp.md`). The label is **created on first use** —
  pass the new label name in `save_issue`'s `labels: [...]`; Linear's MCP auto-creates
  unknown labels on write. **No label** = generic developer (less noise) — so skip the
  label when the picker fell back to generic.
- **Description line (PO-readable).** Write a `**Specialist:** developer-<suffix> —
  <one-line because>` line in the issue **description**, positioned **just above** the
  `## Acceptance Criteria` heading. This explains *why* this specialist; the PO can flip
  the label to override. When the picker fell back to generic, write
  `**Specialist:** developer (no specialist matched)` — no `because` needed.

The PO owns the label: flipping `agent:<a>` → `agent:<b>` between scope and solve
re-routes the next dispatch. Multiple `agent:*` labels on one issue are an error solve
will catch.
=======
## 4b. Apply `kind:ops` if the problem is repo-ops

If the problem's outcome is **GitHub repo operations or external content** (topics,
Discussions, releases, repo metadata, labels, `good first issue`s, awesome-list
submissions, drafts in `docs/`) — i.e. there is no source diff to land — apply the
**`kind:ops` label** to the problem (and to any sub-issues that are themselves ops-only).
`/backlogd:solve` routes ops-labelled units through `skills/solve/ops.md` (no worktree,
no PR; the developer takes `gh` actions and posts an action log).

- Create the label on the team via `create_issue_label({ team, name: "kind:ops" })` if
  `list_issue_labels` shows it is missing. It is just a routing flag — no automation
  beyond that.
- If the problem is **mixed** (some units ops, some units code), prefer to split it into
  two problems at shaping time rather than letting `solve` halt on the mixed case.
>>>>>>> origin/dev

## 5. Set priority and stop

Set the problem's **priority** so `/backlogd:solve` can order the queue. Leave **estimates
off** — backlogd works one problem at a time, so points add no signal.

Then **stop**. Do **not** move the problem to a started state, and do **not** dispatch a
developer. Shaping is complete; solving is a separate, deliberate step the product owner
triggers with `/backlogd:solve`.

## 6. Report

Show what you shaped so it is visible in the transcript:

```
Shaped: {identifier} — {title}
  acceptance criteria  -> {n} written
  decomposition        -> single issue | {n} sub-issues (blocked-by wired) | promoted to Project "{name}" ({n} issues, {m} milestones)
<<<<<<< HEAD
  specialist           -> developer-{suffix} (label agent:{suffix}) | developer (no specialist matched) | per sub-issue: NB-N -> developer-{suffix}, …
=======
  route                -> standard (code → worktree + PR) | ops-only (kind:ops, no PR)
>>>>>>> origin/dev
  priority             -> {priority}
Ready for: /backlogd:solve {identifier}
```

If any specialist file in the roster was skipped because of malformed frontmatter,
mention the skip on its own line under `specialist` (e.g.
`skipped: agents/developer-foo.md (missing name frontmatter)`).
