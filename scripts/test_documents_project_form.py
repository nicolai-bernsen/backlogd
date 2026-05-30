"""Content tests for NB-364 — Unit 1: Documents (Project-form only).

This unit is largely a prose/markdown change. Each testable AC is proven by an
explicit file-existence + content assertion on the markdown sources (templates,
commands, skills, CI workflow). Single-Issue regression bullets are proven by
asserting the original description-canonical branch is still named in each file.

Run from the repo root:  python scripts/test_documents_project_form.py
"""

import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

SPEC_TEMPLATE = REPO_ROOT / "templates" / "spec.md"
BRIEF_TEMPLATE = REPO_ROOT / "templates" / "solution-brief.md"
SCOPE_CMD = REPO_ROOT / "commands" / "scope.md"
SOLVE_CMD = REPO_ROOT / "commands" / "solve.md"
REVIEW_CMD = REPO_ROOT / "commands" / "review.md"
PICKUP_SKILL = REPO_ROOT / "skills" / "solve" / "pickup.md"
HANDOFF_SKILL = REPO_ROOT / "skills" / "solve" / "handoff.md"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


class AC1_TemplatesExistAndValidatedByCI(unittest.TestCase):
    """AC1: Committed templates/spec.md (has `## Acceptance Criteria`) and
    templates/solution-brief.md (has `## What changed`, `## How it was verified`)
    exist and are validated by CI."""

    def test_AC1_spec_template_exists(self):
        self.assertTrue(
            SPEC_TEMPLATE.is_file(),
            f"AC1: templates/spec.md must exist at {SPEC_TEMPLATE}",
        )

    def test_AC1_spec_template_has_acceptance_criteria_heading(self):
        body = _read(SPEC_TEMPLATE)
        self.assertIn(
            "## Acceptance Criteria",
            body,
            "AC1: templates/spec.md must carry a `## Acceptance Criteria` heading",
        )

    def test_AC1_solution_brief_template_exists(self):
        self.assertTrue(
            BRIEF_TEMPLATE.is_file(),
            f"AC1: templates/solution-brief.md must exist at {BRIEF_TEMPLATE}",
        )

    def test_AC1_solution_brief_template_has_what_changed_heading(self):
        body = _read(BRIEF_TEMPLATE)
        self.assertIn(
            "## What changed",
            body,
            "AC1: templates/solution-brief.md must carry a `## What changed` heading",
        )

    def test_AC1_solution_brief_template_has_how_verified_heading(self):
        body = _read(BRIEF_TEMPLATE)
        self.assertIn(
            "## How it was verified",
            body,
            "AC1: templates/solution-brief.md must carry a `## How it was verified` heading",
        )

    def test_AC1_ci_workflow_validates_templates(self):
        """The CI workflow must carry a step that validates both templates and
        their required headings — so a regression in either file breaks CI."""
        body = _read(CI_WORKFLOW)
        self.assertIn(
            "Validate templates",
            body,
            "AC1: ci.yml must declare a 'Validate templates' step",
        )
        self.assertIn(
            "templates/spec.md",
            body,
            "AC1: ci.yml's validate-templates step must reference templates/spec.md",
        )
        self.assertIn(
            "templates/solution-brief.md",
            body,
            "AC1: ci.yml's validate-templates step must reference templates/solution-brief.md",
        )
        # Required headings must appear in the CI validator so the check fails
        # if a heading is removed.
        self.assertIn(
            "## Acceptance Criteria",
            body,
            "AC1: ci.yml must assert templates/spec.md carries `## Acceptance Criteria`",
        )
        self.assertIn(
            "## What changed",
            body,
            "AC1: ci.yml must assert templates/solution-brief.md carries `## What changed`",
        )
        self.assertIn(
            "## How it was verified",
            body,
            "AC1: ci.yml must assert templates/solution-brief.md carries `## How it was verified`",
        )


