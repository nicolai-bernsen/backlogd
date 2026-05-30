---
name: Linear comment
description: Constrains agent-authored Markdown so it renders cleanly on Linear (language-tagged fences, simple tables, no em-dashes, shallow nesting). Used by backlogd's developer subagent for its progress comments.
---

# Linear comment output style

You are writing Markdown that a human (the product owner) reads **inside Linear**, not in
a terminal or on GitHub. Linear's Markdown renderer is good but not complete: a few
constructs that render fine elsewhere look broken, noisy, or untrustworthy in Linear. Your
comments must stay readable there.

Apply the rules below to **every comment you post to Linear**. They are formatting
constraints only: they do not change *what* you say, only *how* it is marked up.

## Hard rules

These are not stylistic preferences; breaking one produces visibly wrong output in Linear.

1. **Language-tag every fenced code block.** Never open a bare ` ``` `. Linear needs an
   explicit language to highlight and to render the block reliably. Use a real language
   token (`bash`, `python`, `json`, `yaml`, `diff`, `text`). When the content is not code
   (a status line, a plan, a quoted log), tag it `text`.
2. **No em-dashes.** The em-dash character is an LLM tell and reads as visual noise in a
   short Linear comment. Use a comma, a colon, parentheses, or two sentences instead. This
   applies to the em-dash and the en-dash alike; a plain hyphen between words is fine.
3. **Simple tables only, or no table.** Linear supports only basic pipe tables: a header
   row, a separator row, and body rows. No merged cells, no nested block content inside a
   cell, no alignment tricks, no tables wider than about four columns. If the data does not
   fit a plain grid, use a short bullet list instead. Prefer a concise table over a long
   bullet list when the data *is* tabular.
4. **Nest lists no deeper than two levels.** A top-level item and one level of sub-items is
   the limit. Linear flattens or mis-indents deeper nesting. If you need a third level,
   restructure: split into separate lists, promote to a sub-heading, or inline the detail.
5. **No exotic or decorative emoji.** Plain status markers are fine in moderation (a
   checkbox list, a single leading marker). Do not use emoji to section content or as
   bullets; certain emoji sequences break Linear's section parsing. The visible
   `**[backlogd developer]**` badge stays as literal bold text, not an emoji.

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

| Construct | Do | Avoid |
| --- | --- | --- |
| Code fence | tagged ` ```bash ` / ` ```text ` | bare ` ``` ` |
| Dash | comma, colon, parentheses | em-dash, en-dash |
| Tabular data | plain pipe table (header, separator, rows) | merged or nested cells |
| List depth | two levels max | three or more levels |
| Markers | a checklist, one leading marker | decorative or sectioning emoji |
