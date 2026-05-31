"""Presence-anchor tests for NB-354 — the specialist roster catalog.

NB-354 adds ``docs/specialists/roster.md`` as ``/backlogd:scope``'s primary
routing table (extending the description-driven picker NB-337 shipped) and rewires
``commands/scope.md`` §4.5 to read the catalog first, fall back to the per-file
``description:`` scan, and flag a missing catalog row as a "catalog gap" in its
report. ``docs/specialists.md`` is updated to link the roster as the canonical list.

The acceptance criteria:

- AC1 ``docs/specialists/roster.md`` exists with a row per specialist (initially
  ``developer`` + ``developer-docs``).
- AC2 each row has columns: name, select-when criteria, tool-grant style, hand-off.
- AC3 ``/backlogd:scope`` reads the catalog as its PRIMARY picker source; falls back
  to per-file ``description:`` if the catalog is missing OR doesn't list a discovered
  agent.
- AC4 a new specialist added WITHOUT a catalog row → scope's report mentions the
  catalog gap.
- AC5 ``docs/specialists.md`` links to the roster as the canonical list.

These are prose-in-markdown ACs (the unit ships docs + a command spec, no runnable
behaviour), so they are anchored the way ``test_contributing_docs.py`` anchors its
docs unit: every assertion targets a DURABLE token — a file path, a table-header
word, a heading, the "catalog"/"fallback"/"gap" routing vocabulary — never a full
sentence or exact wording (the NB-389 reword-fragility trap). The anchors are
themselves the facts the unit had to land: pre-change, the literal token "catalog"
appears ZERO times in ``scope.md`` and ``docs/specialists.md``, neither links
``specialists/roster.md``, and ``roster.md`` does not exist. So each test fails
before the change and passes after it — not a ``True == True`` tautology.

Deliberately NOT covered here (REVIEW-scope — the reviewer's judgement, reported as
review-scope rather than silently skipped; see the tester's report):

- whether ``/backlogd:scope``'s prose, when an LLM follows it at runtime, ACTUALLY
  reads the catalog first and ACTUALLY emits a gap line for an unlisted agent — that
  is agent behaviour a markdown grep cannot execute without becoming a tautology
  against the very prose it asserts;
- whether each roster row's *select-when* criteria are correct / good routing
  signal, and whether the row's *select-when* truly mirrors the agent file's
  ``description:`` frontmatter (the "catalog is source of truth, frontmatter mirrors
  it" contract) — an editorial/accuracy call;
- whether the tool-grant-style values match each agent's real grant (partially
  spot-checked below for ``developer-docs`` as a non-tautological anchor, but
  "is the *style label* the right abstraction" stays review-scope).

Why stdlib only: this is the repo's test convention — CI runs
``python3 -m unittest discover -s scripts -p 'test_*.py'`` on a bare Python with no
``pip install``. Files are read as UTF-8 and scanned case-insensitively for stable
tokens.

Run from the repo root:  python scripts/test_specialist_roster.py
"""

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
ROSTER = REPO_ROOT / "docs" / "specialists" / "roster.md"
SPECIALISTS = REPO_ROOT / "docs" / "specialists.md"
SCOPE = REPO_ROOT / "commands" / "scope.md"
DEV_DOCS = REPO_ROOT / ".claude" / "agents" / "developer-docs.md"


def _read(path):
    """File text (UTF-8), or empty string if absent so the file-exists test owns
    the missing-file failure rather than every test erroring."""
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _table_rows(text):
    """Return the markdown table-body rows (lines starting with '|', minus the
    header and the '---' separator) from the roster text. Robust to the exact
    column count and ordering — we only need the *content* of the data rows."""
    rows = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        # Skip the header separator row (|---|---|...).
        if re.fullmatch(r"\|[\s:|-]+\|?", stripped):
            continue
        rows.append(stripped)
    return rows


# --- AC1: the roster file exists, one row per specialist --------------------

class RosterFileTest(unittest.TestCase):
    """AC1 — ``docs/specialists/roster.md`` exists."""

    def test_roster_file_exists(self):
        self.assertTrue(
            ROSTER.is_file(),
            f"{ROSTER} must exist (AC1) — the canonical routing catalog",
        )


