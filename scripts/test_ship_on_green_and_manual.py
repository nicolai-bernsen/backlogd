"""Regression tests for NB-393 — PO is ideation-only:
tighten `[manual]` semantics + ship-on-green (auto-merge a fully-green verdict).

The change is prose-only across command/skill/doc markdown. Each *testable* AC is
proven by an explicit content assertion on the markdown sources. The two `[test]`
ACs in the problem are:

  1. No prose in `skills/ac/`, `agents/refiner.md`, or `commands/scope.md` still
     presents `[manual]` as appropriate for a judgement/correctness call — stated
     in the problem as a `bash -c 'rg ... && exit 1 || exit 0'` one-liner. `rg` is
     NOT on PATH in the dev sandbox, so that literal command passes *vacuously*
     (rg: command not found → exit 127 → `|| exit 0`). `ForbiddenManualProseTest`
     below re-implements the exact ripgrep pattern with Python's `re` so the
     property is proven **regardless of `rg` availability** — it fails here and in
     CI the moment forbidden prose reappears.
  2. The existing unittest suite stays green — this file joins that suite, so it is
     collected by `python -m unittest discover -s scripts -p "test_*.py"`.

The remaining ship-on-green / `[manual]`-contract ACs are `[review]` (Claude
judgement); the pins here are not a substitute for that read — they anchor the
load-bearing strings so an incidental prose regression in the touched neighbourhood
trips CI (the same guard-the-neighbourhood discipline as
scripts/test_documents_project_form.py).

Run from the repo root:  python scripts/test_ship_on_green_and_manual.py
(or collected by `python -m unittest discover -s scripts -p 'test_*.py'`).
"""

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

AC_SKILL = REPO_ROOT / "skills" / "ac" / "SKILL.md"
REFINER = REPO_ROOT / "agents" / "refiner.md"
SCOPE_CMD = REPO_ROOT / "commands" / "scope.md"
SOLVE_CMD = REPO_ROOT / "commands" / "solve.md"
REVIEW_CMD = REPO_ROOT / "commands" / "review.md"
SHIP_SKILL = REPO_ROOT / "skills" / "solve" / "ship.md"
DRYRUN_SKILL = REPO_ROOT / "skills" / "solve" / "dryrun.md"
HANDOFF_SKILL = REPO_ROOT / "skills" / "solve" / "handoff.md"
REVIEWER_SKILL = REPO_ROOT / "skills" / "reviewer" / "SKILL.md"


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def _norm(text: str) -> str:
    """Whitespace-collapse so a content pin survives prose line-wrapping."""
    return " ".join(text.split())


class ForbiddenManualProseTest(unittest.TestCase):
    """AC (`[test]`): no prose presents `[manual]` as appropriate for a
    judgement/correctness call.

    Re-implements the AC's ripgrep one-liner in Python so it is non-vacuous even
    when `rg` is absent from PATH:

        rg -n -i "manual.{0,40}(decision|sound|correct|consistent|review the .* and confirm)" \\
           skills/ac agents/refiner.md commands/scope.md && exit 1 || exit 0
    """

    # Mirror of the AC's ripgrep pattern. `re.DOTALL` is deliberately NOT set so
    # `.` does not cross newlines — matching ripgrep's default per-line behaviour.
    PATTERN = re.compile(
        r"manual.{0,40}(decision|sound|correct|consistent|review the .* and confirm)",
        re.IGNORECASE,
    )

    def _scan(self, path: pathlib.Path):
        """Return [(lineno, line)] for lines matching the forbidden pattern."""
        hits = []
        for i, line in enumerate(_read(path).splitlines(), start=1):
            if self.PATTERN.search(line):
                hits.append((i, line))
        return hits

    def test_no_forbidden_manual_prose_in_ac_skill(self):
        hits = self._scan(AC_SKILL)
        self.assertEqual(
            hits, [],
            f"skills/ac/SKILL.md still ties `manual` to a judgement word: {hits}",
        )

    def test_no_forbidden_manual_prose_in_refiner(self):
        hits = self._scan(REFINER)
        self.assertEqual(
            hits, [],
            f"agents/refiner.md still ties `manual` to a judgement word: {hits}",
        )

    def test_no_forbidden_manual_prose_in_scope_cmd(self):
        hits = self._scan(SCOPE_CMD)
        self.assertEqual(
            hits, [],
            f"commands/scope.md still ties `manual` to a judgement word: {hits}",
        )

    def test_pattern_actually_bites(self):
        """Guard against a tautological green: prove the regex would FIRE on the
        forbidden shape (so the three empty results above are meaningful). Each
        example keeps the judgement word within the pattern's `manual.{0,40}`
        window, mirroring how the AC's ripgrep alternation is anchored."""
        for forbidden in (
            "[manual] is fine for a soundness decision",
            "use manual when the change is correct per the ADRs",
            "a manual check that the design is consistent with our principles",
            "[manual] review the ADR and confirm the content is right",
        ):
            self.assertTrue(
                self.PATTERN.search(forbidden),
                f"the forbidden-prose regex must match: {forbidden!r}",
            )


