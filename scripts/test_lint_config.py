"""Behaviour tests for NB-286 (T1: lint config files).

The unit adds two config files at the repo root:
- ``.markdownlint-cli2.jsonc`` — markdownlint-cli2 config (JSONC),
- ``.pre-commit-config.yaml`` — pre-commit hook definitions.

These files had no regression coverage, so this module turns the issue's
acceptance signal + spec'd config shape into durable, executable checks. Each
acceptance bullet maps 1:1 to a test below:

* both files exist and are well-formed,
* the JSONC ``config`` object deep-equals the spec dict exactly,
* the pre-commit config carries the five hygiene hooks, the markdownlint-cli2
  hook, and a ruff hook scoped to ``\\.py$`` that is **non-gating** — pinned to
  ``stages: [manual]`` so ``pre-commit run --all-files`` (what CI runs) skips it
  and ruff is not an always-on gate (NB-285 AC #7),
* every ``rev`` is pinned (no floating refs like a branch name or ``HEAD``).

Why stdlib only: this is the repo's test convention (CI runs
``python3 -m unittest discover -s scripts -p 'test_*.py'`` on a bare
ubuntu-latest Python with no ``pip install``). The JSONC config is validated
with stdlib ``json`` after stripping ``//`` comments. The YAML is validated two
ways: a PyYAML round-trip *when PyYAML is importable* (so well-formedness is
proven where the parser exists), and — always — a parser-independent line scan
that asserts the hook ids and pinned revs the AC names. The line scan is what
keeps the core AC proven even on a CI image without PyYAML; it never silently
skips the contract.

Tests fail without the change (the files do not exist) and pass with it.

Run from the repo root:  python scripts/test_lint_config.py
"""

import importlib.util
import json
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
MARKDOWNLINT_CONFIG = REPO_ROOT / ".markdownlint-cli2.jsonc"
PRECOMMIT_CONFIG = REPO_ROOT / ".pre-commit-config.yaml"

# The exact config object the issue spec pins down.
EXPECTED_MARKDOWNLINT_CONFIG = {
    "default": True,
    "MD013": False,
    "MD033": False,
    "MD041": False,
    "MD024": {"siblings_only": True},
    "MD036": False,
}

# Hook ids the AC requires the pre-commit config to carry.
EXPECTED_HYGIENE_HOOK_IDS = {
    "end-of-file-fixer",
    "trailing-whitespace",
    "mixed-line-ending",
    "check-json",
    "check-yaml",
}

HAVE_YAML = importlib.util.find_spec("yaml") is not None


def _strip_jsonc_comments(text):
    """Remove ``//`` line comments from JSONC so stdlib ``json`` can parse it.

    The committed file uses only ``//`` comments (one per disabled rule) and no
    string contains a literal ``//``, so a line-trim is sufficient and safe here.
    """
    out = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("//"):
            continue
        out.append(line)
    return "\n".join(out)


class MarkdownlintConfigTest(unittest.TestCase):
    """``.markdownlint-cli2.jsonc`` exists, is well-formed, matches the spec."""

    def test_file_exists(self):
        self.assertTrue(
            MARKDOWNLINT_CONFIG.is_file(),
            f"{MARKDOWNLINT_CONFIG.name} must exist at the repo root",
        )

    def test_is_well_formed_jsonc(self):
        text = MARKDOWNLINT_CONFIG.read_text(encoding="utf-8")
        # Parses as JSON once comments are stripped — i.e. it is well-formed JSONC.
        json.loads(_strip_jsonc_comments(text))

    def test_config_object_equals_spec(self):
        text = MARKDOWNLINT_CONFIG.read_text(encoding="utf-8")
        data = json.loads(_strip_jsonc_comments(text))
        self.assertIn("config", data, "top-level 'config' key is required")
        # Deep equality: the whole config object must match the spec exactly —
        # no missing rules, no extra rules, MD024 siblings_only nested correctly.
        self.assertEqual(data["config"], EXPECTED_MARKDOWNLINT_CONFIG)