class RosterHasARowPerSpecialistTest(unittest.TestCase):
    """AC1 — the catalog table carries a row for ``developer`` AND ``developer-docs``."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(ROSTER)
        cls.rows = _table_rows(cls.text)

    def test_has_a_markdown_table(self):
        """A pipe-delimited table is present (header + at least the two data rows)."""
        self.assertGreaterEqual(
            len(self.rows), 2,
            "roster.md must contain a markdown table with a row per specialist",
        )

    def test_row_for_developer(self):
        """A data row names the generic ``developer`` (backticked cell token)."""
        self.assertTrue(
            any(re.search(r"`developer`", r) for r in self.rows),
            "roster.md must have a catalog row for `developer` (AC1)",
        )

    def test_row_for_developer_docs(self):
        """A data row names ``developer-docs`` (the second initial specialist)."""
        self.assertTrue(
            any(re.search(r"`developer-docs`", r) for r in self.rows),
            "roster.md must have a catalog row for `developer-docs` (AC1)",
        )


# --- AC2: each row has the four named columns -------------------------------

class RosterColumnsTest(unittest.TestCase):
    """AC2 — the table's columns: name, select-when criteria, tool-grant style,
    hand-off target. Anchored on a stable token for each column in the HEADER row,
    not on exact header wording."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(ROSTER)
        # The header is the first table line; grab everything up to the '---'
        # separator so we assert against the column titles, not the data.
        header = ""
        for line in cls.text.splitlines():
            s = line.strip()
            if s.startswith("|") and not re.fullmatch(r"\|[\s:|-]+\|?", s):
                header = s
                break
        cls.header = header
        cls.header_lower = header.lower()

    def test_header_row_found(self):
        self.assertTrue(
            self.header.startswith("|"),
            "roster.md must have a markdown table header row (AC2)",
        )

    def test_column_name(self):
        """A name/specialist column heads the table."""
        self.assertTrue(
            "specialist" in self.header_lower or "name" in self.header_lower,
            f"header must carry a name/specialist column; got: {self.header!r}",
        )

    def test_column_select_when(self):
        """The select-when criteria column — the routing signal."""
        self.assertRegex(
            self.header_lower,
            r"select[\s-]*when",
            f"header must carry a 'select when' column; got: {self.header!r}",
        )

    def test_column_tool_grant_style(self):
        """The tool-grant style column."""
        self.assertRegex(
            self.header_lower,
            r"tool[\s-]*grant",
            f"header must carry a 'tool-grant style' column; got: {self.header!r}",
        )

    def test_column_hand_off(self):
        """The hand-off target column."""
        self.assertRegex(
            self.header_lower,
            r"hand[\s-]*off",
            f"header must carry a 'hand-off' column; got: {self.header!r}",
        )


class RosterToolGrantSpotCheckTest(unittest.TestCase):
    """AC2 (anti-tautology anchor) — the ``developer-docs`` tool-grant cell reflects
    the agent's ACTUAL reduced grant, not a placeholder. We don't assert the *style
    label* is the right abstraction (review-scope); we assert the row records a
    'reduced' grant for ``developer-docs``, which is true ONLY because the real
    ``.claude/agents/developer-docs.md`` carries an explicit ``tools:`` list. This
    keeps the columns test honest without grading the prose."""

    @classmethod
    def setUpClass(cls):
        cls.rows = _table_rows(_read(ROSTER))
        cls.dev_docs_frontmatter = _read(DEV_DOCS)[:600].lower()

    def test_developer_docs_real_grant_is_reduced(self):
        """Sanity: the real agent file DOES carry an explicit tools: list (so
        'reduced' is the truthful value, not invented)."""
        self.assertRegex(
            self.dev_docs_frontmatter,
            r"(?m)^tools:\s*\S",
            ".claude/agents/developer-docs.md must carry an explicit tools: list "
            "(this is what makes the roster's 'reduced' grant truthful)",
        )

    def test_developer_docs_row_records_reduced_grant(self):
        rows = [r for r in self.rows if "`developer-docs`" in r]
        self.assertTrue(rows, "no developer-docs row to check the grant style on")
        self.assertIn(
            "reduced", rows[0].lower(),
            "the developer-docs row must record a 'reduced' tool-grant style "
            "(it carries an explicit tools: list)",
        )


# --- AC3: scope reads the catalog first, description: as fallback -----------

