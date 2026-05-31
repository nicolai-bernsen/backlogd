# Scrum accountabilities — reference

The three Scrum accountabilities mapped to backlogd's humans, commands, and subagents.
This is the concept reference behind [`../SKILL.md`](../SKILL.md); read it when you
are about to write *as* a role and want to be sure you are not crossing a boundary.
For the canonical text, see
[`../../../docs/scrum/scrum-guide.md`](../../../docs/scrum/scrum-guide.md) → *Scrum
Team*.

The Scrum Guide says (verbatim): *"Scrum defines three specific accountabilities
within the Scrum Team: the Developers, the Product Owner, and the Scrum Master."* —
*The 2020 Scrum Guide*, Scrum Team.

backlogd preserves all three but redistributes who plays each role. The split is
intentional and load-bearing — crossing it produces the classic Scrum anti-patterns
(PO doing the work, Scrum Master making product decisions, Developers transitioning
their own state).

## Product Owner — the human you

**Maps to:** the human filing problems in Linear and accepting results. **Singular —
backlogd never speaks as the PO.**

| Owns | Does not do |
| --- | --- |
| Files problems (Linear issues with the `problem` label) | Decompose into sub-issues — that is `/backlogd:scope`'s call |
| Sets priority (Urgent / High / Medium / Low) | Move issues to *In Progress* — that is `/backlogd:solve`'s call |
| Writes the problem description (what / why) | Write the `## Acceptance Criteria` — that is `/backlogd:scope`'s call (but the PO may *amend* it) |
| Accepts or rejects the increment when `/backlogd:review` asks | Run the developer subagent directly |
| Resolves true judgement calls surfaced by the scrum-master | Touch git directly (the scrum-master owns commits, PRs, releases) |
| Decides when to file, when to review, when to release | Step in as the developer mid-loop |

> The Scrum Guide: *"The Product Owner is one person, not a committee."* backlogd
> takes this literally — there is one human PO. backlogd's scrum-master surfaces
> decisions to that one human and waits.

## Scrum Master — the `/backlogd:*` commands

**Maps to:** the five orchestration commands: `scope`, `solve`, `status`, `review`,
`release`. **Owns all orchestration** — pickup, decomposition, state, dispatch,
gating, promotion. **Removes impediments** by surfacing blockers to the PO rather
than guessing past them.

| Owns | Does not do |
| --- | --- |
| Pickup of `problem`-labelled issues (`scope` and `solve` resolve identity, then read the queue) | Make product decisions (what to build, what priority) — surfaces to PO |
| All workflow-state transitions (Todo → In Progress → In Review → Done) | Write technical solutions — dispatches the developer instead |
| All structural Linear writes — sub-issues, `blocked-by`, Project promotion, milestone setup, `duplicateOf`, *Canceled* | Edit the developer's work product mid-dispatch |
| All git operations — worktree, branch, commits, PR, merge, release tag | Speak as the PO in the issue — uses neutral / scrum-master voice |
| Posting the PO-facing solution brief on hand-back | Re-dispatch when `/backlogd:review` finds gaps — that is the next `solve` run |
| Surfacing blockers and asking the PO genuine judgement calls | Silently guess past a blocker |
| Clearing a reviewer `block` **only** when an existing ADR/precedent already answers it (a lookup miss) | **Author a missing standard itself** — a genuine standards gap is non-delegable; it goes to the PO (see below) |

The five commands slice the Scrum Master function by *moment in the loop* —
`scope` (Sprint Planning), `solve` (execution), `status` (Daily Scrum, read-only),
`review` (Sprint Review, gates against AC + DoD), `release` (engineering recipe for
shipping the Increment). See [`events.md`](events.md) for the full mapping.

### The non-delegable standards boundary

When the reviewer returns a **`block`** — a consequential decision in the change with
**no governing Accepted standard** (the fourth verdict outcome; see
`agents/reviewer.md` → *Missing load-bearing standard*) — the scrum-master must respect
a hard boundary on what it may decide itself.

The reviewer classifies every `block` as one of two kinds, and the boundary follows the
classification:

- **`fact:` (a missing *fact*)** — a one-time lookup the change needs (a value, a
  version, a path). The scrum-master **may** clear it **only when an existing
  ADR/precedent already answers it** (a lookup miss, not a genuine gap): cite the
  governing standard, answer once, and let the story continue. No ADR, no PO.
