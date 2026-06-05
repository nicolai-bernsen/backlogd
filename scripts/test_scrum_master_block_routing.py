"""Regression net for NB-385 — the scrum-master side of the block-and-ask flow.

NB-385 owns NB-378 acceptance criteria #5 and #6.

  - AC #5 (`[review]`) — the **non-delegable standards boundary**: the scrum-master may
    clear a reviewer `block` ONLY when an existing ADR/precedent already answers it (a
    `fact:` lookup miss); a genuine `standard:` gap is non-delegable and goes to the PO —
    the scrum-master never authors the standard itself. Documented in
    `skills/scrum/references/accountabilities.md` + `commands/review.md` / `commands/solve.md`.
  - AC #6 (`[manual]`) — the Linear-native missing-standard flow (create a "Define
    standard for X" sub-issue, mark the parent blocked-by it, ask the PO, on the answer
    refine+solve the sub-issue, the parent unblocks). The end-to-end PO confirmation is a
    walkthrough (NOT runnable here); but the *documented* flow + its wiring through the
    orchestrator surfaces is `[review]`-checkable and is pinned below.

Both ACs are `[review]`/`[manual]` — they are judgements/walkthroughs, NOT behaviours a
test runner can exercise. So this file does **not** try to prove "the scrum-master routes
a block correctly" (that would be a tautology against the doc that *is* the instruction).
It pins the load-bearing prose invariants the change introduced across the four
scrum-master surfaces it edited — `skills/scrum/references/accountabilities.md`,
`commands/review.md`, `skills/solve/ship.md`, `commands/solve.md` — so an incidental
reword in the touched neighbourhood trips CI instead of silently regressing the policy
back to "the scrum-master guesses past / authors the standard itself".

The sibling reviewer surfaces (`agents/reviewer.md`, `skills/reviewer/SKILL.md`) are
covered by scripts/test_reviewer_block_outcome.py (NB-384) and
scripts/test_reviewer_standards_enforcement.py (NB-383); NB-385 did NOT touch those, so
this file deliberately does not re-cover them. The ship-on-green / `[manual]`-contract
pins on these same files live in scripts/test_ship_on_green_and_manual.py (NB-393); this
file pins only the net-new `block`-routing invariants, which no existing test guards.

Each class carries a `*_would_bite_on_the_pre_fix_wording` guard proving the pin actually
FIRES on synthetic pre-NB-385 text (the three-way "guess past the blocker" model with no
non-delegable boundary, no `Define standard for X` flow), so a green here is never
tautological.

Run from the repo root:  python scripts/test_scrum_master_block_routing.py
(or collected by `python -m unittest discover -s scripts -p 'test_*.py'`).
"""

import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

ACCOUNTABILITIES = REPO_ROOT / "skills" / "scrum" / "references" / "accountabilities.md"
REVIEW_CMD = REPO_ROOT / "commands" / "review.md"
SHIP_SKILL = REPO_ROOT / "skills" / "solve" / "ship.md"
SOLVE_CMD = REPO_ROOT / "commands" / "solve.md"

# AC #5's boundary is documented in accountabilities.md and pointed-to from both surfaces
# where the scrum-master acts on the verdict. The boundary is only proven if it holds in
# accountabilities.md AND is reachable from where the scrum-master acts, so the two act
# surfaces are checked as a set.
ACT_SURFACES = (REVIEW_CMD, SHIP_SKILL)

# The block glyph, kept as an escape so this source file stays ASCII and never trips a
# Windows cp1252 round-trip. Membership-tested only — never printed.
BLOCK_GLYPH = "\U0001f6ab"  # the block glyph


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def _norm(text: str) -> str:
    """Whitespace-collapse so a content pin survives prose line-wrapping."""
    return " ".join(text.split())


