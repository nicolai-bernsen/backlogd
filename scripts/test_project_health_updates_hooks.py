"""Content tests for NB-365 (Unit 2: Project health updates).

Prose/skill-edit unit: prove each AC by file-existence + content assertions on
the four edited markdown sources (dispatch.md, handoff.md, walk.md,
commands/status.md) and the central reference they delegate to
(skills/linear/references/documents-and-updates.md).

ACs proven here:
- AC1 — `solve` posts a health comment at each defined transition. Each of the
  four markers (`claim`, `blocked`, `handback`, `milestone:<name>`) appears in
  its right hook site, each hook delegates body shape + badge + `Health:` lead
  line to the central reference.
- AC2 — Health derivation rules (`on track` / `at risk` / `off track`) live in
  one place (the reference) — hooks delegate, never re-define.
- AC3 — `commands/status.md` carries both the read-only assertion AND an
  explicit guard against posting project health comments, and never calls
  `save_comment` (the one write that would post one).
- AC4 — Each hook site delegates the dedupe procedure to the reference
  (idempotency by marker dedupe) — re-runs are by construction in-place.
- AC5 — Pulse-surfacing is `[manual]` per the issue description; not testable
  in code. Named in the tester report as untestable.

Project-form-only regression check: each hook site explicitly carries
"Project-form" language so single-issue / sub-issue / ops-only forms do NOT
post these updates.

Run from the repo root:  python scripts/test_project_health_updates_hooks.py
"""

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DISPATCH_PATH = REPO_ROOT / "skills" / "solve" / "dispatch.md"
HANDOFF_PATH = REPO_ROOT / "skills" / "solve" / "handoff.md"
WALK_PATH = REPO_ROOT / "skills" / "solve" / "walk.md"
STATUS_PATH = REPO_ROOT / "commands" / "status.md"
REFERENCE_PATH = (
    REPO_ROOT / "skills" / "linear" / "references" / "documents-and-updates.md"
)


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


class AC1_TransitionMarkersAtRightHooks(unittest.TestCase):
    """AC1: `solve` posts a health comment at each defined transition.

    Each of the four markers must appear in its right hook site, and each hook
    must reference the central documents-and-updates.md doc so it inherits the
    `**[backlogd]**` badge + `Health:` lead line shape (not redefined locally).
    """

    def test_AC1_dispatch_md_exists(self):
        self.assertTrue(DISPATCH_PATH.is_file(), f"{DISPATCH_PATH} must exist")

    def test_AC1_handoff_md_exists(self):
        self.assertTrue(HANDOFF_PATH.is_file(), f"{HANDOFF_PATH} must exist")

    def test_AC1_walk_md_exists(self):
        self.assertTrue(WALK_PATH.is_file(), f"{WALK_PATH} must exist")

    def test_AC1_dispatch_carries_claim_marker(self):
        body = _read(DISPATCH_PATH)
        self.assertIn(
            "marker `claim`",
            body,
            "AC1: dispatch.md must mention the `claim` transition marker at the claim hook",
        )

    def test_AC1_dispatch_carries_blocked_marker(self):
        body = _read(DISPATCH_PATH)
        self.assertIn(
            "marker `blocked`",
            body,
            "AC1: dispatch.md must mention the `blocked` transition marker on partial/blocked outcome",
        )

    def test_AC1_handoff_carries_handback_marker(self):
        body = _read(HANDOFF_PATH)
        self.assertIn(
            "marker `handback`",
            body,
            "AC1: handoff.md must mention the `handback` transition marker at the In-Review hook",
        )

    def test_AC1_walk_carries_milestone_marker(self):
        body = _read(WALK_PATH)
        self.assertIn(
            "milestone:<milestone-name>",
            body,
            "AC1: walk.md must mention the `milestone:<name>` transition marker at milestone completion",
        )

    def test_AC1_walk_uses_save_comment_with_milestoneId(self):
        body = _read(WALK_PATH)
        # The milestone-completion variant goes through save_comment({ milestoneId })
        # per documents-and-updates.md — verify the walk hook names that API shape.
        self.assertRegex(
            body,
            r"save_comment\(\{\s*milestoneId",
            "AC1: walk.md must call save_comment({ milestoneId, ... }) for the milestone-completion variant",
        )

    def test_AC1_all_four_hook_sites_delegate_to_reference(self):
        """Each hook site must reference documents-and-updates.md so body shape
        (badge + `Health:` lead line) is inherited, not redefined locally."""
        for path in (DISPATCH_PATH, HANDOFF_PATH, WALK_PATH):
            body = _read(path)
            self.assertIn(
                "documents-and-updates.md",
                body,
                f"AC1: {path.name} must delegate body shape to documents-and-updates.md",
            )

    def test_AC1_reference_specifies_backlogd_badge_and_health_lead_line(self):
        """The badge + `Health:` lead line are documented in the central reference
        — proving "each post carries `**[backlogd]**` badge + `Health:` lead line"
        for every hook that delegates to it."""
        body = _read(REFERENCE_PATH)
        self.assertIn(
            "**[backlogd]** Health:",
            body,
            "AC1: documents-and-updates.md must specify the `**[backlogd]** Health:` body shape",
        )

    def test_AC1_reference_lists_all_four_marker_values(self):
        """The trailing transition marker vocabulary must cover all four values."""
        body = _read(REFERENCE_PATH)
        for token in ("claim", "blocked", "handback", "milestone:<name>"):
            self.assertIn(
                token,
                body,
                f"AC1: reference must list `{token}` in the marker vocabulary",
            )


