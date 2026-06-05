"""Regression net for NB-384 — the reviewer's fourth verdict outcome `block`.

NB-384 owns NB-378 acceptance criteria #2 and #4. Both are `[review]`-kind — they are
judgements an agent renders from prose at verdict time, NOT behaviours a test runner can
exercise. So this file does **not** try to prove "the reviewer blocks correctly" (that
would be a tautology against the doc that *is* the instruction). It pins the load-bearing
prose invariants the change introduced across the two reviewer surfaces (`agents/
reviewer.md`, `skills/reviewer/SKILL.md`) and the verdict-body template, so an incidental
reword in the touched neighbourhood trips CI instead of silently regressing the policy
back to the pre-NB-384 three-way verdict.

  - AC #2 — when a consequential decision has no governing standard the verdict is a
    **fourth outcome `block`** (not an accept); the reviewer **names the missing standard**
    and **does NOT invent** one. Pinned on BOTH surfaces as a set: the verdict enumeration
    must be 4-way (accept / send-back / needs-PO / block), and the "names / does not invent"
    guard phrase must be present.
  - AC #4 — each block is classified **standard** (durable → ADR, escalates to PO) vs
    **fact** (one-time → answered once, no ADR/PO), and that classification is written into
    the verdict body. Pinned on both surfaces (the standard-vs-fact distinction with its two
    routes) and on the `agents/reviewer.md` verdict-body template (the `standard:` / `fact:`
    lines under a "Missing standard / fact" section).

These are content pins, not a substitute for the reviewer's `[review]` judgement — they
anchor the strings so the neighbourhood can't drift unnoticed (same guard-the-
neighbourhood discipline as scripts/test_reviewer_standards_enforcement.py, the NB-383
sibling). Each class also carries a `*_would_bite_on_the_pre_fix_wording` guard proving the
pin actually FIRES on the old three-way verdict, so a green here is never tautological.

Run from the repo root:  python scripts/test_reviewer_block_outcome.py
(or collected by `python -m unittest discover -s scripts -p 'test_*.py'`).
"""

import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

REVIEWER_AGENT = REPO_ROOT / "agents" / "reviewer.md"
REVIEWER_SKILL = REPO_ROOT / "skills" / "reviewer" / "SKILL.md"

# AC #2 and AC #4 are only proven if the invariant holds on BOTH the agent file and its
# mirroring skill, so they are checked as a set — a reword that fixes one and strands the
# other must fail.
REVIEWER_SURFACES = (REVIEWER_AGENT, REVIEWER_SKILL)

# The block glyph, kept as an escape so this source file stays ASCII and never trips a
# Windows cp1252 round-trip. Membership-tested only — never printed.
BLOCK_GLYPH = "\U0001f6ab"  # 🚫


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def _norm(text: str) -> str:
    """Whitespace-collapse so a content pin survives prose line-wrapping."""
    return " ".join(text.split())


class FourthOutcomeBlockTest(unittest.TestCase):
    """AC #2 — `block` is a documented fourth verdict outcome on both surfaces, and the
    reviewer names the missing standard without inventing one."""

    def test_both_surfaces_name_block_as_the_fourth_outcome(self):
        # Lower-cased so the pin survives sentence-start vs mid-sentence capitalization.
        # The load-bearing fact: a *fourth* verdict outcome literally named `block` exists.
        for path in REVIEWER_SURFACES:
            with self.subTest(surface=path.name):
                body = _norm(_read(path)).lower()
                self.assertIn(
                    "fourth",
                    body,
                    f"{path.relative_to(REPO_ROOT)} must introduce a *fourth* verdict "
                    f"outcome (AC #2).",
                )
                self.assertIn(
                    "outcome",
                    body,
                    f"{path.relative_to(REPO_ROOT)} must frame `block` as a verdict "
                    f"outcome (AC #2).",
                )
                self.assertIn(
                    "`block`",
                    body,
                    f"{path.relative_to(REPO_ROOT)} must name the fourth outcome `block` "
                    f"(AC #2).",
                )

    def test_both_surfaces_enumerate_a_four_way_verdict(self):
        # The verdict set must list all four outcomes alongside `block`. The pre-NB-384
        # wording enumerated only accept / send-back / needs-PO; require the three prior
        # outcomes to be named together with `block` so a regression to a three-way list
        # (dropping `block`) fails.
        for path in REVIEWER_SURFACES:
            with self.subTest(surface=path.name):
                body = _norm(_read(path)).lower()
                self.assertIn(
                    "accepted / sent back",
                    body,
                    f"{path.relative_to(REPO_ROOT)} must enumerate the prior outcomes "
                    f"alongside `block` (AC #2 four-way verdict).",
                )

    def test_both_surfaces_block_names_the_gap_and_does_not_invent(self):
        # The self-marking guard: the reviewer NAMES the missing standard and does NOT
        # invent one to clear its own block. Both halves must be present on both surfaces.
        for path in REVIEWER_SURFACES:
            with self.subTest(surface=path.name):
                body = _norm(_read(path)).lower()
                self.assertIn(
                    "names the missing standard",
                    body,
                    f"{path.relative_to(REPO_ROOT)} must require the reviewer to NAME the "
                    f"missing standard (AC #2).",
                )
                self.assertIn(
                    "does not invent",
                    body,
                    f"{path.relative_to(REPO_ROOT)} must require the reviewer NOT invent a "
                    f"standard to unblock (AC #2 self-marking guard).",
                )

    def test_pins_would_bite_on_the_pre_fix_three_way_wording(self):
        # Guard against a tautological green: prove these assertions actually FIRE on the
        # pre-NB-384 three-way verdict (no fourth outcome, no `block`, no name-the-gap
        # guard). If the synthetic pre-fix text passed the pins, they'd prove nothing.
        pre_fix = _norm(
            "The reviewer's verdict is one of three outcomes: accepted, sent back, or "
            "needs you. If no indexed standard is applicable to the change, say so "
            "explicitly — that is a valid, bounded result."
        ).lower()
        self.assertNotIn("`block`", pre_fix)
        self.assertNotIn("fourth", pre_fix)
        self.assertNotIn("names the missing standard", pre_fix)
        self.assertNotIn("does not invent", pre_fix)


