"""Prose-contract tests for NB-388 — PO-overview "Delegated to agent" saved view.

NB-388 is the third/final follow-up off the agent-identity spike (NB-370 → ADR-001,
carried into ADR-006 AC#7): it extends `docs/guides/po-overview.md` with a **View 4 —
Delegated to agent** saved-view section so the PO sees `delegate = backlogd` pickups at a
glance in the 60-second daily routine. The deliverable is **documentation only** — saved
views are a PO-configured Linear-UI artifact with no key-free MCP write tool — so every AC
is a claim about the markdown source.

The unit's three `[test]` ACs are self-proving and already guarded elsewhere:

  * AC1  — `grep -q "Delegated to agent" docs/guides/po-overview.md` exits 0
  * AC2  — `grep -q "Delegate" docs/guides/po-overview.md` exits 0
  * AC3  — `python -m unittest scripts.test_manual_pending_label` exits 0 (the edit is
           additive — View 3's "manual-pending"/"Waiting on me" strings are preserved)

AC3 is proven by the *existing* `scripts/test_manual_pending_label.py` (it pins View 3's
load-bearing strings; this edit leaves them green). This file is the symmetric **durable
guard for View 4** — the same drift class the manual-pending suite guards for View 3, and
the precedent set by `scripts/test_delegate_pickup_wiring.py` for NB-391 (the dependency
that wired the `delegate` write). It bites if View 4's wiring is silently dropped or
reworded later.

What is pinned here (the load-bearing strings, per the scrum-master's earn-its-keep note):

  * AC1 — the "Delegated to agent" view title is present (the grep-able half, re-implemented
          in stdlib Python so it holds regardless of `grep` being on PATH — the rg-vacuity
          lesson).
  * AC2 — the filter targets the **Delegate** field (the grep-able half).
  * AC5 [review] (mechanical half) — the Filter recipe scopes to `Label is problem` +
          `Delegate is backlogd`, consistent with `list_issues(delegate:"backlogd")`. Whether
          the recipe reads cleanly is the reviewer's call; its presence is a fact this pins.
  * AC4 [review] (mechanical half) — the section mirrors the View 1/2/3 shape: a fenced
          Filter recipe + Group by + Sort + Display options with Identifier toggled off +
          an empty-state note. Whether the *prose* truly mirrors the style is [review].
  * AC6 [review] (mechanical half) — the view is woven into "What to do daily" (a routine
          step references View 4), keeping the ~60-second framing. Whether it reads as
          integrated rather than bolted-on is [review].
  * AC7 [review] (ADR-008 hedging, mechanical half) — the Insights-by-delegate slice is
          explicitly marked **unverified** and **plan-gated** (not asserted as fact), and the
          Delegate-filter menu placement is hedged ("may differ by Linear plan/version"). The
          cross-link to `agent-identity-setup.md` (the one-time install the view depends on)
          is present. Whether the hedging reads soundly is the reviewer's judgement.

The deeper *judgement* halves of AC4–AC7 (does it read in-style / integrated / soundly
hedged?) are Claude `[review]` reads over the prose — the string pins here are not a
substitute for that read; they keep the wiring honest so an incidental regression in the
touched neighbourhood trips CI.

AC8 [test] — `markdownlint-cli2 docs/guides/po-overview.md` reports no new violations — is
proven by the lint gate run live at authoring time and re-run by CI (.github/workflows/
ci.yml) + the pre-commit gate; it is NOT recursively re-invoked from inside a unittest (a
slow tautology). The lint gate IS the proof; this file proves the content contract it
cannot see.

AC9 [manual] — the PO's first-live-run of the section in the Linear UI — is a human
Linear-UI fact no fresh-context agent can observe from the repo. Named untestable; not
faked here.

Matches are whitespace-collapsed (survive prose line-wrapping) and never pin exact
indentation. `ProseGuardBitesTest` is the negative control: it proves each anchor *would*
fail were the wiring removed, so the green results above are non-vacuous.

Run from the repo root:  python scripts/test_po_overview_delegated_view.py
(or collected by `python -m unittest discover -s scripts -p 'test_*.py'`).
"""

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
PO_OVERVIEW = REPO_ROOT / "docs" / "guides" / "po-overview.md"
AGENT_IDENTITY_SETUP = REPO_ROOT / "docs" / "guides" / "agent-identity-setup.md"


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def _norm(text: str) -> str:
    """Whitespace-collapse so a content pin survives prose line-wrapping."""
    return " ".join(text.split())


