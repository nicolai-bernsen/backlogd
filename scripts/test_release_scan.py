"""Tests for scripts/release_scan.py — standard library only (unittest).

The headline test (``RealV020HistoryTest``) feeds a synthetic commit list drawn from the
repo's **real v0.20.0 history** and asserts the computed *included* set is exactly right —
the two-directional failure NB-425 fixes (missing real issues, inventing false ones):

* ``feat(#413): …``                       -> 413 included (bare ``#N`` scope, no ``NB-`` prefix)
* ``fix(#418): … (closes NB-420) (#129)``  -> 418 + 420 included, 129 **not** (trailing PR no.)
* a plain ``NB-360 …`` subject              -> 360 included
* head-branch ``nicolaibernsen/nb-354-…``  -> 354 included
* a body-only mention of NB-315/340/398     -> advisory, **not** included

Run from the repo root:
    python -m unittest scripts.test_release_scan
    python -m unittest discover -s scripts -p 'test_*.py'    # CI uses this
"""

import io
import contextlib
import pathlib
import shutil
import subprocess
import sys
import unittest
import unittest.mock

# Make `import release_scan` work regardless of how this file is invoked.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import release_scan as rs  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


# --- real v0.20.0 commit bodies (verbatim shapes) --------------------------
# Drawn from `git log v0.19.0..v0.20.0`. The two issue-bearing squash subjects plus a
# realistic body that references prior shipped issues (the over-detection trap).

FEAT_413_SUBJECT = (
    "feat(#413): specialists self-verify their ACs (gate-run checks + enumerated hand-off) (#128)"
)
FEAT_413_BODY = (
    "Every runnable AC a specialist is dispatched against is now verifiable before "
    "hand-off. The decision plus rejected alternatives is recorded in the NB-340 "
    "tool-grant lineage (skills/reviewer + skills/linear). Collateral: scopes the "
    "ADR-005 footprint tests to ADR-005-attributable paths (converges with PR #124; "
    "NB-418), keeping the whole-diff runtime-artifact scan."
)

FIX_418_SUBJECT = (
    "fix(#418): scope ADR-005 footprint tests to the introducing commit (closes NB-420) (#129)"
)
FIX_418_BODY = (
    "The ADR-005 footprint tests computed the unit's changed set over the whole worktree, "
    "so they false-failed every other unit's local suite (NB-418 / NB-420). Supersedes the "
    "incidental marker-scope from #128. 584 tests pass."
)

# A release-branch merge commit — carries NO Linear identity at all (the --merges trap).
RELEASE_MERGE_SUBJECT = "Merge pull request #130 from nicolai-bernsen/release/v0.20.0"
CHORE_RELEASE_SUBJECT = "chore(release): v0.20.0"


class ExtractorUnitTest(unittest.TestCase):
    """Each pure per-field extractor in isolation."""

    def test_scope_id_bare_hash(self):
        self.assertEqual(rs.scope_ids("feat(#413): do a thing"), {413})
        self.assertEqual(rs.scope_ids("fix(#418): another (closes NB-420) (#129)"), {418})

    def test_scope_id_various_types_and_bang(self):
        self.assertEqual(rs.scope_ids("docs(#395): readme"), {395})
        self.assertEqual(rs.scope_ids("refactor(#7)!: breaking"), {7})
        self.assertEqual(rs.scope_ids("CHORE(#12): caps type"), {12})

    def test_scope_id_absent(self):
        self.assertEqual(rs.scope_ids("Merge pull request #130 from x"), set())
        self.assertEqual(rs.scope_ids("just some words #99 in the middle"), set())

    def test_trailing_pr_number(self):
        self.assertEqual(rs.trailing_pr_number("fix(#418): x (closes NB-420) (#129)"), 129)
        self.assertEqual(rs.trailing_pr_number("feat(#413): y (#128)"), 128)
        self.assertIsNone(rs.trailing_pr_number("feat(#413): no trailing pr"))
        # A bracketed number NOT at end-of-string is not the trailing PR number.
        self.assertIsNone(rs.trailing_pr_number("feat: see (#99) for context here"))

    def test_magic_word_ids_subject_and_body(self):
        self.assertEqual(rs.magic_word_ids("x (closes NB-420)"), {420})
        self.assertEqual(rs.magic_word_ids("fixes #77 and resolves NB-78"), {77, 78})
        self.assertEqual(rs.magic_word_ids("no directive NB-5 here"), set())

    def test_branch_ids_case_insensitive(self):
        self.assertEqual(rs.branch_ids("nicolaibernsen/nb-354-roster"), {354})
        self.assertEqual(rs.branch_ids("bernie/NB-425-release-scan"), {425})
        self.assertEqual(rs.branch_ids(""), set())
        self.assertEqual(rs.branch_ids("main"), set())

    def test_bare_subject_ids_excludes_scope_and_trailing_pr(self):
        # The scope (#418) is excluded here (added separately); the trailing (#129) PR
        # number is stripped; only the NB-420 magic-word id remains in the subject sweep.
        self.assertEqual(
            rs.bare_subject_ids("fix(#418): x (closes NB-420) (#129)"), {420}
        )

    def test_bare_subject_id_plain(self):
        self.assertEqual(rs.bare_subject_ids("NB-360 tidy the roster"), {360})


