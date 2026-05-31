"""Structural regression test for NB-395 (conversion-rewrite of `README.md`).

NB-395's seven acceptance criteria are all `[review]` (editorial judgement on
marketing prose) — none is a `[test]` AC provable by a runnable command. This
file does *not* try to grade the prose. Instead it gives each AC a **structural
regression guard**: it asserts that the load-bearing artifact behind each AC —
a stable section heading and the concept tokens that carry the claim — is
*present* in `README.md` at the repo root, so a future edit cannot silently
drop the category claim, the subscription hook, the demo slot, the status
section, the quickstart, or the roadmap/open-questions section.

Design rule (the #1 docs-test trap): assert ROBUST invariants — headings and
case-insensitive concept tokens — NOT brittle marketing sentences, which will
be reworded over time and must not break the suite. Headings are stable; exact
copy is not.

One test method per AC, named so a failure says which AC regressed. Plus one
regression guard: `NB-396` is a Linear id and must live only in the HTML demo
placeholder comment — it must never appear as a markdown link to a GitHub
issues URL.

Discoverable by `python -m unittest discover -s scripts` (how CI runs the
suite). Also runnable directly:  python scripts/test_readme_convert.py
"""

import pathlib
import re
import unittest


# Same idiom as scripts/test_release_linear_summary.py: resolve the repo root
# relative to this file so the test reads the repo-root README regardless of cwd.
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
README_PATH = REPO_ROOT / "README.md"


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def _lead(text: str, n: int = 15) -> str:
    """The lead — first `n` non-empty lines — where the category claim must sit
    (AC#1 requires it up top, 'not a feature list')."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    return "\n".join(lines[:n])


def _has_heading(text: str, *needles: str) -> bool:
    """True if any markdown ATX heading line (`#`..`######`) contains every
    needle (case-insensitive). Matching the heading — not the surrounding prose —
    is what keeps these assertions robust to copy edits."""
    for line in text.splitlines():
        if not re.match(r"^#{1,6}\s+", line):
            continue
        low = line.lower()
        if all(n.lower() in low for n in needles):
            return True
    return False


class Readme_Exists(unittest.TestCase):
    def test_readme_exists_at_repo_root(self):
        self.assertTrue(
            README_PATH.is_file(), f"{README_PATH} must exist at the repo root"
        )


class AC1_CategoryClaimFirst(unittest.TestCase):
    """AC#1: opens with the category claim — an *agent team* running *Scrum*,
    *any problem type*, on a *subscription* not *API tokens* — in the first
    sentences (not a feature list)."""

    def test_AC1_lead_carries_the_category_claim_tokens(self):
        lead = _lead(_read(README_PATH)).lower()
        for token in ("team", "scrum", "subscription"):
            self.assertIn(
                token,
                lead,
                f"AC#1: the lead (first ~15 lines) must carry the category-claim "
                f"token '{token}' — the opening must be the claim, not a feature list",
            )

    def test_AC1_lead_contrasts_subscription_with_api(self):
        """The claim's contrast is 'subscription, NOT API tokens' — assert the
        anti-pole is present in the lead, tolerant of wording ('API tokens' or
        'not API')."""
        lead = _lead(_read(README_PATH)).lower()
        self.assertTrue(
            ("api token" in lead) or ("not api" in lead),
            "AC#1: the lead must state the contrast against API tokens "
            "('API tokens' or 'not API')",
        )


class AC2_WhyNotOthers(unittest.TestCase):
    """AC#2: a short 'why backlogd vs the others / vs Cyrus' section."""

    def test_AC2_why_backlogd_heading_present(self):
        text = _read(README_PATH)
        self.assertTrue(
            _has_heading(text, "why", "backlogd"),
            "AC#2: a '## Why backlogd ...'-style heading must exist",
        )

    def test_AC2_names_cyrus_as_the_comparison(self):
        text = _read(README_PATH).lower()
        self.assertIn(
            "cyrus",
            text,
            "AC#2: the why-not-others section must name Cyrus specifically",
        )


class AC3_DemoSlot(unittest.TestCase):
    """AC#3: a clearly-marked demo slot near the top — a 'Watch it work' section
    plus the NB-396 HTML placeholder comment, ready to fill when the asset lands."""

    def test_AC3_watch_it_work_heading_present(self):
        text = _read(README_PATH)
        self.assertTrue(
            _has_heading(text, "watch it work"),
            "AC#3: a '## Watch it work' demo-slot heading must exist",
        )

    def test_AC3_nb396_placeholder_comment_present(self):
        """The slot must reserve the spot with an HTML comment naming NB-396, so
        the demo asset (which lands with NB-396) has a marked home."""
        text = _read(README_PATH)
        self.assertRegex(
            text,
            r"<!--[^>]*NB-396",
            "AC#3: an HTML comment naming NB-396 must reserve the demo slot",
        )


