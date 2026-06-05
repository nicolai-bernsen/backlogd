"""Regression net for NB-429 — the Definition of Done is wired, not declared-not-wired.

NB-429 closes the single genuine Scrum-fidelity gap at 1.0: the scrum skill *declared*
the Definition of Done at ``docs/scrum/definition-of-done.md`` but flagged it as a
"target — not yet wired", while ``/backlogd:review`` already gated against "AC + DoD".
The fix de-stales that flag and pins the standing-DoD-vs-per-problem-AC distinction.

The AC bucket split, and how each is proven here:

  - AC1 ``[test]`` — ``test -s docs/scrum/definition-of-done.md`` — the DoD artifact
    exists, is non-empty, AND carries a concrete checkable DoD (not just a stub).
    This is the one AC the runner can exercise *directly* (a filesystem assertion):
    ``DefinitionOfDoneArtifactTest`` re-implements ``test -s`` in Python and asserts the
    standing-bar substance (tests pass / CI green / no secrets / docs updated) is present.

  - AC4 ``[review]``, but filesystem-assertable — the "target — not yet wired" flag *on
    the DoD* is removed once wired. This is the core defect the issue names, and it is a
    flag-*removal* a test can pin exactly (same discipline as
    ``scripts/test_retro.py``'s "Out of scope today" removal): ``DoDFlagRemovedTest``
    asserts the scrum SKILL's DoD lines say *wired* and no longer carry the
    not-yet-wired flag or the stale NB-331 framing — with a guard proving the pin
    actually bites the pre-fix wording (no tautological green).

  - AC2 ``[review]`` — "``/backlogd:review`` reads and enforces the DoD in addition to
    the AC; its verdict cites both" — a judgement an agent renders from prose at verdict
    time, NOT a behaviour a runner can exercise (proving "the reviewer obeys the
    instruction" is a tautology against the doc that *is* the instruction — see the
    docstring of ``scripts/test_reviewer_standards_enforcement.py``). So
    ``ReviewerCitesBothTest`` pins the load-bearing prose invariant the AC depends on:
    both reviewer surfaces cite the **Definition of Done** alongside the Acceptance
    Criteria, the verdict template carries a DoD section, and the merge condition names
    "every DoD line" — so an incidental reword can't silently un-wire the enforcement.

  - AC3 ``[review]`` — "the DoD is authored agent-checkable (crisp assertions),
    consistent with the NB-380 standards format". This is mostly a taste call (named
    partly untestable in the report); its *structural* half — that the DoD is a checklist
    of concrete observable rules, not a prose essay — is pinned by
    ``DefinitionOfDoneArtifactTest.test_dod_is_a_hard_rules_checklist_not_an_essay`` and
    the substance pins beside it. Whether each line is "crisp enough" stays a judgement.

  - AC5 ``[manual]`` — "reads unmistakably" is a PO taste call (named untestable in the
    report). Its *structural* half is pinnable and pinned here:
    ``DoDvsACDistinctionPresentTest`` asserts both docs contrast DoD (standing) against
    AC (per-problem). The "unmistakably-clear" judgement stays with the PO.

Run from the repo root:
    python -m pytest scripts/test_definition_of_done_wired.py
    python -m unittest discover -s scripts -p 'test_*.py'    # CI uses this
"""

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

DOD_PATH = REPO_ROOT / "docs" / "scrum" / "definition-of-done.md"
SCRUM_SKILL = REPO_ROOT / "skills" / "scrum" / "SKILL.md"
MAPPING_PATH = REPO_ROOT / "docs" / "scrum" / "mapping.md"
REVIEWER_AGENT = REPO_ROOT / "agents" / "reviewer.md"
REVIEW_CMD = REPO_ROOT / "commands" / "review.md"


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def _norm(text: str) -> str:
    """Whitespace-collapse so a content pin survives prose line-wrapping."""
    return " ".join(text.split())


# The artifacts section's DoD entry is the line AC4 is about — the one that used to read
# "Definition of Done → …definition-of-done.md — 🎯 Target — not yet wired (NB-331)". We
# isolate exactly that entry (from the "Definition of Done →" lead-in up to the next
# artifact arrow / blank-line break) and assert on it, rather than a fuzzy whole-document
# proximity window. A crude window false-positives on the legitimate, reworded sentence
# "the DoD is fully wired … the /backlogd:scope command is *not yet wired*", which is
# correct prose — the not-yet-wired clause is about the commands, not the DoD.
_TARGET_FLAG = "🎯"  # the inline "Target — not yet wired" flag glyph


