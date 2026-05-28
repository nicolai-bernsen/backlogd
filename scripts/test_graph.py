"""Unit tests for scripts/graph.py — standard library only (unittest).

Run from the repo root:  python scripts/test_graph.py
Each test redirects the store to a fresh temp dir via BACKLOGD_GRAPH_DIR, so no
.backlogd/ directory is created in the working tree.
"""

import contextlib
import io
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

# Make `import graph` work regardless of how this file is invoked.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import graph  # noqa: E402


class GraphCoreTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["BACKLOGD_GRAPH_DIR"] = str(pathlib.Path(self._tmp.name) / "graph")

    def tearDown(self):
        os.environ.pop("BACKLOGD_GRAPH_DIR", None)
        self._tmp.cleanup()

    def test_append_creates_file_and_reads_back(self):
        session = "users/nbe/nb-264-demo"
        graph.write_edges(session, [
            graph.solves_edge(session, "NB-264"),
            graph.touches_edge(session, "scripts/graph.py"),
        ])
        # The session file is created with a filesystem-safe (sanitised) name.
        files = list(graph.graph_dir().glob("*.json"))
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].name, "users__nbe__nb-264-demo.json")
        # Read-back returns both edges.
        edges = graph.read_graph()
        self.assertEqual(len(edges), 2)
        self.assertEqual({e["type"] for e in edges}, {"solves", "touches"})

    def test_dedup_on_src_tgt_type_session(self):
        session = "branch-x"
        graph.write_edges(session, [graph.solves_edge(session, "NB-1", ts="2026-01-01T00:00:00Z")])
        # Re-append the same logical edge with a newer timestamp — must collapse to one.
        graph.write_edges(session, [graph.solves_edge(session, "NB-1", ts="2026-02-02T00:00:00Z")])
        solves = [e for e in graph.read_graph() if e["type"] == "solves"]
        self.assertEqual(len(solves), 1)
        # The newer edge wins on a duplicate key.
        self.assertEqual(solves[0]["ts"], "2026-02-02T00:00:00Z")

    def test_append_accumulates_distinct_edges_in_one_session(self):
        session = "branch-y"
        graph.write_edges(session, [graph.touches_edge(session, "a.py")])
        graph.write_edges(session, [graph.touches_edge(session, "b.py")])
        touched = sorted(e["tgt"] for e in graph.read_graph() if e["type"] == "touches")
        self.assertEqual(touched, ["module:a.py", "module:b.py"])

    def test_missing_store_returns_empty(self):
        os.environ["BACKLOGD_GRAPH_DIR"] = str(pathlib.Path(self._tmp.name) / "never-created")
        self.assertEqual(graph.read_graph(), [])

    def test_node_id_conventions(self):
        self.assertEqual(graph.problem_node("NB-264"), "problem:linear:NB-264")
        self.assertEqual(graph.session_node("branch-x"), "session:branch-x")
        self.assertEqual(graph.module_node("a\\b.py"), "module:a/b.py")
        self.assertEqual(graph.node_id("problem", "linear", "NB-9"), "problem:linear:NB-9")

    def test_edges_persisted_as_valid_json_array(self):
        session = "s1"
        graph.write_edges(session, [graph.touches_edge(session, "f.py")])
        path = next(graph.graph_dir().glob("*.json"))
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertIsInstance(data, list)
        self.assertEqual(data[0]["v"], "backlogd/v1")
        self.assertEqual(data[0]["session"], session)


