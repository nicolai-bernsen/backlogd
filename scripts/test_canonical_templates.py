"""Unit tests for ADR-003's canonical templates encoded in scripts/linear_setup.py.

Standard library only (unittest); the network is never touched — every test drives
the pure constants and the pure planner (``plan_canonical_templates`` /
``plan_ensure_template``) directly. Run from the repo root:

    python scripts/test_canonical_templates.py
    python -m unittest discover -s scripts -p 'test_*.py'

What this covers (the NB-392 ``[test]`` acceptance criteria):

* **AC1** — ADR-003's three designed template bodies are encoded as **named
  constants** in ``linear_setup.py`` (not improvised in command prose) and each
  body matches ADR-003 **verbatim**. "Verbatim" is asserted *robustly*: each
  encoded body must appear as an exact substring of the ADR markdown file (the ADR
  fences the bodies in ``` ```markdown ``` blocks, so the body text is byte-present
  there) — plus content/structural assertions on the load-bearing parts. This is
  stronger than a whitespace-exact diff against the rendered ADR (which would also
  have to strip the fences/tables) and not brittle to the ADR's surrounding prose.
* **AC2** — the ``Problem`` issue body carries both ``## Problem`` and
  ``## Acceptance Criteria`` headings and the template applies the ``problem``
  label, encoded the way the proven ``save_issue`` create encodes labels (by name).
* **AC3** — the ``backlogd problem`` project template encodes the three milestones
  **in order** — Investigate → Implement → Verify — and ADR-003's one-line pointer
  description.
* **AC4** — a ``Spec`` **document** template is built via ``plan_ensure_template``
  with the ``:memo:`` icon and the ``## Problem`` / ``## Approach`` /
  ``## Acceptance Criteria`` body, and the create plan carries ``type: "document"``.
* **AC5** — no project-label write verb is added: the parser still exposes exactly
  the six existing verbs (also guarded by ``CliSurfaceTest`` in
  ``test_linear_setup.py``).
"""

import argparse
import pathlib
import sys
import unittest

# Make ``import linear_setup`` work regardless of how this file is invoked.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import linear_setup  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
ADR = (
    REPO_ROOT
    / "docs"
    / "standards"
    / "adrs"
    / "ADR-003-canonical-linear-workspace-configuration.md"
)


def _adr_text() -> str:
    return ADR.read_text(encoding="utf-8")


# --- AC1: bodies are named constants and match ADR-003 verbatim -----------

class CanonicalTemplateConstantsTest(unittest.TestCase):
    """AC1 — the three designed bodies are encoded as module constants whose text
    matches ADR-003 verbatim (each body is an exact substring of the ADR file)."""

    def test_bodies_are_named_module_constants(self):
        # They live on the engine module — the single source of truth — not in
        # command prose. (A missing attribute fails the import-time getattr.)
        for const_name in (
            "CANONICAL_ISSUE_TEMPLATE_BODY",
            "CANONICAL_DOCUMENT_TEMPLATE_BODY",
            "CANONICAL_PROJECT_TEMPLATE_DESCRIPTION",
            "CANONICAL_PROJECT_MILESTONES",
            "CANONICAL_TEMPLATES",
        ):
            self.assertTrue(
                hasattr(linear_setup, const_name),
                f"AC1: linear_setup must expose the constant {const_name!r}",
            )
            self.assertIn(const_name, linear_setup.__all__)

    def test_issue_body_matches_adr_verbatim(self):
        # The ADR fences the issue body in a ```markdown block, so the encoded body
        # must appear in the ADR file character-for-character.
        self.assertIn(
            linear_setup.CANONICAL_ISSUE_TEMPLATE_BODY,
            _adr_text(),
            "AC1: the encoded issue-template body must match ADR-003 verbatim",
        )

    def test_document_body_matches_adr_verbatim(self):
        self.assertIn(
            linear_setup.CANONICAL_DOCUMENT_TEMPLATE_BODY,
            _adr_text(),
            "AC1: the encoded document-template body must match ADR-003 verbatim",
        )

    def test_project_pointer_description_matches_adr_verbatim(self):
        # ADR-003 §3 specifies the exact one-line pointer description.
        self.assertIn(
            linear_setup.CANONICAL_PROJECT_TEMPLATE_DESCRIPTION,
            _adr_text(),
            "AC1: the project-template pointer description must match ADR-003 verbatim",
        )
        # And it is genuinely a single line (no embedded newline).
        self.assertNotIn("\n", linear_setup.CANONICAL_PROJECT_TEMPLATE_DESCRIPTION)

    def test_registry_keys_and_types(self):
        # Exactly the three canonical templates, mapped to the right entity types.
        self.assertEqual(
            {n: s["type"] for n, s in linear_setup.CANONICAL_TEMPLATES.items()},
            {"Problem": "issue", "backlogd problem": "project", "Spec": "document"},
        )
        # Every declared type is a valid TEMPLATE_TYPES entry.
        for spec in linear_setup.CANONICAL_TEMPLATES.values():
            self.assertIn(spec["type"], linear_setup.TEMPLATE_TYPES)