def _dod_artifact_entry(raw_text: str) -> str:
    """Return the normalised text of the artifacts-table DoD entry — the 'Definition of
    Done →' lead-in through to (but not including) the next artifact arrow or the table
    break. This is the precise span AC4 governs. Empty string if not found."""
    body = _norm(raw_text)
    lead = "**Definition of Done →"
    i = body.find(lead)
    if i == -1:
        # Fall back to the un-bolded lead-in form.
        lead = "Definition of Done →"
        i = body.find(lead)
        if i == -1:
            return ""
    rest = body[i + len(lead):]
    # The entry ends at the next artifact arrow ("→") or the "See …" trailer the SKILL
    # closes the entry with — whichever comes first — so we don't swallow neighbours.
    end_candidates = [p for p in (rest.find(" → "), rest.find("See ")) if p != -1]
    end = min(end_candidates) if end_candidates else len(rest)
    return (lead + rest[:end]).strip()


def _dod_flagged_not_yet_wired(raw_text: str) -> bool:
    """True iff the artifacts-table DoD entry still carries the 'Target — not yet wired'
    flag (the glyph or the phrase landing *on the DoD entry itself*). Shared by the AC4
    test and its bites-the-pre-fix-wording self-guard so both exercise identical logic."""
    entry = _dod_artifact_entry(raw_text)
    if not entry:
        return False
    low = entry.lower()
    return (_TARGET_FLAG in entry) or ("not yet wired" in low)


class DefinitionOfDoneArtifactTest(unittest.TestCase):
    """AC1 ``[test]`` — ``test -s docs/scrum/definition-of-done.md``: the DoD artifact
    exists with a concrete, checkable DoD."""

    def test_dod_file_exists_and_is_non_empty(self):
        # The literal AC command is `test -s <path>` — true iff the file exists and has
        # size > 0. Re-implement it as a filesystem assertion (not a shell-out, so it
        # holds on every platform CI runs on, and never false-greens where `test` is
        # absent — cf. the rg-vacuity gotcha in the repo memory).
        self.assertTrue(DOD_PATH.is_file(),
                        f"{DOD_PATH.relative_to(REPO_ROOT)} must exist (AC1 `test -s`).")
        self.assertGreater(DOD_PATH.stat().st_size, 0,
                           f"{DOD_PATH.relative_to(REPO_ROOT)} must be non-empty "
                           f"(AC1 `test -s`).")

    def test_dod_carries_the_standing_bar_substance(self):
        # AC1 asks for a *concrete, checkable* DoD — "tests pass, standards adhered, no
        # regressions, docs updated as applicable, etc." A non-empty file of prose would
        # pass `test -s` while failing the AC's intent, so pin that the floor's
        # load-bearing rules are actually present (not a tautology-stub).
        body = _norm(_read(DOD_PATH))
        self.assertIn("Definition of Done", body)
        # Every increment must clear it regardless of its specific AC — the standing bar.
        self.assertIn("Every line in the issue's `## Acceptance Criteria` is met", body,
                      "DoD must require the AC to be met by the diff.")
        self.assertIn("automated test", body,
                      "DoD must require testable AC to be covered by an automated test.")
        self.assertIn("CI is green", body,
                      "DoD must require CI green on the PR head.")
        self.assertIn("No secrets", body,
                      "DoD must forbid secrets/tokens/.env files in the diff.")

    def test_dod_is_a_hard_rules_checklist_not_an_essay(self):
        # The artifact is a checklist of observable rules. Require it to actually carry
        # checklist items (`- [ ]` task lines), so a future reword into prose-essay form
        # (which would re-open the "is this checkable?" question AC1 settles) trips CI.
        raw = _read(DOD_PATH)
        checklist_lines = [ln for ln in raw.splitlines() if ln.lstrip().startswith("- [ ]")]
        self.assertGreaterEqual(
            len(checklist_lines), 5,
            "the DoD must be a checklist of concrete rules (>=5 `- [ ]` items), "
            "not an essay — AC1 asks for a *checkable* DoD.")


