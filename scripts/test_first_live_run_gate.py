"""Regression tests for NB-424 — first-live-run gate for guide/runbook deliverables.

The change is prose-only across three markdown sources:

  * skills/ac/SKILL.md   — the AC grammar / per-kind contract (source of truth)
  * commands/scope.md    — the refiner dispatch envelope (§3) + the agent:docs hook (§4.5)
  * agents/refiner.md    — the refiner's own AC-drafting guidance (mirror)

Most of NB-424's ACs are `[review]` (Claude judgement against the diff + the shipped
ship-on-green / review semantics + ADR-008). They are not re-litigated here. What *is*
pinned is the one drift risk the developer named: the **named exception class could
silently vanish in a future `[manual]`-section reword**. These content pins anchor the
load-bearing strings so an incidental prose regression in the touched neighbourhood
trips CI — the same guard-the-neighbourhood discipline as
scripts/test_ship_on_green_and_manual.py and scripts/test_adr_008_live_surface_verification.py.

Mapped to NB-424's ACs:

  * AC1 [review] (substance) — the guide/runbook **first-live-run** exception is stated
    as an explicit, named exception class inside the `[manual]` kind of skills/ac/SKILL.md:
    the guide/runbook trigger, the default-`[manual]` first-live-run AC, the standard
    one-line justification, AND the two non-weakening guards (it stays narrow; it does
    NOT touch soundness/correctness ⇒ `[review]`). Pinned by GuideRunbookExceptionInAcSkill.
  * AC2 [review] (substance) — scope.md §3 + §4.5 (`agent:docs` hook) and refiner.md both
    name the exception and point at skills/ac/SKILL.md as the source of truth (no rule
    duplication). Pinned by ScopeNamesExceptionAndAgentDocsHook + RefinerMirrorsException.
  * AC3 [test] — PR #132's guide retrofit is present:
    `grep -q "Verified — first live run" docs/guides/agent-identity-setup.md` exits 0.
    Pinned non-vacuously by GuideRetrofitPresent (a Python content assertion, so it holds
    regardless of `grep` availability — the same anti-vacuity discipline
    test_ship_on_green_and_manual re-implements its `rg` one-liner with).
  * AC4 [review] (testable sliver) — the gate binds **Done, not the merge** by being a
    *plain* `[manual]` AC that rides the EXISTING rails (no new merge-blocker, label, or
    automation). Pinned negatively: the exception block introduces no new gate/label noun
    and the canonical example is a bare `[manual]` bullet (so it inherits the shipped
    In-Review hold + manual-pending surfacing). Pinned by GateBindsDoneNotMergeNoNewMachinery.
  * AC5 [review] (testable sliver) — the execution lane (this rule) cross-references the
    evidence lane (ADR-008) in all three files, framed as distinct (execution gate vs
    live-evidence standard). Pinned by ExecutionAndEvidenceLanesCrossReferenced.

Whether the prose is *sound*, the diff truly *minimal*, the two lanes *non-overlapping*,
and the composition with ship-on-green *correct* stay the reviewer's call ([review]) — the
pins here are not a substitute for that read; they guard the rule + its scope + its
cross-reference against silent drift.

CI runs `python3 -m unittest discover -s scripts -p 'test_*.py'` from the repo root
(see .github/workflows/ci.yml), so this lives in scripts/ as a stdlib unittest. It does
NOT do a git-diff / whole-worktree footprint scan (the NB-418 bug that false-fails every
other unit's local suite).

Run from the repo root:
    python -m unittest scripts.test_first_live_run_gate
    python scripts/test_first_live_run_gate.py
"""

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

AC_SKILL = REPO_ROOT / "skills" / "ac" / "SKILL.md"
SCOPE_CMD = REPO_ROOT / "commands" / "scope.md"
REFINER = REPO_ROOT / "agents" / "refiner.md"
GUIDE = REPO_ROOT / "docs" / "guides" / "agent-identity-setup.md"


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def _norm(text: str) -> str:
    """Whitespace-collapse so a content pin survives prose line-wrapping."""
    return " ".join(text.split())


