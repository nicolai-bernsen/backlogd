"""Unit tests for scripts/ac_parse.py — standard library only (unittest).

Run from the repo root:  python scripts/test_ac_parse.py
(or collected by `python3 -m unittest discover -s scripts -p 'test_*.py'`).

These pin down the bug NB-387 fixes: typed-AC kind extraction must survive the
round-trip through Linear's description storage. Linear escapes a bare leading ``[``,
so an authored ``[test] …`` comes back as ``\\[test\\] …``; the backtick workaround
```[test]` …`` round-trips verbatim. All three storage forms of each of the three
kinds must normalize to the bare kind *before* the canonical regex matches, while
untagged text, non-kind tokens, and a tag with no trailing space all stay ``review``
with their full text preserved.
"""

import pathlib
import sys
import unittest

# Make ``import ac_parse`` work regardless of how this file is invoked — same shape
# as the sibling scripts/test_witness.py.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ac_parse  # noqa: E402


class ExtractKindStorageFormsTest(unittest.TestCase):
    """Each of the three kinds, in each of the three storage forms, → that kind."""

    # (kind, list of (item_text, expected_body)) — body is what survives after the
    # "[kind] " prefix is stripped from the normalized text.
    CASES = {
        "test": [
            ("[test] run the suite", "run the suite"),          # 1. canonical / bare
            ("\\[test\\] run the suite", "run the suite"),      # 2. Linear's stored form
            ("`[test]` run the suite", "run the suite"),        # 3. backtick workaround
        ],
        "manual": [
            ("[manual] PO confirms the wording", "PO confirms the wording"),
            ("\\[manual\\] PO confirms the wording", "PO confirms the wording"),
            ("`[manual]` PO confirms the wording", "PO confirms the wording"),
        ],
        "review": [
            ("[review] the diff is small", "the diff is small"),
            ("\\[review\\] the diff is small", "the diff is small"),
            ("`[review]` the diff is small", "the diff is small"),
        ],
    }

    def test_all_kinds_all_storage_forms(self):
        for expected_kind, cases in self.CASES.items():
            for item_text, expected_body in cases:
                with self.subTest(kind=expected_kind, item=item_text):
                    kind, body = ac_parse.extract_kind(item_text)
                    self.assertEqual(kind, expected_kind, f"{item_text!r} → kind")
                    self.assertEqual(body, expected_body, f"{item_text!r} → body")


class ExtractKindDefaultsTest(unittest.TestCase):
    """Untagged / non-kind / malformed-tag items all default to review, text intact."""

    def test_untagged_defaults_to_review_full_text_preserved(self):
        text = "Existing un-tagged AC continues to work."
        kind, body = ac_parse.extract_kind(text)
        self.assertEqual(kind, "review")
        self.assertEqual(body, text, "untagged body must be the original text, unchanged")

    def test_non_kind_token_stays_body_text_review(self):
        # A bracketed token that is not one of the three kinds is body text, not a tag.
        text = "[wip] still drafting this criterion"
        kind, body = ac_parse.extract_kind(text)
        self.assertEqual(kind, "review")
        self.assertEqual(body, text, "non-kind [token] must be preserved verbatim")

    def test_escaped_non_kind_token_stays_body_text_review(self):
        # Even in Linear's escaped storage form, a non-kind token is not a tag.
        text = "\\[wip\\] still drafting this criterion"
        kind, body = ac_parse.extract_kind(text)
        self.assertEqual(kind, "review")
        self.assertEqual(body, text, "escaped non-kind \\[token\\] must be preserved verbatim")

    def test_tag_without_trailing_space_does_not_match(self):
        # The canonical regex requires exactly one trailing space; [test]foo must not
        # match — it stays review with the original text preserved.
        text = "[test]foo no space after the bracket"
        kind, body = ac_parse.extract_kind(text)
        self.assertEqual(kind, "review")
        self.assertEqual(body, text, "no-trailing-space tag must be preserved verbatim")

    def test_escaped_tag_without_trailing_space_does_not_match(self):
        text = "\\[test\\]foo no space after the bracket"
        kind, body = ac_parse.extract_kind(text)
        self.assertEqual(kind, "review")
        self.assertEqual(body, text, "escaped no-space tag must be preserved verbatim")


class ExtractKindNarrownessTest(unittest.TestCase):
    """Normalization is surgical — it only rewrites the leading tag region."""

    def test_only_leading_backslash_unescaped_body_backslashes_kept(self):
        # A backslash later in the body (e.g. an escaped bracket in prose) is NOT
        # touched — only the leading tag region is normalized.
        kind, body = ac_parse.extract_kind("\\[test\\] keep this \\[literal\\] intact")
        self.assertEqual(kind, "test")
        self.assertEqual(body, "keep this \\[literal\\] intact")

    def test_only_leading_code_span_unwrapped_body_spans_kept(self):
        kind, body = ac_parse.extract_kind("`[review]` see the `code` span untouched")
        self.assertEqual(kind, "review")
        self.assertEqual(body, "see the `code` span untouched")

    def test_kind_must_be_lowercase(self):
        # The canonical regex is case-sensitive; an uppercase tag is body text.
        text = "[TEST] uppercase is not a kind"
        kind, body = ac_parse.extract_kind(text)
        self.assertEqual(kind, "review")
        self.assertEqual(body, text)


class ExtractKindReviewerBodyCommandTest(unittest.TestCase):
    """The reviewer's real need: on a matched [test] bullet, the first backticked
    span in the *body* is the command it runs. Normalization only touches the
    leading tag region, so a body command must survive byte-for-byte after the
    ``[kind] `` prefix is stripped — in every storage form a [test] tag can take.
    """

    def test_test_body_keeps_backticked_command_bare_form(self):
        kind, body = ac_parse.extract_kind("[test] run `dbtf build` first")
        self.assertEqual(kind, "test")
        self.assertEqual(body, "run `dbtf build` first")
        # The first backticked span — what the reviewer extracts and runs.
        self.assertIn("`dbtf build`", body)

    def test_test_body_keeps_backticked_command_escaped_form(self):
        # Linear's stored form of a bare [test]; the body command must be intact.
        kind, body = ac_parse.extract_kind("\\[test\\] Run `python -m unittest` then check")
        self.assertEqual(kind, "test")
        self.assertEqual(body, "Run `python -m unittest` then check")
        self.assertIn("`python -m unittest`", body)

    def test_test_body_keeps_backticked_command_codespan_form(self):
        # The backtick workaround wrapping the tag must NOT swallow a *separate*
        # backticked command later in the body — only the leading span unwraps.
        kind, body = ac_parse.extract_kind("`[test]` Run the suite `python -m unittest`")
        self.assertEqual(kind, "test")
        self.assertEqual(body, "Run the suite `python -m unittest`")
        self.assertIn("`python -m unittest`", body)

    def test_test_body_keeps_internal_brackets_on_match(self):
        # Body-internal brackets (e.g. an [exit 0] note) are not part of the tag
        # region and must be preserved verbatim alongside a backticked command.
        kind, body = ac_parse.extract_kind("[test] run `cmd` and confirm [exit 0]")
        self.assertEqual(kind, "test")
        self.assertEqual(body, "run `cmd` and confirm [exit 0]")


if __name__ == "__main__":
    unittest.main(verbosity=2)
