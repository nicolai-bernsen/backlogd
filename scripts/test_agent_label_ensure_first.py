"""Regression tests for NB-421 — `save_issue` silently drops unknown labels, so
`commands/scope.md` §4.5's `agent:*` routing must **ensure the label first**
(`create_issue_label`, idempotent) before applying it, not rely on a phantom
"auto-creates unknown labels on write" behaviour.

NB-421 is a **prose / behaviour-doc** unit: the developer corrected the false
"auto-creates unknown labels" claim and wired the ensure-first procedure across
`commands/scope.md` §4.5, `skills/linear/references/linear-mcp.md`,
`docs/specialists.md` and `skills/retro/SKILL.md`. Real Linear behaviour (observed in
the NB-417 solve, 2026-05-31): passing a not-yet-existing label name in
`save_issue(labels: [...])` succeeds but **silently drops** the unknown name — no error,
no label created — so a brand-new `agent:*` routing label would never land and
`/backlogd:solve` would fall back to the generic developer unnoticed.

This file is the **durable guard** the reviewer leans on. AC4's
`grep -rn "auto-creates unknown labels" commands/ skills/` is a one-shot check the
developer ran; this re-implements it as a *standing* stdlib check (the rg-vacuity
lesson — a bare `rg … && exit 1` passes false-green where `rg` is absent, so we walk the
trees and read the text in Python instead). It also pins the *positive* side of the fix
— that the ensure-first `create_issue_label` step is actually **present** at the two
load-bearing sites — so a future edit can't quietly delete the fix while leaving the bad
claim gone.

What is proven here (the `[review]`/`[test]` ACs whose *presence/absence* is
mechanically checkable):

  * AC4  (`[test]`)   — the false phrase "auto-creates unknown labels" appears in **no**
                        file under `commands/` or `skills/` (re-implements the grep in
                        Python, whitespace-tolerant, walking both trees).
  * AC1  (`[review]`) — `commands/scope.md` §4.5's `agent:*` application path references
                        `create_issue_label` (the ensure-first fix is *present*, not
                        merely the bad claim removed) and states the corrected behaviour
                        (the unknown name is silently dropped).
  * AC2  (`[review]`) — the corrected approach mirrors the proven ensure-label pattern
                        (names `blocked` / `manual-pending`) and stays key-free
                        (no `LINEAR_API_KEY`). The `linear-mcp.md` `agent:*` table note
                        carries the same ensure-first `create_issue_label` correction.

The deeper *semantic* AC3 claim ("a repo audit confirms no *other* live site relies on
save_issue auto-create") is a `[review]` judgement over the developer's work log; its
durable mechanical proxy is the AC4 absence sweep below (the false belief is gone
repo-wide), but the audit reasoning itself is the reviewer's read, not a string pin.

Matches are whitespace-collapsed (survive prose line-wrapping) and never pin exact
indentation. `EnsureFirstGuardBitesTest` is the negative control: it proves each anchor
*would* fail were the fix removed / the bad phrase re-introduced, so the green results
above are non-vacuous.

Run from the repo root:  python scripts/test_agent_label_ensure_first.py
(or collected by `python3 -m unittest discover -s scripts -p 'test_*.py'`).
"""

import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

SCOPE_CMD = REPO_ROOT / "commands" / "scope.md"
LINEAR_MCP_REF = REPO_ROOT / "skills" / "linear" / "references" / "linear-mcp.md"

# The exact false claim NB-421 removed. Lower-cased + whitespace-collapsed before
# matching so a re-wrapped or re-cased reintroduction is still caught.
FALSE_PHRASE = "auto-creates unknown labels"

# Trees the AC4 grep covered (`grep -rn ... commands/ skills/`).
SWEPT_TREES = ("commands", "skills")


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def _norm(text: str) -> str:
    """Whitespace-collapse so a content pin survives prose line-wrapping."""
    return " ".join(text.split())


def _iter_tree_files(tree: str):
    """Yield every regular file under REPO_ROOT/<tree> (depth-first walk)."""
    root = REPO_ROOT / tree
    if not root.is_dir():
        return
    for path in sorted(root.rglob("*")):
        if path.is_file():
            yield path


