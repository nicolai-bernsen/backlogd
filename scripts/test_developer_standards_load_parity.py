"""Independent tester pass for NB-430 — supplements scripts/test_developer_variety_via_standards.py.

The developer's own drift net (``test_developer_variety_via_standards.py``) pins that the
new prose EXISTS on each surface. This file covers two genuine gaps that net leaves open,
both of which the change itself introduced and both testable without tautology:

  1. **Protocol-numbering integrity + the surviving step-number cross-references.** NB-430
     inserted a new step 5 into ``agents/developer.md`` ``<Investigation_Protocol>`` and
     renumbered the old 5/6/7 → 6/7/8. The protocol must stay **contiguously numbered**
     (1..N, no gap, no dupe) and the two places that cite a developer-protocol step by
     NUMBER must still point at the right step:
       * ``agents/developer.md`` itself cites "`<Investigation_Protocol>` step 2" (the
         spec-read step) — it sat BEFORE the insert, so it must still be step 2.
       * ``docs/specialists.md`` cites "`<Investigation_Protocol>` step 5" as the standards
         load — that pointer must land on the NEW standards step, not drift.
     A future edit that inserts another step ahead of these would silently re-stale the
     pointers; this test trips when it does. (This is exactly hazard (a) the dispatch flagged.)

  2. **Developer↔reviewer index-first PARITY (AC4).** AC4 is "the single developer loads the
     applicable standards profile at dispatch the SAME index-first way the reviewer does
     (depends on NB-380's selective loading)". The sibling net pins that the developer
     *mentions* index-first / applies-to in isolation; this file pins the PARITY that is the
     substance of AC4 — the developer's step cross-references the reviewer's discipline, and
     the two share the load-order vocabulary (read the index first, filter by ``applies-to``,
     honour only ``Accepted``, open a full ADR only when engaged). If a future edit makes the
     developer's load order diverge from the reviewer's, AC4 silently regresses; this fails first.

Deliberately NOT covered (REVIEW/MANUAL-scope, surfaced not silently skipped): whether an LLM
developer, following the prose, ACTUALLY loads the right profile at runtime (untestable without
tautology — the reviewer owns it); and the editorial quality of the rule's wording (AC2 is
`[manual]` — it batches to the PO).

Same convention as the file it supplements and ``test_reviewer_standards_enforcement.py``:
stdlib only (CI runs ``python3 -m unittest discover -s scripts -p 'test_*.py'`` on a bare
Python), UTF-8 reads, whitespace-collapsed so a pin survives line-wrapping.

Run from the repo root:  python scripts/test_developer_standards_load_parity.py
(or collected by `python -m unittest discover -s scripts -p 'test_*.py'`).
"""

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

DEVELOPER = REPO_ROOT / "agents" / "developer.md"
REVIEWER = REPO_ROOT / "agents" / "reviewer.md"
SPECIALISTS = REPO_ROOT / "docs" / "specialists.md"


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def _norm(text: str) -> str:
    """Whitespace-collapse so a content pin survives prose line-wrapping."""
    return " ".join(text.split())


def _investigation_protocol(developer_md: str) -> str:
    """Return just the <Investigation_Protocol> block body (between its open/close tags)."""
    m = re.search(
        r"<Investigation_Protocol>(.*?)</Investigation_Protocol>",
        developer_md,
        re.DOTALL,
    )
    return m.group(1) if m else ""


def _ordered_step_numbers(block: str) -> list:
    """The leading ordered-list numbers of the protocol's top-level steps, in document order.

    Matches a digit-run + '.' at the start of a line (the markdown ordered-list markers the
    protocol uses: `1.`, `2.`, ...). Anchored to line starts so backtick-quoted "step 2"
    references inside prose are not counted.
    """
    return [int(n) for n in re.findall(r"(?m)^\s*(\d+)\.\s", block)]