class ScanInclusionTest(unittest.TestCase):
    """`scan` over single commits — each inclusion rule fires."""

    def test_scope_inclusion(self):
        r = rs.scan([rs.Commit(subject="feat(#413): a thing")])
        self.assertEqual(r.included_sorted, [413])
        self.assertEqual(r.advisory_sorted, [])

    def test_plain_nb_subject_inclusion(self):
        r = rs.scan([rs.Commit(subject="NB-360 tidy the roster")])
        self.assertEqual(r.included_sorted, [360])

    def test_magic_word_in_body_is_inclusion(self):
        # A closes/fixes directive in the BODY is a structural inclusion (explicit intent),
        # not a mere advisory mention.
        r = rs.scan([rs.Commit(subject="some work", body="This closes NB-501 finally.")])
        self.assertEqual(r.included_sorted, [501])
        self.assertEqual(r.advisory_sorted, [])

    def test_branch_inclusion(self):
        r = rs.scan([rs.Commit(subject="opaque subject",
                               head_branch="nicolaibernsen/nb-354-tidy")])
        self.assertEqual(r.included_sorted, [354])

    def test_trailing_pr_number_never_included_or_advisory(self):
        r = rs.scan([rs.Commit(subject="feat(#413): a thing (#128)")])
        self.assertEqual(r.included_sorted, [413])
        self.assertNotIn(128, r.included)
        self.assertNotIn(128, r.advisory)

    def test_body_only_mention_is_advisory(self):
        r = rs.scan([rs.Commit(subject="feat(#413): a thing",
                               body="builds on NB-340 and NB-398 (already shipped)")])
        self.assertEqual(r.included_sorted, [413])
        self.assertEqual(r.advisory_sorted, [340, 398])

    def test_inclusion_wins_over_advisory_globally(self):
        # NB-413 is a body mention in one commit and a scope inclusion in another — it must
        # land in included only, never advisory.
        r = rs.scan([
            rs.Commit(subject="docs(#9): note", body="see NB-413 for context"),
            rs.Commit(subject="feat(#413): the actual work"),
        ])
        self.assertIn(413, r.included)
        self.assertNotIn(413, r.advisory_sorted)


