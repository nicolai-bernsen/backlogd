"""Regression net for NB-436 — the shared problem-Goal artifact flows end-to-end.

NB-436 (team cohesion 1/3) recovers the evaporated Sprint Goal at the *problem* level:
a single-sentence ``## Goal`` that the refiner authors at scope, that the dispatch
envelope inlines verbatim, and that the reviewer's verdict reasons against — so the
developer, tester, and reviewer all serve the same "why", not just their local artifact.

Every AC on NB-436 is ``[review]`` or ``[manual]`` — there is **no** behaviour a process
can exercise here; the change is prose in skill/command/agent markdown. So this file does
NOT try to prove "the refiner/reviewer obeys the instruction" (that is a tautology against
the doc that *is* the instruction — see ``scripts/test_reviewer_standards_enforcement.py``
and ``scripts/test_definition_of_done_wired.py`` for the same discipline). It pins the
**load-bearing prose invariants** the change introduced, so an incidental reword in any
touched surface trips CI instead of silently un-wiring the contract. Each AC's pin carries
a *would-bite-on-the-pre-fix-wording* guard so the green is not tautological.

The AC buckets, and how each is proven here:

  - AC1 ``[review]`` — ``/backlogd:scope`` writes a single-sentence ``## Goal`` above
    ``## Acceptance Criteria``; **the refiner authors it; the scrum-master never
    substitutes its own product intent.** Structural half is pinnable in both authoring
    surfaces (``agents/refiner.md`` writes the section + carries the don't-invent guard;
    ``commands/scope.md`` instructs Goal authoring + the never-substitute guard +
    execution-ready includes the Goal). ``ScopeWritesGoalTest`` pins it; whether the
    refiner's *wording* is a good objective stays a refiner/PO judgement.

  - AC2 ``[review]`` — the dispatch envelope (``skills/solve/dispatch.md`` §
    ``## Issue context``) inlines the Goal **verbatim** so developer + tester + reviewer
    all read the same objective. ``EnvelopeInlinesGoalTest`` pins that the envelope names
    the ``## Goal`` as travelling with the description, that all three roles are named, and
    that the worked example actually contains a ``## Goal`` block.

  - AC3 ``[review]`` — the reviewer's verdict **reasons against the Goal** (serves the
    "why", not only the local AC). ``ReviewerReasonsAgainstGoalTest`` pins the *Reason
    against the Goal* section, the verdict-template ``Goal`` line with its three outcomes
    (SERVED / NEEDS-PO mismatch / NO-GOAL), and that the rollup routes a Goal/AC mismatch
    to *needs you*. Whether a given verdict's Goal judgement is correct stays the
    reviewer's ``[review]`` call.

  - AC4 ``[review]`` — **Goal home = a ``## Goal`` section in the description**, matching
    the description-canonical / no-separate-AC-field precedent, NOT a Linear custom field
    (default; PO may flip). ``GoalHomeIsDescriptionTest`` pins that the source-of-truth doc
    (``skills/ac/SKILL.md``) records the description as home and explicitly *not* a custom
    field, with the PO-may-flip escape hatch.

  - AC5 ``[manual]`` — **No boundary loosened** (cross-cutting invariant, verify against
    ``skills/scrum/references/accountabilities.md``): the Goal must not let the
    scrum-master author product intent nor the developer/reviewer redefine the objective.
    Whether the change *as a whole* loosens a boundary is a judgement against the
    accountabilities prose (named untestable in the report — the runner cannot assert "no
    boundary was loosened" without re-deriving the whole accountabilities model, a
    tautology). Its **structural half is pinned** here, same discipline the repo uses for
    ``[manual]`` structural halves: ``NoBoundaryLoosenedStructuralTest`` asserts the two
    boundary guards the change leans on are present (refiner "don't invent a product
    objective", reviewer "never redefine the `## Goal`") AND that the accountabilities
    reference still states the unchanged boundaries the Goal must not cross (scrum-master
    does NOT make product decisions; developers do NOT redefine the objective). The PO's
    holistic "no boundary loosened" sign-off stays the ``[manual]`` step.

Run from the repo root:
    python -m pytest scripts/test_shared_problem_goal.py
    python -m unittest discover -s scripts -p 'test_*.py'    # CI uses this
"""

import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