# --- AC2: Problem issue template — headings + applied label ---------------

class ProblemIssueTemplateTest(unittest.TestCase):
    """AC2 — the ``Problem`` issue template body has both headings and applies the
    ``problem`` label (encoded by name, the proven save_issue way)."""

    def setUp(self):
        self.spec = linear_setup.CANONICAL_TEMPLATES["Problem"]
        self.data = self.spec["templateData"]

    def test_body_has_problem_and_ac_headings(self):
        body = self.data["description"]
        self.assertIn("## Problem", body)
        self.assertIn("## Acceptance Criteria", body)

    def test_body_uses_typed_ac_grammar(self):
        # ADR-003 specifies the typed-AC bullets ([review] / [manual]) in the body.
        body = self.data["description"]
        self.assertIn("- [ ] [review]", body)
        self.assertIn("- [ ] [manual]", body)

    def test_applies_problem_label_by_name(self):
        # The label is encoded the same way the proven save_issue create encodes
        # labels — by NAME in a ``labels`` array (Linear resolves/auto-creates it),
        # never a hardcoded per-workspace id. This keeps a templated issue
        # pickup-eligible by construction.
        self.assertIn("labels", self.data, "AC2: issue template must apply a label")
        self.assertEqual(self.data["labels"], ["problem"])

    def test_create_plan_carries_label_in_templatedata(self):
        # Drive the real planner: the create input's templateData must carry the
        # applied label so the build is the single source of truth.
        plan = linear_setup.plan_ensure_template(
            "Problem", "issue", self.data, [], team_id="team_1"
        )
        self.assertEqual(plan["action"], "create")
        self.assertEqual(plan["input"]["type"], "issue")
        self.assertEqual(plan["input"]["templateData"]["labels"], ["problem"])
        self.assertIn("## Acceptance Criteria", plan["input"]["templateData"]["description"])


# --- AC3: project template — ordered milestones + pointer description ------

class ProjectTemplateTest(unittest.TestCase):
    """AC3 — the ``backlogd problem`` project template encodes the three milestones
    in order and the one-line pointer description."""

    def setUp(self):
        self.spec = linear_setup.CANONICAL_TEMPLATES["backlogd problem"]
        self.data = self.spec["templateData"]

    def test_milestones_in_canonical_order(self):
        names = [m["name"] for m in self.data["projectMilestones"]]
        self.assertEqual(names, ["Investigate", "Implement", "Verify"])
        # The dedicated ordered constant agrees.
        self.assertEqual(
            list(linear_setup.CANONICAL_PROJECT_MILESTONES),
            ["Investigate", "Implement", "Verify"],
        )

    def test_milestone_sort_order_is_ascending_and_matches_position(self):
        # Each milestone carries a strictly-ascending sortOrder so Linear renders
        # them in ADR-003's order regardless of dict/iteration quirks.
        ms = self.data["projectMilestones"]
        orders = [m["sortOrder"] for m in ms]
        self.assertEqual(orders, sorted(orders))
        self.assertEqual(len(set(orders)), len(orders), "sortOrders must be distinct")

    def test_pointer_description_present(self):
        self.assertEqual(
            self.data["description"],
            linear_setup.CANONICAL_PROJECT_TEMPLATE_DESCRIPTION,
        )
        # ADR-003's exact wording — names the Spec document + Acceptance Criteria.
        self.assertIn("Spec document", self.data["description"])
        self.assertIn("Acceptance Criteria", self.data["description"])

    def test_create_plan_is_project_type(self):
        plan = linear_setup.plan_ensure_template(
            "backlogd problem", "project", self.data, [], team_id="team_1"
        )
        self.assertEqual(plan["action"], "create")
        self.assertEqual(plan["input"]["type"], "project")
        names = [m["name"] for m in plan["input"]["templateData"]["projectMilestones"]]
        self.assertEqual(names, ["Investigate", "Implement", "Verify"])


