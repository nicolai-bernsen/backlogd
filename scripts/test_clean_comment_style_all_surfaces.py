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
    ``PinsBiteThePreChangeBaselineTest`` proves (via a git-independent inline fixture of the
    OLD vs NEW format) that the glyph-counting logic genuinely discriminates -- it returns
    > 0 on a synthetic old-format sample and 0 on a clean checkbox+label sample -- so a green
    here is a genuine pre/post anchor, never a tautology. This is the literal evidence for
    both AC1 (the verdict no longer uses the status glyphs) and AC5 (the converse: their
    *absence* is what the display-surface tests now assert).

    The non-tautology guarantee is deliberately INDEPENDENT of git state: a ``git show
    HEAD:<file>`` baseline is a moving target (it is the post-change file once the change is
    committed or merged, which inverts the guard on a CI checkout of the PR head), so the
    discrimination proof is carried by inline synthetic fixtures, never by reading git.
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


def _count_status_glyphs(text):
    """Total occurrences of any status glyph in ``text``. The single discrimination
    primitive the live ``== 0`` pins and the inline-fixture guard both exercise, so the
    guard proves exactly the logic the live assertion relies on."""
    return sum(text.count(g) for g in STATUS_GLYPHS.values())


def _references_style(text):
    """True iff ``text`` references the canonical comment style file. The single
    discrimination primitive the live reference pins and the inline-fixture guard share."""
    return "output-styles/linear-comment.md" in text


