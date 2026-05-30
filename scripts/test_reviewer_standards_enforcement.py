"""Regression net for NB-383 — reviewer loads + enforces the docs/standards/ corpus.

NB-383 owns NB-378 acceptance criteria #1 and #7. Both are `[review]`-kind — they are
judgements an agent renders from prose at verdict time, NOT behaviours a test runner can
exercise. So this file does **not** try to prove "the reviewer obeys the instruction"
(that would be a tautology against the doc that *is* the instruction). It pins the two
load-bearing prose invariants the change introduced, so an incidental reword in the
touched neighbourhood (`agents/reviewer.md`, `skills/reviewer/SKILL.md`) trips CI instead
of silently regressing the policy:

  - AC #7 — the status filter is the *exact* fix the AC asks for: enforce only the
    **current Accepted** set and ignore non-Accepted statuses, `Proposed` **included**
    (the pre-NB-383 wording skipped only Superseded/Deprecated, leaving `Proposed` —
    "not yet binding" — wrongly enforceable). This file fails the moment either reviewer
    surface drops the Accepted-only filter or stops naming `Proposed` as ignored.
  - AC #1 — every verdict must cite which standards it checked **by id/path**. The verdict
    template already carries that; the pin guards against a reword that drops the
    cite-by-id/path requirement (which would un-prove AC #1's "cites which standards").

These are content pins, not a substitute for the reviewer's `[review]` judgement — they
anchor the strings so the neighbourhood can't drift unnoticed (same guard-the-
neighbourhood discipline as scripts/test_ship_on_green_and_manual.py).

Run from the repo root:  python scripts/test_reviewer_standards_enforcement.py
(or collected by `python -m unittest discover -s scripts -p 'test_*.py'`).
"""

import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

REVIEWER_AGENT = REPO_ROOT / "agents" / "reviewer.md"
REVIEWER_SKILL = REPO_ROOT / "skills" / "reviewer" / "SKILL.md"

# Both surfaces the developer edited carry the status filter. AC #7 is only proven if the
# invariant holds in BOTH the agent file and its mirroring skill, so they are checked as a
# set — a reword that fixes one and strands the other must fail.
REVIEWER_SURFACES = (REVIEWER_AGENT, REVIEWER_SKILL)


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def _norm(text: str) -> str:
    """Whitespace-collapse so a content pin survives prose line-wrapping."""
    return " ".join(text.split())


class AcceptedOnlyFilterTest(unittest.TestCase):
    """AC #7 — the reviewer enforces only the *current Accepted* set and ignores
    Superseded/Proposed/Deprecated entries."""

    def test_both_surfaces_enforce_only_the_accepted_set(self):
        # Lower-cased so the pin survives the legitimate sentence-start vs mid-sentence
        # capitalization of the verb ("Enforce ..." in reviewer.md, "enforce ..." in the
        # skill); the load-bearing phrase is "only the current `Accepted` set".
        for path in REVIEWER_SURFACES:
            with self.subTest(surface=path.name):
                body = _norm(_read(path)).lower()
                self.assertIn(
                    "enforce only the current `accepted` set",
                    body,
                    f"{path.relative_to(REPO_ROOT)} must state the reviewer enforces "
                    f"only the current Accepted set (AC #7).",
                )

    def test_both_surfaces_name_proposed_as_ignored(self):
        # The crux of AC #7: `Proposed` is not-yet-binding and must be skipped. The
        # pre-NB-383 wording skipped only Superseded/Deprecated, so a regression that
        # drops `Proposed` from the skip set re-introduces the exact bug. Require all
        # three non-Accepted statuses to be named alongside the Accepted-only filter.
        for path in REVIEWER_SURFACES:
            with self.subTest(surface=path.name):
                body = _norm(_read(path))
                for status in ("Proposed", "Superseded", "Deprecated"):
                    self.assertIn(
                        status,
                        body,
                        f"{path.relative_to(REPO_ROOT)} must name `{status}` among the "
                        f"non-Accepted statuses the reviewer skips (AC #7).",
                    )

    def test_pins_would_bite_on_the_pre_fix_wording(self):
        # Guard against a tautological green: prove these assertions actually FIRE on the
        # superseded wording (Superseded/Deprecated only, no Accepted-only filter, no
        # `Proposed`). If this synthetic regression passed the pins, they'd prove nothing.
        pre_fix = _norm(
            "Filter to applicable standards by scope, then skip Superseded and "
            "Deprecated entries (history, not in force)."
        )
        self.assertNotIn("enforce only the current `Accepted` set", pre_fix)
        self.assertNotIn("Proposed", pre_fix)


class VerdictCitesStandardsByIdTest(unittest.TestCase):
    """AC #1 — the verdict cites which standards it verified, by id/path."""

    def test_agent_verdict_template_cites_standards_by_id_or_path(self):
        body = _norm(_read(REVIEWER_AGENT))
        # The verdict must reference the index/ADR id or path as its citation surface.
        # `index.json` is the always-read artifact named in the "Evidence I ran" line;
        # the `ADR-` id token is how an applicable standard is cited in the rollup.
        self.assertIn("index.json", body,
                      "agents/reviewer.md verdict must cite the standards it read "
                      "(docs/standards/index.json) — AC #1 cite-by-path.")
        self.assertIn("ADR-", body,
                      "agents/reviewer.md verdict must cite applicable standards by id "
                      "(ADR-NNN) — AC #1 cite-by-id.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
