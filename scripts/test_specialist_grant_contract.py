"""Regression net for NB-413 — the specialist tool-grant contract.

NB-413: a specialist dispatched against an AC that requires *running* a check
(markdownlint, an index regen + ``--check``, a drift test, a label/issue create)
could be handed a tool grant that excludes the tool needed to run it, so the check
fell **silently** to the orchestrator or the pre-commit gate — quietly relocating
the trust boundary upward with nobody deciding it should. The fix has three parts,
one per acceptance criterion, and this module turns each into a durable check so the
neighbourhood can't drift unnoticed.

The three AC are `[review]`-kind (judgements an agent renders), so a test cannot prove
"the agent obeys the instruction" without becoming a tautology against the doc that *is*
the instruction. Instead this file does two stronger things:

  1. **Pins the load-bearing prose invariants** the change introduced, across **every**
     surface that must agree (the gate, the developer report contract, both lineage docs)
     — checked as a *set* so a reword that fixes one surface and strands another fails.
     (Same guard-the-neighbourhood discipline as
     ``scripts/test_reviewer_standards_enforcement.py``.)
  2. **Executes the real artifact where it can** — the gate states markdownlint is invoked
     "the way CI does" (``markdownlint-cli2`` pinned to the same rev as
     ``.pre-commit-config.yaml``, reading ``.markdownlint-cli2.jsonc``). One test asserts
     the *pin agreement* (gate version == pre-commit rev) parser-independently — always —
     and a second **actually runs** that pinned linter against a known-clean and a
     known-dirty fixture when ``npx`` is available, so AC2 is proven against a running
     binary, not prose alone. The runtime test self-skips where ``npx`` is absent (a bare
     CI Python image), so it never flakes the suite — but where the toolchain exists it is
     a real demonstration that the gate's stated invocation discovers the repo config and
     reports errors.

AC → test mapping:
  * AC1 (every runnable AC verifiable before hand-off: grant covers it OR the hand-off is
    explicit + enumerated) → ``EnumeratedHandoffContractTest`` +
    ``GateConsumesDeferredChecksTest``.
  * AC2 (docs/research self-checks — markdownlint/index/drift — runnable or declared) →
    ``GateRunsMarkdownlintLikeCITest`` (prose pin + pin-agreement) and
    ``MarkdownlintRuntimeTest`` (runs the pinned linter).
  * AC3 (decision recorded where the NB-340/NB-368 tool-grant lineage lives) →
    ``DecisionRecordedInLineageTest``.

Why stdlib only: the repo's test convention (CI runs
``python3 -m unittest discover -s scripts -p 'test_*.py'`` on a bare ubuntu-latest
Python with no ``pip install``). The one test that needs a toolchain guards on it and
skips cleanly.

Run from the repo root:  python scripts/test_specialist_grant_contract.py
(or collected by `python -m unittest discover -s scripts -p 'test_*.py'`).
"""

import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

GATE = REPO_ROOT / "skills" / "solve" / "gate.md"
DISPATCH = REPO_ROOT / "skills" / "solve" / "dispatch.md"
DEVELOPER = REPO_ROOT / "agents" / "developer.md"
REVIEWER_SKILL = REPO_ROOT / "skills" / "reviewer" / "SKILL.md"
LINEAR_SKILL = REPO_ROOT / "skills" / "linear" / "SKILL.md"
PRECOMMIT_CONFIG = REPO_ROOT / ".pre-commit-config.yaml"
MARKDOWNLINT_CONFIG = REPO_ROOT / ".markdownlint-cli2.jsonc"

# Both lineage docs must record the contract (AC3 wants it where the NB-340 lineage
# lives, and that section is mirrored in both skills). Checked as a set.
LINEAGE_SURFACES = (REVIEWER_SKILL, LINEAR_SKILL)


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def _norm(text: str) -> str:
    """Whitespace-collapse so a content pin survives prose line-wrapping."""
    return " ".join(text.split())


