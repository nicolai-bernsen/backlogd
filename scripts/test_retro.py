"""Tests for NB-381 — Milestone/cycle retrospective (`/backlogd:retro`).

Standard library only (unittest). Run from the repo root:

    python scripts/test_retro.py
    (or collected by `python3 -m unittest discover -s scripts -p 'test_*.py'`).

This unit ships `/backlogd:retro` as command+skill prose plus two CI-checkable doc
flips. Only **two** of its acceptance criteria name a behaviour a test runner can
assert; this file proves exactly those two, one test-class per AC so the evidence
maps 1:1 to the unit's `## Acceptance Criteria`:

* **[test] "The graph evidence surface is actually consumable."** —
  ``python scripts/graph.py report --json`` exits 0 and emits the five documented
  top-level keys the retro reads (``dispatches`` / ``rework`` / ``dispatch_to_pr_ms``
  / ``run_wall_time_ms`` / ``by_area``), AND degrades cleanly on an empty/sparse
  store (the five keys still appear with n=0 / None rather than the reducer raising).
  Covered by ``GraphEvidenceSurfaceConsumableTest``.

* **[test] "The Scrum mapping stops calling the Retrospective out of scope."** —
  the literal string ``"Out of scope today"`` no longer appears in either
  ``docs/scrum/mapping.md`` or ``skills/scrum/references/events.md``.
  Covered by ``ScrumMappingNotOutOfScopeTest``.

The remaining ACs ([manual] Trigger, [manual] Dogfood, and the four [review] design
properties) are not assertable in code — see this unit's tester report for why.

The graph cases redirect the store to a fresh temp dir via ``BACKLOGD_GRAPH_DIR`` so
no ``.backlogd/`` directory is created in the working tree, and so the empty-store
case is genuinely empty regardless of what the developer's machine has accumulated.
"""

import contextlib
import io
import json
import os
import pathlib
import sys
import tempfile
import unittest

# Make `import graph` work regardless of how this file is invoked (mirrors
# scripts/test_graph.py — the discover runner sets cwd to the repo root, not scripts/).
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import graph  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
MAPPING_PATH = REPO_ROOT / "docs" / "scrum" / "mapping.md"
EVENTS_PATH = REPO_ROOT / "skills" / "scrum" / "references" / "events.md"

# The five top-level keys the retro's read step consumes off `report --json`.
# Named verbatim in the AC; the retro contract breaks the moment one disappears.
REQUIRED_KEYS = ("dispatches", "rework", "dispatch_to_pr_ms", "run_wall_time_ms", "by_area")


