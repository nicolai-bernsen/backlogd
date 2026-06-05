"""Content drift tests for NB-441 — correct the stale "no Initiative-write MCP tool"
claim and document the initiative + status-update surface (docs-only `[review]` unit).

Each AC bullet that names a corrected/added claim is proven by a file-existence +
content assertion on the markdown sources, mapped 1:1 to the unit's acceptance criteria.
This is a *drift* guard with two halves per claim:

* **positive** — the corrected/new string is present (proves the change landed), and
* **anti-regression** — the stale "no Initiative-write tool / created manually" framing
  is GONE and must not creep back.

Anti-vacuity is established against the pre-change base (`git diff HEAD` at authoring
time): `docs/scrum/mapping.md` carried "the official Linear MCP has no Initiative-write
tool", `skills/linear/SKILL.md` carried "no initiative-write tool" + "Create/attach the
Initiative manually", and `references/linear-mcp.md` omitted the five tools entirely — so
each positive assertion below failed against the base and passes only with the fix, and
each anti-regression assertion would fail if the stale framing returned.

This is a sibling to `test_documents_and_updates_ref.py` (it does NOT edit that file's
pinned assertions — in particular the `Surface snapshot: 2026-05-28` baseline line is
left untouched; AC6 here pins the *added* re-verification date, not a replacement of the
baseline token).

Whether the corrected prose reads well / is agent-concise stays the reviewer's call
([review]); this pins only that each claim is on the books and the stale one is gone.

Run from the repo root:  python -m unittest scripts.test_initiative_surface_corrected -v
"""

import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL_PATH = REPO_ROOT / "skills" / "linear" / "SKILL.md"
MAPPING_PATH = REPO_ROOT / "docs" / "scrum" / "mapping.md"
LINEAR_MCP_PATH = REPO_ROOT / "skills" / "linear" / "references" / "linear-mcp.md"
DOCS_UPDATES_PATH = REPO_ROOT / "skills" / "linear" / "references" / "documents-and-updates.md"
LINEAR_MODEL_PATH = REPO_ROOT / "skills" / "linear" / "references" / "linear-model.md"

# The five tools the corrected surface must name (AC2).
NEW_TOOLS = [
    "save_initiative",
    "list_initiatives",
    "save_status_update",
    "get_status_updates",
    "delete_status_update",
]

# Stale framings that must NOT survive anywhere the claim lived (AC1/AC5 anti-regression).
# Matched case-insensitively so a re-capitalised variant can't slip back in.
STALE_PHRASES = [
    "no initiative-write tool",
    "no initiative-write mcp tool",
    "has no initiative-write",
    "created/attached manually",
    "create/attach the initiative manually",
]


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


class AC1_ProductGoalRowReflectsSaveInitiative(unittest.TestCase):
    """AC1: the canonical home of the claim — the *Commitment: Product Goal* row in
    `docs/scrum/mapping.md` (the README itself carries no Initiative claim) — no longer
    says initiatives lack an MCP write tool, and names `save_initiative` as the wired
    path."""

    def test_AC1_mapping_file_exists(self):
        self.assertTrue(MAPPING_PATH.is_file(), f"AC1 expects {MAPPING_PATH} to exist")

    def test_AC1_mapping_names_save_initiative_as_wired_path(self):
        body = _read(MAPPING_PATH)
        self.assertIn(
            "save_initiative",
            body,
            "AC1: the Product Goal row must name `save_initiative` as the wired write path "
            "for the engagement Initiative.",
        )

    def test_AC1_mapping_no_longer_claims_no_write_tool(self):
        body = _read(MAPPING_PATH).lower()
        for stale in STALE_PHRASES:
            self.assertNotIn(
                stale,
                body,
                f"AC1 (anti-regression): docs/scrum/mapping.md still carries the stale "
                f"framing {stale!r} — initiatives are MCP-writable via save_initiative.",
            )


class AC2_SurfaceTableAddsTheFiveTools(unittest.TestCase):
    """AC2: `references/linear-mcp.md` surface table adds the five initiative +
    status-update tools with their params (Initiatives + Status updates rows)."""

    def test_AC2_linear_mcp_file_exists(self):
        self.assertTrue(LINEAR_MCP_PATH.is_file(), f"AC2 expects {LINEAR_MCP_PATH} to exist")

    def test_AC2_all_five_tool_names_present(self):
        body = _read(LINEAR_MCP_PATH)
        missing = [t for t in NEW_TOOLS if t not in body]
        self.assertEqual(
            missing,
            [],
            f"AC2: linear-mcp.md must name every initiative + status-update tool in the "
            f"surface table; missing: {missing}",
        )

    def test_AC2_has_initiatives_surface_row(self):
        body = _read(LINEAR_MCP_PATH)
        self.assertIn(
            "**Initiatives**",
            body,
            "AC2: the surface table must carry an **Initiatives** row.",
        )

    def test_AC2_has_status_updates_surface_row(self):
        body = _read(LINEAR_MCP_PATH)
        self.assertIn(
            "**Status updates**",
            body,
            "AC2: the surface table must carry a **Status updates** row.",
        )

    def test_AC2_save_initiative_params_documented(self):
        body = _read(LINEAR_MCP_PATH)
        # Params verified live on the issue: the status enum is its OWN enum (a load-bearing
        # gotcha — not workflow-state categories), and create requires `name`.
        for token in ("name", "Planned", "Active", "Completed"):
            self.assertIn(
                token,
                body,
                f"AC2: save_initiative params must document {token!r} "
                "(name required on create; status is its own Planned/Active/Completed enum).",
            )

    def test_AC2_save_status_update_params_documented(self):
        body = _read(LINEAR_MCP_PATH)
        # type is required and project|initiative; health is the typed enum.
        for token in ("onTrack", "atRisk", "offTrack"):
            self.assertIn(
                token,
                body,
                f"AC2: save_status_update params must document the health enum value "
                f"{token!r}.",
            )


