"""Tester-side widening for NB-428 — Definition of Ready, enforcement + anti-vacuity.

The developer's `scripts/test_definition_of_ready.py` pins the *presence* of NB-428's
load-bearing prose across the five touched surfaces (the DoR doc, refiner, scope, mapping,
overview) so an incidental reword trips CI. This file is the **tester's widening** to the
full AC contract. It does NOT restructure or duplicate the developer's file; it adds the
three contract corners the presence-pins left thin, plus an anti-vacuity guard that makes
the family's "anti-vacuity verified" claim true *in the suite*:

  1. AC1 — the enforcement half. AC1 says a problem **cannot become ready/solvable until**
     it clears the floor. Presence of the three rules is necessary but not sufficient: the
     gate must *route an unmet rule to the PO and stop*, never guess past it. Pinned by
     GateStopsRatherThanGuessing — the "until" in AC1.
  2. AC2/AC3 — symmetric framing across all three runtime surfaces. The developer pinned
     the Socratic questions / pre-mortem / question-then-criticism pairing in the DoR doc
     and refiner; this file pins the same in commands/scope.md's dispatch envelope so the
     gate the scrum-master *dispatches* carries the interrogate-not-generate contract too
     (otherwise scope could drift out of step with the doc it cites). Pinned by
     ScopeDispatchCarriesTheSocraticContract.
  3. Anti-vacuity. The whole presence-pin family is only worth its bytes if the pins would
     actually fail when the prose drifts. AntiVacuityGuard proves the matcher distinguishes
     a present needle from an absent one (a vacuous `assertIn("", ...)`-style pin would pass
     against anything) — the discipline test_ship_on_green_and_manual.py applies to its `rg`
     re-impl, made explicit here for the prose-pin family.

Every NB-428 AC is `[review]` except AC5 (`[manual]`): whether the prose is *sound*, the
gate truly *non-generative*, and the framing *honest* stay the reviewer's call. These pins
(like the developer's) guard the strings against silent drift; they do not pre-litigate the
verdict. AC5's first-use judgement (the PO running `/backlogd:scope` on a raw idea and
confirming the gate interrogates without generating/ranking) is named untestable in code —
the testable sliver (the out-of-scope guard is present in every surface) is already pinned
by the developer's HoldsTheLineNotGenerativeNotPrioritization.

CI runs `python3 -m unittest discover -s scripts -p 'test_*.py'` from the repo root
(see .github/workflows/ci.yml), so this lives in scripts/ as a stdlib unittest. It does
NOT do a git-diff / whole-worktree footprint scan (the NB-418 bug that false-fails every
other unit's local suite).

Run from the repo root:
    python -m unittest scripts.test_definition_of_ready_enforcement
    python scripts/test_definition_of_ready_enforcement.py
"""

import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

DOR = REPO_ROOT / "docs" / "scrum" / "definition-of-ready.md"
REFINER = REPO_ROOT / "agents" / "refiner.md"
SCOPE_CMD = REPO_ROOT / "commands" / "scope.md"


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def _norm(text: str) -> str:
    """Whitespace-collapse so a content pin survives prose line-wrapping.

    Mirrors the developer's `_norm`: drops a leading Markdown blockquote marker (`> `) per
    line *before* collapsing, so a phrase that wraps across lines inside scope.md's
    blockquote dispatch envelope still matches (an interior `>` would otherwise land
    mid-phrase). Kept identical on purpose — the two files must agree on what "the prose
    says X" means."""
    lines = [ln.lstrip().lstrip(">").lstrip() if ln.lstrip().startswith(">") else ln
             for ln in text.splitlines()]
    return " ".join(" ".join(lines).split())


