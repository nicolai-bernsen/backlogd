"""Regression net for NB-430 — developer variety via standards-profiles, not more subagents.

NB-430's outcome: ONE `developer` agent whose specialization comes from the standards it
loads (NB-380's `applies-to` selective load), not from a separate agent file per domain;
and a baked-in, quotable rule — *split agents on tool grants, not on topics* — so a future
contributor doesn't add `developer-react` / `developer-python` and recreate the sprawl.

The four AC are prose/`[review]`/`[manual]`-kind (the unit ships docs + an agent-prompt
instruction, no runnable behaviour). A test cannot prove "the developer obeys the
instruction at runtime" without becoming a tautology against the very prose it asserts. So,
like ``scripts/test_reviewer_standards_enforcement.py`` and
``scripts/test_specialist_grant_contract.py``, this file pins the **load-bearing prose
invariants** the change introduced — keyed to DURABLE tokens (file paths, the rule's
quotable phrase, the index-first vocabulary), never a full sentence — so an incidental
reword in the touched neighbourhood trips CI instead of silently regressing the policy.

The anchors are themselves the facts the unit had to land — each fails before NB-430 and
passes after, not a ``True == True`` tautology:

  * AC1 + AC4 — ``agents/developer.md`` MUST now consult ``docs/standards/index.json``
    index-first and filter by ``applies-to`` (pre-NB-430: zero references to the standards
    corpus in that file — the developer only found out at the gate). →
    ``DeveloperLoadsStandardsIndexTest``.
  * AC2 + AC3 — the rule "split agents on tool grants, not on topics" is baked into
    ``docs/specialists.md`` AND echoed at the add-a-specialist seam in
    ``docs/specialists/roster.md``, with ``developer-docs`` named as the grant-justified
    (not topic-justified) worked example. → ``SplitOnGrantsNotTopicsRuleTest``.

Deliberately NOT covered here (REVIEW-scope — the reviewer's judgement, surfaced rather
than silently skipped): whether the developer's prose, when an LLM follows it at runtime,
ACTUALLY loads the right profile; and whether the rule's *wording* is good enough to deter a
contributor (an editorial call, and AC2 is `[manual]` — it batches to the PO).

Why stdlib only: the repo's test convention — CI runs
``python3 -m unittest discover -s scripts -p 'test_*.py'`` on a bare Python with no
``pip install``. Files are read as UTF-8 and whitespace-collapsed so a pin survives
line-wrapping.

Run from the repo root:  python scripts/test_developer_variety_via_standards.py
(or collected by `python -m unittest discover -s scripts -p 'test_*.py'`).
"""

import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

DEVELOPER = REPO_ROOT / "agents" / "developer.md"
SPECIALISTS = REPO_ROOT / "docs" / "specialists.md"
ROSTER = REPO_ROOT / "docs" / "specialists" / "roster.md"

# AC2/AC3 want the rule baked into the mechanism/policy home AND echoed at the
# add-a-specialist seam — checked as a SET so a reword that fixes one surface and strands
# the other fails (same guard-the-neighbourhood discipline as
# test_reviewer_standards_enforcement.py / test_specialist_grant_contract.py).
RULE_SURFACES = (SPECIALISTS, ROSTER)


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def _norm(text: str) -> str:
    """Whitespace-collapse so a content pin survives prose line-wrapping."""
    return " ".join(text.split())


class DeveloperLoadsStandardsIndexTest(unittest.TestCase):
    """AC1 + AC4 — the single `developer` loads the applicable standards profile at
    dispatch via NB-380's index-first selective load. Pre-NB-430 `agents/developer.md`
    had ZERO references to the standards corpus, so each assertion fires only after the
    wire is added."""

    @classmethod
    def setUpClass(cls):
        cls.norm = _norm(_read(DEVELOPER))

    def test_developer_reads_the_standards_index(self):
        """The developer must name the compact index as the artifact it reads — the
        cite-by-path anchor mirroring the reviewer's `Read docs/standards/index.json`."""
        self.assertIn(
            "docs/standards/index.json",
            self.norm,
            "agents/developer.md must consult docs/standards/index.json (AC1/AC4) — the "
            "developer's specialization = the standards it loads, loaded at dispatch.",
        )

    def test_developer_filters_by_applies_to_scope(self):
        """Specialization-by-standards is real only if the developer FILTERS the index by
        scope — the NB-380 `applies-to` discipline, not 'read every ADR'."""
        self.assertIn(
            "applies-to",
            self.norm,
            "agents/developer.md must filter the index by `applies-to` scope (AC1/AC4).",
        )

    def test_developer_uses_index_first_load_order(self):
        """The load order is index-first, full ADR only when engaged — bounded context,
        the same discipline the reviewer runs."""
        self.assertIn(
            "index-first",
            self.norm.lower(),
            "agents/developer.md must state the index-first load order (AC1/AC4).",
        )
        # Full ADRs are opened selectively, not wholesale — the bounded-context property.
        self.assertRegex(
            self.norm,
            r"full ADR.{0,80}only when|only when.{0,80}assertion is engaged",
            "agents/developer.md must open a full ADR only when its assertion is engaged",
        )

    def test_developer_honours_only_accepted_standards(self):
        """Like the reviewer, the developer enforces only the *current Accepted* set and
        skips non-Accepted statuses — so it builds to the binding corpus, not drafts."""
        self.assertRegex(
            self.norm,
            r"only the current `Accepted` set",
            "agents/developer.md must honour only the current Accepted standards (AC1).",
        )

    def test_developer_ties_specialization_to_loaded_standards(self):
        """The crux: the developer's *kind* is data — its specialization comes from which
        standards apply (React when they say React), NOT from a separate agent file."""
        lower = self.norm.lower()
        self.assertIn(
            "specialization is the standards you load",
            lower,
            "agents/developer.md must frame specialization as the standards it loads (AC1).",
        )


