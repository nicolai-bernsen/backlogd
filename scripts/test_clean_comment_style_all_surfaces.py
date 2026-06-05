"""Regression net for NB-415 -- extend the clean Linear-comment style to the reviewer +
review-rollup (and tester + scrum-master) comment surfaces; drop status emoji + tables.

NB-359 gave only the *developer* subagent the clean Linear-comment output style
(``output-styles/linear-comment.md``: no tables, no status/checkmark emoji,
language-tagged fences, max two-level nesting). NB-415 extends that to **every** backlogd
agent-authored comment surface: the ``**[backlogd reviewer]**`` work log, the
``**[backlogd review]**`` verdict rollup (``commands/review.md`` section 4 template +
``agents/reviewer.md`` verdict body), the ``**[backlogd tester]**`` comment, and the
scrum-master ``**[backlogd]**`` brief. The status glyphs (the green-check, the cross, the
question-mark, the memo) are replaced by a ``- [x]`` / ``- [ ]`` checkbox + a leading bold
state label (``MET`` / ``UNMET`` / ``NEEDS-PO`` / ``AWAITING-PO`` / ``NO-STANDARD``), keeping
each line's ``[test]`` / ``[manual]`` / ``[review]`` kind tag.

This file is the backlogd **tester's** independent evidence. The developer adapted the
*existing* glyph-pinning tests (test_reviewer_block_outcome.py, test_scrum_master_block_-
routing.py, test_definition_of_done_wired.py, test_ship_on_green_and_manual.py) to the new
vocabulary and added ``assertNotIn(BLOCK_GLYPH)`` guards on the *block* glyph only. What
was NOT yet pinned, and is the AC contract this file proves:

  - AC1 / AC5 -- the verdict-display surfaces carry **zero** of the FULL status-glyph set
    AC1 names (the green-check, the cross, the question-mark, the memo), not only the block
    glyph. ``NoStatusGlyphInVerdictSurfacesTest`` asserts each glyph is absent from
    ``commands/review.md`` section 4 + ``agents/reviewer.md``, and
    ``PinsBiteThePreChangeBaselineTest`` proves (via ``git show HEAD:<file>``) that the
    pre-change files DID carry these glyphs, so a green here is a genuine pre/post anchor,
    never a tautology. This is the literal evidence for both AC1 (the verdict no longer uses
    the status glyphs) and AC5 (the converse: their *absence* is what the display-surface
    tests now assert).
  - AC1 (positive half) -- the surfaces adopt the Linear-clean convention: the verdict
    templates use ``- [x]`` / ``- [ ]`` checkboxes + the bold state labels. Pinned by
    ``CheckboxStateConventionTest``.
  - AC2 -- the reviewer (agent + skill), tester, and scrum-master (review.md section 4
    rollup + handoff.md brief) surfaces reference ``output-styles/linear-comment.md`` the
    same prompt-level way the developer does. Pinned by ``AllSurfacesReferenceTheStyleTest``
    (the NB-359 sibling test_linear_comment_style.py covers only the *developer* surface).
  - AC3 -- the per-AC verdict line keeps each AC's kind tag (``[test]`` / ``[manual]`` /
    ``[review]``) alongside the new bold state label. Pinned by ``KindTagPreservedTest``.
  - AC5 (literal bar) -- no ``scripts/test_*.py`` *asserts* a status glyph as required
    content (the glyphs survive only inside comments/escapes / ``assertNotIn`` absence
    guards, never inside a positive assertion). Pinned by ``NoLiveTestAssertsTheGlyphsTest``.
  - AC6 -- ``docs/specialists.md`` notes the style applies to ALL agent comment surfaces,
    naming the reviewer + tester + scrum-master, not just the developer. Pinned by
    ``SpecialistsNotesAllSurfacesTest``.

  - AC4 is ``[manual]`` (a PO eyeball on the live Linear render) -- NOT covered here; named
    untestable-in-code in the tester's report.

These are prose-in-markdown ACs (the unit ships command/agent/skill/doc prose, no runnable
behaviour), so -- exactly as test_linear_comment_style.py does -- every assertion targets a
DURABLE token (a glyph, a file path, the ``MET``/``[{kind}]`` vocabulary), never a full
sentence. Every status glyph in this source is kept as a ``\\Uxxxxxxxx`` escape (in the
``STATUS_GLYPHS`` map) so the source stays pure ASCII: it never trips a Windows cp1252
round-trip, AND it can never become its own AC5 offender. Glyphs are membership-tested,
never printed and never written as literal characters in prose or messages.

Why stdlib only: CI runs ``python -m unittest discover -s scripts -p 'test_*.py'`` on a
bare Python with no ``pip install`` (the repo test convention).

Run from the repo root:  python scripts/test_clean_comment_style_all_surfaces.py
(or collected by ``python -m unittest discover -s scripts -p 'test_*.py'``).
"""