class ManualContractTightenedTest(unittest.TestCase):
    """`[manual]` semantics tightened in skills/ac/SKILL.md (`[review]`-judgements)."""

    def test_ac_skill_excludes_soundness_correctness_consistency(self):
        body = _norm(_read(AC_SKILL))
        self.assertIn(
            "Soundness, correctness, and consistency-with-our-standards judgements all route to",
            body,
            "skills/ac/SKILL.md must explicitly route soundness/correctness/consistency to [review]",
        )

    def test_ac_skill_states_in_the_world_test(self):
        body = _norm(_read(AC_SKILL))
        self.assertIn(
            "facts a fresh-context agent genuinely cannot observe in the world",
            body,
            "skills/ac/SKILL.md must restrict [manual] to in-the-world facts",
        )

    def test_ac_skill_states_default_prefer_review(self):
        body = _norm(_read(AC_SKILL))
        self.assertIn(
            "Default to `[review]`.",
            body,
            "skills/ac/SKILL.md must state the default-prefer-[review] rule",
        )

    def test_ac_skill_requires_manual_justification(self):
        body = _norm(_read(AC_SKILL))
        self.assertIn(
            "one-line justification of",
            body,
            "skills/ac/SKILL.md must require a one-line justification on any [manual]",
        )

    def test_refiner_carries_tightened_manual_discipline(self):
        body = _norm(_read(REFINER))
        self.assertIn(
            "rare, earned exception",
            body,
            "agents/refiner.md must call [manual] the rare, earned exception",
        )
        self.assertIn(
            "must carry a one-line justification",
            body,
            "agents/refiner.md must require a one-line justification on any [manual]",
        )

    def test_scope_dispatch_points_at_in_the_world_test(self):
        # Assert on the whitespace-collapsed form so the pin survives prose
        # line-wrapping in the scope dispatch one-liner.
        body = _norm(_read(SCOPE_CMD))
        self.assertIn(
            "a fact only a human can observe in the world",
            body,
            "commands/scope.md step 3 must point the refiner at the in-the-world-facts test",
        )
        # The phrase wraps across a blockquote line in scope.md
        # ("... a peer\n> default alongside"), so the `> ` marker survives the
        # whitespace-collapse. Pin the two halves rather than the joined phrase.
        self.assertIn("is **not** a peer", body)
        self.assertIn(
            "default alongside `[review]`",
            body,
            "commands/scope.md step 3 must state [manual] is not a peer default alongside [review]",
        )


