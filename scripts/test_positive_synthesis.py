"""Regression net for NB-438 — positive synthesis in retro + status, data-derived.

NB-438 (team cohesion 3/3 of NB-431) gives the scrum-master a *positive* valence: the
retro (primary home) and the standup (lighter, gated touch) narrate **what the team did
well and how it is improving over the scope**, every claim grounded in the execution graph
(`scripts/graph.py report --json`), never invented praise.

Three ACs are ``[review]`` (the design contract) and one is ``[manual]`` (no boundary
loosened) — there is **no** new runtime behaviour to exercise; the change is prose in two
commands + the retro skill. So, exactly like its siblings
``scripts/test_shared_problem_goal.py`` (NB-436) and
``scripts/test_negotiated_handoffs.py`` (NB-437), this file does NOT try to prove "the
scrum-master obeys the instruction" (a tautology against the doc that *is* the
instruction). It pins the **load-bearing prose invariants** the change introduced, so an
incidental reword in any touched surface trips CI instead of silently un-wiring the
positive-synthesis contract. Each AC class carries a ``*_would_bite_on_the_pre_fix_wording``
guard proving the pins actually FIRE on synthetic pre-NB-438 text, so a green here is never
tautological.

The change also makes a *substantive* claim that a runner CAN verify directly: every
positive signal the contract cites (``rework.rate``, ``dispatches.solved`` + the rates,
``dispatch_to_pr_ms.p50``, ``fanout.parallel_runs`` / ``parallel_rate``, ``by_area``) is a
real top-level key of the live reducer — so "derived from `report --json`, **not
invented**" is provable against ``graph.metrics()`` itself, not only against the prose.
``PositiveSignalsAreRealGraphKeysTest`` does exactly that (the non-prose backbone of AC1).

The AC buckets, and how each is proven here:

  - AC1 ``[review]`` — ``/backlogd:retro`` narrates positive synthesis (what the team did
    well / how it is improving over the scope), **derived from `report --json`, not
    invented**; the retro is the primary home. Pinned in both retro surfaces:
    ``skills/retro/SKILL.md`` grows a **property 5 (positive synthesis)** mapping each
    positive signal to the graph key it reads + a **What went well** block in the summary
    shape; ``commands/retro.md`` wires it as **step 4b** reading the SAME `report --json`
    as step 3 (never re-derived). ``RetroNarratesPositiveSynthesisTest`` pins the prose;
    ``PositiveSignalsAreRealGraphKeysTest`` proves the cited keys are real, so the synthesis
    is genuinely data-derived.

  - AC2 ``[review]`` — ``/backlogd:status`` carries a **lighter** data-derived positive
    signal, **gated** by default (milestone-close / real signal, silent on a routine
    standup; PO may widen), retro stays the primary home.
    ``StatusCarriesLighterGatedSignalTest`` pins ``commands/status.md`` step 4f: the
    `Bright spot:` line, the real-signal gate (omitted on a routine standup), the
    PO-may-widen escape hatch, and that it is a pure local read (no `save_*` write).

  - AC3 ``[review]`` — **every positive claim cites its graph/Linear evidence** (no
    ungrounded praise); on a sparse graph it leans on Linear and says so.
    ``EveryPositiveClaimCitesEvidenceTest`` pins the cite-or-don't-write discipline, the
    delta-only-when-comparable rule, and the sparse-graph "lean on Linear and say so"
    clause across the surfaces that carry it.

  - AC4 ``[manual]`` — **No boundary loosened** (cross-cutting invariant, verify against
    ``skills/scrum/references/accountabilities.md``): synthesis is the scrum-master
    narrating observed data; it must not let the reviewer self-mark, nor convert the gate
    into self-congratulation, nor let the scrum-master claim credit for a product call.
    Whether the change *as a whole* loosens a boundary is a holistic judgement against the
    accountabilities prose — **named untestable in the tester report** (the runner cannot
    assert "no boundary was loosened" without re-deriving the whole accountabilities model,
    a tautology). Its **structural half is pinned** here, the same discipline the siblings
    use: ``NoBoundaryLoosenedStructuralTest`` asserts the three boundary clauses the change
    leans on are present in BOTH the retro and status surfaces (reviewer never self-marks /
    appears; the retro/status runs no gate so no self-congratulation; narrates execution
    metrics, never claims credit for a product call) AND that ``accountabilities.md`` still
    states the unchanged scrum-master boundaries this narration must not cross (does NOT
    make product decisions; does NOT speak as the PO). The PO's holistic sign-off stays the
    ``[manual]`` step.

Run from the repo root:
    python -m pytest scripts/test_positive_synthesis.py
    python -m unittest discover -s scripts -p 'test_*.py'    # CI uses this
"""