class GraphCliTest(unittest.TestCase):
    """The emit / prior-work CLI subcommands added for the scrum-master wiring (#266)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["BACKLOGD_GRAPH_DIR"] = str(pathlib.Path(self._tmp.name) / "graph")

    def tearDown(self):
        os.environ.pop("BACKLOGD_GRAPH_DIR", None)
        self._tmp.cleanup()

    def test_emit_cli_writes_solves_and_touches(self):
        rc = graph.main(["emit", "--session", "s1", "--problem", "NB-9",
                         "--files", "a.py", "b.py"])
        self.assertEqual(rc, 0)
        edges = graph.read_graph()
        self.assertEqual(sum(1 for e in edges if e["type"] == "solves"), 1)
        self.assertEqual(
            sorted(e["tgt"] for e in edges if e["type"] == "touches"),
            ["module:a.py", "module:b.py"],
        )

    def test_emit_cli_reads_files_from_stdin(self):
        with mock.patch("sys.stdin", io.StringIO("x.py\ny.py\n")):
            rc = graph.main(["emit", "--session", "s2", "--problem", "NB-7", "--stdin"])
        self.assertEqual(rc, 0)
        touched = sorted(e["tgt"] for e in graph.read_graph() if e["type"] == "touches")
        self.assertEqual(touched, ["module:x.py", "module:y.py"])

    def test_prior_work_empty_store_prints_nothing(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = graph.main(["prior-work", "--problem", "NB-1"])
        self.assertEqual(rc, 0)
        self.assertEqual(buf.getvalue().strip(), "")

    def test_prior_work_reports_history_and_neighbours(self):
        # NB-1's session touched shared.py + only1.py; NB-2's session touched shared.py.
        graph.write_edges("s-a", [graph.solves_edge("s-a", "NB-1"),
                                  graph.touches_edge("s-a", "shared.py"),
                                  graph.touches_edge("s-a", "only1.py")])
        graph.write_edges("s-b", [graph.solves_edge("s-b", "NB-2"),
                                  graph.touches_edge("s-b", "shared.py")])
        lines = graph.prior_work("NB-1")
        self.assertTrue(any("previously touched" in ln and "shared.py" in ln for ln in lines))
        self.assertTrue(any("NB-2" in ln for ln in lines))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            graph.main(["prior-work", "--problem", "NB-1"])
        out = buf.getvalue()
        self.assertIn("## Prior work", out)
        self.assertIn("NB-2", out)


class AgentExecutionEdgesTest(unittest.TestCase):
    """The new agent-execution edge types added for #320 (rework/partials/latency)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["BACKLOGD_GRAPH_DIR"] = str(pathlib.Path(self._tmp.name) / "graph")

    def tearDown(self):
        os.environ.pop("BACKLOGD_GRAPH_DIR", None)
        self._tmp.cleanup()

    def test_dispatch_started_edge_shape(self):
        e = graph.dispatch_started_edge("s1", "NB-9", ts="2026-05-01T10:00:00Z")
        self.assertEqual(e["type"], "dispatch_started")
        self.assertEqual(e["src"], "session:s1")
        self.assertEqual(e["tgt"], "problem:linear:NB-9")
        self.assertEqual(e["ts"], "2026-05-01T10:00:00Z")
        self.assertEqual(e["session"], "s1")
        self.assertEqual(e["v"], "backlogd/v1")

    def test_dispatch_completed_edge_carries_outcome_and_latency(self):
        e = graph.dispatch_completed_edge("s1", "NB-9", "solved",
                                          ts="2026-05-01T10:05:00Z",
                                          latency_ms=300_000)
        self.assertEqual(e["type"], "dispatch_completed")
        self.assertEqual(e["outcome"], "solved")
        self.assertEqual(e["latency_ms"], 300_000)

    def test_dispatch_end_cli_derives_latency_from_recorded_start(self):
        rc = graph.main(["dispatch-start", "--session", "s1", "--problem", "NB-9",
                         "--ts", "2026-05-01T10:00:00Z"])
        self.assertEqual(rc, 0)
        rc = graph.main(["dispatch-end", "--session", "s1", "--problem", "NB-9",
                         "--outcome", "solved", "--ts", "2026-05-01T10:05:00Z"])
        self.assertEqual(rc, 0)
        # The dispatch_completed edge should now carry a 5-minute latency.
        completed = [e for e in graph.read_graph()
                     if e["type"] == "dispatch_completed"]
        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0]["outcome"], "solved")
        self.assertEqual(completed[0]["latency_ms"], 5 * 60 * 1000)

    def test_pr_opened_and_run_end_cli(self):
        graph.main(["dispatch-start", "--session", "s1", "--problem", "NB-9",
                    "--ts", "2026-05-01T10:00:00Z"])
        graph.main(["dispatch-end", "--session", "s1", "--problem", "NB-9",
                    "--outcome", "solved", "--ts", "2026-05-01T10:05:00Z"])
        graph.main(["pr-opened", "--session", "s1", "--problem", "NB-9",
                    "--ts", "2026-05-01T10:06:00Z"])
        graph.main(["run-end", "--session", "s1", "--problem", "NB-9",
                    "--ts", "2026-05-01T10:07:00Z"])
        edges = graph.read_graph()
        types = {e["type"] for e in edges}
        self.assertEqual(types, {"dispatch_started", "dispatch_completed",
                                 "pr_opened", "run_completed"})
        run = [e for e in edges if e["type"] == "run_completed"][0]
        # wall time = 10:07 - 10:00 = 7 minutes
        self.assertEqual(run["wall_time_ms"], 7 * 60 * 1000)

    def test_rework_events_accumulate(self):
        rc = graph.main(["rework", "--session", "review-1", "--problem", "NB-9",
                         "--ts", "2026-05-01T11:00:00Z",
                         "--notes", "first send-back"])
        self.assertEqual(rc, 0)
        rc = graph.main(["rework", "--session", "review-1", "--problem", "NB-9",
                         "--ts", "2026-05-02T11:00:00Z",
                         "--notes", "second send-back"])
        self.assertEqual(rc, 0)
        rework = [e for e in graph.read_graph() if e["type"] == "rework"]
        self.assertEqual(len(rework), 2)
        # The notes themselves are NOT stored — only their hash prefix.
        for r in rework:
            self.assertNotIn("notes", r)
            self.assertIn("notes_hash", r)
            self.assertEqual(len(r["notes_hash"]), 12)

    def test_labeled_edge_attaches_labels(self):
        rc = graph.main(["labeled", "--session", "s1", "--problem", "NB-9",
                         "--labels", "area:graph", "problem"])
        self.assertEqual(rc, 0)
        labeled = [e for e in graph.read_graph() if e["type"] == "labeled"][0]
        self.assertEqual(labeled["labels"], ["area:graph", "problem"])

    def test_prior_work_treats_dispatch_completed_as_solve_evidence(self):
        # No legacy `solves` edge — the new flow only emits dispatch_completed.
        graph.write_edges("s-new", [
            graph.dispatch_completed_edge("s-new", "NB-9", "solved"),
            graph.touches_edge("s-new", "scripts/graph.py"),
        ])
        # prior_work for NB-9 should still surface the touched file.
        lines = graph.prior_work("NB-9")
        self.assertTrue(any("scripts/graph.py" in ln for ln in lines),
                        f"expected NB-9's touched file to surface; got {lines}")


