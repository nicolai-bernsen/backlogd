"""Behaviour tests for NB-289 (T4: scheduled advisory external-link workflow).

The unit adds a NEW ``.github/workflows/links-external.yml`` — the ADVISORY,
EXTERNAL-link counterpart to ci.yml's BLOCKING, internal/offline lychee gate.
Its load-bearing contract (the reason this unit exists) is its TRIGGER SHAPE:
it runs ONLY on a weekly ``schedule`` + manual ``workflow_dispatch`` and has NO
``pull_request`` and NO ``push`` trigger, so it is structurally incapable of
gating a PR or the ``dev`` branch. A transient external 4xx/timeout can never
fail a PR because the workflow never runs on one.

This module turns the AC ("Workflow exists, runs on schedule + manual dispatch,
is non-blocking; a transient external 4xx/timeout does not fail any PR" — shape:
triggers exactly ``schedule`` + ``workflow_dispatch`` with NO
``pull_request``/``push``; lychee over external links; advisory/non-blocking;
action pinned) into durable, executable checks. Each AC facet maps to a test:

* the workflow file exists and parses as valid YAML,
* its ``on:`` triggers are EXACTLY ``{schedule, workflow_dispatch}`` — and
  CRUCIALLY there is no ``pull_request`` and no ``push`` trigger (the
  can-never-gate invariant — this is THE load-bearing assertion),
* it has a weekly ``schedule`` cron,
* it has a ``workflow_dispatch`` trigger,
* its lychee step is pinned (a 40-hex SHA or a ``v<semver>`` tag, not a bare
  floating ref) — and every other ``uses:`` ref is pinned too,
* it scans EXTERNAL links — i.e. it does NOT pass ``--offline`` (that is
  ci.yml's internal-only mode),
* it is advisory: the lychee step sets ``fail: false`` and never ``fail: true``,
  so the job never hard-fails on a broken/transient link,
* (distinctness) ci.yml — the blocking gate — is a SEPARATE file that still
  carries its internal-only ``--offline`` lychee and still triggers on
  ``pull_request``; this unit did not collapse the two.

Why stdlib only: this is the repo's test convention (CI runs
``python3 -m unittest discover -s scripts -p 'test_*.py'`` on a bare
ubuntu-latest Python with no ``pip install``). The YAML is validated two ways:
a PyYAML round-trip *when PyYAML is importable* (so the parsed ``on:`` mapping —
exact trigger keys, cron presence — is proven where the parser exists), and —
always — parser-independent text/line scans that assert the same trigger shape,
pinned-ness, external (non-offline) scope, and advisory ``fail: false``. The
text scans keep the contract proven even on a CI image without PyYAML; they
never silently skip.

Deliberately NOT covered here (untestable as unit tests — would need a real
runner / the live internet): the cron actually firing weekly, lychee resolving
real external URLs, and ``create-issue-from-file`` filing/refreshing the
tracking issue. Those are the workflow's RUNTIME behaviour and are confirmed
when the workflow runs in GitHub Actions; they are reported as
untestable-as-unit-tests, not silently skipped.

Tests fail without the change (the file / trigger shape are absent) and pass
with it.

Run from the repo root:  python scripts/test_links_external_workflow.py
"""

import importlib.util
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
EXTERNAL_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "links-external.yml"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"

HAVE_YAML = importlib.util.find_spec("yaml") is not None


def _read(path):
    """File text, or empty string if the file is absent (so the file-exists
    test owns the missing-file failure rather than every test erroring)."""
    return path.read_text(encoding="utf-8") if path.is_file() else ""


class ExternalWorkflowFileTest(unittest.TestCase):
    """``.github/workflows/links-external.yml`` exists and is well-formed YAML."""

    def test_file_exists(self):
        self.assertTrue(
            EXTERNAL_WORKFLOW.is_file(),
            f"{EXTERNAL_WORKFLOW} must exist",
        )

    @unittest.skipUnless(HAVE_YAML, "PyYAML not installed in this interpreter")
    def test_is_well_formed_yaml(self):
        """Well-formedness via a real YAML parser, where one is available."""
        import yaml  # noqa: WPS433 — optional, guarded by skipUnless

        doc = yaml.safe_load(EXTERNAL_WORKFLOW.read_text(encoding="utf-8"))
        self.assertIsInstance(doc, dict, "top-level YAML document must be a mapping")
        self.assertIn("jobs", doc, "workflow must declare 'jobs'")


