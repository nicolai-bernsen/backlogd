"""Prose-contract tests for NB-391 — wire `delegate` pickup into /backlogd:solve (Tier 1).

Prose-and-policy unit: no runtime code ships, so every AC is a claim about the
**markdown source** of four skill files. Each mechanically-checkable AC is proven by a
content assertion on those files, one test per AC-string-shape claim so the proof maps
1:1 to the unit's acceptance criteria. This mirrors the repo's established prose-contract
precedent (`scripts/test_release_linear_summary.py`, `scripts/test_adr_006_*.py`).

Files under test (the developer's four changed files):
- `skills/solve/dispatch.md`            — step 1 carries the delegate write
- `skills/solve/identity.md`            — the write-shape + best-effort + leave-on-completion contract
- `skills/linear/SKILL.md`              — "Boundaries" reconciled (Tier-1 wired, Tier-2 guard kept)
- `skills/linear/references/linear-mcp.md` — `delegate` param line + rule-8 reconciled

ACs proven here (the testable contract):
- AC1 — dispatch.md step 1 sets `delegate:"backlogd"` in the SAME `save_issue` as the
        In Progress transition; one MCP write, no extra round-trip.
- AC2 — the write is documented best-effort: degrade gracefully (errors/no-ops) on an
        uninstalled workspace, pickup MUST NOT fail; attempt → swallow-and-note.
- AC3 — the agent is named by its CONFIGURED name (`"backlogd"`), never a hardcoded uuid.
- AC4 — completion default is stated EXPLICITLY: leave `delegate` set (additive, preserves
        the NB-388 audit signal), not cleared.
- AC5 [test] — SKILL.md "Boundaries" no longer instructs "default to leaving delegate
        unset"; re-runs the unit's own verify one-liner as the durable guard.
- AC6 [review] (grep-able half) — SKILL.md "Boundaries" states Tier-1 is WIRED into the
        solve pickup, AND the Tier-2 guard (agent sessions + webhooks out of scope) is
        still present. (Whether the reconciliation reads cleanly is the reviewer's call.)
- AC7 [review] (grep-able half) — both linear-mcp.md notes (the `save_issue` `delegate`
        param line and rule-8 "Pure MCP client") no longer say delegate is out of scope,
        while still fencing the Tier-2 surface out. (Prose-soundness is [review].)
- AC8 [review] (negative-scope, grep-able half) — the wiring stays "one MCP write / no
        extra round-trip" and the changed files introduce no server/webhook/`actor=app`
        token-handling language. (Whether the *diff* is truly so scoped is [review].)
- AC9 [test] — proven by live runs at test-authoring time (full `unittest discover` → 636
        OK; `markdownlint-cli2@0.22.1` → 0 errors on the 4 files) and re-run by CI; NOT
        recursively re-invoked from inside a unittest (that would be a slow tautology, and
        a literal-`\n` guard false-fails on linear-mcp.md, which documents that very token
        in rule 6). The unittest+lint gate is the proof; this file proves the AC1–AC8
        content contract those tools cannot see.

Run from the repo root:  python scripts/test_delegate_pickup_wiring.py
"""

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DISPATCH = REPO_ROOT / "skills" / "solve" / "dispatch.md"
IDENTITY = REPO_ROOT / "skills" / "solve" / "identity.md"
SKILL = REPO_ROOT / "skills" / "linear" / "SKILL.md"
LINEAR_MCP = REPO_ROOT / "skills" / "linear" / "references" / "linear-mcp.md"

CHANGED_FILES = [DISPATCH, IDENTITY, SKILL, LINEAR_MCP]


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


class AC1_DispatchStepOneCarriesTheDelegateWrite(unittest.TestCase):
    """AC1: dispatch.md step 1 sets `delegate:"backlogd"` as part of the In Progress
    transition, explicitly noting it can be the SAME save_issue call (one write, no
    extra round-trip)."""

    def test_dispatch_md_exists(self):
        self.assertTrue(DISPATCH.is_file(), f"{DISPATCH} must exist")

    def test_step1_sets_delegate_backlogd(self):
        body = _read(DISPATCH)
        self.assertRegex(
            body,
            r'delegate:\s*"backlogd"',
            'AC1: dispatch.md must instruct setting `delegate:"backlogd"` on pickup',
        )

    def test_step1_says_same_save_issue_call(self):
        """The 'same save_issue call' framing is the whole point — one MCP write, not a
        second round-trip. Require both the `save_issue` token and the same-call phrasing
        near the delegate instruction."""
        body = _read(DISPATCH)
        self.assertIn(
            "save_issue",
            body,
            "AC1: dispatch.md must reference the `save_issue` call the delegate rides on",
        )
        self.assertRegex(
            body,
            r"same\s+`?save_issue`?\s+call",
            "AC1: dispatch.md must say the delegate goes in the SAME `save_issue` call",
        )

    def test_step1_states_one_write_no_extra_round_trip(self):
        body = _read(DISPATCH)
        self.assertRegex(
            body,
            r"no\s+extra\s+round-?trip",
            "AC1: dispatch.md must state there is no extra round-trip (one MCP write)",
        )


