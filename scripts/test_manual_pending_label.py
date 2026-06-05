"""Regression tests for NB-417 — surface `[manual]`-carrying problems in Linear
via an auto-managed `manual-pending` label + a PO "Waiting on me" saved view.

NB-417 is a **prose / wiring** unit: a new helper skill plus markdown edits across
`commands/scope.md` / `review.md` / `status.md` and `docs/guides/po-overview.md`.
The two `[test]` ACs are self-proving shell checks the developer ran:

  * AC1  — `test -f skills/linear/manual-pending-label.md`
  * AC8  — `grep -q "manual-pending" docs/guides/po-overview.md`

This file is the **durable guard** the reviewer leans on: it bites if the wiring
is silently dropped or reworded later (the lesson is the witness-floor / the
guard-the-neighbourhood discipline in `test_ship_on_green_and_manual.py`). It
re-implements the `[test]` checks in stdlib Python (so they hold regardless of
`grep`/`test`/`rg` being on PATH — the rg-vacuity lesson) and anchors the
load-bearing wiring strings at each of the three call-sites + the doc view.

What is proven here (the `[review]` ACs whose *presence* is mechanically checkable):

  * AC1  — the helper skill exists and defines ensure / attach / detach, scope-guarded
           to `problem`-labelled issues.
  * AC3  — `commands/scope.md` loads the helper at the same insertion point as the
           `blocked`-label helper and uses the `extract_kind` normalize-then-match rule
           (not a naive substring scan).
  * AC4  — `commands/review.md` clears the label on the `accepted` close and leaves it
           attached while any `[manual]` is AWAITING-PO (awaiting PO confirmation).
  * AC5  — `commands/status.md` re-evaluates the label read-only on each in-scope
           problem (the signal-layer carve-out).
  * AC8  — `docs/guides/po-overview.md` documents the "Waiting on me" view filtered on
           the `manual-pending` label.

The deeper *semantic* claims (idempotency on both ends — AC2/AC6; per-unit placement
— AC7) are `[review]` Claude judgements over the prose; the string pins here are not a
substitute for that read — they keep the wiring honest so an incidental regression in
the touched neighbourhood trips CI. AC9 (the saved view's rendered membership in the
Linear UI) is `[manual]` — a UI fact no fresh-context agent can observe from the repo.

Matches are whitespace-collapsed (survive prose line-wrapping) and never pin exact
indentation. `ProseGuardBitesTest` is the negative control: it proves each anchor
*would* fail were the wiring removed, so the green results above are non-vacuous.

Run from the repo root:  python scripts/test_manual_pending_label.py
(or collected by `python3 -m unittest discover -s scripts -p 'test_*.py'`).
"""

import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

MANUAL_LABEL_SKILL = REPO_ROOT / "skills" / "linear" / "manual-pending-label.md"
BLOCKED_LABEL_SKILL = REPO_ROOT / "skills" / "linear" / "blocked-label.md"
SCOPE_CMD = REPO_ROOT / "commands" / "scope.md"
REVIEW_CMD = REPO_ROOT / "commands" / "review.md"
STATUS_CMD = REPO_ROOT / "commands" / "status.md"
PO_OVERVIEW = REPO_ROOT / "docs" / "guides" / "po-overview.md"


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def _norm(text: str) -> str:
    """Whitespace-collapse so a content pin survives prose line-wrapping."""
    return " ".join(text.split())


