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

The five commands slice the Scrum Master function by *moment in the loop* —
`scope` (Sprint Planning), `solve` (execution), `status` (Daily Scrum, read-only),
`review` (Sprint Review, gates against AC + DoD), `release` (engineering recipe for
shipping the Increment). See [`events.md`](events.md) for the full mapping.

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
its own assigned issue, so drift becomes a *new* problem filed back to the PO).

## See also

- [`../SKILL.md`](../SKILL.md) — the playbook these accountabilities feed into.
- [`events.md`](events.md) — which command (Scrum Master role) runs at which moment.
- [`values.md`](values.md) — which value each role is expected to embody.
- [`../../../docs/scrum/scrum-guide.md`](../../../docs/scrum/scrum-guide.md) → *Scrum
  Team* — the canonical text.
- [`../../linear/SKILL.md`](../../linear/SKILL.md) → *Who does what* — the same
  split from Linear's side.