import pathlib
import sys
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

RETRO_SKILL = REPO_ROOT / "skills" / "retro" / "SKILL.md"
RETRO_CMD = REPO_ROOT / "commands" / "retro.md"
STATUS_CMD = REPO_ROOT / "commands" / "status.md"
ACCOUNTABILITIES = REPO_ROOT / "skills" / "scrum" / "references" / "accountabilities.md"

# The positive-synthesis discipline is carried on three surfaces. AC3's "every positive
# claim cites its evidence" is only proven if the cite-or-don't-write rule holds in the
# primary home (the retro skill) AND each command home echoes it — a surface that drifts
# back to ungrounded praise strands the contract — so the no-praise guard is checked as a
# set across all three.
SYNTHESIS_SURFACES = (RETRO_SKILL, RETRO_CMD, STATUS_CMD)


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def _norm(text: str) -> str:
    """Whitespace-collapse so a content pin survives prose line-wrapping."""
    return " ".join(text.split())


class RetroNarratesPositiveSynthesisTest(unittest.TestCase):
    """AC1 — /backlogd:retro narrates positive synthesis (what the team did well / how it
    is improving over the scope), derived from `report --json`, not invented. The retro is
    the primary home: property 5 in the skill + step 4b in the command, both reading the
    same reducer surface the retro already consumes."""

    def test_skill_has_a_positive_synthesis_property(self):
        body = _norm(_read(RETRO_SKILL))
        self.assertIn(
            "### 5. Positive synthesis — what the team did well, data-derived and cited",
            body,
            "skills/retro/SKILL.md must carry a property 5 'Positive synthesis' section "
            "(AC1 — the primary home).",
        )
        # The substance: what the team did well AND how it is improving over the scope.
        self.assertIn(
            "what the team did well and how it is improving over the scope",
            body,
            "skills/retro/SKILL.md property 5 must frame synthesis as what the team did "
            "well and how it is improving over the scope (AC1).",
        )

    def test_skill_derives_synthesis_from_report_json_not_invented(self):
        # The crux of AC1: derived from the SAME report --json (property 2), never a new
        # metric, never re-derived math — "not invented".
        body = _norm(_read(RETRO_SKILL))
        self.assertIn(
            "Derive it from the same `report --json` you already read (property 2) — do "
            "not invent a metric, and never re-derive the math.",
            body,
            "skills/retro/SKILL.md property 5 must derive the synthesis from the same "
            "`report --json` (property 2), not invent a metric (AC1).",
        )

    def test_skill_summary_carries_a_what_went_well_block_above_patterns(self):
        # The retro summary body shape grows a "What went well" block, placed ABOVE the
        # patterns/gaps so the wins are read before the fixes — the visible positive home.
        body = _norm(_read(RETRO_SKILL))
        self.assertIn(
            "What went well",
            body,
            "skills/retro/SKILL.md summary shape must carry a 'What went well' block (AC1).",
        )
        self.assertIn(
            "It sits **above** the patterns/gaps",
            body,
            "skills/retro/SKILL.md must place the 'What went well' block above the "
            "patterns/gaps (AC1 — wins read before fixes).",
        )

    def test_command_wires_synthesis_as_step_4b_reading_the_same_report(self):
        body = _norm(_read(RETRO_CMD))
        self.assertIn(
            "## 4b. Synthesize what the team did well (positive synthesis)",
            body,
            "commands/retro.md must wire positive synthesis as step 4b (AC1).",
        )
        # It reads the SAME report --json already read in step 3 — never re-derives.
        # (`_norm` already collapses the line break + indent to a single space, so pin the
        # exact normalized span: "step 3** — do not re-derive them".)
        self.assertIn(
            "Read the positive signals off the *same* `report --json` you already read in "
            "step 3** — do not re-derive them",
            body,
            "commands/retro.md step 4b must read the same `report --json` as step 3, not "
            "re-derive (AC1).",
        )

    def test_pins_would_bite_on_the_pre_fix_wording(self):
        # Anti-tautology: pre-NB-438 the retro had four properties (all gating) and no
        # "What went well" block; the command went straight from step 4 to step 5. Every
        # AC1 pin must FAIL on synthetic pre-fix text.
        pre_fix_skill = _norm(
            "### 4. Classify + calibrate — load-bearing only; propose, don't prioritize. "
            "## The candidate improvement issue — exact shape."
        )
        self.assertNotIn(
            "### 5. Positive synthesis — what the team did well, data-derived and cited",
            pre_fix_skill,
        )
        self.assertNotIn(
            "what the team did well and how it is improving over the scope", pre_fix_skill
        )
        self.assertNotIn("It sits **above** the patterns/gaps", pre_fix_skill)
        pre_fix_cmd = _norm(
            "## 4. File the load-bearing improvements as candidates. ## 5. Post the retro "
            "summary and report."
        )
        self.assertNotIn(
            "## 4b. Synthesize what the team did well (positive synthesis)", pre_fix_cmd
        )