class AC2_DelegateWriteIsBestEffort(unittest.TestCase):
    """AC2: the write is best-effort — an uninstalled workspace degrades gracefully
    (errors or no-ops) and the pickup MUST NOT fail; attempt, then swallow-and-note."""

    def test_identity_md_exists(self):
        self.assertTrue(IDENTITY.is_file(), f"{IDENTITY} must exist")

    def test_best_effort_named(self):
        body = _read(IDENTITY)
        self.assertRegex(
            body,
            r"[Bb]est-?effort",
            "AC2: identity.md must name the write `best-effort`",
        )

    def test_uninstalled_workspace_degrades_errors_or_noops(self):
        body = _read(IDENTITY)
        self.assertRegex(
            body,
            r"errors?\s+or\s+no-?ops",
            "AC2: identity.md must state an uninstalled workspace errors or no-ops",
        )

    def test_pickup_must_not_fail(self):
        """The load-bearing safety contract: the missing optional identity must never
        abort the pickup / In Progress transition."""
        body = _read(IDENTITY)
        self.assertRegex(
            body,
            r"never\b.*\b(fail|block)|must\s+\*?\*?never\*?\*?\s+block",
            "AC2: identity.md must state the pickup must NEVER fail/block on the delegate write",
        )

    def test_attempt_then_swallow_and_note(self):
        body = _read(IDENTITY)
        self.assertIn(
            "swallow-and-note",
            body,
            "AC2: identity.md must say attempt, then swallow-and-note on failure",
        )


class AC3_AgentNamedByConfiguredNameNotUuid(unittest.TestCase):
    """AC3: the agent is referred to by its configured name (`"backlogd"`), not a
    hardcoded app-user uuid, anywhere the write is described."""

    def test_configured_name_rule_stated(self):
        body = _read(IDENTITY)
        self.assertRegex(
            body,
            r"configured\s+name",
            "AC3: identity.md must say to use the agent's CONFIGURED name",
        )

    def test_no_hardcoded_uuid_rule_stated(self):
        """The rule explicitly forbids pasting a uuid."""
        body = _read(IDENTITY)
        self.assertRegex(
            body,
            r"never\s+a?\s*hardcoded\s+uuid|never\s+a?\s*hardcoded\s+app-user\s+uuid",
            "AC3: identity.md must say to NEVER use a hardcoded uuid",
        )

    def test_no_literal_uuid_pasted_in_changed_files(self):
        """Guard: no canonical 8-4-4-4-12 hex uuid is pasted anywhere the write is
        described (the `backlogd` app-user id is `ce2bed26-...`; the contract forbids
        hardcoding it). Catches a future edit that swaps the configured name for the
        literal id."""
        uuid_re = re.compile(
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
            r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
        )
        for path in (DISPATCH, IDENTITY):
            with self.subTest(file=path.name):
                self.assertIsNone(
                    uuid_re.search(_read(path)),
                    f"AC3: {path.name} must not paste a hardcoded app-user uuid for the delegate",
                )


class AC4_LeaveOnCompletionStatedExplicitly(unittest.TestCase):
    """AC4: the completion default is stated EXPLICITLY — leave `delegate` set (additive,
    preserves the NB-388 audit signal), rather than clearing it."""

    def test_leave_on_completion_default(self):
        body = _read(IDENTITY)
        # The default is to LEAVE it set on completion — and to NOT clear it.
        self.assertRegex(
            body,
            r"leave[^.]{0,40}set",
            "AC4: identity.md must state the default is to LEAVE delegate set on completion",
        )
        self.assertRegex(
            body,
            r"do\s+\*?\*?not\*?\*?\s+clear|not\s+clear(ing)?\s+it",
            "AC4: identity.md must state the default is NOT to clear delegate on completion",
        )

    def test_completion_default_references_audit_signal(self):
        """The reason the default is 'leave' is the NB-388 saved-view audit signal —
        the AC ties the decision to it explicitly."""
        body = _read(IDENTITY)
        self.assertIn(
            "NB-388",
            body,
            "AC4: identity.md must tie the leave-on-completion default to NB-388's saved view",
        )
        self.assertRegex(
            body,
            r"audit\s+signal",
            "AC4: identity.md must frame the preserved signal as an audit signal",
        )


