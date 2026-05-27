"""backlogd graph — append-only code<->Linear memory for the agent team.

Records the dimension Linear can't see: which *sessions* solved which *problems*,
and which *files (modules)* they touched along the way. Linear (via the official
MCP) already owns work-item hierarchy, relations, comments and PR links — this
graph deliberately does not duplicate any of that. Its only job is the local
code/session memory that lets the scrum-master and developers recall how related
problems and areas were solved before.

Storage
-------
Append-only JSON, one file per session, under ``.backlogd/graph/`` relative to the
current working directory (the repository backlogd is operating on). Override the
location with the ``BACKLOGD_GRAPH_DIR`` environment variable (used by tests).

Each file is a JSON array of edge objects::

    {"v": "backlogd/v1", "src": "...", "tgt": "...", "type": "...",
     "ts": "<ISO 8601 UTC>", "session": "<session id>"}

Schema (pruned)
---------------
Node ids follow ``kind:backend:native_id`` (the backend segment is omitted where
it does not apply):

* session — ``session:<session id>``          e.g. a git branch name
* problem — ``problem:linear:<identifier>``   e.g. ``problem:linear:NB-264``
* module  — ``module:<file path>``            a file touched while solving

Edge types:

* ``solves``  — session -> problem
* ``touches`` — session -> module

Dedup key: ``(src, tgt, type, session)``.

Design notes
------------
* Pure Python standard library — zero third-party dependencies.
* Windows-safe — ``pathlib`` throughout; session ids are sanitised for filenames.
* Best-effort — write failures are logged to stderr and swallowed; graph
  persistence must never block the scrum loop.
* Nodes are implicit: a node exists once an edge references its id. Richer entity
  records (titles, relations, PR links) are intentionally deferred to later work.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

__all__ = [
    "SCHEMA_VERSION",
    "graph_dir",
    "node_id",
    "session_node",
    "problem_node",
    "module_node",
    "make_edge",
    "solves_edge",
    "touches_edge",
    "write_edges",
    "read_graph",
]

SCHEMA_VERSION = "backlogd/v1"
_DEFAULT_DIR = Path(".backlogd") / "graph"


# --- location -------------------------------------------------------------

def graph_dir() -> Path:
    """Return the graph store directory.

    Defaults to ``.backlogd/graph`` relative to the current working directory;
    overridable via the ``BACKLOGD_GRAPH_DIR`` environment variable. Read at call
    time so tests can redirect the store without reimporting the module.
    """
    override = os.environ.get("BACKLOGD_GRAPH_DIR")
    return Path(override) if override else _DEFAULT_DIR


# --- node ids -------------------------------------------------------------

def node_id(kind: str, backend: str, native_id: str) -> str:
    """Build a ``kind:backend:native_id`` node id (e.g. ``problem:linear:NB-264``)."""
    return f"{kind}:{backend}:{native_id}"


def session_node(session_id: str) -> str:
    """Node id for a session (a branch name or other session identifier)."""
    return f"session:{session_id}"


def problem_node(identifier: str) -> str:
    """Node id for a Linear problem, e.g. ``problem:linear:NB-264``."""
    return node_id("problem", "linear", identifier)


def module_node(file_path: str) -> str:
    """Node id for a module (a file path), e.g. ``module:scripts/graph.py``.

    Backslashes are normalised to forward slashes so the same file yields one id
    regardless of the platform that recorded it.
    """
    return "module:" + str(file_path).replace("\\", "/")


# --- edges ----------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_edge(src, tgt, edge_type, session, ts=None) -> dict:
    """Construct a well-formed ``backlogd/v1`` edge dict."""
    return {
        "v": SCHEMA_VERSION,
        "src": src,
        "tgt": tgt,
        "type": edge_type,
        "ts": ts or _now_iso(),
        "session": session,
    }


def solves_edge(session_id, problem_identifier, ts=None) -> dict:
    """Build a ``solves`` edge: session -> problem."""
    return make_edge(
        session_node(session_id), problem_node(problem_identifier),
        "solves", session_id, ts,
    )


def touches_edge(session_id, file_path, ts=None) -> dict:
    """Build a ``touches`` edge: session -> module."""
    return make_edge(
        session_node(session_id), module_node(file_path),
        "touches", session_id, ts,
    )


# --- persistence ----------------------------------------------------------

def _sanitize_session(session_id: str) -> str:
    """Make a session id safe as a filename (``a/b\\c`` -> ``a__b__c``)."""
    return session_id.replace("/", "__").replace("\\", "__")


def _session_file(session_id: str) -> Path:
    return graph_dir() / f"{_sanitize_session(session_id)}.json"


def _dedup_key(edge: dict) -> tuple:
    return (edge.get("src"), edge.get("tgt"), edge.get("type"), edge.get("session"))


def _load(path: Path) -> list:
    """Read one session file into a list of edges; tolerate missing/garbage."""
    if not path.exists():
        return []
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"[backlogd-graph] WARNING: cannot read {path}: {exc}", file=sys.stderr)
        return []
    if not raw.strip():
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"[backlogd-graph] WARNING: invalid JSON in {path}: {exc}", file=sys.stderr)
        return []
    return data if isinstance(data, list) else []


def write_edges(session_id: str, edges: list) -> None:
    """Append ``edges`` to the session file, deduped on ``(src,tgt,type,session)``.

    Reads any existing edges, merges the new ones (the new edge wins on a
    duplicate key), and writes the full array back. Creates the store directory
    if needed. Best-effort: any failure is logged to stderr and swallowed — it is
    never raised, so graph persistence cannot block the caller.
    """
    try:
        directory = graph_dir()
        directory.mkdir(parents=True, exist_ok=True)
        path = _session_file(session_id)

        merged: dict = {}
        for edge in _load(path):
            if isinstance(edge, dict):
                merged[_dedup_key(edge)] = edge
        for edge in edges:
            if not isinstance(edge, dict):
                print(
                    f"[backlogd-graph] WARNING: skipping non-dict edge: {type(edge).__name__}",
                    file=sys.stderr,
                )
                continue
            e = dict(edge)
            e.setdefault("v", SCHEMA_VERSION)
            e.setdefault("ts", _now_iso())
            e.setdefault("session", session_id)
            merged[_dedup_key(e)] = e

        path.write_text(json.dumps(list(merged.values()), indent=2), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001 — best-effort persistence
        print(
            f"[backlogd-graph] ERROR: write_edges failed for '{session_id}': {exc}",
            file=sys.stderr,
        )


def read_graph() -> list:
    """Return every stored edge across all session files, deduplicated.

    A missing or empty store returns ``[]`` (never raises). Files that fail to
    parse are skipped with a stderr warning.
    """
    directory = graph_dir()
    if not directory.exists():
        return []
    merged: dict = {}
    for path in sorted(directory.glob("*.json")):
        for edge in _load(path):
            if isinstance(edge, dict):
                merged.setdefault(_dedup_key(edge), edge)
    return list(merged.values())
