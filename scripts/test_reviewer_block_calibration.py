"""Regression net for NB-386 — calibrating the reviewer's `block` by reversibility ×
blast-radius (and the AC #8 scope deferral to ADR-004).

NB-386 owns NB-378 acceptance criteria #3 and #8. Both are typed `[manual]` / `[review]`
— they are judgements (the PO reads the threshold on a worked example; the reviewer
renders code-vs-general scope from prose at verdict time), NOT behaviours a test runner
can exercise. So this file does **not** try to prove "the reviewer calibrates correctly"
(that would be a tautology against the doc that *is* the policy). It pins the load-bearing
prose invariants NB-386 introduced across the two reviewer surfaces (`agents/reviewer.md`
owns the operational calibration + worked examples; `skills/reviewer/SKILL.md` states the
threshold exists and why), so an incidental reword in the touched neighbourhood trips CI
instead of silently regressing the calibration back to the pre-NB-386 always-block (or
no-threshold) behaviour that would make a blank repo unusable.

  - AC #3 — the `block` fires by a **reversibility × blast-radius** calibration: a
    **one-way door** (irreversible AND wide blast-radius) blocks; a **two-way door**
    (reversible OR narrow) records a **flagged assumption** and **proceeds**; and the
    **blank / empty-corpus repo stays usable** (the bootstrap degrades gracefully rather
    than firing fifty blocking questions on issue #1). Pinned on the agent doc (the policy
    owner: the calibration heading, both axes, the conjunction rule, the flag-and-proceed
    branch, the blank-repo bootstrap) AND, for the parts the trust model owns, on the
    skill (the threshold exists + the blank-repo rationale).
  - AC #8 — the code-vs-general scope question is **owned by ADR-004**, *named* as the
    dependency and **not re-decided** here. Pinned on the agent doc's scope blockquote
    (ADR-004 named as owner + the "does not re-open / re-decide" guard).

These are content pins, not a substitute for the reviewer's `[manual]`/`[review]`
judgement — they anchor the strings so the neighbourhood can't drift unnoticed (same
guard-the-neighbourhood discipline as scripts/test_reviewer_block_outcome.py and
scripts/test_reviewer_standards_enforcement.py, the NB-383/NB-384 siblings). Each class
also carries a `*_would_bite_on_the_pre_fix_wording` guard proving the pin actually FIRES
on the pre-NB-386 wording (no calibration, always-block, no ADR-004 scope), so a green
here is never tautological.

Run from the repo root:  python scripts/test_reviewer_block_calibration.py
(or collected by `python -m unittest discover -s scripts -p 'test_*.py'`).
"""

import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

REVIEWER_AGENT = REPO_ROOT / "agents" / "reviewer.md"
REVIEWER_SKILL = REPO_ROOT / "skills" / "reviewer" / "SKILL.md"

# The block glyph, kept as an escape so this source file stays ASCII and never trips a
# Windows cp1252 round-trip. Not used in an assertion here, kept for parity with the
# sibling pin and in case the calibration grows a glyphed line.
BLOCK_GLYPH = "\U0001f6ab"  # 🚫

# Both surfaces carry the reversibility × blast-radius framing. The parts the *trust
# model* owns (the threshold exists; the blank-repo bootstrap rationale) are checked as a
# set across both files; the *operational* calibration (worked rule + examples) and the
# AC #8 scope blockquote live only on the agent doc, which owns the policy.
REVIEWER_SURFACES = (REVIEWER_AGENT, REVIEWER_SKILL)


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def _norm(text: str) -> str:
    """Whitespace-collapse so a content pin survives prose line-wrapping."""
    return " ".join(text.split())