class MetricsTest(unittest.TestCase):
    """The metrics() aggregator and the `report` CLI subcommand (#320)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["BACKLOGD_GRAPH_DIR"] = str(pathlib.Path(self._tmp.name) / "graph")

    def tearDown(self):
        os.environ.pop("BACKLOGD_GRAPH_DIR", None)
        self._tmp.cleanup()

    def test_metrics_on_empty_store(self):
        m = graph.metrics()
        self.assertEqual(m["problems"], 0)
        self.assertEqual(m["dispatches"]["total"], 0)
        self.assertIsNone(m["dispatches"]["partial_rate"])
        self.assertIsNone(m["dispatch_to_pr_ms"]["p50"])
        self.assertEqual(m["by_area"], {})
        self.assertIsNotNone(m["by_area_note"])

    def test_metrics_computes_rates_and_latencies(self):
        # Two problems, with different outcomes / one rework.
        # NB-1: dispatched, solved, PR opened, run completed; later sent back (rework).
        graph.main(["dispatch-start", "--session", "s1", "--problem", "NB-1",
                    "--ts", "2026-05-01T10:00:00Z"])
        graph.main(["dispatch-end", "--session", "s1", "--problem", "NB-1",
                    "--outcome", "solved", "--ts", "2026-05-01T10:10:00Z"])
        graph.main(["pr-opened", "--session", "s1", "--problem", "NB-1",
                    "--ts", "2026-05-01T10:15:00Z"])
        graph.main(["run-end", "--session", "s1", "--problem", "NB-1",
                    "--ts", "2026-05-01T10:16:00Z"])
        graph.main(["rework", "--session", "rev-1", "--problem", "NB-1",
                    "--ts", "2026-05-02T09:00:00Z", "--notes", "x"])
        # NB-2: dispatched, blocked.
        graph.main(["dispatch-start", "--session", "s2", "--problem", "NB-2",
                    "--ts", "2026-05-01T11:00:00Z"])
        graph.main(["dispatch-end", "--session", "s2", "--problem", "NB-2",
                    "--outcome", "blocked", "--ts", "2026-05-01T11:02:00Z"])

        m = graph.metrics()
        self.assertEqual(m["dispatches"]["total"], 2)
        self.assertEqual(m["dispatches"]["solved"], 1)
        self.assertEqual(m["dispatches"]["blocked"], 1)
        self.assertEqual(m["dispatches"]["partial"], 0)
        self.assertAlmostEqual(m["dispatches"]["blocked_rate"], 0.5)
        # NB-1 dispatch_to_pr = 15 minutes.
        self.assertEqual(m["dispatch_to_pr_ms"]["n"], 1)
        self.assertEqual(m["dispatch_to_pr_ms"]["p50"], 15 * 60 * 1000)
        # Rework: 1 problem has rework out of {NB-1, NB-2}.
        self.assertEqual(m["rework"]["events"], 1)
        self.assertEqual(m["rework"]["problems_with_rework"], 1)
        self.assertAlmostEqual(m["rework"]["rate"], 0.5)

    def test_metrics_by_area_uses_labeled_edges(self):
        # NB-1 in area:graph, blocked. NB-2 in area:docs, solved.
        graph.main(["labeled", "--session", "s1", "--problem", "NB-1",
                    "--labels", "area:graph"])
        graph.main(["dispatch-end", "--session", "s1", "--problem", "NB-1",
                    "--outcome", "blocked", "--ts", "2026-05-01T10:00:00Z"])
        graph.main(["labeled", "--session", "s2", "--problem", "NB-2",
                    "--labels", "area:docs"])
        graph.main(["dispatch-end", "--session", "s2", "--problem", "NB-2",
                    "--outcome", "solved", "--ts", "2026-05-01T11:00:00Z"])

        m = graph.metrics()
        self.assertIn("area:graph", m["by_area"])
        self.assertEqual(m["by_area"]["area:graph"]["blocked"], 1)
        self.assertEqual(m["by_area"]["area:docs"]["blocked"], 0)
        # When labels exist the explanatory note disappears.
        self.assertIsNone(m["by_area_note"])

    def test_report_cli_prints_markdown_table(self):
        graph.main(["dispatch-end", "--session", "s1", "--problem", "NB-1",
                    "--outcome", "solved", "--ts", "2026-05-01T10:00:00Z"])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = graph.main(["report"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("# backlogd — agent-execution metrics", out)
        self.assertIn("Rework rate", out)
        self.assertIn("Partial rate", out)
        self.assertIn("Blocked rate", out)
        self.assertIn("Dispatch→PR latency p50", out)

    def test_report_cli_json_mode(self):
        graph.main(["dispatch-end", "--session", "s1", "--problem", "NB-1",
                    "--outcome", "partial", "--ts", "2026-05-01T10:00:00Z"])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            graph.main(["report", "--json"])
        m = json.loads(buf.getvalue())
        self.assertEqual(m["dispatches"]["partial"], 1)

    def test_run_end_records_fanout(self):
        # The parallel-walk metadata added in #321: --fanout on run-end is
        # stored on the run_completed edge as a passthrough field.
        graph.main(["run-end", "--session", "s1", "--problem", "NB-1",
                    "--ts", "2026-05-01T10:00:00Z", "--fanout", "3"])
        run = [e for e in graph.read_graph()
               if e["type"] == "run_completed"][0]
        self.assertEqual(run["fanout"], 3)

    def test_run_end_without_fanout_is_backward_compatible(self):
        # An old caller (no --fanout) writes the edge without the field;
        # the metrics aggregate handles its absence cleanly.
        graph.main(["run-end", "--session", "s1", "--problem", "NB-1",
                    "--ts", "2026-05-01T10:00:00Z"])
        run = [e for e in graph.read_graph()
               if e["type"] == "run_completed"][0]
        self.assertNotIn("fanout", run)
        m = graph.metrics()
        # No fanout-bearing edges -> aggregate reports n=0, max=None.
        self.assertEqual(m["fanout"]["n"], 0)
        self.assertIsNone(m["fanout"]["max"])
        self.assertEqual(m["fanout"]["parallel_runs"], 0)

    def test_metrics_aggregates_fanout(self):
        # Three runs: 2 sequential (fanout=1), 1 parallel (fanout=3).
        graph.main(["run-end", "--session", "s1", "--problem", "NB-1",
                    "--ts", "2026-05-01T10:00:00Z", "--fanout", "1"])
        graph.main(["run-end", "--session", "s2", "--problem", "NB-2",
                    "--ts", "2026-05-02T10:00:00Z", "--fanout", "1"])
        graph.main(["run-end", "--session", "s3", "--problem", "NB-3",
                    "--ts", "2026-05-03T10:00:00Z", "--fanout", "3"])
        m = graph.metrics()
        self.assertEqual(m["fanout"]["n"], 3)
        self.assertEqual(m["fanout"]["max"], 3)
        self.assertEqual(m["fanout"]["parallel_runs"], 1)
        self.assertAlmostEqual(m["fanout"]["parallel_rate"], 1/3)


class RunStatusTest(unittest.TestCase):
    """`run_status` + `run-status` CLI for /backlogd:solve's resume reconcile (#322)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["BACKLOGD_GRAPH_DIR"] = str(pathlib.Path(self._tmp.name) / "graph")

    def tearDown(self):
        os.environ.pop("BACKLOGD_GRAPH_DIR", None)
        self._tmp.cleanup()

    def test_run_status_empty_store_reports_untouched(self):
        st = graph.run_status("NB-322")
        self.assertEqual(st["problem"], "NB-322")
        self.assertEqual(st["units"]["NB-322"]["state"], "untouched")
        self.assertEqual(st["units"]["NB-322"]["sessions"], [])
        self.assertIsNone(st["units"]["NB-322"]["outcome"])

    def test_run_status_marks_completed_when_dispatch_completed_exists(self):
        graph.write_edges("s1", [
            graph.dispatch_started_edge("s1", "NB-322", ts="2026-05-01T10:00:00Z"),
            graph.dispatch_completed_edge("s1", "NB-322", "solved",
                                          ts="2026-05-01T10:05:00Z",
                                          latency_ms=300_000),
        ])
        st = graph.run_status("NB-322")
        unit = st["units"]["NB-322"]
        self.assertEqual(unit["state"], "completed")
        self.assertEqual(unit["outcome"], "solved")
        self.assertEqual(unit["sessions"], ["s1"])
        self.assertEqual(unit["last_completed"], "2026-05-01T10:05:00Z")
        self.assertEqual(unit["last_started"], "2026-05-01T10:00:00Z")

    def test_run_status_marks_in_progress_when_start_has_no_completion(self):
        # A crashed mid-walk: dispatch_started recorded, dispatch_completed never landed.
        graph.write_edges("s1", [
            graph.dispatch_started_edge("s1", "NB-322", ts="2026-05-01T10:00:00Z"),
        ])
        st = graph.run_status("NB-322")
        unit = st["units"]["NB-322"]
        self.assertEqual(unit["state"], "in-progress")
        self.assertIsNone(unit["outcome"])
        self.assertEqual(unit["sessions"], ["s1"])
        self.assertEqual(unit["last_started"], "2026-05-01T10:00:00Z")
        self.assertIsNone(unit["last_completed"])

    def test_run_status_collects_sessions_across_runs(self):
        # Two sessions both attempted the unit; one crashed (no completion),
        # the other later finished it. Both sessions should be listed; the
        # state collapses to `completed` because a completion edge exists.
        graph.write_edges("s-crashed", [
            graph.dispatch_started_edge("s-crashed", "NB-322",
                                        ts="2026-05-01T09:00:00Z"),
        ])
        graph.write_edges("s-rerun", [
            graph.dispatch_started_edge("s-rerun", "NB-322",
                                        ts="2026-05-01T10:00:00Z"),
            graph.dispatch_completed_edge("s-rerun", "NB-322", "solved",
                                          ts="2026-05-01T10:05:00Z"),
        ])
        st = graph.run_status("NB-322")
        unit = st["units"]["NB-322"]
        self.assertEqual(unit["state"], "completed")
        self.assertEqual(sorted(unit["sessions"]), ["s-crashed", "s-rerun"])

    def test_run_status_picks_latest_outcome_when_multiple_completions(self):
        # A unit re-dispatched after a partial: the more recent outcome wins.
        graph.write_edges("s1", [
            graph.dispatch_completed_edge("s1", "NB-322", "partial",
                                          ts="2026-05-01T10:00:00Z"),
        ])
        graph.write_edges("s2", [
            graph.dispatch_completed_edge("s2", "NB-322", "solved",
                                          ts="2026-05-02T10:00:00Z"),
        ])
        st = graph.run_status("NB-322")
        unit = st["units"]["NB-322"]
        self.assertEqual(unit["state"], "completed")
        self.assertEqual(unit["outcome"], "solved")
        self.assertEqual(unit["last_completed"], "2026-05-02T10:00:00Z")

    def test_run_status_treats_legacy_solves_as_untouched(self):
        # Legacy `solves` edges have no started/completed semantics — the
        # resume flow only fires on the new edge types, so a unit known only
        # via `solves` is reported as `untouched` and the orchestrator falls
        # back to Linear state.
        graph.write_edges("legacy", [graph.solves_edge("legacy", "NB-322")])
        st = graph.run_status("NB-322")
        self.assertEqual(st["units"]["NB-322"]["state"], "untouched")

    def test_run_status_cli_prints_json_to_stdout(self):
        graph.write_edges("s1", [
            graph.dispatch_completed_edge("s1", "NB-322", "solved",
                                          ts="2026-05-01T10:00:00Z"),
        ])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = graph.main(["run-status", "--problem", "NB-322"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["problem"], "NB-322")
        self.assertEqual(payload["units"]["NB-322"]["state"], "completed")
        self.assertEqual(payload["units"]["NB-322"]["outcome"], "solved")


class BackwardCompatTest(unittest.TestCase):
    """Existing on-disk graphs must keep parsing, and existing CLI shape stays."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["BACKLOGD_GRAPH_DIR"] = str(pathlib.Path(self._tmp.name) / "graph")

    def tearDown(self):
        os.environ.pop("BACKLOGD_GRAPH_DIR", None)
        self._tmp.cleanup()

    def test_legacy_solves_and_touches_still_round_trip(self):
        # Simulate an on-disk graph from before #320.
        graph.emit("legacy-session", "NB-9", ["a.py", "b.py"])
        edges = graph.read_graph()
        types = sorted({e["type"] for e in edges})
        self.assertEqual(types, ["solves", "touches"])

    def test_make_edge_drops_none_extras(self):
        e = graph.make_edge("s", "p", "dispatch_completed", "sess",
                            outcome="solved", latency_ms=None)
        self.assertIn("outcome", e)
        self.assertNotIn("latency_ms", e)

    def test_make_edge_extras_never_override_base_fields(self):
        # extras must not overwrite v/src/tgt/type/ts/session.
        e = graph.make_edge("s", "p", "dispatch_started", "sess",
                            ts="2026-05-01T00:00:00Z",
                            type="malicious", v="evil/v0")
        self.assertEqual(e["type"], "dispatch_started")
        self.assertEqual(e["v"], "backlogd/v1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
