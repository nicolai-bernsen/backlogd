"""Membership test for ADR-007 — persisted on-disk run/state data (NB-427).

Why this file exists — the gap it closes
-----------------------------------------
``test_standards_index.py`` proves the index is **consistent** with the corpus
(``IndexDriftTest`` rebuilds the index and compares byte-for-byte) and that every ADR
carries the required front-matter keys. ``test_adr_003_workspace_config.py`` proves the
ADR-NNN numbers are **contiguous**. None of those pin **membership**: delete BOTH the
ADR-007 file *and* its ``index.json`` entry and every existing test still passes — the
drift guard sees a (smaller) corpus that still matches a (smaller) index, and the
contiguity check sees ``[1..6]`` which is still gap-free. So nothing asserts that an
Accepted ADR-007 carrying the PO's ruled standard is actually *present*.

This test pins exactly that, and only that — a fact about the committed artifact a
reviewer reads (``docs/standards/index.json``):

* ADR-007 is in the index,
* it is ``status: Accepted`` (a Proposed/Rejected entry would not govern), and
* its ``assertion`` carries the load-bearing tokens of the ruled standard — gitignored
  ``.backlogd/`` home, append-only newline-delimited JSON, a per-record schema
  ``version`` field, reader-tolerance of unknown fields, grow-only schema evolution, and
  the never-commit rule.

It deliberately asserts the *substance* (the standard's load-bearing tokens), not the
exact wording — it is not a byte-for-byte echo of the assertion (that would be a
tautology against the same artifact the drift test already guards). Whether the ADR's
prose, options, and grandfathering rationale are *sound* stays the reviewer's call
([review]); this only proves the rule is on the books.

CI runs ``python3 -m unittest discover -s scripts -p 'test_*.py'`` from the repo root
(see .github/workflows/ci.yml), so this lives in scripts/ as a stdlib unittest.

Run from the repo root:
    python -m pytest scripts/test_adr_007_persisted_data.py
    python scripts/test_adr_007_persisted_data.py
    python -m pytest scripts -k ADR007        # natural -k selection
"""

import json
import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
INDEX_PATH = REPO_ROOT / "docs" / "standards" / "index.json"


class ADR007MembershipInIndex(unittest.TestCase):
    """The standards index must *contain* an Accepted ADR-007 whose assertion captures
    the persisted-data standard. (Consistency + contiguity are proven elsewhere; this is
    the missing membership anchor — deleting ADR-007 + its index entry must fail HERE.)"""

    @classmethod
    def setUpClass(cls):
        cls.index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        cls.by_id = {e["id"]: e for e in cls.index["standards"]}

    def test_adr007_is_present_in_index(self):
        self.assertIn(
            "ADR-007", self.by_id,
            "the standards index must contain ADR-007 (persisted on-disk run/state "
            "data) — regenerate with `python scripts/standards_index.py` after adding "
            "the ADR.",
        )

    def test_adr007_is_accepted(self):
        self.assertEqual(
            self.by_id["ADR-007"]["status"], "Accepted",
            "ADR-007 must be `status: Accepted` to govern persisted-store decisions "
            "(a non-Accepted entry does not bind the next store).",
        )

    def test_adr007_assertion_captures_the_ruled_standard(self):
        """The assertion must carry every load-bearing token of the PO's ruled standard.
        Substance, not exact wording — each clause is matched by the token(s) that make
        it checkable, so a regeneration that dropped a clause from the assertion is
        caught here without re-echoing the assertion verbatim."""
        assertion = self.by_id["ADR-007"]["assertion"].lower()

        # Each tuple is one clause of the ruled standard; a clause passes if ANY of its
        # tokens is present (tolerates minor rewording, fails on a dropped clause).
        clauses = {
            "gitignored .backlogd/ home": (".backlogd",),
            "append-only": ("append-only", "append only"),
            "newline-delimited JSON / NDJSON / one-record-per-line": (
                "newline-delimited", "ndjson", "one record per line",
            ),
            "per-record schema version field": ("version",),
            "readers tolerate unknown fields": (
                "unknown field", "tolerate unknown", "unknown-field",
            ),
            "grow-only schema evolution": (
                "only ever grows", "grow-only", "grow only", "only grows",
            ),
            "never commit .backlogd/ content": ("never commit", "never committed"),
        }
        missing = [
            label for label, tokens in clauses.items()
            if not any(tok in assertion for tok in tokens)
        ]
        self.assertEqual(
            missing, [],
            "ADR-007's indexed assertion is missing load-bearing clause(s) of the "
            f"ruled persisted-data standard: {missing}\n"
            f"assertion was: {self.by_id['ADR-007']['assertion']!r}",
        )

    def test_adr007_scope_catches_persisted_store_decisions(self):
        """The whole point of the ADR is that the reviewer's index-first walk catches
        the *next* persisted-store decision. Pin that the scope actually targets the
        persisted-data domain + a data-format/schema-evolution decision type, so a
        regeneration that emptied or narrowed the scope (making the rule un-findable)
        fails here. (Whether the chosen axes are the *best* set is [review].)"""
        scope = self.by_id["ADR-007"]["applies-to"]
        domains = {d.lower() for d in scope.get("domains", [])}
        dtypes = {d.lower() for d in scope.get("decision-types", [])}
        self.assertTrue(
            domains & {"persistence", "storage", "runtime"},
            f"ADR-007 applies-to.domains must target the persisted-data domain; got {sorted(domains)}",
        )
        self.assertTrue(
            dtypes & {"data-format", "schema-evolution", "persistence", "storage-location"},
            "ADR-007 applies-to.decision-types must catch a persisted-store format/"
            f"schema decision; got {sorted(dtypes)}",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
