"""Tests for scripts/standards_index.py — standard library only (unittest).

The headline test is the **sync checker** (``IndexDriftTest``): it rebuilds the
standards index from the live corpus under ``docs/standards/adrs/`` and asserts the
committed ``docs/standards/index.json`` matches byte-for-byte. That fails the moment an
ADR is added or edited without regenerating the index — the regenerate-from-corpus vs
committed mismatch the AC asks for (the same idea as scripts/test_graph.py guarding graph.py).

Run from the repo root:
    python -m pytest scripts/test_standards_index.py
    python -m unittest discover -s scripts -p 'test_*.py'    # CI uses this

The synthetic-corpus tests write tiny ADR fixtures into a temp dir and point the
generator at it via ``--adrs-dir`` / the ``*_dir`` kwargs, so they never touch the real
corpus or the committed index.
"""

import contextlib
import io
import pathlib
import sys
import tempfile
import unittest

# Make `import standards_index` work regardless of how this file is invoked.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import standards_index as si  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


# --- a valid synthetic ADR fixture -----------------------------------------

VALID_ADR = """\
---
id: ADR-900
title: A test decision
status: Accepted
date: 2026-05-29
problem: NB-900
supersedes: ~
superseded-by: ~
assertion: A crisp checkable rule that holds for the test.
applies-to:
  domains: [docs, runtime]
  file-patterns: ["scripts/**", "docs/**"]
  decision-types: [dependency]
---

# ADR-900 — A test decision

Body prose that the index must ignore.
"""


def _write(dir_path: pathlib.Path, name: str, body: str) -> pathlib.Path:
    p = dir_path / name
    p.write_text(body, encoding="utf-8")
    return p


class FrontMatterReaderTest(unittest.TestCase):
    """The zero-dependency front-matter reader: the fixed YAML subset it must handle."""

    def test_split_front_matter_returns_body_between_fences(self):
        block = si.split_front_matter("---\nid: X\ntitle: Y\n---\nbody\n")
        self.assertEqual(block, "id: X\ntitle: Y")

    def test_split_front_matter_requires_opening_fence(self):
        with self.assertRaises(si.FrontMatterError):
            si.split_front_matter("id: X\n---\n")

    def test_split_front_matter_requires_closing_fence(self):
        with self.assertRaises(si.FrontMatterError):
            si.split_front_matter("---\nid: X\nno closing fence\n")

    def test_parse_scalar_inline_list_and_null(self):
        fm = si.parse_front_matter(
            "id: ADR-1\n"
            "title: Some title\n"
            "supersedes: ~\n"
            "tags: [a, b, c]\n"
        )
        self.assertEqual(fm["id"], "ADR-1")
        self.assertEqual(fm["title"], "Some title")
        self.assertIsNone(fm["supersedes"])
        self.assertEqual(fm["tags"], ["a", "b", "c"])

    def test_parse_nested_applies_to_mapping(self):
        fm = si.parse_front_matter(
            "id: ADR-1\n"
            "applies-to:\n"
            "  domains: [auth, runtime]\n"
            "  file-patterns: [\"**\"]\n"
            "  decision-types: [dependency, hosting]\n"
        )
        self.assertEqual(fm["applies-to"], {
            "domains": ["auth", "runtime"],
            "file-patterns": ["**"],
            "decision-types": ["dependency", "hosting"],
        })

    def test_parse_empty_inline_list(self):
        fm = si.parse_front_matter("applies-to:\n  domains: []\n")
        self.assertEqual(fm["applies-to"]["domains"], [])

    def test_parse_strips_inline_comment_outside_quotes(self):
        fm = si.parse_front_matter("supersedes: ~        # none here\n")
        self.assertIsNone(fm["supersedes"])

    def test_parse_keeps_hash_inside_value_text(self):
        # A '#' that is part of the value (not a comment) must survive.
        fm = si.parse_front_matter("note: refers to NB-377 see #377 detail\n")
        self.assertEqual(fm["note"], "refers to NB-377 see #377 detail")

    def test_parse_keeps_special_chars_in_assertion(self):
        # Real assertions carry parens, semicolons, slashes, em dashes.
        text = ("assertion: No new runtime dep (lib) without an ADR; "
                "reached via gh/MCP only — keyless.\n")
        fm = si.parse_front_matter(text)
        self.assertIn("keyless", fm["assertion"])
        self.assertIn(";", fm["assertion"])