class PositiveSignalsAreRealGraphKeysTest(unittest.TestCase):
    """AC1 (substantive half) — "derived from `report --json`, **not invented**" is
    provable against the live reducer: every positive signal the contract cites is a real
    top-level key of ``graph.metrics()``. If a future edit cited a key the reducer does not
    emit, the synthesis would be ungrounded (inventing a metric) and this test would FAIL —
    so it guards the data-derived claim directly, not only via the prose."""

    @classmethod
    def setUpClass(cls):
        # Import the reducer the same way test_retro.py / test_graph.py do, so this works
        # regardless of how the discover runner sets cwd.
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
        import graph  # noqa: E402

        # Read over an empty edge set so the assertion is about the *shape* of the reducer
        # surface (the keys the contract reads), independent of any accumulated store.
        cls.metrics = graph.metrics(edges=[])

    def test_rework_rate_is_a_real_key(self):
        # Clean-gate streak — the contract reads `rework.rate`.
        self.assertIn("rework", self.metrics)
        self.assertIn(
            "rate",
            self.metrics["rework"],
            "graph.metrics()['rework'] must expose 'rate' — the clean-gate signal the "
            "positive synthesis cites (AC1 derived-not-invented).",
        )

    def test_dispatches_solved_and_rates_are_real_keys(self):
        # High solved share — the contract reads `dispatches.solved` vs `total` with the
        # partial/blocked rates.
        self.assertIn("dispatches", self.metrics)
        for key in ("solved", "total", "partial_rate", "blocked_rate"):
            self.assertIn(
                key,
                self.metrics["dispatches"],
                f"graph.metrics()['dispatches'] must expose '{key}' — a positive-synthesis "
                f"signal (AC1 derived-not-invented).",
            )

    def test_dispatch_to_pr_p50_is_a_real_key(self):
        # Faster dispatch->PR — the contract reads `dispatch_to_pr_ms.p50`.
        self.assertIn("dispatch_to_pr_ms", self.metrics)
        self.assertIn(
            "p50",
            self.metrics["dispatch_to_pr_ms"],
            "graph.metrics()['dispatch_to_pr_ms'] must expose 'p50' — the loop-speed "
            "positive signal (AC1 derived-not-invented).",
        )

    def test_fanout_parallel_keys_are_real(self):
        # The team working in parallel — the contract reads `fanout.parallel_runs` /
        # `parallel_rate`. These are the freshest keys the contract leans on, so pin them.
        self.assertIn("fanout", self.metrics)
        for key in ("parallel_runs", "parallel_rate"):
            self.assertIn(
                key,
                self.metrics["fanout"],
                f"graph.metrics()['fanout'] must expose '{key}' — the parallelism positive "
                f"signal the contract cites (AC1 derived-not-invented).",
            )

    def test_by_area_is_a_real_key(self):
        # A clean area — the contract reads a `by_area` row.
        self.assertIn(
            "by_area",
            self.metrics,
            "graph.metrics() must expose 'by_area' — the clean-area positive signal (AC1 "
            "derived-not-invented).",
        )


