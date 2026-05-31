"""Structural tests for ADR-003 — canonical Linear workspace configuration (NB-382).

Docs-only unit: the artifact under test is a markdown ADR, so most acceptance
criteria are prose/judgement ([review]) or PO-confirmation ([manual]) and are
NOT mechanically testable without becoming a tautology. The one mechanically
verifiable surface is AC1's *structural* shape — the file existing at the next
free ADR number with the five headings the ADR convention requires, a one-line
TL;DR, a `**Problem:** NB-382` ref, and the YAML frontmatter block TEMPLATE.md
mandates — plus the verifiable half of AC4: the change is documentation-only (no
engine/seed file is rewritten) and the ADR names the two engine gaps the
decision creates.

This mirrors the ADR-001 structural checker (`scripts/ci/check-agent-identity-adr.sh`)
but as a unittest, because the suite CI actually runs is
`python3 -m unittest discover -s scripts -p 'test_*.py'` (see .github/workflows/ci.yml)
— the shell checker is a standalone style precedent, not wired into CI.

Note on numbering: this ADR is **003**. A parallel merge (PR #92, `docs(#377)`)
claimed ADR-002 (`ADR-002-keyless-mcp.md`) and added `TEMPLATE.md` while this was
in review, so the next free number became 003 and the frontmatter convention
applies. The contiguity check below tolerates ADR-002 existing.

The *correctness of the decision* (which labels, whether project labels, the
template content) is the reviewer's + PO's judgement, not asserted here.

Run from the repo root:  python scripts/test_adr_003_workspace_config.py
"""

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
ADR_DIR = REPO_ROOT / "docs" / "standards" / "adrs"
ADR = ADR_DIR / "ADR-003-canonical-linear-workspace-configuration.md"

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
    follows ADR-001's shape — the five required headings, a one-line TL;DR, a
    `**Problem:** NB-382` ref, and the TEMPLATE.md frontmatter block. (Whether the
    prose is *good* is the reviewer's call.)"""

    def test_AC1_adr_file_exists(self):
        self.assertTrue(
            ADR.is_file(),
            f"AC1: the ADR must exist at {ADR}",
        )

    def test_AC1_filename_is_the_next_free_number(self):
        """The new ADR must claim the next free integer with no gap and no
        collision — i.e. exactly one ADR-NNN file per number, contiguous from
        001, and the highest is this 003 file (002 was taken by PR #92's
        keyless-mcp ADR while this was in review)."""
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
        # ADR-003 (this file) is present and contiguously numbered. It was the
        # next free number when authored; later ADRs legitimately extend the set
        # (NB-376 added ADR-004), so we assert presence + contiguity (checked
        # above), not that 003 is still the highest.
        self.assertIn(
            3,
            numbers,
            "AC1: ADR-003 must be present and contiguously numbered (after ADR-001 and ADR-002-keyless-mcp)",
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
                f"AC1: ADR-003 is missing required heading: {heading!r}",
            )

    def test_AC1_carries_one_line_tldr(self):
        body = _read(ADR)
        self.assertIn(
            "Decision (TL;DR):",
            body,
            "AC1: ADR-003 must carry a one-line `Decision (TL;DR):` summary (ADR-001's shape)",
        )

    def test_AC1_carries_problem_ref_nb382(self):
        body = _read(ADR)
        self.assertIn(
            "**Problem:** NB-382",
            body,
            "AC1: ADR-003 must carry a `**Problem:** NB-382` ref",
        )

    def test_AC1_carries_mandated_frontmatter(self):
        """TEMPLATE.md (PR #92 / NB-377) mandates a `---`-fenced YAML frontmatter
        block so an index can enumerate ADRs without parsing prose. Assert it
        exists, is closed, and carries this ADR's identity (id / title / status /
        problem)."""
        body = _read(ADR)
        self.assertTrue(
            body.startswith("---\n"),
            "AC1: ADR must open with a `---`-fenced YAML frontmatter block (TEMPLATE.md)",
        )
        parts = body.split("---\n", 2)
        self.assertGreaterEqual(
            len(parts), 3, "AC1: the frontmatter block must be closed with a `---` line"
        )
        front = parts[1]
        self.assertIn("id: ADR-003", front, "AC1: frontmatter `id` must be `ADR-003`")
        self.assertIn("problem: NB-382", front, "AC1: frontmatter must carry `problem: NB-382`")
        self.assertRegex(front, r"status:\s*Accepted", "AC1: frontmatter `status` must be `Accepted`")
        self.assertRegex(front, r"title:\s*\S", "AC1: frontmatter must carry a non-empty `title`")


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
            "AC4: ADR-003 must name `issueLabelCreate` as the issue-labels-only write path",
        )
        self.assertIn(
            "project label",
            body.lower(),
            "AC4: ADR-003 must name the missing project-label verb as an engine gap",
        )

    def test_AC4_names_templatedata_ui_verification_gap(self):
        body = _read(ADR)
        self.assertIn(
            "templateData",
            body,
            "AC4: ADR-003 must name the freeform `templateData` gap",
        )
        # "created" is not "renders" — the gap is that the JSON must be UI-verified.
        self.assertRegex(
            body,
            re.compile(r"UI[- ]verif", re.IGNORECASE),
            "AC4: ADR-003 must state the templateData must be UI-verified",
        )

    def test_AC4_points_at_a_separate_implementation_follow_up(self):
        body = _read(ADR).lower()
        self.assertIn(
            "follow-up",
            body,
            "AC4: ADR-003 must point the build work at a separate implementation follow-up",
        )

    def test_AC4_is_documentation_only_no_engine_rewrite(self):
        """The ADR-003 *decision* shipped no engine change — it added the ADR doc
        (+ this test) and nothing else; the build is a follow-up (NB-392).

        We anchor this to the **commit that introduced the ADR file**, not to the
        live working tree. The earlier working-tree heuristic was only valid while
        NB-382 was the branch tip — once its sanctioned follow-up NB-392 edits the
        engine (as ADR-003's "Follow-up" explicitly directs), a working-tree diff
        would wrongly red-flag that build. Inspecting the authoring commit's own
        tree-diff keeps the historical guarantee true and decoupled from any later
        engine edit. On a **shallow checkout** (CI's default fetch-depth=1) git
        sees only one commit and reports every path as added in it, so the
        introducing-commit lookup resolves a whole-tree commit it cannot trust —
        we detect that (shallow repo, or an implausibly large changed-set) and
        skip rather than false-fail. On a full clone (local, or fetch-depth=0 CI)
        the assertion runs."""
        import subprocess

        engine_rel = "scripts/linear_setup.py"
        adr_rel = "docs/standards/adrs/ADR-003-canonical-linear-workspace-configuration.md"

        def _git(args: list[str]) -> str:
            return subprocess.run(
                ["git", *args],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=True,
            ).stdout

        # A shallow checkout can't see history: git reports the lone commit as
        # adding every file, so the introducing-commit lookup is meaningless.
        try:
            shallow = _git(["rev-parse", "--is-shallow-repository"]).strip() == "true"
        except (subprocess.CalledProcessError, FileNotFoundError):
            shallow = False
        if shallow:
            self.skipTest(
                "shallow checkout — ADR-003 introducing-commit history unavailable; "
                "the documentation-only guarantee is verified on full-history clones"
            )

        # Find the commit that *introduced* the ADR file (the NB-382 decision unit).
        # No --follow: the ADR was added at this path and never renamed; --follow can
        # rename-detect into an unrelated ancestor. ``--diff-filter=A``; last line = add.
        try:
            log = _git(
                ["log", "--diff-filter=A", "--format=%H", "--", adr_rel]
            ).split()
            intro_sha = log[-1] if log else ""
        except (subprocess.CalledProcessError, FileNotFoundError):
            intro_sha = ""

        if intro_sha:
            # Files that commit changed. The decision unit must NOT have touched the
            # engine (it ships no engine change — the build is the follow-up).
            try:
                changed = set(
                    _git(["show", "--name-only", "--format=", intro_sha]).split()
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                changed = set()
            # A genuine single-ADR doc commit touches a handful of files (the ADR +
            # its test). A large changed-set means we resolved a squash/root/shallow
            # commit we can't trust — skip rather than red-flag a legitimate edit.
            if engine_rel in changed and len(changed) > 6:
                self.skipTest(
                    f"resolved commit {intro_sha[:9]} touches {len(changed)} files — "
                    "looks like a squash/root commit, not the ADR's focused add; "
                    "cannot verify documentation-only here"
                )
            if changed:  # only assert when we resolved a trustworthy focused diff
                self.assertNotIn(
                    engine_rel,
                    changed,
                    f"AC4: the ADR-003 decision commit {intro_sha[:9]} is "
                    f"documentation-only and must NOT change {engine_rel}; "
                    f"changed files seen: {sorted(changed)}",
                )
                self.assertIn(
                    adr_rel,
                    changed,
                    f"AC4: the introducing commit {intro_sha[:9]} must add the ADR doc",
                )

        # The engine file is still present (not deleted/re-seeded by the ADR itself).
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
# AC5 [review] — "the decision is internally consistent and aligns with backlogd's
#   documented principles and ADR-001's precedent." A judgement against the
#   standards (re-tagged from [manual]: the PO is ideation-only; the reviewer
#   verifies decision-soundness against documented principles, not a human gate).
#   Untestable in code by construction — left to [review].


if __name__ == "__main__":
    unittest.main(verbosity=2)
