"""Presence-anchor tests for NB-359 — the Linear-comment Output Style.

NB-359 adds a Claude Code Output Style, ``output-styles/linear-comment.md``, that
constrains the developer subagent's ``**[backlogd developer]**`` Linear comment so it
renders cleanly on Linear: language-tagged code fences, no em-dashes, NO markdown tables
(use a bold-label list or short prose), NO status / checkmark emoji, list nesting no
deeper than two levels, no decorative emoji. ``agents/developer.md`` is wired to adopt the
style at the PROMPT level (pointing at the style file as the canonical rule-set), and
``docs/specialists.md`` documents the constraint set so future specialists know how to
inherit or override it.

(PO rework on AC3's live render: the original cut allowed "simple pipe tables only" and
plain status markers; the PO judged both render poorly in Linear, so tables are now banned
outright and status / checkmark emoji are explicitly forbidden. The table/emoji anchors
below assert the BAN and guard against the pre-rework affirmative wording.)

The acceptance criteria:

- AC1 ``output-styles/linear-comment.md`` exists with explicit formatting constraints
  (no em-dashes; language-tagged fences; max 2-level nesting; NO markdown tables; NO
  status / checkmark emoji).
- AC2 ``agents/developer.md`` declares / adopts the output style.
- AC3 on a controlled run the developer's comment renders cleanly on Linear (verified
  VISUALLY — REVIEW-scope, not assertable here without becoming a tautology).
- AC4 the constraint set is documented in ``docs/specialists.md`` so future specialists
  know how to inherit or override.

These are prose-in-markdown / agent-prose ACs (the unit ships an output-style doc + agent
prose + a docs section, no runnable behaviour), so they are anchored the way
``test_specialist_roster.py`` and ``test_contributing_docs.py`` anchor their docs units:
every assertion targets a DURABLE token — a file path, a heading, the constraint
vocabulary ("language", "em-dash", "table", "nest") — never a full sentence or exact
wording (the NB-389 reword-fragility trap). The anchors are themselves the facts the unit
had to land: pre-change, ``output-styles/linear-comment.md`` does not exist, and neither
``agents/developer.md`` nor ``docs/specialists.md`` mentions the style file or the token
"em-dash". So each test fails before the change and passes after it — not a
``True == True`` tautology.

Deliberately NOT covered here (REVIEW-scope — the reviewer's / PO's judgement, reported
as review-scope rather than silently skipped; see the tester's report):

- AC3's visual render: whether the comment ACTUALLY renders cleanly in Linear's UI is an
  eyeball check no markdown grep can perform;
- whether the developer subagent, when an LLM follows the prompt at runtime, ACTUALLY
  obeys the constraints in every comment — that is agent behaviour, not a static fact;
- whether the constraint set is the *right* set for Linear's renderer (an editorial /
  correctness call about Linear's Markdown support).

Why stdlib only: this is the repo's test convention — CI runs
``python3 -m unittest discover -s scripts -p 'test_*.py'`` on a bare Python with no
``pip install``. Files are read as UTF-8 and scanned case-insensitively for stable tokens.

Run from the repo root:  python scripts/test_linear_comment_style.py
"""

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
STYLE = REPO_ROOT / "output-styles" / "linear-comment.md"
DEVELOPER = REPO_ROOT / "agents" / "developer.md"
SPECIALISTS = REPO_ROOT / "docs" / "specialists.md"


def _read(path):
    """File text (UTF-8), or empty string if absent so the file-exists test owns
    the missing-file failure rather than every test erroring."""
    return path.read_text(encoding="utf-8") if path.is_file() else ""


# --- AC1: the style file exists with explicit formatting constraints ---------

class StyleFileExistsTest(unittest.TestCase):
    """AC1 — ``output-styles/linear-comment.md`` exists."""

    def test_style_file_exists(self):
        self.assertTrue(
            STYLE.is_file(),
            f"{STYLE} must exist (AC1) — the canonical Linear-comment output style",
        )


