"""Content tests for NB-366 (Unit 3: Releases — notes + GH Release + Linear summary).

Prose/skill-edit unit on a single command file (`commands/release.md`). Each AC
is proven by file-existence + content assertions on the markdown source. One
test per AC string-shape claim so the proof maps 1:1 to the unit's acceptance
criteria.

ACs proven here:
- AC1 — `release` computes the included-issue set for a tag range
  (branch/PR linkage; degrade to issues completed in range).
- AC2 — A GitHub Release is created with grouped notes
  (`gh release create --notes-file`).
- AC3 — Each included issue gets a "Shipped in vX.Y.Z — <url>" comment; an
  Initiative/Project roll-up is posted where one exists.
- AC4 — Re-running `release` for an existing tag does not duplicate comments
  (marker detect).
- AC5 — `release-script-version` is bumped to the next release version
  (per §0 preflight).

PLUS a regression check: §0 preflight logic is structurally unchanged
(the comparison still references `$SCRIPT_VERSION` and `$REPO_VERSION`).

Run from the repo root:  python scripts/test_release_linear_summary.py
"""

import json
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
RELEASE_PATH = REPO_ROOT / "commands" / "release.md"
PLUGIN_JSON = REPO_ROOT / ".claude-plugin" / "plugin.json"


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


class AC1_IncludedIssueSetComputation(unittest.TestCase):
    """AC1: `release` computes the included-issue set for a tag range
    (branch/PR linkage; degrade to issues completed in range).
    """

    def test_AC1_release_md_exists(self):
        self.assertTrue(RELEASE_PATH.is_file(), f"{RELEASE_PATH} must exist")

    def test_AC1_walks_all_commits_not_only_merges(self):
        """NB-425: §6.5a must walk ALL commits in the tag range (the squash-merges onto
        the integration branch carry the issue identity; the release-branch merge commits
        do not), feeding them to `scripts/release_scan.py`. The old `git log --merges`
        contract is superseded and must be gone.
        """
        body = _read(RELEASE_PATH)
        # The walk must be the all-commits form `git ... log <prev-tag>..vX.Y.Z` (no
        # --merges). Every git call in this file is `-C "$WT"`-scoped per §3, so allow the
        # -C "$WT" interposition.
        self.assertRegex(
            body,
            r"git\s+(-C\s+[^\s]+\s+)?log\s+<prev-tag>\.\.vX\.Y\.Z",
            "AC1/NB-425: must walk `git log <prev-tag>..vX.Y.Z` (all commits, not merges)",
        )
        # The superseded merge-only *instruction* must NOT reappear (drift guard): forbid
        # the `log --merges <prev-tag>..vX.Y.Z` walk command specifically, so an
        # explanatory mention of the old contract in prose does not false-trip.
        self.assertNotRegex(
            body,
            r"log\s+--merges\s+<prev-tag>",
            "AC1/NB-425: the superseded `git log --merges <prev-tag>..` walk must be gone",
        )
        # The all-commits set is computed by the tested pure module, not inline prose.
        self.assertIn(
            "scripts/release_scan.py",
            body,
            "AC1/NB-425: §6.5a must invoke the tested `scripts/release_scan.py` module",
        )

    def test_AC1_documents_inclusion_vs_advisory(self):
        """NB-425: the inclusion-vs-advisory distinction and the bare `#N` scope form (the
        identifier the old pattern missed) must be documented in prose."""
        body = _read(RELEASE_PATH)
        self.assertRegex(
            body,
            r"[Aa]dvisory",
            "AC1/NB-425: §6.5a must document the advisory (incidental-reference) set",
        )
        # The conventional-commit scope form `feat(#N)` (bare #N, no NB- prefix) is the
        # form the old scan missed — it must be named as an inclusion.
        self.assertRegex(
            body,
            r"feat\(#N\)|`#N`",
            "AC1/NB-425: §6.5a must name the bare `#N` conventional-commit scope form",
        )

    def test_AC1_extracts_NB_identifiers_from_branch_pr_or_commit(self):
        body = _read(RELEASE_PATH)
        # The magic-word pattern NB-N must be named so the script knows what to extract.
        self.assertIn(
            "NB-N",
            body,
            "AC1: must name the `NB-N` magic-word pattern as the Linear-identifier shape",
        )
        # And the branch-naming convention used by /backlogd:solve must be referenced
        # so the script knows where to scan.
        self.assertIn(
            "nicolaibernsen/nb-",
            body,
            "AC1: must reference the `nicolaibernsen/nb-<n>-<slug>` branch convention as one extraction source",
        )

    def test_AC1_degrades_to_issues_completed_in_range(self):
        """If branch/PR linkage yields nothing, fall back to issues completed in the
        tag's date range — the AC's explicit degrade path."""
        body = _read(RELEASE_PATH)
        # The fallback must reference list_issues with a completedAt filter.
        self.assertIn(
            "list_issues",
            body,
            "AC1: degrade path must call `list_issues` to enumerate issues by completion date",
        )
        self.assertIn(
            "completedAt",
            body,
            "AC1: degrade path must filter by `completedAt` in the tag range",
        )
        # The "degrade" framing must be explicit in prose (so a reader knows this is
        # the fallback, not the primary path).
        self.assertRegex(
            body,
            r"[Dd]egrade",
            "AC1: must explicitly frame the fallback as a graceful degrade path",
        )