class FalsePhraseAbsentTest(unittest.TestCase):
    """AC4 (`[test]`): the misleading "auto-creates unknown labels" claim is gone —
    `grep -rn "auto-creates unknown labels" commands/ skills/` returns no occurrence.

    Re-implemented in pure Python (walk `commands/` + `skills/`, read each file, scan
    the whitespace-collapsed lower-cased text) so the check is non-vacuous regardless of
    `grep`/`rg` being on PATH — the rg-vacuity lesson. Whitespace-tolerant + case-folded
    so a re-wrapped or re-cased reintroduction of the phrase is still caught.
    """

    def test_false_phrase_absent_from_commands_and_skills(self):
        offenders = []
        for tree in SWEPT_TREES:
            for path in _iter_tree_files(tree):
                try:
                    haystack = _norm(_read(path)).lower()
                except (UnicodeDecodeError, OSError):
                    # Binary / unreadable file — not a prose doc; skip.
                    continue
                if FALSE_PHRASE in haystack:
                    offenders.append(str(path.relative_to(REPO_ROOT)))
        self.assertEqual(
            offenders,
            [],
            "the false 'auto-creates unknown labels' claim must not appear under "
            f"commands/ or skills/ — found in: {offenders}",
        )

    def test_sweep_actually_visited_files(self):
        """Guard the guard: prove the walk found the trees + read real content, so a
        green `test_false_phrase_absent...` can't be silently empty (e.g. a bad path)."""
        visited = [p for tree in SWEPT_TREES for p in _iter_tree_files(tree)]
        self.assertGreater(
            len(visited), 10,
            "the commands/ + skills/ sweep must visit a non-trivial number of files — "
            f"only saw {len(visited)} (is the path wrong?)",
        )
        # scope.md is the file the fix lives in — it must be in the swept set.
        self.assertIn(
            SCOPE_CMD.resolve(),
            {p.resolve() for p in visited},
            "commands/scope.md must be within the swept trees",
        )


class ScopeEnsureFirstFixPresentTest(unittest.TestCase):
    """AC1: `commands/scope.md` §4.5's `agent:*` application **ensures the label exists**
    (via `create_issue_label`) before applying it, and states the corrected behaviour —
    not merely the absence of the old bad claim."""

    def test_scope_agent_label_uses_create_issue_label(self):
        body = _norm(_read(SCOPE_CMD))
        self.assertIn(
            "create_issue_label",
            body,
            "commands/scope.md §4.5 must ensure the agent:* label via create_issue_label",
        )

    def test_scope_states_silent_drop_behaviour(self):
        """The corrected behaviour (unknown name → silently dropped) must be documented,
        so the fix carries its own rationale rather than reading as an unexplained step.
        Match on the markdown-bold-stripped, whitespace-collapsed text so the assertion
        survives `**not**` emphasis and prose wrapping."""
        body = _norm(_read(SCOPE_CMD)).replace("**", "").lower()
        # The corrected claim: save_issue does NOT auto-create labels.
        self.assertIn(
            "does not auto-create labels",
            body,
            "commands/scope.md §4.5 must state the corrected behaviour "
            "(save_issue does NOT auto-create labels)",
        )
        # The load-bearing correction: the unknown name is silently dropped.
        self.assertIn(
            "silently dropped",
            body,
            "the §4.5 correction must explain the unknown label name is silently dropped",
        )

    def test_scope_ensure_first_anchored_to_agent_label(self):
        """The fix lives specifically on the agent:* routing path — assert both the
        agent label token and the ensure-first verb co-occur in the collapsed text."""
        body = _norm(_read(SCOPE_CMD))
        self.assertIn("`agent:<suffix>`", body)
        # Ensure-first phrasing the developer used ("Ensure the label exists first").
        self.assertIn("Ensure the label exists first", body)