class ScopeReadsCatalogAsPrimaryTest(unittest.TestCase):
    """AC3 — ``commands/scope.md`` names the roster catalog as its PRIMARY picker
    source and the per-file ``description:`` scan as the FALLBACK, triggered when the
    catalog is missing OR a discovered agent has no row.

    Pre-change anchor: ``scope.md`` @ HEAD uses the literal token 'catalog' ZERO
    times and a 'description-driven' picker — so these assertions fail before NB-354."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(SCOPE)
        cls.lower = cls.text.lower()

    def test_scope_references_the_roster_catalog_path(self):
        """Scope points at the concrete catalog file."""
        self.assertIn(
            "docs/specialists/roster.md",
            self.text,
            "scope.md must reference the catalog at docs/specialists/roster.md (AC3)",
        )

    def test_scope_names_the_catalog_as_primary(self):
        """The catalog is the PRIMARY source — 'primary' co-occurs with the
        catalog/routing vocabulary (token presence, not wording)."""
        self.assertIn("catalog", self.lower, "scope.md must use the 'catalog' concept")
        self.assertIn(
            "primary", self.lower,
            "scope.md must name the catalog as the 'primary' picker source (AC3)",
        )

    def test_scope_names_description_fallback(self):
        """The per-file ``description:`` scan is the FALLBACK."""
        self.assertIn(
            "fallback", self.lower,
            "scope.md must describe a 'fallback' picker source (AC3)",
        )
        self.assertIn(
            "description:", self.lower,
            "scope.md must name the per-file `description:` scan as that fallback",
        )

    def test_scope_names_both_fallback_triggers(self):
        """The fallback fires when the catalog is MISSING or a discovered agent
        has no row — both triggers named (AC3)."""
        self.assertIn(
            "missing", self.lower,
            "scope.md must say the fallback fires when the catalog is 'missing'",
        )
        self.assertTrue(
            re.search(r"no row|doesn'?t list|not listed|absent", self.lower),
            "scope.md must say the fallback fires when a discovered agent is not "
            "listed in the catalog (the 'no row' trigger)",
        )


# --- AC4: scope's report flags a catalog gap --------------------------------

class ScopeReportFlagsCatalogGapTest(unittest.TestCase):
    """AC4 — when a discovered specialist has no catalog row, scope's REPORT mentions
    the catalog gap. Anchored on the 'catalog gap' report token keyed to the roster
    path. Whether scope at runtime actually emits it is review-scope."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(SCOPE)
        cls.lower = cls.text.lower()

    def test_scope_report_mentions_catalog_gap(self):
        self.assertIn(
            "catalog gap", self.lower,
            "scope.md must document a 'catalog gap' the report surfaces (AC4)",
        )

    def test_catalog_gap_is_tied_to_the_roster_path(self):
        """The gap line references the roster file so the reader knows where the
        missing row goes. We check the gap vocabulary and the path BOTH appear in
        the report section (§6), without pinning exact wording."""
        # Find a window of text around the first 'catalog gap' mention and assert
        # the roster path appears near it (same documented example line).
        idx = self.lower.find("catalog gap")
        self.assertNotEqual(idx, -1, "no 'catalog gap' text to anchor on")
        window = self.text[max(0, idx - 200): idx + 400]
        self.assertIn(
            "docs/specialists/roster.md", window,
            "the 'catalog gap' report line must reference docs/specialists/roster.md "
            "so the missing row's home is clear (AC4)",
        )


# --- AC5: docs/specialists.md links the roster as canonical -----------------

class SpecialistsLinksRosterAsCanonicalTest(unittest.TestCase):
    """AC5 — ``docs/specialists.md`` links to the roster as the canonical list.

    Pre-change anchor: ``specialists.md`` @ HEAD carries NO link to
    ``specialists/roster.md`` and uses 'catalog' zero times — so this fails before
    NB-354."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(SPECIALISTS)
        cls.lower = cls.text.lower()

    def test_specialists_file_exists(self):
        self.assertTrue(SPECIALISTS.is_file(), f"{SPECIALISTS} must exist")

    def test_links_to_roster_file(self):
        """A markdown link points at the roster file (relative path from
        docs/specialists.md is ``specialists/roster.md``)."""
        self.assertRegex(
            self.text,
            r"\]\(\s*specialists/roster\.md\s*\)",
            "docs/specialists.md must contain a markdown link to "
            "`specialists/roster.md` (AC5)",
        )

    def test_frames_roster_as_canonical(self):
        """The link is framed as the CANONICAL list — 'canonical' co-occurs with the
        roster link in the SAME window. (Anchoring on co-occurrence, not the bare
        word: ``specialists.md`` @ HEAD already used 'canonical' elsewhere — for the
        Linear label — so a bare-word check would pass before the change and prove
        nothing. The window check fails at HEAD, where there is no roster link to be
        near, and passes after NB-354 adds the 'Canonical roster' pointer.)"""
        m = re.search(r"specialists/roster\.md", self.lower)
        self.assertIsNotNone(
            m, "no roster link to anchor the 'canonical' framing on (AC5)")
        window = self.lower[max(0, m.start() - 300): m.end() + 200]
        self.assertIn(
            "canonical", window,
            "docs/specialists.md must frame the roster LINK as the 'canonical' list "
            "(the word 'canonical' must appear near the roster reference) (AC5)",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