class RealV020HistoryTest(unittest.TestCase):
    """THE headline test: the synthetic v0.20.0 commit list yields the exact shipped set.

    Covers every case the AC enumerates at once, against real commit shapes.
    """

    def _commits(self):
        return [
            # The two issue-bearing squash-merges onto the integration branch.
            rs.Commit(subject=FEAT_413_SUBJECT, body=FEAT_413_BODY),
            rs.Commit(subject=FIX_418_SUBJECT, body=FIX_418_BODY),
            # A plain NB-N subject (no conventional scope).
            rs.Commit(subject="NB-360 tidy the persona roster"),
            # A commit whose issue identity lives only in the head-branch name.
            rs.Commit(subject="chore: routine cleanup",
                      head_branch="nicolaibernsen/nb-354-roster-tidy"),
            # Release-branch noise: merge commit + the version-bump chore — no issue id.
            rs.Commit(subject=RELEASE_MERGE_SUBJECT),
            rs.Commit(subject=CHORE_RELEASE_SUBJECT),
        ]

    def test_included_set_is_exactly_right(self):
        r = rs.scan(self._commits())
        # 413 (scope), 418 (scope) + 420 (closes), 360 (plain subject), 354 (branch).
        self.assertEqual(r.included_sorted, [354, 360, 413, 418, 420])

    def test_trailing_pr_numbers_not_included(self):
        r = rs.scan(self._commits())
        for pr in (128, 129, 130):
            self.assertNotIn(pr, r.included, f"PR #{pr} must not be in the included set")

    def test_body_only_refs_are_advisory_not_included(self):
        r = rs.scan(self._commits())
        # NB-315/340/398 are the classic incidental body refs; 340 is the one actually
        # present in the feat(#413) body. None may be included.
        for inc in (315, 340, 398):
            self.assertNotIn(inc, r.included,
                             f"NB-{inc} is a body-only ref — must not be included")
        # 340 must surface as advisory (it is mentioned in the feat body, not via any
        # inclusion rule).
        self.assertIn(340, r.advisory_sorted)

    def test_release_merge_commits_contribute_nothing(self):
        # The --merges trap: these carry no Linear identity. Scanning them alone yields an
        # empty included set — which is exactly why --merges under-detected.
        r = rs.scan([rs.Commit(subject=RELEASE_MERGE_SUBJECT),
                     rs.Commit(subject=CHORE_RELEASE_SUBJECT),
                     rs.Commit(subject="Merge pull request #126 from nicolai-bernsen/main")])
        self.assertEqual(r.included_sorted, [])
        self.assertEqual(r.advisory_sorted, [])


# --- live git-history regression (the AC's "drawn from real v0.20.0 history" at its
# strongest: run the ACTUAL `git log v0.19.0..v0.20.0` through the module rather than a
# hand-transcribed copy of it, so the test cannot pass while the real CLI drifts) --------

def _git(args):
    """Run a git command in the repo root; return (rc, stdout) or (None, '') if git absent."""
    try:
        proc = subprocess.run(
            ["git", *args], cwd=str(REPO_ROOT),
            capture_output=True, text=True, encoding="utf-8",
        )
    except FileNotFoundError:
        return None, ""
    return proc.returncode, proc.stdout


def _live_history_available():
    """True only when this checkout can be trusted for a v0.19.0..v0.20.0 range scan.

    Skips (returns False) on the conditions the repo's other shell-out tests already guard
    for — git absent, a shallow CI checkout (no history), or the tags simply not present in
    this clone — so the regression degrades to a clean skip instead of a false red.
    """
    if shutil.which("git") is None:
        return False
    rc, out = _git(["rev-parse", "--is-shallow-repository"])
    if rc != 0 or out.strip() == "true":
        return False
    for tag in ("v0.19.0", "v0.20.0"):
        rc, _ = _git(["rev-parse", "--verify", "-q", f"{tag}^{{commit}}"])
        if rc != 0:
            return False
    return True


@unittest.skipUnless(
    _live_history_available(),
    "git/tags/full-history unavailable (shallow CI checkout or missing v0.19.0/v0.20.0) — "
    "the synthetic RealV020HistoryTest still covers the contract",
)
class LiveV020HistoryRegressionTest(unittest.TestCase):
    """Scan the REAL `git log v0.19.0..v0.20.0` payload and assert the exact sets.

    This is the empirical backstop behind the synthetic ``RealV020HistoryTest``: if a future
    edit to the module (or a drift between the hand-transcribed fixtures and what git really
    emits) changed the answer for the actual shipped range, this fires where the fixture test
    would not. It feeds the module exactly the delimited stream ``commands/release.md`` §6.5a
    pipes in, via the module's own ``parse_log``.
    """

    def _scan_real_range(self):
        fmt = "%s" + rs.FIELD_SEP + "%b" + rs.RECORD_SEP
        rc, out = _git(["log", "v0.19.0..v0.20.0", f"--format={fmt}"])
        self.assertEqual(rc, 0, "git log of the v0.19.0..v0.20.0 range must succeed")
        return rs.scan(rs.parse_log(out))

    def test_included_set_matches_real_v020_range(self):
        # The true shipped set for v0.20.0: NB-413 (feat scope — the id the old bare-`NB-N`
        # pattern dropped), NB-418 (fix scope) and NB-420 (its `closes NB-420` directive).
        r = self._scan_real_range()
        self.assertEqual(r.included_sorted, [413, 418, 420])

    def test_advisory_set_matches_real_v020_range(self):
        # The incidental body references in the real commits — reported separately, never
        # shipped: NB-315 / NB-340 / NB-398.
        r = self._scan_real_range()
        self.assertEqual(r.advisory_sorted, [315, 340, 398])

    def test_trailing_pr_numbers_absent_from_both_sets_in_real_range(self):
        # The squash subjects carry trailing PR numbers (#128, #129) and the range includes
        # `Merge pull request #130 …`; none of these PR numbers may appear in either set.
        r = self._scan_real_range()
        for pr in (126, 127, 128, 129, 130):
            self.assertNotIn(pr, r.included, f"PR #{pr} must not be in the included set")
            self.assertNotIn(pr, r.advisory, f"PR #{pr} must not be in the advisory set")


