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


if __name__ == "__main__":
    unittest.main(verbosity=2)
