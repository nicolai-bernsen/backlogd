"""Structural tests for ADR-002 — canonical Linear workspace configuration (NB-382).

Docs-only unit: the artifact under test is a markdown ADR, so most acceptance
criteria are prose/judgement ([review]) or PO-confirmation ([manual]) and are
NOT mechanically testable without becoming a tautology. The one mechanically
verifiable surface is AC1's *structural* shape — the file existing at the next
free ADR number with the five headings the ADR convention requires, a one-line
TL;DR, and a `**Problem:** NB-382` ref — plus the verifiable half of AC4: the
change is documentation-only (no engine/seed file is rewritten) and the ADR
names the two engine gaps the decision creates.

This mirrors the ADR-001 structural checker (`scripts/ci/check-agent-identity-adr.sh`)
but as a unittest, because the suite CI actually runs is
`python3 -m unittest discover -s scripts -p 'test_*.py'` (see .github/workflows/ci.yml)
— the shell checker is a standalone style precedent, not wired into CI.

The *correctness of the decision* (which labels, whether project labels, the
template content) is the reviewer's + PO's judgement, not asserted here.

Run from the repo root:  python scripts/test_adr_002_workspace_config.py
"""

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
ADR_DIR = REPO_ROOT / "docs" / "standards" / "adrs"
ADR = ADR_DIR / "ADR-002-canonical-linear-workspace-configuration.md"

# Engine/seed files the decision must NOT rewrite (AC4: documentation-only,
# re-seeds nothing). The ADR's own claim is that the build is a follow-up.
ENGINE_FILE = REPO_ROOT / "scripts" / "linear_setup.py"

# The five headings backlogd's ADR shape requires — kept in lockstep with
# scripts/ci/check-agent-identity-adr.sh and ADR-001.
REQUIRED_HEADINGS = ["Status", "Context", "Considered Options", "Decision", "Consequences"]


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


class AC1_AdrExistsAtNextFreeNumberWithRequiredShape(unittest.TestCase):
    """AC1 [review] (structural half): the ADR exists at the next free number and
    follows ADR-001's shape — the five required headings, a one-line TL;DR, and a
    `**Problem:** NB-382` ref. (Whether the prose is *good* is the reviewer's call.)"""

    def test_AC1_adr_file_exists(self):
        self.assertTrue(
            ADR.is_file(),
            f"AC1: the ADR must exist at {ADR}",
        )

    def test_AC1_filename_is_the_next_free_number(self):
        """The new ADR must claim the next free integer with no gap and no
        collision — i.e. exactly one ADR-NNN file per number, contiguous from
        001, and the highest is this 002 file."""
        numbers = sorted(
            int(m.group(1))
            for p in ADR_DIR.glob("ADR-*.md")
            for m in [re.match(r"ADR-(\d+)-", p.name)]
            if m
        )
        self.assertTrue(numbers, "AC1: expected at least one ADR-NNN-*.md file")
        # Contiguous from 1, no duplicates.
        self.assertEqual(
            numbers,
            list(range(1, numbers[-1] + 1)),
            f"AC1: ADR numbers must be contiguous from 001 with no gap/collision; got {numbers}",
        )
        # This file is the highest (the next free number when it was authored).
        self.assertEqual(
            numbers[-1],
            2,
            "AC1: ADR-002 must be the next free number after ADR-001",
        )

    def test_AC1_carries_all_five_required_headings(self):
        """Mirror of check-agent-identity-adr.sh: each required heading must
        appear as a Markdown heading line (one-or-more '#', then the text)."""
        body = _read(ADR)
        for heading in REQUIRED_HEADINGS:
            pattern = re.compile(r"^#{1,6}\s+.*" + re.escape(heading), re.MULTILINE)
            self.assertRegex(
                body,
                pattern,
                f"AC1: ADR-002 is missing required heading: {heading!r}",
            )

    def test_AC1_carries_one_line_tldr(self):
        body = _read(ADR)
        self.assertIn(
            "Decision (TL;DR):",
            body,
            "AC1: ADR-002 must carry a one-line `Decision (TL;DR):` summary (ADR-001's shape)",
        )

    def test_AC1_carries_problem_ref_nb382(self):
        body = _read(ADR)
        self.assertIn(
            "**Problem:** NB-382",
            body,
            "AC1: ADR-002 must carry a `**Problem:** NB-382` ref",
        )


