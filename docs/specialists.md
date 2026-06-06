# Specialist developers

backlogd's default loop dispatches the generic `developer` subagent for every problem. You
can sharpen that by **dropping in specialists** — a `developer-<suffix>` agent file per
flavour of work (docs, release, UI…) — and let `/backlogd:scope` pick the right one when
it shapes a problem. The product owner keeps final say: a Linear label exposes the choice
and flips it.

> **Canonical roster.** The list of specialists and their *select-when* routing criteria
> lives in the roster catalog — [`docs/specialists/roster.md`](specialists/roster.md). That
> table is the source of truth `/backlogd:scope` reads to route; this page explains the
> *mechanism* (discovery, the picker, the two surfaces, PO override). Add a specialist =
> add a row there + drop the agent file.

## The rule: split agents on tool grants, not on topics

**Read this before you add a `developer-<suffix>` agent.** backlogd deliberately keeps
**one** `developer` agent. Developer *variety* — React, data, slides, prose — comes from
**the standards the developer loads**, not from a separate agent file per domain. The
"kind" of developer is **data, not code**: a React problem and a data problem are solved by
the same `developer`, behaving differently because different `applies-to` standards in
[`docs/standards/index.json`](standards/index.json) engage (the index-first selective load
the developer runs at dispatch — `agents/developer.md` → `<Investigation_Protocol>` step 5,
mirroring the reviewer's discipline). A new domain is a **new standards file, not a new
agent**.

So the bar for a genuinely separate agent is narrow and explicit:

> **A separate `developer-<suffix>` is justified ONLY when it needs a different
> capability / tool grant — never merely a domain label.** If the only difference is "it
> works on React" or "it works on data", that is a standards-profile difference and stays
> on the single `developer`. A separate agent earns its place only when its job needs a
> tool the generic `developer` must *not* have (or must be *denied* a tool the generic one
> has) — e.g. a slides specialist that needs a rendering tool, or a docs specialist
> restricted to a no-Bash/no-git grant.

This is what stops the roster sprawling into `developer-react` / `developer-python` /
`developer-go` near-duplicates that drift out of sync and need a new file per domain. Less
clutter **and** more power: variety lives in the **corpus** (standards), not the **roster**
(agents). When you think you want a new specialist, ask: *does it need a different tool
grant?* If no — write a standards file instead.

**Worked example — `developer-docs` is grant-justified, not topic-justified.** The
repo-local `developer-docs` specialist (`.claude/agents/developer-docs.md`) is a legitimate
separate agent **not because its topic is docs**, but because its job needs a **narrower
tool grant**: `Read, Grep, Glob, Edit, Write` plus the Linear comment tools only — **no
Bash, no git**. That reduced capability surface is the justification; "it edits prose" by
itself would not be. State the same test for any future specialist in its roster row's
*tool-grant style* column.

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
| --- | --- | --- |
| 1 | `<Role>` | What the specialist **is** and **is NOT** responsible for — including the negative-scope clause (no PRs, no Linear state, no dispatching, no scoping). |
| 2 | `<Constraints>` | Hard boundaries: which worktree to act in, no git, touch only relevant files, the Linear-surface "own issue only" rule, the read-only graph boundary, the DoD floor. |
| 3 | `<Investigation_Protocol>` | The ordered steps — step 1 is *open the work log* (the NB-338 Step 0 contract), then read context, consult prior work, understand, act, close the log. (The one-line *Problem Read* head step is authored once in the generic developer and inherited — a specialist does not re-author it.) |
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

```text
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

## Linear-comment output style

Every specialist posts its `**[backlogd <suffix>]**` progress comment as **Markdown the
product owner reads inside Linear**, whose renderer has gotchas (bare code fences,
em-dashes, tables, status emoji, and deep list nesting all render badly). The canonical
formatting rule-set is a Claude Code Output Style file —
[`output-styles/linear-comment.md`](../output-styles/linear-comment.md) — and the generic
developer's `<Output_Format>` points at it (the "Render it for Linear" bullet). The
constraint set, in brief:

> **The style governs every backlogd agent comment surface, not just the developer.** The
> same rule-set is wired (at the prompt level, the same "Render it for Linear" way) into the
> **reviewer** (`agents/reviewer.md` + `skills/reviewer/SKILL.md`: the `**[backlogd
> reviewer]**` work log and the `drafted-verdict-body`), the **scrum-master** (the
> `**[backlogd review]**` verdict rollup in `commands/review.md` §4 and the `**[backlogd]**`
> solution brief in `skills/solve/handoff.md`), and the **tester** (`agents/tester.md`: the
> `**[backlogd tester]**` evidence comment). In particular the per-AC and per-DoD verdict
> shows each line's state with a `- [x]` (met) / `- [ ]` (unmet) checkbox plus a leading bold
> state label (`MET` / `UNMET` / `NEEDS-PO` / `AWAITING-PO` / `NO-STANDARD`) — keeping the
> `[test]` / `[manual]` / `[review]` kind tag and the cited evidence — instead of the
> ✅/❌/❔/📝/🚫 status emoji it used before (NB-415). No agent comment surface uses a status
> or checkmark emoji.

| Constraint | Rule |
| --- | --- |
| Code fences | language-tag every fence (`bash`, `python`, `json`, `text`); never a bare fence |
| Dashes | no em-dashes or en-dashes; use commas, colons, or parentheses |
| Tables | no markdown tables (they render poorly in a Linear comment); use a bold-label list (`- **Label:** value`) or short prose instead |
| List depth | nest no deeper than two levels |
| Emoji | no decorative or sectioning emoji, and **no status or checkmark emoji**; use `- [x]` checkboxes or bold labels for state; the bold `**[backlogd …]**` badge stays literal text |

**How a specialist inherits it.** Because the `<Output_Format>` envelope is cloned
byte-for-byte (see [What a specialist may narrow vs must keep identical](#what-a-specialist-may-narrow-vs-must-keep-identical)),
a specialist inherits the "Render it for Linear" pointer for free — keep that bullet, just
swap the badge text to `**[backlogd <suffix>]**`. No specialist needs to restate the rules;
they live once in `output-styles/linear-comment.md`.

**How a specialist overrides it.** If a specialist's surface needs different formatting
(say it posts to a target with richer table support, or it must emit raw logs verbatim),
add a `<Constraints>` line in *that* specialist naming the deviation and why, and point at a
sibling output-style file rather than editing the shared one. Keep the override narrow:
the shared rule-set stays the default for every specialist that does not opt out.

> **Why an Output Style and not just prose.** `output-styles/linear-comment.md` is a real
> Claude Code Output Style: a maintainer can activate it session-wide with `/output-style`
> while driving backlogd, so the same constraints apply to the orchestrator's own Linear
> writes, not only the subagents' comments. The subagents additionally get the rules at the
> prompt level (the `<Output_Format>` pointer), which is what makes the constraint apply
> even when no session-level style is selected.

## Work-log tail schema

Every specialist's `**[backlogd <suffix>]**` progress comment closes with a lightweight,
**omit-when-empty** structured tail so each increment leaves a scannable **decision and
risk record**, not just a diff. ADR-004's transparency pillar wants that reasoning explicit.
The schema is authored once in the generic developer's `<Output_Format>`
(`agents/developer.md`) and is up to four bold-label sections, each dropped entirely when
it has nothing:

- **Decided:** the choices made, one line of rationale each.
- **Rejected:** alternatives weighed and why-not.
- **Risks:** the risks or partial coverage the PO should see — the **same content** as the
  `DONE_WITH_CONCERNS` `Concerns:` line, surfaced here rather than in a parallel channel.
- **Remaining:** follow-ups or unfinished edges for the next person.

**Omit-when-empty is load-bearing:** a section with nothing to say is omitted (never
`Decided: none`), so a trivial change stays terse — it may carry one section, or no tail at
all. The tail **adds** to the comment; it does **not** duplicate the `STATUS:` line (that
lives in the final report), the Problem-Read head line, or the files-changed list already
in the log.

**How a specialist inherits it.** Because the `<Output_Format>` envelope is cloned
byte-for-byte (see [What a specialist may narrow vs must keep identical](#what-a-specialist-may-narrow-vs-must-keep-identical)),
a specialist inherits this tail for free — keep the bullet, swap only the badge text. The
four sections and the omit-when-empty default carry over unchanged; the same pattern as the
Linear-comment style above.

**How a specialist overrides it.** A specialist whose flavour of work needs a different
record (say it must log raw command output verbatim, or its domain has a fifth recurring
section) adds a `<Constraints>` or `<Output_Format>` line in *that* specialist naming the
deviation and why, and keeps the four shared sections as the base. Keep the override
narrow: the four-section omit-when-empty tail stays the default for every specialist that
does not opt out.

## The STATUS contract

Every specialist's final report — the single structured summary the scrum-master reads —
**opens with a machine-readable `STATUS: <enum>` line**. This is the contract the
`/backlogd:solve` loop branches on *mechanically*: the orchestrator reads STATUS and maps
it deterministically to a Linear state transition and an orchestrator action, with **no
prose-heuristic parsing** of the free-text body. The STATUS line is the single source of
truth for "what happens next"; the body below it is for humans.

The enum has exactly **five** values:

| `STATUS` | Meaning | Linear transition | Orchestrator action |
| --- | --- | --- | --- |
| `DONE` | AC met, work landed in the worktree | → **In Review** | Accept the unit, run the quality gate, commit; on the last unit post the solution brief |
| `DONE_WITH_CONCERNS` | Work landed but the specialist flags a risk or partial coverage | → **In Review** | Same as `DONE`, **and** surface the concerns inline in the PO solution brief (under *Needs your eyes*) |
| `BLOCKED` | Cannot proceed without input outside the specialist's authority | **stay In Progress** | Surface the blocker to the PO as a question; stop the run (don't guess past it) |
| `NEEDS_CONTEXT` | The spec is too thin / ambiguous to act on | **stay In Progress** | Post the context gap as a Linear comment for the PO to fill; stop the run (do **not** re-dispatch) |
| `DISPUTES_AC` | The specialist *can* act but believes one AC is wrong and challenges it back to its owner (scope / the PO) | **stay In Progress** | Log the AC challenge as a Linear comment addressed to scope / the PO who own the AC; stop the run (do **not** re-dispatch, do **not** edit the AC). The AC owner keeps or sharpens the AC, then a later solve re-runs |

`DONE` and `DONE_WITH_CONCERNS` both mean *the increment exists and is mergeable-pending-review* —
the difference is whether the specialist attached a caveat the PO should see. `BLOCKED`,
`NEEDS_CONTEXT`, and `DISPUTES_AC` all leave the unit In Progress and stop the run, but they
are **distinct**: `BLOCKED` is "I know what to do but can't (missing access, a decision
above my pay grade, a hard external dependency)"; `NEEDS_CONTEXT` is "I can't even start —
the problem as written is too vague to turn into a concrete action"; `DISPUTES_AC` is "I
*can* act, but I believe one AC is wrong and want scope (the AC owner) to reconsider it,
instead of silently complying or drifting." The orchestrator handles them differently
(`BLOCKED` → blocker question; `NEEDS_CONTEXT` → context-gap comment; `DISPUTES_AC` →
AC-challenge comment to scope / the PO), so picking the right one matters.

`DISPUTES_AC` is the bounded, logged **dev→scope handoff at the AC seam**: a developer
formally challenges an AC back to its owner instead of either silently complying with a thin
AC or silently drifting from it. It is **two-way without removing who-decides-what** — the
developer only *emits* the challenge (one structured statement, never an unbounded
back-and-forth) and never sets Linear state, overrules scope, or merges; the orchestrator
*logs and routes* the challenge but never authors the AC's answer; scope / the PO keep sole
authority to keep or change the AC. The deterministic routing and the boundary are in
[`skills/solve/capture.md`](../skills/solve/capture.md) → *`DISPUTES_AC`*; the
accountabilities it preserves are in
[`skills/scrum/references/accountabilities.md`](../skills/scrum/references/accountabilities.md)
(scope owns the AC, the PO owns priority/intent, the developer owns the *how*).

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
| --- | --- | --- |
| `accepted` | `ok` | `DONE` |
| `accepted` with manual checks / caveats for the PO | `ok` carrying `untestable:` items | `DONE_WITH_CONCERNS` |
| `sent back` | `needs-changes` | `BLOCKED` *(the developer goes back; the unit can't pass as-is)* |
| `needs you` | — | `NEEDS_CONTEXT` *(AC too vague to verify; the PO must clarify)* |

This is a **documented mapping, not a code change to the reviewer** — the reviewer still
emits its own verdict vocabulary (`accepted` / `sent back` / `needs you` / `block`, with
per-line MET / UNMET / NEEDS-PO / AWAITING-PO / NO-STANDARD labels since NB-415) and the
gate/`/backlogd:review` machinery is untouched. If a
future change wants the reviewer to *literally* emit a `STATUS:` line, that is a separate,
cross-cutting unit (it touches `agents/reviewer.md`, `skills/solve/gate.md`, and
`commands/review.md`) and should be scoped on its own.

> **`DISPUTES_AC` is developer-emitted; the reviewer has its own pushback seam.** The fifth
> value is a **developer→scope** channel — only a *solving* specialist (the developer or a
> `developer-*`) emits `DISPUTES_AC`, to challenge an AC it believes is wrong back to the
> AC's owner. The reviewer's verdict vocabulary deliberately has **no** row that maps to
> `DISPUTES_AC`: when the reviewer disagrees about a *verdict*, its bounded pushback is the
> **dev↔reviewer one-shot reconciliation** the gate runs before PO escalation
> ([`skills/solve/gate.md`](../skills/solve/gate.md) → *Verdict reconciliation*), not an
> AC challenge. The two seams are symmetric (each lane can talk back once, both logged) but
> they sit at different boundaries — the developer challenges the *AC* (scope's), the
> reviewer and developer reconcile a *verdict* (the reviewer's) — and neither dissolves who
> decides what.

## Discovery — two sources

When `/backlogd:scope` shapes a problem, it globs both:

- `<plugin-root>/agents/developer*.md` — the plugin's own roster (at v1, only
  `developer.md`)
- `<repo>/.claude/agents/developer*.md` — per-project additions

A file with malformed/missing frontmatter is **skipped** with a note in scope's report —
the run does not fail. On a name clash between the two sources, the per-project source
wins.

## How scope picks

The picker is **criteria-driven**, and it reads two sources in order:

1. **The roster catalog first** — [`docs/specialists/roster.md`](specialists/roster.md).
   Scope reads the problem (title + spec + AC) and routes it by the catalog's *select-when*
   rows. This is the **primary** source: one scannable table read once, instead of
   reasoning over N `description:` blocks.
2. **The per-file `description:` as fallback** — used only when the catalog can't answer:
   the catalog file is **missing**, or a **discovered agent has no row** in it. A
   discovered-but-unlisted agent is still routed by its `description:` and picked if it
   fits; scope **flags the missing row as a catalog gap** in its report so the gap gets
   closed. The catalog is the fast path, not a hard gate.

There's still no taxonomy, no scoring, no extra frontmatter. If nothing clearly matches,
scope picks the generic `developer` and says so explicitly in its report.

> **Writing a good specialist description.** Even with the catalog as the primary source,
> the `description:` still matters — it is the fallback scope scans, and it is what Claude
> Code's *native* subagent picker reads. Keep it saying the same thing as the catalog row's
> *select-when* (the catalog wins for backlogd's picker when they drift). Lead with the
> **shape of work** the specialist handles ("README polish, narrative prose, conventions
> pages") and what it **leaves out** ("not for code-level refactors"). One or two crisp
> sentences beats a paragraph; vague descriptions get vague picks.

## Two surfaces, on purpose

Scope records the picked specialist in two places:

- **Linear label `agent:<suffix>`** — the canonical, machine-readable surface.
  `/backlogd:solve` reads this label to decide which subagent to dispatch. Scope **ensures
  the label exists** (`create_issue_label`, idempotent) before applying it — `save_issue`
  does **not** auto-create labels; an unknown name passed in `save_issue.labels` is silently
  dropped, which would silently no-op specialist routing. This mirrors the `blocked` /
  `manual-pending` ensure-label pattern. See `skills/linear/references/linear-mcp.md` for
  the `agent:*` label family.
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
