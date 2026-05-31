"""Structural tests for ADR-005 — tokenless bridge + local-CLI executor (NB-379).

Design spike → ADR. The artifact under test is a markdown ADR, so the substance of
its 13 acceptance criteria (the *decision*, the *rationale*, whether the cited ToS
findings are sound, whether the fork-vs-build call is right) is **prose/judgement**
([review]) or PO-confirmation ([manual]) — judged by the reviewer from the artifact,
NOT provable by a runner without becoming a tautology. A grep for "does it mention
`claude -p`?" proves a string is present, not that the design is correct, so it is
explicitly NOT done here.

What IS mechanically checkable — and is *not* already covered by other tests — is the
**verifiable half of AC #1 + AC #13**: this is a *design-only* spike that **ships no
runtime code**. That is an observable fact about the unit's diff, not a judgement: the
unit's changed set is exactly the ADR markdown + the regenerated standards index
(+ this test), and it introduces no runtime artifact (no `package.json`, no bridge
executable, no new runtime module). This mirrors the ADR-003 precedent
(`test_adr_003_workspace_config.py::test_AC4_is_documentation_only_no_engine_rewrite`)
and bites if a future edit ships bridge code under this issue.

Deliberately NOT re-asserted here (already covered elsewhere — would be redundant):

* **ADR-005 is present in the index with consistent front-matter** — proven
  byte-for-byte by `test_standards_index.py::IndexDriftTest.test_committed_index_matches_corpus`
  (it rebuilds the index from the corpus and fails if ADR-005 drifted). The
  orchestrator flagged this; a separate "ADR-005 present in index" test would
  duplicate the drift guard, so we don't write one.
* **ADR numbering is contiguous (005 is the next free number, no gap/collision)** —
  proven by `test_adr_003_workspace_config.py::test_AC1_filename_is_the_next_free_number`,
  which asserts the ADR-NNN set is contiguous from 001 to the highest; that test now
  transitively covers ADR-005.

So this file adds only (a) a thin AC #1 *existence + identity + required-shape* anchor
specific to ADR-005 (the structural skeleton a "committed ADR recording the decision"
must have — the five headings + a `## Decision` body, the `id: ADR-005`/`status:
Proposed` front-matter, the `Problem: NB-379` ref), and (b) the design-only / no-
runtime-code diff guard. Whether the prose under those headings is *good* is the
reviewer's call.

CI runs `python3 -m unittest discover -s scripts -p 'test_*.py'` from the repo root
(see .github/workflows/ci.yml), so this lives in scripts/ as a stdlib unittest.

Run from the repo root:  python scripts/test_adr_005_tokenless_bridge.py
"""

import pathlib
import re
import subprocess
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
ADR_DIR = REPO_ROOT / "docs" / "standards" / "adrs"
ADR = ADR_DIR / "ADR-005-tokenless-bridge-local-cli-executor.md"

# The five headings backlogd's ADR shape requires (kept in lockstep with
# scripts/test_adr_003_workspace_config.py / scripts/ci/check-agent-identity-adr.sh).
REQUIRED_HEADINGS = ["Status", "Context", "Considered Options", "Decision", "Consequences"]


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


