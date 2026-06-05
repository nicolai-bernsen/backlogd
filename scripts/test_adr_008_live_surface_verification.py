"""Contract test for ADR-008 — live-surface verification (NB-423).

Why this file exists — the gap it closes
-----------------------------------------
``test_standards_index.py::IndexDriftTest`` proves the committed index is *consistent*
with the corpus (it rebuilds byte-for-byte) and that every ADR carries the required
front-matter keys. ``test_adr_003_workspace_config.py::test_AC1_filename_is_the_next_free_number``
proves the ADR-NNN numbers are *contiguous* (transitively: ADR-008 is the next free
number). None of those pin **ADR-008's membership or substance**: delete the ADR-008
file *and* its ``index.json`` entry and every existing test still passes — the drift
guard sees a (smaller) corpus that still matches a (smaller) index, and the contiguity
check sees ``[1..7]`` which is still gap-free. So nothing asserts that an Accepted
ADR-008 carrying *this* standard is actually present, scoped to catch external-surface
changes, additive (supersedes nothing), and accompanied by the bounded reconciliation
the AC names.

This pins exactly that — facts about committed artifacts a reviewer reads, mapped 1:1
to the testable ACs of NB-423:

* **AC1 (structural half)** — the ADR exists at ``ADR-008-live-surface-verification.md``,
  carries the five required headings, a one-line TL;DR, a bold lead-in title (NOT a
  second ``# H1`` — MD025), the ``NB-423`` ref, and ``id: ADR-008`` / ``status: Accepted``
  / ``supersedes: ~`` front-matter; and its assertion names the four external surfaces
  (MCP / API / UI / OAuth) **and** the live-evidence-vs-``created``/``200`` distinction.
* **AC3** — ``applies-to`` selects the ADR for an external-surface change: ``domains``
  includes ``linear``; ``decision-types`` cover the surface kinds; ``file-patterns``
  reach ``skills/linear/**``, ``commands/**``, ``scripts/linear_setup.py``, and
  ``docs/guides/*-setup.md``.
* **AC4** — the emitted index lists ADR-008 as ``"status": "Accepted"`` (membership +
  governs), and the ADR supersedes nothing (``supersedes: ~`` / no ``superseded-by``
  written onto any other ADR by this change — see ``test_no_existing_assertion_dropped``).
* **AC5** — the known false external-surface assumptions are reconciled where the AC
  names them: the NB-421 silently-dropped-label correction is present in
  ``commands/scope.md`` and ``linear-mcp.md``; the retro project-thread dedupe is
  reconciled to the verified-live ``list_comments({ projectId })`` finding; the
  agent-identity guide carries its 2026-06-02 corrections; ``docs/README.md`` lists
  ADR-008.

It deliberately asserts the *substance* (load-bearing tokens), not exact wording — it is
not a byte-for-byte echo of the assertion or the prose (that would be a tautology against
the same artifacts the drift test already guards). Whether the ADR's decision is *sound*,
whether the prose is *agent-read concise*, and whether the reconciliation reads *well*
stay the reviewer's call ([review]); this only proves the rule + its scope + its
reconciliation are on the books.

CI runs ``python3 -m unittest discover -s scripts -p 'test_*.py'`` from the repo root
(see .github/workflows/ci.yml), so this lives in scripts/ as a stdlib unittest. It does
NOT do a git-diff / whole-worktree footprint scan (that pattern is the tracked NB-418 bug
that false-fails every other unit's local suite); membership and supersession are pinned
against the committed artifacts instead.

Run from the repo root:
    python -m pytest scripts/test_adr_008_live_surface_verification.py
    python scripts/test_adr_008_live_surface_verification.py
    python -m pytest scripts -k ADR008
"""

import json
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
ADR_DIR = REPO_ROOT / "docs" / "standards" / "adrs"
ADR = ADR_DIR / "ADR-008-live-surface-verification.md"
INDEX = REPO_ROOT / "docs" / "standards" / "index.json"

SCOPE_MD = REPO_ROOT / "commands" / "scope.md"
LINEAR_MCP_MD = REPO_ROOT / "skills" / "linear" / "references" / "linear-mcp.md"
RETRO_SKILL_MD = REPO_ROOT / "skills" / "retro" / "SKILL.md"
AGENT_IDENTITY_MD = REPO_ROOT / "docs" / "guides" / "agent-identity-setup.md"
DOCS_README_MD = REPO_ROOT / "docs" / "README.md"