class EnumeratedHandoffContractTest(unittest.TestCase):
    """AC1 — a specialist that cannot run a required check must declare it in a
    machine-readable, enumerated way (not defer it silently)."""

    def test_developer_report_template_carries_deferred_checks_field(self):
        """The STATUS report template gains a ``Deferred-checks:`` field — the
        machine-readable hand-off line the gate consumes."""
        text = _read(DEVELOPER)
        self.assertIn(
            "Deferred-checks:",
            text,
            "agents/developer.md must add a Deferred-checks: line to the STATUS report",
        )
        # It must sit inside the ```text STATUS report block, not just be mentioned in
        # prose — i.e. it is part of the contract the orchestrator captures.
        report_block = re.search(
            r"STATUS: DONE.*?Next:[^\n]*", text, flags=re.DOTALL
        )
        self.assertIsNotNone(
            report_block, "could not locate the STATUS report template block"
        )
        self.assertIn(
            "Deferred-checks:",
            report_block.group(0),
            "Deferred-checks: must be a field *inside* the STATUS report template",
        )

    def test_contract_replaces_silent_deferral(self):
        """The developer doc frames the contract as replacing *silent* deferral —
        the exact gap NB-413 names — and ties the un-runnable checks to the gate."""
        norm = _norm(_read(DEVELOPER))
        self.assertIn("enumerated deferred-check hand-off", norm.lower())
        # The default-and-honest answer is spelled out so an empty line is never read as
        # "nothing to run" while a check silently went un-run.
        self.assertIn("Deferred-checks: none", norm)
        # The gap NB-413 names: the OLD behaviour let an un-runnable check fall silently.
        self.assertRegex(
            norm,
            r"cannot.{0,60}(run|execute).{0,120}(silent|fall silently)"
            r"|fall silently.{0,120}(orchestrator|gate)",
            "developer doc must name the old silent-deferral behaviour the contract closes",
        )
        # The NEW behaviour: each un-runnable check becomes one enumerated line the gate runs.
        self.assertRegex(
            norm,
            r"cannot.{0,30}\*?\*?run.{0,80}one line per check",
            "developer doc must say un-runnable checks are enumerated one-per-line",
        )

    def test_developer_domain_check_asserts_enumeration(self):
        """The developer's <Final_Checklist> gains a domain box that makes the
        developer self-assert it enumerated (or ran) every required check."""
        norm = _norm(_read(DEVELOPER))
        self.assertRegex(
            norm,
            r"Deferred checks enumerated",
            "developer <Final_Checklist> must carry a 'Deferred checks enumerated' box",
        )


class GateConsumesDeferredChecksTest(unittest.TestCase):
    """AC1 — the explicit hand-off is *consumed*: the gate is obligated to run each
    enumerated deferred check, and the orchestrator pipes the line through."""

    def test_gate_runs_each_enumerated_deferred_check(self):
        norm = _norm(_read(GATE))
        self.assertIn("Deferred-checks:", norm)
        # The gate must state it RUNS each enumerated check and that a failure is
        # needs-changes — i.e. the hand-off is obligatory, not advisory.
        self.assertRegex(
            norm,
            r"Deferred-checks.{0,400}?needs-changes",
            "gate must tie the developer's Deferred-checks to a needs-changes outcome",
        )
        self.assertIn(
            "replaces today's silent deferral",
            norm,
            "gate must name that the enumerated hand-off replaces silent deferral",
        )

    def test_dispatch_captures_and_passes_the_line(self):
        """The orchestrator (dispatch.md) captures the Deferred-checks: line from the
        developer report and passes it into the gate — otherwise the gate's
        envelope placeholder is never populated."""
        norm = _norm(_read(DISPATCH))
        self.assertIn("Deferred-checks:", norm)
        self.assertRegex(
            norm,
            r"Deferred-checks.{0,200}?(gate|reviewer runs)",
            "dispatch.md must pass the Deferred-checks line into the gate",
        )


class GateRunsMarkdownlintLikeCITest(unittest.TestCase):
    """AC2 (+ Fold-in NB-417) — the gate runs markdownlint on changed .md the way CI
    does, and trusts the error count over the exit code."""

    def test_gate_states_markdownlint_on_changed_md(self):
        norm = _norm(_read(GATE))
        self.assertIn("markdownlint-cli2", norm)
        self.assertRegex(
            norm,
            r"changed `?\.md`?",
            "gate must scope markdownlint to changed .md files",
        )

    def test_gate_trusts_error_count_over_exit_code(self):
        """The false-exit-0 caveat is load-bearing (NB-417): a non-zero error count is
        needs-changes even on a shell exit 0."""
        norm = _norm(_read(GATE)).lower()
        self.assertIn("false exit-0", norm)
        self.assertRegex(
            norm,
            r"(error count|error\(s\)|printed).{0,80}exit code"
            r"|exit code.{0,80}(error count|error\(s\)|printed)",
            "gate must say to trust the printed error count over the exit code",
        )

    def test_gate_markdownlint_version_matches_precommit_pin(self):
        """'The way CI does' means the *same pinned version*. This pins the agreement
        between the gate's stated invocation and the pre-commit rev — parser-
        independently, so it holds on a CI Python without PyYAML. If someone bumps the
        pre-commit markdownlint rev without updating the gate (or vice versa), this
        fails — the two must move in lockstep or the gate stops matching CI."""
        precommit = _read(PRECOMMIT_CONFIG)
        # The markdownlint-cli2 hook's pinned rev in pre-commit (e.g. v0.22.1). In a
        # pre-commit config the rev: sits on the repo entry (the DavidAnson/markdownlint-cli2
        # repo), *before* the hook id — match the repo URL then the next rev:.
        m = re.search(
            r"DavidAnson/markdownlint-cli2\s*\n\s*rev:\s*(v?\d[\w.\-]*)",
            precommit,
        )
        self.assertIsNotNone(
            m,
            "could not find the pinned markdownlint-cli2 rev in .pre-commit-config.yaml",
        )
        pinned = m.group(1)
        gate = _read(GATE)
        self.assertIn(
            f"markdownlint-cli2@{pinned}",
            gate,
            "gate must invoke markdownlint-cli2 at the SAME pinned rev as "
            f"pre-commit ({pinned}) so it matches CI",
        )