class StyleFileFrontmatterTest(unittest.TestCase):
    """AC1 — it is a Claude Code Output Style file: YAML frontmatter with a
    ``name:`` and a ``description:`` key, then the body. Anchored on the
    frontmatter fence + the two required keys, not on their values."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(STYLE)

    def test_opens_with_frontmatter(self):
        self.assertTrue(
            self.text.lstrip().startswith("---"),
            "the style file must open with a `---` YAML frontmatter block "
            "(Claude Code Output Style format) (AC1)",
        )

    def test_has_name_key(self):
        self.assertRegex(
            self.text,
            r"(?m)^name:\s*\S",
            "the style file frontmatter must carry a non-empty `name:` key (AC1)",
        )

    def test_has_description_key(self):
        self.assertRegex(
            self.text,
            r"(?m)^description:\s*\S",
            "the style file frontmatter must carry a non-empty `description:` key (AC1)",
        )


class StyleFileConstraintsTest(unittest.TestCase):
    """AC1 — the four named constraints the AC requires are all spelled out:
    language-tagged fences, no em-dashes, max two-level nesting, no
    Linear-unsupported (complex) tables. Each anchored on a durable token."""

    @classmethod
    def setUpClass(cls):
        cls.lower = _read(STYLE).lower()

    def test_constraint_language_tagged_fences(self):
        """Fences must be language-tagged — the 'language' + 'fence' vocabulary."""
        self.assertIn(
            "language", self.lower,
            "the style must require LANGUAGE-tagged code fences (AC1)",
        )
        self.assertTrue(
            re.search(r"fence|code\s*block|```", self.lower),
            "the style must talk about code fences / code blocks (AC1)",
        )

    def test_constraint_no_em_dashes(self):
        """The em-dash ban — the literal token 'em-dash' (zero occurrences before
        this unit, so this is a non-tautological anchor)."""
        self.assertRegex(
            self.lower,
            r"em[\s-]*dash",
            "the style must ban em-dashes (the 'em-dash' constraint) (AC1)",
        )

    def test_constraint_two_level_nesting(self):
        """List nesting capped at two levels — the 'nest' + 'two' vocabulary."""
        self.assertIn(
            "nest", self.lower,
            "the style must constrain list NESTING (AC1)",
        )
        self.assertTrue(
            re.search(r"two[\s-]*level|2[\s-]*level|two\b", self.lower),
            "the style must cap nesting at TWO levels (AC1)",
        )

    def test_constraint_no_markdown_tables(self):
        """Tables are BANNED outright (PO rework: pipe tables render poorly in a
        Linear comment). The style must (a) state a "no markdown tables" rule and
        (b) NOT carry any of the pre-rework AFFIRMATIVE table-allowance phrases
        (`simple tables`, `basic pipe tables`, `plain pipe table`, `prefer a
        concise table`). Both halves go red against the pre-rework style file and
        green after the rework, so this is a genuine pre/post anchor, not a
        tautology on the bare word "table"."""
        self.assertIn(
            "table", self.lower,
            "the style must constrain TABLE use (AC1)",
        )
        self.assertIn(
            "no markdown table", self.lower,
            "the style must BAN markdown tables outright with a 'no markdown "
            "tables' rule (PO rework) — not the old 'simple tables only' (AC1)",
        )
        # Guard against the pre-rework affirmative wording surviving anywhere
        # (description, rule body, or quick reference). Any of these means tables
        # are still being PERMITTED, which the rework forbids.
        for forbidden in (
            r"simple\s+tables",
            r"basic\s+pipe\s+tables",
            r"plain\s+pipe\s+table",
            r"prefer\s+a\s+concise\s+table",
        ):
            self.assertNotRegex(
                self.lower,
                forbidden,
                f"the style must NOT permit tables (matched pre-rework phrase "
                f"/{forbidden}/) — the PO rework replaced 'simple/pipe tables' "
                f"with a hard no-tables ban (AC1)",
            )

    def test_constraint_no_status_emoji(self):
        """Status / checkmark emoji are FORBIDDEN (PO rework: the PO disliked the
        green-check / cross / question-mark / memo style). The style must (a) name
        a status-emoji ban (the 'status' + 'emoji' vocabulary in a no-/never
        clause) and (b) NOT carry the pre-rework permissive 'status markers are
        fine' wording. Both halves discriminate pre vs post the rework, so this is
        not a tautology on the bare word 'emoji'."""
        self.assertIn(
            "emoji", self.lower,
            "the style must constrain EMOJI use (AC1)",
        )
        self.assertTrue(
            re.search(r"(no|never)[\w\s,]*status[\w\s,/-]*emoji"
                      r"|status[\w\s,/-]*emoji[\w\s,/-]*(never|forbidden|noise)",
                      self.lower),
            "the style must explicitly FORBID status / checkmark emoji (PO "
            "rework) — name the status-emoji ban, not just 'no decorative "
            "emoji' (AC1)",
        )
        # Guard against the pre-rework permissive wording (status markers were
        # previously allowed "in moderation").
        self.assertNotRegex(
            self.lower,
            r"status\s+markers?\s+are\s+fine",
            "the style must NOT say 'status markers are fine' — the PO rework "
            "forbids status / checkmark emoji outright (AC1)",
        )


# --- AC2: agents/developer.md adopts / declares the style -------------------

class DeveloperAdoptsStyleTest(unittest.TestCase):
    """AC2 — ``agents/developer.md`` declares / adopts the output style by pointing
    its ``<Output_Format>`` at the style file as the canonical rule-set.

    Pre-change anchor: ``developer.md`` @ HEAD references neither
    ``output-styles/linear-comment.md`` nor the token 'em-dash' — so these fail
    before NB-359."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(DEVELOPER)
        cls.lower = cls.text.lower()

    def test_developer_references_the_style_file(self):
        """The developer prompt names the concrete style file (relative path from
        ``agents/developer.md`` is ``../output-styles/linear-comment.md``)."""
        self.assertIn(
            "output-styles/linear-comment.md",
            self.text,
            "agents/developer.md must reference output-styles/linear-comment.md "
            "as the canonical comment rule-set (AC2)",
        )

    def test_developer_names_a_concrete_constraint(self):
        """The reference is not a bare mention: at least one concrete constraint
        (e.g. the em-dash ban) is named at the point of adoption, so the wiring is
        meaningful even read in isolation."""
        self.assertRegex(
            self.lower,
            r"em[\s-]*dash",
            "agents/developer.md must name a concrete style constraint (e.g. the "
            "em-dash ban) where it adopts the style (AC2)",
        )

    def test_no_tools_frontmatter_line(self):
        """NB-345 invariant guard: adopting the style must NOT reintroduce a
        ``tools:`` frontmatter line (that re-triggers the NB-340 MCP-tool drop).
        The frontmatter is the leading ``---`` block; assert no ``tools:`` key in
        it."""
        m = re.match(r"---\s*\n(.*?)\n---", self.text, re.DOTALL)
        self.assertIsNotNone(
            m, "agents/developer.md must have a leading --- frontmatter block")
        frontmatter = m.group(1)
        self.assertNotRegex(
            frontmatter,
            r"(?m)^tools:",
            "agents/developer.md frontmatter must NOT carry a `tools:` line "
            "(NB-345 invariant — re-adding it re-triggers NB-340)",
        )