class AC3_StatusUpdateIdempotencyRule(unittest.TestCase):
    """AC3: the read → capture-`id` → write idempotency rule is documented for status
    updates (use get_status_updates, pass id, or you stack duplicate updates) — the same
    rule already stated for issues/comments."""

    def test_AC3_idempotency_rule_present_in_linear_mcp(self):
        body = _read(LINEAR_MCP_PATH)
        # The rule names the read call AND the duplicate-stacking failure it prevents.
        self.assertIn(
            "get_status_updates",
            body,
            "AC3: linear-mcp.md must name `get_status_updates` as the read step of the "
            "status-update idempotency rule.",
        )
        self.assertIn(
            "stack",
            body.lower(),
            "AC3: linear-mcp.md must state that omitting the `id` stacks duplicate "
            "status updates (the failure the read→capture-id→write rule prevents).",
        )


class AC4_StatusUpdateIsTypedSiblingWriteHealthOneWay(unittest.TestCase):
    """AC4: `save_status_update` is documented as the typed sibling of `save_project`'s
    health field, cross-referenced so health is never written two ways. The "write health
    one way" warning must appear in BOTH linear-mcp.md and documents-and-updates.md."""

    def test_AC4_linear_mcp_names_typed_health_write(self):
        body = _read(LINEAR_MCP_PATH)
        self.assertIn(
            "save_status_update",
            body,
            "AC4: linear-mcp.md must name save_status_update as the typed health write.",
        )
        self.assertIn(
            "typed",
            body.lower(),
            "AC4: linear-mcp.md must frame save_status_update as the *typed* "
            "sibling/write for health.",
        )

    def test_AC4_linear_mcp_write_health_one_way(self):
        body = _read(LINEAR_MCP_PATH).lower()
        self.assertIn(
            "write health",
            body,
            "AC4: linear-mcp.md must carry the 'write health one way' cross-reference.",
        )
        # The point of the cross-ref: never both channels for the same transition.
        self.assertIn(
            "one",
            body,
            "AC4: the write-health warning must say to write health ONE way.",
        )

    def test_AC4_documents_updates_write_health_one_way(self):
        body = _read(DOCS_UPDATES_PATH).lower()
        self.assertIn(
            "write health",
            body,
            "AC4: documents-and-updates.md must carry the 'write health one way' "
            "cross-reference so the comment shape and save_status_update don't both fire.",
        )
        self.assertIn(
            "save_status_update",
            _read(DOCS_UPDATES_PATH),
            "AC4: documents-and-updates.md must point at the typed save_status_update "
            "as the preferred health write (comment shape becomes the legacy fallback).",
        )

    def test_AC4_documents_updates_marks_comment_shape_legacy(self):
        body = _read(DOCS_UPDATES_PATH).lower()
        self.assertIn(
            "legacy fallback",
            body,
            "AC4: documents-and-updates.md must mark the project-thread-comment health "
            "shape the 'legacy fallback', not a parallel channel.",
        )


class AC5_SkillNoLongerFlagsInitiativeNotWired(unittest.TestCase):
    """AC5: `skills/linear/SKILL.md` 'Current state vs target' (the Engagement = Initiative
    bullet) no longer flags it as not-yet-wired, and states the MCP exposes
    save_initiative."""

    def test_AC5_skill_file_exists(self):
        self.assertTrue(SKILL_PATH.is_file(), f"AC5 expects {SKILL_PATH} to exist")

    def test_AC5_skill_names_save_initiative(self):
        body = _read(SKILL_PATH)
        self.assertIn(
            "save_initiative",
            body,
            "AC5: SKILL.md's Engagement = Initiative bullet must name save_initiative as "
            "the exposed write tool.",
        )

    def test_AC5_skill_no_longer_claims_not_wired(self):
        body = _read(SKILL_PATH).lower()
        for stale in STALE_PHRASES:
            self.assertNotIn(
                stale,
                body,
                f"AC5 (anti-regression): SKILL.md still carries the stale framing "
                f"{stale!r} — Engagement = Initiative is no longer 'not yet wired' for the "
                "Initiative record write.",
            )

    def test_AC5_skill_scopes_remaining_work_to_wiring_not_the_write(self):
        """AC5/AC7: what remains is the *auto-attach wiring*, not the write tool itself —
        the bullet must reframe the open work as a separate wiring task, so the corrected
        claim isn't ambiguous about what is and isn't done."""
        body = _read(SKILL_PATH).lower()
        self.assertIn(
            "wiring",
            body,
            "AC5: SKILL.md must reframe the remaining work as a separate *wiring* task "
            "(init create + status-update roll-ups), distinct from the now-available "
            "save_initiative write.",
        )