class ParseLogTest(unittest.TestCase):
    """The delimited-stream parser the CLI reads."""

    def test_parse_two_records(self):
        stream = (
            "feat(#413): a thing" + rs.FIELD_SEP + "body one" + rs.FIELD_SEP + "" + rs.RECORD_SEP
            + "fix(#418): another" + rs.FIELD_SEP + "body two (closes NB-420)" + rs.FIELD_SEP
            + "nicolaibernsen/nb-418-x" + rs.RECORD_SEP
        )
        commits = rs.parse_log(stream)
        self.assertEqual(len(commits), 2)
        self.assertEqual(commits[0].subject, "feat(#413): a thing")
        self.assertEqual(commits[0].body, "body one")
        self.assertEqual(commits[1].head_branch, "nicolaibernsen/nb-418-x")

    def test_parse_skips_empty_trailing_record(self):
        stream = "NB-1 x" + rs.FIELD_SEP + "" + rs.FIELD_SEP + "" + rs.RECORD_SEP + "\n"
        commits = rs.parse_log(stream)
        self.assertEqual(len(commits), 1)

    def test_parse_handles_missing_fields(self):
        # A subject-only record (no field separators) still parses.
        commits = rs.parse_log("feat(#7): solo" + rs.RECORD_SEP)
        self.assertEqual(len(commits), 1)
        self.assertEqual(commits[0].subject, "feat(#7): solo")
        self.assertEqual(commits[0].body, "")

    def test_parse_then_scan_end_to_end(self):
        stream = (
            FEAT_413_SUBJECT + rs.FIELD_SEP + FEAT_413_BODY + rs.FIELD_SEP + "" + rs.RECORD_SEP
            + FIX_418_SUBJECT + rs.FIELD_SEP + FIX_418_BODY + rs.FIELD_SEP + "" + rs.RECORD_SEP
        )
        r = rs.scan(rs.parse_log(stream))
        self.assertEqual(r.included_sorted, [413, 418, 420])
        self.assertIn(340, r.advisory_sorted)
        self.assertNotIn(129, r.included)


class RenderAndCliTest(unittest.TestCase):
    """The two-line CLI rendering + the stdin-driven `main`."""

    def test_render_shape(self):
        r = rs.ScanResult(included={413, 418}, advisory={340})
        self.assertEqual(rs.render(r), "included: NB-413, NB-418\nadvisory: NB-340\n")

    def test_render_none_when_empty(self):
        self.assertEqual(rs.render(rs.ScanResult()), "included: none\nadvisory: none\n")

    def test_main_reads_stdin_and_prints(self):
        stream = (
            FEAT_413_SUBJECT + rs.FIELD_SEP + FEAT_413_BODY + rs.FIELD_SEP + "" + rs.RECORD_SEP
            + FIX_418_SUBJECT + rs.FIELD_SEP + FIX_418_BODY + rs.FIELD_SEP + "" + rs.RECORD_SEP
        )
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with unittest.mock.patch("sys.stdin", io.StringIO(stream)):
                rc = rs.main([])
        self.assertEqual(rc, 0)
        printed = out.getvalue()
        self.assertIn("included: NB-413, NB-418, NB-420", printed)
        self.assertIn("advisory:", printed)
        self.assertIn("NB-340", printed.splitlines()[1])  # the advisory line
        self.assertNotIn("NB-129", printed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
