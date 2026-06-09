"""Regression net for NB-437 — negotiated handoffs at the seams.

NB-437 (team cohesion 2/3) adds **bounded, logged, two-way** negotiation at two seams
without removing who-decides-what:

  1. dev->scope: a developer can formally **challenge an AC back to scope** via a new fifth
     first-class ``STATUS`` value ``DISPUTES_AC`` (the binding PO decision, chosen over a
     dispute comment / a ``NEEDS_CONTEXT`` extension). The orchestrator logs the challenge
     to scope/the PO, leaves the unit In Progress, stops, does **not** re-dispatch, and does
     **not** edit the AC. The developer only *emits* the challenge — never sets state,
     overrules scope, or merges.
  2. dev<->reviewer: a contested ``needs-changes`` verdict gets **exactly one** logged
     dev<->reviewer reconciliation (``skills/solve/gate.md`` §3.5) before it spends a rework
     round or escalates to the PO — extending the existing 2-round channel, bounded by a
     per-unit ``reconciled`` flag, explicitly NOT a new unbounded loop and NOT a
     ``gate_round``-spending re-dispatch.

Every AC on NB-437 is ``[review]`` or ``[manual]`` — there is **no** behaviour a process
can exercise here; the change is prose in skill/command/agent/docs markdown. So this file
does NOT try to prove "the orchestrator/developer/reviewer obeys the instruction" (that is
a tautology against the doc that *is* the instruction — see the same discipline in
``scripts/test_shared_problem_goal.py``, ``scripts/test_reviewer_standards_enforcement.py``,
``scripts/test_scrum_master_block_routing.py``). It pins the **load-bearing prose
invariants** the change introduced across the surfaces it touched, so an incidental reword
in any of them trips CI instead of silently un-wiring the contract. Each AC's class carries
a ``*_would_bite_on_the_pre_fix_wording`` guard proving the pins actually FIRE on synthetic
pre-NB-437 text (a four-value enum, no ``DISPUTES_AC``, no §3.5 reconciliation), so a green
here is never tautological.

The AC buckets, and how each is proven here:

  - AC1 ``[review]`` — a developer can formally challenge an AC back to scope, bounded and
    logged on Linear; the challenge surfaces to scope/the PO (who own the AC); the developer
    never overrules it or sets state. Structural pins: ``DISPUTES_AC`` is a first-class fifth
    STATUS in the developer's ``<Output_Format>`` enum + a ``Disputed-AC:`` report field
    (``agents/developer.md``) and its specialist clone (``.claude/agents/developer-docs.md``);
    the orchestrator's deterministic routing in ``skills/solve/capture.md`` leaves the unit
    In Progress, logs the challenge to scope/PO, does NOT re-dispatch, does NOT edit the AC;
    the routing is propagated to every orchestrator surface. ``DevChallengesAcStatusTest`` +
    ``DisputesAcRoutingTest`` pin it.

  - AC2 ``[review]`` — the reviewer and developer reconcile a contested verdict through
    exactly one structured exchange before PO escalation, extending the gate's 2-round
    channel, not a new unbounded loop. ``VerdictReconciliationTest`` pins ``gate.md`` §3.5:
    one logged exchange, bounded by a per-unit ``reconciled`` flag, runs only on a contested
    reviewer ``needs-changes`` (not a failing test), and explicitly does NOT increment
    ``gate_round``.

  - AC3 ``[review]`` — both handoffs stay two-way without removing who-decides-what, and the
    exchange is logged so it is inspectable. ``BothSeamsTwoWayTest`` pins the who-decides
    boundary on both seams (scope owns the AC; the reviewer owns the verdict; the developer
    owns the *how*; the PO owns intent/escalation) and that each exchange is logged.

  - AC4 ``[manual]`` — **No boundary loosened** (cross-cutting invariant, verify against
    ``skills/scrum/references/accountabilities.md``): the AC-challenge must not let the
    developer set state or overrule scope; the reconciliation must not let the reviewer
    self-mark or the developer merge its own work. Whether the change *as a whole* loosens a
    boundary is a holistic judgement against the accountabilities prose — named untestable in
    the report (the runner cannot assert "no boundary was loosened" without re-deriving the
    whole accountabilities model, a tautology). Its **structural half is pinned** here, the
    same discipline the repo uses for ``[manual]`` structural halves
    (``test_shared_problem_goal.py`` ``NoBoundaryLoosenedStructuralTest``):
    ``NoBoundaryLoosenedStructuralTest`` asserts the two negative-guards the change leans on
    are present (developer "never set state / overrule scope" on ``DISPUTES_AC``; reviewer
    "keeps sole authority over the verdict", developer "never self-marks or merges" in §3.5)
    AND that ``accountabilities.md`` still states the unchanged boundaries these seams must
    not cross (developers do NOT move workflow state; do NOT open PRs or merge). The PO's
    holistic "no boundary loosened" sign-off stays the ``[manual]`` step.

Run from the repo root:
    python -m pytest scripts/test_negotiated_handoffs.py
    python -m unittest discover -s scripts -p 'test_*.py'    # CI uses this
"""