class AC2_ScopeWritesSpecDocumentForProject(unittest.TestCase):
    """AC2: For a promoted Project, `scope` writes a "Spec" Document containing
    the spec + `## Acceptance Criteria`; the issue description becomes a
    summary + link."""

    def test_AC2_scope_references_spec_template(self):
        body = _read(SCOPE_CMD)
        self.assertIn(
            "templates/spec.md",
            body,
            "AC2: commands/scope.md must reference templates/spec.md as the seed",
        )

    def test_AC2_scope_writes_spec_document_via_upsert(self):
        body = _read(SCOPE_CMD)
        # The upsert call shape for create. Asserting save_document with
        # title: "Spec" proves the Document type the spec lands in.
        normalised = " ".join(body.split())
        self.assertIn(
            'title: "Spec"',
            normalised,
            "AC2: commands/scope.md must save the Document with title: \"Spec\"",
        )
        self.assertIn(
            "save_document",
            body,
            "AC2: commands/scope.md must invoke save_document for the Spec Document",
        )

    def test_AC2_scope_cross_links_upsert_procedure(self):
        body = _read(SCOPE_CMD)
        self.assertIn(
            "documents-and-updates.md",
            body,
            "AC2: commands/scope.md must cross-link the documents-and-updates.md upsert procedure",
        )

    def test_AC2_scope_reduces_description_to_summary_and_link(self):
        body = _read(SCOPE_CMD)
        # Two markers: the directive to reduce the description, and the
        # explicit summary + link pointer to the Spec Document.
        self.assertIn(
            "reduce the Project's container issue description",
            body,
            "AC2: commands/scope.md must direct the orchestrator to reduce the description",
        )
        self.assertIn(
            "Spec Document",
            body,
            "AC2: commands/scope.md must point the reduced description at the Spec Document",
        )

    def test_AC2_scope_preserves_single_issue_description_canonical(self):
        """Regression guard: the Spec Document is Project-form only — the
        single-Issue / sub-issue forms keep their description as canonical."""
        body = _read(SCOPE_CMD)
        self.assertIn(
            "Project-form only",
            body,
            "AC2: commands/scope.md must label the Spec Document as Project-form only",
        )
        self.assertIn(
            "single-Issue and",
            body,
            "AC2: commands/scope.md must explicitly guard the single-Issue / sub-issue form",
        )


class AC3_SolveAndReviewReadAcFromSpecDocument(unittest.TestCase):
    """AC3: `solve`/`review` read AC from the Spec Document for Project-form;
    single-Issue still reads the description (regression)."""

    def test_AC3_pickup_skill_reads_spec_document_for_project_form(self):
        body = _read(PICKUP_SKILL)
        # Project-form branch must reference list_documents + Spec title +
        # get_document as the AC source for that form.
        self.assertIn(
            "list_documents",
            body,
            "AC3: skills/solve/pickup.md must call list_documents for Project-form",
        )
        self.assertIn(
            'title === "Spec"',
            body,
            "AC3: skills/solve/pickup.md must match the Spec Document title",
        )
        self.assertIn(
            "get_document",
            body,
            "AC3: skills/solve/pickup.md must read the Document body via get_document",
        )

    def test_AC3_pickup_skill_preserves_single_issue_description_path(self):
        body = _read(PICKUP_SKILL)
        # Single-Issue regression: the issue description is still the shaped
        # signal + AC source for non-Project forms.
        self.assertIn(
            "Single-Issue / sub-issue form",
            body,
            "AC3: skills/solve/pickup.md must keep the Single-Issue / sub-issue branch named",
        )
        self.assertIn(
            "issue description",
            body,
            "AC3: skills/solve/pickup.md must keep `issue description` as the single-Issue AC source",
        )

    def test_AC3_solve_command_pre_loads_document_tools_for_project_form(self):
        body = _read(SOLVE_CMD)
        # Step 0 pre-load: for Project-form the orchestrator must pre-load the
        # document MCP tools so it can read the Spec Document at pickup.
        self.assertIn(
            "list_documents",
            body,
            "AC3: commands/solve.md must pre-load list_documents for Project-form",
        )
        self.assertIn(
            "get_document",
            body,
            "AC3: commands/solve.md must pre-load get_document for Project-form",
        )
        self.assertIn(
            "Project-form",
            body,
            "AC3: commands/solve.md step 0 must scope the document tools to Project-form",
        )

    def test_AC3_review_reads_ac_from_spec_document_for_project_form(self):
        body = _read(REVIEW_CMD)
        # The reviewer's restricted tool grant has no get_document — the
        # orchestrator must list the Spec Document, get its body, and paste
        # it verbatim into the reviewer envelope.
        self.assertIn(
            "Spec Document",
            body,
            "AC3: commands/review.md must name the Spec Document as the Project-form AC source",
        )
        self.assertIn(
            'title === "Spec"',
            body,
            "AC3: commands/review.md must match the Spec Document title for Project-form",
        )
        self.assertIn(
            "Project-form",
            body,
            "AC3: commands/review.md must branch on Project-form for AC sourcing",
        )

    def test_AC3_review_preserves_single_issue_description_path(self):
        body = _read(REVIEW_CMD)
        # Single-Issue regression: AC still read from the issue description on
        # non-Project forms.
        self.assertIn(
            "Single-Issue / sub-issue form",
            body,
            "AC3: commands/review.md must keep the Single-Issue / sub-issue branch named",
        )
        self.assertIn(
            "issue **description**",
            body,
            "AC3: commands/review.md must keep the issue description as the single-Issue AC source",
        )