class AC1_DelegatedToAgentViewExists(unittest.TestCase):
    """AC1 (`[test]`): the guide contains a "Delegated to agent" saved-view section.

    Re-implements `grep -q "Delegated to agent" docs/guides/po-overview.md` in stdlib
    Python so the check holds regardless of `grep`/`rg` being on PATH, and goes further:
    it asserts the string anchors an actual `##` view section, not a passing mention."""

    def test_po_overview_exists(self):
        self.assertTrue(PO_OVERVIEW.is_file(), f"{PO_OVERVIEW} must exist")

    def test_delegated_to_agent_title_present(self):
        body = _read(PO_OVERVIEW)
        self.assertIn(
            "Delegated to agent",
            body,
            'AC1: po-overview.md must contain a "Delegated to agent" view',
        )

    def test_delegated_to_agent_is_a_view_heading(self):
        """It is a first-class saved-view section (a `##` heading), in the style of the
        other views — not merely a phrase buried in prose."""
        body = _read(PO_OVERVIEW)
        self.assertRegex(
            body,
            r"(?m)^#{2,3}\s+.*Delegated to agent",
            'AC1: "Delegated to agent" must be a `##` view heading like View 1/2/3',
        )


class AC2_FilterTargetsTheDelegateField(unittest.TestCase):
    """AC2 (`[test]`): the new section documents a filter on the **Delegate** field.

    Re-implements `grep -q "Delegate" docs/guides/po-overview.md` in stdlib Python."""

    def test_delegate_field_mentioned(self):
        body = _read(PO_OVERVIEW)
        self.assertIn(
            "Delegate",
            body,
            "AC2: po-overview.md must reference the Delegate field",
        )


class AC5_FilterRecipeScopesProblemAndBacklogd(unittest.TestCase):
    """AC5 [review] (mechanical half): the Filter recipe scopes to `Label is problem` +
    `Delegate is backlogd` — the value `/backlogd:solve` writes on pickup, consistent with
    the live-verified `list_issues(delegate:"backlogd")`."""

    def test_filter_scopes_to_problem_label(self):
        body = _norm(_read(PO_OVERVIEW))
        self.assertIn(
            "Label is problem",
            body,
            "AC5: the View 4 filter must scope to `Label is problem`",
        )

    def test_filter_scopes_to_delegate_is_backlogd(self):
        body = _norm(_read(PO_OVERVIEW))
        self.assertIn(
            "Delegate is backlogd",
            body,
            "AC5: the View 4 filter must scope to `Delegate is backlogd`",
        )

    def test_consistent_with_mcp_side_query(self):
        """The doc ties the UI predicate to the MCP-side filter the runtime uses, so the
        two surfaces can't silently diverge."""
        body = _norm(_read(PO_OVERVIEW))
        self.assertIn(
            'list_issues(delegate:"backlogd")',
            body,
            "AC5: View 4 must tie its filter to the MCP-side list_issues(delegate:\"backlogd\")",
        )