import pathlib
import re
import subprocess
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"

REVIEW_CMD = REPO_ROOT / "commands" / "review.md"
REVIEWER_AGENT = REPO_ROOT / "agents" / "reviewer.md"
REVIEWER_SKILL = REPO_ROOT / "skills" / "reviewer" / "SKILL.md"
TESTER_AGENT = REPO_ROOT / "agents" / "tester.md"
HANDOFF_SKILL = REPO_ROOT / "skills" / "solve" / "handoff.md"
SPECIALISTS = REPO_ROOT / "docs" / "specialists.md"
STYLE = REPO_ROOT / "output-styles" / "linear-comment.md"

# The two verdict-DISPLAY surfaces AC1 names directly: the scrum-master's section 4 rollup
# template and the reviewer's verdict body. These are the comment surfaces the PO reads on
# Linear; they must be entirely free of the status-glyph set.
VERDICT_DISPLAY_SURFACES = (REVIEW_CMD, REVIEWER_AGENT)

# Status / checkmark glyphs kept as \\Uxxxxxxxx escapes (NOT literal characters) so this
# source stays pure ASCII: membership-tested only, never printed, and (crucially) never an
# AC5 offender against itself. These are exactly the four glyphs AC1 enumerates: the
# white-heavy-check-mark, the cross-mark, the white-question-mark-ornament, and the memo.
STATUS_GLYPHS = {
    "CHECK": "\U00002705",    # white heavy check mark
    "CROSS": "\U0000274c",    # cross mark
    "QUESTION": "\U00002754",     # white question mark ornament
    "MEMO": "\U0001f4dd",     # memo
}
# The block glyph too (the developer already guards it on the NO-STANDARD lines; included
# here so the FULL display-glyph vocabulary is swept in one place).
BLOCK_GLYPH = "\U0001f6ab"   # no entry sign


def _read(p):
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def _norm(text):
    """Whitespace-collapse so a content pin survives prose line-wrapping."""
    return " ".join(text.split())


