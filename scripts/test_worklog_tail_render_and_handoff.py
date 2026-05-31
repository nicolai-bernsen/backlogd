"""Tester widening for NB-355 AC4 — the work-log tail renders under the NB-359
Linear-comment style, and ``skills/solve/handoff.md`` is left untouched.

Added by the backlogd tester to cover AC4, which the developer's
``test_worklog_tail_schema.py`` does not touch:

    "The schema renders under the NB-359 Linear-comment style (bold-label lists,
     no tables, no status emoji); ``skills/solve/handoff.md`` untouched."

AC4 has a visual half and a mechanical half. The *visual* render ("renders
cleanly in Linear's UI") is an eyeball check no markdown grep can make — that is
review/PO-scope and is reported as such, not asserted here. The *mechanical*
halves ARE static facts and are anchored below:

- the schema region in ``agents/developer.md`` is authored as a **bold-label
  list** (``- **Decided:** ...``), carries **no markdown pipe table**, and uses
  **no status / checkmark emoji** — the three concrete NB-359 constraints the AC
  names, applied to the schema region specifically (the developer's suite only
  asserts the four ``**Label:**`` tokens exist, not that the region is
  table-free and emoji-free);
- ``skills/solve/handoff.md`` is the In-Review PR-handoff skill and stays that —
  it still declares ``name: solve-handoff`` and describes opening the PR, and it
  carries **none** of the work-log-tail schema's distinctive tokens. The original
  framing of NB-355 would have *created/edited* ``handoff.md`` (a name
  collision); this test guards that the schema did NOT leak onto it.

Why these earn their keep (non-tautology):

- the no-table / bold-label anchors discriminate against the obvious wrong
  implementation — authoring the four sections as a markdown table — exactly the
  shape NB-359 bans; the ``_TABLE_SEPARATOR`` detector is the same one
  ``test_linear_comment_style.py`` uses;
- the no-status-emoji anchor scans the schema region for the concrete emoji
  NB-359 calls out (green-check, cross, question, memo, warning) and the common
  variants; a careless ``✅ Decided`` edit would trip it;
- the handoff anchors go red the moment any work-log-tail token (``Decided`` /
  ``Rejected`` / ``Remaining`` / ``omit-when-empty``) appears in ``handoff.md``,
  which is precisely the regression AC4 forbids — and pass now because the file
  is genuinely untouched (verified: ``git diff origin/dev -- skills/solve/handoff.md``
  is empty).

These complement, not duplicate, ``test_worklog_tail_schema.py``: that file
proves the four sections + omit-when-empty rule are DEFINED (AC1/AC2/AC3); this
file proves they are RENDERED in the NB-359 shape and that ``handoff.md`` stayed
out of it (AC4).

Why stdlib only: the repo's test convention — CI runs
``python3 -m unittest discover -s scripts -p 'test_*.py'`` on a bare Python with
no ``pip install``. Files are read as UTF-8 and scanned for stable tokens.

Run from the repo root:  python scripts/test_worklog_tail_render_and_handoff.py
"""

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEVELOPER = REPO_ROOT / "agents" / "developer.md"
HANDOFF = REPO_ROOT / "skills" / "solve" / "handoff.md"

SECTIONS = ("Decided", "Rejected", "Risks", "Remaining")

# The work-log-tail's distinctive tokens — the ones that, if they appeared in
# handoff.md, would mean the schema leaked onto the PR-handoff skill. "Risks" is
# excluded as a token here: it is a common English word that can legitimately
# appear in unrelated prose, whereas Decided/Rejected/Remaining/omit-when-empty
# are the schema's signature vocabulary.
SCHEMA_SIGNATURE_TOKENS = ("decided", "rejected", "remaining", "omit-when-empty")