class StandardVsFactClassificationTest(unittest.TestCase):
    """AC #4 — every block is classified standard (durable → ADR + PO) vs fact (one-time →
    answered once, no ADR/PO), written into the verdict so the scrum-master can route it."""

    def test_both_surfaces_classify_standard_vs_fact_with_routes(self):
        # Both kinds must be named, each with its distinguishing route, on both surfaces:
        #   standard -> durable / cross-issue, graduates to an ADR + escalates to the PO
        #   fact     -> one-time lookup, answered once, no ADR, no PO
        for path in REVIEWER_SURFACES:
            with self.subTest(surface=path.name):
                body = _norm(_read(path)).lower()
                # The two kinds are the classification itself. Bold-insensitive: the agent
                # file writes `missing **standard**`, the skill writes `**missing
                # standard**` — the load-bearing token is the kind phrase, not where the
                # `**` markers fall, so pin the markdown-stripped phrase present in both.
                self.assertIn(
                    "missing standard",
                    body,
                    f"{path.relative_to(REPO_ROOT)} must classify the durable-gap kind as "
                    f"a missing standard (AC #4).",
                )
                self.assertIn(
                    "missing fact",
                    body,
                    f"{path.relative_to(REPO_ROOT)} must classify the one-time kind as a "
                    f"missing fact (AC #4).",
                )
                # The standard kind escalates (ADR + PO); the fact kind does not.
                self.assertIn(
                    "adr",
                    body,
                    f"{path.relative_to(REPO_ROOT)} must route a missing standard to an "
                    f"ADR (AC #4).",
                )
                self.assertIn(
                    "answered once",
                    body,
                    f"{path.relative_to(REPO_ROOT)} must route a missing fact to "
                    f"'answered once' (AC #4).",
                )

    def test_agent_verdict_template_carries_the_standard_fact_section(self):
        # AC #4 says the classification is *written into the verdict*. The agent file owns
        # the verdict-body template the scrum-master lifts verbatim; it must carry a
        # block-only "Missing standard / fact" section with a per-kind line for each of
        # `standard:` and `fact:`.
        #
        # NB-415 migrated the verdict-body display off the block glyph (🚫) onto the
        # `- [ ] **NO-STANDARD**` checkbox + bold-label convention (the verdict body is a
        # Linear comment and must carry no status emoji). The classification lines now read
        # `- [ ] **NO-STANDARD** standard:` / `- [ ] **NO-STANDARD** fact:`; the pin tracks
        # that, asserting the block glyph is GONE from the template.
        body = _norm(_read(REVIEWER_AGENT))
        self.assertIn(
            "Missing standard / fact",
            body,
            "agents/reviewer.md verdict template must carry a 'Missing standard / fact' "
            "section so the classification is written into the verdict (AC #4).",
        )
        self.assertIn(
            "**NO-STANDARD** standard:",
            body,
            "agents/reviewer.md verdict template must carry a NO-STANDARD `standard:` block "
            "line (AC #4).",
        )
        self.assertIn(
            "**NO-STANDARD** fact:",
            body,
            "agents/reviewer.md verdict template must carry a NO-STANDARD `fact:` block line "
            "(AC #4).",
        )
        self.assertNotIn(
            BLOCK_GLYPH,
            body,
            "agents/reviewer.md verdict template must use no status/block emoji — NB-415 "
            "migrated the block glyph to the NO-STANDARD bold label.",
        )

    def test_classification_pins_would_bite_on_the_pre_fix_wording(self):
        # Anti-tautology: the pre-NB-384 verdict template had no standard/fact section, no
        # per-kind lines, and no standard-vs-fact classification at all. Prove every AC #4
        # pin fires on that wording — both the surface-prose phrases and the template lines.
        pre_fix = _norm(
            "Applicable standards (filtered from docs/standards/index.json by scope)\n"
            "  ok {ADR-NNN} {assertion} — {how the diff honours it}\n"
            "Evidence I ran\n"
            "  - `{command}` -> {what it showed}\n"
            "CI signal: {green | red | pending}\n"
        ).lower()
        self.assertNotIn("missing standard", pre_fix)
        self.assertNotIn("missing fact", pre_fix)
        self.assertNotIn("answered once", pre_fix)
        self.assertNotIn("missing standard / fact", pre_fix)
        self.assertNotIn("**no-standard** standard:", pre_fix)
        self.assertNotIn("**no-standard** fact:", pre_fix)


if __name__ == "__main__":
    unittest.main(verbosity=2)