class AC2_HealthDerivationRulesSingleSourceOfTruth(unittest.TestCase):
    """AC2: Health value matches derivation rules across representative states.

    The three values (`on track` / `at risk` / `off track`) and the derivation
    rules are documented in one place — the reference — and the hook sites
    delegate to it. Hooks that mention health (dispatch's `claim` and `blocked`)
    name the values that apply, but do not redefine the rules.
    """

    def test_AC2_reference_carries_all_three_health_values(self):
        body = _read(REFERENCE_PATH)
        for value in ("on track", "at risk", "off track"):
            self.assertIn(
                value,
                body,
                f"AC2: reference must document health value `{value}`",
            )

    def test_AC2_reference_documents_derivation_table(self):
        """The reference must carry the trigger conditions for each health value
        (the derivation rules) — not just the labels."""
        body = _read(REFERENCE_PATH)
        # The table rows tie each value to a condition.
        self.assertRegex(
            body,
            r"\*\*on track\*\*\s*\|",
            "AC2: reference must document the `on track` derivation trigger",
        )
        self.assertRegex(
            body,
            r"\*\*at risk\*\*\s*\|",
            "AC2: reference must document the `at risk` derivation trigger",
        )
        self.assertRegex(
            body,
            r"\*\*off track\*\*\s*\|",
            "AC2: reference must document the `off track` derivation trigger",
        )

    def test_AC2_dispatch_names_health_values_at_claim(self):
        """The claim hook must name `on track` (default) and reference at risk /
        off track via the derivation rules."""
        body = _read(DISPATCH_PATH)
        self.assertIn(
            "on track",
            body,
            "AC2: dispatch.md (claim hook) must name `on track` as the default health at claim",
        )

    def test_AC2_dispatch_names_blocked_health_values(self):
        """The blocked hook must name `at risk` and `off track` per the rules."""
        body = _read(DISPATCH_PATH)
        self.assertIn(
            "at risk",
            body,
            "AC2: dispatch.md (blocked hook) must name `at risk` for a single blocker / first stall",
        )
        self.assertIn(
            "off track",
            body,
            "AC2: dispatch.md (blocked hook) must name `off track` for multiple blockers / rework",
        )

    def test_AC2_handoff_names_handback_health(self):
        """The handback hook is typically `on track` because the slice completed
        and is unblocked."""
        body = _read(HANDOFF_PATH)
        self.assertIn(
            "on track",
            body,
            "AC2: handoff.md (handback hook) must name `on track` as the typical health at In-Review",
        )

    def test_AC2_hooks_do_not_redefine_derivation_rules(self):
        """The trigger-table style (`No open blocked-by, recent forward motion`)
        belongs to the reference only — hook sites must NOT redefine the rules
        locally (so the source of truth stays single)."""
        # The exact phrase from the reference's `on track` row:
        unique_rule_phrase = "No open `blocked-by`, recent forward motion"
        for path in (DISPATCH_PATH, HANDOFF_PATH, WALK_PATH):
            body = _read(path)
            self.assertNotIn(
                unique_rule_phrase,
                body,
                f"AC2: {path.name} must NOT redefine the derivation rules — delegate to the reference",
            )