class ShipOnGreenDocumentedTest(unittest.TestCase):
    """Ship-on-green: the loop auto-merges a fully-green verdict with no human gate."""

    def test_ship_skill_exists(self):
        self.assertTrue(
            SHIP_SKILL.is_file(),
            f"skills/solve/ship.md must exist at {SHIP_SKILL}",
        )

    def test_solve_step_8_chains_ship_on_green(self):
        body = _norm(_read(SOLVE_CMD))
        self.assertIn(
            "skills/solve/ship.md",
            body,
            "commands/solve.md must point its final phase at skills/solve/ship.md",
        )
        self.assertIn(
            "ship-on-green",
            body,
            "commands/solve.md must name the ship-on-green phase",
        )

    def test_solve_documents_no_ship_flag_alongside_dryrun(self):
        body = _norm(_read(SOLVE_CMD))
        self.assertIn("--no-ship", body, "commands/solve.md must document --no-ship")
        self.assertIn("--dryrun", body, "commands/solve.md must keep --dryrun documented")
        self.assertIn(
            "BACKLOGD_SHIP_ON_GREEN=0",
            body,
            "commands/solve.md must document the BACKLOGD_SHIP_ON_GREEN=0 env opt-out",
        )

    def test_default_is_ship_on_green(self):
        body = _norm(_read(SOLVE_CMD))
        self.assertIn(
            "default (no flag",
            body,
            "commands/solve.md must state the default (no flag) is ship-on-green",
        )

    def test_merge_condition_stated_exactly(self):
        """The happy-path merge condition string is canonical in review.md step 5 and
        echoed in solve.md + ship.md. Pin the exact phrasing in all three.

        NB-415 migrated the merge-condition vocabulary off the status glyphs (`✅`/`❔`)
        onto the text labels `MET` / `NEEDS-PO` — the same logic in new words, so nothing
        asserts a glyph. The canonical string is now stated label-form."""
        condition = (
            "every AC line MET AND every DoD line MET AND CI green AND zero `[manual]` AND zero NEEDS-PO"
        )
        review = _norm(_read(REVIEW_CMD))
        self.assertIn(
            condition, review,
            "commands/review.md step 5 must state the exact merge condition",
        )
        # solve.md / ship.md echo it (line/DoD wording may wrap — accept the core
        # 'zero [manual] AND zero NEEDS-PO' clause as the anchor in those two).
        for path, name in ((SOLVE_CMD, "commands/solve.md"), (SHIP_SKILL, "skills/solve/ship.md")):
            self.assertIn(
                "zero `[manual]`",
                _norm(_read(path)),
                f"{name} must echo the zero-[manual] clause of the merge condition",
            )
            self.assertIn(
                "zero NEEDS-PO",
                _norm(_read(path)),
                f"{name} must echo the zero-NEEDS-PO clause of the merge condition",
            )

    def test_base_race_guard_present_in_review_step_5(self):
        body = _norm(_read(REVIEW_CMD))
        self.assertIn(
            "gh pr checks", body,
            "commands/review.md must re-confirm CI on the live PR head before merge",
        )
        self.assertIn(
            "mergeable,mergeStateStatus", body,
            "commands/review.md must check PR mergeability before merge",
        )
        self.assertIn(
            "do not auto-rebase and do not merge", body,
            "commands/review.md must state it does not auto-rebase / bails on a stale state",
        )

    def test_merge_gated_on_independent_accepted_rollup(self):
        body = _norm(_read(SHIP_SKILL))
        self.assertIn(
            "gated on the independent reviewer's `accepted` rollup",
            body,
            "skills/solve/ship.md must gate the merge on the independent reviewer's accepted rollup",
        )
        self.assertIn(
            "not the in-session pre-commit gate",
            body,
            "skills/solve/ship.md must distinguish the verdict pass from the pre-commit gate",
        )

    def test_po_interrupted_only_on_non_happy_outcomes(self):
        body = _norm(_read(SHIP_SKILL))
        for needle in ("sent back", "needs you", "blocker"):
            self.assertIn(
                needle, body,
                f"skills/solve/ship.md must distinguish the '{needle}' surface",
            )
        self.assertIn(
            "clean green merge the PO is never interrupted",
            body,
            "skills/solve/ship.md must state the PO is never interrupted on a clean green merge",
        )

    def test_review_remains_independently_invocable(self):
        """The explicit gate is not deleted — /backlogd:review still exists and is
        framed as the standalone re-entry point."""
        self.assertTrue(
            REVIEW_CMD.is_file(),
            "commands/review.md (the explicit gate) must not be deleted",
        )
        ship = _norm(_read(SHIP_SKILL))
        self.assertIn(
            "/backlogd:review",
            ship,
            "skills/solve/ship.md must reference /backlogd:review as the standalone re-entry point",
        )

    def test_dryrun_forbids_ship_phase(self):
        body = _norm(_read(DRYRUN_SKILL))
        self.assertIn(
            "No ship-on-green phase",
            body,
            "skills/solve/dryrun.md must forbid the ship phase under --dryrun",
        )

    def test_handoff_no_longer_ends_run_with_po_merges(self):
        """handoff.md §4 must hand off to the ship phase, not end the run with
        'PO triggers review + merges'."""
        body = _norm(_read(HANDOFF_SKILL))
        self.assertIn(
            "continues to its **ship-on-green** final phase",
            body,
            "skills/solve/handoff.md §4 must hand the run to the ship-on-green phase",
        )


class ReviewerSkillContradictionFixedTest(unittest.TestCase):
    """The skills/reviewer/SKILL.md contradiction is corrected and no longer misleads."""

    def test_old_contradiction_string_is_gone(self):
        body = _read(REVIEWER_SKILL)
        self.assertNotIn(
            "There is no 'pre-commit gate' reviewer dispatch in this model",
            body,
            "skills/reviewer/SKILL.md must no longer carry the pre-commit-gate contradiction",
        )

    def test_two_pass_model_is_stated(self):
        body = _norm(_read(REVIEWER_SKILL))
        self.assertIn(
            "two distinct passes",
            body,
            "skills/reviewer/SKILL.md must describe the two-pass (gate + verdict) model",
        )
        self.assertIn(
            "two triggers, one engine",
            body,
            "skills/reviewer/SKILL.md must describe the auto-chain (two triggers, one engine)",
        )

    def test_three_trust_properties_intact(self):
        body = _norm(_read(REVIEWER_SKILL))
        for prop in ("Fresh context", "Restricted tool grant", "Machine-verifiable check execution"):
            self.assertIn(
                prop, body,
                f"skills/reviewer/SKILL.md must keep the '{prop}' trust property",
            )
        self.assertIn(
            "removes the human *trigger*, never the independent *verification*",
            body,
            "skills/reviewer/SKILL.md must state ship-on-green removes the trigger, not the verification",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