# --- AC4: docs/specialists.md documents the constraint set ------------------

class SpecialistsDocumentsStyleTest(unittest.TestCase):
    """AC4 — ``docs/specialists.md`` documents the constraint set and links the
    style file so future specialists know how to inherit or override it.

    Pre-change anchor: ``specialists.md`` @ HEAD links neither
    ``output-styles/linear-comment.md`` nor uses the token 'em-dash' — so these
    fail before NB-359."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(SPECIALISTS)
        cls.lower = cls.text.lower()

    def test_specialists_links_the_style_file(self):
        """A markdown link points at the style file (relative path from
        ``docs/specialists.md`` is ``../output-styles/linear-comment.md``)."""
        self.assertRegex(
            self.text,
            r"\]\(\s*\.\./output-styles/linear-comment\.md\s*\)",
            "docs/specialists.md must contain a markdown link to "
            "`../output-styles/linear-comment.md` (AC4)",
        )

    def test_specialists_names_the_constraints(self):
        """The constraint set is summarised, not just linked: the em-dash ban and
        the language-tagged-fence rule both appear (durable tokens)."""
        self.assertRegex(
            self.lower,
            r"em[\s-]*dash",
            "docs/specialists.md must document the em-dash constraint (AC4)",
        )
        self.assertIn(
            "language",
            self.lower,
            "docs/specialists.md must document the language-tagged-fence constraint (AC4)",
        )

    def test_specialists_explains_inherit_or_override(self):
        """The AC asks specifically that the doc tells specialists how to INHERIT
        or OVERRIDE the style — both verbs present near the constraint set."""
        self.assertIn(
            "inherit", self.lower,
            "docs/specialists.md must explain how a specialist INHERITS the style (AC4)",
        )
        self.assertIn(
            "override", self.lower,
            "docs/specialists.md must explain how a specialist OVERRIDES the style (AC4)",
        )


# --- AC4 (tester, widening): inherit/override guidance is SECTION-SCOPED --------
#
# Added by the backlogd tester. The developer's
# ``SpecialistsDocumentsStyleTest.test_specialists_explains_inherit_or_override``
# asserts the words "inherit" and "override" appear *somewhere* in
# ``docs/specialists.md``. That is a weak anchor: both words pre-existed in the
# file at HEAD for unrelated reasons (``model: inherit``, the "How the PO
# overrides" section), so that test passes even against the pre-change file and
# does not prove the AC4-SPECIFIC requirement — that the doc tells specialists how
# to inherit *or override* the LINEAR-COMMENT OUTPUT STYLE in particular.
#
# This test closes that gap by scoping the assertion to the "## Linear-comment
# output style" section: both the inherit guidance and the override guidance must
# live INSIDE that section. Pre-change the section does not exist, so this fails
# at HEAD and passes after NB-359 — a genuine pre/post anchor, not a tautology.


class SpecialistsInheritOverrideSectionScopedTest(unittest.TestCase):
    """AC4 (tester) — the inherit/override guidance is documented *for the output
    style* specifically, inside the dedicated section, not merely present somewhere
    in the file."""

    # The dedicated AC4 section heading the developer added. Matched as a stable
    # token (the heading text), tolerant of any prose that follows it.
    _SECTION = re.compile(
        r"(?ms)^##\s+Linear-comment output style\b(.*?)(?=^##\s|\Z)"
    )

    @classmethod
    def setUpClass(cls):
        cls.text = _read(SPECIALISTS)

    def _section_body(self):
        m = self._SECTION.search(self.text)
        self.assertIsNotNone(
            m,
            "docs/specialists.md must contain a dedicated `## Linear-comment "
            "output style` section documenting the constraint set (AC4)",
        )
        return m.group(1).lower()

    def test_inherit_guidance_is_in_the_output_style_section(self):
        """The 'how to inherit it' guidance lives inside the output-style section
        (not just somewhere else in the file, e.g. `model: inherit`)."""
        self.assertIn(
            "inherit",
            self._section_body(),
            "the `## Linear-comment output style` section must explain how a "
            "specialist INHERITS the style (AC4) — the file-global word does not "
            "count, the guidance must be in this section",
        )

    def test_override_guidance_is_in_the_output_style_section(self):
        """The 'how to override it' guidance lives inside the output-style section
        (not just somewhere else in the file, e.g. the PO-override section)."""
        self.assertIn(
            "override",
            self._section_body(),
            "the `## Linear-comment output style` section must explain how a "
            "specialist OVERRIDES the style (AC4) — the file-global word does not "
            "count, the guidance must be in this section",
        )


# --- AC3 (tester, proxy): the style file DOGFOODS its own dash rule -------------
#
# Added by the backlogd tester. AC3 ("the developer's progress comment renders
# cleanly on Linear, verified visually") is not machine-assertable — confirming
# the Linear UI render needs the reviewer's / PO's eye, and is reported as
# review-scope. What CAN be asserted mechanically is a self-consistency proxy: the
# canonical style file must itself obey the constraints it sets, because it is the
# artifact every specialist copies from. The most-emphasised, unambiguous rule is
# rule 2 (no em-dashes / en-dashes), so the style file must contain zero of each.
#
# Non-tautological: the dashes are real Unicode characters a careless edit can
# reintroduce (the developer used plain hyphens deliberately); this test would go
# red the moment the file stops practising its own rule. It is a proxy for AC3, not
# a substitute — it does not prove the Linear render.

EM_DASH = "—"  # —
EN_DASH = "–"  # –


class StyleFileDogfoodsNoDashesTest(unittest.TestCase):
    """AC3 (tester, proxy) — the style file obeys its own no-em-dash rule: it
    contains no em-dash and no en-dash characters."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(STYLE)

    def test_no_em_dash_character(self):
        self.assertNotIn(
            EM_DASH,
            self.text,
            "output-styles/linear-comment.md must contain no em-dash (U+2014) "
            "character — it must dogfood its own rule 2 (AC3 proxy / AC1 "
            "self-consistency)",
        )

    def test_no_en_dash_character(self):
        self.assertNotIn(
            EN_DASH,
            self.text,
            "output-styles/linear-comment.md must contain no en-dash (U+2013) "
            "character — rule 2 bans the en-dash alongside the em-dash (AC3 proxy "
            "/ AC1 self-consistency)",
        )