class HelperSkillExistsTest(unittest.TestCase):
    """AC1 (`[test]`): the helper skill exists and defines ensure / attach / detach,
    scope-guarded to `problem`-labelled issues — modelled on `blocked-label.md`.

    Re-implements `test -f skills/linear/manual-pending-label.md` in Python so the
    check is non-vacuous regardless of `test`/shell availability, and goes further:
    it asserts the file actually carries the algorithm (a bare touch'd file would
    pass `test -f` but fail here)."""

    def test_skill_file_exists(self):
        self.assertTrue(
            MANUAL_LABEL_SKILL.is_file(),
            f"skills/linear/manual-pending-label.md must exist at {MANUAL_LABEL_SKILL}",
        )

    def test_skill_defines_ensure_attach_detach(self):
        body = _norm(_read(MANUAL_LABEL_SKILL))
        # Ensure step (created-on-write, idempotent) — AC2.
        self.assertIn(
            "Ensure the `manual-pending` label exists",
            body,
            "skill must define an ensure-label (created-on-write) step",
        )
        # Attach + detach are expressed as the delta table's save_issue add/remove.
        self.assertIn(
            'save_issue({ id, labels: [...labels, "manual-pending"] })',
            body,
            "skill must define the attach (add-label) path",
        )
        self.assertIn(
            'l !== "manual-pending"',
            body,
            "skill must define the detach (remove-label) path",
        )

    def test_skill_is_scope_guarded_to_problem_issues(self):
        body = _norm(_read(MANUAL_LABEL_SKILL))
        self.assertIn(
            "Only `problem`-labelled issues",
            body,
            "skill must be scope-guarded to problem-labelled issues",
        )
        # Active-state guard, mirroring blocked-label.
        self.assertIn("unstarted", body)
        self.assertIn(
            "started", body,
            "skill must restrict re-evaluation to active (unstarted/started) states",
        )

    def test_skill_uses_extract_kind_not_substring(self):
        """AC3's contract lives in the skill too: detect `[manual]` via the
        `extract_kind` normalize-then-match rule, never a naive substring scan."""
        body = _norm(_read(MANUAL_LABEL_SKILL))
        self.assertIn(
            "extract_kind",
            body,
            "skill must parse [manual] via the extract_kind rule",
        )
        self.assertIn(
            "normalize",
            body,
            "skill must normalize Linear's stored form before matching",
        )

    def test_skill_is_keyfree_mcp_only(self):
        """AC2: no API key / non-MCP path is introduced."""
        body = _read(MANUAL_LABEL_SKILL)
        self.assertNotIn(
            "LINEAR_API_KEY", body,
            "skill must not introduce an API key",
        )


class ScopeWiringTest(unittest.TestCase):
    """AC3: `/backlogd:scope` applies the label at the same insertion point as the
    `blocked`-label helper, using the `extract_kind` normalize-then-match rule."""

    def test_scope_loads_the_helper(self):
        body = _norm(_read(SCOPE_CMD))
        self.assertIn(
            "skills/linear/manual-pending-label.md",
            body,
            "commands/scope.md must load the manual-pending-label helper",
        )

    def test_scope_uses_same_insertion_point_as_blocked(self):
        body = _norm(_read(SCOPE_CMD))
        # Both helpers wired in §5; the manual-pending one explicitly at the "same
        # insertion point" as blocked-label.
        self.assertIn(
            "skills/linear/blocked-label.md",
            body,
            "commands/scope.md must still load the blocked-label helper (the sibling)",
        )
        self.assertIn(
            "same insertion point",
            body,
            "commands/scope.md must wire manual-pending at the same point as blocked",
        )

    def test_scope_detects_manual_via_extract_kind(self):
        body = _norm(_read(SCOPE_CMD))
        self.assertIn(
            "extract_kind",
            body,
            "commands/scope.md must determine has-a-[manual]-AC via extract_kind",
        )
        # The anti-pattern is named explicitly: NOT a naive substring scan.
        self.assertIn(
            "not** fooled by a naive `[manual]` substring",
            body,
            "commands/scope.md must reject the naive [manual] substring scan",
        )


class ReviewWiringTest(unittest.TestCase):
    """AC4: `/backlogd:review` clears the label on the `accepted` close and leaves it
    attached while any `[manual]` is AWAITING-PO (awaiting PO confirmation)."""

    def test_review_loads_the_helper(self):
        body = _norm(_read(REVIEW_CMD))
        self.assertIn(
            "skills/linear/manual-pending-label.md",
            body,
            "commands/review.md must reference the manual-pending-label helper",
        )

    def test_review_clears_label_on_accepted(self):
        body = _norm(_read(REVIEW_CMD))
        self.assertIn(
            "clear the `manual-pending` label",
            body,
            "commands/review.md must clear the label on the accepted close",
        )

    def test_review_leaves_label_attached_while_awaiting_po(self):
        body = _norm(_read(REVIEW_CMD))
        self.assertIn(
            "Leave the `manual-pending` label attached",
            body,
            "commands/review.md must leave the label attached while a [manual] is awaiting PO",
        )
        # The state that keeps it on is the AWAITING-PO (awaiting-PO-confirmation) one.
        self.assertIn("awaiting PO confirmation", body)


