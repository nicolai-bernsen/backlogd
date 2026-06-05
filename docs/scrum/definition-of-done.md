# Definition of Done

backlogd's repo-level **Definition of Done** — the Scrum *commitment* attached to the
Increment (the merged PR). Every increment must meet every rule below before it can move
to *Done* and merge into `dev`. This is a **hard-rules floor**, not a methodology essay:
each line is observable by an agent or reviewer without taste calls. If a line takes
judgement, it does not belong here.

**DoD vs AC — two distinct commitments, both enforced.** The Definition of Done is
**standing**: the same bar *every* increment clears, regardless of which problem it
solves. A problem's `## Acceptance Criteria` is **per-problem**: the contract for *that*
one increment. The reviewer holds each diff against **both** — every AC line *and* every
DoD line — and a red DoD line blocks the merge exactly like a red AC line. The AC says
*what this problem must deliver*; the DoD says *what every increment must satisfy
anyway*. Neither subsumes the other.

See [`mapping.md`](mapping.md) → *Artifacts › Increment* for where the DoD sits in
backlogd's Scrum interpretation, and [`scrum-guide.md`](scrum-guide.md) →
*Increment › Commitment: Definition of Done* for the canonical Scrum text.

## Code & change

- [ ] Every line in the issue's `## Acceptance Criteria` is met by the diff.
- [ ] Every acceptance criterion that names a behaviour is covered by an automated test
      that fails without the change and passes with it.
- [ ] CI is green on the head commit of the PR.
- [ ] No `TODO`, `FIXME`, or `XXX` comments added by the diff are left unresolved or
      untracked — each either references a follow-up Linear issue or is removed.
- [ ] No secrets, tokens, API keys, or `.env*` files are added by the diff
      (`git diff` against the base branch shows none).

## Docs & spec

- [ ] Every page under `/docs` that describes behaviour the diff changed has been
      updated in the same PR (per the [living-spec contract](../living-spec-contract.md)).
- [ ] `docs/conventions.md` has been updated when the diff introduces or changes a
      convention (branching, Linear usage, docs rule, file layout, naming).
- [ ] `README.md` has been updated when the diff changes a user-facing surface — the
      install steps, the setup steps, the listed commands, or the walking-skeleton flow.

## Linear & git hygiene

- [ ] The PR's branch has **exactly one commit per unit issue** solved on it
      (`git log --oneline base..head` matches the unit count).
- [ ] Each commit message follows Conventional Commits and includes the unit's
      identifier — its subject matches `^(feat|fix|docs|chore|refactor|test|ci|build|perf|style)\(#\d+\): ` <!-- markdownlint-disable-line MD038 -->
      (per [CONTRIBUTING.md](../../CONTRIBUTING.md) → *Commits*).
- [ ] The PR title and body carry the problem's identifier (`#NB-N` or `NB-N`) so
      Linear auto-links the PR to the problem.
- [ ] Every unit issue closed by this PR has the developer's
      `**[backlogd developer]**` work-log comment posted on it.
- [ ] The problem issue has the scrum-master's `**[backlogd]**` solution brief comment
      posted on it.

## Out of scope (deliberately)

These are **not** in the DoD — listed here so they are not added by accident:

- **TDD / spec-first as a mandate.** The [README](../../README.md) states the
  methodology underneath (spec-driven development, small vertical slices, tests first)
  is *encouraged but not mandated* — the contract is the problem and the outcome, not
  the process. The DoD demands tests cover testable AC (above); it does not demand
  tests come first.
- **Human review of every PR.** backlogd's loop is autonomous by design — the PO files
  problems and accepts results; the scrum-master commands open and merge PRs against
  green CI. Requiring a human reviewer on every PR would break the loop. The **independent
  verdict reviewer** verifies the *increment* against this floor; on the happy path
  `/backlogd:solve` auto-chains that verdict and merges a fully-green increment to *Done*
  with **no human gate** (ship-on-green). The PO does not trigger the review or click merge
  on green — they are interrupted only on a sent-back verdict, a NEEDS-PO/`[manual]` judgement
  call, or a blocker. `/backlogd:review` remains available as a manual re-entry point.