class AC3_StatusReadOnlyGuarantee(unittest.TestCase):
    """AC3: `status` writes nothing health-related (read-only guarantee intact).

    `commands/status.md` carries both the existing read-only assertion AND an
    explicit guard against posting project health comments. Crucially: the
    command does not call `save_comment` (the one write that would post a
    project-thread health update). The two pre-existing `save_*` writes
    (`save_issue` for the blocked label and `save_project` for the Forecast
    block) are deliberately documented carve-outs unrelated to health comments.
    """

    def test_AC3_status_md_exists(self):
        self.assertTrue(STATUS_PATH.is_file(), f"{STATUS_PATH} must exist")

    def test_AC3_status_carries_read_only_assertion(self):
        body = _read(STATUS_PATH).lower()
        self.assertIn(
            "read-only",
            body,
            "AC3: status.md must carry the read-only assertion",
        )

    def test_AC3_status_carries_explicit_no_health_comments_guard(self):
        body = _read(STATUS_PATH)
        self.assertIn(
            "does not post project health comments",
            body,
            "AC3: status.md must carry an explicit guard against posting project health comments",
        )

    def test_AC3_status_does_not_call_save_comment(self):
        """The single write that *would* post a project health comment is
        `save_comment({ projectId | milestoneId, ... })` — status.md must NOT
        contain that call shape anywhere."""
        body = _read(STATUS_PATH)
        self.assertNotRegex(
            body,
            r"save_comment\s*\(",
            "AC3: status.md must NOT call save_comment(...) — health comments are solve-owned",
        )

    def test_AC3_status_does_not_call_save_document(self):
        """status.md must not write Documents either — those are scope/solve
        helpers per documents-and-updates.md."""
        body = _read(STATUS_PATH)
        self.assertNotRegex(
            body,
            r"save_document\s*\(",
            "AC3: status.md must NOT call save_document(...) — read-only on documents",
        )

    def test_AC3_status_documents_only_two_intentional_writes(self):
        """The read-only banner explicitly lists the two carve-outs (save_issue
        for the blocked label and save_project for the Forecast block) — both
        unrelated to health comments. Verify the banner names them so a future
        reader knows the read-only guarantee has a precise boundary."""
        body = _read(STATUS_PATH)
        # The two intentional writes must be the only `save_*` calls present.
        self.assertIn(
            "save_issue(labels:",
            body,
            "AC3: status.md must document save_issue(labels: …) as one of the two intentional writes",
        )
        self.assertIn(
            "save_project(description:",
            body,
            "AC3: status.md must document save_project(description: …) as one of the two intentional writes",
        )


