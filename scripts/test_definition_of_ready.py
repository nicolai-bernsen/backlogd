"""Regression net for NB-428 — Definition of Ready, the Socratic problem-shaping entry gate.

The change is prose-only across five markdown sources:

  * docs/scrum/definition-of-ready.md  — the DoR hard-rules floor (new; source of truth)
  * agents/refiner.md                  — the refiner runs the gate (step 5)
  * commands/scope.md                  — the scrum-master dispatches + frames the gate (§3)
  * docs/scrum/mapping.md              — Sprint Planning row + the DoR-is-community-practice note
  * docs/overview.md                   — the symmetric entry/exit pointer

Most of NB-428's ACs are `[review]` — judgements an agent renders from the prose at verdict
time (is the gate *truly* Socratic-not-generative, does the framing *read* honestly), NOT
behaviours a test runner can exercise. So this file does **not** try to prove "the gate
behaves" (a tautology against the doc that *is* the instruction). It pins the load-bearing
prose invariants the change introduced, so an incidental reword in the touched
neighbourhood trips CI instead of silently regressing the policy — the same
guard-the-neighbourhood discipline as scripts/test_first_live_run_gate.py and
scripts/test_reviewer_standards_enforcement.py.

Mapped to NB-428's ACs:

  * AC1 [review] — a Definition-of-Ready check in /backlogd:scope: a problem cannot become
    ready until it has a crisp outcome, falsifiable AC, and no unresolved one-way-door
    decision. Pinned by DorFloorRules + ScopeRunsTheGate.
  * AC2 [review] — Socratic pressure-test (interrogate, don't generate): the three
    questions, surfaced to the PO, not answered for them. Pinned by SocraticPressureTest.
  * AC3 [review] — devil's-advocate / pre-mortem recorded as the PO's input, not the
    agent's invention; the question-then-criticism pairing. Pinned by DevilsAdvocatePremortem.
  * AC4 [review] — standards-conflict check against the ADR corpus, fusing the Socratic
    front-end with the inspection layer. Pinned by StandardsConflictCheck.
  * AC5 [manual] — explicitly NOT idea generation / prioritization / ranking. This is the
    PO's first-use judgement and cannot be closed by a test; what IS pinned is that all
    surfaces carry the out-of-scope guard so the reviewer can verify it from the text.
    Pinned by HoldsTheLineNotGenerativeNotPrioritization.
  * AC6 [review] — symmetric framing documented: DoR (entry) mirrors DoD (exit). Pinned by
    SymmetricFramingDocumented.

Whether the prose is *sound*, the gate truly *non-generative*, and the framing *honest*
stay the reviewer's call ([review]); the pins here anchor the strings against silent drift.

CI runs `python3 -m unittest discover -s scripts -p 'test_*.py'` from the repo root
(see .github/workflows/ci.yml), so this lives in scripts/ as a stdlib unittest. It does
NOT do a git-diff / whole-worktree footprint scan (the NB-418 bug that false-fails every
other unit's local suite).

Run from the repo root:
    python -m unittest scripts.test_definition_of_ready
    python scripts/test_definition_of_ready.py
"""

import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

DOR = REPO_ROOT / "docs" / "scrum" / "definition-of-ready.md"
DOD = REPO_ROOT / "docs" / "scrum" / "definition-of-done.md"
REFINER = REPO_ROOT / "agents" / "refiner.md"
SCOPE_CMD = REPO_ROOT / "commands" / "scope.md"
MAPPING = REPO_ROOT / "docs" / "scrum" / "mapping.md"
OVERVIEW = REPO_ROOT / "docs" / "overview.md"


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def _norm(text: str) -> str:
    """Whitespace-collapse so a content pin survives prose line-wrapping.

    Also drops leading Markdown blockquote markers (`> `) per line *before* collapsing, so a
    pin survives a phrase that wraps across lines inside scope.md's blockquote dispatch
    envelope (otherwise an interior `>` lands mid-phrase and breaks the match)."""
    lines = [ln.lstrip().lstrip(">").lstrip() if ln.lstrip().startswith(">") else ln
             for ln in text.splitlines()]
    return " ".join(" ".join(lines).split())