class AC1_AdrArtifactLands(unittest.TestCase):
    """AC #1 [review] (structural half): a committed ADR exists at ADR-005, carrying
    the five required headings, a one-line TL;DR, the `**Problem:** NB-379` ref, and
    the TEMPLATE.md front-matter identifying it as ADR-005 / Proposed. (Whether the
    prose actually records a sound decision + rationale + citations + fork-vs-build
    call is the reviewer's judgement, not asserted here.)"""

    def test_AC1_adr_file_exists(self):
        self.assertTrue(
            ADR.is_file(),
            f"AC1: the ADR must exist at {ADR}",
        )

    def test_AC1_carries_all_five_required_headings(self):
        body = _read(ADR)
        for heading in REQUIRED_HEADINGS:
            pattern = re.compile(r"^#{1,6}\s+.*" + re.escape(heading), re.MULTILINE)
            self.assertRegex(
                body,
                pattern,
                f"AC1: ADR-005 is missing required heading: {heading!r}",
            )

    def test_AC1_carries_one_line_tldr(self):
        body = _read(ADR)
        self.assertIn(
            "Decision (TL;DR):",
            body,
            "AC1: ADR-005 must carry a one-line `Decision (TL;DR):` summary (ADR shape)",
        )

    def test_AC1_carries_problem_ref_nb379(self):
        body = _read(ADR)
        self.assertIn(
            "NB-379",
            body,
            "AC1: ADR-005 must reference its problem NB-379",
        )

    def test_AC1_carries_adr005_frontmatter_identity(self):
        """TEMPLATE.md mandates a `---`-fenced YAML front-matter block. Assert it
        exists, is closed, and carries this ADR's identity: id ADR-005, a non-empty
        title, the problem ref, and a non-empty status.

        NOTE: this previously pinned `status: Proposed`. ADR-005 was superseded by
        ADR-006 (NB-419), which per the TEMPLATE lifecycle flipped its status to
        `Superseded by ADR-006` — a supersession is additive history, not a rewrite,
        and the byte-for-byte index status is already guarded by
        test_standards_index.py::IndexDriftTest. So this asserts a non-empty status
        (still a real shape check) rather than a hard-coded lifecycle value that goes
        stale the moment the ADR is legitimately superseded."""
        body = _read(ADR)
        self.assertTrue(
            body.startswith("---\n"),
            "AC1: ADR must open with a `---`-fenced YAML front-matter block (TEMPLATE.md)",
        )
        parts = body.split("---\n", 2)
        self.assertGreaterEqual(
            len(parts), 3, "AC1: the front-matter block must be closed with a `---` line"
        )
        front = parts[1]
        self.assertIn("id: ADR-005", front, "AC1: front-matter `id` must be `ADR-005`")
        self.assertRegex(front, r"status:\s*\S",
                         "AC1: front-matter must carry a non-empty `status`")
        self.assertRegex(front, r"problem:\s*NB-379",
                         "AC1: front-matter must carry `problem: NB-379`")
        self.assertRegex(front, r"title:\s*\S",
                         "AC1: front-matter must carry a non-empty `title`")