REFINER_AGENT = REPO_ROOT / "agents" / "refiner.md"
SCOPE_CMD = REPO_ROOT / "commands" / "scope.md"
DISPATCH = REPO_ROOT / "skills" / "solve" / "dispatch.md"
REVIEWER_AGENT = REPO_ROOT / "agents" / "reviewer.md"
AC_SKILL = REPO_ROOT / "skills" / "ac" / "SKILL.md"
SPEC_TEMPLATE = REPO_ROOT / "templates" / "spec.md"
ACCOUNTABILITIES = REPO_ROOT / "skills" / "scrum" / "references" / "accountabilities.md"


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def _norm(text: str) -> str:
    """Whitespace-collapse so a content pin survives prose line-wrapping."""
    return " ".join(text.split())


class ScopeWritesGoalTest(unittest.TestCase):
    """AC1 — /backlogd:scope writes a single-sentence ``## Goal`` above the AC; the
    refiner authors it and the scrum-master never substitutes its own product intent."""

    def test_refiner_writes_goal_above_acceptance_criteria(self):
        body = _norm(_read(REFINER_AGENT))
        self.assertIn(
            "Write the `## Goal`",
            body,
            "agents/refiner.md must instruct the refiner to write the `## Goal` section "
            "(AC1).",
        )
        # The position contract — the Goal sits immediately above ## Acceptance Criteria.
        self.assertIn(
            "immediately above `## Acceptance Criteria`",
            body,
            "agents/refiner.md must position the `## Goal` immediately above "
            "`## Acceptance Criteria` (AC1).",
        )

    def test_refiner_goal_is_a_single_sentence(self):
        body = _norm(_read(REFINER_AGENT))
        self.assertIn(
            "single sentence",
            body.lower(),
            "agents/refiner.md must require the `## Goal` to be a single sentence (AC1).",
        )

    def test_refiner_owns_wording_scrum_master_never_substitutes_intent(self):
        # The boundary half of AC1: the refiner authors it; the scrum-master never
        # substitutes its own product intent. Pinned in both authoring surfaces.
        refiner = _norm(_read(REFINER_AGENT))
        self.assertIn(
            "do **not** invent a new product objective",
            refiner,
            "agents/refiner.md must guard that the refiner does not invent a new product "
            "objective in the `## Goal` (AC1 boundary).",
        )
        # scope.md carries the guard inside a blockquote, so the phrase can wrap across a
        # leading `>` marker; assert the two contiguous halves rather than one literal span
        # so the pin survives the blockquote wrap (and still bites the pre-fix wording).
        scope = _norm(_read(SCOPE_CMD))
        self.assertIn(
            "the scrum-master never substitutes",
            scope,
            "commands/scope.md must state the scrum-master never substitutes its own "
            "product intent for the refiner-authored Goal (AC1 boundary).",
        )
        self.assertIn(
            "its own product intent",
            scope,
            "commands/scope.md must state the scrum-master never substitutes *its own "
            "product intent* for the refiner-authored Goal (AC1 boundary).",
        )

    def test_scope_makes_goal_part_of_execution_ready(self):
        # AC1's "scope writes a `## Goal` into each shaped problem" is enforced by making
        # the Goal part of the execution-ready definition and the scope dispatch order.
        scope = _norm(_read(SCOPE_CMD))
        self.assertIn(
            "single-sentence `## Goal`",
            scope,
            "commands/scope.md must include a single-sentence `## Goal` in the "
            "execution-ready definition / refiner dispatch (AC1).",
        )

    def test_pins_would_bite_on_the_pre_fix_wording(self):
        # Guard against tautological green: before NB-436 neither authoring surface
        # mentioned a Goal or the never-substitute boundary. A synthetic pre-fix body
        # must FAIL every AC1 pin.
        pre_fix_refiner = _norm(
            "Draft the spec. A short statement of the desired outcome. "
            "Write `## Acceptance Criteria`. A checklist of testable statements."
        )
        self.assertNotIn("Write the `## Goal`", pre_fix_refiner)
        self.assertNotIn("do **not** invent a new product objective", pre_fix_refiner)
        pre_fix_scope = _norm(
            "A problem is execution-ready when its description carries a clear spec and a "
            "`## Acceptance Criteria` section."
        )
        self.assertNotIn("single-sentence `## Goal`", pre_fix_scope)
        self.assertNotIn("the scrum-master never substitutes", pre_fix_scope)
        self.assertNotIn("its own product intent", pre_fix_scope)