class AC2_GitHubReleaseWithGroupedNotes(unittest.TestCase):
    """AC2: A GitHub Release is created with grouped notes
    (`gh release create --notes-file`).
    """

    def test_AC2_invokes_gh_release_create(self):
        body = _read(RELEASE_PATH)
        self.assertIn(
            "gh release create",
            body,
            "AC2: must invoke `gh release create` to cut the GitHub Release",
        )

    def test_AC2_uses_notes_file_flag(self):
        body = _read(RELEASE_PATH)
        self.assertIn(
            "--notes-file",
            body,
            "AC2: must use `--notes-file` (the canonical hand-off mechanism, not inline --notes)",
        )

    def test_AC2_release_notes_are_grouped(self):
        """The release notes body must be grouped (features / fixes / docs / etc.) —
        not a flat dump. Look for grouping language and at least one canonical group
        heading in the rendered notes block.
        """
        body = _read(RELEASE_PATH)
        self.assertRegex(
            body,
            r"[Gg]roup(ed|ing)?",
            "AC2: must document that release notes are grouped (not a flat list)",
        )
        # The rendered example must show at least one of the standard group headings.
        self.assertRegex(
            body,
            r"##\s+(Features|Fixes|Docs|Tech-debt|Other)",
            "AC2: notes-file template must show a grouped section heading (Features/Fixes/Docs/...)",
        )

    def test_AC2_captures_release_url(self):
        """`gh release create --notes-file` returns the release URL — the script
        must capture it for the per-issue Shipped comments to link to."""
        body = _read(RELEASE_PATH)
        # The captured variable convention from the developer's diff.
        self.assertIn(
            "REL_URL",
            body,
            "AC2: must capture the gh-release URL (e.g. as $REL_URL) for downstream Linear writes",
        )


class AC3_ShippedCommentAndRollup(unittest.TestCase):
    """AC3: Each included issue gets a "Shipped in vX.Y.Z — <url>" comment;
    an Initiative/Project roll-up is posted where one exists.
    """

    def test_AC3_per_issue_shipped_marker(self):
        body = _read(RELEASE_PATH)
        # The canonical marker substring — also the dedupe key (AC4).
        self.assertIn(
            "Shipped in vX.Y.Z",
            body,
            "AC3: must specify the `Shipped in vX.Y.Z` marker line as the per-issue comment shape",
        )

    def test_AC3_per_issue_save_comment_with_issueId(self):
        body = _read(RELEASE_PATH)
        # The verified call shape for the per-issue write: save_comment({ issueId, body }).
        self.assertRegex(
            body,
            r"save_comment\(\{\s*issueId",
            "AC3: must call save_comment({ issueId, ... }) for the per-issue Shipped comment",
        )

    def test_AC3_rollup_for_project_or_initiative(self):
        body = _read(RELEASE_PATH)
        # Roll-up is posted to whichever parent exists (Project and/or Initiative).
        # Accept either parent — the AC requires "where one exists".
        has_project_rollup = bool(re.search(r"save_comment\(\{\s*projectId", body))
        has_initiative_rollup = bool(
            re.search(r"save_comment\(\{\s*initiativeId", body)
        )
        self.assertTrue(
            has_project_rollup or has_initiative_rollup,
            "AC3: must call save_comment({ projectId | initiativeId, ... }) for the roll-up",
        )

    def test_AC3_rollup_covers_both_parent_shapes(self):
        """The reference (and this command) supports both Project and Initiative
        roll-ups — `save_comment` accepts exactly one parent at a time. Verify
        both call shapes appear so the script can route to whichever the issue
        actually rolls up to.
        """
        body = _read(RELEASE_PATH)
        self.assertRegex(
            body,
            r"save_comment\(\{\s*projectId",
            "AC3: must show the projectId roll-up call shape",
        )
        self.assertRegex(
            body,
            r"save_comment\(\{\s*initiativeId",
            "AC3: must show the initiativeId roll-up call shape",
        )

    def test_AC3_rollup_links_to_release_url(self):
        body = _read(RELEASE_PATH)
        # The roll-up body must include the captured release URL placeholder.
        self.assertIn(
            "$REL_URL",
            body,
            "AC3: roll-up bodies must include the captured release URL",
        )


