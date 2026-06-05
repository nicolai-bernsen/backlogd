---
name: ac
description: backlogd's contract for typed Acceptance Criteria — every `## Acceptance Criteria` item declares *how it is verifiable* via an optional `[test]` / `[manual]` / `[review]` prefix tag; untagged items default to `[review]` (backwards compatible). Load when shaping AC (`/backlogd:scope`) or judging a verdict (`/backlogd:review`).
---

# Typed Acceptance Criteria

backlogd problems are decided by their `## Acceptance Criteria` list. Without structure
that list is fuzzy markdown — one Claude judging another against vague bullets, and a
vague bullet ("works correctly") always passes. **Typed AC** gives each item a contract:
the *kind* of check that verifies it, declared at the start of the bullet, so reviewers
can branch per-kind instead of waving a single "judgement" wand over everything.

This skill is the source of truth for the AC grammar and how each kind is verified.
**Load it from any command or subagent that writes or reads AC** — today: the
`/backlogd:scope` command (which dispatches the **refiner** subagent to draft AC), and
the **reviewer** subagent (`agents/reviewer.md`, dispatched by `/backlogd:review`)
which branches per-kind on the verdict walk.

## The grammar

Each `## Acceptance Criteria` item is a GitHub-flavoured markdown task list entry with
an **optional kind prefix** in square brackets, immediately after the checkbox, with a
single space on each side:

```markdown
## Acceptance Criteria

- [ ] [test] Unit tests pass — run `pytest tests/parse_ac.py::test_extract_kind`.
- [ ] [manual] PO confirms the wording in the README skim reads naturally.
- [ ] [review] No new public API surface introduced.
- [ ] Existing un-tagged AC continues to work (defaults to `[review]`).
```

Rules:

- **Three kinds, lowercase, exact:** `[test]` · `[manual]` · `[review]`. No other tags.
- **Position:** right after `[ ]` (or `[x]`), with one space before the tag and one
  space after the closing bracket. Anywhere else, the brackets are body text.
- **At most one tag per item.** A second `[…]` in the body is body text.
- **Untagged → `[review]`.** Backwards compatible with every existing problem.
- **Parsing rule (normalize, then match):** kind extraction is *normalize-then-match*,
  because Linear escapes a bare leading `[` when it stores a description — an authored
  `[test] …` comes back as `\[test\] …`, and the backtick workaround `` `[test]` … ``
  round-trips verbatim. So **before** matching, normalize the *leading tag region* of
  the item text: unwrap a leading inline code span around the tag (`` `[test]` `` →
  `[test]`) and markdown-unescape a leading bracket escape (`\[`→`[`, `\]`→`]`). Then
  apply the regex `^\[(test|manual|review)\] ` (case-sensitive, single trailing space): <!-- markdownlint-disable-line MD038 -->
  on a match, strip that prefix and the rest is the *body*; otherwise the whole
  **original** text is the body with kind=`review`. Normalization is surgical — only the
  leading tag region is rewritten, so backslashes or code spans elsewhere in the body
  survive untouched, and a non-kind `[something]` (or `\[something\]`) keeps its
  brackets and stays `review`. **`scripts/ac_parse.py` is the reference implementation**
  (`extract_kind` → `(kind, body)`); the reviewer (an LLM, there is no runtime parser)
  mirrors it exactly, the way `/backlogd:status` mirrors `scripts/forecast.py`.

## When to use each kind

Pick the **strongest** check the AC item can support. `[test]` is the strongest — an
exit-coded command. `[review]` is Claude judgement against the artifacts and the
standards, and is the **default** for everything that is not a runnable check. `[manual]`
is the **rare exception** — reserved for a fact only a human can observe in the world (see
its section below); it is **not** a peer default and **never** the home for a
correctness/soundness call. But **don't fabricate**: if no runnable check exists, leave the
item untagged (defaults to `[review]`) rather than inventing a test command that doesn't
exist.

### `[test]` — automated, exit-coded

Use when the AC item names a check that can return **exit 0 / non-zero**:

- a test command (`` `pytest tests/foo.py::test_bar` ``, `` `npm test -- --grep "foo"` ``),
- a build/lint command (`` `python -m compileall scripts/` ``, `` `ruff check .` ``),
- a script that asserts (`` `bash scripts/verify-something.sh` ``),
- a one-liner that greps for an exact required string in a file
  (`` `grep -q "expected phrase" path/to/file` ``).

**Contract:** the AC item body **must contain** at least one backticked runnable thing —
a command line in backticks (the reviewer will execute it with Bash from the worktree
root). If the bullet says `[test]` but has no backticked command, the reviewer reports
the item as **NEEDS-PO** `no runnable check found` rather than guessing.

The reviewer subagent extracts the **first** `` `…` `` span as the command, runs it
from the worktree, and judges:

- exit code `0` → **MET** (cite the command + the exit code or the last line).
- non-zero → **UNMET** (cite the command + the last few lines of stderr).

Example:

```markdown
- [ ] [test] AC parser handles untagged items — `python -m pytest tests/test_ac.py::test_untagged_defaults_to_review` exits 0.
```

### `[manual]` — a fact only a human can observe in the world

`[manual]` is the **rare, earned exception**, not a peer default. Reserve it strictly for
**facts a fresh-context agent genuinely cannot observe in the world** — something whose
truth lives outside the repo, the diff, the issue, and the comments, where no command and
no careful read can reach:

- "does this `templateData` actually render in the Linear UI",
- "is this visually on-brand / does the layout look right",
- "did the external service actually receive the webhook".

Soundness, correctness, and consistency-with-our-standards judgements all route to
`[review]` — they are explicitly **excluded** from the `[manual]` kind. "Is this the right
call", "does this match the ADRs", "did the refiner shape this well", "the PO signs off that
the content reads well" — every one of these is a judgement an independent reviewer makes
against the artifacts and the documented standards, so each routes to `[review]`, not to a
human gate. An item phrased as "the PO confirms the content is right" is mis-typed: retype it
`[review]` and let the independent reviewer judge it. The test is narrow: *can no agent
observe this, even with a fresh context, the diff, and Bash?* If a reviewer could read or run
something to settle it, it is a `[review]` item.

**Two rules the refiner and the scope dispatch enforce:**

1. **Default to `[review]`.** When you are unsure which kind fits, it is `[review]`
   (or untagged, which is the same) — never `[manual]`.
2. **Justify every `[manual]`.** Any `[manual]` item must carry a **one-line justification of
   why no fresh-context agent could observe it** — inline in the bullet (e.g. *"— [manual]
   because only a human eye can confirm the brand palette renders correctly in Linear"*). A
   `[manual]` without that justification is treated as mis-typed and should be retyped
   `[review]`.

#### The one named exception: a guide/runbook **first-live-run** AC

There is exactly **one** standing exception where a `[manual]` is the default rather than the
rare case: a **guide/runbook-class deliverable** — a doc whose entire value is a human
**following it end-to-end** (a `docs/guides/*-setup.md`, an install/onboarding walk-through, a
demo runbook, any step-by-step a person is meant to execute). Prose review reads the steps; it
cannot *run* them, and the defects that matter (a copied URL the terminal mangles, a redirect
that errors yet succeeds, a step misordered against what the live tool actually does) only
surface when a human walks it. So a guide/runbook-class problem **carries a `[manual]`
first-live-run AC by default**:

```markdown
- [ ] [manual] One real end-to-end execution of this guide by a human; defects fed back into
  the guide — [manual] because no fresh-context agent can perform the human walk-through.
```

The one-line justification is the standard one (no fresh-context agent can do the human
walk-through), so it satisfies rule 2 above. This is the **execution** gate; it is a sibling of
the live-evidence rule in
[ADR-008](../../docs/standards/adrs/ADR-008-live-surface-verification.md), which governs the
*evidence behind an external-surface claim* — keep the two crisp: ADR-008 asks *is the claim
proven against the live surface*; this AC asks *has a human run the deliverable end to end*. The
guide's recorded run (e.g. the "Verified — first live run" blockquote that
[`docs/guides/agent-identity-setup.md`](../../docs/guides/agent-identity-setup.md) carries) is
where the run and any defects it fed back are written down.