class DoDFlagRemovedTest(unittest.TestCase):
    """AC4 — the scrum skill's "target — not yet wired" flag *on the DoD* is removed
    once wired (the core defect: the DoD was enforced but flagged as not-wired)."""

    def test_skill_declares_the_dod_wired(self):
        # The artifacts section's DoD entry must now state the wired reality. Pre-fix it
        # carried "🎯 Target — not yet wired" / an NB-331 "not yet wired" follow-up; the
        # de-staled line says the reviewer enforces it on every increment. Assert on the
        # DoD *entry* specifically so a "wired" claim about something else can't satisfy it.
        entry = _dod_artifact_entry(_read(SCRUM_SKILL))
        self.assertTrue(entry, "could not locate the artifacts-table DoD entry in "
                               "skills/scrum/SKILL.md (AC4).")
        self.assertIn(
            "the reviewer enforces it on every increment", entry,
            "the DoD artifacts entry in skills/scrum/SKILL.md must declare it wired "
            "(the reviewer enforces it on every increment) — AC4.")

    def test_dod_neighbourhood_no_longer_flags_not_yet_wired(self):
        # The crux of AC4: the DoD must not be described as not-yet-wired anywhere it is
        # named. We don't forbid the generic inline-flag *legend* (`🎯 Target — not yet
        # wired.` still legitimately documents the convention for genuinely-unwired
        # command-level work). We forbid the not-yet-wired claim landing *near* a DoD
        # mention in the normalised body (the flag and the mention can sit on separate
        # physical lines, so this is a proximity check, not a per-line one).
        self.assertFalse(
            _dod_flagged_not_yet_wired(_read(SCRUM_SKILL)),
            "the DoD must not be flagged 'not yet wired' anywhere it is named in "
            "skills/scrum/SKILL.md — the reviewer already gates against it (AC4).")

    def test_skill_drops_the_stale_nb331_not_yet_wired_followup(self):
        # The stale flag pointed at NB-331 as the "not yet wired" follow-up. Once wired,
        # the skill must not still route the DoD to NB-331 as un-wired work. (NB-331 may
        # be referenced historically, but not as the open wiring task — and the dev's
        # report says no NB-331 reference remains.)
        body = _norm(_read(SCRUM_SKILL))
        self.assertNotIn("NB-331", body,
                         "skills/scrum/SKILL.md must drop the stale NB-331 "
                         "'DoD not yet wired' follow-up once the DoD is wired (AC4).")

    def test_pins_would_bite_the_pre_fix_wording(self):
        # Guard against a tautological green: prove the AC4 assertions actually FIRE on
        # the superseded wording. If the pre-fix text passed these pins, they'd prove
        # nothing. The pre-fix DoD *artifact entry* (reconstructed):
        stale_entry = (
            "**Definition of Done → "
            "[`docs/scrum/definition-of-done.md`](../../docs/scrum/definition-of-done.md)** "
            "— 🎯 **Target — not yet wired.** Follow-up NB-331. "
            "See ../../docs/scrum/mapping.md for the full table.")
        # The flag detector must bite the stale entry (both the glyph and the phrase form).
        self.assertTrue(
            _dod_flagged_not_yet_wired(stale_entry),
            "the AC4 flag detector must fire on the pre-fix DoD artifact entry.")
        # And the "wired" pin must be ABSENT on the stale entry — proving the live
        # assertion (entry must say 'the reviewer enforces it on every increment') has
        # real teeth and isn't vacuously satisfiable.
        self.assertNotIn("the reviewer enforces it on every increment",
                         _dod_artifact_entry(stale_entry))
        # The NB-331 follow-up pin (assertNotIn in the live test) must have something to
        # bite in the stale text.
        self.assertIn("NB-331", _norm(stale_entry))

    def test_detector_does_not_false_fire_on_correct_wired_prose(self):
        # The crux that makes the AC4 detector *correct* (not just strict): the shipped
        # prose legitimately says "the DoD is fully wired … the `/backlogd:scope` command
        # is *not yet wired*". The not-yet-wired clause is about the COMMANDS, not the
        # DoD — so the detector must NOT fire on the real post-fix artifact entry, nor on
        # this reconstructed correct form. A blunt whole-doc proximity check would
        # false-positive here and force removal of true prose.
        correct_entry = (
            "**Definition of Done → "
            "[`docs/scrum/definition-of-done.md`](../../docs/scrum/definition-of-done.md)** "
            "— wired: the reviewer enforces it on every increment. "
            "See ../../docs/scrum/mapping.md for the full table.")
        self.assertFalse(
            _dod_flagged_not_yet_wired(correct_entry),
            "the AC4 detector must not fire on a correctly-wired DoD entry.")
        # And the generic inline-flag legend ("🎯 Target — not yet wired") plus a
        # commands-are-unwired sentence elsewhere in the skill must not trip it either.
        self.assertFalse(
            _dod_flagged_not_yet_wired(_read(SCRUM_SKILL)),
            "the AC4 detector must not fire on the shipped skill (legend + "
            "commands-not-yet-wired prose are legitimate).")