class NonDelegableBoundaryTest(unittest.TestCase):
    """AC #5 — the scrum-master clears only a `fact:` lookup-miss (existing ADR answers
    it); a `standard:` gap is non-delegable and goes to the PO; the scrum-master never
    authors the standard itself."""

    def test_accountabilities_documents_the_non_delegable_boundary_section(self):
        # The boundary lives in a dedicated, findable subsection — not buried in a table
        # cell alone. AC #5 names accountabilities.md as the home of record.
        body = _norm(_read(ACCOUNTABILITIES))
        self.assertIn(
            "The non-delegable standards boundary",
            body,
            "accountabilities.md must carry a 'The non-delegable standards boundary' "
            "section (AC #5).",
        )

    def test_accountabilities_clear_only_a_lookup_miss(self):
        # The permissive half: the scrum-master MAY clear a block, but ONLY when an
        # existing ADR/precedent already answers it (a lookup miss). Pinned lower-cased so
        # the assertion survives sentence-start vs mid-sentence capitalization.
        body = _norm(_read(ACCOUNTABILITIES)).lower()
        self.assertIn(
            "only when an existing\nadr/precedent already answers it".replace("\n", " "),
            body,
            "accountabilities.md must permit clearing a block ONLY when an existing "
            "ADR/precedent already answers it (AC #5 lookup-miss).",
        )
        self.assertIn(
            "lookup miss",
            body,
            "accountabilities.md must name the clearable case a lookup miss (AC #5).",
        )

    def test_accountabilities_standard_gap_is_non_delegable_and_never_authored(self):
        # The restrictive half: a `standard:` gap is non-delegable; the scrum-master must
        # NEVER author the standard itself. Both halves are load-bearing — drop either and
        # the scrum-master can quietly become the architect.
        body = _norm(_read(ACCOUNTABILITIES)).lower()
        self.assertIn(
            "non-delegable",
            body,
            "accountabilities.md must call a standards gap non-delegable (AC #5).",
        )
        self.assertIn(
            "never author the standard itself",
            body,
            "accountabilities.md must forbid the scrum-master authoring the standard "
            "itself (AC #5).",
        )

    def test_accountabilities_standard_gap_routes_to_the_po(self):
        # Where the non-delegable gap goes: to the PO. AC #5's whole point is the routing.
        body = _norm(_read(ACCOUNTABILITIES)).lower()
        self.assertIn(
            "goes to the **po**".replace("**", ""),  # bold-insensitive
            body.replace("**", ""),
            "accountabilities.md must route a standard: gap to the PO (AC #5).",
        )

    def test_accountabilities_table_row_carries_the_boundary(self):
        # AC #5 also asks for the boundary at the Scrum-Master accountability table: the
        # clear-only-a-lookup-miss permission paired with the never-author prohibition.
        body = _norm(_read(ACCOUNTABILITIES))
        self.assertIn(
            "Clearing a reviewer `block` **only** when an existing ADR/precedent already answers it",
            body,
            "accountabilities.md Scrum-Master table must carry the clear-only-a-lookup-miss row (AC #5).",
        )
        self.assertIn(
            "Author a missing standard itself",
            body,
            "accountabilities.md Scrum-Master 'Does not do' column must forbid authoring a "
            "missing standard (AC #5).",
        )

    def test_what_the_split_prevents_names_the_architect_failure(self):
        # The "What the split prevents" list must name the failure mode AC #5 guards
        # against — the scrum-master quietly becoming the architect.
        body = _norm(_read(ACCOUNTABILITIES)).lower()
        self.assertIn(
            "quietly becoming the architect",
            body,
            "accountabilities.md 'What the split prevents' must name the scrum-master "
            "becoming the architect (AC #5).",
        )

    def test_both_act_surfaces_point_at_the_boundary_doc(self):
        # AC #5 requires the boundary be documented *where the scrum-master acts*:
        # commands/review.md and the ship-on-green chain skills/solve/ship.md. Both must
        # name the non-delegable standards boundary and point at accountabilities.md.
        for path in ACT_SURFACES:
            with self.subTest(surface=path.name):
                body = _norm(_read(path))
                self.assertIn(
                    "non-delegable standards boundary",
                    body,
                    f"{path.relative_to(REPO_ROOT)} must name the non-delegable standards "
                    f"boundary (AC #5).",
                )
                self.assertIn(
                    "accountabilities.md",
                    body,
                    f"{path.relative_to(REPO_ROOT)} must point at accountabilities.md for "
                    f"the boundary (AC #5).",
                )

    def test_review_step_5_forbids_authoring_the_standard(self):
        # The act surface must restate the prohibition inline so the scrum-master sees it
        # at the point of action, not just by following a link — the "de-facto architect"
        # consequence is the load-bearing phrasing.
        body = _norm(_read(REVIEW_CMD)).lower()
        self.assertIn(
            "never author a missing\n`standard:` yourself".replace("\n", " "),
            body,
            "commands/review.md step 5 must forbid authoring a missing standard inline (AC #5).",
        )
        self.assertIn(
            "de-facto architect",
            body,
            "commands/review.md step 5 must name the de-facto-architect failure mode (AC #5).",
        )

    def test_boundary_pins_would_bite_on_the_pre_fix_wording(self):
        # Anti-tautology: the pre-NB-385 model let the scrum-master 'remove impediments'
        # without a non-delegable standards carve-out. Prove every AC #5 pin FIRES on a
        # synthetic pre-fix text (no boundary section, no never-author rule, no
        # architect-failure naming). If this passed the pins, they'd prove nothing.
        pre_fix = _norm(
            "Scrum Master removes impediments by surfacing blockers to the PO rather than "
            "guessing past them. It owns all orchestration and clears blockers as they "
            "arise so the developer can keep moving."
        )
        low = pre_fix.lower()
        self.assertNotIn("the non-delegable standards boundary", pre_fix)
        self.assertNotIn("non-delegable", low)
        self.assertNotIn("never author the standard itself", low)
        self.assertNotIn("lookup miss", low)
        self.assertNotIn("de-facto architect", low)
        self.assertNotIn("quietly becoming the architect", low)


