"""Unit tests for scripts/witness.py — standard library only (unittest).

Run from the repo root:  python scripts/test_witness.py
(or collected by `python3 -m unittest discover -s scripts -p 'test_*.py'`).

``witness.run`` is parameterised on ``manifest_path`` / ``repo_root`` / ``out`` so
every case here builds a throwaway manifest + marker tree under ``tempfile`` —
the real ``solved-problems.json`` and the real repo files are never mutated. The
four behaviours the AC pins down each get their own test:

* present marker            → checker returns 0
* missing marker (snippet absent from an existing file) → non-zero
* missing marker file       → non-zero
* malformed entry (a required field absent) → non-zero

``WitnessRealManifestTest`` is a smoke check that the committed manifest actually
passes against the live tree — it is what makes the three seeded markers a
durable, self-verifying guarantee rather than just data.
"""

import io
import json
import pathlib
import sys
import tempfile
import unittest

# Make ``import witness`` work regardless of how this file is invoked.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import witness  # noqa: E402


def _entry(**overrides):
    """A complete, valid manifest entry; override individual fields per test."""
    base = {
        "id": "NB-001",
        "title": "Example fix",
        "marker_file": "marker.txt",
        "marker_snippet": "the load-bearing string",
        "shipped_in": "dev",
        "shipped_at": "2026-05-29",
    }
    base.update(overrides)
    return base


