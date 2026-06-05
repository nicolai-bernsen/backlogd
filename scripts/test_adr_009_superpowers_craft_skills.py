"""Contract test for ADR-009 — adopt selected superpowers craft skills by reference (NB-412).

Why this file exists — the gap it closes
-----------------------------------------
``test_standards_index.py::IndexDriftTest`` proves the committed index *rebuilds* from the
corpus byte-for-byte and that every ADR carries the required front-matter keys.
``test_adr_003_workspace_config.py`` proves the ADR-NNN numbers are *contiguous*. None of
those pin **ADR-009's membership or substance**: delete the ADR-009 file *and* its
``index.json`` entry and every existing test still passes — the drift guard sees a (smaller)
corpus that still matches a (smaller) index, and the contiguity check sees ``[1..8]`` which
is still gap-free. So nothing asserts that an Accepted ADR-009 carrying *this* decision is
actually present and records exactly the load-bearing choices NB-412 asked for.

This pins exactly that — facts about committed artifacts a reviewer reads, mapped 1:1 to the
testable substance of NB-412's ACs. NB-412's ACs are all ``[review]``/``[manual]``
prose-decision kinds (no runnable behaviour), so the evidence is: (1) the standards-index
drift check stays green (covered by ``test_standards_index.py``, not duplicated here);
(2) content pins asserting each load-bearing decision is present in the ADR text; (3)
anti-vacuity — these pins bite against the pre-change base, where the ADR file does not
exist at ``HEAD`` (see ``AntiVacuity_PinsBiteAgainstBase``).

The decision NB-412 records, and what each test class pins:

* **AC1 (evaluate the three craft skills + assess two-stage review)** — the ADR adopts
  exactly ``test-driven-development`` + ``verification-before-completion`` +
  ``systematic-debugging``, and *assesses but does not adopt* two-stage subagent review
  (backlogd's tester+reviewer split is it). ``AC1_AdoptsExactlyThreeCraftSkills``.
* **AC2 [manual] (exclude the two conflicts, explicitly, by name)** — the ADR rejects (a)
  the aggressive auto-trigger and (b) the run-to-completion stance, each named AND quoted
  verbatim from the real 5.1.0 source (the quotes are checked against the upstream
  ``SKILL.md`` files in ``AC2_VerbatimQuotesMatchUpstream`` so the pin is anchored to facts,
  not the author's paraphrase). ``AC2_ExcludesBothConflictsByName``.
* **AC3 (by-reference vs depend-on-plugin)** — chooses by-reference, names the
  depend-on-plugin alternative, and ties it to keyless/ADR-002. ``AC3_ChoosesByReference``.
* **AC4 (overlap — avoid two competing systems)** — does NOT adopt superpowers'
  brainstorming (scope/refiner is the Linear/standards-aware version) or two-stage review.
  ``AC4_DoesNotAdoptGenericDuplicates``.
* **AC5 (license/attribution)** — credits obra / Jesse Vincent and notes MIT.
  ``AC5_LicenseAndAttribution``.

Plus the structural ADR-shape pin every house ADR carries (``AC0_AdrArtifactLands``), kept
in lockstep with ``test_adr_005/006/007/008``.

It deliberately asserts the *substance* (load-bearing tokens), not exact wording — it is not
a byte-for-byte echo of the assertion or the prose (that would be a tautology against the
same artifacts the drift test already guards). Whether the ADR's *decision is sound*, whether
the evaluation *reasoning* is good, and whether the prose is *agent-read concise* stay the
reviewer's call ([review]); whether the two exclusions *match the PO's intent* stays the PO's
call ([manual]). This only proves the decisions + their exclusions are on the books, with the
exclusion quotes anchored to the real upstream text.

CI runs ``python -m unittest discover -s scripts -p 'test_*.py'`` from the repo root (see
.github/workflows/ci.yml), so this lives in scripts/ as a stdlib unittest. It does NOT do a
git-diff / whole-worktree footprint scan (that pattern is the tracked NB-418 bug that
false-fails every other unit's local suite); membership is pinned against the committed
artifacts instead. The one git read it does (anti-vacuity) is read-only, optional, and
skips cleanly when git or HEAD is unavailable.

Run from the repo root:
    python -m pytest scripts/test_adr_009_superpowers_craft_skills.py
    python scripts/test_adr_009_superpowers_craft_skills.py
    python -m pytest scripts -k ADR009
"""