class LinearNativeMissingStandardFlowTest(unittest.TestCase):
    """AC #6 (documented-flow half) — the block routes through Linear's sub-issue +
    blocked-by primitives: create a `Define standard for X` sub-issue, mark the parent
    blocked-by it, ask the PO, on the answer refine+solve the sub-issue, the parent
    unblocks. The end-to-end PO walkthrough is `[manual]`; the wiring is pinned here."""

    def test_block_is_a_four_way_rollup_on_both_orchestrator_surfaces(self):
        # NB-384 hand-off: the verdict rollup the scrum-master surfaces is now 4-way and
        # `block` is the fourth. Pin the enumeration so a regression to the three-way
        # rollup (dropping `block`) fails on both review.md and ship.md.
        for path in (REVIEW_CMD, SHIP_SKILL):
            with self.subTest(surface=path.name):
                body = _norm(_read(path)).lower()
                self.assertIn(
                    "`block`",
                    body,
                    f"{path.relative_to(REPO_ROOT)} must name the fourth rollup `block` "
                    f"(AC #6 / NB-384 hand-off).",
                )
                self.assertIn(
                    "accepted` / `sent back` / `needs po` / **`block`".replace("**", ""),
                    body.replace("**", ""),
                    f"{path.relative_to(REPO_ROOT)} must enumerate the 4-way rollup with "
                    f"`block` (AC #6 / NB-384 hand-off).",
                )

    def test_accountabilities_flow_creates_define_standard_subissue(self):
        # Step 1 of the flow: a `Define standard for X` sub-issue via Linear's parentId
        # primitive — not a buried comment.
        body = _norm(_read(ACCOUNTABILITIES))
        self.assertIn(
            "Define standard for X",
            body,
            "accountabilities.md flow must create a 'Define standard for X' sub-issue (AC #6).",
        )
        self.assertIn(
            "sub-issue +\nblocked-by".replace("\n", " "),
            body,
            "accountabilities.md flow must use Linear's sub-issue + blocked-by primitives (AC #6).",
        )

    def test_accountabilities_flow_marks_parent_blocked_by(self):
        # Step 2: the parent is marked blocked-by the sub-issue (the `blockedBy` primitive)
        # and does NOT merge — it parks In Review, blocked.
        body = _norm(_read(ACCOUNTABILITIES))
        self.assertIn(
            "blockedBy",
            body,
            "accountabilities.md flow must mark the parent blockedBy the sub-issue (AC #6).",
        )
        self.assertIn(
            "does **not** merge".replace("**", ""),
            body.replace("**", ""),
            "accountabilities.md flow must state the parent does not merge (AC #6).",
        )

    def test_accountabilities_flow_asks_the_po_the_standard_question(self):
        # Step 3: surface the genuine judgement call to the PO; the scrum-master does NOT
        # invent the answer.
        body = _norm(_read(ACCOUNTABILITIES)).lower()
        self.assertIn(
            "what standard would you like for",
            body,
            "accountabilities.md flow must surface the 'what standard would you like for X?' "
            "question to the PO (AC #6).",
        )

    def test_accountabilities_flow_refines_solves_subissue_writes_adr(self):
        # Step 4: on the PO's answer, refine + solve the sub-issue, writing the ADR from
        # the template (which regenerates the index).
        body = _norm(_read(ACCOUNTABILITIES)).lower()
        self.assertIn(
            "refine + solve the sub-issue",
            body,
            "accountabilities.md flow must refine+solve the sub-issue on the PO's answer (AC #6).",
        )
        self.assertIn(
            "write the adr",
            body,
            "accountabilities.md flow must write the ADR from the template (AC #6).",
        )

    def test_accountabilities_flow_parent_unblocks_and_story_continues(self):
        # Step 5: the parent unblocks once the sub-issue is completed and the new standard
        # governs X; the original story continues.
        body = _norm(_read(ACCOUNTABILITIES)).lower()
        self.assertIn(
            "the parent **unblocks**".replace("**", ""),
            body.replace("**", ""),
            "accountabilities.md flow must state the parent unblocks (AC #6).",
        )
        self.assertIn(
            "the original story continues",
            body,
            "accountabilities.md flow must state the original story continues (AC #6).",
        )

    def test_review_step_5_block_branch_wires_the_full_flow(self):
        # The actionable block branch in commands/review.md step 5 must carry the same
        # five-step Linear-native flow so the scrum-master acts on it at verdict time:
        # create the sub-issue (parentId), mark blockedBy, ask the PO, on the answer
        # refine+solve writing the ADR, unblock.
        body = _norm(_read(REVIEW_CMD))
        for needle, why in (
            ("Define standard for {X}` sub-issue", "create the Define-standard sub-issue"),
            ("parentId", "create it as a sub-issue via parentId"),
            ("save_issue(id: problem, blockedBy: [sub-issue])", "mark the parent blockedBy it"),
            ("Linear sub-issue + blocked-by\nprimitives".replace("\n", " "),
             "use Linear's sub-issue + blocked-by primitives, not a buried comment"),
            ("refine + solve the", "refine+solve the sub-issue on the PO's answer"),
            ("regenerates `docs/standards/index.json`", "writing the ADR regenerates the index"),
        ):
            self.assertIn(
                needle, body,
                f"commands/review.md step 5 block branch must {why} (AC #6).",
            )

    def test_review_step_5_block_does_not_merge_and_parks_blocked_by(self):
        # The load-bearing consequence of a block: the problem does NOT merge — it parks
        # blocked-by a new sub-issue.
        body = _norm(_read(REVIEW_CMD))
        self.assertIn(
            "the problem does NOT merge",
            body,
            "commands/review.md step 5 must state a block does NOT merge (AC #6).",
        )
        self.assertIn(
            "parks blocked-by a new sub-issue",
            body,
            "commands/review.md step 5 must state a block parks blocked-by a new sub-issue (AC #6).",
        )

    def test_review_verdict_template_carries_block_classification_lines(self):
        # The drafted verdict body the scrum-master lifts carries the block-only standard:
        # / fact: classification lines so the route is written into the verdict. Mirrors the
        # reviewer template guarded in test_reviewer_block_outcome.py, but here on the
        # scrum-master's review.md copy that NB-385 added.
        #
        # NB-415 migrated the verdict-body display off the block glyph (🚫) onto the
        # `- [ ] **NO-STANDARD**` checkbox + bold-label convention (the verdict rollup is a
        # Linear comment and carries no status emoji). The lines now read `- [ ]
        # **NO-STANDARD** standard:` / `... fact:`; the pin tracks that and asserts the block
        # glyph is GONE.
        body = _norm(_read(REVIEW_CMD))
        self.assertIn(
            "Missing standard / fact",
            body,
            "commands/review.md verdict template must carry the 'Missing standard / fact' "
            "section (AC #6 classification written into the verdict).",
        )
        self.assertIn(
            "**NO-STANDARD** standard:",
            body,
            "commands/review.md verdict template must carry a NO-STANDARD `standard:` block "
            "line (AC #6).",
        )
        self.assertIn(
            "**NO-STANDARD** fact:",
            body,
            "commands/review.md verdict template must carry a NO-STANDARD `fact:` block line "
            "(AC #6).",
        )
        self.assertNotIn(
            BLOCK_GLYPH,
            body,
            "commands/review.md verdict template must use no status/block emoji — NB-415 "
            "migrated the block glyph to the NO-STANDARD bold label.",
        )

    def test_fact_block_is_answered_once_without_po_or_adr(self):
        # The fact: route is the mirror of the standard: route — answer once, no ADR, no
        # PO, no sub-issue. Pinned in both the boundary doc and the act surface so the two
        # routes can't collapse into one.
        review = _norm(_read(REVIEW_CMD)).lower()
        self.assertIn(
            "answer once and continue",
            review,
            "commands/review.md must route a fact: block to 'answer once and continue' (AC #6).",
        )
        accountab = _norm(_read(ACCOUNTABILITIES)).lower()
        self.assertIn(
            "answer once",
            accountab,
            "accountabilities.md must route a fact: block to answer-once (AC #6).",
        )

    def test_ship_block_outcome_parks_and_interrupts_po_on_standard_gap(self):
        # The ship-on-green chain's `block` Outcome: the problem does not merge, parks
        # blocked-by a sub-issue, and interrupts the PO ONLY on a standard: gap (a fact:
        # gap is answered once, no PO). This is what makes ship-on-green honour the block.
        body = _norm(_read(SHIP_SKILL))
        self.assertIn(
            "parks blocked-by a new sub-issue",
            body,
            "skills/solve/ship.md block Outcome must park blocked-by a new sub-issue (AC #6).",
        )
        self.assertIn(
            "the scrum-master never authors the standard itself",
            body,
            "skills/solve/ship.md block Outcome must forbid authoring the standard (AC #5/#6).",
        )
        self.assertIn(
            "Interrupt the PO** on a `standard:` gap".replace("**", ""),
            body.replace("**", ""),
            "skills/solve/ship.md must interrupt the PO only on a standard: gap (AC #6).",
        )

    def test_solve_surfaces_block_as_a_po_surface_and_in_report_ladder(self):
        # commands/solve.md is the orchestrator surface: `block` must appear in the
        # PO-surface list (step 8) and the Report verdict/problem ladder, holding the
        # problem In Review blocked-by the sub-issue.
        body = _norm(_read(SOLVE_CMD))
        self.assertIn(
            "Define standard for X",
            body,
            "commands/solve.md must name the Define-standard sub-issue in its surface/report (AC #6).",
        )
        self.assertIn(
            "blocked-by {Define standard for X}",
            body,
            "commands/solve.md Report ladder must show the problem held blocked-by the "
            "Define-standard sub-issue on a block (AC #6).",
        )

    def test_flow_pins_would_bite_on_the_pre_fix_wording(self):
        # Anti-tautology: the pre-NB-385 wording had a three-way verdict and no
        # Linear-native missing-standard flow at all. Prove every AC #6 wiring pin FIRES on
        # a synthetic pre-fix text (no `block`, no Define-standard sub-issue, no blockedBy
        # routing, no standard:/fact: classification lines). A green here would otherwise
        # be tautological.
        pre_fix = _norm(
            "On hand-back the scrum-master surfaces a three-way verdict (accepted, sent "
            "back, or needs you) to the PO and merges a clean green PR. A sent-back verdict "
            "re-dispatches the developer; a needs-you verdict asks the PO a question."
        )
        low = pre_fix.lower()
        self.assertNotIn("`block`", low)
        self.assertNotIn("define standard for", low)
        self.assertNotIn("blockedBy", pre_fix)
        self.assertNotIn("what standard would you like for", low)
        self.assertNotIn("parks blocked-by", low)
        self.assertNotIn("**no-standard** standard:", low)
        self.assertNotIn("**no-standard** fact:", low)


if __name__ == "__main__":
    unittest.main(verbosity=2)
