"""Structural tests for ADR-006 — Tier-2 locally-hosted agent identity (NB-419).

Decision/ADR problem. The artifact under test is a markdown ADR, so the *substance*
of its acceptance criteria (is the two-token distinction right, is the supersession
rationale sound, is the billing split honest, is the architecture correct, does the
build-precondition gate make sense) is **prose/judgement** ([review]) or
PO-confirmation ([manual]) — judged by the reviewer from the artifact, NOT provable by
a runner without becoming a tautology. A grep for "does it mention `actor=app`?" proves
a string is present, not that the design is correct, so it is explicitly NOT done here.

What IS mechanically checkable — and not already covered elsewhere — is the **structural
skeleton** an ADR must have, plus the **verifiable half of the supersession (AC#3)**:
the two superseded ADRs must actually carry `status: Superseded by ADR-006` and
`superseded-by: ADR-006` in their front-matter (a fact, not a judgement — supersession
must be *recorded*, even if whether it was the right call is [review]).

This file deliberately MIRRORS ONLY the thin AC#1-style existence/identity/required-shape
anchor from scripts/test_adr_005_tokenless_bridge.py::AC1_AdrArtifactLands. It does NOT
copy that file's whole-worktree *footprint* tests (`_changed_files()` over
`git diff origin/dev...HEAD` ∪ `git status --porcelain`): that pattern is a tracked bug
(NB-418) that false-fails every other unit's local suite by tripping on the worktree's
own files. The "ships no build code" claim of this docs-only ADR is left to the reviewer
to judge from the diff, not asserted via a footprint scan here.

Deliberately NOT re-asserted here (already covered elsewhere — would be redundant):

* **ADR-006 is present in the index with consistent front-matter, and ADR-001/005 show
  as Superseded** — proven byte-for-byte by
  `test_standards_index.py::IndexDriftTest.test_committed_index_matches_corpus` (it
  rebuilds the index from the corpus and fails if any ADR drifted). A separate "ADR-006
  in index" test would duplicate the drift guard, so we don't write one.
* **ADR numbering is contiguous (006 is the next free number)** — proven by
  `test_adr_003_workspace_config.py::test_AC1_filename_is_the_next_free_number`, which
  asserts the ADR-NNN set is contiguous from 001 to the highest; it now transitively
  covers ADR-006.

CI runs `python3 -m unittest discover -s scripts -p 'test_*.py'` from the repo root
(see .github/workflows/ci.yml), so this lives in scripts/ as a stdlib unittest.

Run from the repo root:  python scripts/test_adr_006_tier2_local_identity.py
"""

import json
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
ADR_DIR = REPO_ROOT / "docs" / "standards" / "adrs"
ADR = ADR_DIR / "ADR-006-tier2-locally-hosted-agent-identity.md"
ADR_001 = ADR_DIR / "ADR-001-visible-agent-identity-in-linear.md"
ADR_005 = ADR_DIR / "ADR-005-tokenless-bridge-local-cli-executor.md"
INDEX = REPO_ROOT / "docs" / "standards" / "index.json"

# The five headings backlogd's ADR shape requires (kept in lockstep with
# scripts/test_adr_005_tokenless_bridge.py / scripts/test_adr_003_workspace_config.py).
REQUIRED_HEADINGS = ["Status", "Context", "Considered Options", "Decision", "Consequences"]


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def _front_matter(p: pathlib.Path) -> str:
    """Return the raw `---`-fenced front-matter block of an ADR (between the fences)."""
    body = _read(p)
    parts = body.split("---\n", 2)
    assert len(parts) >= 3, f"{p.name}: front-matter must be a closed `---` block"
    return parts[1]


class AC_AdrArtifactLands(unittest.TestCase):
    """Structural half: a committed ADR exists at ADR-006, carrying the five required
    headings, a one-line TL;DR, the `**Problem:** NB-419` ref, and the TEMPLATE.md
    front-matter identifying it as ADR-006 / Accepted. (Whether the prose actually
    records a sound decision + the two-token split + the architecture + the honest
    billing split is the reviewer's judgement, not asserted here.)"""

    def test_adr_file_exists(self):
        self.assertTrue(ADR.is_file(), f"the ADR must exist at {ADR}")

    def test_carries_all_five_required_headings(self):
        body = _read(ADR)
        for heading in REQUIRED_HEADINGS:
            pattern = re.compile(r"^#{1,6}\s+.*" + re.escape(heading), re.MULTILINE)
            self.assertRegex(
                body, pattern,
                f"ADR-006 is missing required heading: {heading!r}",
            )

    def test_carries_one_line_tldr(self):
        self.assertIn(
            "Decision (TL;DR):", _read(ADR),
            "ADR-006 must carry a one-line `Decision (TL;DR):` summary (ADR shape)",
        )

    def test_carries_problem_ref_nb419(self):
        self.assertIn(
            "NB-419", _read(ADR), "ADR-006 must reference its problem NB-419",
        )

    def test_carries_adr006_frontmatter_accepted(self):
        """TEMPLATE.md mandates a `---`-fenced YAML front-matter block. Assert it
        exists, is closed, and carries this ADR's identity: id ADR-006, a non-empty
        title, status Accepted (an Accepted superseder is required to mark ADR-001/005
        Superseded), and the problem ref."""
        body = _read(ADR)
        self.assertTrue(
            body.startswith("---\n"),
            "ADR must open with a `---`-fenced YAML front-matter block (TEMPLATE.md)",
        )
        front = _front_matter(ADR)
        self.assertIn("id: ADR-006", front, "front-matter `id` must be `ADR-006`")
        self.assertRegex(
            front, r"status:\s*Accepted",
            "an Accepted superseder is required to supersede ADR-001/005",
        )
        self.assertRegex(front, r"problem:\s*NB-419",
                         "front-matter must carry `problem: NB-419`")
        self.assertRegex(front, r"title:\s*\S",
                         "front-matter must carry a non-empty `title`")