import json
import os
import pathlib
import re
import subprocess
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
ADR_DIR = REPO_ROOT / "docs" / "standards" / "adrs"
ADR = ADR_DIR / "ADR-009-superpowers-craft-skills-by-reference.md"
INDEX = REPO_ROOT / "docs" / "standards" / "index.json"
DOCS_README_MD = REPO_ROOT / "docs" / "README.md"
ADR_REL = "docs/standards/adrs/ADR-009-superpowers-craft-skills-by-reference.md"

# The five headings backlogd's ADR shape requires (kept in lockstep with
# test_adr_005/006/007/008 and TEMPLATE.md).
REQUIRED_HEADINGS = ["Status", "Context", "Considered Options", "Decision", "Consequences"]

# The three craft skills NB-412 asks the ADR to adopt — exactly these, no more.
ADOPTED_SKILLS = [
    "test-driven-development",
    "verification-before-completion",
    "systematic-debugging",
]

# Upstream superpowers source (5.1.0 is the version the ADR cites). The two excluded
# stances are quoted verbatim in the ADR; AC2_VerbatimQuotesMatchUpstream confirms the
# quotes are real, not paraphrased — but only when the source is present (adopter CI will
# not have superpowers installed, so that class self-skips).
_SP_BASE = pathlib.Path.home() / ".claude/plugins/cache/claude-plugins-official/superpowers"
SP_AUTOTRIGGER = _SP_BASE / "5.1.0/skills/using-superpowers/SKILL.md"
SP_RUNTOCOMPLETION = _SP_BASE / "5.1.0/skills/subagent-driven-development/SKILL.md"


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def _front_matter(p: pathlib.Path) -> str:
    """Return the raw `---`-fenced front-matter block of an ADR (between the fences)."""
    body = _read(p)
    parts = body.split("---\n", 2)
    assert len(parts) >= 3, f"{p.name}: front-matter must be a closed `---` block"
    return parts[1]


def _norm(s: str) -> str:
    """Collapse whitespace so a quote that wraps across lines still matches verbatim text."""
    return re.sub(r"\s+", " ", s).strip()


class AC0_AdrArtifactLands(unittest.TestCase):
    """Structural half (shared with NB-412 AC1 [review]): a committed ADR exists at ADR-009
    with the five required headings, a one-line TL;DR, a bold lead-in title (not a second
    `# H1`), the NB-412 ref, and `id: ADR-009` / `status: Accepted` / `supersedes: ~`
    front-matter. (Whether the prose is a *good*, *concise* decision is the reviewer's
    call — [review].)"""

    def test_adr_file_exists_at_expected_path(self):
        self.assertTrue(
            ADR.is_file(),
            f"AC1: the ADR must exist at {ADR} — the next free number is ADR-009.",
        )

    def test_carries_all_five_required_headings(self):
        body = _read(ADR)
        for heading in REQUIRED_HEADINGS:
            pattern = re.compile(r"^#{1,6}\s+.*" + re.escape(heading), re.MULTILINE)
            self.assertRegex(
                body, pattern, f"AC1: ADR-009 is missing required heading: {heading!r}",
            )

    def test_carries_one_line_tldr(self):
        self.assertIn(
            "Decision (TL;DR):", _read(ADR),
            "AC1: ADR-009 must carry a one-line `Decision (TL;DR):` (front-loaded decision).",
        )

    def test_carries_problem_ref_nb412(self):
        self.assertIn(
            "NB-412", _read(ADR), "AC1: ADR-009 must reference its problem NB-412.",
        )

    def test_body_opens_with_bold_lead_in_not_a_second_h1(self):
        """TEMPLATE.md mandates a **bold lead-in** title, NOT a second `# H1` (which would
        duplicate the front-matter title and trip MD025). Assert the body after the
        front-matter has no top-level `# ` ATX heading."""
        body = _read(ADR)
        after_fm = body.split("---\n", 2)[2]
        offending = [ln for ln in after_fm.splitlines() if re.match(r"^#\s+\S", ln)]
        self.assertEqual(
            offending, [],
            "AC1: ADR body must use a bold lead-in title, not a second `# H1` "
            f"(MD025); found H1 line(s): {offending}",
        )

    def test_frontmatter_identifies_accepted_adr009_superseding_nothing(self):
        body = _read(ADR)
        self.assertTrue(
            body.startswith("---\n"),
            "AC1: ADR must open with a `---`-fenced YAML front-matter block (TEMPLATE.md).",
        )
        front = _front_matter(ADR)
        self.assertIn("id: ADR-009", front, "AC1: front-matter `id` must be `ADR-009`.")
        self.assertRegex(
            front, r"status:\s*Accepted",
            "AC1: ADR-009 must be `status: Accepted` (an Accepted ADR governs).",
        )
        self.assertRegex(
            front, r"problem:\s*NB-412", "AC1: front-matter must carry `problem: NB-412`.",
        )
        self.assertRegex(
            front, r"supersedes:\s*~",
            "AC1: ADR-009 must carry `supersedes: ~` (it adds a craft layer, replaces none).",
        )


