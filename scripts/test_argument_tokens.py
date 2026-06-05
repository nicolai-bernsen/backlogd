"""Regression tests for NB-356 — shared mode-token grammar for the backlogd verbs.

NB-356 adds a single `$ARGUMENTS` token grammar every long-running `/backlogd:*` verb
parses — `mode:report-only`, `mode:headless`, `base:<sha>` — defined **once** in
`skills/common/argument-tokens.md` and **referenced** (never restated) by the five verb
command files. The change is prose-only across:

  * skills/common/argument-tokens.md         — the grammar (new, single source of truth)
  * commands/{scope,solve,status,review,release}.md — each carries a "Parse argument
                                                tokens" step that loads the shared skill
  * skills/solve/dryrun.md                    — `--dryrun` ≡ `mode:report-only` (alias)
  * README.md                                 — user-facing token list

These content pins anchor the **cross-verb wiring** so an incidental prose regression in
the touched neighbourhood trips CI (the same guard-the-neighbourhood discipline as
scripts/test_first_live_run_gate.py and scripts/test_ship_on_green_and_manual.py). They are
the AC7 regression test, and they re-implement the self-contained `python -c …` checks the
other `[test]` ACs carry so the wiring is pinned from one place that CI always runs.

Mapped to NB-356's ACs (the `[test]` ones carry their own `python -c` one-liners; these
pin the same facts non-vacuously so they cannot silently drift):

  * AC1 [test] — argument-tokens.md exists and defines all three tokens.
                 Pinned by GrammarDocDefinesAllThreeTokens.
  * AC2 [test] — the grammar doc states the unrecognised-token rule (ignore-with-warning)
                 and position-independence. Pinned by GrammarDocStatesRules.
  * AC3 [test] — all five verb command files reference the shared grammar skill.
                 Pinned by AllFiveVerbsReferenceSharedSkill.
  * AC4 [test] — every verb's command file carries a "Parse argument tokens" step.
                 Pinned by EveryVerbCarriesParseStep.
  * AC5 [test] — `--dryrun` retained as a working alias for `mode:report-only` on solve.
                 Pinned by DryrunAliasRetainedOnSolve.
  * AC6 [test] — the grammar doc records `base:<sha>` is honoured only where a verb opens a
                 worktree (solve) and warn-ignored elsewhere. Pinned by
                 GrammarDocRecordsBaseIsWorktreeOnly.
  * AC8 [test] — user-facing docs list the tokens and which verbs honour each.
                 Pinned by UserFacingDocsListTokens.

Whether the prose is *sound*, the diff truly *minimal*, the report-only/headless semantics
*correct* on each verb, and the grammar genuinely *defined-once-not-restated* stay the
reviewer's call (the `[review]` ACs) — these pins guard the wiring + its single-source-of-
truth shape against silent drift, not a substitute for that read.

CI runs `python3 -m unittest discover -s scripts -p 'test_*.py'` from the repo root
(see .github/workflows/ci.yml), so this lives in scripts/ as a stdlib unittest. It does
NOT do a git-diff / whole-worktree footprint scan.

Run from the repo root:
    python -m unittest scripts.test_argument_tokens
    python scripts/test_argument_tokens.py
"""

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

GRAMMAR = REPO_ROOT / "skills" / "common" / "argument-tokens.md"
DRYRUN = REPO_ROOT / "skills" / "solve" / "dryrun.md"
README = REPO_ROOT / "README.md"

VERBS = ("scope", "solve", "status", "review", "release")

THREE_TOKENS = ("mode:report-only", "mode:headless", "base:<sha>")


def _cmd(verb: str) -> pathlib.Path:
    return REPO_ROOT / "commands" / f"{verb}.md"


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def _norm(text: str) -> str:
    """Whitespace-collapse so a content pin survives prose line-wrapping."""
    return " ".join(text.split())


class GrammarDocDefinesAllThreeTokens(unittest.TestCase):
    """AC1: skills/common/argument-tokens.md exists and defines all three tokens."""

    def test_grammar_doc_exists(self):
        self.assertTrue(
            GRAMMAR.is_file(),
            f"AC1: the shared grammar must exist at {GRAMMAR}.",
        )

    def test_all_three_tokens_defined(self):
        body = _read(GRAMMAR)
        for token in THREE_TOKENS:
            self.assertIn(
                token,
                body,
                f"AC1: skills/common/argument-tokens.md must define the {token!r} token.",
            )


class GrammarDocStatesRules(unittest.TestCase):
    """AC2: the grammar doc states the unrecognised-token rule (ignore-with-warning) and
    position-independence."""

    def test_unrecognised_token_ignore_with_warning(self):
        body = _read(GRAMMAR).lower()
        self.assertTrue(
            ("unrecogni" in body) or ("unknown" in body),
            "AC2: the grammar doc must name the unrecognised/unknown-token rule.",
        )
        self.assertIn(
            "warn",
            body,
            "AC2: the unrecognised-token rule must be ignore-with-a-warning (the word "
            "'warn' must appear).",
        )

    def test_position_independence_stated(self):
        body = _read(GRAMMAR).lower()
        self.assertTrue(
            ("any position" in body)
            or ("position-independent" in body)
            or ("order-independent" in body),
            "AC2: the grammar doc must state tokens are position-independent (any "
            "position / position-independent / order-independent).",
        )