class ValidationTest(unittest.TestCase):
    """`validate` / `--check`: required keys + applies-to shape, on synthetic corpora."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.adrs = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_valid_adr_passes(self):
        _write(self.adrs, "ADR-900-test.md", VALID_ADR)
        self.assertEqual(si.validate(self.adrs), [])

    def test_missing_required_key_is_reported(self):
        # Drop the `assertion` key.
        broken = VALID_ADR.replace(
            "assertion: A crisp checkable rule that holds for the test.\n", "")
        _write(self.adrs, "ADR-901-broken.md", broken)
        errors = si.validate(self.adrs)
        self.assertTrue(any("assertion" in e for e in errors), errors)

    def test_each_required_key_missing_is_reported(self):
        # AC: `--check` exits non-zero if ANY required front-matter key is
        # missing — not just `assertion`. Drop each scalar required key in turn
        # and assert it is named in the errors. (`applies-to` is a block, covered
        # by test_missing_applies_to_block_is_reported below.)
        import re
        scalar_keys = [k for k in si.REQUIRED_KEYS if k != "applies-to"]
        # Guard: this list should track REQUIRED_KEYS so a future addition is covered.
        self.assertEqual(set(scalar_keys),
                         {"id", "title", "status", "date", "assertion"})
        for key in scalar_keys:
            with self.subTest(key=key):
                broken = re.sub(rf"(?m)^{re.escape(key)}:.*\n", "", VALID_ADR, count=1)
                self.assertNotEqual(broken, VALID_ADR, f"{key}: line not found in fixture")
                d = tempfile.TemporaryDirectory()
                self.addCleanup(d.cleanup)
                _write(pathlib.Path(d.name), f"ADR-90{scalar_keys.index(key)}-x.md", broken)
                errors = si.validate(pathlib.Path(d.name))
                self.assertTrue(
                    any(key in e and ("missing" in e or "empty" in e) for e in errors),
                    f"removing {key!r} should be reported; got {errors}")

    def test_missing_applies_to_block_is_reported(self):
        # Drop the whole applies-to mapping (the one required block key).
        broken = VALID_ADR.replace(
            "applies-to:\n"
            "  domains: [docs, runtime]\n"
            "  file-patterns: [\"scripts/**\", \"docs/**\"]\n"
            "  decision-types: [dependency]\n", "")
        _write(self.adrs, "ADR-904-noscope.md", broken)
        errors = si.validate(self.adrs)
        self.assertTrue(any("applies-to" in e and "missing" in e for e in errors), errors)

    def test_applies_to_scalar_not_mapping_is_rejected(self):
        # `applies-to: some-string` (a scalar, not the three-axis mapping) must fail.
        bad = VALID_ADR.replace(
            "applies-to:\n"
            "  domains: [docs, runtime]\n"
            "  file-patterns: [\"scripts/**\", \"docs/**\"]\n"
            "  decision-types: [dependency]\n",
            "applies-to: just-a-string\n")
        _write(self.adrs, "ADR-905-flat.md", bad)
        errors = si.validate(self.adrs)
        self.assertTrue(any("must be a mapping" in e for e in errors), errors)

    def test_applies_to_axis_scalar_not_list_is_rejected(self):
        # An axis that is a scalar (`domains: docs`) instead of a list must fail.
        bad = VALID_ADR.replace("  domains: [docs, runtime]\n", "  domains: docs\n")
        _write(self.adrs, "ADR-906-axisflat.md", bad)
        errors = si.validate(self.adrs)
        self.assertTrue(any("'applies-to.domains' must be a list" in e for e in errors),
                        errors)

    def test_check_cli_exits_nonzero_on_missing_key(self):
        broken = VALID_ADR.replace(
            "assertion: A crisp checkable rule that holds for the test.\n", "")
        _write(self.adrs, "ADR-901-broken.md", broken)
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            rc = si.main(["--check", "--adrs-dir", str(self.adrs)])
        self.assertEqual(rc, 1)
        self.assertIn("assertion", buf.getvalue())

    def test_check_cli_exits_zero_on_valid_corpus(self):
        _write(self.adrs, "ADR-900-test.md", VALID_ADR)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = si.main(["--check", "--adrs-dir", str(self.adrs)])
        self.assertEqual(rc, 0)
        self.assertIn("OK", buf.getvalue())

    def test_applies_to_all_empty_axes_is_rejected(self):
        empty = VALID_ADR.replace(
            "  domains: [docs, runtime]\n"
            "  file-patterns: [\"scripts/**\", \"docs/**\"]\n"
            "  decision-types: [dependency]\n",
            "  domains: []\n"
            "  file-patterns: []\n"
            "  decision-types: []\n",
        )
        _write(self.adrs, "ADR-902-empty.md", empty)
        errors = si.validate(self.adrs)
        self.assertTrue(any("at least one non-empty" in e for e in errors), errors)

    def test_empty_assertion_value_is_rejected(self):
        # AC: each ADR carries a *crisp checkable assertion*. An `assertion:` line
        # with no value is not a checkable rule — it must fail `--check` exactly as
        # a missing key does. (A blank assertion otherwise lands in the index as the
        # empty payload `{}`, which a reviewer would read as no rule at all.)
        # NOTE: the common unquoted blank form `assertion:` is the realistic way an
        # author leaves it empty (vs. the quoted `assertion: ""` form, already caught).
        blank = VALID_ADR.replace(
            "assertion: A crisp checkable rule that holds for the test.\n",
            "assertion:\n")
        _write(self.adrs, "ADR-907-blank.md", blank)
        errors = si.validate(self.adrs)
        self.assertTrue(
            any("assertion" in e and ("empty" in e or "missing" in e) for e in errors),
            f"a blank assertion: must be rejected; got {errors}")

    def test_applies_to_unknown_subkey_is_rejected(self):
        bad = VALID_ADR.replace(
            "  decision-types: [dependency]\n",
            "  decision-types: [dependency]\n  bogus-axis: [x]\n",
        )
        _write(self.adrs, "ADR-903-bad.md", bad)
        errors = si.validate(self.adrs)
        self.assertTrue(any("unknown sub-key" in e for e in errors), errors)

    def test_empty_corpus_dir_is_an_error(self):
        errors = si.validate(self.adrs)  # empty temp dir, no ADR-*.md
        self.assertTrue(any("no ADR files" in e for e in errors), errors)

    def test_template_md_is_not_treated_as_an_adr(self):
        # TEMPLATE.md carries placeholder front-matter (id: ADR-NNN) and must be
        # skipped by both validate and the index build.
        _write(self.adrs, "ADR-900-test.md", VALID_ADR)
        _write(self.adrs, "TEMPLATE.md",
               "---\nid: ADR-NNN\ntitle: <x>\n---\n# template\n")
        self.assertEqual(si.validate(self.adrs), [])
        index = si.build_index(self.adrs)
        ids = [e["id"] for e in index["standards"]]
        self.assertEqual(ids, ["ADR-900"])


class IndexBuildTest(unittest.TestCase):
    """build_index produces the compact, scope-bearing payload, sorted by id."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.adrs = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_index_entry_shape(self):
        _write(self.adrs, "ADR-900-test.md", VALID_ADR)
        index = si.build_index(self.adrs)
        self.assertEqual(index["version"], si.INDEX_VERSION)
        self.assertEqual(len(index["standards"]), 1)
        entry = index["standards"][0]
        self.assertEqual(set(entry), {"id", "title", "status", "assertion", "applies-to"})
        self.assertEqual(entry["id"], "ADR-900")
        self.assertEqual(entry["applies-to"]["domains"], ["docs", "runtime"])
        # The body prose is NOT in the index — only the front-matter payload.
        self.assertNotIn("Body prose", si.render_index(index))

    def test_index_sorted_by_id(self):
        _write(self.adrs, "ADR-902-b.md", VALID_ADR.replace("ADR-900", "ADR-902"))
        _write(self.adrs, "ADR-900-a.md", VALID_ADR)
        index = si.build_index(self.adrs)
        self.assertEqual([e["id"] for e in index["standards"]], ["ADR-900", "ADR-902"])

    def test_missing_applies_to_axis_normalises_to_empty_list(self):
        # An ADR that omits one axis entirely still yields all three in the index.
        partial = VALID_ADR.replace(
            "  domains: [docs, runtime]\n"
            "  file-patterns: [\"scripts/**\", \"docs/**\"]\n"
            "  decision-types: [dependency]\n",
            "  domains: [docs]\n",
        )
        _write(self.adrs, "ADR-900-test.md", partial)
        entry = si.build_index(self.adrs)["standards"][0]
        self.assertEqual(entry["applies-to"], {
            "domains": ["docs"], "file-patterns": [], "decision-types": [],
        })

    def test_write_and_reload_round_trips(self):
        _write(self.adrs, "ADR-900-test.md", VALID_ADR)
        out = pathlib.Path(self._tmp.name) / "out" / "index.json"
        si.write_index(self.adrs, out)
        self.assertTrue(out.is_file())
        import json
        reloaded = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(reloaded, si.build_index(self.adrs))