import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

DEVELOPER_AGENT = REPO_ROOT / "agents" / "developer.md"
DEVELOPER_DOCS = REPO_ROOT / ".claude" / "agents" / "developer-docs.md"
CAPTURE = REPO_ROOT / "skills" / "solve" / "capture.md"
GATE = REPO_ROOT / "skills" / "solve" / "gate.md"
SPECIALISTS = REPO_ROOT / "docs" / "specialists.md"
ACCOUNTABILITIES = REPO_ROOT / "skills" / "scrum" / "references" / "accountabilities.md"
DISPATCH = REPO_ROOT / "skills" / "solve" / "dispatch.md"
WALK = REPO_ROOT / "skills" / "solve" / "walk.md"
SOLVE_CMD = REPO_ROOT / "commands" / "solve.md"
OPS = REPO_ROOT / "skills" / "solve" / "ops.md"
CLAIM_LOCK = REPO_ROOT / "skills" / "linear" / "claim-lock.md"

# The two surfaces that carry the developer STATUS enum line: the generic developer and its
# specialist clone. AC1's "DISPUTES_AC is a first-class STATUS value" is only proven if the
# enum holds in BOTH — a clone that drifts back to four values strands the contract — so they
# are checked as a set.
ENUM_SURFACES = (DEVELOPER_AGENT, DEVELOPER_DOCS)

# Every orchestrator surface the routing was propagated to. AC1's routing is only proven if
# the non-terminal stop holds across all of them, so they are checked as a set (a surface
# that still treats the enum as four-value would silently mis-route a challenge).
ROUTING_SURFACES = (CAPTURE, DISPATCH, WALK, SOLVE_CMD, OPS, CLAIM_LOCK)


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def _norm(text: str) -> str:
    """Whitespace-collapse so a content pin survives prose line-wrapping."""
    return " ".join(text.split())