class TriggerShapeTest(unittest.TestCase):
    """THE load-bearing AC: triggers are EXACTLY schedule + workflow_dispatch,
    with NO pull_request and NO push — so this workflow can never gate a PR."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(EXTERNAL_WORKFLOW)

    @unittest.skipUnless(HAVE_YAML, "PyYAML not installed in this interpreter")
    def test_on_triggers_are_exactly_schedule_and_dispatch_parsed(self):
        """Parsed view: the ``on:`` mapping keys are exactly
        {schedule, workflow_dispatch} — nothing more, nothing less."""
        import yaml  # noqa: WPS433

        doc = yaml.safe_load(self.text)
        # PyYAML parses the bare key ``on:`` as the boolean True (YAML 1.1), so
        # accept either spelling when reading the triggers mapping back.
        triggers = doc.get("on", doc.get(True))
        self.assertIsInstance(
            triggers, dict, "the 'on:' triggers must be a mapping of trigger names"
        )
        self.assertEqual(
            set(triggers.keys()),
            {"schedule", "workflow_dispatch"},
            "triggers must be EXACTLY {schedule, workflow_dispatch}; "
            f"got {sorted(triggers.keys())}",
        )

    @unittest.skipUnless(HAVE_YAML, "PyYAML not installed in this interpreter")
    def test_no_pull_request_or_push_trigger_parsed(self):
        """Parsed view: neither pull_request nor push is a trigger — the
        can-never-gate invariant, asserted explicitly."""
        import yaml  # noqa: WPS433

        doc = yaml.safe_load(self.text)
        triggers = doc.get("on", doc.get(True))
        self.assertIsInstance(triggers, dict, "the 'on:' triggers must be a mapping")
        self.assertNotIn(
            "pull_request",
            triggers,
            "advisory workflow MUST NOT trigger on pull_request — it would gate PRs",
        )
        self.assertNotIn(
            "push",
            triggers,
            "advisory workflow MUST NOT trigger on push — it would gate branches",
        )

    def test_no_pull_request_or_push_trigger_textual(self):
        """Parser-independent: no ``pull_request:`` / ``push:`` trigger key.

        Scoped to the ``on:`` block (between ``on:`` and the next top-level key)
        so an unrelated mention elsewhere can't mask a real trigger. Holds even
        on a CI Python without PyYAML — this is the always-on guard for THE
        load-bearing invariant."""
        on_block = self._on_block_lines()
        self.assertTrue(on_block, "workflow has no top-level 'on:' block")
        for ln in on_block:
            self.assertNotRegex(
                ln,
                r"^\s+pull_request\s*:",
                "advisory workflow MUST NOT have a pull_request trigger",
            )
            self.assertNotRegex(
                ln,
                r"^\s+push\s*:",
                "advisory workflow MUST NOT have a push trigger",
            )

    def test_schedule_and_dispatch_present_textual(self):
        """Parser-independent: both ``schedule:`` and ``workflow_dispatch`` are
        present inside the ``on:`` block."""
        on_block = self._on_block_lines()
        self.assertTrue(on_block, "workflow has no top-level 'on:' block")
        self.assertTrue(
            any(re.match(r"^\s+schedule\s*:", ln) for ln in on_block),
            "advisory workflow must declare a 'schedule:' trigger",
        )
        self.assertTrue(
            any(re.match(r"^\s+workflow_dispatch\s*:?\s*$", ln) for ln in on_block),
            "advisory workflow must declare a 'workflow_dispatch' trigger",
        )

    def _on_block_lines(self):
        """Lines belonging to the top-level ``on:`` block (its indented body),
        i.e. from the line after ``on:`` until the next column-0 key."""
        lines = self.text.splitlines()
        try:
            on_idx = next(
                i for i, ln in enumerate(lines) if re.match(r"^on:\s*$", ln)
            )
        except StopIteration:
            return []
        block = []
        for ln in lines[on_idx + 1 :]:
            if re.match(r"^\S", ln):  # dedented to top level → on: block ended
                break
            block.append(ln)
        return block


class WeeklyScheduleTest(unittest.TestCase):
    """The schedule is a weekly cron (the AC says 'runs on schedule')."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(EXTERNAL_WORKFLOW)

    @unittest.skipUnless(HAVE_YAML, "PyYAML not installed in this interpreter")
    def test_schedule_has_cron_parsed(self):
        """Parsed view: ``on.schedule`` is a list carrying at least one cron
        expression with the canonical five whitespace-separated fields."""
        import yaml  # noqa: WPS433

        doc = yaml.safe_load(self.text)
        triggers = doc.get("on", doc.get(True))
        schedule = triggers.get("schedule")
        self.assertIsInstance(
            schedule, list, "on.schedule must be a list of cron entries"
        )
        crons = [entry.get("cron") for entry in schedule if isinstance(entry, dict)]
        self.assertTrue(crons, "on.schedule must declare at least one 'cron'")
        for cron in crons:
            self.assertRegex(
                cron,
                r"^\s*\S+\s+\S+\s+\S+\s+\S+\s+\S+\s*$",
                f"cron {cron!r} must have five whitespace-separated fields",
            )

    def test_cron_present_textual(self):
        """Parser-independent: a ``cron:`` entry exists somewhere in the file."""
        self.assertRegex(
            self.text,
            r"-\s*cron\s*:",
            "advisory workflow must declare a 'cron:' schedule entry",
        )