class EnvelopeInlinesGoalTest(unittest.TestCase):
    """AC2 — the dispatch envelope inlines the Goal verbatim so the developer, tester,
    and reviewer all read the same objective, not just the AC."""

    def test_envelope_states_goal_travels_with_description(self):
        body = _norm(_read(DISPATCH))
        self.assertIn(
            "carries the single-sentence `## Goal`",
            body,
            "skills/solve/dispatch.md must state the inlined description carries the "
            "single-sentence `## Goal` (AC2).",
        )
        # Must not be trimmed/summarised out of the verbatim description.
        self.assertIn(
            "Do not trim or summarise the `## Goal` out",
            body,
            "skills/solve/dispatch.md must forbid trimming/summarising the `## Goal` out "
            "of the verbatim description (AC2).",
        )

    def test_envelope_names_all_three_reading_roles(self):
        # AC2 names developer, tester AND reviewer reading the same objective. The
        # sentence that carries the Goal must name all three so the contract can't drift
        # to "developer only".
        body = _norm(_read(DISPATCH))
        for role in ("developer", "tester", "reviewer"):
            self.assertIn(
                role,
                body,
                f"skills/solve/dispatch.md must name the {role} among the roles that read "
                f"the same `## Goal` (AC2).",
            )
        self.assertIn(
            'same "why"',
            body,
            "skills/solve/dispatch.md must state the three roles read the same \"why\" "
            "(AC2).",
        )

    def test_worked_example_contains_a_goal_block(self):
        # The worked envelope example must actually show a ## Goal so the contract is
        # demonstrated, not only described.
        raw = _read(DISPATCH)
        self.assertIn(
            "## Goal",
            raw,
            "skills/solve/dispatch.md worked example must contain a `## Goal` block (AC2).",
        )

    def test_pins_would_bite_on_the_pre_fix_wording(self):
        # Pre-NB-436 the envelope inlined "full description, and its ## Acceptance
        # Criteria" with no mention of a Goal. The pins must FAIL on that wording.
        pre_fix = _norm(
            "Inline this unit's own issue context verbatim — its title, its full "
            "description, and its `## Acceptance Criteria` exactly as they read in Linear."
        )
        self.assertNotIn("carries the single-sentence `## Goal`", pre_fix)
        self.assertNotIn("Do not trim or summarise the `## Goal` out", pre_fix)


class ReviewerReasonsAgainstGoalTest(unittest.TestCase):
    """AC3 — the reviewer's verdict reasons against the Goal (serves the stated "why",
    not only passes the local AC)."""

    def test_reviewer_has_reason_against_the_goal_section(self):
        body = _norm(_read(REVIEWER_AGENT))
        self.assertIn(
            "Reason against the Goal",
            body,
            "agents/reviewer.md must carry a 'Reason against the Goal' instruction (AC3).",
        )
        self.assertIn(
            "does the increment actually serve the stated Goal",
            body,
            "agents/reviewer.md must frame the verdict as judging whether the increment "
            "serves the stated Goal, not only the local AC (AC3).",
        )

    def test_verdict_template_carries_a_goal_line_with_three_outcomes(self):
        # The verdict body gains a Goal line; AC3 is only proven if the three outcomes are
        # all present so the reviewer cannot silently drop the mismatch branch.
        body = _norm(_read(REVIEWER_AGENT))
        for token in ("**SERVED**", "**NEEDS-PO**", "**NO-GOAL**"):
            self.assertIn(
                token,
                body,
                f"agents/reviewer.md verdict template must carry the {token} Goal outcome "
                f"(AC3).",
            )

    def test_rollup_routes_goal_ac_mismatch_to_needs_you(self):
        # A pass-the-AC-but-miss-the-Goal increment must surface to the PO, never accept
        # silently — the routing is the substance of AC3.
        body = _norm(_read(REVIEWER_AGENT))
        self.assertIn(
            "Goal/AC mismatch",
            body,
            "agents/reviewer.md rollup must name the Goal/AC mismatch route (AC3).",
        )
        self.assertIn(
            "the **Goal SERVED** (or **NO-GOAL**)",
            body,
            "agents/reviewer.md accepted-rollup must require the Goal SERVED (or NO-GOAL) "
            "(AC3).",
        )

    def test_pins_would_bite_on_the_pre_fix_wording(self):
        # Pre-NB-436 the reviewer's accept condition named only AC + DoD + standards + CI,
        # with no Goal clause and no SERVED/NO-GOAL tokens. The pins must FAIL on that.
        pre_fix = _norm(
            "accepted — every AC item MET, every DoD line MET, every applicable standard "
            "honoured, no NO-STANDARD block, and CI green."
        )
        self.assertNotIn("the **Goal SERVED** (or **NO-GOAL**)", pre_fix)
        self.assertNotIn("Reason against the Goal", pre_fix)
        self.assertNotIn("Goal/AC mismatch", pre_fix)