def _git_show_head(rel_path):
    """The file's content at HEAD (the pre-change baseline), or '' if unavailable.

    Used only by the anti-tautology guard to prove the live pins would FIRE on the
    pre-NB-415 wording. Run from the repo root so the path resolves in this worktree."""
    out = subprocess.run(
        ["git", "show", f"HEAD:{rel_path}"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return out.stdout if out.returncode == 0 else ""


class NoStatusGlyphInVerdictSurfacesTest(unittest.TestCase):
    """AC1 / AC5 -- the verdict-display surfaces (commands/review.md section 4 template +
    agents/reviewer.md verdict body) carry ZERO of the status-glyph set AC1 names."""

    def test_no_status_glyphs_in_review_command(self):
        text = _read(REVIEW_CMD)
        self.assertTrue(text, "commands/review.md must exist (AC1).")
        for name, glyph in {**STATUS_GLYPHS, "BLOCK": BLOCK_GLYPH}.items():
            self.assertNotIn(
                glyph, text,
                f"commands/review.md must carry no {name} status emoji -- AC1 replaced "
                f"the check/cross/question/memo verdict glyphs with the checkbox + bold-label convention.",
            )

    def test_no_status_glyphs_in_reviewer_agent(self):
        text = _read(REVIEWER_AGENT)
        self.assertTrue(text, "agents/reviewer.md must exist (AC1).")
        for name, glyph in {**STATUS_GLYPHS, "BLOCK": BLOCK_GLYPH}.items():
            self.assertNotIn(
                glyph, text,
                f"agents/reviewer.md must carry no {name} status emoji -- AC1 replaced "
                f"the check/cross/question/memo verdict glyphs with the checkbox + bold-label convention.",
            )

    def test_canonical_style_forbids_status_emoji(self):
        # The style file the surfaces inherit must itself ban status emoji (so the
        # convention has a single source of truth). Token-anchored, not full-sentence.
        low = _read(STYLE).lower()
        self.assertIn("emoji", low, "output-styles/linear-comment.md must constrain emoji.")
        self.assertTrue(
            re.search(r"no status[\w\s,/-]*emoji|status[\w\s,/-]*emoji[\w\s,/-]*(noise|forbidden|never)", low),
            "output-styles/linear-comment.md must forbid status/checkmark emoji outright (AC1).",
        )


class PinsBiteThePreChangeBaselineTest(unittest.TestCase):
    """Anti-tautology guard: prove the NoStatusGlyph* pins would FIRE on the pre-NB-415
    wording. If the pre-change files had NO glyphs, the assertions above would prove
    nothing. We read each surface at HEAD and confirm the status glyphs WERE present there
    (and that the live worktree file has dropped them)."""

    def test_pre_change_surfaces_carried_the_glyphs(self):
        any_baseline_seen = False
        for path in VERDICT_DISPLAY_SURFACES:
            rel = path.relative_to(REPO_ROOT).as_posix()
            head = _git_show_head(rel)
            if not head:
                # No git / detached baseline: skip the guard for this surface rather
                # than fail (the live pins still stand on their own).
                continue
            any_baseline_seen = True
            head_glyph_total = sum(head.count(g) for g in STATUS_GLYPHS.values())
            self.assertGreater(
                head_glyph_total, 0,
                f"expected the pre-NB-415 {rel} to carry status glyphs (so the live "
                f"absence pins are non-tautological); found none at HEAD.",
            )
            live_glyph_total = sum(_read(path).count(g) for g in STATUS_GLYPHS.values())
            self.assertEqual(
                live_glyph_total, 0,
                f"the live {rel} must have dropped every status glyph (AC1).",
            )
        if not any_baseline_seen:
            self.skipTest("no HEAD baseline available for the verdict surfaces "
                          "(git show returned nothing) -- live pins still hold.")


class CheckboxStateConventionTest(unittest.TestCase):
    """AC1 (positive half) -- the verdict templates adopt the Linear-clean convention:
    `- [x]` / `- [ ]` checkbox + a leading bold state label (MET / UNMET / NEEDS-PO)."""

    def test_review_template_uses_checkbox_and_bold_labels(self):
        body = _norm(_read(REVIEW_CMD))
        self.assertIn("- [x] **MET**", body,
                      "commands/review.md section 4 template must show a met line as a "
                      "`- [x] **MET**` checkbox + bold label (AC1).")
        self.assertIn("- [ ] **UNMET**", body,
                      "commands/review.md section 4 template must show an unmet line as a "
                      "`- [ ] **UNMET**` checkbox + bold label (AC1).")
        self.assertIn("**NEEDS-PO**", body,
                      "commands/review.md section 4 template must carry the NEEDS-PO state "
                      "label (AC1).")

    def test_reviewer_agent_uses_checkbox_and_bold_labels(self):
        body = _norm(_read(REVIEWER_AGENT))
        self.assertIn("- [x] **MET**", body,
                      "agents/reviewer.md verdict body must show a met line as a "
                      "`- [x] **MET**` checkbox + bold label (AC1).")
        self.assertIn("- [ ] **UNMET**", body,
                      "agents/reviewer.md verdict body must show an unmet line as a "
                      "`- [ ] **UNMET**` checkbox + bold label (AC1).")


class AllSurfacesReferenceTheStyleTest(unittest.TestCase):
    """AC2 -- the reviewer (agent + skill), tester, and scrum-master (review.md section 4 +
    handoff.md) surfaces reference output-styles/linear-comment.md the same prompt-level
    way the developer does.

    The NB-359 sibling (test_linear_comment_style.py) only checks the DEVELOPER surface, so
    this is the AC2-specific evidence for the four NEW surfaces."""

    # surface -> the relative link it should carry to the style file (depth-dependent).
    SURFACES = {
        "agents/reviewer.md": REVIEWER_AGENT,
        "skills/reviewer/SKILL.md": REVIEWER_SKILL,
        "agents/tester.md": TESTER_AGENT,
        "commands/review.md": REVIEW_CMD,        # scrum-master's section 4 rollup
        "skills/solve/handoff.md": HANDOFF_SKILL,  # scrum-master's solution brief
    }

    def test_each_new_surface_references_the_style_file(self):
        for name, path in self.SURFACES.items():
            with self.subTest(surface=name):
                text = _read(path)
                self.assertTrue(text, f"{name} must exist (AC2).")
                self.assertIn(
                    "output-styles/linear-comment.md", text,
                    f"{name} must reference output-styles/linear-comment.md as the "
                    f"canonical comment rule-set (AC2 -- the style governs all surfaces, "
                    f"not just the developer).",
                )

    def test_references_are_non_tautological_new_wiring(self):
        # Anti-tautology: at HEAD these surfaces did NOT all reference the style file
        # (the style was developer-only). Prove at least one of the four NEW surfaces
        # gained the reference, so the pin tracks a real change, not pre-existing prose.
        gained = []
        for name, path in self.SURFACES.items():
            head = _git_show_head(path.relative_to(REPO_ROOT).as_posix())
            if head and "output-styles/linear-comment.md" not in head:
                gained.append(name)
        # If git is unavailable, head is '' for all and we can't prove the delta here;
        # the live pin above still stands. Only assert the delta when a baseline exists.
        baseline_seen = any(
            _git_show_head(p.relative_to(REPO_ROOT).as_posix())
            for p in self.SURFACES.values()
        )
        if baseline_seen:
            self.assertTrue(
                gained,
                "expected at least one reviewer/tester/scrum-master surface to NEWLY "
                "reference output-styles/linear-comment.md (AC2 extends the "
                "developer-only NB-359 style); none gained the reference vs HEAD.",
            )
        else:
            self.skipTest("no HEAD baseline available (git show returned nothing) -- "
                          "the live AC2 reference pins still hold.")


class KindTagPreservedTest(unittest.TestCase):
    """AC3 -- the per-AC verdict line still carries each AC's kind tag ([test] / [manual] /
    [review]) alongside the new bold state label (the scannable signal preserved)."""

    def test_review_template_carries_kind_tag_beside_state_label(self):
        # The template line shape is `- [x] **MET** [{kind}] {criterion}` -- the bold state
        # label immediately followed by the `[{kind}]` placeholder. Pin the joined token so
        # a reword that drops the kind tag from the per-AC line trips CI.
        body = _norm(_read(REVIEW_CMD))
        self.assertIn("**MET** [{kind}]", body,
                      "commands/review.md section 4 template must keep the `[{kind}]` tag right "
                      "after the state label on the per-AC line (AC3).")
        # And the three concrete kinds are documented as the inhabitants of {kind}.
        for kind in ("[test]", "[manual]", "[review]"):
            self.assertIn(kind, body,
                          f"commands/review.md must name the `{kind}` kind (AC3).")

    def test_reviewer_agent_carries_kind_tag_beside_state_label(self):
        body = _norm(_read(REVIEWER_AGENT))
        self.assertIn("**MET** [{kind}]", body,
                      "agents/reviewer.md verdict body must keep the `[{kind}]` tag right "
                      "after the state label on the per-AC line (AC3).")
        for kind in ("[test]", "[manual]", "[review]"):
            self.assertIn(kind, body,
                          f"agents/reviewer.md must name the `{kind}` kind (AC3).")


class NoLiveTestAssertsTheGlyphsTest(unittest.TestCase):
    """AC5 (literal bar) -- no test still asserts the status glyphs. A glyph may survive
    inside a ``#`` comment or a ``BLOCK_GLYPH = "..."`` escape (those are explanatory /
    membership-tested for ABSENCE), but no test source may carry a status glyph inside a
    LIVE positive assertion call (a ``self.assertIn`` / ``assertEqual`` / ``assertRegex``
    that pins the glyph as required content). ``assertNotIn`` / ``assertNotRegex`` calls are
    fine: they pin the glyph's ABSENCE, which is exactly what AC5 wants."""

    # The status glyphs AC5 calls out, swept across the whole test corpus (escapes only).
    AC5_GLYPHS = (STATUS_GLYPHS["CHECK"], STATUS_GLYPHS["QUESTION"],
                  STATUS_GLYPHS["CROSS"], STATUS_GLYPHS["MEMO"])

    @staticmethod
    def _is_live_positive_assertion(line):
        """True iff the line is an assertion *call* that REQUIRES its argument (a positive
        assert), not prose mentioning the word and not an absence guard. Keyed on the
        ``self.assert`` call token so prose like 'the doc asserts X' never matches, and the
        negative forms are excluded."""
        if "self.assert" not in line:
            return False
        if "self.assertNotIn" in line or "self.assertNotRegex" in line:
            return False
        return True

    def test_no_assertion_line_pins_a_status_glyph(self):
        offenders = []
        for path in sorted(SCRIPTS_DIR.glob("test_*.py")):
            for lineno, line in enumerate(_read(path).splitlines(), start=1):
                if not self._is_live_positive_assertion(line):
                    continue
                if any(g in line for g in self.AC5_GLYPHS):
                    offenders.append(
                        f"{path.name}:{lineno}: {line.encode('ascii', 'replace').decode()}"
                    )
        self.assertEqual(
            offenders, [],
            "no test may assert a status/checkmark glyph as required content (AC5): the "
            "verdict no longer emits them. Offending live assertions:\n"
            + "\n".join(offenders),
        )

    def test_scan_is_non_vacuous(self):
        # Guard the scan itself: prove the corpus is present and the matcher actually FIRES
        # on a synthetic positive assertion carrying a glyph (so an empty `offenders` above
        # is meaningful, not a no-op over zero files or a dead matcher). Also prove it does
        # NOT fire on the two legitimate shapes (an absence guard, and prose).
        files = list(SCRIPTS_DIR.glob("test_*.py"))
        self.assertGreater(len(files), 10,
                           "expected the scripts/ test corpus to be present (AC5 scan).")
        glyph = STATUS_GLYPHS["CHECK"]
        positive = f'        self.assertIn("{glyph}", body)'
        absence = f'        self.assertNotIn("{glyph}", body)'
        prose = '        # the verdict no longer asserts the status glyph'
        self.assertTrue(
            self._is_live_positive_assertion(positive) and glyph in positive,
            "the AC5 matcher must flag a positive self.assertIn pinning a glyph.")
        self.assertFalse(
            self._is_live_positive_assertion(absence),
            "the AC5 matcher must NOT flag an assertNotIn absence guard (that is allowed).")
        self.assertFalse(
            self._is_live_positive_assertion(prose),
            "the AC5 matcher must NOT flag a prose/comment line mentioning 'asserts'.")


class SpecialistsNotesAllSurfacesTest(unittest.TestCase):
    """AC6 -- docs/specialists.md notes the style applies to ALL agent comment surfaces,
    not only the developer (names the reviewer + tester + scrum-master)."""

    @classmethod
    def setUpClass(cls):
        cls.body = _norm(_read(SPECIALISTS))
        cls.low = cls.body.lower()

    def test_specialists_states_all_surfaces_not_just_developer(self):
        self.assertTrue(self.body, "docs/specialists.md must exist (AC6).")
        # The load-bearing claim: the style governs *every* surface / *all* surfaces, not
        # only the developer. Accept either phrasing of the universal quantifier.
        self.assertTrue(
            re.search(r"every backlogd agent comment surface"
                      r"|all\b[\w\s]*agent comment surface"
                      r"|not (just|only) the developer", self.low),
            "docs/specialists.md must state the style applies to ALL agent comment "
            "surfaces, not just the developer (AC6).",
        )

    def test_specialists_names_the_other_three_roles(self):
        # AC6's "all agent comment surfaces" is only meaningful if the doc enumerates the
        # surfaces beyond the developer. Require the reviewer, tester, and scrum-master to
        # all be named in the style section's neighbourhood.
        for role in ("reviewer", "tester", "scrum-master"):
            self.assertIn(
                role, self.low,
                f"docs/specialists.md must name the {role} surface as one the style "
                f"governs (AC6 -- all surfaces, not just the developer).",
            )

    def test_pin_bites_the_pre_change_baseline(self):
        # Anti-tautology: at HEAD docs/specialists.md documented the DEVELOPER-only style
        # (NB-359) and did NOT carry the all-surfaces claim. Prove the universal-quantifier
        # phrase is NEW vs HEAD, so this is a genuine pre/post anchor.
        head = _git_show_head(SPECIALISTS.relative_to(REPO_ROOT).as_posix())
        if not head:
            self.skipTest("no HEAD baseline for docs/specialists.md (git show returned "
                          "nothing) -- the live AC6 pins still hold.")
        head_low = _norm(head).lower()
        had_all_surfaces = bool(re.search(
            r"every backlogd agent comment surface"
            r"|all\b[\w\s]*agent comment surface"
            r"|not (just|only) the developer", head_low))
        self.assertFalse(
            had_all_surfaces,
            "expected the pre-NB-415 docs/specialists.md to NOT yet carry the "
            "all-surfaces claim (so the AC6 pin is non-tautological); it already did.",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