class DevChallengesAcStatusTest(unittest.TestCase):
    """AC1 — a developer can formally challenge an AC back to scope via the first-class
    fifth STATUS ``DISPUTES_AC`` + its ``Disputed-AC:`` report field. The primitive shape is
    the binding PO decision (a STATUS value, not a comment or a NEEDS_CONTEXT extension)."""

    def test_disputes_ac_is_in_the_status_enum_on_both_developer_surfaces(self):
        # The enum line in <Output_Format> must spell all five values including DISPUTES_AC,
        # in both the generic developer and its specialist clone.
        for path in ENUM_SURFACES:
            with self.subTest(surface=path.name):
                body = _norm(_read(path))
                self.assertIn(
                    "STATUS: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT | DISPUTES_AC",
                    body,
                    f"{path.relative_to(REPO_ROOT)} <Output_Format> must carry the five-value "
                    f"STATUS enum line including DISPUTES_AC (AC1).",
                )

    def test_developer_report_has_a_disputed_ac_field(self):
        # The bounded challenge is carried in a dedicated, machine-readable report field —
        # the one AC + why it is wrong + what scope should reconsider.
        body = _norm(_read(DEVELOPER_AGENT))
        self.assertIn(
            "Disputed-AC: the one AC you challenge",
            body,
            "agents/developer.md report shape must carry a `Disputed-AC:` field for the one "
            "challenged AC (AC1).",
        )

    def test_developer_enum_count_says_five_not_four(self):
        # The binding PO decision makes DISPUTES_AC a *fifth* first-class value. The
        # <Final_Checklist> guard that forbids inventing an extra value must now name five
        # legal values and forbid a *sixth* (pre-NB-437 it forbade a *fifth*). This pins that
        # the enum count was widened, not that a sixth was smuggled in.
        body = _norm(_read(DEVELOPER_AGENT))
        self.assertIn(
            "Only the five shipped STATUS values are legal",
            body,
            "agents/developer.md <Final_Checklist> must state five legal STATUS values (AC1).",
        )
        self.assertIn(
            "never invent a sixth",
            body,
            "agents/developer.md <Final_Checklist> must forbid inventing a *sixth* STATUS "
            "value (five are legal) — AC1.",
        )

    def test_disputes_ac_is_a_formal_challenge_back_to_the_ac_owner(self):
        # AC1's substance: the value means "challenge the AC back to its owner", explicitly
        # *instead of* silently complying or silently drifting.
        body = _norm(_read(DEVELOPER_AGENT))
        self.assertIn(
            "instead of silently complying with a thin AC or silently drifting",
            body,
            "agents/developer.md must frame DISPUTES_AC as the in-contract alternative to "
            "silently complying or drifting (AC1).",
        )
        self.assertIn(
            "challenging the AC back to its owner",
            body,
            "agents/developer.md must describe DISPUTES_AC as challenging the AC back to its "
            "owner (AC1).",
        )

    def test_specialists_doc_records_disputes_ac_as_the_dev_to_scope_handoff(self):
        # The canonical STATUS contract in docs/specialists.md names DISPUTES_AC as the
        # bounded, logged dev->scope handoff at the AC seam — and distinguishes it from
        # NEEDS_CONTEXT ("I can act but the AC is wrong" vs "spec too thin to act").
        body = _norm(_read(SPECIALISTS))
        self.assertIn(
            "bounded, logged **dev→scope handoff at the AC seam**".replace("**", ""),
            body.replace("**", ""),
            "docs/specialists.md must record DISPUTES_AC as the bounded, logged dev->scope "
            "handoff at the AC seam (AC1).",
        )
        # The distinction from NEEDS_CONTEXT is load-bearing — collapsing them re-opens the
        # "thin spec" vs "wrong AC" ambiguity the PO's decision resolves.
        self.assertIn(
            "I *can* act, but I believe one AC is wrong".replace("*", ""),
            body.replace("*", ""),
            "docs/specialists.md must distinguish DISPUTES_AC ('I can act but the AC is "
            "wrong') from NEEDS_CONTEXT (AC1).",
        )

    def test_pins_would_bite_on_the_pre_fix_wording(self):
        # Anti-tautology: pre-NB-437 the enum was four-value with no DISPUTES_AC, no
        # Disputed-AC field, and the guard forbade inventing a *fifth*. Every AC1 pin must
        # FAIL on synthetic pre-fix text.
        pre_fix_enum = _norm(
            "STATUS: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT\n"
            "What I did: concrete actions taken\n"
            "Next: the blocker or the context gap"
        )
        self.assertNotIn(
            "STATUS: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT | DISPUTES_AC",
            pre_fix_enum,
        )
        self.assertNotIn("Disputed-AC: the one AC you challenge", pre_fix_enum)
        pre_fix_guard = _norm(
            "Only the four shipped STATUS values are legal "
            "(DONE / DONE_WITH_CONCERNS / BLOCKED / NEEDS_CONTEXT); never invent a fifth."
        )
        self.assertNotIn("Only the five shipped STATUS values are legal", pre_fix_guard)
        self.assertNotIn("never invent a sixth", pre_fix_guard)


