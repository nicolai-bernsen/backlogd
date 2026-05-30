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

## Section template

A specialist's **body** follows the same six XML-tagged sections as the generic
`developer` (`agents/developer.md`), in this order. Keeping the layout identical is what
lets a specialist *clone* the developer and swap only what its flavour of work needs —
each section has a fixed job, and a one-line `<!-- purpose -->` comment opens each so you
know what belongs where:

| # | Section | Purpose |
|---|---|---|
| 1 | `<Role>` | What the specialist **is** and **is NOT** responsible for — including the negative-scope clause (no PRs, no Linear state, no dispatching, no scoping). |
| 2 | `<Constraints>` | Hard boundaries: which worktree to act in, no git, touch only relevant files, the Linear-surface "own issue only" rule, the read-only graph boundary, the DoD floor. |
| 3 | `<Investigation_Protocol>` | The ordered steps — step 1 is *open the work log* (the NB-338 Step 0 contract), then read context, consult prior work, understand, act, close the log. |
| 4 | `<Output_Format>` | The exact shape of the two outputs: the single `**[backlogd developer]**` comment edited in place, and the final report whose **first machine-readable line is `STATUS: <enum>`** (see [The STATUS contract](#the-status-contract)), followed by the structured body. |
| 5 | `<Failure_Modes_To_Avoid>` | The named ways the dispatch fails even when the code looks right (missing/duplicated work-log comment, touching another issue, fabricating a result). |
| 6 | `<Final_Checklist>` | Mechanical yes/no checks run before reporting — orchestrator-defined **harness checks** (identical across specialists) plus specialist-owned **domain checks** (see [Harness vs domain checks](#harness-vs-domain-checks)). |

### What a specialist may narrow vs must keep identical

- **May narrow / adapt** — `<Role>`, `<Constraints>`, the **step content** of
  `<Investigation_Protocol>`, `<Failure_Modes_To_Avoid>`, and the **domain checks** in
  `<Final_Checklist>`. A docs specialist narrows `<Role>` to "README polish, narrative
  prose" and adds a `<Constraints>` line like "don't touch code under `src/`"; a release
  specialist narrows `<Investigation_Protocol>` to its release steps. The work-log step
  (step 1) stays — every specialist opens a work log.
- **Must keep identical** — the **`<Output_Format>` envelope** (the badge, the
  single-comment-edited-in-place rule, the **`STATUS: <enum>` first line** of the final
  report, and the `What I did / Result / Concerns / Next` body shape), and the **harness
  checks** in `<Final_Checklist>` (see [Harness vs domain checks](#harness-vs-domain-checks)).
  These are what the orchestrator
  parses across *all* specialists; the `STATUS:` line in particular is the contract the
  dispatch loop branches on mechanically (see [The STATUS contract](#the-status-contract)),
  so a specialist that emits a different first line or a STATUS value outside the enum
  breaks the audit trail and the dispatch loop.

### Harness vs domain checks

The `<Final_Checklist>` (section 6) holds **two** kinds of mechanical yes/no box, and the
split is what lets the orchestrator hold every specialist to the same bar:

- **Harness checks — orchestrator-defined, identical across specialists.** The five boxes
  the dispatch loop is held to: STATUS line is the literal first line; exactly one
  `**[backlogd developer]**` progress comment edited in place; changes exist to commit on
  the dispatched branch; all edits made under the dispatched worktree/branch; no internal
  contradiction (a `DONE` report carries no `BLOCKED`/`NEEDS_CONTEXT` claim). A specialist
  clones these **byte-for-byte** — it never edits, reorders, or drops one.
- **Domain checks — specialist-owned (≤3).** The boxes for *that* flavour of work: a
  developer checks "relevant tests/checks pass" and "no new dependencies"; a docs
  specialist might check "links resolve"; a release specialist "version bumped, changelog
  updated". Each specialist authors its own.

Both live in the developer prompt's `<Final_Checklist>` (`agents/developer.md`), and the
developer **reads the whole checklist aloud in its final report** — each box answered
yes/no + one line of evidence, not "review carefully". The linkage is mechanical: **any
harness box "no" forbids `DONE`** — the specialist reports `DONE_WITH_CONCERNS`, `BLOCKED`,
or `NEEDS_CONTEXT` instead (see [The STATUS contract](#the-status-contract) for the enum).

### Worked example — swapping `<Role>`

A hypothetical `developer-release` keeps sections 2–6 structurally the same and swaps the
identity and negative scope in `<Role>`:

```
<Role>
<!-- What you ARE and what you are NOT responsible for. -->

You are a **release developer** on a backlogd team. You own cutting **one** release —
version bump, changelog, tag prep — end to end, in the worktree your dispatch names.

You are **NOT** responsible for: opening or merging the release PR, transitioning Linear
state, dispatching other specialists, scoping the release, or self-reviewing your diff.
The scrum-master does all of that after you report.
</Role>
```

Everything below `<Role>` — `<Constraints>`, `<Investigation_Protocol>`,
`<Output_Format>`, `<Failure_Modes_To_Avoid>`, `<Final_Checklist>` — is cloned from
`agents/developer.md`, narrowing only the step content and domain checks for release work
while keeping the `<Output_Format>` envelope byte-for-byte — including the `STATUS: <enum>`
first line ([The STATUS contract](#the-status-contract)), which every specialist emits
unchanged so the orchestrator can branch on it the same way regardless of flavour.

## The STATUS contract

Every specialist's final report — the single structured summary the scrum-master reads —
**opens with a machine-readable `STATUS: <enum>` line**. This is the contract the
`/backlogd:solve` loop branches on *mechanically*: the orchestrator reads STATUS and maps
it deterministically to a Linear state transition and an orchestrator action, with **no
prose-heuristic parsing** of the free-text body. The STATUS line is the single source of
truth for "what happens next"; the body below it is for humans.

The enum has exactly **four** values:

| `STATUS` | Meaning | Linear transition | Orchestrator action |
|---|---|---|---|
| `DONE` | AC met, work landed in the worktree | → **In Review** | Accept the unit, run the quality gate, commit; on the last unit post the solution brief |
| `DONE_WITH_CONCERNS` | Work landed but the specialist flags a risk or partial coverage | → **In Review** | Same as `DONE`, **and** surface the concerns inline in the PO solution brief (under *Needs your eyes*) |
| `BLOCKED` | Cannot proceed without input outside the specialist's authority | **stay In Progress** | Surface the blocker to the PO as a question; stop the run (don't guess past it) |
| `NEEDS_CONTEXT` | The spec is too thin / ambiguous to act on | **stay In Progress** | Post the context gap as a Linear comment for the PO to fill; stop the run (do **not** re-dispatch) |

`DONE` and `DONE_WITH_CONCERNS` both mean *the increment exists and is mergeable-pending-review* —
the difference is whether the specialist attached a caveat the PO should see. `BLOCKED` and
`NEEDS_CONTEXT` both leave the unit In Progress, but they are **distinct**: `BLOCKED` is "I
know what to do but can't (missing access, a decision above my pay grade, a hard external
dependency)", while `NEEDS_CONTEXT` is "I can't even start — the problem as written is too
vague to turn into a concrete action." The orchestrator handles them differently
(`BLOCKED` → blocker question; `NEEDS_CONTEXT` → context-gap comment), so picking the right
one matters.

The orchestrator's deterministic branch table — STATUS → transition → action, plus how
each maps onto the coarse-grained graph outcome — lives in
[`skills/solve/capture.md`](../skills/solve/capture.md); `skills/solve/dispatch.md` step 7
consumes it.

### The reviewer maps onto the same enum

The independent reviewer (`agents/reviewer.md`, NB-326) shipped before this contract with
its own verdict vocabulary, and it **keeps that vocabulary** — `ok` / `needs-changes` in
`pre-commit-gate` mode, `accepted` / `sent back` / `needs you` in `verdict` mode. Rather
than rewrite the review machinery, the reviewer's verdicts **map onto the shared STATUS
enum** so the orchestrator reasons about both specialists in one vocabulary:

| Reviewer verdict (`verdict` mode) | Reviewer gate (`pre-commit-gate` mode) | Shared `STATUS` |
|---|---|---|
| `accepted` | `ok` | `DONE` |
| `accepted` with manual checks / caveats for the PO | `ok` carrying `untestable:` items | `DONE_WITH_CONCERNS` |
| `sent back` | `needs-changes` | `BLOCKED` *(the developer goes back; the unit can't pass as-is)* |
| `needs you` | — | `NEEDS_CONTEXT` *(AC too vague to verify; the PO must clarify)* |

This is a **documented mapping, not a code change to the reviewer** — the reviewer still
emits its own verdict glyphs and the gate/`/backlogd:review` machinery is untouched. If a
future change wants the reviewer to *literally* emit a `STATUS:` line, that is a separate,
cross-cutting unit (it touches `agents/reviewer.md`, `skills/solve/gate.md`, and
`commands/review.md`) and should be scoped on its own.

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
