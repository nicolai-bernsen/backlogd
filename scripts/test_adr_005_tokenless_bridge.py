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

import json
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
    implementation" (AC #13); whether the *reasons* are well argued is [review].

    NB-418 / NB-420 — the *footprint* tests below were a tracked bug. They computed the
    unit's changed set over the **whole worktree** (`git diff origin/dev...HEAD` ∪
    `git status --porcelain`), so once ADR-005 merged to the integration branch the
    footprint collapsed to *whatever is uncommitted in the current worktree* — false-failing
    **every other unit's** local suite on that unit's own files (e.g. NB-413's gate/skill
    edits), and "passing" in CI only by the accident of a depth-1 checkout (no `origin/dev`
    → empty → skip). The fix anchors the footprint to the **commit that introduced the ADR
    doc** (`_intro_footprint()`, the `test_adr_003_workspace_config.py` precedent): it
    isolates ADR-005's own files from history, so the design-only guarantee verifies
    robustly on any full clone — local or a deep CI — and a foreign worktree can never
    pollute it (no marker-based blind spots, no reliance on the shallow-skip). On a shallow
    checkout history is unavailable, so it returns empty and the callers skip — unchanged CI
    behaviour, where the guarantee is anchored by ``test_adr_and_index_present_no_runtime_anchor``
    (the ADR exists + the committed index carries ADR-005) and ``test_standards_index.py::IndexDriftTest``
    (the index's byte-for-byte correctness). The stray/runtime predicates are pure
    (`_strays` / `_runtime_markers`), so the "still bites a planted artifact" guarantee
    (NB-418 AC#2) is unit-tested directly rather than only asserted on the live diff."""

    # The unit's allowed footprint: the ADR doc, the regenerated index, and tests.
    _ALLOWED_EXACT = {
        "docs/standards/adrs/ADR-005-tokenless-bridge-local-cli-executor.md",
        "docs/standards/index.json",
    }

    def test_adr_and_index_present_no_runtime_anchor(self):
        """AC1/AC13 non-footprint anchor: the ADR markdown exists and the committed
        standards index carries an ADR-005 entry — read directly, not via the live
        worktree diff. This proves the design-only deliverable *landed* without policing
        what else is uncommitted in the current worktree (the NB-418 trap). The index's
        content correctness is proven byte-for-byte by test_standards_index.py."""
        adr = REPO_ROOT / "docs" / "standards" / "adrs" / \
            "ADR-005-tokenless-bridge-local-cli-executor.md"
        self.assertTrue(adr.is_file(), "AC1: the ADR-005 markdown deliverable must exist")
        index = REPO_ROOT / "docs" / "standards" / "index.json"
        self.assertTrue(index.is_file(), "AC1: the standards index must exist")
        data = json.loads(index.read_text(encoding="utf-8"))
        # The index is a list of standard entries; ADR-005 must be one of them.
        ids = {
            entry.get("id")
            for entry in (data if isinstance(data, list) else data.get("standards", []))
            if isinstance(entry, dict)
        }
        self.assertIn(
            "ADR-005", ids,
            "AC1: landing ADR-005 must regenerate docs/standards/index.json with an "
            "ADR-005 entry",
        )

    _ADR_REL = "docs/standards/adrs/ADR-005-tokenless-bridge-local-cli-executor.md"

    # Runtime artifacts a design-only spike must never ship (a Node manifest / lockfile,
    # or TypeScript/JS source). Pure data so the predicates below can be unit-tested.
    _RUNTIME_BASENAMES = {"package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock"}
    _RUNTIME_SUFFIXES = (".ts", ".tsx", ".js", ".mjs", ".cjs")

    @classmethod
    def _intro_footprint(cls) -> set:
        """ADR-005's footprint = the files changed by the commit that **introduced** the
        ADR-005 doc — read from history, never from the live worktree.

        The previous implementation unioned `git diff origin/dev...HEAD` with
        `git status --porcelain`, i.e. the *whole* worktree, so it false-failed every
        other unit's local suite on that unit's own files and only "passed" in CI by the
        accident of a depth-1 checkout (NB-418 / NB-420). Anchoring to the introducing
        commit — the
        `test_adr_003_workspace_config.py::test_AC4_is_documentation_only_no_engine_rewrite`
        precedent — isolates ADR-005's own files, so the guarantee holds on any full clone
        (local or a deep CI) and a foreign worktree can never pollute it.

        Returns an empty set when the footprint can't be trusted — a shallow checkout
        (CI's default fetch-depth=1, no history), the ADR not yet committed, or a resolved
        commit that looks like a squash/root (more than a handful of files). Callers treat
        empty as a clean scope-skip, which preserves the existing CI behaviour."""

        def _git(args: list[str]) -> str:
            return subprocess.run(
                ["git", *args], cwd=str(REPO_ROOT),
                capture_output=True, text=True, check=True,
            ).stdout

        # A shallow checkout sees one commit and reports every path as added in it, so the
        # introducing-commit lookup is meaningless → empty (callers skip).
        try:
            if _git(["rev-parse", "--is-shallow-repository"]).strip() == "true":
                return set()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return set()

        # The commit that first ADDED the ADR doc (the NB-379 unit). No --follow: the ADR
        # was added at this path and never renamed. First add = last log line.
        try:
            log = _git(
                ["log", "--diff-filter=A", "--format=%H", "--", cls._ADR_REL]
            ).split()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return set()
        if not log:
            return set()

        try:
            changed = set(
                _git(["show", "--name-only", "--format=", log[-1]]).split()
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            return set()

        # A focused single-ADR doc commit touches a handful of files (ADR + index + test).
        # A larger set means a squash/root we can't trust → empty (skip).
        if len(changed) > 6:
            return set()
        return {p.replace("\\", "/") for p in changed if p}

    @classmethod
    def _runtime_markers(cls, footprint) -> list:
        """Runtime artifacts present in a footprint set. Pure — unit-tested below."""
        markers = []
        for path in sorted(footprint):
            base = path.rsplit("/", 1)[-1]
            if base in cls._RUNTIME_BASENAMES or path.endswith(cls._RUNTIME_SUFFIXES):
                markers.append(path)
        return markers

    @classmethod
    def _strays(cls, footprint) -> list:
        """Footprint paths that are neither an allowed deliverable (the ADR + the
        regenerated index) nor a test. Pure — unit-tested below."""
        out = []
        for path in footprint:
            if path in cls._ALLOWED_EXACT:
                continue
            base = path.rsplit("/", 1)[-1]
            if base.startswith("test_") and base.endswith(".py"):
                continue
            out.append(path)
        return sorted(out)

    def test_AC13_no_runtime_code_artifact_shipped(self):
        """No runtime artifact may appear in ADR-005's footprint: no Node manifest
        (`package.json` / lockfile), no TypeScript/JS source, no executable bridge module.
        (The ADR's own claim: 'no `package.json`, no executable — only this ADR and the
        regenerated standards index'.)

        Scoped to `_intro_footprint()` (NB-418 / NB-420): the scan runs on ADR-005's own
        introducing commit, so a foreign worktree — even one that legitimately ships
        `.js` / `package.json` for an unrelated unit — can't false-fail it, and it no longer
        leans on the depth-1 shallow-skip to stay green."""
        footprint = self._intro_footprint()
        if not footprint:
            self.skipTest(
                "ADR-005 introducing commit not resolvable here (shallow checkout / "
                "uncommitted) — anchored instead by the existence test"
            )
        markers = self._runtime_markers(footprint)
        self.assertEqual(
            markers, [],
            "AC1/AC13: this is a design-only spike and must ship NO runtime code; "
            f"found runtime artifact(s) in ADR-005's footprint: {markers}",
        )

    def test_AC13_footprint_is_docs_plus_index_plus_tests_only(self):
        """Every file ADR-005's introducing commit touches must be an allowed deliverable
        (the ADR + the regenerated index) or a test — a stray file outside that set fails,
        proving 'design only' against the diff, not the prose.

        Scoped to `_intro_footprint()` (NB-418 / NB-420): isolates ADR-005's own commit, so
        a foreign worktree skips cleanly (empty footprint) and ADR-005's real footprint is
        policed in full — including a stray with no ADR-005 name marker, the blind spot the
        earlier marker-scoped footprint had."""
        footprint = self._intro_footprint()
        if not footprint:
            self.skipTest(
                "ADR-005 introducing commit not resolvable here — scope skip (NB-418)"
            )
        strays = self._strays(footprint)
        self.assertEqual(
            strays, [],
            "AC1/AC13: a design-only spike's footprint must be the ADR + the "
            "regenerated index (+ tests) only; unexpected file(s) in the unit: "
            f"{strays}",
        )

    def test_AC1_index_modified_for_the_new_adr(self):
        """The deliverable is the ADR *and* the regenerated index, so ADR-005's introducing
        commit must include `docs/standards/index.json` (the index's byte-for-byte content
        is proven by `test_standards_index.py::IndexDriftTest`).

        Scoped to `_intro_footprint()` (NB-418 / NB-420)."""
        footprint = self._intro_footprint()
        if not footprint:
            self.skipTest(
                "ADR-005 introducing commit not resolvable here — scope skip (NB-418)"
            )
        self.assertIn(
            "docs/standards/index.json", footprint,
            "AC1: landing ADR-005 must also regenerate docs/standards/index.json",
        )

    # --- NB-418 AC#2: the design-only guarantee still BITES (not gutted) -----------
    # The footprint *source* is the introducing commit (history), so a stray can't be
    # planted into it from a test. Instead the detection predicates are pure, and these
    # prove they still flag a planted runtime / stray artifact in a synthetic footprint —
    # i.e. were ADR-005's commit to ship such a file, the tests above would fail.
    def test_AC2_runtime_marker_flagged_in_synthetic_footprint(self):
        planted = {self._ADR_REL, "docs/standards/index.json",
                   "package.json", "src/bridge.ts"}
        self.assertEqual(
            self._runtime_markers(planted), ["package.json", "src/bridge.ts"],
            "AC2: a planted Node manifest / TS source must be flagged — the design-only "
            "guarantee must still bite, not be gutted by the scoping fix",
        )

    def test_AC2_unmarked_stray_flagged_in_synthetic_footprint(self):
        planted = {self._ADR_REL, "docs/standards/index.json", "scripts/runtime_bridge.py"}
        self.assertEqual(
            self._strays(planted), ["scripts/runtime_bridge.py"],
            "AC2: a stray non-deliverable, non-test file is flagged even with no ADR-005 "
            "name marker — the blind spot the prior marker-scoped footprint had",
        )

    def test_AC2_clean_synthetic_footprint_is_silent(self):
        clean = {self._ADR_REL, "docs/standards/index.json",
                 "scripts/test_adr_005_tokenless_bridge.py"}
        self.assertEqual(self._strays(clean), [], "AC2: a clean ADR footprint has no strays")
        self.assertEqual(
            self._runtime_markers(clean), [],
            "AC2: a clean ADR footprint has no runtime markers",
        )

    # --- NB-418 AC#5: sibling ADR footprint tests checked for the same pattern ------
    # test_adr_003_workspace_config.py already anchors to the ADR's introducing commit
    # (test_AC4_is_documentation_only_no_engine_rewrite) — it does NOT carry the
    # whole-worktree pattern, so no change is needed there.
    # test_adr_006_tier2_local_identity.py deliberately ships no footprint scan (its header
    # cites this very pattern as a tracked bug). ADR-005 (this file) was the last carrier of
    # the whole-worktree footprint; with this change it is gone.


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
