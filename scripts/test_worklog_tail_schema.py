"""Presence-anchor tests for NB-355 — the developer work-log tail schema.

NB-355 adds a lightweight, omit-when-empty structured tail to the developer's
``**[backlogd developer]**`` work-log comment: four bold-label sections —
**Decided** / **Rejected** / **Risks** / **Remaining** — so every increment
leaves a scannable decision-and-risk record (ADR-004's transparency pillar). It
is a CONTENT schema for the existing comment: no new file, no new dispatch
surface, and ``skills/solve/handoff.md`` (the In-Review PR-handoff skill) is left
untouched. The schema is authored in ``agents/developer.md`` ``<Output_Format>``
and documented for inherit/override in ``docs/specialists.md``.

The acceptance criteria covered here:

- AC1 ``agents/developer.md`` ``<Output_Format>`` defines the four-section,
  omit-when-empty tail; **Risks** reuses the ``DONE_WITH_CONCERNS`` ``Concerns:``
  items (not a parallel channel); it does not duplicate the ``STATUS:`` line, the
  Problem-Read head step, or the files list.
- AC2 ``docs/specialists.md`` documents the schema + the omit-when-empty rule with
  inherit/override guidance.

These are prose-in-markdown ACs (the unit ships a contract + docs, no runnable
behaviour), so they are anchored the way ``test_specialist_roster.py`` and
``test_contributing_docs.py`` anchor their docs units: every assertion targets a
DURABLE token — a section label, the "omit-when-empty" routing word, the
``Concerns:`` reuse phrase — never a full sentence or exact wording (the NB-389
reword-fragility trap). The anchors are themselves the facts the unit had to
land: pre-change, the literal tokens "Decided", "Rejected", "Remaining", and
"omit-when-empty" appear ZERO times in BOTH files (verified at HEAD), so each
test fails before the change and passes after it — not a ``True == True``
tautology.

Deliberately NOT covered here (REVIEW-scope — the reviewer's judgement, reported
as review-scope rather than silently skipped; see the tester's report):

- whether the four sections are the *right* set and whether the omit-when-empty
  default reads cleanly on a real comment — that is the ``[manual]`` PO-confirm AC,
  an editorial/product call a markdown grep cannot make;
- whether a developer at runtime ACTUALLY fills the tail coherently (and omits
  empty sections) — agent behaviour, not a static fact;
- whether the schema renders correctly under Linear's renderer — a rendering /
  visual call, not a token presence one.

Why stdlib only: this is the repo's test convention — CI runs
``python3 -m unittest discover -s scripts -p 'test_*.py'`` on a bare Python with
no ``pip install``. Files are read as UTF-8 and scanned case-insensitively for
stable tokens.

Run from the repo root:  python scripts/test_worklog_tail_schema.py
"""

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEVELOPER = REPO_ROOT / "agents" / "developer.md"
SPECIALISTS = REPO_ROOT / "docs" / "specialists.md"

# The four section labels the schema defines, in their canonical bold-label form.
SECTIONS = ("Decided", "Rejected", "Risks", "Remaining")


def _read(path):
    """File text (UTF-8), or empty string if absent so the file-exists test owns
    the missing-file failure rather than every test erroring."""
    return path.read_text(encoding="utf-8") if path.is_file() else ""


# --- AC1: the four sections are defined in agents/developer.md --------------

class DeveloperDefinesTheFourSectionsTest(unittest.TestCase):
    """AC1 — ``agents/developer.md`` ``<Output_Format>`` defines the work-log tail
    with all four named sections, rendered as bold labels (the Linear-comment style).

    Pre-change anchor: "Decided", "Rejected", and "Remaining" appear ZERO times in
    ``developer.md`` @ HEAD, so these fail before NB-355."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(DEVELOPER)
        cls.lower = cls.text.lower()

    def test_developer_file_exists(self):
        self.assertTrue(DEVELOPER.is_file(), f"{DEVELOPER} must exist")

    def test_defines_each_section_as_a_bold_label(self):
        """Each of Decided / Rejected / Risks / Remaining appears as a bold label
        (``**Decided:**`` etc.) — the schema is rendered in the bold-label list shape
        the NB-359 Linear-comment style mandates, not as a markdown table."""
        for section in SECTIONS:
            with self.subTest(section=section):
                self.assertRegex(
                    self.text,
                    rf"\*\*{section}:\*\*",
                    f"agents/developer.md must define a **{section}:** "
                    f"work-log tail section (AC1)",
                )

    def test_tail_is_in_the_output_format_section(self):
        """The schema lives inside the ``<Output_Format>`` contract section — the
        right home (not, say, a stray note elsewhere)."""
        m = re.search(r"<Output_Format>(.*?)</Output_Format>", self.text, re.S)
        self.assertIsNotNone(
            m, "agents/developer.md must have an <Output_Format> section")
        body = m.group(1)
        for section in SECTIONS:
            with self.subTest(section=section):
                self.assertRegex(
                    body,
                    rf"\*\*{section}:\*\*",
                    f"the **{section}:** section must be defined INSIDE "
                    f"<Output_Format> (AC1)",
                )


class DeveloperTailIsOmitWhenEmptyTest(unittest.TestCase):
    """AC1 — the tail is OMIT-WHEN-EMPTY: a section with nothing is dropped, so a
    trivial change stays terse.

    Pre-change anchor: "omit-when-empty" appears ZERO times in ``developer.md`` @
    HEAD, so this fails before NB-355."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(DEVELOPER)
        cls.lower = cls.text.lower()

    def test_states_the_omit_when_empty_rule(self):
        """The omit-when-empty contract is named explicitly (hyphenated or spaced)."""
        self.assertRegex(
            self.lower,
            r"omit[\s-]*when[\s-]*empty",
            "agents/developer.md must state the 'omit-when-empty' rule for the "
            "work-log tail (AC1)",
        )