class GuideRunbookExceptionInAcSkill(unittest.TestCase):
    """AC1 (substance): skills/ac/SKILL.md states the guide/runbook first-live-run AC as a
    named exception class inside the `[manual]` kind — with the standard justification and
    the two non-weakening guards. (Whether the prose is *sound* / well-shaped is [review].)"""

    def test_named_exception_subheading_present(self):
        body = _read(AC_SKILL)
        # The exception is an explicit, *named* sub-section under the `[manual]` kind —
        # not a buried aside. Pin the heading shape (a #### sub-block naming first-live-run).
        self.assertRegex(
            body,
            re.compile(
                r"^#{3,4}\s+.*(one named exception|first-live-run|first live run)",
                re.MULTILINE,
            ),
            "skills/ac/SKILL.md must carry an explicit named sub-section for the "
            "guide/runbook first-live-run exception inside the [manual] kind.",
        )

    def test_guide_runbook_trigger_named(self):
        body = _norm(_read(AC_SKILL))
        self.assertIn(
            "guide/runbook-class deliverable",
            body,
            "skills/ac/SKILL.md must name the trigger as a guide/runbook-class deliverable.",
        )
        # The class is anchored to a concrete file-shape so it is recognisable, not vague.
        self.assertIn(
            "docs/guides/*-setup.md",
            body,
            "skills/ac/SKILL.md must anchor the guide class to docs/guides/*-setup.md.",
        )

    def test_default_manual_first_live_run_ac_stated(self):
        body = _norm(_read(AC_SKILL))
        self.assertIn(
            "carries a `[manual]`",
            body,
            "skills/ac/SKILL.md must state a guide/runbook problem carries a [manual] AC "
            "by default.",
        )
        self.assertIn(
            "One real end-to-end execution of this guide by a human",
            body,
            "skills/ac/SKILL.md must phrase the first-live-run AC as one real end-to-end "
            "execution of this guide by a human, defects fed back into the guide.",
        )
        self.assertIn(
            "defects fed back into",
            body,
            "skills/ac/SKILL.md must require defects be fed back into the guide.",
        )

    def test_standard_justification_satisfies_rule_2(self):
        body = _norm(_read(AC_SKILL))
        self.assertIn(
            "no fresh-context agent can",
            body,
            "skills/ac/SKILL.md must carry the standard one-line justification (no "
            "fresh-context agent can perform the human walk-through) for the exception.",
        )

    def test_exception_does_not_weaken_manual_is_rare(self):
        """The exception must be framed as the ONE standing exception — `[manual]` stays
        the rare case for everything else (the exception is explicitly narrow)."""
        body = _norm(_read(AC_SKILL))
        self.assertIn(
            "exactly **one** standing exception",
            body,
            "skills/ac/SKILL.md must frame this as exactly one standing exception (so "
            "[manual]-is-rare survives for everything else).",
        )
        self.assertIn(
            "It does **not** widen",
            body,
            "skills/ac/SKILL.md must state the exception does not widen [manual] for "
            "anything else.",
        )

    def test_exception_does_not_weaken_soundness_routes_to_review(self):
        """The exception must explicitly NOT touch the soundness/correctness ⇒ [review]
        rule — a guide can still carry [review] ACs for whether its prose is right."""
        body = _norm(_read(AC_SKILL))
        self.assertIn(
            "does **not** touch the rule above that a",
            body,
            "skills/ac/SKILL.md must state the exception does not touch the "
            "soundness/correctness/consistency ⇒ [review] rule.",
        )


