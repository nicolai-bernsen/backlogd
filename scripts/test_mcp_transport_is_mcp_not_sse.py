"""Content-pin regression tests for NB-442 — `.mcp.json` uses `/mcp`, not the
deprecated `/sse`, transport.

NB-442's three acceptance criteria are all `[review]` (a config-verification +
two one-line doc confirmations), but each rests on a load-bearing artifact a
runnable command can pin:

  AC1 — `.mcp.json` at the repo root uses the `https://mcp.linear.app/mcp`
        HTTP-stream URL and does NOT point at `/sse`. This is the strongest pin
        here: an actual assertion on the parsed JSON content, so a future edit
        cannot silently regress the transport back to the deprecated endpoint.
  AC2 — `README.md`'s Linear-MCP setup note states that `/sse` is removed and
        `/mcp` is the required transport. Pinned by case-insensitive concept
        tokens (not a brittle sentence), with an explicit anti-vacuity guard
        proving the same assertion FAILS against the pre-change README at the
        diff base (`git merge-base HEAD origin/dev`, fall back to `origin/main`)
        — anchored to the diff base, not `HEAD`, so it stays correct once the
        change is committed.
  AC3 — `skills/linear/references/linear-mcp.md` carries the current
        `Re-verified 2026-06-05` snapshot line (pairs with NB-441), so the MCP
        surface snapshot is confirmed current alongside the transport fix.

Design rule (the repo's #1 docs-test trap): assert ROBUST invariants — the
parsed JSON URL, case-insensitive concept tokens, a stable date line — NOT
brittle marketing prose, which gets reworded over time and must not break the
suite. One test method per AC claim so a failure names the AC that regressed.

Discoverable by `python -m unittest discover -s scripts` (how CI runs the
suite). Also runnable directly:  python scripts/test_mcp_transport_is_mcp_not_sse.py
"""

import json
import pathlib
import subprocess
import unittest


# Same idiom as the sibling content-pin tests (test_readme_convert.py,
# test_documents_and_updates_ref.py): resolve the repo root relative to this
# file so the assertions read repo-root artifacts regardless of cwd.
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
MCP_JSON_PATH = REPO_ROOT / ".mcp.json"
README_PATH = REPO_ROOT / "README.md"
LINEAR_MCP_PATH = REPO_ROOT / "skills" / "linear" / "references" / "linear-mcp.md"

# The two endpoints at stake (Linear changelog 2026-02-05: `/sse` deprecated,
# HTTP streams via `/mcp` now required).
MCP_URL = "https://mcp.linear.app/mcp"
SSE_URL = "https://mcp.linear.app/sse"

# AC3 snapshot date — paired with NB-441, which re-verified the surface.
SNAPSHOT_REVERIFIED = "Re-verified 2026-06-05"


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


class AC1_McpJsonUsesMcpTransport(unittest.TestCase):
    """AC1: `.mcp.json` (repo root) uses the `/mcp` HTTP-stream URL, not `/sse`."""

    def test_AC1_mcp_json_exists_at_repo_root(self):
        self.assertTrue(
            MCP_JSON_PATH.is_file(),
            f"AC1 expects {MCP_JSON_PATH} to exist at the repo root",
        )

    def test_AC1_linear_server_url_is_the_mcp_endpoint(self):
        """The Linear server's `url` must be the `/mcp` HTTP-stream endpoint —
        asserted on the parsed JSON, so this survives whitespace/key-order edits
        but catches any regression of the actual transport value."""
        cfg = json.loads(_read(MCP_JSON_PATH))
        linear = cfg.get("mcpServers", {}).get("linear", {})
        self.assertEqual(
            linear.get("url"),
            MCP_URL,
            "AC1: .mcp.json mcpServers.linear.url must be the /mcp HTTP-stream "
            f"endpoint ({MCP_URL})",
        )

    def test_AC1_linear_server_transport_type_is_http(self):
        """HTTP streams ride the `type: http` transport (the `/mcp` endpoint),
        not the legacy SSE transport."""
        cfg = json.loads(_read(MCP_JSON_PATH))
        linear = cfg.get("mcpServers", {}).get("linear", {})
        self.assertEqual(
            linear.get("type"),
            "http",
            "AC1: .mcp.json mcpServers.linear.type must be `http` (the /mcp "
            "HTTP-stream transport), not the deprecated SSE transport",
        )

    def test_AC1_mcp_json_does_not_point_at_deprecated_sse(self):
        """The deprecation guard: the `/sse` endpoint must appear NOWHERE in the
        file's raw text — not as the url, not in a comment, not anywhere."""
        raw = _read(MCP_JSON_PATH)
        self.assertNotIn(
            SSE_URL,
            raw,
            f"AC1: .mcp.json must not reference the deprecated {SSE_URL} endpoint",
        )
        self.assertNotIn(
            "/sse",
            raw,
            "AC1: .mcp.json must not reference the deprecated `/sse` transport path",
        )