class ReversibilityBlastRadiusCalibrationTest(unittest.TestCase):
    """AC #3 — the `block` is gated by a reversibility × blast-radius calibration, present
    on both reviewer surfaces (the axes framing is mirrored across agent doc + skill)."""

    def test_both_surfaces_frame_the_calibration_as_reversibility_x_blast_radius(self):
        # The load-bearing framing: *when* a missing standard blocks is a
        # reversibility × blast-radius judgement. Both surfaces must carry both axes by
        # name so a reword that drops the calibration (and silently reverts to
        # always-block) fails on either file.
        for path in REVIEWER_SURFACES:
            with self.subTest(surface=path.name):
                body = _norm(_read(path)).lower()
                self.assertIn(
                    "reversibility",
                    body,
                    f"{path.relative_to(REPO_ROOT)} must name reversibility as a "
                    f"calibration axis (AC #3).",
                )
                self.assertIn(
                    "blast-radius",
                    body,
                    f"{path.relative_to(REPO_ROOT)} must name blast-radius as a "
                    f"calibration axis (AC #3).",
                )

    def test_both_surfaces_use_the_one_way_two_way_door_test(self):
        # The threshold is expressed as the one-way / two-way door test. Both the agent
        # doc and the trust model lean on this metaphor; require both door kinds named on
        # both surfaces.
        for path in REVIEWER_SURFACES:
            with self.subTest(surface=path.name):
                body = _norm(_read(path)).lower()
                self.assertIn(
                    "one-way door",
                    body,
                    f"{path.relative_to(REPO_ROOT)} must name the one-way door (the "
                    f"blocking case) (AC #3).",
                )
                self.assertIn(
                    "two-way door",
                    body,
                    f"{path.relative_to(REPO_ROOT)} must name the two-way door (the "
                    f"proceed case) (AC #3).",
                )

    def test_agent_doc_states_the_conjunction_rule_one_way_blocks(self):
        # The policy owner (agents/reviewer.md) must state the *conjunction*: only an
        # irreversible AND wide-blast-radius decision is a one-way door that blocks. A
        # reword that loosens this to "irreversible OR wide" would over-block and break
        # the blank-repo guarantee, so pin the AND.
        body = _norm(_read(REVIEWER_AGENT)).lower()
        self.assertIn(
            "irreversible and wide blast-radius",
            body,
            "agents/reviewer.md must state the one-way-door block rule as the "
            "*conjunction* irreversible AND wide blast-radius (AC #3).",
        )

    def test_agent_doc_states_two_way_door_flags_and_proceeds(self):
        # The other half of the rule: a two-way door (reversible OR narrow) does NOT
        # block — it records a flagged assumption and proceeds. Both the "flag" and the
        # "proceed" must survive, or the calibration collapses back to always-block.
        body = _norm(_read(REVIEWER_AGENT)).lower()
        self.assertIn(
            "flag and proceed",
            body,
            "agents/reviewer.md must give the two-way-door branch as flag-and-proceed "
            "(AC #3).",
        )
        self.assertIn(
            "flagged assumption",
            body,
            "agents/reviewer.md must record a *flagged assumption* on the proceed branch "
            "(AC #3).",
        )

    def test_pins_would_bite_on_pre_fix_always_block_wording(self):
        # Anti-tautology: prove these assertions actually FIRE on a pre-NB-386 wording
        # with no calibration at all (every ungoverned consequential decision blocks, no
        # door test, no flag-and-proceed). If the synthetic pre-fix text passed the pins,
        # they would prove nothing.
        pre_fix = _norm(
            "When a consequential decision has no governing Accepted standard, the "
            "verdict is a block. Name the missing standard and do not invent one."
        ).lower()
        self.assertNotIn("reversibility", pre_fix)
        self.assertNotIn("blast-radius", pre_fix)
        self.assertNotIn("one-way door", pre_fix)
        self.assertNotIn("two-way door", pre_fix)
        self.assertNotIn("irreversible and wide blast-radius", pre_fix)
        self.assertNotIn("flag and proceed", pre_fix)


