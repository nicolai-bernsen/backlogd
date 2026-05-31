# backlogd roadmap — the Definition of 1.0

This is a roadmap doc, not a standard: it names a temporal milestone (it goes stale the
moment 1.0 ships), so it **cites** [ADR-004](standards/adrs/ADR-004-backlogd-identity.md)
rather than being an ADR. It doubles as the launch gate, the demo script for
[NB-396](https://linear.app/nicolai-bernsen/issue/NB-396), and the launch narrative.

backlogd's identity is fixed by ADR-004: **problem-type-agnostic empirical Scrum for an
agent team.** The framework is the Scrum scaffolding and never does the domain work; an
instance's value is **specialists × standards**. "1.0" must be the *honest minimum* of
that identity — the smallest set of capability where the core loop genuinely works
end-to-end on a real problem — not a louder claim than the substance. The two gates this
doc was written ahead of have since **shipped in v0.17.0**: the **1.0 substance has
shipped**, and what remains is **public-launch readiness** — the demo recording, this
README, the announcement, and the 1.0.0 version bump (see
[Preconditions](#preconditions-and-honest-status)).

## Definition of 1.0

backlogd is 1.0 when the **minimal end-to-end loop runs on a real problem, end to end,
with all three empirical pillars real** — transparency, inspection, and adaptation — not
ceremony. Concretely, 1.0 means all of the following are true at once:

- The [minimal working loop](#the-minimal-working-loop) runs unattended on a real,
  PO-filed problem and closes it.
- The reviewer **blocks on a missing load-bearing standard** rather than guessing — the
  moment that distinguishes a *team* from a single-agent runner.
- The **adaptation loop** closes: the team reads its own execution graph and files
  improvements back into the backlog.
- All [preconditions](#preconditions-and-honest-status) hold, and the two open gates
  ([NB-378](https://linear.app/nicolai-bernsen/issue/NB-378) and
  [NB-381](https://linear.app/nicolai-bernsen/issue/NB-381)) have shipped.

Everything beyond that minimum is [explicitly out of 1.0](#what-is-explicitly-out-of-10).

## The minimal working loop

The canonical end-to-end loop, in order:

1. **PO files a problem** — a Linear issue with the `problem` label, describing an outcome,
   not a spec.
2. **Scrum-master decomposes** — `/backlogd:scope` shapes the problem, writes its
   `## Acceptance Criteria`, and decomposes on discovery (sub-issues + `blocked-by`, or a
   Project).
3. **Specialist solves** — `/backlogd:solve` dispatches a specialist developer per unit of
   work; it owns the *how* and opens one PR.
4. **Tester / reviewer gate against AC + standards** — the tester proves the `[test]` AC;
   the independent verdict reviewer checks each increment against its AC, the
   [Definition of Done](scrum/definition-of-done.md), and the Accepted standards corpus.
5. **Reviewer blocks on a missing load-bearing standard** — when a consequential, one-way
   decision has no governing standard, the reviewer **blocks and asks** instead of
   inventing one. This is the **load-bearing moment of the whole loop**: a single-agent
   runner guesses and ships plausible-wrong work; a *team* surfaces "we need a rule for X."
6. **PO defines the standard** — the missing standard routes to the PO as a Linear-native
   blocker (a "Define standard for X" sub-issue, parent `blocked-by` it); the PO answers.
7. **The team resolves it** — the scrum-master refines and solves the sub-issue (writing
   the ADR), the parent unblocks, and the original problem continues.
8. **PR merged** — on a fully-green verdict the increment is squash-merged and the issue
   moves to Done.

### Why the missing-standard block is load-bearing

Anyone can wire an agent to a backlog and have it produce diffs. What makes backlogd a
*team* is that the reviewer is a standards-enforcing quality gate that knows the difference
between a decision it may make and one only the PO may make. The block is not a failure
mode — it is the loop working: the absence of a standard is itself a valuable finding, and
answering it is how the standards corpus bootstraps in a fresh repo. This is exactly
ADR-004's "value = specialists × standards" made operational.

### Adaptation is part of the minimal bar

ADR-004 holds backlogd to Scrum's **three empirical pillars — transparency, inspection,
and adaptation** — and judges it honest only if all three are real. The loop above is
transparency (Linear is the system of record; agent identity is visible) and inspection
(the execution graph plus the independent verdict). **It is not 1.0 without adaptation.**

The adaptation pillar is the **retrospective / adaptation loop**
([NB-381](https://linear.app/nicolai-bernsen/issue/NB-381)): completing a milestone triggers
a retrospective that **reads the execution graph** (rework, latency, blockers, recurring
gaps) and **files the load-bearing improvements back into the backlog** as problems, bugs,
or ADRs — closing the loop from inspection data to acted-on change. It is the batch-level
complement to the reviewer's in-the-moment gap detection: it catches patterns no single
review can see (for example, three problems in one milestone hitting the same missing
standard → one high-priority ADR). The retro *proposes*; the PO *prioritises* — the team
does not grade its own homework and auto-fix. Because adaptation is a core empirical-Scrum
pillar, a working retrospective is a 1.0 gate alongside the standards gate, **not** a
post-1.0 nicety.

## Real merged passes of the build loop

The loop is not aspirational — backlogd is built by running it on itself. Each problem
below was PO-filed → scoped → solved by a specialist → gated by the tester and the
independent verdict reviewer → squash-merged → moved to Done:

- **[NB-352](https://linear.app/nicolai-bernsen/issue/NB-352)** — Problem Read head step
  ([PR #104](https://github.com/nicolai-bernsen/backlogd/pull/104)).
- **[NB-387](https://linear.app/nicolai-bernsen/issue/NB-387)** — typed-AC parser tolerates
  Linear's bracket-escaping ([PR #93](https://github.com/nicolai-bernsen/backlogd/pull/93)).
- **[NB-351](https://linear.app/nicolai-bernsen/issue/NB-351)** — the developer's pre-flight
  check matrix ([PR #97](https://github.com/nicolai-bernsen/backlogd/pull/97)).

This very doc is another pass: a PO-filed problem
([NB-394](https://linear.app/nicolai-bernsen/issue/NB-394)) solved by the docs specialist.

## What is explicitly out of 1.0

To keep the "1.0" claim honest, the following are **explicitly out of scope** for 1.0. Each
names the issue or ADR that owns it:

- **The always-on, tokenless runtime** —
  [NB-379](https://linear.app/nicolai-bernsen/issue/NB-379). A continuously-running /
  headless loop is a GO-to-*explore* per ADR-004, gated on preserving the keyless principle
  ([ADR-002](standards/adrs/ADR-002-keyless-mcp.md)); it is not a 1.0 deliverable.
- **The standards ↔ execution-graph join (graph-DB v2)** —
  [NB-320](https://linear.app/nicolai-bernsen/issue/NB-320), the inspection pillar's named
  v2 in ADR-004. 1.0 ships the graph and the independent verdict; joining standards to
  graph data is later.
- **Full Agent-Interaction-Protocol identity** —
  [NB-390](https://linear.app/nicolai-bernsen/issue/NB-390) /
  [NB-391](https://linear.app/nicolai-bernsen/issue/NB-391). Richer agent presence /
  delegate work is **Tier-1-only** per [ADR-001](standards/adrs/ADR-001-visible-agent-identity-in-linear.md);
  1.0 ships the visible comment-badge identity, not the full protocol.

> **Not on this list: the retrospective.** The adaptation loop
> ([NB-381](https://linear.app/nicolai-bernsen/issue/NB-381)) is **in** scope for 1.0 — it
> is a 1.0 gate, not a deferral (see [the minimal bar](#adaptation-is-part-of-the-minimal-bar)).

## Preconditions and honest status

The loop is theatre without all of these. Each precondition is stated with its current
Linear state as of 2026-05-31 — **all of them now hold; both former gates shipped in
v0.17.0**:

- **Agents can write to Linear** — [NB-368](https://linear.app/nicolai-bernsen/issue/NB-368):
  **Done** ([PR #82](https://github.com/nicolai-bernsen/backlogd/pull/82)). The reviewer,
  tester, and refiner can actually post their verdict / evidence / spec; without this the
  whole loop is silent.
- **The standards spine** — the corpus the reviewer enforces:
  - [NB-377](https://linear.app/nicolai-bernsen/issue/NB-377) — ADR template + ADR-002:
    **Done** ([PR #92](https://github.com/nicolai-bernsen/backlogd/pull/92)).
  - [NB-380](https://linear.app/nicolai-bernsen/issue/NB-380) — agent-readable, index-first
    standards index: **Done** ([PR #94](https://github.com/nicolai-bernsen/backlogd/pull/94)).
  - [NB-378](https://linear.app/nicolai-bernsen/issue/NB-378) — the reviewer enforces the
    corpus and **blocks on missing standards**: **shipped in v0.17.0**.
- **The adaptation loop** — [NB-381](https://linear.app/nicolai-bernsen/issue/NB-381):
  the retrospective that reads the graph and files improvements — `/backlogd:retro` +
  `skills/retro/`: **shipped in v0.17.0**, and **dogfooded** — a real retro run read the
  execution graph and filed [NB-413](https://linear.app/nicolai-bernsen/issue/NB-413), a
  genuine improvement, so the pillar is fully closed (not merely shipped).

### The two gates before 1.0 — both shipped

The two gates that had to ship before 1.0 could be declared **both landed in v0.17.0**:

1. **[NB-378](https://linear.app/nicolai-bernsen/issue/NB-378)** — the reviewer enforces the
   standards corpus and blocks on a missing load-bearing standard (**shipped**).
2. **[NB-381](https://linear.app/nicolai-bernsen/issue/NB-381)** — the retrospective /
   adaptation loop that closes the empirical loop (**shipped and dogfooded** — a real retro
   run filed [NB-413](https://linear.app/nicolai-bernsen/issue/NB-413)).

With both landed, the **1.0 substance has shipped**. What remains before the milestone is
*declared* is public-launch readiness — the demo recording
([NB-396](https://linear.app/nicolai-bernsen/issue/NB-396)), the rewritten README
([NB-395](https://linear.app/nicolai-bernsen/issue/NB-395)), and the announcement — plus
the 1.0.0 version bump. This doc states the status honestly — substance shipped,
launch-readiness remaining — the same discipline ADR-004 demands of every "Scrum" claim
backlogd makes.

## Demo run-of-show

A short, recordable run-of-show. These beats are the script
[NB-396](https://linear.app/nicolai-bernsen/issue/NB-396) records against — keep them
identical so the recording does not re-derive them:

1. **File a problem** — the PO files a Linear issue with the `problem` label.
2. **The team picks it up** — `/backlogd:solve` moves it Backlog → In Progress and
   dispatches a specialist; role-prefixed comments and the delegate field show *which*
   agent is acting (the transparency story, visible on the Linear side, not just the
   terminal).
3. **The reviewer blocks on a missing standard** — the verdict is a block, not an accept,
   naming the missing load-bearing standard. This is the beat to feature: it is what shows
   backlogd is more than a single-agent runner.
4. **The PO defines it** — the block surfaces as a Linear-native sub-issue ("Define standard
   for X") with the parent `blocked-by` it; the PO answers the standards question.
5. **The team resolves it** — the scrum-master refines and solves the sub-issue (writing the
   ADR); the parent unblocks.
6. **PR merged** — the original problem continues to a fully-green verdict and squash-merges
   to Done.

The strongest framing is the dogfood angle: the demo is backlogd solving a backlogd problem.

## Alignment with ADR-004

This Definition of 1.0 is consistent with backlogd's identity
([ADR-004](standards/adrs/ADR-004-backlogd-identity.md)):

- **Empirical Scrum, all three pillars real** — the loop is gated on transparency,
  inspection, *and* adaptation actually working, not on ceremony.
- **Problem-type-agnostic** — the loop is identical for code and non-code problems; only
  the specialist changes. This doc itself is a non-code (docs) problem closing through the
  same loop.
- **Value = specialists × standards** — 1.0 is exactly the smallest instance where a
  specialist's craft and the standards corpus (the Definition of Done) together make the
  empty Scrum real, with the missing-standard block as the hinge.
- **Category claim, not a feature race** — 1.0 is "the loop works as a team," not "it does N
  task types." backlogd does not rebuild Cyrus runtime plumbing or duplicate Linear Diffs;
  see ADR-004's non-goals.

For the full Scrum mapping see [`scrum/mapping.md`](scrum/mapping.md); for the identity
decision and its three-pillar honesty note, see
[ADR-004](standards/adrs/ADR-004-backlogd-identity.md).