class GateStopsRatherThanGuessing(unittest.TestCase):
    """AC1 (the enforcement half — the *until*): a problem cannot become ready until it
    clears the floor, which means an unmet rule is **surfaced to the PO and the gate stops
    / does not guess past it** — not merely that the three rules are named. Pinning only the
    rules' presence (the developer's DorFloorRules) leaves "cannot become ready until"
    unproven; this class pins the routing-and-stop that makes the gate a gate."""

    def test_dor_doc_surfaces_open_decisions_and_stops(self):
        low = _norm(_read(DOR)).lower()
        # An open one-way door is a PO call the gate surfaces and halts on, not a guess.
        self.assertIn("an open one-way door is a po decision", low,
                      "AC1: the DoR doc must frame an open one-way-door decision as a PO "
                      "call, not a developer guess.")
        self.assertIn("surface it and stop", low,
                      "AC1: the DoR doc must say an unmet rule is surfaced and the gate "
                      "stops (it does not shape around / guess past it).")
        # A standards conflict is likewise surfaced, not silently shaped around.
        self.assertIn("not shaped around silently", low,
                      "AC1: the DoR doc must say a standards conflict is surfaced, not "
                      "shaped around silently.")

    def test_refiner_routes_a_dor_gap_into_ambiguities_and_does_not_guess(self):
        low = _norm(_read(REFINER)).lower()
        # The refiner runs the gate (step 5) and routes any gap to the PO via step 6's
        # ambiguities — the mechanism by which "cannot become ready until" is enforced.
        self.assertIn("raise it in step 6's ambiguities", low,
                      "AC1: agents/refiner.md must route a DoR gap into step 6's "
                      "ambiguities (surfaced to the PO).")
        self.assertIn("let the scrum-master surface it", low,
                      "AC1: agents/refiner.md must hand a DoR gap to the scrum-master to "
                      "surface (the refiner does not resolve it itself).")
        self.assertIn("do not guess past it", low,
                      "AC1: agents/refiner.md must say it does not guess past an unmet DoR "
                      "rule (the gate stops).")

    def test_refiner_step6_includes_dor_gaps_explicitly(self):
        low = _norm(_read(REFINER)).lower()
        # Step 6 (flag ambiguities) must name the DoR gap kinds, so a found gap is a
        # first-class PO question — not silently dropped.
        self.assertIn("including any definition-of-ready gap from step 5", low,
                      "AC1: agents/refiner.md step 6 must explicitly fold any "
                      "Definition-of-Ready gap into the ambiguities it surfaces.")

    def test_scope_dispatch_raises_unmet_dor_rule_as_ambiguity(self):
        body = _norm(_read(SCOPE_CMD))
        # The scrum-master's dispatch must instruct the refiner to raise an unmet DoR rule
        # as an ambiguity — the orchestrator side of the stop-don't-guess contract.
        self.assertIn("Raise any unmet DoR rule as an ambiguity", body,
                      "AC1: commands/scope.md dispatch must tell the refiner to raise any "
                      "unmet DoR rule as an ambiguity (surfaced to the PO, gate stops).")
        # And §3's prose must say scope acts on what the gate surfaces (it doesn't auto-pass).
        self.assertIn("you act on what it surfaces", body,
                      "AC1: commands/scope.md must say the scrum-master acts on what the "
                      "DoR gate surfaces.")