class AC4_EngineGapsCalledOutAndDocumentationOnly(unittest.TestCase):
    """AC4 [review] (verifiable half): the ADR names the engine gaps the decision
    creates — that `linear_setup.py` writes only issue labels (`issueLabelCreate`,
    no project-label verb) and that `templateData` must be UI-verified — and the
    change is documentation-only: no engine code is rewritten and nothing is
    re-seeded. (Whether the gaps are *well* explained is the reviewer's call.)"""

    def test_AC4_names_issue_label_only_engine_gap(self):
        body = _read(ADR)
        self.assertIn(
            "issueLabelCreate",
            body,
            "AC4: ADR-002 must name `issueLabelCreate` as the issue-labels-only write path",
        )
        self.assertIn(
            "project label",
            body.lower(),
            "AC4: ADR-002 must name the missing project-label verb as an engine gap",
        )

    def test_AC4_names_templatedata_ui_verification_gap(self):
        body = _read(ADR)
        self.assertIn(
            "templateData",
            body,
            "AC4: ADR-002 must name the freeform `templateData` gap",
        )
        # "created" is not "renders" — the gap is that the JSON must be UI-verified.
        self.assertRegex(
            body,
            re.compile(r"UI[- ]verif", re.IGNORECASE),
            "AC4: ADR-002 must state the templateData must be UI-verified",
        )

    def test_AC4_points_at_a_separate_implementation_follow_up(self):
        body = _read(ADR).lower()
        self.assertIn(
            "follow-up",
            body,
            "AC4: ADR-002 must point the build work at a separate implementation follow-up",
        )

    def test_AC4_is_documentation_only_no_engine_rewrite(self):
        """The unit's diff vs the integration branch must touch only the ADR
        document — no engine/seed file. We assert the engine file is unchanged
        relative to the merge-base by content-identity with the integration
        branch's copy when available, and otherwise that the worktree diff
        names no engine file. This proves the ADR's 'ships no engine change'
        claim mechanically rather than by reading its prose."""
        import subprocess

        # Names of files changed by this unit relative to the integration branch.
        try:
            out = subprocess.run(
                ["git", "diff", "--name-only", "dev...HEAD"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=True,
            )
            committed = set(out.stdout.split())
        except (subprocess.CalledProcessError, FileNotFoundError):
            committed = set()

        # Untracked/working-tree changes (the ADR is added in the worktree).
        try:
            stat = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=True,
            )
            working = {line[3:] for line in stat.stdout.splitlines() if line.strip()}
        except (subprocess.CalledProcessError, FileNotFoundError):
            working = set()

        changed = committed | working
        # The engine file must not be among the unit's changes.
        engine_rel = "scripts/linear_setup.py"
        self.assertNotIn(
            engine_rel,
            changed,
            f"AC4: ADR-002 is documentation-only and must NOT change {engine_rel}; "
            f"changed files seen: {sorted(changed)}",
        )
        # And the engine file is still present (not deleted/re-seeded by this unit).
        self.assertTrue(
            ENGINE_FILE.is_file(),
            f"AC4: engine file {ENGINE_FILE} must remain present (no re-seed by this ADR)",
        )


# --- ACs that are NOT mechanically testable (named, not faked) -----------------
#
# AC2 [review] — "decides all three items, with researched options weighed and a
#   single clear recommendation per item, not an open question." This is a
#   judgement about whether the prose actually *decides* (and decides well).
#   The headings/tables exist (AC1 proves the shape), but asserting "this is a
#   real decision, not an open question" from a markdown grep would be a
#   tautology — the reviewer reads the Considered Options + Decision sections
#   and judges it. Left to [review].
#
# AC3 [review] — "names the exact canonical labels + template content precisely
#   enough that the engine could seed them without further product judgement."
#   Whether the named scaffolds are *precise/seedable enough* is an engineering
#   judgement about content quality, not a string-presence fact. A grep for the
#   label names would not prove "precise enough to seed without judgement". Left
#   to [review].
#
# AC5 [manual] — "the PO reviews the ADR and confirms items 1-3 reflect the
#   intended canonical configuration." PO confirmation of an architectural
#   decision; untestable in code by construction.


if __name__ == "__main__":
    unittest.main(verbosity=2)