class GraphEvidenceSurfaceConsumableTest(unittest.TestCase):
    """[test] "The graph evidence surface is actually consumable."

    `python scripts/graph.py report --json` exits 0 and emits the documented
    top-level keys the retro reads — degrading cleanly on an empty/sparse store
    rather than raising. Each half of the AC ("exits 0 + keys present" and
    "degrades cleanly on empty/sparse") gets its own assertion.
    """

    def setUp(self):
        # Redirect the graph store to a fresh temp dir so we control sparseness
        # and never touch the real .backlogd/ in the working tree.
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["BACKLOGD_GRAPH_DIR"] = str(pathlib.Path(self._tmp.name) / "graph")

    def tearDown(self):
        os.environ.pop("BACKLOGD_GRAPH_DIR", None)
        self._tmp.cleanup()

    def _report_json(self):
        """Run the `report --json` CLI; return (exit_code, parsed_dict)."""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = graph.main(["report", "--json"])
        payload = json.loads(buf.getvalue())
        return rc, payload

    def test_report_json_exits_zero_on_empty_store(self):
        # An empty/sparse store is the realistic case for an early milestone's
        # first retro — the surface must still exit 0, not raise.
        rc, _payload = self._report_json()
        self.assertEqual(rc, 0, "graph.py report --json must exit 0 on an empty store")

    def test_report_json_emits_all_five_documented_keys_on_empty_store(self):
        # The AC names the five keys the retro reads verbatim; assert each is a
        # top-level key of the JSON the retro parses.
        _rc, payload = self._report_json()
        for key in REQUIRED_KEYS:
            self.assertIn(
                key, payload,
                f"report --json must emit the documented top-level key '{key}'",
            )

    def test_report_json_degrades_cleanly_on_empty_store(self):
        # "Degrading cleanly" = the keys are present with n=0 / None / empty
        # rather than the reducer raising or omitting them on a sparse store.
        _rc, payload = self._report_json()
        self.assertEqual(payload["dispatches"]["total"], 0)
        self.assertEqual(payload["rework"]["events"], 0)
        self.assertEqual(payload["dispatch_to_pr_ms"]["n"], 0)
        self.assertIsNone(payload["dispatch_to_pr_ms"]["p50"])
        self.assertEqual(payload["run_wall_time_ms"]["n"], 0)
        self.assertIsNone(payload["run_wall_time_ms"]["p50"])
        self.assertEqual(payload["by_area"], {})

    def test_metrics_on_empty_edge_list_does_not_raise_and_carries_keys(self):
        # The reducer function the CLI sits on must not raise when handed an
        # explicitly empty edge list (the in-process call the retro prose can
        # also reach), and must still expose the five keys with n=0.
        m = graph.metrics([])
        for key in REQUIRED_KEYS:
            self.assertIn(key, m, f"metrics([]) must carry the key '{key}'")
        self.assertEqual(m["dispatches"]["total"], 0)
        self.assertEqual(m["run_wall_time_ms"]["n"], 0)

    def test_report_json_still_consumable_on_a_sparse_store(self):
        # A single dispatch edge (one problem, no PR/run/rework) is the sparse —
        # not empty — case: the five keys must still be present and the latency
        # percentiles still degrade to None where there is no data.
        graph.main(["dispatch-end", "--session", "s1", "--problem", "NB-1",
                    "--outcome", "solved", "--ts", "2026-05-01T10:00:00Z"])
        rc, payload = self._report_json()
        self.assertEqual(rc, 0)
        for key in REQUIRED_KEYS:
            self.assertIn(key, payload, f"sparse store must still emit '{key}'")
        self.assertEqual(payload["dispatches"]["total"], 1)
        self.assertEqual(payload["dispatches"]["solved"], 1)
        # No pr_opened / run_completed edges → latency surfaces stay n=0 / None,
        # not a divide-by-zero or a missing key.
        self.assertEqual(payload["dispatch_to_pr_ms"]["n"], 0)
        self.assertIsNone(payload["run_wall_time_ms"]["p50"])


class ScrumMappingNotOutOfScopeTest(unittest.TestCase):
    """[test] "The Scrum mapping stops calling the Retrospective out of scope."

    Neither `docs/scrum/mapping.md` nor `skills/scrum/references/events.md`
    describes the Sprint Retrospective as "Out of scope today" once this lands.
    A prose-grep regression test, mirroring the AC's stated verification
    (`grep -rn "Out of scope today" <the two files>` → no match).
    """

    def test_both_gated_files_exist(self):
        # A vacuous pass guard: the absence assertion below would false-green if
        # a file were renamed/deleted, so pin existence first.
        self.assertTrue(MAPPING_PATH.is_file(), f"expected {MAPPING_PATH} to exist")
        self.assertTrue(EVENTS_PATH.is_file(), f"expected {EVENTS_PATH} to exist")

    def test_mapping_md_does_not_call_retro_out_of_scope(self):
        body = MAPPING_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            "Out of scope today", body,
            "docs/scrum/mapping.md must not describe the Retrospective as "
            "'Out of scope today' — the row must reflect the shipped /backlogd:retro",
        )

    def test_events_md_does_not_call_retro_out_of_scope(self):
        body = EVENTS_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            "Out of scope today", body,
            "skills/scrum/references/events.md must not describe the Retrospective "
            "as 'Out of scope today' — the row must reflect the shipped /backlogd:retro",
        )

    def test_retrospective_row_now_points_at_retro_command(self):
        # Beyond the absence: confirm the rows were positively flipped to the
        # shipped mechanism, so the absence isn't from the Retrospective row
        # simply being deleted. Both files must now reference `/backlogd:retro`.
        for path in (MAPPING_PATH, EVENTS_PATH):
            body = path.read_text(encoding="utf-8")
            self.assertIn(
                "/backlogd:retro", body,
                f"{path.name} must reference the shipped /backlogd:retro command",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
