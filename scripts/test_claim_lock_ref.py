"""Content tests for the claim-lock skill — NB-414 (solve/review claim-lock).

NB-414 adds a key-free, Linear-native **work-item lock** so two concurrent
`/backlogd:solve` / `/backlogd:review` sessions never pick up the same problem
at once (no duplicate reviews, no double-merge). The mechanism is prose: a new
skill plus references wired into the solve and review pickup paths.

Only **one** of the unit's eight acceptance criteria names a behaviour a test
runner can assert in code — the rest are [review] design contracts the reviewer
reads against the merged prose, and one [manual] AC that needs two live
simultaneous Claude Code sessions to observe. This file proves exactly that one
[test] AC, mirroring the repo's prose-grep test pattern
(`scripts/test_documents_and_updates_ref.py`, `scripts/test_retro.py`):

* **[test]** "A claim-lock skill is added and referenced from both solve and
  review pickup paths" — the AC's own verification one-liner is
  ``bash -c 'test -f skills/linear/claim-lock.md && grep -rqlE "claim-lock(\\.md)?" \\
  commands/solve.md commands/review.md skills/solve/ && echo ok'`` printing ``ok``.
  Re-expressed here as stdlib assertions so it is portable + non-vacuous:
  (a) the skill file exists, and (b) the token ``claim-lock`` is referenced from
  ``commands/solve.md``, ``commands/review.md``, and at least one file under
  ``skills/solve/``.

Non-vacuity: at the parent commit (5338c21) ``skills/linear/claim-lock.md`` does
not exist and neither command references ``claim-lock`` — so every assertion
below fails without NB-414 and passes with it (verified by the tester against
that commit).

Standard library only (unittest). Run from the repo root:

    python scripts/test_claim_lock_ref.py
    (or collected by `python -m unittest discover -s scripts -p 'test_*.py'`).

The remaining ACs ([manual] live two-session race; the six [review] design
properties) are not assertable in code — see this unit's tester report for why.
"""

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

CLAIM_LOCK_SKILL = REPO_ROOT / "skills" / "linear" / "claim-lock.md"
SOLVE_CMD = REPO_ROOT / "commands" / "solve.md"
REVIEW_CMD = REPO_ROOT / "commands" / "review.md"
SOLVE_SKILLS_DIR = REPO_ROOT / "skills" / "solve"

# The exact token the AC's grep matches: "claim-lock" optionally followed by ".md".
# Mirrors `grep -rqlE "claim-lock(\.md)?"` so this test asserts the same contract.
CLAIM_LOCK_REF = re.compile(r"claim-lock(\.md)?")


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def _references_claim_lock(p: pathlib.Path) -> bool:
    return bool(CLAIM_LOCK_REF.search(_read(p)))


class ClaimLockSkillAddedAndReferencedTest(unittest.TestCase):
    """[test] A claim-lock skill is added and referenced from both the solve and
    review pickup paths.

    One assertion per clause of the AC's verification one-liner so the evidence
    maps 1:1 to the contract: the skill file exists (`test -f`), and the
    `claim-lock` reference appears in `commands/solve.md`, `commands/review.md`,
    and at least one file under `skills/solve/` (`grep -rqlE ... && echo ok`).
    """

    def test_claim_lock_skill_file_exists(self):
        # `test -f skills/linear/claim-lock.md`
        self.assertTrue(
            CLAIM_LOCK_SKILL.is_file(),
            f"[test] AC expects the claim-lock skill at {CLAIM_LOCK_SKILL} to exist",
        )

    def test_solve_command_references_claim_lock(self):
        # solve pickup path must reference the skill.
        self.assertTrue(
            SOLVE_CMD.is_file(),
            f"expected {SOLVE_CMD} to exist (a vacuous-pass guard before the grep)",
        )
        self.assertTrue(
            _references_claim_lock(SOLVE_CMD),
            "[test] AC: commands/solve.md must reference `claim-lock` "
            "(the solve pickup path wires in the claim-lock skill)",
        )

    def test_review_command_references_claim_lock(self):
        # review pick path must reference the skill.
        self.assertTrue(
            REVIEW_CMD.is_file(),
            f"expected {REVIEW_CMD} to exist (a vacuous-pass guard before the grep)",
        )
        self.assertTrue(
            _references_claim_lock(REVIEW_CMD),
            "[test] AC: commands/review.md must reference `claim-lock` "
            "(the review pick path wires in the claim-lock skill)",
        )

    def test_some_solve_skill_references_claim_lock(self):
        # `grep -r ... skills/solve/` — at least one file under skills/solve/
        # must reference the skill (the AC's third grep target is the directory).
        self.assertTrue(
            SOLVE_SKILLS_DIR.is_dir(),
            f"expected {SOLVE_SKILLS_DIR} to exist (a vacuous-pass guard before the grep)",
        )
        referencing = [
            p
            for p in sorted(SOLVE_SKILLS_DIR.rglob("*.md"))
            if _references_claim_lock(p)
        ]
        self.assertTrue(
            referencing,
            "[test] AC: at least one file under skills/solve/ must reference "
            "`claim-lock` (the solve pickup/dispatch path), but none do",
        )

    def test_one_liner_contract_holds_end_to_end(self):
        # The AC's whole verification one-liner, re-expressed: file exists AND all
        # three grep targets reference the token. This is the single assertion that
        # would print `ok`; the per-target tests above localise a failure.
        skill_present = CLAIM_LOCK_SKILL.is_file()
        solve_ref = SOLVE_CMD.is_file() and _references_claim_lock(SOLVE_CMD)
        review_ref = REVIEW_CMD.is_file() and _references_claim_lock(REVIEW_CMD)
        solve_skill_ref = SOLVE_SKILLS_DIR.is_dir() and any(
            _references_claim_lock(p) for p in SOLVE_SKILLS_DIR.rglob("*.md")
        )
        self.assertTrue(
            skill_present and solve_ref and review_ref and solve_skill_ref,
            "[test] AC one-liner must hold: `test -f skills/linear/claim-lock.md && "
            'grep -rqlE "claim-lock(\\.md)?" commands/solve.md commands/review.md '
            "skills/solve/` should print `ok` "
            f"(skill={skill_present}, solve={solve_ref}, review={review_ref}, "
            f"solve_skill={solve_skill_ref})",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