class ScopeNamesExceptionAndAgentDocsHook(unittest.TestCase):
    """AC2: commands/scope.md §3 (refiner dispatch) names the exception + points at
    skills/ac/SKILL.md as source of truth, and §4.5 names `agent:docs` as the routing
    hook. (Whether the dispatch reads well is [review].)"""

    def test_scope_dispatch_names_the_exception(self):
        body = _norm(_read(SCOPE_CMD))
        self.assertIn(
            "guide or runbook",
            body,
            "commands/scope.md §3 must name the guide/runbook exception in the refiner "
            "dispatch envelope.",
        )
        self.assertIn(
            "first-live-run",
            body,
            "commands/scope.md must name the first-live-run AC.",
        )
        self.assertIn(
            "one real end-to-end execution of this guide",
            body,
            "commands/scope.md must spell out the first-live-run AC text.",
        )

    def test_scope_points_at_ac_skill_as_source_of_truth(self):
        """No rule duplication: scope.md must defer to skills/ac/SKILL.md as the source of
        truth ('do not restate it') rather than re-stating the full rule."""
        body = _norm(_read(SCOPE_CMD))
        self.assertIn(
            "`skills/ac/SKILL.md` carries the full rule",
            body,
            "commands/scope.md must point at skills/ac/SKILL.md as the source of truth "
            "for the full rule.",
        )
        self.assertRegex(
            body,
            r"do not restate it",
            "commands/scope.md must say not to restate the rule (no duplication).",
        )

    def test_scope_4_5_names_agent_docs_as_the_hook(self):
        """AC2: §4.5 names agent:docs as the recognised routing hook for the
        guide/runbook first-live-run AC."""
        body = _norm(_read(SCOPE_CMD))
        self.assertIn(
            "`agent:docs` is also the **recognised hook for",
            body,
            "commands/scope.md §4.5 must name agent:docs as the recognised hook for the "
            "guide/runbook first-live-run AC.",
        )
        # Tie the hook to the source-of-truth AC, not a re-stated rule (the phrase wraps
        # across lines in §4.5; assert on the whitespace-collapsed form).
        self.assertIn(
            "first-live-run AC from `skills/ac/SKILL.md`",
            body,
            "commands/scope.md §4.5 must route via the first-live-run AC from "
            "skills/ac/SKILL.md (the source of truth).",
        )


class RefinerMirrorsException(unittest.TestCase):
    """AC2: agents/refiner.md mirrors the exception in its AC-drafting guidance and points
    at skills/ac/SKILL.md as source of truth (no duplication)."""

    def test_refiner_names_the_exception(self):
        body = _norm(_read(REFINER))
        self.assertIn(
            "The one standing `[manual]` exception",
            body,
            "agents/refiner.md must name the one standing [manual] exception (the "
            "guide/runbook first-live-run AC).",
        )
        self.assertIn(
            "guide or runbook",
            body,
            "agents/refiner.md must name the guide/runbook trigger.",
        )
        self.assertIn(
            "first-live-run",
            body,
            "agents/refiner.md must name the first-live-run AC.",
        )

    def test_refiner_points_at_ac_skill_not_restating(self):
        body = _norm(_read(REFINER))
        self.assertIn(
            "see `skills/ac/SKILL.md` for the full rule",
            body,
            "agents/refiner.md must point at skills/ac/SKILL.md for the full rule.",
        )
        self.assertIn(
            "source of truth — do not restate it",
            body,
            "agents/refiner.md must defer to skills/ac/SKILL.md as source of truth and "
            "not restate the rule.",
        )


class GuideRetrofitPresent(unittest.TestCase):
    """AC3 [test]: PR #132's guide retrofit is present —
    `grep -q "Verified — first live run" docs/guides/agent-identity-setup.md` exits 0.

    Re-implemented as a Python content assertion so it is non-vacuous regardless of
    whether `grep` is on PATH (the anti-vacuity discipline test_ship_on_green_and_manual
    applies to its `rg` one-liner)."""

    def test_verified_first_live_run_blockquote_present(self):
        self.assertTrue(
            GUIDE.is_file(),
            f"AC3: the guide must exist at {GUIDE}.",
        )
        self.assertIn(
            "Verified — first live run",
            _read(GUIDE),
            "AC3: docs/guides/agent-identity-setup.md must carry the "
            "'Verified — first live run' blockquote (PR #132 retrofit) — "
            "`grep -q \"Verified — first live run\" ...` must exit 0.",
        )