# The five headings backlogd's ADR shape requires (kept in lockstep with
# test_adr_005/006/007 and TEMPLATE.md).
REQUIRED_HEADINGS = ["Status", "Context", "Considered Options", "Decision", "Consequences"]


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def _front_matter(p: pathlib.Path) -> str:
    """Return the raw `---`-fenced front-matter block of an ADR (between the fences)."""
    body = _read(p)
    parts = body.split("---\n", 2)
    assert len(parts) >= 3, f"{p.name}: front-matter must be a closed `---` block"
    return parts[1]


class AC1_AdrArtifactLands(unittest.TestCase):
    """AC1 (structural half): a committed ADR exists at ADR-008 with the five required
    headings, a one-line TL;DR, a bold lead-in title (not a second `# H1`), the NB-423
    ref, and `id: ADR-008` / `status: Accepted` / `supersedes: ~` front-matter. (Whether
    the prose is a *good*, *concise* decision is the reviewer's call — AC6 [review].)"""

    def test_adr_file_exists_at_expected_path(self):
        self.assertTrue(
            ADR.is_file(),
            f"AC1: the ADR must exist at {ADR} — the next free number is ADR-008.",
        )

    def test_carries_all_five_required_headings(self):
        body = _read(ADR)
        for heading in REQUIRED_HEADINGS:
            pattern = re.compile(r"^#{1,6}\s+.*" + re.escape(heading), re.MULTILINE)
            self.assertRegex(
                body, pattern, f"AC1: ADR-008 is missing required heading: {heading!r}",
            )

    def test_carries_one_line_tldr(self):
        self.assertIn(
            "Decision (TL;DR):", _read(ADR),
            "AC1: ADR-008 must carry a one-line `Decision (TL;DR):` (front-loaded decision).",
        )

    def test_carries_problem_ref_nb423(self):
        self.assertIn(
            "NB-423", _read(ADR), "AC1: ADR-008 must reference its problem NB-423.",
        )

    def test_body_opens_with_bold_lead_in_not_a_second_h1(self):
        """AC1/AC6: TEMPLATE.md mandates a **bold lead-in** title, NOT a second `# H1`
        (a `# heading` would duplicate the front-matter title and trip MD025). Assert the
        body after the front-matter has no top-level `# ` ATX heading."""
        body = _read(ADR)
        after_fm = body.split("---\n", 2)[2]
        offending = [
            ln for ln in after_fm.splitlines()
            if re.match(r"^#\s+\S", ln)  # exactly one '#' then text == H1
        ]
        self.assertEqual(
            offending, [],
            "AC1/AC6: ADR body must use a bold lead-in title, not a second `# H1` "
            f"(MD025); found H1 line(s): {offending}",
        )

    def test_frontmatter_identifies_accepted_adr008_superseding_nothing(self):
        body = _read(ADR)
        self.assertTrue(
            body.startswith("---\n"),
            "AC1: ADR must open with a `---`-fenced YAML front-matter block (TEMPLATE.md).",
        )
        front = _front_matter(ADR)
        self.assertIn("id: ADR-008", front, "AC1: front-matter `id` must be `ADR-008`.")
        self.assertRegex(
            front, r"status:\s*Accepted",
            "AC1: ADR-008 must be `status: Accepted` (an Accepted ADR governs).",
        )
        self.assertRegex(
            front, r"problem:\s*NB-423", "AC1: front-matter must carry `problem: NB-423`.",
        )
        # AC4 (corpus side): this ADR supersedes nothing — `supersedes: ~`.
        self.assertRegex(
            front, r"supersedes:\s*~",
            "AC4: ADR-008 must carry `supersedes: ~` (it adds a rule, replaces none).",
        )