This exception is **narrow**: it fires only for the guide/runbook class. It does **not** widen
`[manual]` for anything else, and it does **not** touch the rule above that a
soundness/correctness/consistency call is `[review]` — a guide can still carry `[review]` ACs
for whether its prose is right; the first-live-run AC is only the standing *execution* check.

The reviewer subagent **does not try to verify** `[manual]` items itself. Instead,
it batches every `[manual]` item on the problem into a single follow-up section in
its drafted verdict body — one bullet per item — titled "Manual checks for the PO".
The scrum-master (or the PO themselves) confirms each one before the verdict closes.

**Split of responsibility:**

- The **reviewer subagent** drafts the batched question — exactly the wording of each
  `[manual]` bullet, in a single list, in the verdict body it returns to the
  scrum-master.
- The **scrum-master** (`/backlogd:review`) lifts the drafted body verbatim into its
  `**[backlogd review]**` comment and surfaces the batched question to the PO,
  waiting for the answer before closing the verdict.

The reviewer's verdict state on a `[manual]` item is **AWAITING-PO** until the batched
check is acknowledged.

In `pre-commit-gate` mode (the same reviewer subagent, dispatched inside
`/backlogd:solve`), the gate is binary and cannot wait on the PO — `[manual]` items
roll up as `needs-changes` until they are either retyped to something the gate can
check or the developer's note explicitly acknowledges the gate-failure-by-design.

### `[review]` — Claude judgement

Use when the AC item is genuinely a **judgement call from the artifacts** — the kind of
thing a careful reader can decide by reading the diff, the issue, and the comments, but
no machine can prove:

- "the change is minimally invasive",
- "the prose is clearer than before",
- "the new API surface is small",
- "existing un-tagged AC continues to work" (the reviewer reads the parser to confirm).

This is the **default** (untagged items become `[review]`). It's also the **current**
behaviour of `/backlogd:review` for every AC item, so no existing problem regresses.

The reviewer reads the artifacts and judges **MET** / **UNMET** / **NEEDS-PO**
(the last is for items that turn out to need a real product decision the
reviewer can't make).

## Standards are persistent, cross-issue AC

A per-issue AC bullet binds **one** problem. An **Accepted standard** (an ADR under
`docs/standards/adrs/`) binds **every** problem in its scope — it is a *persistent,
cross-issue acceptance criterion* the reviewer enforces on **every** verdict, not just the
issue that authored it. Same machinery, wider scope: each Accepted ADR carries a crisp
checkable **`assertion`** — authored in the **same checkable spirit as a `[test]`/`[review]`
bullet** (a single line the reviewer judges `met`/`unmet`) — so a standard is just an AC
that never expires and isn't re-typed per issue.

This is why the kinds and the corpus coordinate:

- A `[review]` bullet is judged against the artifacts **and** the Accepted standards — an
  Accepted ADR's `assertion` is a standing `[review]`-grade check folded into every walk.
- Author each ADR `assertion` as **one crisp checkable line** (mirroring a `[test]`/`[review]`
  bullet) so the reviewer can call it `met`/`unmet` straight from the diff — vague prose in
  an `assertion` fails for the same reason a vague AC bullet does.
- Only the **current `Accepted`** set is enforced (`Proposed`/`Superseded`/`Deprecated` are
  ignored) — ADRs stay agile, reopenable, supersedable.

The reviewer's **index-first load order** (read `docs/standards/index.json`, filter by
`applies-to`, judge each applicable `assertion`, cite which it verified) lives in
`agents/reviewer.md` and `skills/reviewer/SKILL.md` — not duplicated here.

## The `## Goal` — one shared objective above the AC