class AC3_SupersessionIsRecorded(unittest.TestCase):
    """AC#3 (verifiable half): supersession must be *explicitly recorded* in BOTH
    directions — ADR-001 and ADR-005 each carry `status: Superseded by ADR-006` and
    `superseded-by: ADR-006`, and ADR-006 references both as superseded. This is a
    fact about the front-matter, not a judgement; whether the supersession was the
    right call (and whether still-binding rules were carried forward) is [review]."""

    def test_adr001_front_matter_marks_superseded_by_006(self):
        front = _front_matter(ADR_001)
        self.assertRegex(
            front, r"status:\s*Superseded by ADR-006",
            "ADR-001 front-matter `status` must be `Superseded by ADR-006`",
        )
        self.assertRegex(
            front, r"superseded-by:\s*ADR-006",
            "ADR-001 front-matter `superseded-by` must be `ADR-006`",
        )

    def test_adr005_front_matter_marks_superseded_by_006(self):
        front = _front_matter(ADR_005)
        self.assertRegex(
            front, r"status:\s*Superseded by ADR-006",
            "ADR-005 front-matter `status` must be `Superseded by ADR-006`",
        )
        self.assertRegex(
            front, r"superseded-by:\s*ADR-006",
            "ADR-005 front-matter `superseded-by` must be `ADR-006`",
        )

    def test_adr006_names_both_superseded_adrs(self):
        body = _read(ADR)
        self.assertIn("ADR-001", body, "ADR-006 must reference the superseded ADR-001")
        self.assertIn("ADR-005", body, "ADR-006 must reference the superseded ADR-005")


class AC3_IndexReflectsSupersession(unittest.TestCase):
    """AC#3 (Consequence half): the *regenerated standards index* — not just the ADR
    front-matter — must show the supersession. ADR-006's Consequences state "the
    standards index reflects both [ADR-001/005] as `Superseded` and adds ADR-006";
    a reviewer reads `docs/standards/index.json` to see ADR-006 as the live identity
    standard and ADR-001/005 as superseded history.

    `test_standards_index.py::IndexDriftTest` proves index==corpus byte-for-byte, and
    `AC3_SupersessionIsRecorded` above pins the corpus (front-matter) side — so the
    statuses are *transitively* anchored. This adds the missing **decoupled** half: a
    direct assertion on the committed index's status values, so a regeneration that
    dropped/changed a status is caught as an AC#3 failure here (not only inferred via
    two other tests), and the index-side claim of AC#3 reads as proven, not implied.
    This is a fact about the artifact (the index says X), not a judgement about whether
    superseding was the right call (that stays [review])."""

    def _status_by_id(self):
        index = json.loads(INDEX.read_text(encoding="utf-8"))
        return {e["id"]: e["status"] for e in index["standards"]}

    def test_index_marks_adr001_superseded_by_006(self):
        statuses = self._status_by_id()
        self.assertEqual(
            statuses.get("ADR-001"), "Superseded by ADR-006",
            "the regenerated index must show ADR-001 as `Superseded by ADR-006`",
        )

    def test_index_marks_adr005_superseded_by_006(self):
        statuses = self._status_by_id()
        self.assertEqual(
            statuses.get("ADR-005"), "Superseded by ADR-006",
            "the regenerated index must show ADR-005 as `Superseded by ADR-006`",
        )

    def test_index_marks_adr006_accepted(self):
        statuses = self._status_by_id()
        self.assertEqual(
            statuses.get("ADR-006"), "Accepted",
            "the regenerated index must carry ADR-006 with status `Accepted` "
            "(an Accepted superseder is what licenses the two supersessions)",
        )


# --- ACs that are NOT mechanically testable (named, not faked) -----------------
#
# These are reviewer-judged ([review]) or PO-confirmed ([manual]) by construction —
# the substance is a judgement about the ADR's prose, which a string-grep cannot prove
# without being a tautology. Listed so the coverage gap is explicit, not silent.
#
# AC#1  [manual] — Kato diagnostic resolved (PO confirmed LOCAL); ADR cites it.
# AC#2  [review] — two-token distinction (actor=app Linear-auth vs Anthropic billing);
#                  actor=app needs no API key.
# AC#3  [review] — supersession states WHAT changed + carries forward still-binding
#                  rules (the *recording* of supersession is asserted above; the
#                  rationale + carry-forward completeness is the reviewer's call).
# AC#4  [review] — architecture: local listener (launchd/systemd, not cloud) as
#                  actor=app; 10s AgentSession ack (immediate thought, then async
#                  spawn); spawns local claude CLI; single-vs-per-role decided.
# AC#5  [manual] — billing split stated honestly; default ships subscription/attended.
# AC#6  [review] — executor-swap seam preserved from ADR-005 (one config change).
# AC#7  [review] — Tier-1 (NB-390/391/388) REMAINS the first rung, shippable now.
# AC#8  [manual] — build precondition (prove one session: actor=app auth + sub-10s
#                  AgentActivity + subscription) BEFORE building the daemon.


if __name__ == "__main__":
    unittest.main(verbosity=2)
