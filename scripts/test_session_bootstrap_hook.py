"""Behaviour tests for NB-350 (SessionStart bootstrap hook).

The unit ships three files under `hooks/`:
- `hooks/session-bootstrap.sh` — POSIX `sh` SessionStart hook,
- `hooks/session-bootstrap.md` — the committed contract block it emits,
- `hooks/hooks.json` — extended to register the hook as a SECOND SessionStart
  group (matcher `startup|clear`) alongside the existing identity guard.

The hook otherwise has no regression coverage, so this module turns the seven
`[test]` acceptance criteria into durable, executable checks. Each AC is a small
shell command in the issue; we run it exactly as written via `sh -c` (with the
repo root as cwd, the way the AC commands assume) and assert the documented exit
status / output. One test per AC so the proof maps 1:1 to the acceptance
criteria.

Why subprocess rather than re-implementing the logic in Python: the AC contract
*is* the shell behaviour (grep exit codes, `additionalContext` on stdout, exit 0
on empty stdin, silence outside a backlogd checkout). Asserting the script's
real observable behaviour is what makes the test fail without the change and pass
with it; re-implementing it would be a tautology.

Each AC command needs a POSIX shell plus `grep`/`printf`/`mktemp`. On Linux CI
these are native; on Windows they come from the Git-Bash/MSYS toolchain. If no
`sh` is discoverable the AC commands cannot be evaluated, so those tests skip
loudly (they do not silently pass).

The `[manual]` and `[review]` ACs are intentionally NOT encoded here — they
require a real fresh Claude Code session (manual) or human judgement (review) and
are named as untestable in the tester report.

Run from the repo root:  python scripts/test_session_bootstrap_hook.py
"""

import pathlib
import shutil
import subprocess
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOKS_DIR = REPO_ROOT / "hooks"
BOOTSTRAP_SH = HOOKS_DIR / "session-bootstrap.sh"
BOOTSTRAP_MD = HOOKS_DIR / "session-bootstrap.md"
HOOKS_JSON = HOOKS_DIR / "hooks.json"


def _find_sh():
    """Locate a POSIX shell. The AC commands are `sh` scripts; without one they
    cannot be evaluated, so callers skip (never silently pass)."""
    return shutil.which("sh") or shutil.which("bash")


SH = _find_sh()


def run_ac(command):
    """Run an acceptance-criterion shell command exactly as written, from the
    repo root (the cwd every AC command assumes for its relative `hooks/...`
    paths and for `$OLDPWD`). Returns the CompletedProcess."""
    return subprocess.run(
        [SH, "-c", command],
        cwd=str(REPO_ROOT),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
    )