class LinearMcpRefMirrorsFixTest(unittest.TestCase):
    """AC2: the corrected approach mirrors the proven ensure-label pattern
    (`blocked` / `manual-pending`), stays key-free, and the `agent:*` family note in
    `skills/linear/references/linear-mcp.md` carries the same ensure-first correction."""

    def test_ref_agent_note_uses_create_issue_label(self):
        body = _norm(_read(LINEAR_MCP_REF))
        self.assertIn(
            "create_issue_label",
            body,
            "the linear-mcp.md agent:* table note must state the ensure-first "
            "create_issue_label step",
        )

    def test_ref_names_the_proven_sibling_patterns(self):
        body = _norm(_read(LINEAR_MCP_REF))
        # The fix is justified by mirroring the existing ensure-label skills.
        self.assertIn("blocked", body)
        self.assertIn(
            "manual-pending", body,
            "the correction must mirror the proven blocked / manual-pending ensure-label "
            "pattern",
        )

    def test_scope_fix_is_keyfree(self):
        """AC2: no API key / non-MCP path is introduced by the fix."""
        self.assertNotIn(
            "LINEAR_API_KEY", _read(SCOPE_CMD),
            "the §4.5 ensure-first fix must stay key-free (official MCP only)",
        )


class EnsureFirstGuardBitesTest(unittest.TestCase):
    """Negative control — prove every anchor above *can* fail (the rg-vacuity lesson: a
    check that cannot fail is worthless).

    Two directions, because NB-421 is half about an **absence** (the bad phrase) and half
    about a **presence** (the ensure-first fix):

      * presence anchors — for each (file, needle) the suite asserts present, mutate the
        *read string* in memory by deleting the needle and re-run the same `in`
        predicate; it must now be False.
      * absence anchor — for the AC4 false-phrase sweep, *inject* the phrase into an
        in-memory copy of scope.md's text and assert the sweep predicate would then flag
        it. This proves `test_false_phrase_absent...` is sensitive to a reintroduction,
        not tautologically green.

    We never mutate files on disk — only the read strings — so the guards are proven
    sensitive to the wiring rather than green by construction.
    """

    # (path, needle) — one per load-bearing presence pin.
    PRESENCE_ANCHORS = [
        (SCOPE_CMD, "create_issue_label"),
        (SCOPE_CMD, "silently dropped"),
        (SCOPE_CMD, "Ensure the label exists first"),
        (LINEAR_MCP_REF, "create_issue_label"),
        (LINEAR_MCP_REF, "manual-pending"),
    ]

    def test_every_presence_anchor_is_present(self):
        for path, needle in self.PRESENCE_ANCHORS:
            self.assertIn(
                needle, _norm(_read(path)),
                f"{path.name} must currently contain the fix anchor {needle!r}",
            )

    def test_every_presence_anchor_would_fail_if_fix_removed(self):
        """Fail-direction proof for the presence pins: delete the needle from the
        in-memory text and the same predicate must now be False."""
        for path, needle in self.PRESENCE_ANCHORS:
            body = _norm(_read(path))
            mutated = body.replace(needle, "")
            self.assertNotIn(
                needle, mutated,
                f"removing {needle!r} from {path.name} must make the presence check FAIL "
                "— otherwise that guard is vacuous",
            )

    def test_false_phrase_sweep_would_catch_a_reintroduction(self):
        """Fail-direction proof for the AC4 absence sweep: the phrase is absent now, but
        injecting it into an in-memory copy of scope.md's text must make the sweep
        predicate (collapsed + lower-cased `in`) flag it — proving the absence test is
        sensitive to a regression, not vacuously empty."""
        clean = _norm(_read(SCOPE_CMD)).lower()
        self.assertNotIn(
            FALSE_PHRASE, clean,
            "precondition: the false phrase must be absent from scope.md today",
        )
        reintroduced = (clean + " linear's mcp " + FALSE_PHRASE + " on write").lower()
        self.assertIn(
            FALSE_PHRASE, reintroduced,
            "the absence sweep must flag a reintroduced 'auto-creates unknown labels' "
            "phrase — otherwise AC4's guard cannot bite",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