class AC1_AdoptsExactlyThreeCraftSkills(unittest.TestCase):
    """NB-412 AC1 [review] (substance): the ADR evaluates and ADOPTS exactly the three named
    craft skills — test-driven-development, verification-before-completion,
    systematic-debugging — and *assesses but does not adopt* two-stage subagent review
    (backlogd's tester+reviewer split is the two-stage review). Read both the ADR body and
    the committed index assertion, so a regeneration that dropped a clause is caught."""

    @classmethod
    def setUpClass(cls):
        cls.body = _read(ADR)
        index = json.loads(INDEX.read_text(encoding="utf-8"))
        cls.by_id = {e["id"]: e for e in index["standards"]}

    def test_adopts_all_three_named_craft_skills(self):
        missing = [s for s in ADOPTED_SKILLS if s not in self.body]
        self.assertEqual(
            missing, [],
            "AC1: ADR-009 must name all three adopted craft skills "
            f"(test-driven-development, verification-before-completion, "
            f"systematic-debugging); missing from the ADR body: {missing}",
        )

    def test_assertion_names_all_three_adopted_skills(self):
        assertion = self.by_id["ADR-009"]["assertion"].lower()
        missing = [s for s in ADOPTED_SKILLS if s not in assertion]
        self.assertEqual(
            missing, [],
            "AC1: the committed index assertion for ADR-009 must name all three adopted "
            f"skills; missing: {missing}\nassertion was: "
            f"{self.by_id['ADR-009']['assertion']!r}",
        )

    def test_records_an_adopt_decision_for_the_three_skills(self):
        """The skills are not merely *mentioned* — the ADR records adopting them. Pin the
        decision verb against the adoption (the `Decision`/`Adopt` section), token-based so
        a rewording survives but a dropped decision fails."""
        body = self.body.lower()
        self.assertTrue(
            "by reference" in body and ("adopt" in body),
            "AC1: ADR-009 must record an ADOPT decision for the three craft skills "
            "(taken 'by reference'); neither the adopt verb nor 'by reference' was found.",
        )

    def test_two_stage_review_assessed_and_not_adopted(self):
        """AC1 explicitly asks to *assess two-stage review vs backlogd's reviewer/tester
        split*. Pin that the ADR (a) names two-stage / subagent review, and (b) ties it to
        backlogd's tester + reviewer split as the reason it is NOT adopted."""
        body = self.body.lower()
        self.assertTrue(
            re.search(r"two-stage", body) or "subagent review" in body,
            "AC1: ADR-009 must assess superpowers' two-stage (subagent) review.",
        )
        self.assertTrue(
            "tester" in body and "reviewer" in body,
            "AC1: the two-stage-review assessment must reference backlogd's tester + "
            "reviewer split (the reason it is not adopted).",
        )
        # The verdict for two-stage review is explicitly "not adopt".
        self.assertRegex(
            self.body,
            r"(?i)(do ?n.?t adopt|not adopt(ed)?).{0,200}(two-stage|subagent review)"
            r"|(two-stage|subagent review).{0,200}(do ?n.?t adopt|not adopt(ed)?)",
            "AC1: ADR-009 must record that two-stage subagent review is NOT adopted "
            "(assessed against backlogd's existing tester+reviewer split).",
        )