class MarkdownlintRuntimeTest(unittest.TestCase):
    """AC2 demonstrable — actually run the pinned linter the gate prescribes against a
    clean and a dirty fixture, proving the stated invocation discovers the repo config
    and reports errors. Self-skips where the toolchain is absent so the suite never
    flakes on a bare CI Python."""

    @classmethod
    def setUpClass(cls):
        cls.npx = shutil.which("npx")
        # The pinned rev the gate uses (read from pre-commit so the runtime test tracks
        # the real pin, not a literal copy that could drift).
        m = re.search(
            r"DavidAnson/markdownlint-cli2\s*\n\s*rev:\s*(v?\d[\w.\-]*)",
            _read(PRECOMMIT_CONFIG),
        )
        cls.pinned = m.group(1) if m else None

    def _run_markdownlint(self, target: pathlib.Path):
        """Invoke the pinned markdownlint-cli2 on a target, returning (rc, combined)."""
        proc = subprocess.run(
            [self.npx, "--yes", f"markdownlint-cli2@{self.pinned}", str(target)],
            cwd=str(REPO_ROOT),  # so .markdownlint-cli2.jsonc is auto-discovered
            capture_output=True,
            text=True,
            timeout=300,
        )
        return proc.returncode, (proc.stdout + proc.stderr)

    def test_clean_file_lints_zero_errors(self):
        if not self.npx or not self.pinned:
            self.skipTest("npx / pinned markdownlint rev unavailable")
        with tempfile.TemporaryDirectory(dir=str(REPO_ROOT)) as d:
            clean = pathlib.Path(d) / "clean.md"
            # A file that satisfies the repo config (MD041/MD013 disabled, etc.).
            clean.write_text("# Title\n\nA clean paragraph.\n", encoding="utf-8")
            rc, out = self._run_markdownlint(clean)
            self.assertIn(
                "Summary: 0 error(s)",
                out,
                f"pinned markdownlint should report 0 errors on a clean file; got:\n{out}",
            )

    def test_dirty_file_is_flagged(self):
        if not self.npx or not self.pinned:
            self.skipTest("npx / pinned markdownlint rev unavailable")
        with tempfile.TemporaryDirectory(dir=str(REPO_ROOT)) as d:
            dirty = pathlib.Path(d) / "dirty.md"
            # MD038 (space inside code span) — the exact rule that slipped through to CI
            # on NB-417. With the repo config MD038 is on (not disabled), so the pinned
            # linter must flag it. This is the running proof of the gate's purpose.
            dirty.write_text("# Title\n\nText with `bad ` code span.\n", encoding="utf-8")
            rc, out = self._run_markdownlint(dirty)
            # Trust the error count, not just rc — mirrors the gate's own rule.
            self.assertRegex(
                out,
                r"Summary: [1-9]\d* error\(s\)",
                f"pinned markdownlint must flag the MD038-dirty file; got:\n{out}",
            )


class DecisionRecordedInLineageTest(unittest.TestCase):
    """AC3 — the decision is recorded where the NB-340/NB-368 tool-grant lineage lives,
    in BOTH mirroring surfaces, so the specialist-grant contract is unambiguous."""

    def test_both_lineage_docs_carry_the_contract(self):
        for surface in LINEAGE_SURFACES:
            norm = _norm(_read(surface))
            self.assertIn(
                "Specialist-grant contract",
                norm,
                f"{surface} must carry a 'Specialist-grant contract' section (AC3)",
            )
            # It must sit in the tool-grant lineage neighbourhood (NB-340/NB-413).
            self.assertIn(
                "NB-413",
                norm,
                f"{surface} must tie the contract to NB-413",
            )
            self.assertIn(
                "NB-340",
                norm,
                f"{surface} must record the contract alongside the NB-340 lineage",
            )

    def test_reviewer_skill_records_rejected_alternatives(self):
        """AC3 wants the *decision* unambiguous — that includes why the two obvious
        alternatives were not taken, so they are not re-litigated. The trust-model home
        (reviewer SKILL) must name both: widen-every-grant and the NB-353
        disallowedTools inverted grant."""
        norm = _norm(_read(REVIEWER_SKILL))
        self.assertRegex(
            norm,
            r"[Ww]hy not just widen every grant",
            "reviewer SKILL must record why widening every grant was rejected",
        )
        self.assertIn(
            "disallowedTools",
            norm,
            "reviewer SKILL must record the NB-353 disallowedTools alternative",
        )
        self.assertIn(
            "NB-353",
            norm,
            "reviewer SKILL must attribute the inverted-grant idea to NB-353",
        )


if __name__ == "__main__":
    unittest.main()