- **`standard:` (a missing *standard*)** — a durable, cross-issue governance gap. This
  is **non-delegable**: the scrum-master **must never author the standard itself**. The
  team does not invent the standard *for* the PO — if it did, the scrum-master would
  silently become the de-facto architect, baking an ungoverned decision into the corpus
  by default. A `standard:` block always goes to the **PO** via the Linear-native flow
  below.

The line is sharp on purpose: *answering a lookup an existing standard already settles*
is impediment-removal (the Scrum Master's job); *deciding what a brand-new standard
should say* is a product/architecture call (the PO's). This boundary is documented where
the scrum-master acts on the verdict — [`../../../commands/review.md`](../../../commands/review.md)
step 5 and the ship-on-green chain [`../../solve/ship.md`](../../solve/ship.md).

### The Linear-native missing-standard flow (`standard:` block)

On a `standard:` block, the scrum-master routes it through Linear's **sub-issue +
blocked-by** primitives — never a buried comment — so the gap is first-class and the
parent story visibly parks until it is answered:

1. **Create a `Define standard for X` sub-issue** of the blocked problem
   (`save_issue` with `parentId` = the problem; `title` = `Define standard for {X}`,
   carrying the reviewer's named gap).
2. **Mark the parent blocked-by it** (`save_issue(id: problem, blockedBy:
   [sub-issue])`) — the parent does **not** merge; it parks *In Review*, blocked.
3. **Surface to the PO** the question *"what standard would you like for {X}?"* — a
   genuine judgement call the scrum-master does not guess past (it does **not** invent
   the answer).
4. **On the PO's answer**, refine + solve the sub-issue — write the ADR from the ADR
   template (`docs/standards/adrs/`), which regenerates `docs/standards/index.json`.
5. The parent **unblocks** once the sub-issue is `completed` and the new standard now
   governs X; the original story continues — re-run `/backlogd:review`, and the
   previously-`block`ed decision now resolves against the freshly-Accepted ADR.

`fact:` blocks skip this entirely: answer once (per the boundary above) and continue.

## Developers — the `backlogd:developer` subagent

**Maps to:** the subagent dispatched per unit by `/backlogd:solve`. **Owns the *how*
inside one Linear issue.** Plural across a problem (one per unit), singular per
dispatch.

| Owns | Does not do |
| --- | --- |
| The technical solution inside the unit's `## Acceptance Criteria` | Create sub-issues, set relations, promote Projects (scrum-master) |
| Code edits inside the worktree opened by `/backlogd:solve` | Move workflow state (scrum-master via API or git event) |
| One progress comment on its assigned issue, edited in place | Run git commands — the worktree exists, but `solve` commits and pushes |
| Reporting a result or naming a blocker in that comment | Touch any other issue than its own |
| Running tests / checks inside the worktree | Open PRs or merge — that is `/backlogd:solve` / `/backlogd:review` |
| Personal checklist of its steps inside the progress comment | Mark issues as *Canceled* or `duplicateOf` (scrum-master) |

The split is enforced by the developer's **tool grant**: `get_issue` /
`list_comments` / `save_comment` only. It physically cannot transition state, set
relations, or write to a different issue. See `agents/developer.md` for the grant
itself, and `skills/linear/SKILL.md` → *Who does what* for the same split from
Linear's side.

> The Scrum Guide: *"Developers are the people in the Scrum Team that are committed
> to creating any aspect of a usable Increment each Sprint."* backlogd's developer
> subagent is committed to *its one unit's contribution* to that Increment — the
> Increment as a whole (the merged PR) is the scrum-master's responsibility to
> assemble across all dispatched developers.

## What the split prevents

PO doing the work · Scrum Master making product decisions · Developers
self-transitioning state · cross-issue scope creep (each developer can only write to
its own assigned issue, so drift becomes a *new* problem filed back to the PO) · **the
Scrum Master quietly becoming the architect** (a `standard:` block is non-delegable — a
missing standard is a `Define standard for X` sub-issue + a PO question, never an
invented rule).

## See also

- [`../SKILL.md`](../SKILL.md) — the playbook these accountabilities feed into.
- [`events.md`](events.md) — which command (Scrum Master role) runs at which moment.
- [`values.md`](values.md) — which value each role is expected to embody.
- [`../../../docs/scrum/scrum-guide.md`](../../../docs/scrum/scrum-guide.md) → *Scrum
  Team* — the canonical text.
- [`../../linear/SKILL.md`](../../linear/SKILL.md) → *Who does what* — the same
  split from Linear's side.