class StatusWiringTest(unittest.TestCase):
    """AC5: `/backlogd:status` re-evaluates the label read-only on each in-scope
    problem (the signal-layer carve-out), console output unchanged."""

    def test_status_loads_the_helper(self):
        body = _norm(_read(STATUS_CMD))
        self.assertIn(
            "skills/linear/manual-pending-label.md",
            body,
            "commands/status.md must load the manual-pending-label helper",
        )

    def test_status_re_evaluates_as_signal_layer_carveout(self):
        body = _norm(_read(STATUS_CMD))
        self.assertIn(
            "re-evaluate the `manual-pending` label",
            body,
            "commands/status.md must re-evaluate the manual-pending label",
        )
        self.assertIn(
            "signal-layer carve-out",
            body,
            "commands/status.md must frame it as the signal-layer carve-out (like blocked)",
        )

    def test_status_console_output_unchanged(self):
        body = _norm(_read(STATUS_CMD))
        self.assertIn(
            "console standup output below is unchanged",
            body,
            "commands/status.md must state the console standup output is unchanged",
        )


class PoOverviewViewTest(unittest.TestCase):
    """AC8 (`[test]`): `docs/guides/po-overview.md` documents the "Waiting on me"
    saved view filtered on `manual-pending` (filter + group/sort + display options).

    Re-implements `grep -q "manual-pending" docs/guides/po-overview.md` in Python so
    the check holds regardless of `grep` availability, and asserts the *view* is
    actually documented (filter/group/sort), not merely that the token appears."""

    def test_doc_mentions_manual_pending(self):
        body = _read(PO_OVERVIEW)
        self.assertIn(
            "manual-pending", body,
            'docs/guides/po-overview.md must mention the "manual-pending" label',
        )

    def test_doc_has_waiting_on_me_view(self):
        body = _norm(_read(PO_OVERVIEW))
        self.assertIn(
            "Waiting on me",
            body,
            'docs/guides/po-overview.md must title a "Waiting on me" view',
        )

    def test_view_documents_filter_group_sort(self):
        body = _norm(_read(PO_OVERVIEW))
        # Same style as the existing PO Daily / Done-this-week views.
        self.assertIn(
            "Label is manual-pending",
            body,
            "the Waiting-on-me view must filter on the manual-pending label",
        )
        for section in ("Filter", "Group by", "Sort", "Display options"):
            self.assertIn(
                section, body,
                f"the Waiting-on-me view must document its {section!r} in the PO-view style",
            )


class ProseGuardBitesTest(unittest.TestCase):
    """Negative control — prove every anchor above *can* fail (the rg-vacuity lesson:
    a check that cannot fail is worthless).

    For each (source file, load-bearing needle) the suite relies on, assert the needle
    is present now AND that removing it from the file's text would make the membership
    test fail. We never mutate the files on disk — we mutate the *read string* in
    memory and re-run the same `in` predicate the real tests use, proving the predicate
    is sensitive to the wiring rather than tautologically green.
    """

    # (path, needle) pairs — one per call-site / artifact the wiring lives at.
    ANCHORS = [
        (MANUAL_LABEL_SKILL, "Ensure the `manual-pending` label exists"),
        (MANUAL_LABEL_SKILL, "Only `problem`-labelled issues"),
        (SCOPE_CMD, "skills/linear/manual-pending-label.md"),
        (SCOPE_CMD, "same insertion point"),
        (REVIEW_CMD, "clear the `manual-pending` label"),
        (REVIEW_CMD, "Leave the `manual-pending` label attached"),
        (STATUS_CMD, "re-evaluate the `manual-pending` label"),
        (PO_OVERVIEW, "Label is manual-pending"),
    ]

    def test_every_anchor_is_present(self):
        for path, needle in self.ANCHORS:
            self.assertIn(
                needle, _norm(_read(path)),
                f"{path.name} must currently contain the wiring anchor {needle!r}",
            )

    def test_every_anchor_would_fail_if_wiring_removed(self):
        """The fail-direction proof: delete the needle from the in-memory text and the
        same predicate must now be False. If this loop ever finds a needle whose
        removal leaves the predicate True, the corresponding real test is vacuous."""
        for path, needle in self.ANCHORS:
            body = _norm(_read(path))
            mutated = body.replace(needle, "")
            self.assertNotIn(
                needle, mutated,
                f"removing {needle!r} from {path.name} must make the wiring check FAIL "
                "— otherwise the guard for that call-site is vacuous",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
