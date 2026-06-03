"""Unit tests for scripts/ledger.py — standard library only (unittest).

Run from the repo root:  python scripts/test_ledger.py
Or via the suite:        python -m unittest discover -s scripts -p 'test_*.py'
Or via pytest:           python -m pytest scripts -k ledger

Each test redirects the ledger to a fresh temp dir via BACKLOGD_LEDGER_DIR, so
no .backlogd/ directory is created in the working tree.

Test method names deliberately contain ``ledger`` so the AC's
``pytest scripts -k ledger`` selector matches them, and the append-only /
across-runs tests contain ``append`` / ``survive`` so
``-k "ledger and (append or survive)"`` matches that subset.
"""

import io
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

# Make `import ledger` work regardless of how this file is invoked.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ledger  # noqa: E402


class _LedgerTempStoreMixin(unittest.TestCase):
    """Redirect the ledger to a throwaway temp dir for each test."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["BACKLOGD_LEDGER_DIR"] = str(pathlib.Path(self._tmp.name) / "store")
        os.environ.pop("BACKLOGD_LEDGER_FILE", None)

    def tearDown(self):
        os.environ.pop("BACKLOGD_LEDGER_DIR", None)
        os.environ.pop("BACKLOGD_LEDGER_FILE", None)
        self._tmp.cleanup()


class LedgerRecordReadTest(_LedgerTempStoreMixin):
    """AC2: a completed run records, then reads back by problem identifier."""

    def test_ledger_record_run_then_read_back_by_problem(self):
        # Record one completed run into the temp store.
        rec = ledger.record_run(
            "NB-426",
            units=[{"identifier": "NB-426", "outcome": "solved"}],
            pr="https://github.com/acme/repo/pull/131",
            outcome="solved",
            ts="2026-06-03T05:00:00Z",
        )
        self.assertEqual(rec["v"], "backlogd-ledger/v1")

        # The query surface returns the record for that problem identifier.
        runs = ledger.read_runs("NB-426")
        self.assertEqual(len(runs), 1)
        run = runs[0]
        # Units solved with their outcomes.
        self.assertEqual(run["units"], [{"identifier": "NB-426", "outcome": "solved"}])
        # PR reference.
        self.assertEqual(run["pr"], "https://github.com/acme/repo/pull/131")
        # Run-level outcome + the timestamp.
        self.assertEqual(run["outcome"], "solved")
        self.assertEqual(run["ts"], "2026-06-03T05:00:00Z")

    def test_ledger_read_runs_unknown_problem_is_empty(self):
        ledger.record_run("NB-1", units=["NB-1"], outcome="solved")
        self.assertEqual(ledger.read_runs("NB-999"), [])

    def test_ledger_read_runs_filters_to_the_asked_problem(self):
        ledger.record_run("NB-1", units=["NB-1"], outcome="solved")
        ledger.record_run("NB-2", units=["NB-2"], outcome="solved")
        runs = ledger.read_runs("NB-2")
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["problem"], "NB-2")

    def test_ledger_missing_store_reads_empty(self):
        # Point at a never-created dir; reads must be empty, not raise.
        os.environ["BACKLOGD_LEDGER_DIR"] = str(
            pathlib.Path(self._tmp.name) / "never-created")
        self.assertEqual(ledger.read_all(), [])
        self.assertEqual(ledger.read_runs("NB-1"), [])

    def test_ledger_bare_string_units_normalise(self):
        # A caller may pass bare identifier strings; they wrap to dicts.
        ledger.record_run("NB-5", units=["NB-5", "NB-6"], outcome="solved")
        units = ledger.read_runs("NB-5")[0]["units"]
        self.assertEqual(
            units,
            [{"identifier": "NB-5", "outcome": None},
             {"identifier": "NB-6", "outcome": None}],
        )

    def test_ledger_ops_only_run_has_null_pr(self):
        # Ops-only runs have no PR; pr is recorded as null and reads back as None.
        ledger.record_run("NB-7", units=["NB-7"], pr=None, outcome="solved")
        self.assertIsNone(ledger.read_runs("NB-7")[0]["pr"])

    def test_ledger_empty_units_run_records_and_reads_back(self):
        # An ops-only / no-units run (units=None or []) records a well-formed
        # record with units: [] and reads back — and a later run with units
        # still appends beside it intact. The handoff doc's ops-only path can
        # produce a unit-less record, so the empty case must round-trip.
        ledger.record_run("NB-8", units=None, pr=None, outcome="solved",
                          ts="2026-06-03T01:00:00Z")
        ledger.record_run("NB-9", units=[], pr=None, outcome="solved",
                          ts="2026-06-03T02:00:00Z")
        self.assertEqual(ledger.read_runs("NB-8")[0]["units"], [])
        self.assertEqual(ledger.read_runs("NB-9")[0]["units"], [])
        # The unit-less records did not clobber each other.
        self.assertEqual([r["problem"] for r in ledger.read_all()], ["NB-8", "NB-9"])


class LedgerAppendSurviveTest(_LedgerTempStoreMixin):
    """AC4: append-friendly and survives across runs (no truncate/overwrite)."""

    def test_ledger_append_does_not_truncate_first_record(self):
        # Record two runs for two problems; the second append must not clobber
        # the first record.
        ledger.record_run("NB-1", units=["NB-1"], outcome="solved",
                          ts="2026-06-01T00:00:00Z")
        ledger.record_run("NB-2", units=["NB-2"], outcome="solved",
                          ts="2026-06-02T00:00:00Z")
        allrecs = ledger.read_all()
        self.assertEqual(len(allrecs), 2)
        # Both problems' records are present and intact.
        self.assertEqual([r["problem"] for r in allrecs], ["NB-1", "NB-2"])
        self.assertEqual(ledger.read_runs("NB-1")[0]["ts"], "2026-06-01T00:00:00Z")

    def test_ledger_append_keeps_multiple_runs_for_same_problem(self):
        # Same problem re-run twice (e.g. a re-dispatch): both records survive,
        # oldest-first — the ledger does not dedup, it is an append-only history.
        ledger.record_run("NB-3", units=["NB-3"], outcome="partial",
                          ts="2026-06-01T00:00:00Z")
        ledger.record_run("NB-3", units=["NB-3"], outcome="solved",
                          ts="2026-06-02T00:00:00Z")
        runs = ledger.read_runs("NB-3")
        self.assertEqual(len(runs), 2)
        self.assertEqual([r["outcome"] for r in runs], ["partial", "solved"])

    def test_ledger_survives_across_simulated_separate_runs(self):
        # Simulate two separate process invocations by re-reading the file fresh
        # after each append (read_all re-opens the file every call).
        ledger.record_run("NB-10", units=["NB-10"], outcome="solved")
        after_first = ledger.read_all()
        self.assertEqual(len(after_first), 1)

        ledger.record_run("NB-11", units=["NB-11"], outcome="solved")
        after_second = ledger.read_all()
        # The first run's record survived the second run's append.
        self.assertEqual(len(after_second), 2)
        self.assertIn("NB-10", [r["problem"] for r in after_second])
        self.assertIn("NB-11", [r["problem"] for r in after_second])

    def test_ledger_survive_preserves_byte_prefix_on_append(self):
        # Stronger append-only guarantee: the on-disk bytes after the first
        # write are a strict prefix of the bytes after the second write — i.e.
        # the second append only ever adds to the end, never rewrites.
        ledger.record_run("NB-20", units=["NB-20"], outcome="solved")
        path = ledger.ledger_path()
        bytes_after_first = path.read_bytes()

        ledger.record_run("NB-21", units=["NB-21"], outcome="solved")
        bytes_after_second = path.read_bytes()

        self.assertTrue(
            bytes_after_second.startswith(bytes_after_first),
            "second append must not rewrite bytes already on disk",
        )
        self.assertGreater(len(bytes_after_second), len(bytes_after_first))

    def test_ledger_is_jsonl_one_record_per_line(self):
        # The on-disk form is JSONL: each line is an independent JSON object.
        ledger.record_run("NB-30", units=["NB-30"], outcome="solved")
        ledger.record_run("NB-31", units=["NB-31"], outcome="solved")
        lines = [ln for ln in ledger.ledger_path().read_text(
            encoding="utf-8").splitlines() if ln.strip()]
        self.assertEqual(len(lines), 2)
        for ln in lines:
            obj = json.loads(ln)  # each line parses on its own
            self.assertEqual(obj["v"], "backlogd-ledger/v1")

    def test_ledger_read_skips_a_malformed_line_but_keeps_the_rest(self):
        # A partial/garbage line (the only corruption risk for append-only)
        # is skipped; the well-formed records around it still read back.
        ledger.record_run("NB-40", units=["NB-40"], outcome="solved")
        with ledger.ledger_path().open("a", encoding="utf-8") as fh:
            fh.write("{ this is not json\n")
        ledger.record_run("NB-41", units=["NB-41"], outcome="solved")
        problems = [r["problem"] for r in ledger.read_all()]
        self.assertEqual(problems, ["NB-40", "NB-41"])

    def test_ledger_record_run_never_raises_when_store_unwritable(self):
        # The headline best-effort contract: a write that cannot land (here the
        # parent path is an existing *file*, so mkdir/open fail) must be
        # swallowed, never raised — ledger persistence must never block the
        # scrum loop. record_run still returns the well-formed record it built.
        clash = pathlib.Path(self._tmp.name) / "a-file-not-a-dir"
        clash.write_text("x", encoding="utf-8")
        # Force the ledger file under a path whose parent is that file.
        os.environ["BACKLOGD_LEDGER_FILE"] = str(clash / "nested" / "ledger.jsonl")
        try:
            rec = ledger.record_run("NB-42", units=["NB-42"], outcome="solved")
        except Exception as exc:  # pragma: no cover - the whole point is no raise
            self.fail(f"record_run must swallow write failure, raised: {exc!r}")
        # It returned the record it built despite the write failing.
        self.assertEqual(rec["problem"], "NB-42")
        self.assertEqual(rec["v"], "backlogd-ledger/v1")


class LedgerLocationTest(_LedgerTempStoreMixin):
    """The store location + env-override resolution."""

    def test_ledger_default_path_is_under_backlogd(self):
        # With no override, the ledger lives at .backlogd/ledger.jsonl.
        os.environ.pop("BACKLOGD_LEDGER_DIR", None)
        os.environ.pop("BACKLOGD_LEDGER_FILE", None)
        p = ledger.ledger_path()
        self.assertEqual(p.name, "ledger.jsonl")
        self.assertEqual(p.parent.name, ".backlogd")

    def test_ledger_file_override_takes_precedence_over_dir(self):
        explicit = pathlib.Path(self._tmp.name) / "custom" / "my-ledger.jsonl"
        os.environ["BACKLOGD_LEDGER_FILE"] = str(explicit)
        self.assertEqual(ledger.ledger_path(), explicit)


class LedgerGitignoredTest(unittest.TestCase):
    """AC5: no ledger content is committed — the ledger path stays gitignored.

    The AC's headline command is ``git check-ignore .backlogd`` (exit 0). That
    holds in any tree where a run has created ``.backlogd/`` (the dir then
    exists on disk and git confirms the match). But ``git check-ignore`` is
    ambiguous on a *bare* directory name that doesn't exist on disk, so this
    test asserts the underlying, deterministic invariant: the actual ledger
    *file path* ``.backlogd/ledger.jsonl`` is ignored regardless of whether the
    directory exists yet — which is exactly what keeps recorded run content out
    of commits.
    """

    def _repo_root(self):
        import subprocess
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(pathlib.Path(__file__).resolve().parent),
            capture_output=True, text=True,
        )
        if out.returncode != 0 or not out.stdout.strip():
            self.skipTest("not in a git work tree")
        return out.stdout.strip()

    def test_ledger_jsonl_path_is_gitignored(self):
        import subprocess
        root = self._repo_root()
        # A file path under .backlogd/ matches the `.backlogd/` rule
        # unambiguously, even when the directory does not exist on disk.
        res = subprocess.run(
            ["git", "check-ignore", ".backlogd/ledger.jsonl"],
            cwd=root, capture_output=True, text=True,
        )
        self.assertEqual(
            res.returncode, 0,
            f"expected .backlogd/ledger.jsonl to be gitignored; "
            f"git check-ignore exited {res.returncode} (stdout={res.stdout!r})",
        )


class LedgerCliTest(_LedgerTempStoreMixin):
    """The record-run / read CLI subcommands wired into the scrum loop."""

    def test_ledger_cli_record_run_then_read(self):
        rc = ledger.main(["record-run", "--problem", "NB-50",
                          "--units", "NB-50", "NB-51",
                          "--pr", "https://example/pr/1",
                          "--outcome", "solved",
                          "--ts", "2026-06-03T05:00:00Z"])
        self.assertEqual(rc, 0)
        runs = ledger.read_runs("NB-50")
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["pr"], "https://example/pr/1")
        self.assertEqual(
            [u["identifier"] for u in runs[0]["units"]], ["NB-50", "NB-51"])

    def test_ledger_cli_read_problem_prints_json(self):
        ledger.record_run("NB-60", units=["NB-60"], outcome="solved")
        buf = io.StringIO()
        from contextlib import redirect_stdout
        with redirect_stdout(buf):
            rc = ledger.main(["read", "--problem", "NB-60"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["problem"], "NB-60")

    def test_ledger_cli_read_all_prints_whole_ledger(self):
        ledger.record_run("NB-70", units=["NB-70"], outcome="solved")
        ledger.record_run("NB-71", units=["NB-71"], outcome="solved")
        buf = io.StringIO()
        from contextlib import redirect_stdout
        with redirect_stdout(buf):
            rc = ledger.main(["read"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual([r["problem"] for r in payload], ["NB-70", "NB-71"])

    def test_ledger_cli_record_run_units_json(self):
        rc = ledger.main([
            "record-run", "--problem", "NB-80",
            "--units-json", '[{"identifier":"NB-80","outcome":"solved"}]',
            "--outcome", "solved",
        ])
        self.assertEqual(rc, 0)
        self.assertEqual(
            ledger.read_runs("NB-80")[0]["units"],
            [{"identifier": "NB-80", "outcome": "solved"}],
        )

    def test_ledger_cli_record_run_reads_units_from_stdin(self):
        with mock.patch("sys.stdin", io.StringIO("NB-90\nNB-91\n")):
            rc = ledger.main(["record-run", "--problem", "NB-90",
                              "--outcome", "solved", "--stdin"])
        self.assertEqual(rc, 0)
        units = ledger.read_runs("NB-90")[0]["units"]
        self.assertEqual([u["identifier"] for u in units], ["NB-90", "NB-91"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