class ExternalScopeTest(unittest.TestCase):
    """It scans EXTERNAL links — i.e. it does NOT run lychee in --offline mode
    (that is ci.yml's internal-only gate). External reach is the whole point."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(EXTERNAL_WORKFLOW)

    def test_uses_lychee(self):
        self.assertRegex(
            self.text,
            r"uses:\s*lycheeverse/lychee-action@",
            "advisory workflow must run the lychee action",
        )

    @unittest.skipUnless(HAVE_YAML, "PyYAML not installed in this interpreter")
    def test_lychee_args_not_offline_parsed(self):
        """Parsed view: no lychee step passes ``--offline`` in its ``with.args``.

        ``--offline`` would reduce lychee to file-existence checks and make zero
        network calls — that is ci.yml's internal-only behaviour, the opposite
        of this advisory external sweep. Parsing the args (vs scanning the whole
        file) avoids matching the explanatory ``NO --offline`` comment."""
        import yaml  # noqa: WPS433

        doc = yaml.safe_load(self.text)
        lychee_args = []
        for job in (doc.get("jobs") or {}).values():
            for step in job.get("steps", []) or []:
                uses = step.get("uses", "")
                if isinstance(uses, str) and uses.startswith(
                    "lycheeverse/lychee-action@"
                ):
                    lychee_args.append((step.get("with") or {}).get("args", ""))
        self.assertTrue(lychee_args, "expected at least one lychee-action step")
        for args in lychee_args:
            self.assertNotIn(
                "--offline",
                args,
                "advisory workflow must NOT pass --offline; it checks EXTERNAL "
                "links over the network (--offline is ci.yml's internal-only mode)",
            )

    def test_lychee_args_not_offline_textual(self):
        """Parser-independent: no ``args:`` line in the file carries
        ``--offline``. Scoped to ``args:`` lines so the explanatory ``NO
        --offline`` comment in the file body is not mistaken for a flag. Holds
        even on a CI Python without PyYAML."""
        args_lines = [
            ln for ln in self.text.splitlines() if re.match(r"^\s*args\s*:", ln)
        ]
        self.assertTrue(args_lines, "expected a lychee 'args:' line to scan")
        for ln in args_lines:
            self.assertNotIn(
                "--offline",
                ln,
                "advisory workflow's lychee args must NOT pass --offline "
                "(--offline is ci.yml's internal-only mode)",
            )


class AdvisoryNonBlockingTest(unittest.TestCase):
    """It is advisory/non-blocking: the lychee step sets fail: false and never
    fail: true, so a transient external 4xx/timeout can never hard-fail a run."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(EXTERNAL_WORKFLOW)

    @unittest.skipUnless(HAVE_YAML, "PyYAML not installed in this interpreter")
    def test_lychee_step_fail_is_false_parsed(self):
        """Parsed view: every lychee-action step passes ``fail: false`` in its
        ``with:`` block (so the job never hard-fails on a broken link)."""
        import yaml  # noqa: WPS433

        doc = yaml.safe_load(self.text)
        lychee_steps = []
        for job in (doc.get("jobs") or {}).values():
            for step in job.get("steps", []) or []:
                uses = step.get("uses", "")
                if isinstance(uses, str) and uses.startswith(
                    "lycheeverse/lychee-action@"
                ):
                    lychee_steps.append(step)
        self.assertTrue(lychee_steps, "expected at least one lychee-action step")
        for step in lychee_steps:
            with_block = step.get("with") or {}
            self.assertEqual(
                with_block.get("fail"),
                False,
                "the advisory lychee step must set 'fail: false' (non-blocking); "
                f"got fail={with_block.get('fail')!r}",
            )

    def test_lychee_fail_false_textual(self):
        """Parser-independent: ``fail: false`` appears and ``fail: true`` does
        not (the advisory step must never be configured to hard-fail)."""
        self.assertRegex(
            self.text,
            r"fail\s*:\s*false",
            "advisory workflow must set 'fail: false' on the lychee step",
        )
        self.assertNotRegex(
            self.text,
            r"fail\s*:\s*true",
            "advisory workflow must NOT set 'fail: true' — it would become blocking",
        )