class AC5_SkillBoundariesDropsGatedUnsetWording(unittest.TestCase):
    """AC5 [test]: SKILL.md "Boundaries" no longer instructs the reader to *default to
    leaving* `delegate` *unset*. This re-implements the unit's own verify one-liner as a
    durable regression guard (the gated-experiment phrase must not creep back)."""

    def test_skill_md_exists(self):
        self.assertTrue(SKILL.is_file(), f"{SKILL} must exist")

    def test_stale_default_to_leaving_unset_phrase_is_gone(self):
        """Mirrors the AC's verify command exactly:
        `sys.exit(1 if 'default to leaving' in t and 'unset' in t else 0)`.
        The stale gated-experiment instruction must be absent."""
        t = _read(SKILL)
        self.assertFalse(
            "default to leaving" in t and "unset" in t,
            "AC5: SKILL.md must no longer instruct 'default to leaving' delegate 'unset'",
        )


class AC6_SkillBoundariesReconciled(unittest.TestCase):
    """AC6 [review] (grep-able half): SKILL.md "Boundaries" instead states Tier-1
    `delegate` is now WIRED into the solve pickup, while the Tier-2 guard (agent sessions
    + webhooks out of scope) is preserved. Whether the reconciliation reads cleanly is the
    reviewer's judgement; the presence of both halves is a fact this pins."""

    def test_boundaries_states_tier1_wired_into_solve_pickup(self):
        body = _read(SKILL)
        self.assertRegex(
            body,
            r"wired\s+into\s+the\s+\n?\s*solve\s+pickup|wired\s+into\s+the\s+solve\s+pickup",
            "AC6: SKILL.md Boundaries must state Tier-1 delegate is WIRED into the solve pickup",
        )

    def test_boundaries_preserves_tier2_guard(self):
        """The Tier-2 guard — agent sessions + webhooks (the Agent Interaction Protocol /
        actor=app surface) — must still read as out of scope in Boundaries."""
        body = _read(SKILL)
        self.assertRegex(
            body,
            r"agent\s+sessions",
            "AC6: SKILL.md Boundaries must still name agent sessions (Tier-2 guard)",
        )
        self.assertRegex(
            body,
            r"webhooks?",
            "AC6: SKILL.md Boundaries must still name webhooks (Tier-2 guard)",
        )
        self.assertRegex(
            body,
            r"out of scope",
            "AC6: SKILL.md Boundaries must still mark the Tier-2 surface out of scope",
        )


class AC7_LinearMcpReferenceReconciled(unittest.TestCase):
    """AC7 [review] (grep-able half): both delegate notes in linear-mcp.md — the
    `save_issue` parameter-table line AND the rule-8 "Pure MCP client" paragraph — are
    reconciled so they no longer say delegate is out of scope, without claiming the Tier-2
    Agents-platform surface (sessions/webhooks/`actor=app`) is in scope."""

    def test_linear_mcp_md_exists(self):
        self.assertTrue(LINEAR_MCP.is_file(), f"{LINEAR_MCP} must exist")

    def test_delegate_param_line_no_longer_says_ignore_out_of_scope(self):
        """The old param line said: '`delegate`: ignore — that's the Agents-platform
        surface, out of scope.' The stale 'ignore … out of scope' instruction for the
        delegate param itself must be gone, replaced by the wired Tier-1 description."""
        body = _read(LINEAR_MCP)
        # The reconciled param line must now describe the Tier-1 usage.
        self.assertRegex(
            body,
            r"\*\*`delegate`:\*\*\s*set\s+to\s+the\s+configured\s+agent\s+name",
            "AC7: the `delegate` param line must now describe the Tier-1 wired usage "
            "(set to the configured agent name), not 'ignore'",
        )
        # And the specific stale instruction for the param must not survive.
        self.assertNotRegex(
            body,
            r"`delegate`:\*\*?\s*ignore",
            "AC7: the stale '`delegate`: ignore … out of scope' param instruction must be gone",
        )

    def test_rule8_pure_mcp_client_reconciled_to_name_delegate_as_used(self):
        """Rule 8 ("Pure MCP client") previously listed `delegate` among the out-of-scope
        Agents-platform surface. It must now carve `delegate` OUT of that ban as the one
        primitive backlogd uses, while keeping sessions/webhooks/actor=app out of scope."""
        body = _read(LINEAR_MCP)
        # The rule-8 region: from the "### 8." heading onward.
        m = re.search(r"###\s*8\.\s*Pure MCP client", body)
        self.assertIsNotNone(m, "AC7: rule 8 'Pure MCP client' heading must exist")
        rule8 = body[m.start():]
        # delegate is now described as IN use (not banned) within rule 8.
        self.assertRegex(
            rule8,
            r"`delegate`\s+field",
            "AC7: rule 8 must now reference the `delegate` field as the one primitive in use",
        )
        # The Tier-2 machinery is still fenced out within rule 8.
        self.assertRegex(
            rule8,
            r"agent\s+sessions",
            "AC7: rule 8 must keep agent sessions out of scope",
        )
        self.assertRegex(
            rule8,
            r"webhooks?",
            "AC7: rule 8 must keep webhooks out of scope",
        )

    def test_actor_app_is_only_ever_out_of_scope(self):
        """Negative guard for AC7/AC8: `actor=app` must never be described as in scope.
        Every mention in the reference sits inside an out-of-scope clause; assert the
        token never co-occurs with an in-scope claim on its own line."""
        body = _read(LINEAR_MCP)
        for line in body.splitlines():
            if "actor=app" in line:
                with self.subTest(line=line.strip()[:80]):
                    self.assertNotRegex(
                        line,
                        r"\bin\s+scope\b",
                        "AC7/AC8: `actor=app` must never be claimed in scope",
                    )