class AC4_SolveWritesSolutionBriefDocumentForProject(unittest.TestCase):
    """AC4: `solve` writes a "Solution brief" Document at In Review for
    Projects."""

    def test_AC4_handoff_writes_solution_brief_document_for_project_form(self):
        body = _read(HANDOFF_SKILL)
        # The handoff branches by form: Project-form writes the Document.
        self.assertIn(
            "Project-form — brief as a Document",
            body,
            "AC4: skills/solve/handoff.md must declare the Project-form Document branch in §3",
        )
        # Title is "Solution brief" — accept either single-line or line-wrapped
        # prose form (prose may wrap between "Solution" and "brief").
        normalised = " ".join(body.split())
        self.assertIn(
            'title: "Solution brief"',
            normalised,
            "AC4: skills/solve/handoff.md must save the Document with title: \"Solution brief\"",
        )
        self.assertIn(
            "save_document",
            body,
            "AC4: skills/solve/handoff.md must invoke save_document for the Solution brief",
        )
        self.assertIn(
            "templates/solution-brief.md",
            body,
            "AC4: skills/solve/handoff.md must seed the Document body from templates/solution-brief.md",
        )

    def test_AC4_handoff_cross_links_upsert_procedure(self):
        body = _read(HANDOFF_SKILL)
        self.assertIn(
            "documents-and-updates.md",
            body,
            "AC4: skills/solve/handoff.md must cross-link the upsert procedure",
        )

    def test_AC4_handoff_preserves_single_issue_brief_as_comment(self):
        """Regression: Single-Issue / sub-issue form still posts the brief as
        a **[backlogd]** comment on the problem issue."""
        body = _read(HANDOFF_SKILL)
        self.assertIn(
            "Single-Issue / sub-issue form — brief as a comment",
            body,
            "AC4: skills/solve/handoff.md must keep the Single-Issue comment branch",
        )
        self.assertIn(
            "**[backlogd]** Solution brief",
            body,
            "AC4: skills/solve/handoff.md must keep the single-Issue **[backlogd]** comment shape",
        )

    def test_AC4_solve_pre_loads_save_document_for_project_form(self):
        body = _read(SOLVE_CMD)
        self.assertIn(
            "save_document",
            body,
            "AC4: commands/solve.md step 0 must pre-load save_document for Project-form",
        )

    def test_AC4_handoff_section_4_preserves_in_review_transition(self):
        """Regression: §4 of skills/solve/handoff.md must keep the stable
        In-Review transition mechanics.

        Originally (NB-364) this asserted §4 was byte-identical to a sibling
        worktree's HEAD. NB-393 (ship-on-green) legitimately rewrites §4's tail
        — handoff no longer ends the run with "PO triggers review + merges";
        the run continues to solve's ship-on-green final phase. The sibling
        byte-identity check is therefore superseded. We instead pin the parts
        of §4 that must NOT regress: the In Review state move, the Project-form
        `handback` health-update rule, and the single-issue/sub-issue carve-out.
        """

        def _section_four(text: str) -> str:
            marker = "## 4. Move the problem to In Review"
            idx = text.find(marker)
            if idx == -1:
                return ""
            return text[idx:]

        sec4 = _section_four(_read(HANDOFF_SKILL))
        self.assertTrue(sec4, "AC4: §4 marker missing in handoff.md")
        for needle, why in (
            ("*In Review* state", "§4 must still move the problem to the In Review state"),
            ("marker `handback`", "§4 must keep the Project-form `handback` health-update rule"),
            (
                "Single-issue and sub-issue forms do",
                "§4 must keep the single-issue / sub-issue carve-out (no health update)",
            ),
        ):
            self.assertIn(needle, sec4, f"AC4: {why}")


# AC5 is [manual] — re-running scope/solve updates the same Documents in place
# (no duplicates). The upsert procedure is documented in
# skills/linear/references/documents-and-updates.md and is structurally proven
# by AC2/AC4's `documents-and-updates.md` cross-link tests, but the actual
# end-to-end "no duplicates" check requires running scope/solve twice against
# a live Linear Project and inspecting the Documents list. That round-trip is
# untestable from a markdown-grep harness; the PO confirms it manually on the
# first dogfood run.


if __name__ == "__main__":
    unittest.main(verbosity=2)