class StatusCarriesLighterGatedSignalTest(unittest.TestCase):
    """AC2 — /backlogd:status carries a *lighter* data-derived positive signal, GATED by
    default (milestone-close / real signal, silent on a routine standup; PO may widen), and
    the retro stays the primary home. Pinned in commands/status.md step 4f."""

    def test_status_has_a_gated_positive_signal_step(self):
        body = _norm(_read(STATUS_CMD))
        self.assertIn(
            "### 4f. Print a lighter data-derived positive signal (gated)",
            body,
            "commands/status.md must carry a step 4f for a lighter, gated positive signal "
            "(AC2).",
        )
        # It is the *lighter touch* and the retro is the *primary home* — the AC's framing.
        self.assertIn(
            "The **retro is the primary home**",
            body,
            "commands/status.md step 4f must keep the retro as the primary home (AC2 — "
            "status is the lighter touch).",
        )

    def test_status_signal_is_gated_silent_on_a_routine_standup(self):
        # The gate is the crux of AC2's "lighter": real signal only, silent otherwise — not
        # emitted noisily on every standup.
        body = _norm(_read(STATUS_CMD))
        self.assertIn(
            "Default — emit only on real signal.",
            body,
            "commands/status.md step 4f must default to emitting only on real signal (AC2).",
        )
        self.assertIn(
            "On a routine standup with nothing notable,\n  **print nothing**".replace(
                "\n ", ""
            ),
            body,
            "commands/status.md step 4f must print nothing on a routine standup (AC2 — "
            "gated, not noisy).",
        )
        # The line is explicitly omitted in both the §5 standup template note and the banner.
        self.assertIn(
            "omitted entirely on a routine standup",
            body,
            "commands/status.md must state the Bright spot line is omitted on a routine "
            "standup (AC2).",
        )

    def test_status_signal_carries_the_po_may_widen_escape_hatch(self):
        # AC2 says "Default (PO may widen)" — the doc must keep that escape hatch so the
        # signal-gated default is explicitly provisional.
        body = _norm(_read(STATUS_CMD))
        self.assertIn(
            "The PO may widen\n  this".replace("\n ", ""),
            body,
            "commands/status.md step 4f must record that the PO may widen the gate (AC2 "
            "'Default — PO may widen').",
        )

    def test_status_signal_is_a_pure_local_read_no_write(self):
        # The developer corrected the AC Note's premise: status did NOT previously read
        # `report --json`. The newly-added read must be a pure local read that adds no
        # `save_*` write — load-bearing so the lighter touch does not become a mutation.
        # The clauses live in the status banner blockquote, so `_norm` leaves a `>` at each
        # line wrap; pin contiguous single-physical-line spans (the repo's proven
        # blockquote-wrap technique), each still load-bearing and pre-fix-biting.
        body = _norm(_read(STATUS_CMD))
        self.assertIn(
            "pure **read** of the local execution graph",
            body,
            "commands/status.md must state step 4f is a pure read of the local graph (AC2).",
        )
        self.assertIn(
            "it never writes the graph",
            body,
            "commands/status.md must state step 4f never writes the graph (AC2 — pure read).",
        )
        self.assertIn(
            "no `save_*` write",
            body,
            "commands/status.md must state step 4f adds no `save_*` write (AC2 — lighter "
            "touch, not a mutation).",
        )

    def test_status_prints_a_cited_bright_spot_line(self):
        # The standup-scale echo is a single cited `Bright spot:` line in the §5 template.
        body = _norm(_read(STATUS_CMD))
        self.assertIn(
            "Bright spot: {one cited positive signal from §4f}",
            body,
            "commands/status.md §5 template must carry the cited `Bright spot:` line (AC2).",
        )

    def test_pins_would_bite_on_the_pre_fix_wording(self):
        # Anti-tautology: pre-NB-438 status.md went straight from §4 (forecast block) to
        # the block-replacement rules with no step 4f, and its §5 template had no Bright
        # spot line. Every AC2 pin must FAIL on synthetic pre-fix text.
        pre_fix = _norm(
            "The console row and the Linear block must always carry the same numbers. "
            "### Block-replacement rules. Forecast: velocity {v}/day, queue {q}. "
            "Standup ({n} active problems)"
        )
        self.assertNotIn(
            "### 4f. Print a lighter data-derived positive signal (gated)", pre_fix
        )
        self.assertNotIn("Bright spot: {one cited positive signal from §4f}", pre_fix)
        self.assertNotIn("Default — emit only on real signal.", pre_fix)