# --- AC4: Spec document template via plan_ensure_template -----------------

class SpecDocumentTemplateTest(unittest.TestCase):
    """AC4 — the new ``Spec`` document template builds via ``plan_ensure_template``
    with the ``:memo:`` icon and the three-heading body; the plan is type document."""

    def setUp(self):
        self.spec = linear_setup.CANONICAL_TEMPLATES["Spec"]
        self.data = self.spec["templateData"]

    def test_icon_is_memo(self):
        self.assertEqual(self.data["icon"], ":memo:")

    def test_body_has_all_three_headings(self):
        body = self.data["content"]
        self.assertIn("## Problem", body)
        self.assertIn("## Approach", body)
        self.assertIn("## Acceptance Criteria", body)

    def test_build_create_plan_inspects_templatedata_and_type(self):
        # AC4 verbatim: "a unit test that builds the create plan and inspects its
        # templateData + type: 'document'".
        plan = linear_setup.plan_ensure_template(
            "Spec", "document", self.data, [], team_id="team_1"
        )
        self.assertEqual(plan["action"], "create")
        self.assertEqual(plan["input"]["type"], "document")
        td = plan["input"]["templateData"]
        self.assertEqual(td["icon"], ":memo:")
        self.assertEqual(td["title"], "Spec")
        self.assertIn("## Approach", td["content"])

    def test_document_is_a_valid_template_type(self):
        # The engine already accepts ``document`` — no new verb/type is needed.
        self.assertIn("document", linear_setup.TEMPLATE_TYPES)


# --- plan_canonical_templates: the init.md single-source-of-truth surface --

class PlanCanonicalTemplatesTest(unittest.TestCase):
    """``plan_canonical_templates`` returns one plan per canonical template — the
    surface ``/backlogd:init`` §4 drives instead of improvising templateData."""

    def test_returns_three_plans_in_registry_order(self):
        plans = linear_setup.plan_canonical_templates([], team_id="team_1")
        self.assertEqual(len(plans), 3)
        self.assertEqual(
            [(p["name"], p["type"]) for p in plans],
            [("Problem", "issue"), ("backlogd problem", "project"), ("Spec", "document")],
        )
        # All three are creates on an empty workspace, each carrying its templateData.
        for p in plans:
            self.assertEqual(p["action"], "create")
            self.assertIn("templateData", p["input"])

    def test_idempotent_update_when_templates_already_exist(self):
        # If a live template already matches (name, type), the plan is an update —
        # idempotency inherited from plan_ensure_template, so a re-seed is a no-op
        # on shape (the engine then issues templateUpdate).
        existing = [
            {"id": "tpl_i", "name": "Problem", "type": "issue"},
            {"id": "tpl_p", "name": "backlogd problem", "type": "project"},
            {"id": "tpl_d", "name": "Spec", "type": "document"},
        ]
        plans = linear_setup.plan_canonical_templates(existing)
        self.assertEqual({p["action"] for p in plans}, {"update"})
        self.assertEqual([p["id"] for p in plans], ["tpl_i", "tpl_p", "tpl_d"])

    def test_team_scope_threads_through_to_create_input(self):
        plans = linear_setup.plan_canonical_templates([], team_id="team_xyz")
        for p in plans:
            self.assertEqual(p["input"]["teamId"], "team_xyz")


# --- AC5: no seventh verb (project-label gap is captured, not built) -------