class DorFileExists(unittest.TestCase):
    """The DoR is a first-class doc, not a buried aside."""

    def test_dor_file_present(self):
        self.assertTrue(
            DOR.is_file(),
            f"NB-428: the Definition of Ready must live at {DOR.relative_to(REPO_ROOT)}.",
        )

    def test_dor_has_single_h1(self):
        # House style: no second `# H1` in an ADR-style doc (MD025 spirit). The DoR mirrors
        # the DoD, which opens with exactly one H1.
        body = _read(DOR)
        h1s = [ln for ln in body.splitlines() if ln.startswith("# ")]
        self.assertEqual(
            len(h1s), 1,
            f"NB-428: {DOR.relative_to(REPO_ROOT)} must have exactly one top-level H1 "
            f"(found {len(h1s)}).",
        )


class DorFloorRules(unittest.TestCase):
    """AC1: the DoR names its three load-bearing readiness rules — crisp outcome,
    falsifiable AC, no unresolved one-way-door decision."""

    def test_crisp_outcome_rule(self):
        self.assertIn("crisp outcome", _norm(_read(DOR)).lower(),
                      "AC1: DoR must require a crisp outcome.")

    def test_falsifiable_ac_rule(self):
        self.assertIn("falsifiable", _norm(_read(DOR)).lower(),
                      "AC1: DoR must require falsifiable acceptance criteria.")

    def test_no_one_way_door_rule(self):
        self.assertIn("one-way-door", _norm(_read(DOR)).lower(),
                      "AC1: DoR must require no unresolved one-way-door decision.")


class ScopeRunsTheGate(unittest.TestCase):
    """AC1: /backlogd:scope runs the DoR gate at the FRONT of scope (the refiner dispatch),
    points at the DoR doc as source of truth, and does not re-state the full rule."""

    def test_scope_dispatch_runs_the_dor_gate(self):
        body = _norm(_read(SCOPE_CMD))
        self.assertIn("Definition-of-Ready gate", body,
                      "AC1: commands/scope.md must run the Definition-of-Ready gate in the "
                      "refiner dispatch.")
        # The three floor properties named in the dispatch.
        for needle in ("crisp outcome", "falsifiable AC", "one-way-door"):
            self.assertIn(needle, body,
                          f"AC1: commands/scope.md must name '{needle}' as a DoR rule.")

    def test_scope_points_at_dor_doc_as_source_of_truth(self):
        body = _norm(_read(SCOPE_CMD))
        self.assertIn("docs/scrum/definition-of-ready.md", body,
                      "AC1: commands/scope.md must link the DoR doc.")
        self.assertIn("source of truth — do not restate it", body,
                      "AC1: commands/scope.md must defer to the DoR doc as source of truth "
                      "(no rule duplication).")

    def test_refiner_runs_the_gate(self):
        body = _norm(_read(REFINER))
        self.assertIn("Definition-of-Ready gate", body,
                      "AC1: agents/refiner.md must run the Definition-of-Ready gate.")
        self.assertIn("definition-of-ready.md", body,
                      "AC1: agents/refiner.md must link the DoR doc.")


class SocraticPressureTest(unittest.TestCase):
    """AC2: the Socratic pressure-test — the three questions, interrogate-don't-generate,
    surfaced to the PO and NOT answered for them. Present in DoR doc, scope, and refiner."""

    QUESTIONS = ("real problem", "who", "fail")

    def _carries_questions(self, body_norm: str, where: str):
        # The three Socratic questions. The wording is terser in scope.md's dispatch
        # ("what is the real problem?") than in the DoR doc/refiner ("real problem
        # behind"), so pin the common substring "real problem".
        low = body_norm.lower()
        self.assertIn("real problem", low,
                      f"AC2: {where} must ask what the real problem behind the request is.")
        self.assertIn("ships wrong", low,
                      f"AC2: {where} must ask who the user is / who fails if it ships wrong.")
        self.assertIn("what would make this fail", low,
                      f"AC2: {where} must ask what would make this fail.")

    def test_dor_doc_socratic_questions(self):
        self._carries_questions(_norm(_read(DOR)), "the DoR doc")

    def test_scope_socratic_questions(self):
        self._carries_questions(_norm(_read(SCOPE_CMD)), "commands/scope.md")

    def test_refiner_socratic_questions(self):
        self._carries_questions(_norm(_read(REFINER)), "agents/refiner.md")

    def test_interrogate_not_generate_framing(self):
        # The discipline phrase appears across surfaces; the DoR doc + scope must carry it.
        for path, where in ((DOR, "the DoR doc"), (SCOPE_CMD, "commands/scope.md")):
            low = _norm(_read(path)).lower()
            self.assertIn("interrogat", low,
                          f"AC2: {where} must frame the move as interrogating the idea.")

    def test_not_answered_for_the_po(self):
        # The questions are surfaced to the PO, not pre-filled. DoR doc + refiner say so.
        self.assertIn("does not answer them for the po", _norm(_read(DOR)).lower(),
                      "AC2: DoR doc must state the gate does not answer the questions for "
                      "the PO.")
        self.assertIn("do **not** answer them for the po", _norm(_read(REFINER)).lower(),
                      "AC2: agents/refiner.md must state the refiner does not answer the "
                      "Socratic questions for the PO.")