class AC2_ExcludesBothConflictsByName(unittest.TestCase):
    """NB-412 AC2 [manual] (substance): the ADR EXCLUDES, explicitly and by name, (a)
    superpowers' aggressive auto-triggering and (b) its run-to-completion stance — each
    quoted verbatim so a reviewer can verify the exclusion and the PO can ratify the stance.

    The PO ratifies *whether the exclusions match intent* ([manual]); this pins only that
    both exclusions are on the books, named, and quoted (the quote text itself is checked
    against the real upstream source in AC2_VerbatimQuotesMatchUpstream)."""

    @classmethod
    def setUpClass(cls):
        cls.body = _read(ADR)
        cls.body_norm = _norm(cls.body)

    def test_excludes_aggressive_auto_triggering_by_name(self):
        body = self.body.lower()
        self.assertTrue(
            "auto-trigger" in body or "auto-triggering" in body or "auto-firing" in body,
            "AC2(a): ADR-009 must name superpowers' aggressive auto-triggering as excluded.",
        )
        # The 1%-chance hook is the distinctive marker of the auto-trigger stance.
        self.assertIn(
            "1%", self.body,
            "AC2(a): the auto-trigger exclusion must quote the distinctive '1% chance' "
            "rule so the exclusion is checkable (not a vague mention).",
        )

    def test_excludes_run_to_completion_by_name(self):
        body = self.body.lower()
        self.assertIn(
            "run-to-completion", body,
            "AC2(b): ADR-009 must name superpowers' run-to-completion stance as excluded.",
        )
        self.assertRegex(
            self.body_norm,
            r"(?i)execute all tasks.{0,40}without stopping|without stopping",
            "AC2(b): the run-to-completion exclusion must quote the 'execute all tasks "
            "... without stopping' rule so the exclusion is checkable.",
        )

    def test_both_exclusions_carry_a_verbatim_quote(self):
        """Both stances are quoted (the AC says 'exclude … explicitly'). Pin the two
        distinctive verbatim fragments are present in the ADR (whitespace-normalised so a
        line-wrapped quote still matches)."""
        for fragment, which in [
            ("you ABSOLUTELY MUST invoke the skill", "auto-trigger (a)"),
            ("Do not pause to check in", "run-to-completion (b)"),
        ]:
            self.assertIn(
                _norm(fragment), self.body_norm,
                f"AC2: the {which} exclusion must carry its verbatim quote "
                f"({fragment!r}) so the reviewer/PO can verify it against the source.",
            )

    def test_names_the_source_skill_for_each_exclusion(self):
        """Each excluded stance is attributed to the SKILL.md it comes from, so the
        exclusion is traceable to the real source (not an unsourced claim)."""
        self.assertIn(
            "using-superpowers/SKILL.md", self.body,
            "AC2(a): the auto-trigger exclusion must cite `using-superpowers/SKILL.md`.",
        )
        self.assertIn(
            "subagent-driven-development/SKILL.md", self.body,
            "AC2(b): the run-to-completion exclusion must cite "
            "`subagent-driven-development/SKILL.md`.",
        )

    def test_exclusions_tied_to_backlogds_gated_model(self):
        """The *reason* both are excluded is the conflict with backlogd's gated model —
        PO-gates / standards-blocks / the developer's stop-and-report contract. Pin that
        the rationale is present (token-based)."""
        body = self.body.lower()
        self.assertTrue(
            ("po-gate" in body or "po gates" in body or "standards-block" in body
             or "standards block" in body or "blocked" in body),
            "AC2: the exclusions must be tied to backlogd's gated model "
            "(PO-gates / standards-blocks / stop-and-report) — the reason they conflict.",
        )


class AC2_VerbatimQuotesMatchUpstream(unittest.TestCase):
    """NB-412 AC2 anti-paraphrase anchor: the two excluded-stance quotes in the ADR are the
    REAL upstream text, not the author's paraphrase. Reads the installed superpowers 5.1.0
    SKILL.md files and asserts each quoted fragment appears verbatim there too.

    This is what makes the AC2 exclusion checkable rather than a tautology against the
    author's own words. It self-skips when superpowers is not installed (adopter CI will not
    have it) — the in-ADR pins above still bite without it."""

    def setUp(self):
        if not (SP_AUTOTRIGGER.is_file() and SP_RUNTOCOMPLETION.is_file()):
            self.skipTest(
                "superpowers 5.1.0 source not installed locally — verbatim-vs-upstream "
                "anchor skipped (the in-ADR exclusion pins still apply)."
            )
        self.adr_norm = _norm(_read(ADR))

    def test_auto_trigger_quote_is_verbatim_from_using_superpowers(self):
        upstream = _norm(_read(SP_AUTOTRIGGER))
        fragment = _norm("you ABSOLUTELY MUST invoke the skill")
        self.assertIn(
            fragment, upstream,
            "anchor: the auto-trigger fragment must exist in the real "
            "using-superpowers/SKILL.md (source moved? re-verify the quote).",
        )
        self.assertIn(
            fragment, self.adr_norm,
            "AC2(a): ADR-009's auto-trigger quote must match the upstream text verbatim.",
        )

    def test_run_to_completion_quote_is_verbatim_from_subagent_skill(self):
        upstream = _norm(_read(SP_RUNTOCOMPLETION))
        fragment = _norm("Execute all tasks from the plan without stopping")
        self.assertIn(
            fragment, upstream,
            "anchor: the run-to-completion fragment must exist in the real "
            "subagent-driven-development/SKILL.md (source moved? re-verify the quote).",
        )
        self.assertIn(
            fragment, self.adr_norm,
            "AC2(b): ADR-009's run-to-completion quote must match the upstream verbatim.",
        )