class ScopeDispatchCarriesTheSocraticContract(unittest.TestCase):
    """AC2/AC3 (symmetric framing across runtime surfaces): the developer pinned the three
    Socratic questions, the pre-mortem, and the question-then-criticism pairing in the DoR
    doc and the refiner. The third runtime surface — commands/scope.md's *dispatch
    envelope*, the instruction the scrum-master actually hands the refiner — must carry the
    same interrogate-not-generate contract, or scope can drift out of step with the doc it
    cites. (Whether the wording is *well-judged* stays [review].)"""

    def test_scope_dispatch_carries_premortem_as_po_input(self):
        body = _norm(_read(SCOPE_CMD))
        low = body.lower()
        # AC3: the devil's-advocate pre-mortem is in the dispatch, framed as the PO's input.
        self.assertIn("devil's-advocate pre-mortem", low,
                      "AC3: commands/scope.md dispatch must name the devil's-advocate "
                      "pre-mortem.")
        self.assertIn("assume this shipped and was wrong", low,
                      "AC3: commands/scope.md dispatch must carry the pre-mortem question "
                      "('assume this shipped and was wrong — why?').")
        self.assertIn("record the PO's", body,
                      "AC3: commands/scope.md must record the PO's answers (the pre-mortem "
                      "is the PO's input, not the agent's invention).")

    def test_scope_dispatch_interrogates_not_generates(self):
        low = _norm(_read(SCOPE_CMD)).lower()
        # AC2: interrogate, don't generate — the discipline phrase in the dispatch itself.
        self.assertIn("interrogating, not generating", low,
                      "AC2: commands/scope.md dispatch must frame the move as "
                      "interrogating, not generating.")
        # And the gate does not answer the Socratic questions for the PO.
        self.assertIn("do **not** answer them yourself", low,
                      "AC2: commands/scope.md dispatch must say the gate does not answer "
                      "the Socratic questions for the PO.")

    def test_scope_dispatch_carries_all_three_socratic_questions(self):
        low = _norm(_read(SCOPE_CMD)).lower()
        # AC2: the three questions are in the dispatch the scrum-master hands the refiner.
        self.assertIn("what is the real problem", low,
                      "AC2: commands/scope.md dispatch must ask what the real problem is.")
        self.assertIn("who fails if it ships wrong", low,
                      "AC2: commands/scope.md dispatch must ask who fails if it ships "
                      "wrong.")
        self.assertIn("what would make this fail", low,
                      "AC2: commands/scope.md dispatch must ask what would make this fail.")


class AntiVacuityGuard(unittest.TestCase):
    """Anti-vacuity: the presence-pin family (this file + the developer's) is only worth its
    bytes if the pins would *fail* when the prose drifts. A pin like `assertIn("", body)` or
    `assertIn(needle, body)` where `needle` is the empty string passes against any text and
    proves nothing. This guard proves the matcher actually discriminates against the real
    DoR doc — a present needle is found, a clearly-absent one is not — so the family's
    'anti-vacuity verified' claim is demonstrated in the suite, not just asserted in a
    docstring. (Same discipline test_ship_on_green_and_manual.py applies to its `rg`
    re-implementation.)"""

    def test_present_needle_is_found(self):
        # A string that genuinely lives in the DoR doc — the matcher must find it.
        self.assertIn("crisp outcome", _norm(_read(DOR)).lower(),
                      "anti-vacuity: a string known to be present must be found (else the "
                      "matcher / fixture is broken and every presence-pin is meaningless).")

    def test_absent_needle_is_not_found(self):
        # A string that must NOT be in a hard-rules DoR doc. If this is ever found, either
        # the doc regressed into generative territory or the matcher is vacuous — both fatal
        # to the pin family.
        low = _norm(_read(DOR)).lower()
        sentinel = "the gate generates and ranks candidate features for the po"
        self.assertNotIn(sentinel, low,
                         "anti-vacuity: a clearly-absent sentinel must NOT match — proves "
                         "the pins discriminate (and that the DoR did not regress into "
                         "generating/ranking, the very line AC5 forbids).")

    def test_norm_is_not_destructive(self):
        # The _norm used by both pin files must not collapse the text to nothing or strip
        # content words — a broken _norm would make every assertIn pass vacuously.
        normed = _norm(_read(DOR))
        self.assertGreater(len(normed), 500,
                           "anti-vacuity: _norm must preserve the DoR doc's content (a "
                           "_norm that emptied the text would make every pin vacuous).")
        self.assertIn("Socratic", normed,
                      "anti-vacuity: _norm must preserve content words (not strip them to "
                      "whitespace).")


if __name__ == "__main__":
    unittest.main(verbosity=2)