class DisputesAcRoutingTest(unittest.TestCase):
    """AC1 (routing half) — the orchestrator logs the challenge to scope/the PO, leaves the
    unit In Progress, stops, does NOT re-dispatch, and does NOT edit the AC. Routing is
    propagated to every orchestrator surface, mechanical (not prose-heuristic)."""

    def test_capture_has_a_dedicated_disputes_ac_branch(self):
        body = _norm(_read(CAPTURE))
        # A dedicated section, not a table cell alone — the deterministic playbook.
        self.assertIn(
            "## `DISPUTES_AC` — the developer challenges an AC back to scope",
            body,
            "skills/solve/capture.md must carry a dedicated `## DISPUTES_AC` branch section "
            "(AC1 routing).",
        )

    def test_capture_branch_leaves_in_progress_logs_to_scope_no_redispatch_no_ac_edit(self):
        # The four mechanical moves of the routing, all load-bearing — drop any one and the
        # handoff stops being bounded/safe.
        body = _norm(_read(CAPTURE))
        # (a) leave In Progress — the developer does NOT set state, the orchestrator does NOT
        #     mark the AC resolved.
        self.assertIn(
            "The developer does **not** set state, and the orchestrator does **not** mark "
            "the AC resolved".replace("**", ""),
            body.replace("**", ""),
            "capture.md DISPUTES_AC branch must leave the unit In Progress with neither the "
            "developer setting state nor the orchestrator resolving the AC (AC1 routing).",
        )
        # (b) log the challenge to scope/the PO as the single inspectable record.
        self.assertIn(
            "Log the developer's `Disputed-AC:` challenge as a Linear comment",
            body,
            "capture.md DISPUTES_AC branch must log the challenge as a Linear comment to "
            "scope/the PO (AC1 routing).",
        )
        # (c) do NOT re-dispatch, and do NOT edit/drop/rewrite the AC yourself.
        self.assertIn(
            "do not edit, drop, or rewrite\nthe AC yourself".replace("\n", " "),
            body,
            "capture.md DISPUTES_AC branch must forbid the orchestrator editing/dropping/"
            "rewriting the AC (AC1 routing).",
        )
        self.assertIn(
            "Do not re-dispatch",
            body,
            "capture.md DISPUTES_AC branch must not re-dispatch the specialist (AC1 routing).",
        )

    def test_capture_branch_table_routes_disputes_ac_to_blocked_and_stays_in_progress(self):
        # The branch table row: stay In Progress, graph outcome `blocked`, log to scope/PO,
        # do NOT re-dispatch. The coarse graph fold must be present too.
        body = _norm(_read(CAPTURE))
        self.assertIn(
            "`DISPUTES_AC` → `blocked`",
            body,
            "capture.md must fold DISPUTES_AC onto the coarse `blocked` graph outcome (AC1 "
            "routing).",
        )

    def test_status_is_parsed_mechanically_against_a_five_value_enum(self):
        # The whole contract is that STATUS is matched mechanically against the enum, not
        # guessed from prose. capture.md's enum line + its "five-value" framing must hold.
        body = _norm(_read(CAPTURE))
        self.assertIn(
            "DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT | DISPUTES_AC",
            body,
            "capture.md must match STATUS against the five-value enum including DISPUTES_AC "
            "(AC1 routing).",
        )
        self.assertIn(
            "five-value enum",
            body,
            "capture.md must call the STATUS enum a five-value enum (AC1 routing).",
        )

    def test_claim_lock_releases_on_a_disputes_ac_stop(self):
        # A DISPUTES_AC stop is a clean exit — the claim-lock must release so the next solve
        # (after the AC owner responds) re-acquires cleanly.
        body = _norm(_read(CLAIM_LOCK))
        self.assertIn(
            "BLOCKED / NEEDS_CONTEXT / DISPUTES_AC stop",
            body,
            "skills/linear/claim-lock.md must release the claim on a DISPUTES_AC stop (AC1 "
            "routing).",
        )

    def test_routing_propagated_to_every_orchestrator_surface(self):
        # AC1's routing must be wired through every orchestrator surface that branches on
        # STATUS — a surface still on the four-value model would mis-route a challenge. Pin
        # that DISPUTES_AC appears in each.
        for path in ROUTING_SURFACES:
            with self.subTest(surface=path.name):
                body = _read(path)
                self.assertIn(
                    "DISPUTES_AC",
                    body,
                    f"{path.relative_to(REPO_ROOT)} must route the DISPUTES_AC STATUS "
                    f"(AC1 routing propagation).",
                )

    def test_routing_pins_would_bite_on_the_pre_fix_wording(self):
        # Anti-tautology: pre-NB-437 capture.md had four branches and no DISPUTES_AC section.
        # Prove the routing pins FIRE on synthetic pre-fix text.
        pre_fix = _norm(
            "Take the first line of the report and match it against "
            "DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT. "
            "NEEDS_CONTEXT: leave In Progress, post the context gap, do not re-dispatch."
        )
        self.assertNotIn(
            "DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT | DISPUTES_AC", pre_fix
        )
        self.assertNotIn("`DISPUTES_AC` → `blocked`", pre_fix)
        self.assertNotIn(
            "## `DISPUTES_AC` — the developer challenges an AC back to scope", pre_fix
        )