A shaped problem's description carries a single-sentence **`## Goal`** section positioned
**immediately above `## Acceptance Criteria`**. Where each AC bullet is a *local* check, the
Goal is the **coherent objective the whole unit serves** — the one "why" the developer,
tester, and reviewer all read so they pull in the same direction instead of each serving a
local artifact (AC / tests / verdict). It recovers the Sprint Goal at the problem level
(the per-bullet AC is too local; the Initiative/Product Goal is too far up).

- **Home: the description, not a custom field.** The Goal lives as a `## Goal` section in
  the issue description (the description-canonical / no-separate-AC-field precedent) — not a
  Linear custom field. This is the working default; the PO may later choose a filterable
  custom field instead if they want to query Goals.
- **Author: the refiner, from the problem.** `/backlogd:scope`'s refiner writes the Goal as
  one crisp sentence stating the outcome the increment must achieve, captured from the
  problem the PO filed. The **scrum-master never substitutes its own product intent**; if the
  problem's "why" is genuinely unclear, the refiner surfaces it as an ambiguity rather than
  inventing an objective.
- **Travels in the dispatch envelope.** Because `/backlogd:solve` inlines the unit's full
  description verbatim (`skills/solve/dispatch.md`), the `## Goal` reaches every dispatched
  role alongside the AC — same "why", not just the AC.
- **The reviewer reasons against it.** The verdict judges whether the increment *serves the
  Goal*, not only passes the local AC; a pass-the-AC-but-miss-the-Goal increment is a
  **NEEDS-PO** Goal/AC mismatch, never a silent accept (`agents/reviewer.md` → *Reason
  against the Goal*). A problem with **no `## Goal`** (older / not re-shaped) falls back to
  AC + DoD judgement — absence is not an UNMET.
- **Distinct from the Project-form `## Goals` list.** A promoted Project's Spec document
  (`templates/spec.md`) carries both: a single-sentence `## Goal` (this shared objective) and
  the granular `## Goals` bullet list (the outcomes the PO is buying). The single `## Goal`
  is the one the envelope inlines and the reviewer reasons against.

## How `/backlogd:scope` writes AC

When `/backlogd:scope` shapes a problem, it dispatches the **refiner subagent** to
draft the description; the dispatch envelope tells the refiner to load this skill and
to write AC bullets with **explicit kinds where possible**:

1. **Default to `[review]`** whenever unsure — it is the home for every judgement call,
   including "is this decision sound / correct / consistent with the ADRs", which the
   independent reviewer decides against the artifacts and standards. Untagged (no prefix)
   is fine and equivalent. Better `[review]` than inventing a `[test]` with no real command.
2. **Use `[test]`** only when the bullet describes something with an obvious automated
   check (a test path, a lint command, an exact string that must appear in a file, a
   shell snippet that exits non-zero on failure). Spell out the command in backticks
   inside the bullet so the reviewer can extract it.
3. **Reserve `[manual]`** for the rare fact only a human can observe in the world (a UI
   render, visual on-brand-ness, an external service actually receiving something) — see
   the `[manual]` section above. It is **not** a peer default: a correctness/soundness/
   consistency judgement is `[review]`, and every `[manual]` carries a one-line
   justification of why no fresh-context agent could observe it.
4. **Encourage the PO**, in the scope report, to refine kinds the reviewer flagged
   **NEEDS-PO** `no runnable check found`.

The PO can always edit the description to retype an AC bullet — the kind is just text.

## How the reviewer subagent reads AC

When `/backlogd:review` dispatches the **reviewer subagent** (`agents/reviewer.md`)
in `verdict` mode, the reviewer walks each `- [ ]` bullet under `## Acceptance
Criteria`:

1. **Parse the kind** by the normalize-then-match rule above — normalize Linear's
   escaped (`\[test\]`) and code-span (`` `[test]` ``) storage forms, then match
   (mirror `scripts/ac_parse.py`). Untagged / non-kind token → `[review]`.