# A markdown pipe table = a header row of `| ... |` immediately followed by a
# separator row whose cells are runs of dashes (`| --- | --- |`). Matching the
# header+separator pair (not a lone `|`) avoids flagging inline code or prose
# that merely contains a pipe character. Same detector as test_linear_comment_style.py.
_TABLE_SEPARATOR = re.compile(r"^\s*\|(?:\s*:?-{1,}:?\s*\|)+\s*$", re.MULTILINE)

# Status / checkmark / decorative emoji NB-359 rule 5 forbids. A representative
# set (the ones the style file calls out by name plus common siblings), not an
# exhaustive Unicode sweep — enough to catch a `✅ Decided` / `⚠️ Risks` slip.
STATUS_EMOJI = (
    "✅",  # ✅ white heavy check mark
    "❌",  # ❌ cross mark
    "✔",  # ✔ heavy check mark
    "✖",  # ✖ heavy multiplication x
    "❓",  # ❓ question mark
    "❗",  # ❗ exclamation mark
    "⚠",  # ⚠ warning
    "\U0001f4dd",  # 📝 memo
    "\U0001f7e2",  # 🟢 green circle
    "\U0001f534",  # 🔴 red circle
    "\U0001f7e1",  # 🟡 yellow circle
    "☑",  # ☑ ballot box with check
)


def _read(path):
    """File text (UTF-8), or empty string if absent so the file-exists test owns
    the missing-file failure rather than every test erroring."""
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _tail_region(text):
    """The work-log tail SCHEMA region of developer.md, tightly bounded so it
    contains the schema and its worked example but NOT the rest of
    ``<Output_Format>`` (which legitimately carries the STATUS-enum documentation
    table — that table is prompt-file documentation, not the Linear-comment schema
    the AC constrains).

    Start: the "Closing tail" schema bullet (a durable token; the schema's first
    line). End: the "If you get stuck" bullet that immediately follows the schema +
    worked example — a stable anchor that brackets the schema and excludes
    everything below it. Falls back to a bounded window if either anchor moves, so
    a reword degrades gracefully rather than swallowing the whole section."""
    start = text.find("Closing tail")
    if start == -1:
        start = text.find("**Decided:**")
    if start == -1:
        return ""
    # End at the next schema-adjacent bullet ("If you get stuck"), which sits right
    # after the worked-example fence. If absent, take a 1200-char window — enough
    # for the four bullets + the omit-when-empty paragraph + the worked example,
    # but short of the STATUS table further down.
    end_marker = text.find("If you get stuck", start)
    end = end_marker if end_marker != -1 else min(len(text), start + 1200)
    return text[start:end]


class SchemaRendersInBoldLabelListTest(unittest.TestCase):
    """AC4 — the schema region is a bold-label list, not a table. Each of the four
    sections appears as a list item with a bold label (``- **Decided:**`` etc.)."""

    @classmethod
    def setUpClass(cls):
        cls.region = _tail_region(_read(DEVELOPER))

    def test_region_exists(self):
        self.assertTrue(
            self.region,
            "agents/developer.md must define a work-log tail region anchored on "
            "**Decided:** (AC4)",
        )

    def test_each_section_is_a_bold_label_list_item(self):
        """Each section is rendered as ``- **Section:**`` — a bold-label LIST item,
        the NB-359 shape (not a table cell, not a bare heading)."""
        for section in SECTIONS:
            with self.subTest(section=section):
                self.assertRegex(
                    self.region,
                    rf"(?m)^\s*[-*]\s+\*\*{section}:\*\*",
                    f"the **{section}:** section must render as a bold-label LIST "
                    f"item (`- **{section}:** ...`), per the NB-359 style (AC4)",
                )