class EveryPositiveClaimCitesEvidenceTest(unittest.TestCase):
    """AC3 — every positive claim cites its graph/Linear evidence (no ungrounded praise);
    on a sparse graph it leans on Linear and says so. The same data-grounded discipline the
    rest of the retro already holds — pinned across the surfaces that carry it."""

    def test_skill_requires_every_positive_claim_to_cite_its_evidence(self):
        # The primary home's cite-or-don't-write rule — the positive-valence twin of the
        # no-flood / no-self-marking discipline.
        body = _norm(_read(RETRO_SKILL))
        self.assertIn(
            "Every positive claim cites its evidence — no ungrounded praise.",
            body,
            "skills/retro/SKILL.md property 5 must require every positive claim to cite its "
            "evidence (AC3).",
        )
        self.assertIn(
            "An uncited positive line is indistinguishable from flattery and\n  must not "
            "be written.".replace("\n ", ""),
            body,
            "skills/retro/SKILL.md must state an uncited positive line is flattery and must "
            "not be written (AC3).",
        )

    def test_skill_claims_improvement_only_when_comparable(self):
        # "How it is improving" is a delta — a trend is claimed only with a comparable
        # prior figure, never an invented baseline. Load-bearing for the honesty of AC3.
        body = _norm(_read(RETRO_SKILL))
        self.assertIn(
            "Improvement is a *delta*, claimed only when comparable.",
            body,
            "skills/retro/SKILL.md property 5 must claim an improvement (a trend) only when "
            "comparable (AC3).",
        )
        self.assertIn(
            "Never invent a baseline.",
            body,
            "skills/retro/SKILL.md must forbid inventing a baseline for a trend (AC3).",
        )

    def test_skill_sparse_graph_leans_on_linear_and_says_so(self):
        # AC3's sparse-graph clause: lean on Linear evidence and SAY so; a None metric is
        # "—", never fabricated.
        body = _norm(_read(RETRO_SKILL))
        self.assertIn(
            "Sparse graph → lean on Linear and say so; never fabricate.",
            body,
            "skills/retro/SKILL.md property 5 must lean on Linear and say so on a sparse "
            "graph (AC3).",
        )
        self.assertIn(
            'says** "sparse graph — positives from Linear evidence"'.replace("**", ""),
            body.replace("**", ""),
            "skills/retro/SKILL.md must say 'sparse graph — positives from Linear evidence' "
            "on a sparse store (AC3).",
        )
        self.assertIn(
            'A `None` metric is "—", never a\n  fabricated win.'.replace("\n ", ""),
            body,
            "skills/retro/SKILL.md must render a None metric as '—', never a fabricated win "
            "(AC3).",
        )

    def test_every_synthesis_surface_carries_the_no_ungrounded_praise_discipline(self):
        # AC3 holds across surfaces: the retro skill (primary), commands/retro.md (step 4b),
        # and commands/status.md (step 4f) must each forbid ungrounded praise — a surface
        # that drifts back to flattery strands the contract.
        for path in SYNTHESIS_SURFACES:
            with self.subTest(surface=path.name):
                body = _norm(_read(path)).lower()
                self.assertIn(
                    "no ungrounded praise",
                    body,
                    f"{path.relative_to(REPO_ROOT)} must forbid ungrounded praise — every "
                    f"positive claim cites its evidence (AC3).",
                )

    def test_command_step_4b_requires_each_line_to_cite_the_metric(self):
        body = _norm(_read(RETRO_CMD))
        self.assertIn(
            "Every positive claim cites its evidence** — name the metric (or the Linear "
            "evidence on\n  a sparse store) behind each \"did well\" line.".replace(
                "\n ", ""
            ).replace("**", ""),
            body.replace("**", ""),
            "commands/retro.md step 4b must require each line to name its metric/Linear "
            "evidence (AC3).",
        )

    def test_status_step_4f_cites_the_metric_no_ungrounded_praise(self):
        body = _norm(_read(STATUS_CMD))
        self.assertIn(
            "Cite the metric — no ungrounded praise.",
            body,
            "commands/status.md step 4f must cite the metric — no ungrounded praise (AC3).",
        )
        # The worked contrast: a cited claim vs flattery that must NOT be printed.
        self.assertIn(
            '"team\'s doing great" is not and must not be printed',
            body,
            "commands/status.md step 4f must contrast a cited claim against flattery that "
            "must not be printed (AC3).",
        )

    def test_pins_would_bite_on_the_pre_fix_wording(self):
        # Anti-tautology: pre-NB-438 none of these surfaces mentioned positive claims or a
        # cite-or-don't-write rule for them. Prove every AC3 pin FIRES on synthetic pre-fix
        # text.
        pre_fix = _norm(
            "A filed candidate with no cited evidence is indistinguishable from a hunch. "
            "Every candidate cites the graph metric and/or the specific problems behind it."
        )
        self.assertNotIn(
            "Every positive claim cites its evidence — no ungrounded praise.", pre_fix
        )
        self.assertNotIn("Improvement is a *delta*, claimed only when comparable.", pre_fix)
        self.assertNotIn(
            "Sparse graph → lean on Linear and say so; never fabricate.", pre_fix
        )
        self.assertNotIn("no ungrounded praise", pre_fix.lower())