class WitnessFixtureTest(unittest.TestCase):
    """Drive witness.run against a tmp manifest + marker tree per case."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def _write_manifest(self, entries):
        path = self.root / "solved-problems.json"
        path.write_text(json.dumps(entries), encoding="utf-8")
        return path

    def _write_marker_file(self, name, contents):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
        return path

    def _run(self, manifest_path):
        """Run the checker against the tmp root; return (exit_code, output)."""
        out = io.StringIO()
        code = witness.run(manifest_path=manifest_path, repo_root=self.root, out=out)
        return code, out.getvalue()

    # --- present marker → 0 ----------------------------------------------------------
    def test_present_marker_returns_zero(self):
        self._write_marker_file("marker.txt", "prefix the load-bearing string suffix\n")
        manifest = self._write_manifest([_entry()])
        code, output = self._run(manifest)
        self.assertEqual(code, 0, f"present marker must exit 0; output:\n{output}")
        self.assertIn("OK NB-001 marker.txt", output)

    def test_multiple_present_markers_return_zero(self):
        self._write_marker_file("a.txt", "has alpha here\n")
        self._write_marker_file("sub/b.txt", "has beta here\n")
        manifest = self._write_manifest(
            [
                _entry(id="NB-A", marker_file="a.txt", marker_snippet="alpha"),
                _entry(id="NB-B", marker_file="sub/b.txt", marker_snippet="beta"),
            ]
        )
        code, output = self._run(manifest)
        self.assertEqual(code, 0, f"all present must exit 0; output:\n{output}")
        self.assertIn("OK NB-A a.txt", output)
        self.assertIn("OK NB-B sub/b.txt", output)

    # --- missing marker (snippet absent) → non-zero ----------------------------------
    def test_missing_marker_snippet_returns_nonzero(self):
        # The file exists but no longer contains the snippet — a silent regression.
        self._write_marker_file("marker.txt", "this file lost the marker line\n")
        manifest = self._write_manifest([_entry()])
        code, output = self._run(manifest)
        self.assertNotEqual(code, 0, f"missing snippet must exit non-zero; output:\n{output}")
        self.assertIn("MISS NB-001 marker.txt", output)

    def test_one_miss_among_hits_still_returns_nonzero(self):
        self._write_marker_file("ok.txt", "alpha present\n")
        self._write_marker_file("bad.txt", "the snippet is gone\n")
        manifest = self._write_manifest(
            [
                _entry(id="NB-OK", marker_file="ok.txt", marker_snippet="alpha"),
                _entry(id="NB-BAD", marker_file="bad.txt", marker_snippet="beta"),
            ]
        )
        code, output = self._run(manifest)
        self.assertNotEqual(code, 0, f"any miss must exit non-zero; output:\n{output}")
        self.assertIn("OK NB-OK ok.txt", output)
        self.assertIn("MISS NB-BAD bad.txt", output)

    # --- missing marker file → non-zero ----------------------------------------------
    def test_missing_marker_file_returns_nonzero(self):
        # No file written at all → unreadable → must red.
        manifest = self._write_manifest([_entry(marker_file="does-not-exist.txt")])
        code, output = self._run(manifest)
        self.assertNotEqual(code, 0, f"missing file must exit non-zero; output:\n{output}")
        self.assertIn("MISS NB-001", output)
        self.assertIn("does-not-exist.txt", output)

    # --- malformed entry (missing field) → non-zero ----------------------------------
    def test_malformed_entry_missing_field_returns_nonzero(self):
        # A present marker file, but the entry drops a required field.
        self._write_marker_file("marker.txt", "the load-bearing string\n")
        entry = _entry()
        del entry["marker_snippet"]
        manifest = self._write_manifest([entry])
        code, output = self._run(manifest)
        self.assertNotEqual(code, 0, f"malformed entry must exit non-zero; output:\n{output}")
        self.assertIn("MISS", output)
        self.assertIn("marker_snippet", output)

    def test_empty_field_value_is_malformed_returns_nonzero(self):
        # An empty string is as malformed as an absent field — the AC wants all
        # six fields non-empty.
        self._write_marker_file("marker.txt", "the load-bearing string\n")
        manifest = self._write_manifest([_entry(shipped_in="")])
        code, output = self._run(manifest)
        self.assertNotEqual(code, 0, f"empty field must exit non-zero; output:\n{output}")
        self.assertIn("shipped_in", output)

    def test_entry_not_an_object_returns_nonzero(self):
        manifest = self._write_manifest(["not-an-object"])
        code, output = self._run(manifest)
        self.assertNotEqual(code, 0, f"non-object entry must exit non-zero; output:\n{output}")
        self.assertIn("MISS", output)

    # --- manifest-shape failures -----------------------------------------------------
    def test_missing_manifest_returns_nonzero(self):
        code, output = self._run(self.root / "no-such-manifest.json")
        self.assertNotEqual(code, 0, f"missing manifest must exit non-zero; output:\n{output}")
        self.assertIn("FAIL", output)

    def test_non_array_manifest_returns_nonzero(self):
        path = self.root / "solved-problems.json"
        path.write_text(json.dumps({"id": "NB-001"}), encoding="utf-8")
        code, output = self._run(path)
        self.assertNotEqual(code, 0, f"non-array manifest must exit non-zero; output:\n{output}")
        self.assertIn("FAIL", output)

    def test_empty_array_manifest_returns_nonzero(self):
        manifest = self._write_manifest([])
        code, output = self._run(manifest)
        self.assertNotEqual(code, 0, f"empty manifest must exit non-zero; output:\n{output}")
        self.assertIn("FAIL", output)

    def test_unparseable_manifest_returns_nonzero(self):
        path = self.root / "solved-problems.json"
        path.write_text("{not valid json", encoding="utf-8")
        code, output = self._run(path)
        self.assertNotEqual(code, 0, f"unparseable manifest must exit non-zero; output:\n{output}")
        self.assertIn("FAIL", output)


class WitnessRealManifestTest(unittest.TestCase):
    """The committed manifest must pass against the live repo tree.

    This is the durable guarantee: if a seeded marker is ever transcribed wrong
    or a shipped fix regresses, this test (and the CI step) go red.
    """

    def test_real_manifest_passes(self):
        out = io.StringIO()
        code = witness.run(out=out)  # defaults: real manifest, real repo root
        self.assertEqual(
            code,
            0,
            "the committed solved-problems.json must pass against the live tree; "
            f"output:\n{out.getvalue()}",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