class SchemaRegionHasNoTableTest(unittest.TestCase):
    """AC4 — the schema region carries NO markdown pipe table (NB-359 rule 3:
    tables render poorly in a Linear comment, use a bold-label list).

    Non-tautological: the obvious wrong implementation is a four-row table
    (`| Section | Meaning |`). This detector (header row + `|---|` separator) goes
    red against that shape and green against the bold-label list the developer
    authored."""

    @classmethod
    def setUpClass(cls):
        cls.region = _tail_region(_read(DEVELOPER))

    def test_no_pipe_table_in_schema_region(self):
        lines = self.region.splitlines()
        offending = []
        for i in range(len(lines) - 1):
            header, separator = lines[i], lines[i + 1]
            if re.match(r"\s*\|.*\|", header) and _TABLE_SEPARATOR.match(separator):
                offending.append(i + 1)
        self.assertEqual(
            offending,
            [],
            "the work-log tail schema must NOT use a markdown pipe table — NB-359 "
            "bans tables in Linear comments; use a bold-label list. Found a table "
            f"header at region line(s): {offending} (AC4)",
        )


class SchemaRegionHasNoStatusEmojiTest(unittest.TestCase):
    """AC4 — the schema region uses NO status / checkmark / decorative emoji
    (NB-359 rule 5).

    Non-tautological: a `- **Decided:** ✅ ...` slip would trip this; the
    developer's bold-label-only authoring passes it."""

    @classmethod
    def setUpClass(cls):
        cls.region = _tail_region(_read(DEVELOPER))

    def test_no_status_emoji_in_schema_region(self):
        found = sorted({e for e in STATUS_EMOJI if e in self.region})
        self.assertEqual(
            found,
            [],
            "the work-log tail schema region must contain no status / checkmark "
            "emoji (NB-359 rule 5 — use `- [x]` or bold labels for state). Found: "
            f"{[hex(ord(c[0])) for c in found]} (AC4)",
        )


class HandoffSkillUntouchedTest(unittest.TestCase):
    """AC4 — ``skills/solve/handoff.md`` stays the In-Review PR-handoff skill: it
    still declares ``name: solve-handoff`` and describes opening the PR, and the
    work-log-tail schema did NOT leak onto it (the original-framing name collision
    this unit deliberately avoided).

    Non-tautological: the signature-token guard goes red the moment any of
    ``Decided`` / ``Rejected`` / ``Remaining`` / ``omit-when-empty`` is written
    into handoff.md — exactly the regression AC4 forbids. It passes now because the
    file is genuinely untouched."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(HANDOFF)
        cls.lower = cls.text.lower()

    def test_handoff_file_exists(self):
        self.assertTrue(
            HANDOFF.is_file(),
            f"{HANDOFF} must still exist — it is the In-Review PR-handoff skill (AC4)",
        )

    def test_handoff_is_still_the_solve_handoff_skill(self):
        """Its identity is unchanged: the ``name: solve-handoff`` frontmatter key."""
        self.assertRegex(
            self.text,
            r"(?m)^name:\s*solve-handoff\b",
            "skills/solve/handoff.md must still declare `name: solve-handoff` — its "
            "In-Review PR-handoff identity is untouched (AC4)",
        )

    def test_handoff_still_describes_pr_handoff(self):
        """Its PR-handoff behaviour is unchanged — it still talks about opening the
        PR / handing the problem to In Review."""
        self.assertIn(
            "pr",
            self.lower,
            "skills/solve/handoff.md must still describe the PR handoff (AC4)",
        )
        self.assertIn(
            "in review",
            self.lower,
            "skills/solve/handoff.md must still describe the In-Review handoff (AC4)",
        )

    def test_worklog_schema_did_not_leak_into_handoff(self):
        """None of the work-log-tail schema's signature tokens appear in
        handoff.md — the schema landed in agents/developer.md, not here (AC4)."""
        leaked = [t for t in SCHEMA_SIGNATURE_TOKENS if t in self.lower]
        self.assertEqual(
            leaked,
            [],
            "the work-log-tail schema must NOT leak into skills/solve/handoff.md "
            f"(found schema token(s): {leaked}) — NB-355 is a content schema for "
            "agents/developer.md and leaves handoff.md untouched (AC4)",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