class DevilsAdvocatePremortem(unittest.TestCase):
    """AC3: devil's-advocate / pre-mortem — 'assume this shipped and was wrong — why?' —
    recorded as the PO's input (not the agent's invention), with the question-then-criticism
    pairing called out."""

    PREMORTEM = "assume this shipped and was wrong"

    def test_premortem_question_present(self):
        for path, where in ((DOR, "the DoR doc"), (SCOPE_CMD, "commands/scope.md"),
                            (REFINER, "agents/refiner.md")):
            self.assertIn(self.PREMORTEM, _norm(_read(path)).lower(),
                          f"AC3: {where} must carry the pre-mortem question "
                          f"('{self.PREMORTEM} — why?').")

    def test_recorded_as_po_input_not_agent_invention(self):
        # DoR doc + refiner must frame the answer as the PO's, not the agent's invention.
        self.assertIn("not the agent's invention", _norm(_read(DOR)).lower(),
                      "AC3: DoR doc must record the pre-mortem as the PO's input, not the "
                      "agent's invention.")
        refiner = _norm(_read(REFINER)).lower()
        self.assertIn("the po's input, not your", refiner,
                      "AC3: agents/refiner.md must record the pre-mortem answer as the PO's "
                      "input, not the agent's invention.")

    def test_question_then_criticism_pairing(self):
        # The PO values the question-then-criticism pairing — it must be named load-bearing.
        for path, where in ((DOR, "the DoR doc"), (REFINER, "agents/refiner.md")):
            self.assertIn("question-then-criticism", _norm(_read(path)).lower(),
                          f"AC3: {where} must name the question-then-criticism pairing.")


class StandardsConflictCheck(unittest.TestCase):
    """AC4: standards-conflict check — test the idea against the ADR corpus, fusing the
    Socratic front-end with the same inspection layer the reviewer runs at the exit."""

    def test_dor_doc_standards_conflict_rule(self):
        body = _norm(_read(DOR))
        low = body.lower()
        self.assertIn("not fighting an accepted standard", low,
                      "AC4: DoR doc must carry the not-fighting-a-standard rule.")
        self.assertIn("docs/standards/index.json", body,
                      "AC4: DoR doc must test against the ADR corpus (index.json).")
        # Fuses with the inspection layer (the persistent cross-issue AC the reviewer runs).
        self.assertIn("persistent, cross-issue", low,
                      "AC4: DoR doc must fuse the check with the persistent cross-issue AC "
                      "inspection layer (skills/ac/SKILL.md).")

    def test_scope_and_refiner_standards_conflict(self):
        for path, where in ((SCOPE_CMD, "commands/scope.md"), (REFINER, "agents/refiner.md")):
            body = _norm(_read(path))
            self.assertIn("Accepted standard", body,
                          f"AC4: {where} must name the Accepted-standard conflict check.")
            self.assertIn("index.json", body,
                          f"AC4: {where} must test the idea against the ADR corpus "
                          "(docs/standards/index.json).")

    def test_only_accepted_adrs_are_in_force(self):
        # Same as the reviewer's exit-side filter: only the *current Accepted* set binds.
        for path, where in ((DOR, "the DoR doc"), (REFINER, "agents/refiner.md")):
            self.assertIn("Accepted", _read(path),
                          f"AC4: {where} must scope the standards check to current "
                          "Accepted ADRs (matching the reviewer's exit-side filter).")