class PrecommitConfigTest(unittest.TestCase):
    """``.pre-commit-config.yaml`` exists, is well-formed, has the right hooks,
    and every ``rev`` is pinned."""

    @classmethod
    def setUpClass(cls):
        cls.text = (
            PRECOMMIT_CONFIG.read_text(encoding="utf-8")
            if PRECOMMIT_CONFIG.is_file()
            else ""
        )

    def test_file_exists(self):
        self.assertTrue(
            PRECOMMIT_CONFIG.is_file(),
            f"{PRECOMMIT_CONFIG.name} must exist at the repo root",
        )

    @unittest.skipUnless(HAVE_YAML, "PyYAML not installed in this interpreter")
    def test_is_well_formed_yaml(self):
        """Well-formedness via a real YAML parser, where one is available."""
        import yaml  # noqa: WPS433 — optional, guarded by skipUnless

        doc = yaml.safe_load(self.text)
        self.assertIsInstance(doc, dict, "top-level YAML document must be a mapping")
        self.assertIn("repos", doc, "pre-commit config must declare 'repos'")
        self.assertIsInstance(doc["repos"], list)

    @unittest.skipUnless(HAVE_YAML, "PyYAML not installed in this interpreter")
    def test_every_rev_is_pinned_parsed(self):
        """Parsed view: every repo entry has a pinned (non-floating) ``rev``."""
        import yaml  # noqa: WPS433

        doc = yaml.safe_load(self.text)
        revs = [
            repo.get("rev")
            for repo in doc["repos"]
            if repo.get("repo") != "local"
        ]
        self.assertTrue(revs, "expected at least one remote repo with a rev")
        for rev in revs:
            self.assertIsNotNone(rev, "every remote repo must declare a 'rev'")
            self._assert_pinned(rev)

    # --- Parser-independent checks: always run, so the AC is proven even on a
    # --- CI Python without PyYAML. ----------------------------------------

    def test_contains_hygiene_hook_ids(self):
        hook_ids = self._hook_ids(self.text)
        missing = EXPECTED_HYGIENE_HOOK_IDS - hook_ids
        self.assertFalse(
            missing,
            f"pre-commit config missing hygiene hook id(s): {sorted(missing)}",
        )

    def test_contains_markdownlint_hook(self):
        self.assertIn(
            "DavidAnson/markdownlint-cli2",
            self.text,
            "pre-commit config must reference the DavidAnson/markdownlint-cli2 repo",
        )
        self.assertIn(
            "markdownlint-cli2",
            self._hook_ids(self.text),
            "pre-commit config must enable the markdownlint-cli2 hook",
        )

    def test_contains_ruff_hook_scoped_to_python(self):
        self.assertIn(
            "astral-sh/ruff-pre-commit",
            self.text,
            "pre-commit config must reference the astral-sh/ruff-pre-commit repo",
        )
        ids = self._hook_ids(self.text)
        self.assertTrue(
            ids & {"ruff", "ruff-check"},
            "pre-commit config must enable a ruff hook (ruff or ruff-check)",
        )
        # The ruff hook must be scoped to Python files so it no-ops on a repo
        # with zero .py until Python lands.
        self.assertRegex(
            self.text,
            r"files:\s*\\?\.py\$",
            r"ruff hook must be scoped with files: \.py$",
        )

    def test_ruff_hook_is_non_gating_manual_stage(self):
        """NB-285 AC #7: ruff is wired but NOT an always-on gate.

        The ruff hook must carry ``stages: [manual]`` so ``pre-commit run
        --all-files`` (what CI runs) skips it — keeping ruff off the default
        gate while leaving it runnable on demand
        (``pre-commit run --hook-stage manual ruff-check``). We assert the
        ``manual`` stage sits on the ruff hook specifically (parser-backed
        where PyYAML exists) and, parser-independently, that the config
        declares a ``manual`` stage at all."""
        # Parser-independent: the config must declare a manual stage somewhere.
        # This holds even on a CI Python without PyYAML.
        self.assertRegex(
            self.text,
            r"stages:\s*\[\s*manual\s*\]",
            "ruff hook must declare stages: [manual] (non-gating, NB-285 AC #7)",
        )
        if not HAVE_YAML:
            self.skipTest("PyYAML not installed; manual-stage scoped check skipped")
        import yaml  # noqa: WPS433 — optional, guarded above

        doc = yaml.safe_load(self.text)
        ruff_hooks = [
            hook
            for repo in doc["repos"]
            if "ruff-pre-commit" in (repo.get("repo") or "")
            for hook in repo.get("hooks", [])
            if hook.get("id") in {"ruff", "ruff-check"}
        ]
        self.assertTrue(ruff_hooks, "expected a ruff hook in the ruff-pre-commit repo")
        for hook in ruff_hooks:
            self.assertEqual(
                hook.get("stages"),
                ["manual"],
                "the ruff hook must be pinned to stages: [manual] so it does "
                "not gate (run on demand with --hook-stage manual)",
            )

    def test_every_rev_is_pinned_textual(self):
        """Parser-independent: every ``rev:`` value is a pinned ref, not a
        floating branch/HEAD. This is the check that holds even without PyYAML."""
        revs = re.findall(r"^\s*rev:\s*(\S+)", self.text, flags=re.MULTILINE)
        self.assertTrue(revs, "expected at least one 'rev:' line in the config")
        for rev in revs:
            self._assert_pinned(rev.strip().strip("'\""))

    # --- helpers ----------------------------------------------------------

    @staticmethod
    def _hook_ids(text):
        """All ``- id: <hook>`` values, parser-independently."""
        return set(re.findall(r"-\s*id:\s*(\S+)", text))

    def _assert_pinned(self, rev):
        """A pinned rev is a version-like tag (e.g. ``v6.0.0``, ``0.22.1``) or a
        full-length commit SHA — never a floating ref. We intentionally assert
        *pinned-ness*, not a specific version literal, to avoid the stale-pin
        fragility a hard-coded version would create."""
        self.assertIsInstance(rev, str)
        floating = {"head", "main", "master", "stable", "latest", "default"}
        self.assertNotIn(
            rev.lower(),
            floating,
            f"rev {rev!r} is a floating ref; pin it to a released tag or SHA",
        )
        version_like = re.fullmatch(r"v?\d+(\.\d+)*[\w.\-]*", rev)
        sha_like = re.fullmatch(r"[0-9a-fA-F]{40}", rev)
        self.assertTrue(
            version_like or sha_like,
            f"rev {rev!r} is not a pinned version tag or commit SHA",
        )


if __name__ == "__main__":
    unittest.main()
