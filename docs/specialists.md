# Specialist developers

backlogd's default loop dispatches the generic `developer` subagent for every problem. You
can sharpen that by **dropping in specialists** — a `developer-<suffix>` agent file per
flavour of work (docs, release, UI…) — and let `/backlogd:scope` pick the right one when
it shapes a problem. The product owner keeps final say: a Linear label exposes the choice
and flips it.

## The convention

A *specialist* is any Claude Code subagent whose `name:` frontmatter begins with
`developer-`. Examples:

```yaml
---
name: developer-docs
description: README polish, conventions pages, narrative prose — keeps the docs honest.
tools: Read, Grep, Glob, Edit, Write, mcp__linear__get_issue, mcp__linear__list_comments, mcp__linear__save_comment
model: inherit
---
```

The plain `developer` (no suffix) is the **fallback** — it stays as it is. You don't need
to redefine it; backlogd ships it.

## Discovery — two sources

When `/backlogd:scope` shapes a problem, it globs both:

- `<plugin-root>/agents/developer*.md` — the plugin's own roster (at v1, only
  `developer.md`)
- `<repo>/.claude/agents/developer*.md` — per-project additions

A file with malformed/missing frontmatter is **skipped** with a note in scope's report —
the run does not fail. On a name clash between the two sources, the per-project source
wins.

## How scope picks

The picker is **description-driven** — there's no taxonomy, no scoring, no extra
frontmatter. Scope reads the problem (title + spec + AC) and the roster
(`{name, description}` per agent), reasons about best fit, and picks one. If nothing
clearly matches, it picks the generic `developer` and says so explicitly in its report.

> **Writing a good specialist description.** The description is what scope reasons over,
> so write it for that reader. Lead with the **shape of work** the specialist handles
> ("README polish, narrative prose, conventions pages") and what it **leaves out**
> ("not for code-level refactors"). One or two crisp sentences beats a paragraph; vague
> descriptions get vague picks.

## Two surfaces, on purpose

Scope records the picked specialist in two places:

- **Linear label `agent:<suffix>`** — the canonical, machine-readable surface.
  `/backlogd:solve` reads this label to decide which subagent to dispatch. The label is
  created on first use (Linear's MCP auto-creates labels passed to `save_issue.labels`).
  See `skills/linear/references/linear-mcp.md` for the `agent:*` label family.
- **`**Specialist:** developer-<suffix> — <one-line because>` line** in the issue
  description, just above the `## Acceptance Criteria` heading — the PO-readable
  explanation of *why* this specialist.

When scope falls back to generic `developer` (no specialist matched), it writes the
description line as `**Specialist:** developer (no specialist matched)` and applies
**no** `agent:*` label — no label = generic dispatch, less noise.

For a **decomposed** problem, the picker runs **per sub-issue**; the parent issue is a
container, not a dispatch target, and gets no `agent:*` label.

## How the PO overrides

The label is the override surface. Between scope and solve, the PO can:

- **Flip** `agent:<a>` → `agent:<b>` on the issue to re-route the next dispatch.
- **Remove** the `agent:*` label to fall back to generic `developer`.
- **Add** an `agent:<suffix>` label to an issue that didn't get one (when scope fell
  back to generic but you want a specialist).

Solve reads the label fresh every dispatch, so a flip between runs takes effect on the
next `/backlogd:solve`. **Once a run starts, the specialist for that dispatch is
fixed** — no mid-flight reassignment.

## How solve dispatches

`/backlogd:solve` reads the issue's labels at dispatch time:

- **No `agent:*` label** → dispatch generic `developer` — today's behaviour.
- **One `agent:*` label** → dispatch `developer-<suffix>` via the Task tool's
  `subagent_type` parameter. If the specialist file isn't discoverable, solve stops
  cleanly, lists what is available, and asks the PO to fix the label.
- **Multiple `agent:*` labels** → solve stops and reports the ambiguity, asks the PO to
  leave exactly one.

See `skills/solve/dispatch.md` for the exact resolution flow.