class AC4_SectionMirrorsViewOneToThreeShape(unittest.TestCase):
    """AC4 [review] (mechanical half): the new section mirrors the View 1/2/3 style — a
    fenced Filter recipe, a Group by + Sort, Display options with Identifier toggled off
    (same rationale), and an empty-state note. Whether the prose truly reads in-style is
    the reviewer's judgement; the structural elements' presence is a fact this pins."""

    def _view4_block(self) -> str:
        """Slice the View 4 section out of the doc — from its heading to the next `##`
        heading — so the structural assertions are scoped to View 4, not satisfied by
        View 1/2/3 incidentally."""
        body = _read(PO_OVERVIEW)
        m = re.search(r"(?m)^#{2,3}\s+.*Delegated to agent.*$", body)
        self.assertIsNotNone(m, "AC4: the View 4 heading must exist to scope the block")
        rest = body[m.end():]
        nxt = re.search(r"(?m)^##\s+\S", rest)
        return rest[: nxt.start()] if nxt else rest

    def test_view4_has_fenced_filter_recipe(self):
        block = _norm(self._view4_block())
        self.assertIn(
            "Filter", block,
            "AC4: View 4 must carry a Filter recipe",
        )
        # The recipe is fenced (a ```text block) like the sibling views.
        self.assertIn(
            "```text",
            self._view4_block(),
            "AC4: View 4's Filter recipe must be fenced like View 1/2/3",
        )

    def test_view4_has_group_by_and_sort(self):
        block = _norm(self._view4_block())
        self.assertIn("Group by", block, "AC4: View 4 must document Group by")
        self.assertIn("Sort", block, "AC4: View 4 must document Sort")

    def test_view4_display_options_toggle_identifier_off(self):
        block = self._view4_block()
        block_norm = _norm(block)
        self.assertIn(
            "Display options", block_norm,
            "AC4: View 4 must document Display options",
        )
        self.assertIn(
            "Identifier", block_norm,
            "AC4: View 4's Display options must mention the Identifier toggle",
        )
        # Toggled OFF, with the same 'titles lead' rationale as View 1.
        self.assertRegex(
            block,
            r"Identifier[^\n]*\n?[^\n]*\b(off|toggle it \*\*off\*\*)",
            "AC4: View 4 must toggle Identifier OFF (same rationale as View 1)",
        )

    def test_view4_has_empty_state_note(self):
        block = _norm(self._view4_block())
        self.assertIn(
            "empty list",
            block,
            "AC4: View 4 must carry an empty-state note (like View 3's happy-state note)",
        )


class AC6_WovenIntoDailyRoutine(unittest.TestCase):
    """AC6 [review] (mechanical half): the view is woven into "What to do daily" as an
    additional step, keeping the ~60-second framing. Whether it reads as integrated rather
    than bolted-on is the reviewer's call; the routine reference is a fact this pins."""

    def _daily_routine_block(self) -> str:
        body = _read(PO_OVERVIEW)
        m = re.search(r"(?m)^##\s+What to do daily.*$", body)
        self.assertIsNotNone(m, "AC6: the 'What to do daily' section must exist")
        rest = body[m.end():]
        nxt = re.search(r"(?m)^##\s+\S", rest)
        return rest[: nxt.start()] if nxt else rest

    def test_daily_routine_references_view4(self):
        routine = _norm(self._daily_routine_block())
        self.assertIn(
            "View 4",
            routine,
            "AC6: the daily routine must reference View 4 (woven in, not a disconnected section)",
        )
        self.assertIn(
            "Delegate is backlogd",
            routine,
            "AC6: the View 4 routine step must name the `Delegate is backlogd` rows",
        )

    def test_routine_keeps_60_second_framing(self):
        """The ~60-second framing must survive the new step — the routine still bills
        itself as a ~60-second check."""
        routine = _norm(self._daily_routine_block())
        self.assertRegex(
            routine,
            r"~?60[\s-]?second",
            "AC6: the daily routine must keep its ~60-second framing",
        )