class AC3_ChoosesByReference(unittest.TestCase):
    """NB-412 AC3 [review] (substance): the ADR decides adopt-BY-REFERENCE over
    depend-on-plugin, names the rejected depend-on-plugin alternative, and ties the choice
    to keyless/serverless (ADR-002)."""

    @classmethod
    def setUpClass(cls):
        cls.body = _read(ADR)

    def test_chooses_by_reference(self):
        self.assertIn(
            "by reference", self.body.lower(),
            "AC3: ADR-009 must choose adopt-by-reference.",
        )

    def test_names_and_rejects_depend_on_plugin_alternative(self):
        body = self.body.lower()
        self.assertIn(
            "depend on the plugin" if "depend on the plugin" in body else "depend-on-plugin",
            body,
            "AC3: ADR-009 must name the depend-on-plugin alternative it rejects.",
        )

    def test_ties_by_reference_to_keyless_adr002(self):
        """The default-to-by-reference reason is 'preserve keyless/serverless' — pin the
        ADR-002 tie (keyless / no-new-dependency), token-based."""
        body = self.body.lower()
        self.assertIn("adr-002", body, "AC3: the by-reference choice must cite ADR-002.")
        self.assertTrue(
            "keyless" in body or "serverless" in body or "no new" in body
            or "new always-on" in body or "no new dependency" in body,
            "AC3: by-reference must be tied to keyless/serverless / no-new-dependency "
            "(the AC's stated default reason).",
        )


class AC4_DoesNotAdoptGenericDuplicates(unittest.TestCase):
    """NB-412 AC4 [review] (substance): the ADR checks the overlap and does NOT adopt
    superpowers' generic brainstorming or two-stage subagent review, because backlogd's
    scope/refiner and tester+reviewer split are the Linear/standards-aware versions — to
    avoid two competing systems. (The two-stage-review non-adoption is also covered by
    AC1; here we pin the brainstorming non-adoption + the 'two competing systems' rationale.)"""

    @classmethod
    def setUpClass(cls):
        cls.body = _read(ADR)

    def test_brainstorming_not_adopted(self):
        body = self.body.lower()
        self.assertIn(
            "brainstorm", body,
            "AC4: ADR-009 must address superpowers' brainstorming overlap.",
        )
        self.assertRegex(
            self.body,
            r"(?i)(do ?n.?t adopt|not adopt(ed)?).{0,160}brainstorm"
            r"|brainstorm\w*.{0,160}(do ?n.?t adopt|not adopt(ed)?)",
            "AC4: ADR-009 must record that brainstorming is NOT adopted (scope/refiner is "
            "the Linear/standards-aware version).",
        )

    def test_brainstorming_tied_to_scope_or_refiner(self):
        body = self.body.lower()
        self.assertTrue(
            "scope" in body or "refiner" in body,
            "AC4: the brainstorming non-adoption must reference backlogd's scope/refiner "
            "(the Linear/standards-aware equivalent).",
        )

    def test_avoids_two_competing_systems(self):
        body = self.body.lower()
        self.assertTrue(
            "competing" in body,
            "AC4: ADR-009 must state the rationale — avoid two competing "
            "(brainstorm/review) systems.",
        )


class AC5_LicenseAndAttribution(unittest.TestCase):
    """NB-412 AC5 [review] (substance): the ADR respects the license and credits obra —
    names MIT and Jesse Vincent (obra)."""

    @classmethod
    def setUpClass(cls):
        cls.body = _read(ADR)

    def test_notes_mit_license(self):
        self.assertIn(
            "MIT", self.body,
            "AC5: ADR-009 must note superpowers' MIT license.",
        )

    def test_credits_obra_jesse_vincent(self):
        body = self.body
        self.assertTrue(
            "Jesse Vincent" in body or "obra" in body,
            "AC5: ADR-009 must credit obra (Jesse Vincent).",
        )

    def test_records_an_attribution_obligation_for_vendored_text(self):
        """By-reference vendoring carries an attribution obligation at the point of use.
        Pin that the ADR records crediting obra/MIT where skill text is vendored."""
        body = self.body.lower()
        self.assertTrue(
            "credit" in body and ("obra" in body or "jesse vincent" in body),
            "AC5: ADR-009 must record the attribution obligation — credit obra at the "
            "point of use for vendored skill text.",
        )


