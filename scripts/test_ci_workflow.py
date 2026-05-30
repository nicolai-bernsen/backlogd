"""Behaviour tests for NB-288 (T3: wire CI gates into the single job).

The unit extends ``.github/workflows/ci.yml`` — keeping the SINGLE ``validate``
job — with four new gates and (per the AC) without dropping any existing step:

* a ``pre-commit/action`` step (runs the repo ``.pre-commit-config.yaml``),
* a ``claude plugin validate .`` invocation (with a pinned Claude Code CLI),
* an ``actionlint`` step,
* a ``lychee`` step scoped to internal/relative links only (``--offline``),

while RETAINING the two python JSON-manifest fallback checks and the existing
``Run test suites`` + witness steps. Every ``uses:`` must stay pinned.

This module turns that acceptance signal + the story-level shape into durable,
executable checks. Each AC bullet maps 1:1 to a test below:

* the workflow file exists and parses as valid YAML,
* there is exactly ONE job (the single-job invariant the AC demands),
* the four new gates are each present,
* the python JSON-manifest fallback steps are STILL present,
* the existing ``Run test suites`` + witness steps are STILL present,
* every ``uses:`` ref is pinned (a 40-hex SHA or a ``v<semver>`` tag).

Why stdlib only: this is the repo's test convention (CI runs
``python3 -m unittest discover -s scripts -p 'test_*.py'`` on a bare
ubuntu-latest Python with no ``pip install``). The YAML is validated two ways:
a PyYAML round-trip *when PyYAML is importable* (so structure — one job, step
lists — is proven where the parser exists), and — always — parser-independent
text/line scans that assert the gates, retained steps, and pinned-ness the AC
names. The text scans are what keep the contract proven even on a CI image
without PyYAML; they never silently skip.

Deliberately NOT covered here (would make the stdlib suite flaky / are not
unit-testable): shelling out to ``actionlint`` / ``lychee`` / ``claude`` /
``pre-commit``, or hitting the network. "CI is green on a clean PR" and the
three break-the-gate demonstrations (dead internal link, malformed ``${{ }}``
expression, invalid manifest each failing the job) need those real binaries and
a GitHub Actions runner — they are proven by the developer's tool-runs and
confirmed live at PR time, and are reported as untestable-as-unit-tests.

Tests fail without the change (the gates / single-job shape are absent) and
pass with it.

Run from the repo root:  python scripts/test_ci_workflow.py
"""

import importlib.util
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"

HAVE_YAML = importlib.util.find_spec("yaml") is not None


class CiWorkflowFileTest(unittest.TestCase):
    """``.github/workflows/ci.yml`` exists and is well-formed YAML."""

    def test_file_exists(self):
        self.assertTrue(
            CI_WORKFLOW.is_file(),
            f"{CI_WORKFLOW} must exist",
        )

    @unittest.skipUnless(HAVE_YAML, "PyYAML not installed in this interpreter")
    def test_is_well_formed_yaml(self):
        """Well-formedness via a real YAML parser, where one is available."""
        import yaml  # noqa: WPS433 — optional, guarded by skipUnless

        doc = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
        self.assertIsInstance(doc, dict, "top-level YAML document must be a mapping")
        self.assertIn("jobs", doc, "workflow must declare 'jobs'")


class SingleJobInvariantTest(unittest.TestCase):
    """The AC demands exactly ONE job — do not split into multiple jobs."""

    @classmethod
    def setUpClass(cls):
        cls.text = (
            CI_WORKFLOW.read_text(encoding="utf-8") if CI_WORKFLOW.is_file() else ""
        )

    @unittest.skipUnless(HAVE_YAML, "PyYAML not installed in this interpreter")
    def test_exactly_one_job_parsed(self):
        """Parsed view: the ``jobs`` mapping has exactly one entry, named
        ``validate``."""
        import yaml  # noqa: WPS433

        doc = yaml.safe_load(self.text)
        jobs = doc.get("jobs", {})
        self.assertIsInstance(jobs, dict, "'jobs' must be a mapping")
        self.assertEqual(
            list(jobs.keys()),
            ["validate"],
            f"expected exactly one job named 'validate', got {list(jobs.keys())}",
        )

    def test_exactly_one_job_textual(self):
        """Parser-independent: exactly one top-level (2-space-indented) job key
        under ``jobs:``. Holds even on a CI Python without PyYAML."""
        # Job keys sit at exactly two-space indentation inside the jobs: block.
        # The file has no other top-level mapping after jobs:, so a scan of
        # `^  <key>:` lines that are not steps/known job-fields is reliable here.
        # Simpler and robust: count children of jobs: by re-parsing the block.
        lines = self.text.splitlines()
        try:
            jobs_idx = next(
                i for i, ln in enumerate(lines) if re.match(r"^jobs:\s*$", ln)
            )
        except StopIteration:
            self.fail("workflow has no top-level 'jobs:' block")
        job_keys = []
        for ln in lines[jobs_idx + 1 :]:
            if re.match(r"^\S", ln):  # dedented back to top level → jobs block ended
                break
            m = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", ln)
            if m:
                job_keys.append(m.group(1))
        self.assertEqual(
            job_keys,
            ["validate"],
            f"expected exactly one job named 'validate', got {job_keys}",
        )