class UsesRefsPinnedTest(unittest.TestCase):
    """Every ``uses:`` ref must be pinned — a 40-hex SHA or a ``v<semver>`` tag —
    never a floating ref like a branch name. We assert pinned-ness SHAPE, not a
    specific version literal, to avoid the stale-pin fragility a hard-coded
    version would create (the NB-389 trap)."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(EXTERNAL_WORKFLOW)

    def _uses_refs(self):
        """All ``uses: <owner>/<repo>@<ref>`` action references in the file."""
        return re.findall(r"uses:\s*([\w.\-]+/[\w.\-]+)@(\S+)", self.text)

    def test_at_least_one_action_used(self):
        self.assertTrue(
            self._uses_refs(),
            "expected at least one 'uses:' action reference in the workflow",
        )

    def test_lychee_action_is_pinned(self):
        """The lychee action specifically must be pinned (the AC names it)."""
        lychee = [
            ref
            for action, ref in self._uses_refs()
            if action == "lycheeverse/lychee-action"
        ]
        self.assertTrue(lychee, "expected the lycheeverse/lychee-action to be used")
        for ref in lychee:
            cleaned = ref.strip().strip("'\"")
            self.assertTrue(
                re.fullmatch(r"[0-9a-fA-F]{40}", cleaned)
                or re.fullmatch(r"v\d+(\.\d+)*[\w.\-]*", cleaned),
                f"lychee-action@{cleaned} is not pinned to a 40-hex SHA or a "
                "v<semver> tag",
            )

    def test_every_uses_ref_is_pinned(self):
        floating = {"main", "master", "head", "latest", "stable", "develop", "dev"}
        for action, ref in self._uses_refs():
            cleaned = ref.strip().strip("'\"")
            self.assertNotIn(
                cleaned.lower(),
                floating,
                f"uses: {action}@{cleaned} is a floating ref; pin it to a "
                "released tag or a full commit SHA",
            )
            sha_like = re.fullmatch(r"[0-9a-fA-F]{40}", cleaned)
            version_like = re.fullmatch(r"v\d+(\.\d+)*[\w.\-]*", cleaned)
            self.assertTrue(
                sha_like or version_like,
                f"uses: {action}@{cleaned} is not pinned to a 40-hex SHA or a "
                "v<semver> tag",
            )


class DistinctFromCiGateTest(unittest.TestCase):
    """This advisory workflow is SEPARATE from ci.yml's blocking gate: ci.yml
    still triggers on pull_request and still runs lychee --offline. This unit
    must not have collapsed the two or weakened the internal gate."""

    @classmethod
    def setUpClass(cls):
        cls.ci_text = _read(CI_WORKFLOW)

    def test_ci_workflow_still_exists(self):
        self.assertTrue(CI_WORKFLOW.is_file(), f"{CI_WORKFLOW} must still exist")

    def test_ci_still_triggers_on_pull_request(self):
        """The BLOCKING gate keeps its pull_request trigger — the advisory
        workflow is additive, not a replacement for the PR gate."""
        self.assertTrue(
            any(
                re.match(r"^\s+pull_request\s*:", ln)
                for ln in self.ci_text.splitlines()
            ),
            "ci.yml must still trigger on pull_request (the blocking PR gate)",
        )

    def test_ci_lychee_still_offline(self):
        """ci.yml's lychee remains internal-only (--offline) — the two lychee
        steps stay distinct in scope."""
        self.assertIn(
            "--offline",
            self.ci_text,
            "ci.yml's lychee gate must remain internal-only (--offline)",
        )


if __name__ == "__main__":
    unittest.main()