class AC4_IdempotencyByMarkerDedupe(unittest.TestCase):
    """AC4: Re-running `release` for an existing tag does not duplicate comments
    (marker detect).
    """

    def test_AC4_lists_existing_comments_before_writing(self):
        body = _read(RELEASE_PATH)
        # The dedupe procedure: list comments first, scan for the marker, skip on hit.
        self.assertIn(
            "list_comments",
            body,
            "AC4: must call `list_comments` first to scan for an existing Shipped marker",
        )

    def test_AC4_skips_if_marker_already_present(self):
        body = _read(RELEASE_PATH)
        # The skip language must be explicit so a reader knows hits are no-ops.
        self.assertRegex(
            body,
            r"skip",
            "AC4: must use `skip` language when the marker is already present",
        )

    def test_AC4_carries_explicit_idempotency_note(self):
        body = _read(RELEASE_PATH)
        # The AC requires an explicit idempotency contract for re-runs.
        self.assertRegex(
            body,
            r"[Ii]dempoten",
            "AC4: must carry an explicit idempotency note for re-runs",
        )
        # And the contract: re-runs must not duplicate comments.
        self.assertIn(
            "must not duplicate comments",
            body,
            "AC4: must state explicitly that re-running must not duplicate comments",
        )

    def test_AC4_dedupe_key_is_the_versioned_marker(self):
        """The `Shipped in vX.Y.Z` substring (for the exact version) is the
        dedupe key — that's the contract that lets a re-run be safe.
        """
        body = _read(RELEASE_PATH)
        # The dedupe-key framing must be explicit somewhere.
        self.assertRegex(
            body,
            r"dedupe key",
            "AC4: must name `Shipped in vX.Y.Z` as the dedupe key",
        )


class AC5_ReleaseScriptVersionBumped(unittest.TestCase):
    """AC5: `release-script-version` is bumped to the next release version
    (per §0 preflight).
    """

    def test_AC5_script_version_tag_is_present(self):
        body = _read(RELEASE_PATH)
        self.assertRegex(
            body,
            r"<!--\s*release-script-version:\s*\d+\.\d+\.\d+\s*-->",
            "AC5: file must carry an `<!-- release-script-version: X.Y.Z -->` tag",
        )

    def test_AC5_script_version_matches_plugin_json(self):
        """release-script-version must equal the plugin.json version (a single
        match) — the invariant that keeps the §0 preflight from false-bailing.
        Version-agnostic by design so it does not re-break on each release bump
        (it broke once at v0.14.0 when frozen to 0.13.0 — see NB-389)."""
        body = _read(RELEASE_PATH)
        matches = re.findall(
            r"<!--\s*release-script-version:\s*(\d+\.\d+\.\d+)\s*-->", body
        )
        plugin_version = json.loads(_read(PLUGIN_JSON))["version"]
        self.assertEqual(
            matches,
            [plugin_version],
            f"AC5: release-script-version must be exactly the plugin.json version "
            f"`{plugin_version}` (single match); got {matches}",
        )

    def test_AC5_script_version_is_bumped_from_previous(self):
        """The current main is at v0.11.1 — the bumped tag must be strictly
        greater (lexicographic over numeric components), proving a forward bump.
        """
        body = _read(RELEASE_PATH)
        m = re.search(
            r"<!--\s*release-script-version:\s*(\d+)\.(\d+)\.(\d+)\s*-->", body
        )
        self.assertIsNotNone(m, "AC5: release-script-version tag must be parseable")
        current = tuple(int(x) for x in m.groups())
        previous = (0, 11, 1)  # the v0.11.1 baseline this PR ships forward from
        self.assertGreater(
            current,
            previous,
            f"AC5: release-script-version must be strictly greater than {previous}; got {current}",
        )


class PreflightRegression(unittest.TestCase):
    """Regression check: §0 preflight comparison logic is structurally unchanged.

    The dev's diff explicitly preserves §0's behaviour — only the version *value*
    in the HTML comment was bumped, the comparison logic between
    `$SCRIPT_VERSION` and `$REPO_VERSION` must still be intact. If a future edit
    refactors §0 without preserving the comparison contract, this test fires.
    """

    def test_preflight_references_SCRIPT_VERSION(self):
        body = _read(RELEASE_PATH)
        self.assertIn(
            "$SCRIPT_VERSION",
            body,
            "Regression: §0 preflight must still reference `$SCRIPT_VERSION`",
        )

    def test_preflight_references_REPO_VERSION(self):
        body = _read(RELEASE_PATH)
        self.assertIn(
            "$REPO_VERSION",
            body,
            "Regression: §0 preflight must still reference `$REPO_VERSION`",
        )

    def test_preflight_compares_script_strictly_older(self):
        """The bail condition is `SCRIPT < REPO` (strictly older) — verify the
        comparison is still written that way (script-older fails, equal/newer
        proceeds)."""
        body = _read(RELEASE_PATH)
        self.assertRegex(
            body,
            r"\$SCRIPT_VERSION\s*<\s*\$REPO_VERSION",
            "Regression: §0 must still compare `$SCRIPT_VERSION < $REPO_VERSION` for the bail path",
        )

    def test_preflight_stop_immediately_phrase_preserved(self):
        """The §0 wording 'stop immediately' is the safety contract — preserve it."""
        body = _read(RELEASE_PATH)
        self.assertIn(
            "stop immediately",
            body,
            "Regression: §0 must still carry the 'stop immediately' bail directive",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