class DeveloperRisksReusesConcernsTest(unittest.TestCase):
    """AC1 — **Risks** reuses the ``DONE_WITH_CONCERNS`` ``Concerns:`` items, it is
    NOT a parallel channel. Anchored on the co-occurrence of the Risks label, the
    'Concerns' token, and a 'not a parallel channel' / 'same' framing in one window."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(DEVELOPER)
        cls.lower = cls.text.lower()

    def test_risks_section_references_concerns(self):
        """Near the **Risks:** label, the schema points at the existing Concerns:
        items (so the reader knows it is one channel, not two)."""
        idx = self.text.find("**Risks:**")
        self.assertNotEqual(
            idx, -1, "no **Risks:** section to anchor the Concerns reuse on (AC1)")
        window = self.lower[max(0, idx - 100): idx + 500]
        self.assertIn(
            "concerns", window,
            "the **Risks:** section must reference the DONE_WITH_CONCERNS "
            "`Concerns:` items it reuses (AC1)",
        )

    def test_risks_is_not_a_parallel_channel(self):
        """The 'not a parallel channel' / 'same content' framing is present, keeping
        Risks tied to Concerns rather than a second risk surface."""
        self.assertTrue(
            re.search(r"not\s+(?:in\s+)?a\s+parallel\s+channel", self.lower)
            or re.search(r"same\s+(?:content|thing)", self.lower)
            or re.search(r"not\s+a\s+second\s+channel", self.lower),
            "agents/developer.md must say Risks is the SAME channel as Concerns "
            "(not a parallel/second channel) (AC1)",
        )


class DeveloperTailDoesNotDuplicateStatusOrFilesTest(unittest.TestCase):
    """AC1 — the tail must NOT duplicate the ``STATUS:`` line, the Problem-Read head
    step, or the files list. Anchored on the explicit 'does not duplicate' framing
    near the tail, naming STATUS and the files list."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(DEVELOPER)
        cls.lower = cls.text.lower()

    def test_states_no_duplication_of_status_or_files(self):
        """A 'does not duplicate' / 'not duplicate' clause co-occurs with both the
        STATUS line and the files list, so the tail is additive, not a copy."""
        # Anchor on the Decided/Rejected/Risks/Remaining tail region. Strip markdown
        # emphasis markers (``**``/``*``) from the window so the anchor matches the
        # WORDS, not incidental ``does **not** duplicate`` bold markup.
        idx = self.text.find("**Decided:**")
        self.assertNotEqual(idx, -1, "no tail region to anchor the no-duplication clause on")
        window = re.sub(r"[*_`]+", " ", self.lower[max(0, idx - 200): idx + 1200])
        self.assertTrue(
            re.search(r"(?:not|does\s+not|doesn'?t|never)\s+duplicate", window),
            "the tail must state it does NOT duplicate existing log content (AC1)",
        )
        self.assertIn(
            "status", window,
            "the no-duplication clause must name the STATUS line (AC1)",
        )
        self.assertIn(
            "files", window,
            "the no-duplication clause must name the files (changed) list (AC1)",
        )


# --- AC2: docs/specialists.md documents the schema + omit-when-empty rule ---

class SpecialistsDocumentsTheSchemaTest(unittest.TestCase):
    """AC2 — ``docs/specialists.md`` documents the four-section schema, the
    omit-when-empty rule, and inherit/override guidance (the same pattern as the
    Linear-comment output-style section).

    Pre-change anchor: "Decided"/"Rejected"/"Remaining"/"omit-when-empty" appear
    ZERO times in ``specialists.md`` @ HEAD, so these fail before NB-355."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(SPECIALISTS)
        cls.lower = cls.text.lower()

    def test_specialists_file_exists(self):
        self.assertTrue(SPECIALISTS.is_file(), f"{SPECIALISTS} must exist")

    def test_documents_all_four_sections(self):
        for section in SECTIONS:
            with self.subTest(section=section):
                self.assertIn(
                    section.lower(),
                    self.lower,
                    f"docs/specialists.md must document the '{section}' section (AC2)",
                )

    def test_documents_omit_when_empty_rule(self):
        self.assertRegex(
            self.lower,
            r"omit[\s-]*when[\s-]*empty",
            "docs/specialists.md must document the 'omit-when-empty' rule (AC2)",
        )

    def test_documents_inherit_and_override(self):
        """Inherit/override guidance is present — mirroring the Linear-comment
        output-style section's structure (AC2)."""
        self.assertIn(
            "inherit", self.lower,
            "docs/specialists.md must give inherit guidance for the schema (AC2)",
        )
        self.assertIn(
            "override", self.lower,
            "docs/specialists.md must give override guidance for the schema (AC2)",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