@unittest.skipIf(SH is None, "no POSIX shell (sh/bash) on PATH — cannot evaluate AC commands")
class SessionBootstrapHookAC(unittest.TestCase):
    """The seven `[test]` ACs from NB-350, one test each."""

    # --- preconditions: the three shipped files exist ---------------------------------
    def test_files_exist(self):
        """The shipped hook files must exist where the manifest invokes them."""
        self.assertTrue(BOOTSTRAP_SH.is_file(), f"{BOOTSTRAP_SH} must exist")
        self.assertTrue(BOOTSTRAP_MD.is_file(), f"{BOOTSTRAP_MD} must exist")
        self.assertTrue(HOOKS_JSON.is_file(), f"{HOOKS_JSON} must exist")

    # --- AC1 -------------------------------------------------------------------------
    def test_AC1_fires_on_startup_clear_and_identity_guard_still_registered(self):
        """[test] bootstrap fires on startup+clear AND the identity guard is still
        registered:
        `grep -Eq 'startup|clear' hooks/hooks.json && grep -q check-git-identity hooks/hooks.json`
        exits 0."""
        cp = run_ac(
            "grep -Eq 'startup|clear' hooks/hooks.json "
            "&& grep -q check-git-identity hooks/hooks.json"
        )
        self.assertEqual(
            cp.returncode,
            0,
            "AC1: hooks.json must contain a startup|clear matcher AND still register "
            f"check-git-identity (stderr: {cp.stderr!r})",
        )

    # --- AC2 -------------------------------------------------------------------------
    def test_AC2_hooks_json_is_valid_json(self):
        """[test] hooks.json is valid JSON (parse-only):
        `python -c "import json;json.load(open('hooks/hooks.json'))"` exits 0.

        Asserted both in-process (parser-agnostic, robust on runners where the
        binary is `python3`) and via the AC command shape itself when a `python`
        on PATH is available."""
        import json

        # In-process parse — the durable, interpreter-independent assertion.
        with HOOKS_JSON.open(encoding="utf-8") as f:
            json.load(f)

        # Also exercise the AC command literally when `python` is resolvable.
        py = shutil.which("python") or shutil.which("python3")
        if py:
            cp = run_ac(
                f"{pathlib.Path(py).name} -c "
                "\"import json;json.load(open('hooks/hooks.json'))\""
            )
            self.assertEqual(
                cp.returncode,
                0,
                f"AC2: hooks.json must parse as JSON (stderr: {cp.stderr!r})",
            )

    # --- AC3 -------------------------------------------------------------------------
    def test_AC3_no_python_dependency_in_script(self):
        """[test] the bootstrap script carries no Python dependency:
        `! grep -Eq 'python|\\bpy\\b' hooks/session-bootstrap.sh` exits 0."""
        cp = run_ac("! grep -Eq 'python|\\bpy\\b' hooks/session-bootstrap.sh")
        self.assertEqual(
            cp.returncode,
            0,
            "AC3: hooks/session-bootstrap.sh must not reference python / py "
            "(no Python runtime dependency)",
        )

    # --- AC4 -------------------------------------------------------------------------
    def test_AC4_emits_additionalContext_from_backlogd_root(self):
        """[test] from the backlogd root the script emits an additionalContext block:
        `printf '{"hook_event_name":"SessionStart","source":"startup"}' \\
            | sh hooks/session-bootstrap.sh | grep -q additionalContext` exits 0."""
        cp = run_ac(
            "printf '{\"hook_event_name\":\"SessionStart\",\"source\":\"startup\"}' "
            "| sh hooks/session-bootstrap.sh | grep -q additionalContext"
        )
        self.assertEqual(
            cp.returncode,
            0,
            "AC4: invoked from the backlogd checkout the script must emit "
            f"additionalContext on stdout (stderr: {cp.stderr!r})",
        )

    # --- AC5 -------------------------------------------------------------------------
    def test_AC5_silent_outside_a_backlogd_checkout(self):
        """[test] outside a backlogd checkout the script emits no additionalContext:
        `test -z "$( cd "$(mktemp -d)" && printf '...' \\
            | sh "$OLDPWD/hooks/session-bootstrap.sh" | grep additionalContext )"`
        exits 0.

        Run from the repo root so `$OLDPWD` inside the subshell is the backlogd
        checkout (the absolute path the AC uses to locate the script) while the
        cwd is an unrelated, non-git temp dir."""
        cp = run_ac(
            'test -z "$( cd "$(mktemp -d)" && '
            'printf \'{"hook_event_name":"SessionStart","source":"startup"}\' '
            '| sh "$OLDPWD/hooks/session-bootstrap.sh" | grep additionalContext )"'
        )
        self.assertEqual(
            cp.returncode,
            0,
            "AC5: from an unrelated directory the script must emit no "
            f"additionalContext (stderr: {cp.stderr!r})",
        )

    # --- AC6 -------------------------------------------------------------------------
    def test_AC6_never_errors_on_empty_stdin(self):
        """[test] the script never errors, even on empty stdin:
        `printf '' | sh hooks/session-bootstrap.sh; echo $?` prints `0`."""
        cp = run_ac("printf '' | sh hooks/session-bootstrap.sh; echo $?")
        self.assertEqual(
            cp.returncode,
            0,
            f"AC6: the AC command itself must exit 0 (stderr: {cp.stderr!r})",
        )
        self.assertEqual(
            cp.stdout.strip().splitlines()[-1] if cp.stdout.strip() else "",
            "0",
            "AC6: `printf '' | sh hooks/session-bootstrap.sh; echo $?` must print 0 "
            f"(got stdout: {cp.stdout!r})",
        )

    # --- AC7 -------------------------------------------------------------------------
    def test_AC7_no_maintainer_specific_values(self):
        """[test] the shipped hook files carry no maintainer-specific values:
        `! grep -REq 'nicolai\\.bernsen@gmail|Private[\\\\/]Repos|nicolaibernsen' \\
            hooks/session-bootstrap.sh hooks/session-bootstrap.md hooks/hooks.json`
        exits 0."""
        cp = run_ac(
            "! grep -REq 'nicolai\\.bernsen@gmail|Private[\\\\/]Repos|nicolaibernsen' "
            "hooks/session-bootstrap.sh hooks/session-bootstrap.md hooks/hooks.json"
        )
        self.assertEqual(
            cp.returncode,
            0,
            "AC7: the shipped hook files must not contain maintainer-specific "
            "values (personal email / Private/Repos / nicolaibernsen)",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