class VerdictReconciliationTest(unittest.TestCase):
    """AC2 — exactly one structured dev<->reviewer reconciliation on a contested verdict
    before it spends a rework round / escalates to the PO; extends the gate's existing
    2-round channel (gate.md), not a new unbounded loop."""

    def test_gate_has_a_dedicated_reconciliation_section(self):
        body = _norm(_read(GATE))
        self.assertIn(
            "## 3.5 Verdict reconciliation — one structured dev↔reviewer exchange",
            body,
            "skills/solve/gate.md must carry a dedicated §3.5 verdict-reconciliation section "
            "(AC2).",
        )

    def test_reconciliation_is_exactly_one_exchange_bounded_by_a_reconciled_flag(self):
        # The crux of AC2: *exactly one* exchange, tracked by a per-unit `reconciled` flag —
        # a second needs-changes skips it. Both halves are load-bearing.
        body = _norm(_read(GATE))
        self.assertIn(
            "exactly one** bounded, logged dev↔reviewer exchange".replace("**", ""),
            body.replace("**", ""),
            "gate.md §3.5 must run exactly one bounded dev<->reviewer exchange (AC2).",
        )
        self.assertIn(
            "Bounded to one exchange per unit",
            body,
            "gate.md §3.5 must bound reconciliation to one exchange per unit (AC2).",
        )
        self.assertIn(
            "per-unit\n`reconciled` flag".replace("\n", " "),
            body,
            "gate.md §3.5 must track the one exchange with a per-unit `reconciled` flag "
            "(AC2).",
        )

    def test_reconciliation_extends_the_2_round_channel_not_a_new_loop(self):
        # AC2 wording: it *extends* the existing 2-round rework channel, it does NOT open a
        # new unbounded loop — and the reconcile turn is NOT a gate_round-spending
        # re-dispatch.
        body = _norm(_read(GATE))
        self.assertIn(
            "extends** the existing 2-round channel, it does **not** open a new unbounded "
            "loop".replace("**", ""),
            body.replace("**", ""),
            "gate.md §3.5 must extend the 2-round channel without opening a new unbounded "
            "loop (AC2).",
        )
        self.assertIn(
            "do **not** increment `gate_round`".replace("**", ""),
            body.replace("**", ""),
            "gate.md §3.5 must state the reconcile turn does not increment gate_round (AC2).",
        )

    def test_reconciliation_runs_only_on_a_contested_reviewer_verdict_not_a_failing_test(self):
        # AC2 reconciles the *reviewer's verdict*, not an objective failing test (a failing
        # test is reconciled by fixing code). This scoping is load-bearing.
        body = _norm(_read(GATE))
        self.assertIn(
            "only when the reviewer's verdict is `needs-changes`",
            body,
            "gate.md §3.5 must run only on a reviewer `needs-changes` verdict (AC2).",
        )
        self.assertIn(
            "a failing test is reconciled by fixing the code, not by debating the reviewer",
            body,
            "gate.md §3.5 must state a failing test is reconciled by fixing code, not "
            "debating (AC2 scoping).",
        )

    def test_gate_frontmatter_advertises_the_one_shot_reconciliation(self):
        # The gate skill's description (its contract surface) must advertise the one logged
        # reconciliation before a round is spent / escalation — so the orchestrator loading
        # the skill sees it.
        body = _norm(_read(GATE))
        self.assertIn(
            "exactly one logged dev<->reviewer reconciliation before it spends a rework round "
            "or escalates",
            body,
            "gate.md frontmatter must advertise the one-shot reconciliation before a round "
            "is spent / escalation (AC2).",
        )

    def test_pins_would_bite_on_the_pre_fix_wording(self):
        # Anti-tautology: pre-NB-437 gate.md went straight from §3 (act on verdicts) to §4
        # (2-round cap) with no reconciliation. Prove every AC2 pin FIRES on synthetic
        # pre-fix text.
        pre_fix = _norm(
            "## 3. Act on gate verdicts. Combine the tester's failing list and the "
            "reviewer's verdict into a single decision. ## 4. Enforce the 2-round hard cap. "
            "On every needs-changes that would re-dispatch, increment gate_round."
        )
        self.assertNotIn(
            "## 3.5 Verdict reconciliation — one structured dev↔reviewer exchange", pre_fix
        )
        self.assertNotIn("Bounded to one exchange per unit", pre_fix)
        self.assertNotIn("reconciled` flag", pre_fix)
        self.assertNotIn(
            "only when the reviewer's verdict is `needs-changes`", pre_fix
        )