class AC1_AC13_DesignOnlyShipsNoRuntimeCode(unittest.TestCase):
    """AC #1 / AC #13 (verifiable half): this is a *design-only* spike — it ships
    **no runtime code**. The unit's changed set is the ADR markdown + the regenerated
    standards index (+ this test), and no runtime artifact (a `package.json`, a bridge
    executable/module) is introduced. This is the mechanically-provable core of "design
    only — no runtime code is shipped" (AC #1) and "does not start runtime
    implementation" (AC #13); whether the *reasons* are well argued is [review]."""

    # The unit's allowed footprint: the ADR doc, the regenerated index, and tests.
    _ALLOWED_EXACT = {
        "docs/standards/adrs/ADR-005-tokenless-bridge-local-cli-executor.md",
        "docs/standards/index.json",
    }

    @staticmethod
    def _changed_files() -> set:
        """The unit's changed files = committed (vs the integration ref) ∪ working
        tree. The NB-379 work lands as a working-tree add of the ADR + a modify of
        index.json before the scrum-master commits; post-commit it is the
        origin/dev...HEAD diff. The union captures it in both states. The try/except
        keeps the test green on a CI checkout where `origin/dev` is absent (matching
        the ADR-003 precedent)."""
        committed: set = set()
        try:
            out = subprocess.run(
                ["git", "diff", "--name-only", "origin/dev...HEAD"],
                cwd=str(REPO_ROOT), capture_output=True, text=True, check=True,
            )
            committed = set(out.stdout.split())
        except (subprocess.CalledProcessError, FileNotFoundError):
            committed = set()
        working: set = set()
        try:
            stat = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(REPO_ROOT), capture_output=True, text=True, check=True,
            )
            # porcelain: 2 status chars + space, then the path (rename → take dest).
            for line in stat.stdout.splitlines():
                if not line.strip():
                    continue
                path = line[3:]
                if " -> " in path:
                    path = path.split(" -> ", 1)[1]
                working.add(path.strip().strip('"'))
        except (subprocess.CalledProcessError, FileNotFoundError):
            working = set()
        # Normalise to forward slashes for cross-platform comparison.
        return {p.replace("\\", "/") for p in (committed | working) if p}

    def test_AC13_no_runtime_code_artifact_shipped(self):
        """No runtime artifact may appear in the unit's footprint: no Node manifest
        (`package.json` / lockfile), no TypeScript/JS source, and no executable bridge
        module. (The ADR's own claim: 'no `package.json`, no executable — only this
        ADR and the regenerated standards index'.)"""
        changed = self._changed_files()
        # If git gave us nothing (detached/offline CI checkout with no diff base and a
        # clean tree), there is no footprint to police — the existence test above still
        # anchors AC1. Don't assert a vacuous pass as a violation.
        if not changed:
            self.skipTest("no diff base and clean tree — footprint not observable here")

        runtime_markers = []
        for path in sorted(changed):
            base = path.rsplit("/", 1)[-1]
            if base in {"package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock"}:
                runtime_markers.append(path)
            elif path.endswith((".ts", ".tsx", ".js", ".mjs", ".cjs")):
                runtime_markers.append(path)
        self.assertEqual(
            runtime_markers, [],
            "AC1/AC13: this is a design-only spike and must ship NO runtime code; "
            f"found runtime artifact(s) in the unit's footprint: {runtime_markers}",
        )

    def test_AC13_footprint_is_docs_plus_index_plus_tests_only(self):
        """Every file the unit touches must be either the two allowed deliverables
        (the ADR + the regenerated index) or a test. A stray source/runtime file
        outside that set fails — proving 'design only' against the diff, not the
        prose."""
        changed = self._changed_files()
        if not changed:
            self.skipTest("no diff base and clean tree — footprint not observable here")
        stray = []
        for path in changed:
            if path in self._ALLOWED_EXACT:
                continue
            base = path.rsplit("/", 1)[-1]
            # Tests are allowed (this file + any the tester adds for the unit).
            if base.startswith("test_") and base.endswith(".py"):
                continue
            stray.append(path)
        self.assertEqual(
            sorted(stray), [],
            "AC1/AC13: a design-only spike's footprint must be the ADR + the "
            "regenerated index (+ tests) only; unexpected file(s) in the unit: "
            f"{sorted(stray)}",
        )

    def test_AC1_index_modified_for_the_new_adr(self):
        """The deliverable is the ADR *and* the regenerated index. Assert the index
        is part of the unit's footprint, so 'ADR lands' includes its index entry
        (the byte-for-byte content correctness is proven by the drift test)."""
        changed = self._changed_files()
        if not changed:
            self.skipTest("no diff base and clean tree — footprint not observable here")
        self.assertIn(
            "docs/standards/index.json", changed,
            "AC1: landing ADR-005 must also regenerate docs/standards/index.json",
        )


# --- ACs that are NOT mechanically testable (named, not faked) -----------------
#
# These are reviewer-judged ([review]) or PO-confirmed ([manual]) by construction —
# the substance is a judgement about the ADR's prose, which a string-grep cannot
# prove without being a tautology. They are listed here so the coverage gap is
# explicit, not silent. (The structural skeleton is covered above; the *content* is
# the reviewer's call.)
#
# AC #2  [review] — Tokenless bridge spec, NO Claude inference, calls no model.
# AC #3  [review] — Local-CLI executor not SDK; SDK-vs-CLI ToS finding is the binding
#                   rationale.
# AC #4  [review] — Four ToS findings each carry a citation a reader can check
#                   (whether each citation is real/sufficient is a reading judgement).
# AC #5  [review] — Executor-swap seam is a one-line config change.
# AC #6  [manual] — "Ordinary individual usage" guard: human as trigger/cadence-setter;
#                   honest ceiling; beach-mode auto-resolve out of scope on subscription.
# AC #7  [review] — Batch DAG before dispatch across the whole batch.
# AC #8  [review] — Quota/budget guard: checks remaining quota, throttles/refuses.
# AC #9  [review] — Confidence + assumptions channel surfaced as elicitation.
# AC #10 [review] — Idempotent resume: reconciles Linear + branch HEAD + worktree.
# AC #11 [review] — Transparency via MCP (Tier 1.5): delegate + role-prefixed comments,
#                   no actor=app webhook server.
# AC #12 [review] — Fork-vs-build call: which Cyrus *ideas* to reuse vs write fresh.
# AC #13 [manual] — Respects NB-376/ADR-004; no runtime implementation started. (The
#                   *no-runtime-code* half is mechanically proven above; the "respects
#                   the differentiator decision" half is a PO/reviewer judgement.)


if __name__ == "__main__":
    unittest.main(verbosity=2)