class NoProjectLabelVerbTest(unittest.TestCase):
    """AC5 — ADR-003 ships no project label and the engine grows no project-label
    write verb: the parser still exposes exactly the six existing verbs."""

    def test_parser_still_exposes_exactly_six_verbs(self):
        parser = linear_setup.build_parser()
        sub = next(
            a
            for a in parser._actions
            if isinstance(a, argparse._SubParsersAction)
        )
        self.assertEqual(
            set(sub.choices),
            {
                "audit",
                "ensure-label",
                "recase-label",
                "delete-label",
                "ensure-state",
                "ensure-template",
            },
        )
        # No verb name hints at a project-label write surface.
        for verb in sub.choices:
            self.assertNotIn("project", verb.lower())

    def test_no_canonical_project_labels_constant_exists(self):
        # The deliberate non-build: there is intentionally no project-label registry.
        self.assertFalse(
            hasattr(linear_setup, "CANONICAL_PROJECT_LABELS"),
            "AC5/AC6: ADR-003 ships no project label; the engine must define no "
            "CANONICAL_PROJECT_LABELS registry (a future one needs a verb first)",
        )

    def test_project_label_gap_is_documented_in_engine(self):
        # AC6 [review] backstop: the deliberate gap is captured as a code comment so
        # a reader sees the non-build rather than a silent omission.
        engine_src = (REPO_ROOT / "scripts" / "linear_setup.py").read_text(encoding="utf-8")
        self.assertIn("project-label", engine_src.lower())
        self.assertRegex(engine_src.lower(), r"no project[- ]label")


# --- AC6/AC7/AC8 [review] regression backstops: doc + command prose --------
#
# These are the [review] acceptance criteria — the reviewer owns the merge call.
# They are pinned here only so a *future reword* that quietly drops a load-bearing
# claim (the single-source-of-truth contract, the three-template list, the
# deliberate project-label non-build) trips CI rather than passing silently. The
# assertions target stable tokens, not whole sentences, to stay robust to prose
# polish while still guarding the contract.

INIT_MD = REPO_ROOT / "commands" / "init.md"
BOOTSTRAP_GUIDE = REPO_ROOT / "docs" / "guides" / "workspace-bootstrap.md"


class ReviewSurfaceRegressionTest(unittest.TestCase):
    """[review] AC6/AC7/AC8 — the command/docs describe the canonical templates and
    the deliberate project-label non-build (greppable backstops against a reword)."""

    def test_init_md_drives_engine_constants_not_inline_json(self):
        # AC7: init.md §4 stops improvising templateData and drives the engine's
        # single source of truth — it must name CANONICAL_TEMPLATES and tell the
        # operator not to improvise the JSON inline.
        text = INIT_MD.read_text(encoding="utf-8")
        self.assertIn("CANONICAL_TEMPLATES", text)
        self.assertRegex(text.lower(), r"do not improvise the json inline")

    def test_init_md_ensures_the_spec_document_template(self):
        # AC7: §4 ensures the Spec document template alongside issue + project.
        text = INIT_MD.read_text(encoding="utf-8")
        self.assertRegex(text, r'"Spec"\s+.*--type document')

    def test_init_md_captures_the_project_label_non_build(self):
        # AC6 (doc half): the deliberate non-build is visible in the command, with
        # the "needs a write verb first" qualifier — not a silent omission.
        text = INIT_MD.read_text(encoding="utf-8").lower()
        self.assertRegex(text, r"no project label is seeded")
        self.assertRegex(text, r"write verb")

    def test_bootstrap_guide_describes_all_three_templates(self):
        # AC8: the guide's "What it configures → Templates" lists the three canonical
        # templates (issue + project + the new Spec document).
        text = BOOTSTRAP_GUIDE.read_text(encoding="utf-8")
        self.assertRegex(text.lower(), r"three (canonical )?templates")
        self.assertIn("`Problem` **issue**", text)
        self.assertIn("`backlogd problem` **project**", text)
        self.assertIn("`Spec` **document**", text)

    def test_bootstrap_guide_notes_no_project_label(self):
        # AC8/AC6: the guide also records the deliberate project-label non-build.
        text = BOOTSTRAP_GUIDE.read_text(encoding="utf-8").lower()
        self.assertRegex(text, r"no project[- ]label")


if __name__ == "__main__":
    unittest.main(verbosity=2)