def _claims_all_surfaces(text):
    """True iff ``text`` carries the all-surfaces universal-quantifier claim AC6 wants
    (the style governs every agent comment surface, not just the developer). The single
    discrimination primitive the live AC6 pin and the inline-fixture guard share."""
    return bool(re.search(
        r"every backlogd agent comment surface"
        r"|all\b[\w\s]*agent comment surface"
        r"|not (just|only) the developer", _norm(text).lower()))


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
    """Anti-tautology guard: prove the live ``glyph total == 0`` pins on the verdict
    surfaces are MEANINGFUL -- i.e. the glyph-counting logic they rely on genuinely
    discriminates the OLD format (carries the status glyphs) from the NEW format (clean
    checkbox + bold label). If the counter could never fire, the live ``== 0`` assertions
    would prove nothing.

    The proof is a git-INDEPENDENT inline fixture: a synthetic pre-NB-415 verdict line (with
    the glyphs) and a synthetic post-NB-415 verdict line (the checkbox + label convention),
    fed through the SAME ``_count_status_glyphs`` primitive the live pins use. A HEAD-relative
    baseline was the old mechanism and is a moving target -- once this change is committed or
    merged, ``HEAD:<file>`` is the post-change file and the guard inverts (which is exactly
    the CI failure this rework fixes) -- so the discrimination is proven from fixtures, never
    from git."""

    def test_pre_change_surfaces_carried_the_glyphs(self):
        # Anti-tautology proof, git-independent. Feed a synthetic OLD-format verdict line
        # (carries the glyphs) and a synthetic NEW-format line (the clean checkbox + bold
        # label) through the SAME `_count_status_glyphs` primitive the live `== 0` pins use,
        # and confirm it fires on old / not on new. The OLD fixture is built from the
        # STATUS_GLYPHS escapes so it can never become a literal-glyph AC5 offender itself.
        old_format = "\n".join(
            f"- {glyph} [test] criterion {name} was met"
            for name, glyph in STATUS_GLYPHS.items()
        )
        self.assertGreater(
            _count_status_glyphs(old_format), 0,
            "the glyph counter must FIRE on a synthetic OLD-format (pre-NB-415) verdict line "
            "(so the live `== 0` absence pins are non-tautological): it found no glyphs in a "
            "sample built from the status-glyph set.",
        )
        new_format = (
            "- [x] **MET** [test] criterion was met\n"
            "- [ ] **UNMET** [review] criterion was not met\n"
            "- [ ] **NEEDS-PO** [manual] criterion needs a PO ruling"
        )
        self.assertEqual(
            _count_status_glyphs(new_format), 0,
            "the glyph counter must return 0 on a clean checkbox + bold-label sample (the "
            "NEW format), proving a zero count is genuinely the cleaned state, not a dead "
            "matcher.",
        )
        # And the REAL live-file assertion, routed through that same proven-discriminating
        # primitive: each verdict-display surface must now carry zero glyphs (AC1).
        for path in VERDICT_DISPLAY_SURFACES:
            rel = path.relative_to(REPO_ROOT).as_posix()
            self.assertTrue(_read(path), f"{rel} must exist (AC1).")
            self.assertEqual(
                _count_status_glyphs(_read(path)), 0,
                f"the live {rel} must have dropped every status glyph (AC1).",
            )


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
        # Live pin, routed through the SAME `_references_style` primitive the sibling guard
        # (test_references_are_non_tautological_new_wiring) proves discriminates.
        for name, path in self.SURFACES.items():
            with self.subTest(surface=name):
                text = _read(path)
                self.assertTrue(text, f"{name} must exist (AC2).")
                self.assertTrue(
                    _references_style(text),
                    f"{name} must reference output-styles/linear-comment.md as the "
                    f"canonical comment rule-set (AC2 -- the style governs all surfaces, "
                    f"not just the developer).",
                )

    def test_references_are_non_tautological_new_wiring(self):
        # Anti-tautology proof, git-independent. The live pin above asserts each surface
        # CONTAINS the style reference; that is only meaningful if the same containment test
        # can also come back False. Feed a synthetic surface WITHOUT the reference and one
        # WITH it through the SAME `_references_style` primitive the live pin uses, and
        # confirm it discriminates. (The old mechanism asked "did this NEWLY reference the
        # style vs HEAD?" -- a moving target that inverts once the change is committed; the
        # discrimination is now proven from inline fixtures, never from git.)
        without_ref = (
            "Prompt body that constrains comment formatting but names no canonical file. "
            "It talks about no tables and no status emoji, yet links nothing."
        )
        with_ref = (
            "Your comment MUST follow the rules in output-styles/linear-comment.md -- "
            "the canonical comment rule-set."
        )
        self.assertFalse(
            _references_style(without_ref),
            "the reference test must return False on a synthetic surface that does NOT link "
            "output-styles/linear-comment.md (so the live 'each surface references it' pin "
            "is non-tautological).",
        )
        self.assertTrue(
            _references_style(with_ref),
            "the reference test must return True on a synthetic surface that DOES link "
            "output-styles/linear-comment.md.",
        )


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
        # only the developer. Routed through the SAME `_claims_all_surfaces` primitive the
        # sibling guard (test_pin_bites_the_pre_change_baseline) proves discriminates.
        self.assertTrue(
            _claims_all_surfaces(self.body),
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
        # Anti-tautology proof, git-independent. The live pin asserts docs/specialists.md
        # CARRIES the all-surfaces claim; that is only meaningful if the same matcher can
        # also come back False. Feed a synthetic pre-NB-415 DEVELOPER-only phrasing (no
        # universal quantifier) and a synthetic all-surfaces phrasing through the SAME
        # `_claims_all_surfaces` primitive the live pin uses, and confirm it discriminates.
        # (The old mechanism asked "is this phrase NEW vs HEAD?" -- a moving target that
        # inverts once the change is committed; the discrimination is now proven from inline
        # fixtures, never from git.)
        developer_only = (
            "The clean Linear-comment style applies to the developer's work-log comment. "
            "It bans tables and status emoji and caps nesting at two levels."
        )
        all_surfaces = (
            "The clean Linear-comment style applies to every backlogd agent comment "
            "surface -- the reviewer, the tester, and the scrum-master, not just the "
            "developer."
        )
        self.assertFalse(
            _claims_all_surfaces(developer_only),
            "the all-surfaces matcher must return False on a synthetic DEVELOPER-only "
            "phrasing (so the live AC6 pin is non-tautological): it matched a sample with "
            "no universal quantifier.",
        )
        self.assertTrue(
            _claims_all_surfaces(all_surfaces),
            "the all-surfaces matcher must return True on a synthetic all-surfaces phrasing "
            "(proving the live AC6 pin tracks a real claim, not pre-existing prose).",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