2. **Branch per-kind:**
   - **`[test]`** → extract the first backticked command from the body. If none, mark
     **NEEDS-PO** `no runnable check found`. Otherwise run the command from
     the worktree root with Bash; exit `0` → **MET**, non-zero → **UNMET**. Cite the
     command and the result.
   - **`[manual]`** → add the bullet to the "Manual checks for the PO" batch in the
     drafted verdict body and mark it **AWAITING-PO**. The reviewer
     does **not** silently pass it.
   - **`[review]`** → judge from the artifacts (the original `[review]` behaviour).
     **MET** / **UNMET** / **NEEDS-PO**.
3. **Verdict rollup** (verdict mode, returned to the scrum-master):
   - **accepted** requires every item **MET** and any `[manual]` items confirmed by
     the PO (no **AWAITING-PO** left dangling), and CI green.
   - **sent back** if any item is **UNMET** (or CI red).
   - **needs you** if any item is **NEEDS-PO** or there are unconfirmed **AWAITING-PO**
     items and no **UNMET**.

In `pre-commit-gate` mode (the same reviewer subagent, dispatched inside
`/backlogd:solve` before commit), the rollup is binary — an **AWAITING-PO**
`[manual]` item counts as `needs-changes` because the gate
cannot wait on the PO.

## Backwards compatibility — non-negotiable

Every existing problem has untagged AC. The parser treats untagged items as `[review]`
*identically* to how `/backlogd:review` already judged them — no behaviour change. The
contract is **additive**: tagging an item enables a stricter check; not tagging
preserves today's behaviour.

When in doubt, leave the bullet untagged — that is always safe.

## Examples — round trip

A *true* round trip has two states: what the author writes, and what Linear stores and
returns. They differ — Linear escapes the leading `[` — so the reviewer normalizes the
stored form back to the bare kind before matching (see the Parsing rule;
`scripts/ac_parse.py` is the reference impl).

**What the author writes** (bare tags):

```markdown
## Acceptance Criteria

- [ ] [test] `bash hooks/install-git-hooks.sh test@example.com && git config backlogd.expectedEmail` prints `test@example.com`.
- [ ] [test] No regression in existing scope flow — `python -m pytest tests/scope/` exits 0.
- [ ] [manual] The PO runs `/backlogd:scope NB-XXX` on a freshly-filed problem and the resulting decomposition looks reasonable.
- [ ] [review] The new code path is small enough to read in one sitting.
- [ ] Existing untagged criteria continue to work (defaults to `[review]`).
```

**What Linear stores and `get_issue` returns** (leading brackets escaped — this is what
the reviewer actually parses, and what `scripts/ac_parse.py` normalizes back to the bare
kind):

```markdown
## Acceptance Criteria

- [ ] \[test\] `bash hooks/install-git-hooks.sh test@example.com && git config backlogd.expectedEmail` prints `test@example.com`.
- [ ] \[test\] No regression in existing scope flow — `python -m pytest tests/scope/` exits 0.
- [ ] \[manual\] The PO runs `/backlogd:scope NB-XXX` on a freshly-filed problem and the resulting decomposition looks reasonable.
- [ ] \[review\] The new code path is small enough to read in one sitting.
- [ ] Existing untagged criteria continue to work (defaults to `[review]`).
```

Reviewer's walk on the stored form (sketch — kinds resolve correctly *because* the
escaping is normalized first):

```text
Acceptance criteria
- [x] **MET** [test] `bash hooks/install-git-hooks.sh …` — ran, exit 0, output matched.
- [ ] **UNMET** [test] `python -m pytest tests/scope/` — ran, exit 1 (3 failures).
- [ ] **AWAITING-PO** [manual] /backlogd:scope walk — awaiting PO confirmation (see batch below).
- [x] **MET** [review] New code path is small — diff is +120/-30 across 4 files; one sitting.
- [x] **MET** [review] Untagged AC defaults to `[review]` — verified parser test exists.

Manual checks for the PO
- Run `/backlogd:scope NB-XXX` on a freshly-filed problem; does the decomposition look reasonable?
```