class ProtocolNumberingIntegrityTest(unittest.TestCase):
    """Hazard (a) — the NB-430 renumber (old 5/6/7 → 6/7/8) must leave the developer's
    <Investigation_Protocol> contiguously numbered, and the step-number cross-references
    that survived the insert must still point at the right step."""

    @classmethod
    def setUpClass(cls):
        cls.dev_raw = _read(DEVELOPER)
        cls.block = _investigation_protocol(cls.dev_raw)

    def test_protocol_block_is_found(self):
        self.assertTrue(
            self.block.strip(),
            "agents/developer.md must contain an <Investigation_Protocol> block.",
        )

    def test_protocol_steps_are_contiguous_from_one(self):
        """A renumber that drops or duplicates a step (the classic insert-and-misnumber bug)
        leaves a gap; the post-NB-430 protocol must read 1..N with no gap and no repeat."""
        nums = _ordered_step_numbers(self.block)
        self.assertTrue(nums, "no ordered steps parsed from <Investigation_Protocol>.")
        self.assertEqual(
            nums,
            list(range(1, len(nums) + 1)),
            "agents/developer.md <Investigation_Protocol> steps must be contiguous 1..N "
            f"with no gap/dupe after the NB-430 insert+renumber; parsed {nums}.",
        )

    def test_new_standards_step_is_step_five(self):
        """NB-430 inserted the standards load as step 5; docs/specialists.md cites it BY
        NUMBER ('<Investigation_Protocol> step 5'), so the standards content must be on the
        step labelled 5 — not drift to another number under a later edit."""
        # The step-5 marker line, then its body up to the step-6 marker.
        m = re.search(r"(?ms)^\s*5\.\s(.*?)^\s*6\.\s", self.block)
        self.assertTrue(m, "could not isolate step 5's body in <Investigation_Protocol>.")
        step5 = _norm(m.group(1))
        self.assertIn(
            "docs/standards/index.json",
            step5,
            "the standards-corpus load must be agents/developer.md step 5 (docs/specialists.md "
            "cites '<Investigation_Protocol> step 5'); if it moved, that pointer is now stale.",
        )

    def test_specialists_pointer_targets_the_standards_step(self):
        """The cross-reference in docs/specialists.md must name step 5 AND the standards step
        in the same breath — so the pointer and its target can't silently diverge."""
        spec = _norm(_read(SPECIALISTS))
        self.assertRegex(
            spec,
            r"<Investigation_Protocol>` step 5",
            "docs/specialists.md must cite the developer's standards load as "
            "'<Investigation_Protocol> step 5' (the step NB-430 added).",
        )

    def test_surviving_step_two_reference_still_resolves(self):
        """agents/developer.md cites '<Investigation_Protocol> step 2' (the spec-read step),
        which sat before the insert and so must remain step 2. Guards the renumber from
        having shifted a reference that should not have moved."""
        # The in-file reference exists ...
        self.assertRegex(
            _norm(self.dev_raw),
            r"<Investigation_Protocol>` step 2",
            "agents/developer.md must still cite '<Investigation_Protocol> step 2'.",
        )
        # ... and step 2 is still the spec / dispatch-envelope read it points at.
        m = re.search(r"(?ms)^\s*2\.\s(.*?)^\s*3\.\s", self.block)
        self.assertTrue(m, "could not isolate step 2's body.")
        step2 = _norm(m.group(1)).lower()
        self.assertTrue(
            "spec" in step2 or "dispatch envelope" in step2 or "issue context" in step2,
            "step 2 must remain the read-your-spec step the 'step 2' reference points at.",
        )


class DeveloperReviewerIndexFirstParityTest(unittest.TestCase):
    """AC4 — the single developer loads the applicable standards profile at dispatch the
    SAME index-first way the reviewer does. Pins the parity (cross-reference + shared
    load-order vocabulary), which is AC4's substance, beyond 'the words appear once'."""

    @classmethod
    def setUpClass(cls):
        cls.dev = _norm(_read(DEVELOPER))
        cls.rev = _norm(_read(REVIEWER))

    def test_developer_cross_references_the_reviewer_discipline(self):
        """AC4 ties the developer's load to the reviewer's ('depends on NB-380's selective
        loading'). The developer's step must point at the reviewer's standards section, so a
        reader sees the two run the same discipline — not two independently-drifting copies."""
        self.assertRegex(
            self.dev,
            r"agents/reviewer\.md.{0,80}(Standards corpus|index first)",
            "agents/developer.md must cross-reference agents/reviewer.md's standards "
            "discipline (AC4 — same index-first load as the reviewer).",
        )

    def test_both_agents_share_the_index_first_load_order(self):
        """The four load-order beats must hold on BOTH agents — read the index, filter by
        applies-to, honour only Accepted, open a full ADR only when engaged. Checked as a set
        across both files so the developer can't claim parity while diverging on a beat."""
        beats = [
            ("read docs/standards/index.json", "docs/standards/index.json"),
            ("filter by applies-to", "applies-to"),
            ("honour only the Accepted set", "Accepted"),
        ]
        for agent_name, text in (("developer", self.dev), ("reviewer", self.rev)):
            for label, token in beats:
                with self.subTest(agent=agent_name, beat=label):
                    self.assertIn(
                        token,
                        text,
                        f"agents/{agent_name}.md must carry the index-first beat "
                        f"'{label}' for AC4 parity.",
                    )
            with self.subTest(agent=agent_name, beat="full ADR only when engaged"):
                self.assertRegex(
                    text,
                    r"full ADR.{0,80}only when|only when.{0,80}assertion is engaged|"
                    r"Open the full ADR only when",
                    f"agents/{agent_name}.md must open a full ADR only when engaged "
                    f"(bounded-context beat) for AC4 parity.",
                )

    def test_specialization_is_data_not_a_new_agent(self):
        """AC1's structural crux, stated as parity with the outcome: a new domain is a new
        standards file, NOT a new agent — the developer file says so itself (the single-agent
        invariant the rest of NB-430 documents)."""
        self.assertRegex(
            self.dev,
            r"data developer when they say data|the kind of developer is \*data\*",
            "agents/developer.md must frame the developer's kind as DATA (specialization by "
            "loaded standards), the single-developer invariant behind AC1.",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