class NewGatesPresentTest(unittest.TestCase):
    """The four new gates the AC adds are each present in the workflow."""

    @classmethod
    def setUpClass(cls):
        cls.text = (
            CI_WORKFLOW.read_text(encoding="utf-8") if CI_WORKFLOW.is_file() else ""
        )

    def test_pre_commit_action_gate_present(self):
        self.assertRegex(
            self.text,
            r"uses:\s*pre-commit/action@",
            "workflow must run the pre-commit/action gate",
        )

    def test_claude_plugin_validate_gate_present(self):
        self.assertRegex(
            self.text,
            r"claude\s+plugin\s+validate\s+\.",
            "workflow must invoke `claude plugin validate .`",
        )

    def test_actionlint_gate_present(self):
        self.assertRegex(
            self.text,
            r"uses:\s*rhysd/actionlint@",
            "workflow must run the actionlint gate",
        )

    def test_lychee_internal_only_gate_present(self):
        self.assertRegex(
            self.text,
            r"uses:\s*lycheeverse/lychee-action@",
            "workflow must run the lychee gate",
        )
        # Internal/relative links only: lychee must be scoped offline so it makes
        # zero network calls (external-link scanning is out of scope for T3).
        self.assertIn(
            "--offline",
            self.text,
            "lychee must run with --offline so only internal/relative links are "
            "checked (no external/network calls)",
        )


class RetainedFallbackChecksTest(unittest.TestCase):
    """The python JSON-manifest fallback checks must be RETAINED per the AC."""

    @classmethod
    def setUpClass(cls):
        cls.text = (
            CI_WORKFLOW.read_text(encoding="utf-8") if CI_WORKFLOW.is_file() else ""
        )

    def test_plugin_manifest_python_check_retained(self):
        self.assertIn(
            ".claude-plugin/plugin.json",
            self.text,
            "the python plugin.json well-formedness fallback must be retained",
        )

    def test_marketplace_manifest_python_check_retained(self):
        self.assertIn(
            ".claude-plugin/marketplace.json",
            self.text,
            "the python marketplace.json well-formedness fallback must be retained",
        )


class RetainedExistingStepsTest(unittest.TestCase):
    """T3 must NOT drop the pre-existing test-suite and witness steps."""

    @classmethod
    def setUpClass(cls):
        cls.text = (
            CI_WORKFLOW.read_text(encoding="utf-8") if CI_WORKFLOW.is_file() else ""
        )

    def test_run_test_suites_step_retained(self):
        self.assertRegex(
            self.text,
            r"unittest\s+discover\s+-s\s+scripts\s+-p",
            "the 'Run test suites' step must be retained",
        )

    def test_witness_step_retained(self):
        self.assertIn(
            "scripts/witness.py",
            self.text,
            "the witness step (scripts/witness.py) must be retained",
        )


class UsesRefsPinnedTest(unittest.TestCase):
    """Every ``uses:`` ref must be pinned — a 40-hex SHA or a ``v<semver>`` tag —
    never a floating ref like a branch name. We assert pinned-ness SHAPE, not a
    specific version literal, to avoid the stale-pin fragility a hard-coded
    version would create (the NB-389 trap)."""

    @classmethod
    def setUpClass(cls):
        cls.text = (
            CI_WORKFLOW.read_text(encoding="utf-8") if CI_WORKFLOW.is_file() else ""
        )

    def _uses_refs(self):
        """All ``uses: <owner>/<repo>@<ref>`` action references in the file."""
        return re.findall(
            r"uses:\s*([\w.\-]+/[\w.\-]+)@(\S+)", self.text
        )

    def test_at_least_one_action_used(self):
        self.assertTrue(
            self._uses_refs(),
            "expected at least one 'uses:' action reference in the workflow",
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


if __name__ == "__main__":
    unittest.main()
