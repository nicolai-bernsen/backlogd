"""Content tests for skills/linear/references/documents-and-updates.md and
skills/linear/references/linear-mcp.md — NB-363 (Unit 0: write-helpers reference).

Docs-only unit: each AC bullet is proven by an explicit file-existence + content
assertion on the markdown sources. One test per AC string-shape claim so the
proof maps 1:1 to the unit's acceptance criteria.

Run from the repo root:  python scripts/test_documents_and_updates_ref.py
"""

import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS_PATH = REPO_ROOT / "skills" / "linear" / "references" / "documents-and-updates.md"
LINEAR_MCP_PATH = REPO_ROOT / "skills" / "linear" / "references" / "linear-mcp.md"


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


class AC1_DocumentsAndUpdatesReference(unittest.TestCase):
    """AC1: documents-and-updates.md documents the verified save_document signature,
    the no-native-update finding + project-comment mechanism, and idempotent upsert
    for both (markers/titles)."""

    def test_AC1_file_exists(self):
        self.assertTrue(
            DOCS_PATH.is_file(),
            f"AC1 expects {DOCS_PATH} to exist",
        )

    def test_AC1_documents_save_document_create_signature(self):
        body = _read(DOCS_PATH)
        # The verified create-call shape: save_document({ project: ..., title, content, icon })
        self.assertIn(
            "save_document({ project",
            body,
            "AC1: must document the save_document create signature with `project` parent",
        )

    def test_AC1_documents_save_document_update_signature(self):
        body = _read(DOCS_PATH)
        # Update is by id: save_document({ id, content })
        self.assertIn(
            "save_document({ id",
            body,
            "AC1: must document the save_document update signature (id + content)",
        )

    def test_AC1_documents_list_documents_with_projectId(self):
        body = _read(DOCS_PATH)
        # The list/find call uses projectId (the asymmetry to project on writes)
        self.assertIn(
            "list_documents({ projectId",
            body,
            "AC1: must document list_documents({ projectId }) as the find call",
        )

    def test_AC1_records_no_native_project_update_finding(self):
        body = _read(DOCS_PATH).lower()
        self.assertIn(
            "no native",
            body,
            "AC1: must record the 'no native Project-Update write' finding",
        )

    def test_AC1_documents_project_comment_mechanism(self):
        body = _read(DOCS_PATH)
        # The fallback path: save_comment({ projectId, body }) on the project thread
        self.assertIn(
            "save_comment({ projectId",
            body,
            "AC1: must name the project-thread save_comment({ projectId, body }) mechanism",
        )

    def test_AC1_documents_health_lead_line(self):
        body = _read(DOCS_PATH)
        self.assertIn(
            "**[backlogd]** Health:",
            body,
            "AC1: must specify the **[backlogd]** Health: lead line shape",
        )

    def test_AC1_idempotent_upsert_for_documents_keyed_by_title(self):
        body = _read(DOCS_PATH)
        self.assertIn(
            "idempotent upsert",
            body.lower(),
            "AC1: must use the phrase 'idempotent upsert' for the helper contract",
        )
        # Title-keyed dedupe for Documents (Spec / Solution brief)
        self.assertIn(
            "Spec",
            body,
            "AC1: must define a canonical Spec document title",
        )
        self.assertIn(
            "Solution brief",
            body,
            "AC1: must define a canonical Solution brief document title",
        )

    def test_AC1_idempotent_upsert_for_health_keyed_by_marker(self):
        body = _read(DOCS_PATH)
        # Trailing HTML-comment markers for dedupe across health comments
        self.assertIn(
            "<!-- marker:",
            body,
            "AC1: must document the `<!-- marker: ... -->` trailing transition marker",
        )
        for token in ("claim", "blocked", "handback", "milestone"):
            self.assertIn(
                token,
                body,
                f"AC1: health marker vocabulary must include `{token}`",
            )

    def test_AC1_release_shipped_summary_marker(self):
        body = _read(DOCS_PATH)
        # Release "Shipped in vX.Y.Z" stable marker for the upsert
        self.assertIn(
            "Shipped in vX.Y.Z",
            body,
            "AC1: must document the 'Shipped in vX.Y.Z' release-summary marker",
        )


class AC2_LinearMcpCrossLinkAndSnapshot(unittest.TestCase):
    """AC2: linear-mcp.md cross-links documents-and-updates.md, records the
    project/projectId asymmetry, and bumps the surface-snapshot date to 2026-05-28."""

    def test_AC2_file_exists(self):
        self.assertTrue(
            LINEAR_MCP_PATH.is_file(),
            f"AC2 expects {LINEAR_MCP_PATH} to exist",
        )

    def test_AC2_cross_links_documents_and_updates(self):
        body = _read(LINEAR_MCP_PATH)
        self.assertIn(
            "documents-and-updates.md",
            body,
            "AC2: linear-mcp.md must cross-link documents-and-updates.md",
        )

    def test_AC2_records_project_projectId_asymmetry(self):
        body = _read(LINEAR_MCP_PATH)
        # The exact framing of the footgun: write parent vs list filter
        self.assertIn(
            "write parent is `project`, list filter is `projectId`",
            body,
            "AC2: must record the `project` (write) / `projectId` (list) asymmetry",
        )

    def test_AC2_records_no_native_project_update_finding(self):
        body = _read(LINEAR_MCP_PATH).lower()
        self.assertIn(
            "no native project-update write",
            body,
            "AC2: must record the verified 'no native Project-Update write' finding",
        )

    def test_AC2_snapshot_date_bumped_to_2026_05_28(self):
        body = _read(LINEAR_MCP_PATH)
        # The surface-snapshot date line at the top of the file
        self.assertIn(
            "Surface snapshot: 2026-05-28",
            body,
            "AC2: must bump the surface-snapshot date to 2026-05-28",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
