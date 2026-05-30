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

Pick the **strongest** check the AC item can support. Reaching higher up the ladder is
better — `[test]` is the strongest, `[manual]` is a question to the PO, `[review]` is
Claude judgement. But **don't fabricate**: if no runnable check exists, leave the item
untagged (defaults to `[review]`) rather than inventing a test command that doesn't
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
the item as `❔ needs PO judgement: no runnable check found` rather than guessing.

The reviewer subagent extracts the **first** `` `…` `` span as the command, runs it
from the worktree, and judges:

- exit code `0` → `✅ met` (cite the command + the exit code or the last line).
- non-zero → `❌ unmet` (cite the command + the last few lines of stderr).

Example:

```markdown
- [ ] [test] AC parser handles untagged items — `python -m pytest tests/test_ac.py::test_untagged_defaults_to_review` exits 0.
```

### `[manual]` — PO confirms

Use when the AC item is **observable but only by a human running it**:

- "the UI renders without console errors",
- "the README skim reads naturally to a new contributor",
- "running `/backlogd:scope` on a fresh problem produces a sensible decomposition".

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

The reviewer's verdict glyph on a `[manual]` item is `📝 awaiting PO confirmation`
until the batched check is acknowledged.

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

The reviewer reads the artifacts and judges `✅ met` / `❌ unmet` / `❔ needs PO
judgement` (the last is for items that turn out to need a real product decision the
reviewer can't make).

## How `/backlogd:scope` writes AC

When `/backlogd:scope` shapes a problem, it dispatches the **refiner subagent** to
draft the description; the dispatch envelope tells the refiner to load this skill and
to write AC bullets with **explicit kinds where possible**:

1. **Default to `[review]`** when unsure — better than inventing a `[test]` that has
   no real runnable command behind it. Untagged (no prefix) is fine and equivalent.
2. **Use `[test]`** only when the bullet describes something with an obvious automated
   check (a test path, a lint command, an exact string that must appear in a file, a
   shell snippet that exits non-zero on failure). Spell out the command in backticks
   inside the bullet so the reviewer can extract it.
3. **Use `[manual]`** for observable-but-human checks (UI feel, prose quality, an
   end-to-end walk only a human can sanity-check).
4. **Encourage the PO**, in the scope report, to refine kinds the reviewer flagged
   `❔ no runnable check found`.

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
     `❔ needs PO judgement: no runnable check found`. Otherwise run the command from
     the worktree root with Bash; exit `0` → `✅ met`, non-zero → `❌ unmet`. Cite the
     command and the result.
   - **`[manual]`** → add the bullet to the "Manual checks for the PO" batch in the
     drafted verdict body and mark it `📝 awaiting PO confirmation`. The reviewer
     does **not** silently pass it.
   - **`[review]`** → judge from the artifacts (the original `[review]` behaviour).
     `✅` / `❌` / `❔`.
3. **Verdict rollup** (verdict mode, returned to the scrum-master):
   - **accepted** requires every item `✅ met` and any `[manual]` items confirmed by
     the PO (no `📝` left dangling), and CI green.
   - **sent back** if any item is `❌` (or CI red).
   - **needs you** if any item is `❔` or there are unconfirmed `📝`s and no `❌`.

In `pre-commit-gate` mode (the same reviewer subagent, dispatched inside
`/backlogd:solve` before commit), the rollup is binary — `📝 awaiting PO
confirmation` for `[manual]` items counts as `needs-changes` because the gate
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
  ✅ [test] `bash hooks/install-git-hooks.sh …` — ran, exit 0, output matched.
  ❌ [test] `python -m pytest tests/scope/` — ran, exit 1 (3 failures).
  📝 [manual] /backlogd:scope walk — awaiting PO confirmation (see batch below).
  ✅ [review] New code path is small — diff is +120/-30 across 4 files; one sitting.
  ✅ [review] Untagged AC defaults to `[review]` — verified parser test exists.

Manual checks for the PO
  - Run `/backlogd:scope NB-XXX` on a freshly-filed problem; does the decomposition look reasonable?
```