class BothSeamsTwoWayTest(unittest.TestCase):
    """AC3 — both handoffs stay two-way without removing who-decides-what: scope owns the
    AC, the PO owns priority/intent, the reviewer owns the verdict, the developer owns the
    *how*. The exchange is logged so it is inspectable."""

    def test_disputes_ac_seam_preserves_who_decides_and_is_logged(self):
        # The capture.md boundary note: two-way, removes no boundary, the exchange is logged
        # on the issue so it is inspectable. The note lives in a blockquote, so `_norm`
        # leaves a `>` marker at each line wrap — pin contiguous spans that stay within a
        # single physical line (the repo's proven blockquote-wrap technique), each still
        # load-bearing and pre-fix-biting.
        body = _norm(_read(CAPTURE)).replace("*", "")
        # The two-way-but-removes-no-boundary spine.
        self.assertIn(
            "DISPUTES_AC` is two-way",
            body,
            "capture.md DISPUTES_AC boundary note must state the seam is two-way (AC3).",
        )
        self.assertIn(
            "the developer only emits the",
            body,
            "capture.md DISPUTES_AC boundary note must state the developer only emits the "
            "challenge (AC3).",
        )
        # The who-decides cross-check (single physical line: "scope owns the AC, the PO owns").
        self.assertIn(
            "scope owns the AC, the PO owns",
            body,
            "capture.md DISPUTES_AC boundary note must keep scope=AC / PO=intent (AC3).",
        )
        # Logged + inspectable ("issue, so it is inspectable" is contiguous on one line).
        self.assertIn(
            "so it is inspectable",
            body,
            "capture.md DISPUTES_AC boundary note must state the exchange is logged and "
            "inspectable (AC3).",
        )

    def test_reconciliation_seam_preserves_who_decides_and_is_logged(self):
        # The gate.md §3.5 boundary note: two-way, removes no boundary — the reviewer still
        # owns the verdict, the developer owns only the *how*, the PO owns the escalation; the
        # whole exchange is logged on the work-log comments so it is inspectable. Blockquote,
        # so pin contiguous single-physical-line spans (repo blockquote-wrap technique).
        body = _norm(_read(GATE)).replace("*", "")
        # The reviewer keeps the verdict ("reviewer still owns the verdict" is contiguous).
        self.assertIn(
            "reviewer still owns the verdict",
            body,
            "gate.md §3.5 boundary note must keep the reviewer owning the verdict (AC3).",
        )
        # The PO keeps the escalation ("the PO still owns" is contiguous on one line).
        self.assertIn(
            "and the PO still owns",
            body,
            "gate.md §3.5 boundary note must keep the PO owning the escalation (AC3).",
        )
        # Logged on the two specialists' work-log comments ("on the two specialists' own
        # work-log comments, so it is" is contiguous on one line; "inspectable" wraps to next).
        self.assertIn(
            "logged on the two specialists' own work-log comments, so it is",
            body,
            "gate.md §3.5 boundary note must state the exchange is logged on the work-log "
            "comments and inspectable (AC3).",
        )

    def test_specialists_doc_frames_the_two_seams_as_symmetric_but_distinct(self):
        # AC3's whole point is that the two seams are two-way *and* sit at different
        # boundaries — neither dissolves who-decides-what. docs/specialists.md must say the
        # developer challenges the AC (scope's) and the dev+reviewer reconcile a verdict
        # (the reviewer's), and that neither dissolves who decides what.
        # The symmetric-seams sentence wraps across blockquote `>` markers, so pin contiguous
        # single-physical-line spans (repo blockquote-wrap technique).
        body = _norm(_read(SPECIALISTS)).replace("*", "")
        self.assertIn(
            "the developer challenges the AC (scope's), the",
            body,
            "docs/specialists.md must frame the developer-challenges-AC half of the seams "
            "(AC3).",
        )
        self.assertIn(
            "reconcile a verdict (the reviewer's)",
            body,
            "docs/specialists.md must frame the dev+reviewer-reconcile-verdict half of the "
            "seams (AC3).",
        )
        self.assertIn(
            "and neither dissolves who",
            body,
            "docs/specialists.md must state neither seam dissolves who decides what (AC3).",
        )

    def test_reviewer_has_no_disputes_ac_row_its_pushback_is_the_reconciliation(self):
        # AC3 boundary integrity: DISPUTES_AC is developer-only; the reviewer's pushback seam
        # is the §3.5 reconciliation, not an AC challenge. The two channels must not be
        # conflated — that would let the reviewer challenge the AC (scope's), crossing a
        # boundary.
        body = _norm(_read(SPECIALISTS))
        self.assertIn(
            "`DISPUTES_AC` is developer-emitted; the reviewer has its own pushback seam",
            body,
            "docs/specialists.md must keep DISPUTES_AC developer-emitted with the reviewer's "
            "own pushback seam (AC3).",
        )
        # The "no row maps to DISPUTES_AC" sentence wraps across a blockquote `>` marker
        # (the backtick `DISPUTES_AC` opens the next quoted line), so `_norm` leaves the `>`
        # between "to" and the backtick. Assert the two contiguous halves separately — the
        # same blockquote-wrap technique the repo's other prose tests use — so the pin still
        # bites the pre-fix wording without depending on the wrap.
        flat = body.replace("**", "")
        self.assertIn(
            "verdict vocabulary deliberately has no row that maps to",
            flat,
            "docs/specialists.md must state the reviewer's verdict vocabulary has no row "
            "mapping to DISPUTES_AC (AC3).",
        )
        self.assertIn(
            "when the reviewer disagrees about a verdict, its bounded pushback is the",
            flat.replace("*", ""),
            "docs/specialists.md must route the reviewer's verdict disagreement to the "
            "reconciliation, not an AC challenge (AC3).",
        )

    def test_pins_would_bite_on_the_pre_fix_wording(self):
        # Anti-tautology: pre-NB-437 neither boundary note nor the symmetric-seams framing
        # existed. Prove the AC3 pins FIRE on synthetic pre-fix text.
        pre_fix_capture = _norm(
            "NEEDS_CONTEXT: leave the unit in its started state, post the context gap as a "
            "Linear comment for the PO, do not re-dispatch."
        )
        self.assertNotIn(
            "scope owns the AC, the PO owns priority/intent, the developer owns the how",
            pre_fix_capture.replace("*", ""),
        )
        pre_fix_gate = _norm(
            "## 4. Enforce the 2-round hard cap. The counter is per-unit and lives in the "
            "scrum-master's working context across the loop."
        )
        self.assertNotIn("the reviewer still owns the verdict", pre_fix_gate)
        self.assertNotIn("the PO still owns the escalation", pre_fix_gate)