class IndexDriftTest(unittest.TestCase):
    """THE sync checker: committed index.json must match a fresh build of the corpus.

    This is the test the AC names — it exits non-zero (fails) the moment the corpus
    and the committed index diverge (an ADR added/edited without regenerating).
    """

    def test_committed_index_matches_corpus(self):
        self.assertTrue(
            si.INDEX_PATH.is_file(),
            f"committed index missing at {si.INDEX_PATH} — run "
            f"`python scripts/standards_index.py` to generate it.",
        )
        committed = si.INDEX_PATH.read_text(encoding="utf-8")
        fresh = si.render_index(si.build_index())
        self.assertEqual(
            committed, fresh,
            "docs/standards/index.json is OUT OF SYNC with the ADR corpus.\n"
            "An ADR was added or edited without regenerating the index.\n"
            "Fix: run  python scripts/standards_index.py  and commit the result.",
        )

    def test_corpus_front_matter_is_valid(self):
        # The real corpus must always pass --check (every ADR carries the keys).
        errors = si.validate()
        self.assertEqual(errors, [], "real ADR corpus has front-matter errors:\n"
                         + "\n".join(errors))

    def test_print_cli_output_matches_committed_index(self):
        # The generator's `--print` (the index *produced from* the corpus front-matter)
        # must equal the committed artifact byte-for-byte — the same drift guard, proven
        # through the public CLI rather than the internal build_index call.
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = si.main(["--print"])
        self.assertEqual(rc, 0)
        self.assertEqual(
            buf.getvalue(), si.INDEX_PATH.read_text(encoding="utf-8"),
            "`standards_index.py --print` differs from committed index.json — "
            "regenerate with `python scripts/standards_index.py` and commit.")

    def test_drift_detected_when_corpus_changes_under_committed_index(self):
        # Belt-and-braces proof that the drift guard actually *bites*: build the index
        # from a synthetic 2-ADR corpus, write it out, then edit one ADR's assertion
        # WITHOUT regenerating — the committed-vs-fresh comparison must now differ.
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        adrs = pathlib.Path(tmp.name) / "adrs"
        adrs.mkdir()
        _write(adrs, "ADR-900-a.md", VALID_ADR)
        _write(adrs, "ADR-901-b.md", VALID_ADR.replace("ADR-900", "ADR-901"))
        index_path = pathlib.Path(tmp.name) / "index.json"

        si.write_index(adrs, index_path)
        committed = index_path.read_text(encoding="utf-8")
        # In sync right after generation.
        self.assertEqual(committed, si.render_index(si.build_index(adrs)))

        # Now drift the corpus (edit an assertion) and DON'T regenerate.
        _write(adrs, "ADR-901-b.md",
               VALID_ADR.replace("ADR-900", "ADR-901")
                        .replace("A crisp checkable rule that holds for the test.",
                                 "A DIFFERENT rule — corpus edited, index stale."))
        fresh = si.render_index(si.build_index(adrs))
        self.assertNotEqual(
            committed, fresh,
            "drift guard failed to detect an edited ADR — a sync checker that "
            "cannot see drift proves nothing.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