class AllFiveVerbsReferenceSharedSkill(unittest.TestCase):
    """AC3: all five verb command files reference the shared grammar skill (so the grammar
    is defined once and referenced, never restated)."""

    def test_every_verb_references_the_shared_skill(self):
        missing = [
            verb
            for verb in VERBS
            if "argument-tokens.md" not in _read(_cmd(verb))
        ]
        self.assertEqual(
            missing,
            [],
            f"AC3: these verb command files do not reference "
            f"skills/common/argument-tokens.md: {missing}.",
        )


class EveryVerbCarriesParseStep(unittest.TestCase):
    """AC4: every verb's command file carries a 'Parse argument tokens' step."""

    PARSE_STEP = re.compile(r"[Pp]arse argument tokens")

    def test_every_verb_has_a_parse_argument_tokens_step(self):
        missing = [
            verb
            for verb in VERBS
            if not self.PARSE_STEP.search(_read(_cmd(verb)))
        ]
        self.assertEqual(
            missing,
            [],
            f"AC4: these verb command files lack a 'Parse argument tokens' step: "
            f"{missing}.",
        )


class DryrunAliasRetainedOnSolve(unittest.TestCase):
    """AC5: --dryrun retained as a working alias for mode:report-only on solve, with one
    contract (no behavioural fork) — asserted across solve.md and dryrun.md."""

    def test_solve_carries_both_spellings(self):
        body = _read(_cmd("solve"))
        self.assertIn(
            "--dryrun",
            body,
            "AC5: commands/solve.md must still carry --dryrun.",
        )
        self.assertIn(
            "mode:report-only",
            body,
            "AC5: commands/solve.md must name mode:report-only (the alias target).",
        )

    def test_dryrun_skill_names_the_alias(self):
        body = _read(DRYRUN)
        self.assertIn(
            "mode:report-only",
            body,
            "AC5: skills/solve/dryrun.md must name mode:report-only so --dryrun and the "
            "token are documented as one contract.",
        )

    def test_alias_is_no_fork(self):
        """The alias must be stated as one contract / no behavioural fork — a future edit
        that forked the two behaviours would want to trip here."""
        grammar = _norm(_read(GRAMMAR)).lower()
        dryrun = _norm(_read(DRYRUN)).lower()
        self.assertIn(
            "no behavioural fork",
            grammar,
            "AC5: the grammar doc must state --dryrun and mode:report-only have no "
            "behavioural fork on solve.",
        )
        self.assertIn(
            "alias",
            dryrun,
            "AC5: skills/solve/dryrun.md must document --dryrun as an alias of "
            "mode:report-only.",
        )


class GrammarDocRecordsBaseIsWorktreeOnly(unittest.TestCase):
    """AC6: the grammar doc records base:<sha> is honoured only where a verb opens a
    worktree (solve) and warn-ignored elsewhere."""

    def test_base_is_recorded_as_worktree_only(self):
        raw = _read(GRAMMAR)
        body = raw.lower()
        self.assertIn(
            "base:<sha>",
            raw,
            "AC6: the grammar doc must carry the literal base:<sha> token.",
        )
        self.assertIn(
            "worktree",
            body,
            "AC6: the grammar doc must tie base:<sha> to opening a worktree.",
        )
        self.assertIn(
            "solve",
            body,
            "AC6: the grammar doc must name solve as the verb that honours base:<sha>.",
        )

    def test_base_is_warn_ignored_elsewhere(self):
        body = _norm(_read(GRAMMAR)).lower()
        self.assertIn(
            "warn-ignored",
            body,
            "AC6: the grammar doc must state base:<sha> is warn-ignored on the non-"
            "worktree verbs.",
        )


class UserFacingDocsListTokens(unittest.TestCase):
    """AC8: user-facing docs (docs/usage.md if present, else README.md) list the tokens and
    which verbs honour each."""

    def _user_facing_text(self) -> str:
        cands = [REPO_ROOT / "docs" / "usage.md", README]
        return "".join(_read(c) for c in cands if c.is_file())

    def test_all_three_tokens_listed(self):
        txt = self._user_facing_text()
        self.assertTrue(txt, "AC8: a user-facing doc (README.md / docs/usage.md) must exist.")
        for token in THREE_TOKENS:
            self.assertIn(
                token,
                txt,
                f"AC8: the user-facing docs must list the {token!r} token.",
            )

    def test_docs_name_which_verbs_honour_each(self):
        """Beyond listing the tokens, the docs must convey which verbs honour each (the AC
        wording). The README token block names the verbs; pin a couple of the load-bearing
        phrases so a reword that dropped the per-verb mapping trips."""
        txt = _norm(self._user_facing_text()).lower()
        self.assertIn(
            "all five verbs",
            txt,
            "AC8: the docs must say mode:report-only is honoured by all five verbs.",
        )
        self.assertIn(
            "only verb that opens a worktree",
            txt,
            "AC8: the docs must say base:<sha> is honoured by solve, the only verb that "
            "opens a worktree.",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