class ReviewerCitesBothTest(unittest.TestCase):
    """AC2 — ``/backlogd:review`` reads and enforces the DoD in addition to the AC; its
    verdict cites both. ``[review]`` kind → pin the prose invariant, not the behaviour."""

    REVIEWER_SURFACES = (REVIEWER_AGENT, REVIEW_CMD)

    def test_both_surfaces_name_the_dod_alongside_the_ac(self):
        for path in self.REVIEWER_SURFACES:
            with self.subTest(surface=path.name):
                body = _norm(_read(path))
                self.assertIn(
                    "Definition of Done", body,
                    f"{path.relative_to(REPO_ROOT)} must name the Definition of Done "
                    f"(AC2 — the reviewer enforces it alongside the AC).")
                self.assertIn(
                    "docs/scrum/definition-of-done.md", body,
                    f"{path.relative_to(REPO_ROOT)} must point at the DoD artifact "
                    f"the reviewer enforces (AC2).")

    def test_verdict_template_carries_a_definition_of_done_section(self):
        # AC2's "its verdict cites both" — the verdict template in BOTH surfaces has a
        # `Definition of Done` block beside the `Acceptance criteria` block, and the
        # report counts carry a `DoD:` line. A reword that drops the DoD section
        # would un-cite the DoD half of the verdict.
        #
        # NB-415 migrated the verdict-state vocabulary off status emoji (✅/❌/❔) onto a
        # `- [x]` / `- [ ]` checkbox + bold MET/UNMET/NEEDS-PO label, and the report
        # count line off `DoD: ✅{n}…` onto `DoD: met={n} unmet={n} needs-po={n}`. The
        # pin tracks the new vocabulary.
        for path in self.REVIEWER_SURFACES:
            with self.subTest(surface=path.name):
                body = _norm(_read(path))
                self.assertIn(
                    "Acceptance criteria", body,
                    f"{path.relative_to(REPO_ROOT)} verdict must have an Acceptance "
                    f"criteria section (AC2 — cites both).")
        # The agent surface owns the `DoD:` count summary line (emoji-free post-NB-415).
        agent_body = _norm(_read(REVIEWER_AGENT))
        self.assertIn(
            "DoD: met=", agent_body,
            "agents/reviewer.md report must carry a `DoD:` count line so the "
            "verdict cites the DoD walk, not only the AC walk (AC2).")

    def test_merge_condition_requires_every_dod_line_green(self):
        # The enforcement teeth: the happy-path merge condition must require every DoD
        # line MET, weighing a red DoD line like a red AC line. This is *why* the verdict
        # citing the DoD matters — it gates the merge. NB-415 migrated the merge-condition
        # vocabulary off the `✅` glyph onto the text label `MET` (same logic, new words).
        body = _norm(_read(REVIEW_CMD))
        self.assertIn(
            "every DoD line MET", body,
            "commands/review.md merge condition must require every DoD line MET "
            "(AC2 — the DoD is enforced, not just cited).")


class DoDvsACDistinctionPresentTest(unittest.TestCase):
    """AC5 ``[manual]`` — distinguish DoD (standing, every increment) from AC
    (per-problem) in the docs. The *structural* half is pinnable; "reads unmistakably"
    stays a PO judgement (reported as untestable)."""

    def test_dod_doc_contrasts_standing_dod_against_per_problem_ac(self):
        body = _norm(_read(DOD_PATH))
        # The distinction must be drawn explicitly: DoD = standing, AC = per-problem.
        self.assertIn("standing", body.lower(),
                      "definition-of-done.md must call the DoD *standing* (AC5).")
        self.assertIn("per-problem", body.lower(),
                      "definition-of-done.md must call the AC *per-problem* (AC5).")
        # And it must name both commitments side by side (not conflate them).
        self.assertIn("DoD vs AC", body,
                      "definition-of-done.md must carry a DoD-vs-AC contrast (AC5).")

    def test_mapping_does_not_conflate_the_two_commitments(self):
        body = _norm(_read(MAPPING_PATH))
        self.assertIn("standing", body.lower(),
                      "mapping.md must distinguish the standing DoD from the AC (AC5).")
        self.assertIn("per-problem", body.lower(),
                      "mapping.md must call the Sprint Goal / AC *per-problem* (AC5).")
        # The reviewer holding each diff against BOTH is the load-bearing claim that
        # keeps the two from being conflated.
        self.assertIn("both", body.lower(),
                      "mapping.md must state the reviewer gates against both AC and DoD "
                      "(AC5 — the two commitments aren't conflated).")


if __name__ == "__main__":
    unittest.main(verbosity=2)