class AC5_ModelRowReframedHandCurated(unittest.TestCase):
    """AC5 (third stale-framing site): the Initiative row in linear-model.md no longer
    reads '(manual)' as if the record were unreachable — it is reframed to '(hand-curated)'
    membership with the record noted MCP-writable via save_initiative."""

    def test_AC5_model_initiative_row_is_mcp_writable(self):
        body = _read(LINEAR_MODEL_PATH)
        self.assertIn(
            "save_initiative",
            body,
            "AC5: linear-model.md's Initiative row must note the record is MCP-writable "
            "via save_initiative.",
        )

    def test_AC5_model_initiative_row_not_labelled_plain_manual(self):
        """Anti-regression: the row's grouping qualifier was '(manual)' in the base, which
        read as 'no write path'. It must now be '(hand-curated)'."""
        body = _read(LINEAR_MODEL_PATH)
        self.assertNotIn(
            "grouping (manual)",
            body,
            "AC5 (anti-regression): the Initiative row must not be labelled "
            "`grouping (manual)` (reads as unreachable) — reframed to `(hand-curated)`.",
        )
        self.assertIn(
            "grouping (hand-curated)",
            body,
            "AC5: the Initiative row qualifier must be `grouping (hand-curated)`.",
        )


class AC6_SnapshotReVerificationDate(unittest.TestCase):
    """AC6: the snapshot in linear-mcp.md is bumped to the re-verification date with the
    method noted — added ALONGSIDE the pinned 2026-05-28 baseline line, not replacing it
    (replacing it would break test_documents_and_updates_ref's pinned assertion)."""

    def test_AC6_reverification_date_present(self):
        body = _read(LINEAR_MCP_PATH)
        self.assertIn(
            "Re-verified 2026-06-05",
            body,
            "AC6: linear-mcp.md must carry the 2026-06-05 re-verification line.",
        )

    def test_AC6_reverification_notes_the_method(self):
        """AC6: 'with method noted' — the re-verification must say HOW it was checked
        (live against the connected MCP) and cite the standard that requires live evidence
        (ADR-008), not just stamp a date."""
        body = _read(LINEAR_MCP_PATH)
        self.assertIn(
            "ADR-008",
            body,
            "AC6: the re-verification note must cite ADR-008 (live-surface verification) "
            "as the method/standard.",
        )
        self.assertIn(
            "live",
            body.lower(),
            "AC6: the re-verification note must state the method was a *live* check of the "
            "connected MCP surface.",
        )

    def test_AC6_baseline_snapshot_line_preserved(self):
        """AC6/AC7 (regression guard): the developer ADDED the re-verification line rather
        than replacing the baseline token, to keep test_documents_and_updates_ref's pinned
        `Surface snapshot: 2026-05-28` assertion green. Pin that the baseline line is still
        present here too, so a future 'tidy-up' that deletes it is caught by THIS file as
        well — not only by the sibling pinned test."""
        body = _read(LINEAR_MCP_PATH)
        self.assertIn(
            "Surface snapshot: 2026-05-28",
            body,
            "AC6/AC7: the baseline `Surface snapshot: 2026-05-28` line must be preserved "
            "(the re-verification line is additive); deleting it breaks the pinned "
            "test_documents_and_updates_ref assertion.",
        )


# --- ACs NOT mechanically pinned here (named, not faked) -----------------------
#
# AC7 [review] — "Docs only, no behavioural/code change." Not provable by a content
#   assertion without becoming a tautology; it is a scope/diff judgement the reviewer
#   makes against the PR (the diff touches only .md docs + this/sibling test files). The
#   *substance* that backs it — the corrected claim names a wiring task as the remaining
#   work, not a code change — is pinned by
#   AC5_SkillNoLongerFlagsInitiativeNotWired::test_AC5_skill_scopes_remaining_work_to_wiring_not_the_write.
#   The load-bearing regression risk of AC7 (a docs edit must not red the existing pinned
#   suite) IS covered: the full `python -m unittest discover -s scripts` run stays green,
#   and AC6_SnapshotReVerificationDate::test_AC6_baseline_snapshot_line_preserved guards
#   the one pinned line the change sits next to.


if __name__ == "__main__":
    unittest.main(verbosity=2)