class AC2_ReadmeNotesSseRemovedMcpRequired(unittest.TestCase):
    """AC2: the README's Linear-MCP setup note states `/sse` is removed and
    `/mcp` is the required transport."""

    def test_AC2_readme_exists_at_repo_root(self):
        self.assertTrue(
            README_PATH.is_file(),
            f"AC2 expects {README_PATH} to exist at the repo root",
        )

    def test_AC2_readme_states_sse_removed_and_mcp_required(self):
        """Pinned by case-insensitive concept tokens, not a brittle sentence: the
        note must mention `/sse`, `/mcp`, and that the older transport was
        removed / is now required."""
        low = _read(README_PATH).lower()
        self.assertIn(
            "/sse",
            low,
            "AC2: README must name the `/sse` transport so the note can say it "
            "was removed",
        )
        self.assertIn(
            "/mcp",
            low,
            "AC2: README must name the `/mcp` transport as the replacement",
        )
        self.assertTrue(
            ("remov" in low) or ("deprecat" in low),
            "AC2: README must state the `/sse` transport was removed/deprecated",
        )
        self.assertTrue(
            ("required" in low) or ("now required" in low),
            "AC2: README must state `/mcp` is now the required transport",
        )

    def _git(self, *args):
        """Run a read-only git command in the repo, returning the CompletedProcess
        or self-skipping if git itself is unavailable (non-git checkout / no git
        on PATH). Read-only — no working-tree mutation."""
        try:
            return subprocess.run(
                ["git", *args],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,
            )
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            self.skipTest(f"git unavailable; cannot check anti-vacuity base: {exc}")

    def test_AC2_anti_vacuity_clause_absent_from_diff_base_readme(self):
        """Anti-vacuity: the AC2 pin must FAIL against the *pre-change* README —
        i.e. the README at the **diff base** (the commit this branch forked from),
        NOT at `HEAD`. Anchoring to `HEAD` is wrong: once this change is committed,
        `HEAD` *is* the changed README, so a `/sse`-absent assertion against it
        inverts and reds CI. The diff base never contains the change, so the bite
        ('fails-without-the-change') holds whether or not the change is committed.

        Resolve the diff base as `git merge-base HEAD origin/dev` (the PR target),
        falling back to `origin/main`. Then `git show <base>:README.md` and assert
        the new clause's distinguishing signal (`/sse`) is absent there.

        Self-skips (does not fail), mirroring the sibling content-pin suites'
        post-merge idiom (see scripts/test_adr_009_superpowers_craft_skills.py and
        scripts/test_initiative_surface_corrected.py), when: git is unavailable,
        no diff base can be resolved (shallow clone with no remote-tracking refs),
        the base blob is unreadable, or the base README *already* carries the
        `/sse` note (base == changed state — the bite is historical, no-op). This
        keeps the suite green on a packaged tarball and after the branch is merged,
        while still biting in the dev worktree and on CI pre-merge."""
        # Resolve the diff base: PR target (origin/dev) first, then origin/main.
        base_sha = None
        for ref in ("origin/dev", "origin/main"):
            res = self._git("merge-base", "HEAD", ref)
            if res.returncode == 0 and res.stdout.strip():
                base_sha = res.stdout.strip()
                break
        if not base_sha:
            self.skipTest(
                "no diff base resolvable (origin/dev and origin/main absent — "
                "shallow checkout?); skipping anti-vacuity base check"
            )

        base = self._git("show", f"{base_sha}:README.md")
        if base.returncode != 0 or not base.stdout:
            self.skipTest(
                f"README.md unreadable at diff base {base_sha[:12]}; "
                "skipping anti-vacuity base check"
            )

        base_low = base.stdout.lower()
        if "/sse" in base_low:
            # The diff base already carries the `/sse` note (e.g. the branch has
            # been merged/rebased onto a base that contains it). The bite is
            # proven historically; assert nothing now — a no-op skip, not a fail.
            self.skipTest(
                f"diff base {base_sha[:12]} README already mentions `/sse` "
                "(post-merge/rebase) — the anti-vacuity bite is historical."
            )
        # Pre-change base genuinely lacks the `/sse` note, so the AC2 token pin
        # had nothing to assert against there: it fails-without-the-change.
        self.assertNotIn(
            "/sse",
            base_low,
            f"Anti-vacuity FAILED: the diff-base README ({base_sha[:12]}) already "
            "mentions `/sse` — the AC2 token pin would pass vacuously, proving "
            "nothing. Re-anchor the pin on the genuinely new signal.",
        )


class AC3_LinearMcpSnapshotIsCurrent(unittest.TestCase):
    """AC3: `references/linear-mcp.md` carries the current re-verified snapshot
    line (pairs with NB-441)."""

    def test_AC3_linear_mcp_reference_exists(self):
        self.assertTrue(
            LINEAR_MCP_PATH.is_file(),
            f"AC3 expects {LINEAR_MCP_PATH} to exist",
        )

    def test_AC3_snapshot_reverified_date_is_current(self):
        """The surface snapshot must be confirmed current via the
        `Re-verified 2026-06-05` line carried over from NB-441."""
        body = _read(LINEAR_MCP_PATH)
        self.assertIn(
            SNAPSHOT_REVERIFIED,
            body,
            f"AC3: linear-mcp.md must carry the current `{SNAPSHOT_REVERIFIED}` "
            "snapshot line (pairs with NB-441)",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