class NoBoundaryLoosenedStructuralTest(unittest.TestCase):
    """AC4 ``[manual]`` — structural half only. The holistic "no boundary was loosened"
    sign-off is a PO judgement against accountabilities.md (named untestable in the report).
    What is pinnable: the two negative-guards the change leans on are present on each seam,
    and accountabilities.md still states the unchanged developer boundaries these seams must
    not cross."""

    def test_disputes_ac_guard_blocks_developer_setting_state_or_overruling_scope(self):
        # The developer's <Failure_Modes_To_Avoid> must guard that DISPUTES_AC never lets the
        # developer overrule scope, set state, drop/rewrite the AC, transition, or merge.
        body = _norm(_read(DEVELOPER_AGENT))
        self.assertIn(
            "Using `DISPUTES_AC` to overrule scope or to set state",
            body,
            "agents/developer.md must name 'using DISPUTES_AC to overrule scope or set "
            "state' as a failure mode (AC4 boundary).",
        )
        self.assertIn(
            "it never lets you drop the AC, re-write it\nyourself, transition the issue, or "
            "merge".replace("\n", " "),
            body,
            "agents/developer.md must forbid DISPUTES_AC dropping/rewriting the AC, "
            "transitioning, or merging (AC4 boundary).",
        )

    def test_reconciliation_guard_blocks_reviewer_self_mark_and_developer_merge(self):
        # The §3.5 guards: the reviewer keeps SOLE authority over the verdict (never forced to
        # flip; the developer cannot overrule it), and the developer states its case but
        # never self-marks or merges.
        body = _norm(_read(GATE))
        self.assertIn(
            "The reviewer keeps sole\nauthority over the verdict".replace("\n", " "),
            body,
            "gate.md §3.5 must keep the reviewer's sole authority over the verdict — no "
            "self-mark by the developer (AC4 boundary).",
        )
        self.assertIn(
            "it states its case but never self-marks or merges",
            body,
            "gate.md §3.5 must forbid the developer self-marking or merging in reconciliation "
            "(AC4 boundary).",
        )
        self.assertIn(
            "does **not** set state, does\n**not** mark the unit resolved, and does **not** "
            "merge".replace("**", "").replace("\n", " "),
            body.replace("**", ""),
            "gate.md §3.5 must state the developer does not set state / mark resolved / merge "
            "in the rebuttal (AC4 boundary).",
        )

    def test_accountabilities_developer_boundaries_the_seams_must_not_cross_are_intact(self):
        # The cross-cutting invariant: these seams must not let developers move workflow state
        # nor open PRs / merge. Those does-NOT boundaries live in accountabilities.md
        # (untouched by this change). Pin that they still read as they must — a future edit
        # that loosens either trips here.
        body = _norm(_read(ACCOUNTABILITIES))
        self.assertIn(
            "Move workflow state (scrum-master via API or git event)",
            body,
            "accountabilities.md must keep the developer 'does NOT move workflow state' "
            "boundary (AC4 cross-cutting invariant).",
        )
        self.assertIn(
            "Open PRs or merge — that is `/backlogd:solve` / `/backlogd:review`",
            body,
            "accountabilities.md must keep the developer 'does NOT open PRs or merge' "
            "boundary (AC4 cross-cutting invariant).",
        )

    def test_pins_would_bite_if_guards_were_dropped(self):
        # Anti-tautology: if a reword stripped the DISPUTES_AC overrule-guard or the §3.5
        # self-mark/merge guard, the structural pins above must FAIL. Prove they bite on
        # guard-free synthetic bodies.
        guardless_developer = _norm(
            "DISPUTES_AC: you believe one AC is wrong and want scope to reconsider it. "
            "Emit the challenge in Disputed-AC and stop."
        )
        self.assertNotIn(
            "Using `DISPUTES_AC` to overrule scope or to set state", guardless_developer
        )
        guardless_gate = _norm(
            "## 3.5 Verdict reconciliation. Offer the developer one rebuttal, the reviewer "
            "reconsiders once, then act on the reconciled verdict."
        )
        self.assertNotIn(
            "it states its case but never self-marks or merges", guardless_gate
        )
        # And the accountabilities boundary pins must bite on a loosened synthetic body.
        loosened_accountab = _norm(
            "Developers own the technical solution and may move their own issue to In Review "
            "and open the PR when the work is done."
        )
        self.assertNotIn(
            "Move workflow state (scrum-master via API or git event)", loosened_accountab
        )
        self.assertNotIn(
            "Open PRs or merge — that is `/backlogd:solve` / `/backlogd:review`",
            loosened_accountab,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