class HoldsTheLineNotGenerativeNotPrioritization(unittest.TestCase):
    """AC5 (testable sliver): explicitly NOT idea generation / prioritization / ranking.
    The [manual] first-use judgement cannot be closed by a test; what IS pinned is that the
    out-of-scope guard is present in all surfaces so the reviewer can verify it from text."""

    def test_dor_doc_out_of_scope_section(self):
        body = _norm(_read(DOR))
        low = body.lower()
        self.assertIn("idea generation", low,
                      "AC5: DoR doc must explicitly exclude idea generation.")
        self.assertIn("prioritization", low,
                      "AC5: DoR doc must explicitly exclude prioritization.")
        self.assertIn("ranking", low,
                      "AC5: DoR doc must explicitly exclude ranking.")
        self.assertIn("rubber-stamp seat", low,
                      "AC5: DoR doc must name the rubber-stamp-seat anti-pattern the line "
                      "exists to avoid.")

    def test_scope_holds_the_line(self):
        low = _norm(_read(SCOPE_CMD)).lower()
        self.assertIn("do **not** generate ideas, prioritize", low,
                      "AC5: commands/scope.md must state the gate does not generate ideas "
                      "or prioritize.")

    def test_refiner_holds_the_line(self):
        low = _norm(_read(REFINER)).lower()
        self.assertIn("does **not** generate ideas", low,
                      "AC5: agents/refiner.md must state the gate does not generate ideas.")
        self.assertIn("prioritize / rank", low,
                      "AC5: agents/refiner.md must state the gate does not prioritize/rank "
                      "the backlog.")


class SymmetricFramingDocumented(unittest.TestCase):
    """AC6: symmetric framing documented — DoR (entry) mirrors DoD (exit) — and the honest
    'DoR is community practice, NOT the 2020 Scrum Guide' caveat is sold as such."""

    def test_dor_doc_states_symmetry(self):
        low = _norm(_read(DOR)).lower()
        self.assertIn("entry", low, "AC6: DoR doc must frame itself as the entry gate.")
        self.assertIn("exit", low, "AC6: DoR doc must reference the DoD exit gate.")
        self.assertIn("mirror", low, "AC6: DoR doc must state it mirrors the DoD.")
        self.assertIn("definition-of-done.md", _read(DOR),
                      "AC6: DoR doc must link the Definition of Done.")

    def test_dor_doc_honest_community_practice_caveat(self):
        low = _norm(_read(DOR)).lower()
        # The "not" is bolded (`**not** in the ...`), so the markdown markers sit between
        # the words — pin the bold-marker form, matching the mapping-note pin below.
        self.assertIn("not** in the", low,
                      "AC6: DoR doc must state the DoR is NOT in the 2020 Scrum Guide.")
        self.assertIn("2020 scrum guide", low,
                      "AC6: DoR doc must name the 2020 Scrum Guide explicitly.")
        self.assertIn("community", low,
                      "AC6: DoR doc must frame DoR as community practice.")
        # "not" is bolded in the doc (`**not** a Scrum-compliance fix`).
        self.assertIn("not** a scrum-compliance fix", low,
                      "AC6: DoR doc must sell it honestly — not a Scrum-compliance fix.")

    def test_mapping_documents_symmetry_and_caveat(self):
        body = _read(MAPPING)
        low = _norm(body).lower()
        self.assertIn("definition-of-ready.md", body,
                      "AC6: mapping.md must link the DoR (Sprint Planning row).")
        self.assertIn("entry gate", low,
                      "AC6: mapping.md must frame the DoR as the entry gate.")
        self.assertIn("symmetric to the", low,
                      "AC6: mapping.md must state the DoR is symmetric to the DoD.")
        # The honest caveat lives in the mapping note too.
        self.assertIn("not** in the november 2020 scrum guide", low,
                      "AC6: mapping.md must carry the honest 'not in the 2020 Scrum Guide' "
                      "caveat.")
        self.assertIn("not** as a scrum-compliance fix", low,
                      "AC6: mapping.md must state DoR is adopted for symmetry, not as a "
                      "Scrum-compliance fix.")

    def test_overview_points_at_both_gates(self):
        body = _read(OVERVIEW)
        self.assertIn("scrum/definition-of-ready.md", body,
                      "AC6: docs/overview.md must point at the DoR entry gate.")
        self.assertIn("scrum/definition-of-done.md", body,
                      "AC6: docs/overview.md must point at the DoD exit gate.")
        low = _norm(body).lower()
        self.assertIn("symmetric", low,
                      "AC6: docs/overview.md must frame the two gates as symmetric.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