class AC1_AssertionDefinesTheRule(unittest.TestCase):
    """AC1 (substance): the one-sentence assertion must name (a) the four external
    surfaces, (b) what live evidence is — and is NOT (a mocked test / a bare
    `created`/`200`), and (c) the unverified-assumption fallback. Substance, not exact
    wording: each clause passes if ANY of its tokens is present, so a reworded-but-intact
    assertion passes and a dropped clause fails. Read from the committed index (the
    artifact a reviewer reads first) so a regeneration that dropped a clause is caught."""

    @classmethod
    def setUpClass(cls):
        index = json.loads(INDEX.read_text(encoding="utf-8"))
        cls.by_id = {e["id"]: e for e in index["standards"]}

    def test_assertion_names_the_four_external_surfaces(self):
        assertion = self.by_id["ADR-008"]["assertion"].lower()
        surfaces = {
            "Linear MCP tool surface": ("mcp",),
            "Linear REST/GraphQL API": ("api",),
            "Linear UI": ("ui",),
            "OAuth/install flow": ("oauth", "install"),
        }
        missing = [
            label for label, toks in surfaces.items()
            if not any(t in assertion for t in toks)
        ]
        self.assertEqual(
            missing, [],
            "AC1: ADR-008's assertion must name all four external surfaces; "
            f"missing: {missing}\nassertion was: {self.by_id['ADR-008']['assertion']!r}",
        )

    def test_assertion_defines_live_evidence_and_excludes_mock_and_bare_success(self):
        assertion = self.by_id["ADR-008"]["assertion"].lower()
        clauses = {
            "live evidence required": ("live evidence", "live probe", "round-trip", "round trip"),
            "screenshot counts": ("screenshot",),
            "NOT a mocked test": ("mocked test", "mock test", "mocked"),
            "NOT a bare created/200": ("created", "200"),
            "before Done": ("done",),
            "unverified-assumption fallback": ("unverified", "assumption"),
        }
        missing = [
            label for label, toks in clauses.items()
            if not any(t in assertion for t in toks)
        ]
        self.assertEqual(
            missing, [],
            "AC1: ADR-008's assertion must define live evidence (probe/screenshot/"
            "round-trip), exclude a mocked test and a bare `created`/`200`, bind it "
            "before Done, and give the unverified-assumption fallback; "
            f"missing clause(s): {missing}\nassertion was: "
            f"{self.by_id['ADR-008']['assertion']!r}",
        )


class AC3_ScopeSelectsExternalSurfaceChanges(unittest.TestCase):
    """AC3: the reviewer's index-first walk must select ADR-008 for an external-surface
    change. Pin that `applies-to` actually reaches the named surfaces — `domains`
    includes `linear`, `decision-types` cover the surface kinds, and `file-patterns`
    reach `skills/linear/**`, `commands/**`, `scripts/linear_setup.py`, and
    `docs/guides/*-setup.md`. Read from the committed index, so a regeneration that
    narrowed the scope (making the rule un-findable) fails here. (Whether the chosen
    axes are the *best* set is [review].)"""

    @classmethod
    def setUpClass(cls):
        index = json.loads(INDEX.read_text(encoding="utf-8"))
        cls.scope = {e["id"]: e["applies-to"] for e in index["standards"]}["ADR-008"]

    def test_domains_include_linear(self):
        domains = {d.lower() for d in self.scope.get("domains", [])}
        self.assertIn(
            "linear", domains,
            f"AC3: applies-to.domains must include `linear`; got {sorted(domains)}",
        )

    def test_decision_types_cover_the_surface_kinds(self):
        dtypes = {d.lower() for d in self.scope.get("decision-types", [])}
        # At least one decision-type that names the external-surface lane.
        self.assertTrue(
            dtypes & {
                "external-surface-claim", "live-evidence", "mcp-behavior",
                "api-behavior", "ui-behavior", "oauth-flow",
            },
            "AC3: applies-to.decision-types must cover the external-surface kinds "
            f"(mcp/api/ui/oauth/live-evidence); got {sorted(dtypes)}",
        )

    def test_file_patterns_reach_every_named_surface(self):
        patterns = list(self.scope.get("file-patterns", []))
        required = [
            "skills/linear/**",
            "commands/**",
            "scripts/linear_setup.py",
            "docs/guides/*-setup.md",
        ]
        missing = [p for p in required if p not in patterns]
        self.assertEqual(
            missing, [],
            "AC3: applies-to.file-patterns must reach every named surface so the "
            f"reviewer selects ADR-008 for the change; missing: {missing}; "
            f"got {patterns}",
        )


class AC4_MembershipAndSupersedesNothing(unittest.TestCase):
    """AC4: the emitted index lists ADR-008 as Accepted (membership — deleting the ADR +
    its index entry must fail HERE, not pass silently), the ADR supersedes nothing, and
    no existing Accepted ADR was marked superseded-by-008 (superseding, if any, is
    additive — here there is none)."""

    @classmethod
    def setUpClass(cls):
        index = json.loads(INDEX.read_text(encoding="utf-8"))
        cls.index = index
        cls.by_id = {e["id"]: e for e in index["standards"]}

    def test_adr008_present_in_index(self):
        self.assertIn(
            "ADR-008", self.by_id,
            "AC4: the standards index must contain ADR-008 — regenerate with "
            "`python scripts/standards_index.py` after adding the ADR.",
        )

    def test_adr008_status_accepted_in_index(self):
        self.assertEqual(
            self.by_id["ADR-008"]["status"], "Accepted",
            "AC4: the emitted index must list ADR-008 with `\"status\": \"Accepted\"` "
            "(a non-Accepted entry would not govern).",
        )

    def test_no_existing_adr_marked_superseded_by_008(self):
        """AC4: ADR-008 supersedes nothing, so no *other* ADR in the index may carry a
        `Superseded by ADR-008` status. (ADR-001/005 are legitimately superseded by
        ADR-006 — that is allowed; only a *new* supersession-by-008 would be wrong.)"""
        offenders = [
            e["id"] for e in self.index["standards"]
            if e["id"] != "ADR-008" and "ADR-008" in str(e.get("status", ""))
        ]
        self.assertEqual(
            offenders, [],
            "AC4: ADR-008 must supersede nothing, but these ADRs are marked "
            f"superseded-by-ADR-008 in the index: {offenders}",
        )