class AC8_ScopedToWiringPlusBoundaryReconciliation(unittest.TestCase):
    """AC8 [review] (negative-scope, grep-able half): the change is wiring + boundary
    reconciliation only — it must NOT introduce a server, a webhook listener, `actor=app`
    token handling, or a second MCP round-trip per pickup. Whether the *diff* is truly so
    scoped is the reviewer's call; these guards pin the load-bearing negatives in the prose
    the unit added."""

    def test_no_second_round_trip_language(self):
        """The wiring must read as one MCP write. No changed file may describe a SECOND
        round-trip per pickup as the contract."""
        for path in CHANGED_FILES:
            body = _read(path)
            with self.subTest(file=path.name):
                self.assertNotRegex(
                    body,
                    r"second\s+(MCP\s+)?round-?trip\s+per\s+pickup",
                    f"AC8: {path.name} must not introduce a second MCP round-trip per pickup",
                )

    def test_identity_states_zero_extra_round_trips(self):
        """The positive form of the same contract: the canonical write-shape section says
        zero extra round-trips."""
        body = _read(IDENTITY)
        self.assertRegex(
            body,
            r"zero\s+extra\s+round-?trips|no\s+extra\s+round-?trip",
            "AC8: identity.md must state the write costs zero extra round-trips",
        )

    def test_no_server_or_webhook_listener_introduced(self):
        """The delegate write must be described as needing no server / no webhook / no
        daemon — never as introducing one. Assert the 'no server' framing is present in
        the contract home and that no changed file instructs standing up a listener."""
        body = _read(IDENTITY)
        self.assertRegex(
            body,
            r"no\s+server",
            "AC8: identity.md must state the delegate write needs no server",
        )
        # No changed file may instruct running/standing-up a webhook server/listener.
        for path in CHANGED_FILES:
            with self.subTest(file=path.name):
                self.assertNotRegex(
                    _read(path),
                    r"(run|stand up|start|implement)\s+(a\s+)?webhook\s+(server|listener)",
                    f"AC8: {path.name} must not instruct standing up a webhook server/listener",
                )


# --- AC9 is proven by the gate, not re-run here --------------------------------
#
# AC9 [test] — `python -m unittest discover -s scripts -p "test_*.py"` exits 0 (636 OK,
# this file included) and `markdownlint-cli2@0.22.1` reports 0 errors on the 4 changed
# files. Both are run live at authoring time and re-run by CI (.github/workflows/ci.yml)
# and the pre-commit gate — they are NOT recursively re-invoked from inside a unittest
# (a slow tautology; and a literal-`\n` content guard false-fails on linear-mcp.md, which
# quotes that token in rule 6 to teach the footgun). The suite+lint ARE the proof.


# --- ACs whose SUBSTANCE is not mechanically testable (named, not faked) -------
#
# AC6 / AC7 / AC8 are [review] items: a string-grep proves the reconciled wording is
# *present* and the load-bearing negatives hold (asserted above), but whether the prose
# actually reads as a clean, non-contradictory reconciliation — and whether the real diff
# is scoped to wiring only — is the reviewer's judgement on the artifact, not a runner's.
# Those judgement halves are deliberately left to the gate's reviewer, not faked here.


if __name__ == "__main__":
    unittest.main(verbosity=2)