class BlankRepoStaysUsableTest(unittest.TestCase):
    """AC #3 — the calibration's *reason for being*: a blank / empty-corpus repo stays
    usable because the bootstrap degrades gracefully (proceed-with-a-flag, not block)."""

    def test_both_surfaces_promise_a_blank_repo_stays_usable(self):
        # The headline guarantee. The agent doc phrases it "a blank or standards-light
        # repo stays usable"; the trust model phrases it "keeps a blank repo usable". The
        # token common to both, after normalization+lowercasing, is "blank" + "repo" +
        # "usable" — pin all three so neither surface can drop the guarantee.
        for path in REVIEWER_SURFACES:
            with self.subTest(surface=path.name):
                body = _norm(_read(path)).lower()
                self.assertIn(
                    "blank",
                    body,
                    f"{path.relative_to(REPO_ROOT)} must promise the *blank* repo stays "
                    f"usable (AC #3).",
                )
                self.assertIn(
                    "usable",
                    body,
                    f"{path.relative_to(REPO_ROOT)} must promise the blank repo stays "
                    f"*usable* (AC #3).",
                )

    def test_both_surfaces_cite_the_empty_corpus_graceful_bootstrap(self):
        # The mechanism behind the guarantee: with an empty corpus almost everything is
        # ungoverned, so the bootstrap must *degrade gracefully* (default to proceed). The
        # phrase "degrade(s) gracefully" + "bootstrap" appears on both surfaces.
        for path in REVIEWER_SURFACES:
            with self.subTest(surface=path.name):
                body = _norm(_read(path)).lower()
                self.assertIn(
                    "bootstrap",
                    body,
                    f"{path.relative_to(REPO_ROOT)} must name the empty-corpus bootstrap "
                    f"(AC #3).",
                )
                self.assertIn(
                    "degrade",
                    body,
                    f"{path.relative_to(REPO_ROOT)} must say the bootstrap degrades "
                    f"gracefully (AC #3) — 'degrade' covers both 'degrade' and "
                    f"'degrades'.",
                )

    def test_pins_would_bite_on_pre_fix_no_bootstrap_wording(self):
        # Anti-tautology: a pre-NB-386 wording made no promise about a blank repo and
        # named no graceful bootstrap. Prove the blank-repo / bootstrap pins fire on it.
        pre_fix = _norm(
            "The reviewer blocks any consequential decision that no Accepted standard "
            "governs."
        ).lower()
        self.assertNotIn("blank", pre_fix)
        self.assertNotIn("bootstrap", pre_fix)
        self.assertNotIn("degrade", pre_fix)


class ScopeDeferredToAdr004Test(unittest.TestCase):
    """AC #8 — the code-vs-general scope question is owned by ADR-004; this unit *names*
    the dependency and does **not** re-decide it."""

    def test_agent_doc_names_adr_004_as_owner_of_code_vs_general(self):
        # The agent doc's scope blockquote must name ADR-004 as the owner of the
        # "code scrum vs general problem-solving" identity question. Pin both the ADR id
        # and the code-vs-general subject so a reword that drops either fails.
        body = _norm(_read(REVIEWER_AGENT))
        self.assertIn(
            "ADR-004",
            body,
            "agents/reviewer.md must name ADR-004 as owner of the code-vs-general scope "
            "question (AC #8).",
        )
        lowered = body.lower()
        self.assertIn(
            "code-vs-general question",
            lowered,
            "agents/reviewer.md must name the code-vs-general question that ADR-004 "
            "owns (AC #8).",
        )

    def test_agent_doc_does_not_re_decide_the_scope_here(self):
        # The crux of AC #8: this unit references the owner, it does not re-decide. The
        # blockquote must carry the "does not re-open" / "does not re-decide" guard so a
        # reword can't quietly turn the reference into a re-litigation.
        body = _norm(_read(REVIEWER_AGENT)).lower()
        self.assertTrue(
            ("does not re-open" in body) or ("does not re-decide" in body),
            "agents/reviewer.md scope note must state it does NOT re-open / re-decide the "
            "code-vs-general question — it names ADR-004 as owner (AC #8).",
        )

    def test_pins_would_bite_on_pre_fix_no_scope_reference(self):
        # Anti-tautology: a pre-NB-386 wording carried no ADR-004 scope blockquote at all.
        # Prove the AC #8 pins fire on a synthetic wording that omits the reference.
        pre_fix = _norm(
            "Calibrate the block by reversibility and blast-radius; a one-way door "
            "blocks, a two-way door proceeds with a flagged assumption."
        )
        self.assertNotIn("ADR-004", pre_fix)
        self.assertNotIn("code-vs-general question", pre_fix.lower())
        self.assertNotIn("does not re-open", pre_fix.lower())
        self.assertNotIn("does not re-decide", pre_fix.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