class AC4_HonestStatus(unittest.TestCase):
    """AC#4: an honest status section — what works today vs roadmap; links
    docs/ROADMAP.md."""

    def test_AC4_status_heading_present(self):
        text = _read(README_PATH)
        self.assertTrue(
            _has_heading(text, "status"),
            "AC#4: a '## Status'-style heading must exist",
        )

    def test_AC4_status_conveys_shipped_state_version_agnostic(self):
        """Honest status must convey what has shipped — version-agnostic, so a
        release bump never makes the README (or this test) go stale. The exact
        version lives in GitHub Releases + plugin.json, not pinned in prose."""
        text = _read(README_PATH).lower()
        for token in ("dogfooded", "gates", "shipped"):
            self.assertIn(
                token,
                text,
                f"AC#4: status must convey shipped state (missing '{token}')",
            )

    def test_AC4_links_roadmap(self):
        text = _read(README_PATH)
        self.assertIn(
            "docs/ROADMAP.md",
            text,
            "AC#4: status must link docs/ROADMAP.md (the what-works-vs-roadmap source)",
        )


class AC5_Quickstart(unittest.TestCase):
    """AC#5: a quickstart — marketplace install `/plugin install backlogd`; the
    `problem` label + Linear MCP prerequisites."""

    def test_AC5_quickstart_or_install_heading_present(self):
        text = _read(README_PATH)
        self.assertTrue(
            _has_heading(text, "quickstart") or _has_heading(text, "install"),
            "AC#5: a '## Quickstart' (or '## Install') heading must exist",
        )

    def test_AC5_marketplace_install_command_present(self):
        text = _read(README_PATH)
        self.assertIn(
            "/plugin install backlogd",
            text,
            "AC#5: quickstart must give the marketplace install command "
            "`/plugin install backlogd`",
        )

    def test_AC5_names_problem_label_and_linear_mcp_prereqs(self):
        text = _read(README_PATH)
        self.assertIn(
            "problem",
            text,
            "AC#5: quickstart must name the `problem` label prerequisite",
        )
        self.assertIn(
            "Linear MCP",
            text,
            "AC#5: quickstart must name the Linear MCP prerequisite",
        )


class AC6_SubscriptionNotApiHook(unittest.TestCase):
    """AC#6: the 'runs on subscription, not API' hook stated prominently — its
    own section; official Linear MCP / OAuth."""

    def test_AC6_subscription_section_heading_present(self):
        text = _read(README_PATH)
        self.assertTrue(
            _has_heading(text, "subscription"),
            "AC#6: the subscription hook must have its own heading "
            "(e.g. '## Runs on your subscription, not API tokens')",
        )

    def test_AC6_subscription_section_names_linear_mcp_and_oauth(self):
        """The hook's substance is the official Linear MCP over OAuth — assert
        both concept tokens are present so the differentiator is actually
        explained, not just headlined."""
        text = _read(README_PATH)
        self.assertIn(
            "Linear MCP",
            text,
            "AC#6: the subscription hook must reference the official Linear MCP",
        )
        self.assertRegex(
            text,
            r"OAuth",
            "AC#6: the subscription hook must reference OAuth (the keyless auth path)",
        )


class AC7_RoadmapOpenQuestions(unittest.TestCase):
    """AC#7: a 'Roadmap / open questions' section — the GitHub Action
    `label_trigger`; the Linear-on-CI auth question incl. the PAT trade-off."""

    def test_AC7_roadmap_heading_present(self):
        text = _read(README_PATH)
        self.assertTrue(
            _has_heading(text, "roadmap"),
            "AC#7: a '## Roadmap ...'-style heading must exist",
        )

    def test_AC7_names_label_trigger_github_action_variant(self):
        text = _read(README_PATH)
        self.assertIn(
            "label_trigger",
            text,
            "AC#7: roadmap must name the claude-code-action `label_trigger` "
            "(the GitHub Action variant)",
        )

    def test_AC7_names_linear_on_ci_pat_tradeoff(self):
        """The open question's honesty hinges on naming the PAT trade-off (a PAT
        would break the no-keys principle) — assert PAT is present."""
        text = _read(README_PATH)
        self.assertIn(
            "PAT",
            text,
            "AC#7: roadmap must name the PAT trade-off in the Linear-on-CI "
            "auth open question",
        )


class Regression_NB396IsNotAGithubIssueLink(unittest.TestCase):
    """Regression guard: NB-396 is a *Linear* id. The demo slot reserves it in an
    HTML comment only (AC#3); it must never be rewritten into a markdown link to
    a GitHub issues URL (a tempting but wrong 'fix' that would point readers at a
    nonexistent GitHub issue #396)."""

    def test_NB396_not_linked_to_github_issues(self):
        text = _read(README_PATH)
        # No markdown link whose visible text is NB-396 pointing at an http(s) URL.
        self.assertNotRegex(
            text,
            r"\[NB-396\]\(http",
            "Regression: NB-396 must stay in the HTML demo-placeholder comment, "
            "not become a markdown link (e.g. to github.com/...issues)",
        )
        # Belt-and-braces: also assert no NB-396 -> github issues URL pairing on a
        # single line, in case the link text differs from the id.
        for line in text.splitlines():
            if "NB-396" in line and re.search(
                r"github\.com/[^)\s]*issues", line, re.IGNORECASE
            ):
                self.fail(
                    "Regression: a line couples NB-396 with a github.com issues URL — "
                    f"NB-396 is a Linear id and must not link to GitHub issues:\n  {line.strip()}"
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