class AC5_KnownFalseAssumptionsReconciled(unittest.TestCase):
    """AC5: the known false external-surface assumptions are reconciled where the AC
    names them. Each is a fact about the committed source a reviewer reads — the
    correction string is present. (Whether each correction is *complete* is [review].)"""

    def test_scope_md_carries_nb421_label_drop_correction(self):
        body = _read(SCOPE_MD).lower()
        self.assertIn(
            "silently drop", body,
            "AC5: commands/scope.md must carry the NB-421 correction — `save_issue` "
            "does NOT auto-create labels, an unknown name is silently dropped.",
        )

    def test_linear_mcp_carries_silently_dropped_label_pitfall(self):
        body = _read(LINEAR_MCP_MD).lower()
        self.assertIn(
            "silently drop", body,
            "AC5: linear-mcp.md must carry the silently-dropped-label pitfall (the "
            "NB-421 finding).",
        )

    def test_retro_skill_reconciles_project_thread_dedupe_to_verified_live(self):
        """AC5: the retro project-thread `list_comments` dedupe is reconciled to the
        verified-live finding — `list_comments({ projectId })` lists the thread (probe
        2026-06-03), NOT the stale 'issues only' assumption. Assert the verified-live
        marker and the projectId-listing claim are both present."""
        body = _read(RETRO_SKILL_MD)
        self.assertIn(
            "list_comments({ projectId })", body,
            "AC5: skills/retro/SKILL.md must reference `list_comments({ projectId })` "
            "for the no-milestone project-thread dedupe path.",
        )
        self.assertRegex(
            body, r"[Vv]erified live 2026-06-03",
            "AC5: the retro project-thread dedupe must be marked verified-live "
            "2026-06-03 (the live-probe flip), not left as an unverified assumption.",
        )

    def test_agent_identity_guide_carries_2026_06_corrections(self):
        """AC5: docs/guides/agent-identity-setup.md carries its live-run corrections —
        the 'Verified — first live run' marker, the percent-encoded authorize URL, and
        the harmless-redirect note."""
        body = _read(AGENT_IDENTITY_MD)
        self.assertIn(
            "Verified — first live run", body,
            "AC5: agent-identity-setup.md must carry the 'Verified — first live run' "
            "marker (the 2026-06-02 corrections).",
        )
        self.assertIn(
            "%2C", body,
            "AC5: agent-identity-setup.md must keep the authorize URL percent-encoded "
            "(`%2C` for `,`) — the unencoded form broke the live install.",
        )

    def test_docs_readme_lists_adr008(self):
        body = _read(DOCS_README_MD)
        self.assertIn(
            "ADR-008", body,
            "AC5: docs/README.md's ADR list must include ADR-008 (it was stuck at "
            "ADR-004 before this change).",
        )


# --- ACs that are NOT mechanically testable here (named, not faked) ------------
#
# Listed so the coverage gap is explicit, not silent.
#
# AC2 [test] — `standards_index.py --check` exits 0 AND `pytest test_standards_index.py`
#              exits 0. Already covered: test_standards_index.py::IndexDriftTest rebuilds
#              the index from the corpus and asserts the committed index matches
#              byte-for-byte, and `validate()` runs on the real corpus. Re-asserting it
#              here would duplicate that guard — not done.
# AC1/AC6 [review] — whether the ADR's prose is a *sound*, *agent-read concise* decision
#              (front-loaded, terse, good tables) is the reviewer's judgement, not a
#              string a runner can prove without becoming a tautology. The structural
#              shape + the assertion's load-bearing tokens ARE pinned above.
# AC6 [test-ish] — `npx markdownlint-cli2 docs/standards/adrs/` exits 0 (MD025/MD060/
#              MD049). Run by the dev markdown gate / CI, not re-shelled from a unittest
#              (the suite is stdlib-only and must not require node). The MD025 "no second
#              # H1" half is independently pinned by
#              AC1_AdrArtifactLands::test_body_opens_with_bold_lead_in_not_a_second_h1.


if __name__ == "__main__":
    unittest.main(verbosity=2)