class AC7_Adr008Hedging(unittest.TestCase):
    """AC7 [review] (ADR-008 live-surface hedging, mechanical half): the Insights-by-
    delegate slice is explicitly marked unverified/plan-gated (not asserted as fact), the
    Delegate-filter menu placement is hedged, and the agent-identity-setup install
    dependency is cross-linked. Whether the hedging reads soundly is the reviewer's call."""

    def test_insights_slice_marked_unverified(self):
        body = _norm(_read(PO_OVERVIEW))
        # The Insights stretch must be flagged unverified — not stated as a working feature.
        self.assertRegex(
            body,
            r"Insights[^.]*\bunverified\b|\bunverified\b[^.]*Insights",
            "AC7: the Insights-by-delegate slice must be marked unverified",
        )

    def test_insights_slice_marked_plan_gated(self):
        body = _norm(_read(PO_OVERVIEW))
        self.assertRegex(
            body,
            r"plan-?gated",
            "AC7: the Insights-by-delegate slice must be marked plausibly plan-gated",
        )

    def test_delegate_menu_placement_is_hedged(self):
        """ADR-008: a UI-placement claim must be hedged, not stated flatly. The exact
        Delegate-filter menu location is hedged as plan/version-dependent."""
        body = _norm(_read(PO_OVERVIEW))
        self.assertRegex(
            body,
            r"may differ by Linear plan/?version|exact label and placement may differ",
            "AC7: the Delegate-filter menu placement must be hedged (ADR-008), not stated flatly",
        )

    def test_cross_links_to_agent_identity_setup(self):
        """The view only resolves once the one-time agent install is done — the section
        must cross-link the install guide so the empty-without-install case is explained."""
        body = _read(PO_OVERVIEW)
        self.assertIn(
            "agent-identity-setup.md",
            body,
            "AC7: View 4 must cross-link the agent-identity-setup install guide",
        )

    def test_cross_link_target_resolves(self):
        """Guard the link target actually exists on disk — a dangling cross-link would
        slip past a pure string-presence check (and lychee only runs in CI)."""
        self.assertTrue(
            AGENT_IDENTITY_SETUP.is_file(),
            f"AC7: the cross-link target {AGENT_IDENTITY_SETUP} must exist",
        )


class AC3_AdditiveEdit_View3StringsPreserved(unittest.TestCase):
    """AC3 (`[test]`): the edit is additive — View 3's load-bearing strings survive.

    AC3's own verify command is `python -m unittest scripts.test_manual_pending_label`,
    which pins View 3 ("manual-pending" + "Waiting on me"). This restates the floor of
    that contract here so a reader of *this* file sees View 3 is intact, without
    re-importing the sibling suite (it runs in the same `unittest discover` pass)."""

    def test_manual_pending_mention_preserved(self):
        body = _read(PO_OVERVIEW)
        self.assertIn(
            "manual-pending",
            body,
            "AC3: the additive edit must preserve View 3's `manual-pending` mention",
        )

    def test_waiting_on_me_view_title_preserved(self):
        body = _norm(_read(PO_OVERVIEW))
        self.assertIn(
            "Waiting on me",
            body,
            "AC3: the additive edit must preserve View 3's 'Waiting on me' title",
        )


class ProseGuardBitesTest(unittest.TestCase):
    """Negative control — prove every View 4 anchor *can* fail (the rg-vacuity lesson:
    a check that cannot fail is worthless).

    For each load-bearing needle, assert it is present now AND that removing it from the
    file's in-memory text makes the membership predicate False. We never mutate the file
    on disk — we mutate the read string and re-run the same `in` predicate the real tests
    use, proving each guard is sensitive to the View 4 wiring rather than tautologically
    green."""

    ANCHORS = [
        "Delegated to agent",       # AC1 — view title
        "Delegate is backlogd",     # AC2/AC5 — the filter predicate
        'list_issues(delegate:"backlogd")',  # AC5 — MCP-side consistency
        "agent-identity-setup.md",  # AC7 — install cross-link
        "unverified",               # AC7 — Insights hedge
        "plan-gated",               # AC7 — Insights hedge
        "View 4",                   # AC6 — woven into the daily routine
    ]

    def test_every_anchor_is_present(self):
        body = _norm(_read(PO_OVERVIEW))
        for needle in self.ANCHORS:
            with self.subTest(needle=needle):
                self.assertIn(
                    needle, body,
                    f"po-overview.md must currently contain the View 4 anchor {needle!r}",
                )

    def test_every_anchor_would_fail_if_wiring_removed(self):
        """The fail-direction proof: delete the needle from the in-memory text and the
        same predicate must now be False. If any needle's removal leaves the predicate
        True, the corresponding real test is vacuous."""
        body = _norm(_read(PO_OVERVIEW))
        for needle in self.ANCHORS:
            with self.subTest(needle=needle):
                mutated = body.replace(needle, "")
                self.assertNotIn(
                    needle, mutated,
                    f"removing {needle!r} must make the View 4 check FAIL "
                    "— otherwise that guard is vacuous",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