class NoBoundaryLoosenedStructuralTest(unittest.TestCase):
    """AC4 ``[manual]`` — structural half only. The holistic "no boundary was loosened"
    sign-off is a PO judgement against accountabilities.md (NAMED UNTESTABLE in the tester
    report — a runner cannot assert it without re-deriving the whole accountabilities model,
    a tautology). What is pinnable, and pinned here exactly as the siblings do: the three
    boundary clauses the change leans on are present in BOTH the retro and status surfaces,
    and accountabilities.md still states the unchanged scrum-master boundaries this
    narration must not cross."""

    def test_retro_synthesis_loosens_no_boundary_clauses_present(self):
        # The three clauses: reviewer never self-marks / appears; the retro is a batch
        # reader not a gate (no self-congratulation); narrates execution metrics, never
        # claims credit for a product call.
        body = _norm(_read(RETRO_SKILL))
        self.assertIn(
            "**This synthesis loosens no boundary.**",
            body,
            "skills/retro/SKILL.md property 5 must state the synthesis loosens no boundary "
            "(AC4 structural half).",
        )
        self.assertIn(
            "does **not** let the reviewer self-mark".replace("**", ""),
            body.replace("**", ""),
            "skills/retro/SKILL.md must keep the 'reviewer never self-marks' boundary "
            "(AC4).",
        )
        self.assertIn(
            "does **not** convert the gate into\nself-congratulation".replace(
                "**", ""
            ).replace("\n", " "),
            body.replace("**", ""),
            "skills/retro/SKILL.md must keep the 'no self-congratulation / retro is a "
            "reader not a gate' boundary (AC4).",
        )
        self.assertIn(
            'does **not** let the scrum-master\nclaim credit for a product call'.replace(
                "**", ""
            ).replace("\n", " "),
            body.replace("**", ""),
            "skills/retro/SKILL.md must keep the 'never claims credit for a product call' "
            "boundary (AC4).",
        )

    def test_command_surfaces_both_carry_the_loosens_no_boundary_guard(self):
        # AC4 is a cross-cutting invariant on BOTH new homes — the retro command step 4b AND
        # the status command step 4f must each carry the loosens-no-boundary guard, citing
        # accountabilities.md, or a future edit to one surface could quietly loosen it.
        for path in (RETRO_CMD, STATUS_CMD):
            with self.subTest(surface=path.name):
                body = _norm(_read(path)).replace("**", "")
                self.assertIn(
                    "oosens no boundary",  # matches "loosens"/"Loosens" after norm
                    body,
                    f"{path.relative_to(REPO_ROOT)} must carry a loosens-no-boundary guard "
                    f"on its positive-signal step (AC4).",
                )
                self.assertIn(
                    "skills/scrum/references/accountabilities.md",
                    body,
                    f"{path.relative_to(REPO_ROOT)} must verify the boundary against "
                    f"accountabilities.md (AC4 cross-cutting invariant).",
                )
                # The "never claims credit for a product call" clause wraps across a
                # blockquote `>` marker on status.md (so `_norm` leaves a `>` mid-phrase);
                # pin "for a product call", which stays contiguous on one physical line in
                # BOTH surfaces and is proven absent in the pre-fix bodies below.
                self.assertIn(
                    "for a product call",
                    body,
                    f"{path.relative_to(REPO_ROOT)} must keep the 'never claims credit for "
                    f"a product call' boundary on its positive-signal step (AC4).",
                )

    def test_status_guard_keeps_reviewer_not_consulted_and_no_gate(self):
        # Status's own twist on the two boundary clauses: the reviewer is not consulted (the
        # graph is read), and status runs no gate (so no gate to self-congratulate through).
        body = _norm(_read(STATUS_CMD)).replace("**", "")
        self.assertIn(
            "the reviewer is not consulted; the graph is read",
            body,
            "commands/status.md step 4f must state the reviewer is not consulted (AC4).",
        )
        self.assertIn(
            "`status` runs no gate".replace("`", ""),
            body.replace("`", ""),
            "commands/status.md step 4f must state status runs no gate, so no "
            "self-congratulation (AC4).",
        )

    def test_accountabilities_scrum_master_boundaries_are_intact(self):
        # The cross-cutting invariant: this narration must not let the scrum-master make
        # product decisions nor speak as the PO. Those does-NOT boundaries live in
        # accountabilities.md (untouched by this change). Pin that they still read as they
        # must — a future edit that loosens either trips here. (Same pins the NB-436 sibling
        # uses for the same Scrum-Master boundaries.)
        body = _norm(_read(ACCOUNTABILITIES))
        self.assertIn(
            "Make product decisions (what to build, what priority) — surfaces to PO",
            body,
            "accountabilities.md must keep the Scrum Master 'does NOT make product "
            "decisions' boundary (AC4 cross-cutting invariant).",
        )
        self.assertIn(
            "Speak as the PO in the issue",
            body,
            "accountabilities.md must keep the Scrum Master 'does NOT speak as the PO' "
            "boundary (AC4 cross-cutting invariant).",
        )

    def test_pins_would_bite_if_guards_were_dropped(self):
        # Anti-tautology: if a reword stripped the loosens-no-boundary guard or the
        # never-claim-credit clause, the structural pins above must FAIL. Prove they bite on
        # guard-free synthetic bodies, and that the accountabilities pins bite on a loosened
        # synthetic body.
        guardless_skill = _norm(
            "### 5. Positive synthesis. Read the wins off report --json and write a 'What "
            "went well' block above the patterns."
        )
        self.assertNotIn("**This synthesis loosens no boundary.**", guardless_skill)
        self.assertNotIn(
            "never claims credit for a product call",
            guardless_skill.replace("**", ""),
        )
        guardless_status = _norm(
            "### 4f. Print a lighter positive signal. Pick one standout positive from the "
            "graph and print a Bright spot line when there is signal."
        )
        self.assertNotIn("the reviewer is not consulted; the graph is read", guardless_status)
        loosened_accountab = _norm(
            "The scrum-master may make product calls and speak as the PO in the issue when "
            "narrating what the team did well."
        )
        self.assertNotIn(
            "Make product decisions (what to build, what priority) — surfaces to PO",
            loosened_accountab,
        )
        self.assertNotIn("Speak as the PO in the issue", loosened_accountab)


if __name__ == "__main__":
    unittest.main(verbosity=2)