class SplitOnGrantsNotTopicsRuleTest(unittest.TestCase):
    """AC2 + AC3 — the rule is baked in (so a contributor doesn't add `developer-react`
    and recreate the sprawl), quotable, and present on BOTH the policy home and the
    add-a-specialist seam, with `developer-docs` as the grant-justified worked example.

    Pre-NB-430 anchor: neither file used the phrase "tool grants, not on topics" nor named
    `developer-react`/`developer-python` as the sprawl to avoid — so these fail at HEAD."""

    def test_rule_phrase_present_on_both_surfaces(self):
        """The quotable rule appears in the policy home (specialists.md) AND is echoed at
        the add-a-specialist seam (roster.md). Checked as a set."""
        for path in RULE_SURFACES:
            with self.subTest(surface=path.name):
                norm = _norm(_read(path)).lower()
                self.assertIn(
                    "split agents on tool grants, not on topics",
                    norm,
                    f"{path.relative_to(REPO_ROOT)} must bake in the rule "
                    f"'split agents on tool grants, not on topics' (AC2/AC3).",
                )

    def test_rule_states_grant_is_the_only_justification(self):
        """The teeth of AC2: a separate agent is justified ONLY by a different
        capability/tool grant, never merely a domain label."""
        for path in RULE_SURFACES:
            with self.subTest(surface=path.name):
                norm = _norm(_read(path))
                # "ONLY ... grant" and "never ... domain label" co-occur — the
                # capability-not-topic test, anchored on durable tokens not exact wording.
                # Tolerant of markdown emphasis/blockquote markers (`**ONLY**`, a wrapped
                # `> ` prefix between 'tool' and 'grant') that survive normalization.
                self.assertRegex(
                    norm,
                    r"ONLY[\s*]{0,40}(when|by).{0,120}grant",
                    f"{path.relative_to(REPO_ROOT)} must say a separate agent is justified "
                    f"ONLY by a different (capability/tool) grant (AC2).",
                )
                self.assertRegex(
                    norm,
                    r"never (merely )?a domain label",
                    f"{path.relative_to(REPO_ROOT)} must say a domain label alone is NOT a "
                    f"justification (AC2).",
                )

    def test_rule_names_the_sprawl_to_avoid(self):
        """AC3's purpose — a future contributor must not 'helpfully' add
        `developer-react`/`developer-python`. Both surfaces name that anti-pattern."""
        for path in RULE_SURFACES:
            with self.subTest(surface=path.name):
                norm = _norm(_read(path))
                self.assertIn(
                    "developer-react",
                    norm,
                    f"{path.relative_to(REPO_ROOT)} must name the `developer-react` sprawl "
                    f"to avoid (AC3).",
                )

    def test_variety_lives_in_the_corpus_not_the_roster(self):
        """The positive framing: domain variety comes from the standards corpus via
        `applies-to`, not from more agent files."""
        norm = _norm(_read(SPECIALISTS))
        self.assertIn(
            "new standards file, not a new\nagent".replace("\n", " "),
            _norm(_read(SPECIALISTS)),
            "docs/specialists.md must say a new domain is a new standards file, not a new "
            "agent (AC1/AC2).",
        )
        # The standards index is the mechanism that makes specialization-by-standards work.
        self.assertIn("applies-to", norm)
        self.assertIn("docs/standards/index.json", norm.replace("../", ""))

    def test_developer_docs_is_the_grant_justified_worked_example(self):
        """AC2 asks the existing `developer-docs` be assessed honestly: its justification
        is its NARROWER GRANT (no Bash/git), not its docs topic. The policy home states
        that worked example."""
        norm = _norm(_read(SPECIALISTS))
        self.assertIn("developer-docs", norm)
        # The grant, not the topic, is the justification — name the reduced surface.
        self.assertRegex(
            norm,
            r"developer-docs.{0,400}?(no Bash|narrower (tool )?grant|reduced)",
            "docs/specialists.md must justify developer-docs by its narrower tool grant, "
            "not its docs topic (AC2 worked example).",
        )

    def test_pins_would_bite_on_a_topic_only_justification(self):
        """Anti-tautology guard: prove the AC2 assertions actually FIRE on a wording that
        justifies a split by topic alone (the sprawl NB-430 forbids). If the pins passed
        that synthetic text, they'd prove nothing."""
        topic_only = _norm(
            "Add a developer-react agent because it works on React, and a developer-python "
            "agent because it works on Python. Each domain gets its own agent."
        )
        self.assertNotIn("split agents on tool grants, not on topics", topic_only.lower())
        self.assertNotRegex(topic_only, r"never (merely )?a domain label")


if __name__ == "__main__":
    unittest.main(verbosity=2)