# --- AC3 (tester, proxy, PO-rework widening): the style file DOGFOODS its own ---
# new no-table rule.
#
# Added by the backlogd tester for the PO-rework round. The rework's headline
# change is that markdown tables are now BANNED outright (rule 3). The canonical
# style file is the artifact every specialist copies from, so — exactly as with the
# no-dash dogfood above — it must itself practise the no-table rule. Before the
# rework the file's own "Quick reference" section WAS a pipe table, so this proxy
# is non-tautological: it goes red against the pre-rework style file (the
# quick-reference table trips it) and green after the rework converted that section
# to a bold-label list. It is a proxy for AC3, not a substitute (it does not prove
# the Linear render); it complements the developer's text-level
# ``test_constraint_no_markdown_tables`` (which asserts the RULE is stated) by
# asserting the file OBEYS the rule it states.

# A markdown pipe table = a header row of `| ... |` immediately followed by a
# separator row whose cells are runs of dashes (`| --- | --- |`). Matching the
# header+separator pair (not a lone `|`) avoids flagging inline code like ` ``` `
# or prose that merely contains a pipe character.
_TABLE_SEPARATOR = re.compile(r"^\s*\|(?:\s*:?-{1,}:?\s*\|)+\s*$", re.MULTILINE)


class StyleFileDogfoodsNoTableTest(unittest.TestCase):
    """AC3 (tester, proxy) — the style file obeys its own new no-table rule: it
    contains no markdown pipe table (header + `|---|` separator) anywhere."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(STYLE)

    def test_style_file_contains_no_pipe_table(self):
        lines = self.text.splitlines()
        offending = []
        for i in range(len(lines) - 1):
            header = lines[i]
            separator = lines[i + 1]
            if re.match(r"\s*\|.*\|", header) and _TABLE_SEPARATOR.match(separator):
                offending.append(i + 1)  # 1-based line number of the header row
        self.assertEqual(
            offending,
            [],
            "output-styles/linear-comment.md must contain no markdown pipe table "
            "(header row + `|---|` separator) — it must dogfood its own rule 3 "
            f"no-tables ban (PO rework). Found a table header at line(s): "
            f"{offending} (AC3 proxy / AC1 self-consistency)",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
