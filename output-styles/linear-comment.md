---
name: Linear comment
description: Constrains agent-authored Markdown so it renders cleanly on Linear (language-tagged fences, no tables, no em-dashes, no status emoji, shallow nesting). The canonical rule-set for every backlogd agent-authored Linear comment, the developer, reviewer, tester, and scrum-master surfaces alike.
---

# Linear comment output style

You are writing Markdown that a human (the product owner) reads **inside Linear**, not in
a terminal or on GitHub. Linear's Markdown renderer is good but not complete: a few
constructs that render fine elsewhere look broken, noisy, or untrustworthy in Linear. Your
comments must stay readable there.

Apply the rules below to **every comment you post to Linear**. They are formatting
constraints only: they do not change *what* you say, only *how* it is marked up.

This style is the canonical rule-set for **all** backlogd agent-authored Linear comments,
not only the developer's. The `**[backlogd developer]**` work log, the `**[backlogd
reviewer]**` verdict draft, the `**[backlogd review]**` rollup the scrum-master posts, the
`**[backlogd tester]**` evidence comment, and the `**[backlogd]**` solution brief all follow
it. A per-AC or per-DoD verdict shows each line's state with a `- [x]` (met) / `- [ ]`
(unmet) checkbox plus a leading bold state label (`MET` / `UNMET` / `NEEDS-PO` /
`AWAITING-PO` / `NO-STANDARD`), keeping the kind tag (`[test]` / `[manual]` / `[review]`)
and the cited evidence, never a status emoji.

## Hard rules

These are not stylistic preferences; breaking one produces visibly wrong output in Linear.

1. **Language-tag every fenced code block.** Never open a bare ` ``` `. Linear needs an
   explicit language to highlight and to render the block reliably. Use a real language
   token (`bash`, `python`, `json`, `yaml`, `diff`, `text`). When the content is not code
   (a status line, a plan, a quoted log), tag it `text`.
2. **No em-dashes.** The em-dash character is an LLM tell and reads as visual noise in a
   short Linear comment. Use a comma, a colon, parentheses, or two sentences instead. This
   applies to the em-dash and the en-dash alike; a plain hyphen between words is fine.
3. **No markdown tables.** Pipe tables render poorly in a Linear comment (cramped columns,
   broken separators), so do not use one at all. Present tabular data as a **bold-label
   list** instead, one item per row, with the label in bold and the value after a colon
   (`- **Suite:** 424 OK`). For two or three related facts, a short sentence of prose is
   even better. This is a hard rule: no ` | ` header-plus-separator table anywhere in the
   comment.
4. **Nest lists no deeper than two levels.** A top-level item and one level of sub-items is
   the limit. Linear flattens or mis-indents deeper nesting. If you need a third level,
   restructure: split into separate lists, promote to a sub-heading, or inline the detail.
5. **No decorative, sectioning, or status emoji.** Do not use emoji to section content,
   as bullets, or as status markers. In particular, **no status or checkmark emoji** (the
   green-check, the cross, the question mark, the memo, and the like): they read as noise
   in a Linear comment and certain emoji sequences break Linear's section parsing. To show
   state, use a `- [x]` / `- [ ]` checkbox list or a plain bold label (`**Result:** done`),
   never an emoji. The visible `**[backlogd developer]**` badge stays as literal bold text,
   not an emoji.

## Soft preferences

These keep the comment scannable. Follow them unless a rule above forces otherwise.

- **Lead with the answer.** The first content line states the outcome or the current
  status, then the detail follows.
- **Short lines, short paragraphs.** A Linear comment column is narrow. Prefer two short
  sentences to one long one.
- **Backtick literal tokens.** File paths, identifiers, commands, and flags go in inline
  code (`scripts/test_x.py`, `--no-ship`) so they do not get auto-linkified or reflowed.
- **Use a checklist for steps.** A `- [ ]` / `- [x]` task list is the clearest progress
  shape and renders natively in Linear.
- **One fenced block per idea.** Do not stack several fences back to back; separate them
  with a sentence of context.

## Quick reference

This list is itself in the target shape: bold labels, no table.

- **Code fence:** tag every fence (` ```bash ` / ` ```text `); never a bare ` ``` `.
- **Dash:** use a comma, colon, or parentheses; never an em-dash or en-dash.
- **Tabular data:** use a bold-label list (`- **Label:** value`) or short prose; never a
  markdown / pipe table.
- **List depth:** two levels max; never three or more.
- **State / status:** use a `- [x]` checkbox or a bold label; never a status or checkmark
  emoji, and no decorative or sectioning emoji.
