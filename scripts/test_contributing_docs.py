"""Presence-anchor tests for NB-290 (T5: document pre-commit + CI gates).

The unit adds a ``### Linting & checks`` subsection to ``CONTRIBUTING.md`` that
documents (a) the local ``pre-commit`` setup and (b) the gating-vs-advisory
split between the blocking ``dev`` checks (markdownlint, hygiene, json/yaml,
``claude plugin validate``, actionlint, internal ``lychee --offline`` links,
plugin/template/test/witness) and the ADVISORY weekly external-link workflow.

AC: ``CONTRIBUTING.md`` documents the local pre-commit setup and the
gating-vs-advisory checks.

This is a DOCS unit, so the AC is primarily REVIEW-verified — whether the prose
*accurately* describes the shipped gates (vs ``.pre-commit-config.yaml`` /
``ci.yml`` / ``links-external.yml``) is the reviewer's call, not a runner's.
What a test CAN prove durably, without becoming a reword-fragile prose-grep
(the NB-389 trap), is that the section exists and names the STABLE, load-bearing
identifiers the AC requires. So every assertion below targets a durable token —
a heading, a command, a tool name, the blocking/advisory distinction — and
never a full sentence or exact wording. The anchors are themselves the facts the
unit had to land (the names of the documented gates), so this is not a
``True == True`` tautology: it fails before the change (the section and these
tokens are absent) and passes after it.

Deliberately NOT covered here (REVIEW-scope, not unit-testable without becoming
a tautology against the source files): that the prose's description of each gate
*matches* what ``.pre-commit-config.yaml`` / ``ci.yml`` / ``links-external.yml``
actually do, that the blocking/advisory framing is correct, and that the wording
stays public/clean-room. Those are the reviewer's judgement, reported as
review-scope rather than silently skipped.

Why stdlib only: this is the repo's test convention (CI runs
``python3 -m unittest discover -s scripts -p 'test_*.py'`` on a bare
ubuntu-latest Python with no ``pip install``). The doc is read as UTF-8 text and
scanned case-insensitively for stable tokens.

Run from the repo root:  python scripts/test_contributing_docs.py
"""

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRIBUTING = REPO_ROOT / "CONTRIBUTING.md"


def _read(path):
    """File text (UTF-8), or empty string if absent so the file-exists test owns
    the missing-file failure rather than every test erroring."""
    return path.read_text(encoding="utf-8") if path.is_file() else ""


class ContributingFileTest(unittest.TestCase):
    """``CONTRIBUTING.md`` exists at the repo root."""

    def test_file_exists(self):
        self.assertTrue(
            CONTRIBUTING.is_file(),
            f"{CONTRIBUTING} must exist",
        )


class LintingSectionTest(unittest.TestCase):
    """The unit's section exists and documents the local pre-commit setup."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(CONTRIBUTING)
        cls.lower = cls.text.lower()

    def test_has_linting_and_checks_heading(self):
        """A 'Linting & checks' heading (any level) anchors the new section."""
        self.assertRegex(
            self.text,
            r"(?im)^#{2,}\s+Linting\s*&\s*checks\b",
            "CONTRIBUTING.md must carry a 'Linting & checks' heading",
        )

    def test_documents_pre_commit(self):
        """The local pre-commit tool is named."""
        self.assertIn(
            "pre-commit",
            self.lower,
            "the section must mention the pre-commit tool",
        )

    def test_documents_pre_commit_install(self):
        """The install step (`pre-commit install`) is documented — the durable
        token for 'how to set up the hooks locally'."""
        self.assertRegex(
            self.lower,
            r"pre-commit\s+install",
            "the section must document `pre-commit install`",
        )


class GateToolsNamedTest(unittest.TestCase):
    """The stable-identifier gate tools the AC names are all present."""

    @classmethod
    def setUpClass(cls):
        cls.lower = _read(CONTRIBUTING).lower()

    def test_names_markdownlint(self):
        self.assertIn("markdownlint", self.lower, "must name markdownlint")

    def test_names_actionlint(self):
        self.assertIn("actionlint", self.lower, "must name actionlint")

    def test_names_lychee(self):
        self.assertIn("lychee", self.lower, "must name lychee (the link checker)")

    def test_names_claude_plugin_validate(self):
        """The manifest gate — a stable command identifier."""
        self.assertRegex(
            self.lower,
            r"claude\s+plugin\s+validate",
            "must name the `claude plugin validate` manifest gate",
        )


class GatingVsAdvisoryTest(unittest.TestCase):
    """The section distinguishes BLOCKING `dev` gates from the ADVISORY
    external-link workflow — the gating-vs-advisory split the AC requires."""

    @classmethod
    def setUpClass(cls):
        cls.lower = _read(CONTRIBUTING).lower()

    def test_marks_something_advisory(self):
        """An 'advisory' framing is present (the non-gating side of the split)."""
        self.assertIn(
            "advisory",
            self.lower,
            "the section must describe an 'advisory' (non-gating) check",
        )

    def test_distinguishes_external_links(self):
        """The advisory side is the EXTERNAL-link check — naming 'external'
        anchors the distinction from the internal/offline blocking gate."""
        self.assertIn(
            "external",
            self.lower,
            "the section must reference the EXTERNAL-link checking that is advisory",
        )

    def test_describes_a_blocking_gate(self):
        """The gating side is present: a 'block'/'gate' word co-occurs with
        'dev' (the branch the checks gate). Token presence only, not wording."""
        self.assertTrue(
            re.search(r"block", self.lower) or re.search(r"\bgat(e|es|ing)\b", self.lower),
            "the section must describe checks that block/gate (the gating side)",
        )
        self.assertIn(
            "dev",
            self.lower,
            "the gating side must reference the `dev` branch the checks gate",
        )


if __name__ == "__main__":
    unittest.main()
