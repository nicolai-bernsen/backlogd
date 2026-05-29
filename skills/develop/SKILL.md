---
name: develop
description: The method a backlogd developer follows to turn one shaped issue into a solution — consult /docs (the living spec), treat the issue's ## Acceptance Criteria as the binding static target, ship a thin vertical slice with tests where they earn their keep, and verify against the AC before reporting solved. Use when solving a problem dispatched by /backlogd:solve.
---

# Developing a backlogd problem

You are solving **one shaped issue**. This is the recommended method — it sharpens *how* you
work without changing the contract. The contract is the **outcome**, and the issue's
acceptance criteria define it: pick the smallest sensible solution, and reach for more
process only when it earns its keep.

## Two specs, two roles

- **Static spec — the issue.** The issue you were handed *is* the specification: its
  description states the intent, and its **`## Acceptance Criteria`** section is the binding
  target for "done." It does not move while you work.
- **Living spec — `/docs`.** The repository's `/docs` directory is the source of truth for
  how the system works — architecture and conventions. It tells you how to fit in.

(See `docs/living-spec-contract.md` for the full contract that governs this split.)

## The method

1. **Understand the issue.** Read the description and every `## Acceptance Criteria` item —
   they are your definition of done. Note any item you're unsure how to verify.
2. **Consult `/docs` before changing code.** Read the parts of the repository's `/docs`
   relevant to what you're touching; follow its architecture and conventions, and don't
   contradict it without cause. **If the repository has no `/docs`,** work from the issue
   alone (description + acceptance criteria) — do **not** create `/docs` unprompted; just
   note its absence in your progress comment.
3. **Take a thin vertical slice.** Make the smallest change that satisfies the criteria end
   to end. Add tests where they earn their keep — where they protect an acceptance criterion
   or catch a real risk, not for their own sake.
4. **Verify against the acceptance criteria.** Before you report `solved`, check **every**
   `## Acceptance Criteria` item against what you built, and run whatever proves it (tests,
   the build, a manual check). If an item isn't met, it isn't done. **Typed AC** (`[test]`
   / `[manual]` / `[review]` prefix on each bullet — see `skills/ac/`) tells you *how* the
   reviewer will judge each item: a `[test]` item names a backticked command the reviewer
   will run, so make sure that command actually exits 0 against your change. Untagged
   bullets default to `[review]`.
5. **Leave the living spec true.** If your change alters how the system behaves in a way the
   `/docs` should reflect, note it in your progress comment so the living spec can be brought
   up to date (you record via comments only — see Boundaries).

## Recording progress

Narrate the method as the **checklist inside your single `**[backlogd developer]**` progress
comment** on your issue — post once, capture its id, and edit it in place (see the `linear`
skill for the exact calls). One comment, kept current:

> understood → consulted `/docs` → implemented → verified AC

If you get stuck, say so in that comment and report `blocked`.

## Boundaries

You own the *how* of one issue and **comments on that one issue** — nothing else. You do
**not** transition workflow state, create or restructure issues, set relations, mark
duplicates, or open pull requests / move work to review: the scrum-master (`/backlogd:scope`
and `/backlogd:solve`) owns all structure and state. **Shaping** the problem — writing the
acceptance criteria, decomposing into units — is `scope`'s job, not yours; you implement an
already-shaped issue. Stay inside your own issue, satisfy its acceptance criteria, and report
your outcome.