class GateBindsDoneNotMergeNoNewMachinery(unittest.TestCase):
    """AC4 (testable sliver): the gate binds **Done, not the merge** by being a *plain*
    `[manual]` AC that rides the existing rails — no new merge-blocker, label, or
    automation. (Whether the diff is truly minimal / composes correctly is [review].)"""

    # The exception sub-block in skills/ac/SKILL.md, from its #### heading to the next
    # heading. The new rule must not invent machinery *inside* its own block.
    def _exception_block(self) -> str:
        body = _read(AC_SKILL)
        start = body.find("#### The one named exception")
        self.assertNotEqual(
            start, -1,
            "skills/ac/SKILL.md must carry the named first-live-run exception block.",
        )
        rest = body[start + 1:]
        nxt = rest.find("\n#")  # next heading of any level
        return rest if nxt == -1 else rest[:nxt]

    def test_exception_canonical_example_is_a_plain_manual_bullet(self):
        """The exception's canonical AC is a bare `[manual]` bullet — so it inherits the
        shipped In-Review hold + manual-pending surfacing, binding Done not the merge."""
        block = _norm(self._exception_block())
        self.assertIn(
            "- [ ] [manual] One real end-to-end execution",
            block,
            "the exception's canonical example must be a plain `[manual]` first-live-run "
            "bullet (it rides the existing [manual] rails — no bespoke gate).",
        )

    def test_exception_block_invents_no_new_machinery(self):
        """No new merge-blocker / label / automation noun introduced by the rule. A future
        edit that bolted on a bespoke gate ('new label', 'merge-blocker', 'CI gate') would
        trip here — the gate must bind Done via the EXISTING manual rails only."""
        block = self._exception_block().lower()
        for forbidden in (
            "new label",
            "new merge-blocker",
            "new merge blocker",
            "merge blocker",
            "blocks the merge",
            "blocks merge",
            "new automation",
            "ci gate",
        ):
            self.assertNotIn(
                forbidden,
                block,
                f"the first-live-run exception must invent no new machinery; found "
                f"a {forbidden!r} noun in the exception block (AC4: it binds Done via the "
                "existing [manual] rails, not a new merge-blocker/label/automation).",
            )


class ExecutionAndEvidenceLanesCrossReferenced(unittest.TestCase):
    """AC5 (testable sliver): the execution lane (this rule) and the evidence lane
    (ADR-008) cross-reference each other, framed as distinct, in all three files.
    (Whether they are truly non-overlapping is [review].)"""

    ADR_LINK = "ADR-008-live-surface-verification.md"

    def test_ac_skill_cross_references_adr008_as_distinct_lane(self):
        body = _norm(_read(AC_SKILL))
        self.assertIn(
            self.ADR_LINK,
            body,
            "skills/ac/SKILL.md must link ADR-008 (the evidence lane).",
        )
        self.assertIn(
            "execution",
            body,
            "skills/ac/SKILL.md must frame this rule as the execution gate.",
        )
        # The two lanes are distinguished, not conflated.
        self.assertIn(
            "evidence behind an external-surface claim",
            body,
            "skills/ac/SKILL.md must distinguish ADR-008 as the evidence-behind-a-claim "
            "lane, distinct from this execution gate.",
        )

    def test_scope_cross_references_adr008_as_distinct_lane(self):
        body = _norm(_read(SCOPE_CMD))
        self.assertIn(
            self.ADR_LINK,
            body,
            "commands/scope.md must link ADR-008.",
        )
        self.assertIn(
            "This is the **execution** gate, distinct from",
            body,
            "commands/scope.md must frame the rule as the execution gate distinct from "
            "ADR-008.",
        )

    def test_refiner_cross_references_adr008_as_distinct_lane(self):
        body = _norm(_read(REFINER))
        self.assertIn(
            self.ADR_LINK,
            body,
            "agents/refiner.md must link ADR-008.",
        )
        self.assertIn(
            "It is the **execution** gate and is distinct",
            body,
            "agents/refiner.md must frame the rule as the execution gate distinct from "
            "ADR-008's live-evidence standard.",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