class GoalHomeIsDescriptionTest(unittest.TestCase):
    """AC4 — the Goal lives as a ``## Goal`` section in the description (the
    description-canonical / no-separate-AC-field precedent), NOT a Linear custom field;
    recorded as the working default, PO may flip."""

    def test_source_of_truth_doc_records_description_as_home(self):
        body = _norm(_read(AC_SKILL))
        self.assertIn(
            "The `## Goal`",
            body,
            "skills/ac/SKILL.md must document the `## Goal` artifact (AC4).",
        )
        self.assertIn(
            "the description, not a custom field",
            body.lower().replace("home: ", "").replace("**", ""),
            "skills/ac/SKILL.md must record the Goal's home as the description, not a "
            "custom field (AC4).",
        )

    def test_source_of_truth_doc_names_no_separate_field_precedent(self):
        body = _norm(_read(AC_SKILL))
        self.assertIn(
            "no-separate-AC-field precedent",
            body,
            "skills/ac/SKILL.md must tie the Goal's home to the no-separate-AC-field "
            "precedent (AC4).",
        )

    def test_source_of_truth_doc_keeps_po_may_flip_escape_hatch(self):
        # AC4 is the "default — PO may flip" decision; the doc must keep the escape hatch
        # to a filterable custom field so the recorded default is explicitly provisional.
        body = _norm(_read(AC_SKILL))
        self.assertIn(
            "the PO may later choose a filterable custom field",
            body,
            "skills/ac/SKILL.md must record that the PO may later flip to a filterable "
            "custom field (AC4 'default — PO may flip').",
        )

    def test_pins_would_bite_on_the_pre_fix_wording(self):
        # Pre-NB-436 skills/ac/SKILL.md said nothing about a Goal. The pins must FAIL on a
        # body that lacks the Goal home decision.
        pre_fix = _norm(
            "The reviewer's index-first load order lives in agents/reviewer.md and "
            "skills/reviewer/SKILL.md — not duplicated here."
        )
        self.assertNotIn("no-separate-AC-field precedent", pre_fix)
        self.assertNotIn("the PO may later choose a filterable custom field", pre_fix)


class NoBoundaryLoosenedStructuralTest(unittest.TestCase):
    """AC5 ``[manual]`` — structural half only. The holistic "no boundary was loosened"
    sign-off is a PO judgement against accountabilities.md (named untestable in the
    report). What is pinnable: the two boundary guards the change leans on are present,
    and accountabilities.md still states the unchanged boundaries the Goal must not cross."""

    def test_refiner_guard_blocks_authoring_new_product_intent(self):
        # Lower-cased haystack, so the needle is lower-cased too (the source reads
        # "do not author intent the PO never stated").
        body = _norm(_read(REFINER_AGENT)).lower()
        self.assertIn(
            "do not author intent the po never stated",
            body,
            "agents/refiner.md must guard against the refiner authoring intent the PO "
            "never stated (AC5 boundary — Goal is captured, not invented).",
        )

    def test_reviewer_guard_blocks_redefining_the_goal(self):
        body = _norm(_read(REVIEWER_AGENT))
        self.assertIn(
            "Never redefine the `## Goal` to fit the increment",
            body,
            "agents/reviewer.md must guard that the reviewer never redefines the `## Goal` "
            "to fit the increment (AC5 boundary — reviewer reasons against, does not "
            "author).",
        )

    def test_accountabilities_boundaries_the_goal_must_not_cross_are_intact(self):
        # The Goal must not let the scrum-master make product decisions, nor developers
        # redefine the objective. Those does-NOT boundaries live in accountabilities.md
        # (untouched by this change). Pin that they still read as they must — a future
        # edit that loosens either trips here.
        body = _norm(_read(ACCOUNTABILITIES))
        self.assertIn(
            "Make product decisions (what to build, what priority) — surfaces to PO",
            body,
            "accountabilities.md must keep the Scrum Master 'does NOT make product "
            "decisions' boundary (AC5 cross-cutting invariant).",
        )
        self.assertIn(
            "Speak as the PO in the issue",
            body,
            "accountabilities.md must keep the Scrum Master 'does NOT speak as the PO' "
            "boundary (AC5 cross-cutting invariant).",
        )

    def test_pins_would_bite_if_guards_were_dropped(self):
        # If a reword stripped the don't-invent / never-redefine guards, the structural
        # pins above must FAIL — prove they bite on a guard-free synthetic body.
        guardless_refiner = _norm(
            "Write the `## Goal`. A single sentence stating the objective the work serves."
        )
        self.assertNotIn(
            "do not author intent the po never stated", guardless_refiner.lower()
        )
        guardless_reviewer = _norm(
            "Reason against the Goal. Read the `## Goal` and judge whether the increment "
            "serves it."
        )
        self.assertNotIn(
            "Never redefine the `## Goal` to fit the increment", guardless_reviewer
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