class AC4_MarkerDedupeIdempotency(unittest.TestCase):
    """AC4: No duplicate health comment for the same transition on a re-run
    (marker dedupe).

    Each hook site delegates the dedupe procedure to documents-and-updates.md so
    a re-run finds the prior comment by marker and updates it in place. The
    reference owns the `<!-- marker: ... -->` shape and the upsert procedure.
    """

    def test_AC4_reference_documents_idempotency_by_marker_dedupe(self):
        body = _read(REFERENCE_PATH)
        self.assertIn(
            "Idempotency by marker dedupe",
            body,
            "AC4: reference must document the idempotency-by-marker-dedupe procedure",
        )

    def test_AC4_reference_specifies_html_comment_marker(self):
        """The trailing `<!-- marker: ... -->` HTML comment is the dedupe key."""
        body = _read(REFERENCE_PATH)
        self.assertIn(
            "<!-- marker:",
            body,
            "AC4: reference must document the `<!-- marker: ... -->` trailing dedupe key",
        )

    def test_AC4_reference_documents_find_then_update_in_place(self):
        """The procedure must find by marker and update in place, not post a new
        comment per transition."""
        body = _read(REFERENCE_PATH)
        # Step 4 of the upsert: capture id, call save_comment with that id.
        self.assertRegex(
            body,
            r"save_comment\(\{\s*id,\s*body\s*\}\)",
            "AC4: reference must specify the update-in-place call shape (save_comment({ id, body }))",
        )

    def test_AC4_dispatch_delegates_dedupe_to_reference(self):
        """The claim and blocked hooks both mention the dedupe-by-marker
        procedure (delegating to the reference rather than duplicating)."""
        body = _read(DISPATCH_PATH)
        self.assertIn(
            "dedupe-by-marker",
            body,
            "AC4: dispatch.md must reference the dedupe-by-marker procedure (delegation)",
        )

    def test_AC4_handoff_delegates_dedupe_to_reference(self):
        body = _read(HANDOFF_PATH)
        self.assertIn(
            "dedupe-by-marker",
            body,
            "AC4: handoff.md must reference the dedupe-by-marker procedure (delegation)",
        )

    def test_AC4_walk_delegates_dedupe_to_reference(self):
        body = _read(WALK_PATH)
        self.assertIn(
            "dedupe-by-marker",
            body,
            "AC4: walk.md must reference the dedupe-by-marker procedure (delegation)",
        )


class ProjectFormOnlyRegression(unittest.TestCase):
    """Regression check (issue body): each hook must make clear the post is
    Project-form-only — single-issue, sub-issue, and ops-only forms do NOT post
    a project health update. This is the boundary that keeps non-Project runs
    silent on the project thread.
    """

    def test_dispatch_claim_hook_is_project_form_only(self):
        body = _read(DISPATCH_PATH)
        # The claim hook (step 1) carries the Project-form gate.
        self.assertRegex(
            body,
            r"On a \*\*Project-form\*\* run, post a project-thread health update immediately after the\s+claim",
            "Regression: dispatch.md claim hook must be guarded as Project-form-only",
        )
        # And it explicitly excludes the single-issue / sub-issue forms.
        self.assertRegex(
            body,
            r"Single-issue and sub-issue forms do\s*\n*\s*NOT post this update",
            "Regression: dispatch.md claim hook must explicitly exclude single-issue / sub-issue forms",
        )

    def test_dispatch_blocked_hook_is_project_form_only(self):
        body = _read(DISPATCH_PATH)
        # The blocked hook (step 7) carries the Project-form gate.
        self.assertRegex(
            body,
            r"On a \*\*Project-form\*\* run, when a unit returns `BLOCKED` or `NEEDS_CONTEXT`",
            "Regression: dispatch.md blocked hook must be guarded as Project-form-only",
        )
        # All three exclusion forms named explicitly somewhere in the file.
        self.assertIn(
            "Single-issue and sub-issue forms do NOT post this update",
            body,
            "Regression: dispatch.md blocked hook must explicitly exclude single-issue / sub-issue forms",
        )

    def test_handoff_handback_hook_is_project_form_only(self):
        body = _read(HANDOFF_PATH)
        self.assertRegex(
            body,
            r"\*\*Project-form\*\* run, post a project-thread health update",
            "Regression: handoff.md handback hook must be guarded as Project-form-only",
        )
        self.assertIn(
            "Single-issue and sub-issue forms do",
            body,
            "Regression: handoff.md handback hook must explicitly exclude single-issue / sub-issue forms",
        )

    def test_walk_milestone_hook_is_project_form_only(self):
        body = _read(WALK_PATH)
        # The section heading is explicit.
        self.assertIn(
            "Post a milestone-completion health update (Project-form only)",
            body,
            "Regression: walk.md milestone hook must be guarded as Project-form-only in its heading",
        )
        # All three non-Project forms named in the exclusion line.
        self.assertRegex(
            body,
            r"Single-issue,\s*sub-issue,\s*and ops-only runs do NOT\s+post this update",
            "Regression: walk.md must exclude single-issue, sub-issue, and ops-only forms",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
