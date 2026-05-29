#!/usr/bin/env python3
"""Witness checker — assert every shipped fix's code marker is still in the tree.

backlogd accepts a problem when its fix lands. Some fixes carry a dedicated test
(NB-369's suite guards those); others are prose, skill content, a command-file
convention, or a config line — there is no behaviour to assert, only a string
that must stay present. This script is the cheapest possible proof for that
second class: for each accepted problem recorded in ``solved-problems.json`` it
reads the named ``marker_file`` and asserts the ``marker_snippet`` is still a
literal substring of it. A miss means a shipped fix silently regressed.

It is deliberately tiny: stdlib ``json`` only, literal ``in`` substring match (no
regex, no signing). Complementary to the test suite — not a replacement for it.

Path resolution: the manifest and every ``marker_file`` are resolved relative to
the repo root (this file's parent's parent), never an absolute path, so the same
script runs on a Linux CI runner and on a maintainer's box. ``marker_file``
entries are repo-root-relative POSIX paths (e.g. ``commands/solve.md``).

Output: one line per entry — ``OK <id> <marker_file>`` or ``MISS <id> ...`` with
a reason. Exit status:
  * 0  — manifest is a non-empty JSON array and every marker is present;
  * non-zero — any miss, any missing/unreadable ``marker_file``, or any
    malformed entry (not an object, or a required field missing/empty), or a
    manifest that is missing, unparseable, or not a non-empty array.

Run from the repo root:  python3 scripts/witness.py
"""

import json
import pathlib
import sys

# Repo root is this file's grandparent: <root>/scripts/witness.py.
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "solved-problems.json"

# Every entry must carry these fields, each a non-empty string.
REQUIRED_FIELDS = (
    "id",
    "title",
    "marker_file",
    "marker_snippet",
    "shipped_in",
    "shipped_at",
)


def load_manifest(path):
    """Load the manifest and return its list of entries.

    Raises ``ValueError`` if the file is missing, unparseable, or not a
    non-empty JSON array — the caller turns that into a non-zero exit.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read manifest {path}: {exc}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"manifest {path} is not valid JSON: {exc}") from exc
    if not isinstance(data, list):
        raise ValueError(f"manifest {path} must be a JSON array")
    if not data:
        raise ValueError(f"manifest {path} must list at least one entry")
    return data


def check_entry(entry, repo_root):
    """Check a single manifest entry.

    Returns ``(ok: bool, line: str)``. ``ok`` is False for a malformed entry, a
    missing/unreadable marker file, or a marker snippet that is not a literal
    substring of the file.
    """
    # Entry must be an object with every required field present and non-empty.
    if not isinstance(entry, dict):
        return False, f"MISS <malformed> entry is not an object: {entry!r}"
    missing = [
        f
        for f in REQUIRED_FIELDS
        if not isinstance(entry.get(f), str) or not entry.get(f).strip()
    ]
    if missing:
        ident = entry.get("id") if isinstance(entry.get("id"), str) else "<no-id>"
        return False, f"MISS {ident} malformed entry — missing/empty field(s): {', '.join(missing)}"

    ident = entry["id"]
    marker_file = entry["marker_file"]
    snippet = entry["marker_snippet"]

    target = repo_root / marker_file
    try:
        contents = target.read_text(encoding="utf-8")
    except OSError as exc:
        return False, f"MISS {ident} {marker_file} — cannot read marker file: {exc}"

    if snippet in contents:
        return True, f"OK {ident} {marker_file}"
    return False, f"MISS {ident} {marker_file} — marker snippet not found"


def run(manifest_path=MANIFEST, repo_root=REPO_ROOT, out=None):
    """Check every entry; print one line each; return a process exit code.

    Kept parameterised (``manifest_path`` / ``repo_root`` / ``out``) so the test
    suite can drive it against tmp fixtures without touching the real manifest or
    repo files.
    """
    if out is None:
        out = sys.stdout
    try:
        entries = load_manifest(manifest_path)
    except ValueError as exc:
        print(f"FAIL {exc}", file=out)
        return 1

    failures = 0
    for entry in entries:
        ok, line = check_entry(entry, repo_root)
        print(line, file=out)
        if not ok:
            failures += 1

    if failures:
        print(f"FAIL {failures} marker(s) missing or malformed", file=out)
        return 1
    print(f"OK all {len(entries)} marker(s) present", file=out)
    return 0


if __name__ == "__main__":
    sys.exit(run())