class AC_MembershipInIndexAndReadme(unittest.TestCase):
    """Deliverable: a regenerated standards index lists ADR-009 as Accepted, and the
    docs/README ADR list is refreshed to include it. (The index *drift* — that it rebuilds
    from the corpus byte-for-byte — is covered by test_standards_index.py::IndexDriftTest;
    here we pin membership + status + the README refresh, which that drift guard alone does
    NOT catch — delete the ADR and its entry together and drift stays green.)"""

    @classmethod
    def setUpClass(cls):
        index = json.loads(INDEX.read_text(encoding="utf-8"))
        cls.by_id = {e["id"]: e for e in index["standards"]}

    def test_adr009_present_in_index(self):
        self.assertIn(
            "ADR-009", self.by_id,
            "deliverable: the standards index must contain ADR-009 — regenerate with "
            "`python scripts/standards_index.py` after adding the ADR.",
        )

    def test_adr009_status_accepted_in_index(self):
        self.assertEqual(
            self.by_id["ADR-009"]["status"], "Accepted",
            "deliverable: the emitted index must list ADR-009 with "
            '`"status": "Accepted"` (a non-Accepted entry would not govern).',
        )

    def test_docs_readme_lists_adr009(self):
        body = _read(DOCS_README_MD)
        self.assertIn(
            "ADR-009", body,
            "deliverable: docs/README.md's ADR list must include ADR-009 "
            "(it was stuck at ADR-008 before this change).",
        )


class AntiVacuity_PinsBiteAgainstBase(unittest.TestCase):
    """Anti-vacuity: prove these pins actually BITE — at the pre-change base (HEAD) the
    ADR-009 file does not exist, so every content pin above would fail without the change.
    This is the 'fails-without-the-change' half the DoD requires for a decision artifact
    whose ACs are all prose-decision kinds.

    Read-only `git show HEAD:<path>` — no working-tree mutation. Self-skips cleanly when git
    is unavailable, when not in a work tree, or when ADR-009 already exists at HEAD (i.e.
    after this unit is merged — at which point the bite is proven historically and this
    becomes a no-op rather than a false failure)."""

    def _git_show_head(self, rel_path):
        try:
            res = subprocess.run(
                ["git", "show", f"HEAD:{rel_path}"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (FileNotFoundError, subprocess.SubprocessError, OSError):
            self.skipTest("git unavailable — anti-vacuity base check skipped.")
        return res

    def test_adr_absent_at_head_so_content_pins_would_fail_without_change(self):
        res = self._git_show_head(ADR_REL)
        if res.returncode == 0:
            # ADR already committed at HEAD (post-merge) — the bite is historical; no-op.
            self.skipTest(
                "ADR-009 already exists at HEAD (post-merge) — the anti-vacuity bite is "
                "proven historically; nothing to assert against the base now."
            )
        # Pre-change base: the file does not exist, so AC0..AC5 pins (which all read the
        # ADR) provably had nothing to assert against — they fail-without-the-change.
        combined = (res.stdout + res.stderr).lower()
        self.assertTrue(
            "exists on disk, but not in" in combined
            or "does not exist" in combined
            or f"path '{ADR_REL.lower()}'" in combined
            or "fatal:" in combined,
            "anti-vacuity: expected `git show HEAD:<ADR>` to report the ADR absent at the "
            f"pre-change base; got rc={res.returncode}, stderr={res.stderr!r}",
        )

    def test_docs_readme_lacked_adr009_at_head(self):
        """The README refresh also bites: at HEAD the ADR list stopped at ADR-008."""
        res = self._git_show_head("docs/README.md")
        if res.returncode != 0:
            self.skipTest("docs/README.md unreadable at HEAD — base check skipped.")
        if "ADR-009" in res.stdout:
            self.skipTest(
                "docs/README.md already lists ADR-009 at HEAD (post-merge) — bite "
                "proven historically."
            )
        self.assertNotIn(
            "ADR-009", res.stdout,
            "anti-vacuity: ADR-009 must be ABSENT from docs/README.md at the pre-change "
            "base (so the refresh is a real change, not a no-op).",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
