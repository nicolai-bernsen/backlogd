"""backlogd graph — append-only agent-execution memory for the scrum loop.

Records the dimension Linear and git can't compute on their own: the *behaviour*
of the agent loop itself — when a developer was dispatched, what it returned
(``solved`` / ``partial`` / ``blocked``), how long that took, when the PR opened,
how long the whole run wall-clocked, and how often a problem came back from
review with rework notes. Linear (via the official MCP) owns work-item state and
PR linkage; ``git log`` owns file authorship — this graph deliberately does not
duplicate either. Its only job is the local agent-execution memory that lets
``/backlogd:metrics`` answer *"did the framework actually help?"*.

Storage
-------
Append-only JSON, one file per session, under ``.backlogd/graph/`` relative to the
current working directory (the repository backlogd is operating on). Override the
location with the ``BACKLOGD_GRAPH_DIR`` environment variable (used by tests).

Each file is a JSON array of edge objects::

    {"v": "backlogd/v1", "src": "...", "tgt": "...", "type": "...",
     "ts": "<ISO 8601 UTC>", "session": "<session id>", ...extras}

Some edge types carry extra fields beyond the base — ``outcome``, ``latency_ms``,
``wall_time_ms``, ``fanout``, ``notes_hash``, ``labels``. They are passed through as-is.

Schema (pruned)
---------------
Node ids follow ``kind:backend:native_id`` (the backend segment is omitted where
it does not apply):

* session — ``session:<session id>``          e.g. a git branch name
* problem — ``problem:linear:<identifier>``   e.g. ``problem:linear:NB-264``
* module  — ``module:<file path>``            a file touched while solving
  (legacy / low-signal — see "File edges" below)

Edge types:

**Agent-execution edges (primary signal — what only the loop knows):**

* ``dispatch_started``  — session -> problem (the *unit* being dispatched)
* ``dispatch_completed`` — session -> problem; carries ``outcome`` +
  ``latency_ms`` (developer wall time)
* ``pr_opened``         — session -> problem (handoff PR opened)
* ``run_completed``     — session -> problem; carries ``wall_time_ms`` (whole run)
  and ``fanout`` (peak parallel-group size: 1 for sequential, ≥2 when the
  parallel walk fanned out — added in #321)
* ``rework``            — session -> problem; recorded by ``/backlogd:review``
  when sending back to *In Progress*; carries an optional ``notes_hash``
* ``labeled``           — session -> problem; carries ``labels`` (list of label
  names from Linear at dispatch time, used for blocker-by-area aggregates).
  Optional — when absent, the area aggregate just notes "no label data".

**Legacy edges (kept for backward read, no longer emitted on new runs):**

* ``solves``  — session -> problem  (now superseded by ``dispatch_completed``;
  ``solves`` is still recognised by ``prior_work`` so historical graphs keep
  working).
* ``touches`` — session -> module   (file-edge dimension; ``git log`` derives
  this signal anyway. Kept readable for old data; not emitted by the new flow.
  See "File edges" below.)

Dedup key: ``(src, tgt, type, session)``. Re-emitting the same logical edge
overwrites the older one — convenient for runs that retry a unit.

File edges
----------
File-touch edges (``touches``) duplicate information ``git log`` already gives
us. They remain a valid, *low-signal* aside — ``prior_work`` still uses them
when present to surface "this problem previously touched X.py" hints — but the
new scrum-loop flow does **not** emit them. The ``emit`` CLI is retained for
back-compat (and so callers can still write touches if they want), but the
recommended path for the orchestrator is the dedicated agent-execution
subcommands below.

Design notes
------------
* Pure Python standard library — zero third-party dependencies.
* Windows-safe — ``pathlib`` throughout; session ids are sanitised for filenames.
* Best-effort — write failures are logged to stderr and swallowed; graph
  persistence must never block the scrum loop.
* Nodes are implicit: a node exists once an edge references its id.
* All new edge writers carry through optional ``extras`` so the schema stays
  additive — old readers ignore unknown fields, new readers degrade gracefully
  when they're missing.
"""

import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict
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
    "dispatch_started_edge",
    "dispatch_completed_edge",
    "pr_opened_edge",
    "run_completed_edge",
    "rework_edge",
    "labeled_edge",
    "write_edges",
    "read_graph",
    "prior_work",
    "run_status",
    "metrics",
    "emit",
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


def _parse_iso(ts: str):
    """Parse an ISO-8601 UTC timestamp into a ``datetime``; return ``None`` on bad input."""
    if not ts:
        return None
    try:
        # Tolerate both trailing-Z and +00:00 forms.
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return None


def _ms_between(start_ts: str, end_ts: str):
    """Return ``end - start`` in integer milliseconds, or ``None`` if either is missing/bad."""
    a = _parse_iso(start_ts)
    b = _parse_iso(end_ts)
    if a is None or b is None:
        return None
    return int((b - a).total_seconds() * 1000)


def make_edge(src, tgt, edge_type, session, ts=None, **extras) -> dict:
    """Construct a well-formed ``backlogd/v1`` edge dict.

    Extra keyword arguments are merged into the edge — used by the new
    agent-execution edge types to attach ``outcome`` / ``latency_ms`` etc. The
    base fields (``v`` / ``src`` / ``tgt`` / ``type`` / ``ts`` / ``session``)
    take precedence and cannot be overridden via ``extras``.
    """
    edge = {
        "v": SCHEMA_VERSION,
        "src": src,
        "tgt": tgt,
        "type": edge_type,
        "ts": ts or _now_iso(),
        "session": session,
    }
    for k, v in extras.items():
        if v is None or k in edge:
            continue
        edge[k] = v
    return edge


def solves_edge(session_id, problem_identifier, ts=None) -> dict:
    """Build a legacy ``solves`` edge: session -> problem.

    Kept for backward compatibility — historical graphs and the ``emit`` CLI
    still produce these. The new flow uses ``dispatch_completed`` instead.
    """
    return make_edge(
        session_node(session_id), problem_node(problem_identifier),
        "solves", session_id, ts,
    )


def touches_edge(session_id, file_path, ts=None) -> dict:
    """Build a ``touches`` edge: session -> module (legacy / low-signal).

    File-touch edges duplicate ``git log`` and are no longer emitted by the new
    scrum-loop flow. ``emit`` still produces them for back-compat; ``prior_work``
    still reads them when present.
    """
    return make_edge(
        session_node(session_id), module_node(file_path),
        "touches", session_id, ts,
    )


def dispatch_started_edge(session_id, problem_identifier, ts=None) -> dict:
    """Build a ``dispatch_started`` edge: session -> unit problem.

    Recorded when the orchestrator hands the unit to a developer subagent. The
    edge's ``ts`` is the dispatch clock that ``dispatch_completed`` later
    differences against to compute ``latency_ms``.
    """
    return make_edge(
        session_node(session_id), problem_node(problem_identifier),
        "dispatch_started", session_id, ts,
    )


def dispatch_completed_edge(session_id, problem_identifier, outcome,
                            ts=None, latency_ms=None) -> dict:
    """Build a ``dispatch_completed`` edge with ``outcome`` and optional ``latency_ms``.

    ``outcome`` is the developer's reported result: ``"solved"`` / ``"partial"``
    / ``"blocked"``. ``latency_ms`` is the wall time from the corresponding
    ``dispatch_started`` (the CLI ``dispatch-end`` subcommand derives this
    automatically when it can find the matching start edge).
    """
    return make_edge(
        session_node(session_id), problem_node(problem_identifier),
        "dispatch_completed", session_id, ts,
        outcome=outcome, latency_ms=latency_ms,
    )


def pr_opened_edge(session_id, problem_identifier, ts=None) -> dict:
    """Build a ``pr_opened`` edge: session -> problem, marking PR open time."""
    return make_edge(
        session_node(session_id), problem_node(problem_identifier),
        "pr_opened", session_id, ts,
    )


def run_completed_edge(session_id, problem_identifier,
                       ts=None, wall_time_ms=None, fanout=None) -> dict:
    """Build a ``run_completed`` edge with optional ``wall_time_ms`` for the whole run.

    ``fanout`` (added with the parallel-dispatch work in #321) records the **peak
    parallel-group size** observed during the run: ``1`` for a sequential / single-unit
    run, ``≥2`` when at least one parallel group ran. The field is additive — old
    readers ignore it, ``metrics`` reads it back when present so the report can break
    out parallel-vs-sequential effects on ``run_wall_time``.
    """
    return make_edge(
        session_node(session_id), problem_node(problem_identifier),
        "run_completed", session_id, ts,
        wall_time_ms=wall_time_ms, fanout=fanout,
    )


def rework_edge(session_id, problem_identifier, ts=None, notes_hash=None) -> dict:
    """Build a ``rework`` edge: session -> problem, recorded by ``/backlogd:review``.

    Each rework event is a *separate* edge — the dedup key includes ``ts`` only
    indirectly (the session+problem+type collapses), so to keep multiple rework
    events for the same problem distinct we vary ``session`` with a suffix or
    rely on the caller to record them per-review. The CLI ``rework`` subcommand
    appends a per-event suffix to the session id so events accumulate.
    """
    return make_edge(
        session_node(session_id), problem_node(problem_identifier),
        "rework", session_id, ts, notes_hash=notes_hash,
    )


def labeled_edge(session_id, problem_identifier, labels, ts=None) -> dict:
    """Build a ``labeled`` edge attaching Linear ``labels`` to a session→problem.

    Labels are stored as a list of strings (e.g. ``["area:graph", "problem"]``)
    so the ``report`` subcommand can break blocker frequency down by area
    without re-reading Linear at report time.
    """
    return make_edge(
        session_node(session_id), problem_node(problem_identifier),
        "labeled", session_id, ts,
        labels=list(labels or []),
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


# --- prior-work query (read-only) -----------------------------------------

def _strip_module(node: str) -> str:
    """``module:scripts/x.py`` -> ``scripts/x.py`` (id -> display)."""
    return node[len("module:"):] if node.startswith("module:") else node


def _strip_problem(node: str) -> str:
    """``problem:linear:NB-9`` -> ``NB-9`` (id -> display)."""
    prefix = "problem:linear:"
    return node[len(prefix):] if node.startswith(prefix) else node


def prior_work(problem_identifier: str, edges=None, max_related: int = 5) -> list:
    """Return report lines describing prior work related to a problem.

    Combines two read-only lookups over the graph:

    * **problem-history** — files that sessions solving this problem touched before.
    * **find-similar** — other problems whose touch-set overlaps this one's, ranked by
      Jaccard similarity then shared-file count.

    Both lookups treat ``solves`` and ``dispatch_completed`` (with any outcome)
    as evidence that a session worked on a problem, so this still returns
    something useful as the graph transitions from legacy to new edges. Returns
    an empty list when the graph has nothing on this problem; the caller treats
    an empty list as "omit the Prior work section". Never raises.
    """
    edges = read_graph() if edges is None else edges
    target = problem_node(problem_identifier)

    solve_like = {"solves", "dispatch_completed"}

    # problem-history: files touched by sessions that solved the target problem
    solving = {e["src"] for e in edges
               if e.get("type") in solve_like and e.get("tgt") == target}
    own_files = sorted({_strip_module(e["tgt"]) for e in edges
                        if e.get("type") == "touches" and e.get("src") in solving})

    # find-similar: each problem's touch-set = union of files its sessions touched
    sess_modules = defaultdict(set)
    sess_problems = defaultdict(set)
    for e in edges:
        if e.get("type") == "touches":
            sess_modules[e["src"]].add(e["tgt"])
        elif e.get("type") in solve_like:
            sess_problems[e["src"]].add(e["tgt"])
    prob_modules = defaultdict(set)
    for sess, probs in sess_problems.items():
        for prob in probs:
            prob_modules[prob] |= sess_modules[sess]

    tset = prob_modules.get(target, set())
    ranked = []
    for prob, mods in prob_modules.items():
        if prob == target or not (tset & mods):
            continue
        shared = tset & mods
        jaccard = len(shared) / len(tset | mods)
        ranked.append((jaccard, len(shared), _strip_problem(prob),
                       sorted(_strip_module(m) for m in shared)))
    ranked.sort(reverse=True)

    if not own_files and not ranked:
        return []

    lines = []
    if own_files:
        lines.append(f"{problem_identifier} previously touched: " + ", ".join(own_files))
    for _jaccard, _shared_n, prob, shared in ranked[:max_related]:
        lines.append(f"related: {prob} (shared: {', '.join(shared)})")
    return lines


# --- run-status query (read-only, for /backlogd:solve --resume) -----------

def run_status(problem_identifier: str, edges=None) -> dict:
    """Reduce per-unit agent-execution edges for a problem to a resume-ready summary.

    Used by ``/backlogd:solve``'s reconcile step (see ``skills/solve/resume.md``)
    to decide, for every unit that touches this problem across **all** sessions,
    whether it's already ``completed``, currently ``in-progress`` (a session
    recorded ``dispatch_started`` but never a matching ``dispatch_completed``),
    or has no agent-execution history at all. The orchestrator cross-references
    this with Linear state and the worktree before re-dispatching.

    Returns a dict::

        {
          "problem": "NB-322",
          "units": {
            "NB-322": {
              "state": "completed" | "in-progress" | "untouched",
              "sessions": ["s1", "s2", ...],
              "last_started": "<ISO ts or None>",
              "last_completed": "<ISO ts or None>",
              "outcome": "solved" | "partial" | "blocked" | None,
            },
            ...
          },
        }

    Decision rules per unit (same target node, all sessions considered):

    - **completed** — any ``dispatch_completed`` edge exists for the unit. The
      most recent one wins; ``outcome`` is its ``outcome`` field. (Linear may
      still say ``Done`` even when the graph has only legacy ``solves`` data —
      that's why the orchestrator also reads Linear state.)
    - **in-progress** — there is at least one ``dispatch_started`` but no
      ``dispatch_completed`` for the unit. The session that recorded the start
      is in ``sessions``; if multiple sessions did, all are listed (the
      orchestrator surfaces that as an inconsistency to the product owner).
    - **untouched** — no ``dispatch_started`` and no ``dispatch_completed`` for
      the unit. (A unit with only legacy ``solves`` edges is also reported as
      ``untouched`` here so the new resume flow doesn't assume legacy semantics;
      the orchestrator falls back to Linear state for these.)

    Because the graph here is **scoped to one problem**, the top-level
    ``problem`` field is the input identifier and the inner ``units`` dict keys
    by the identifier we know — call sites that walk sub-issues call this once
    per sub-issue and merge. Sub-issue discovery itself stays in Linear; the
    graph is per-target.

    Pure read; never raises. An empty store yields a single ``untouched`` entry
    so the caller can write the resume report uniformly.
    """
    edges = read_graph() if edges is None else edges
    target = problem_node(problem_identifier)

    starts = []   # (ts, session)
    completes = []  # (ts, session, outcome)
    for e in edges:
        if not isinstance(e, dict) or e.get("tgt") != target:
            continue
        etype = e.get("type")
        if etype == "dispatch_started":
            starts.append((e.get("ts") or "", e.get("session")))
        elif etype == "dispatch_completed":
            completes.append(
                (e.get("ts") or "", e.get("session"), e.get("outcome"))
            )

    sessions = sorted({s for _ts, s in starts if s}
                      | {s for _ts, s, _o in completes if s})

    last_started_ts = max((ts for ts, _s in starts if ts), default=None)
    if completes:
        ts_sorted = sorted(completes)
        last_completed_ts, _sess, last_outcome = ts_sorted[-1]
    else:
        last_completed_ts, last_outcome = None, None

    if completes:
        state = "completed"
    elif starts:
        state = "in-progress"
    else:
        state = "untouched"

    return {
        "problem": problem_identifier,
        "units": {
            problem_identifier: {
                "state": state,
                "sessions": sessions,
                "last_started": last_started_ts,
                "last_completed": last_completed_ts,
                "outcome": last_outcome,
            }
        },
    }


# --- emit (legacy write) ---------------------------------------------------

def emit(session_id: str, problem_identifier: str, files) -> list:
    """Append one ``solves`` edge + one ``touches`` edge per file. Best-effort.

    **Legacy.** The new flow uses ``dispatch-start`` / ``dispatch-end`` /
    ``pr-opened`` / ``run-end`` instead — see the module docstring. ``emit`` is
    retained so old wirings and the file-edge "low-signal" path keep working.

    Delegates persistence to ``write_edges`` (which swallows and logs any
    failure), so this never raises. Returns the edges it built (handy for
    callers and tests).
    """
    edges = [solves_edge(session_id, problem_identifier)]
    edges += [touches_edge(session_id, f) for f in files if f and f.strip()]
    write_edges(session_id, edges)
    return edges


# --- metrics (read-only aggregation) --------------------------------------

def _percentile(values, p):
    """Return the ``p``-th percentile of ``values`` (linear interp); ``None`` if empty."""
    if not values:
        return None
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * (p / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    frac = k - lo
    return s[lo] + (s[hi] - s[lo]) * frac


def metrics(edges=None) -> dict:
    """Compute agent-execution metrics over the graph.

    Returns a dict::

        {
          "problems":  <int>,             # distinct problems with any run/dispatch edge
          "dispatches": {                 # per-unit outcomes
            "total":   <int>,
            "solved":  <int>,
            "partial": <int>,
            "blocked": <int>,
            "partial_rate": <float 0..1 or None>,
            "blocked_rate": <float 0..1 or None>,
          },
          "rework": {                     # problem-level rework events
            "events":  <int>,
            "problems_with_rework": <int>,
            "rate":    <float or None>,   # problems_with_rework / problems
          },
          "dispatch_to_pr_ms": {          # per-problem dispatch_started -> pr_opened
            "n":   <int>,
            "p50": <int or None>,
            "p90": <int or None>,
          },
          "run_wall_time_ms": {           # per-problem wall time from run_completed edges
            "n":   <int>,
            "p50": <int or None>,
            "p90": <int or None>,
          },
          "fanout": {                     # parallel-walk aggregate (#321)
            "n":   <int>,                 # runs with a recorded fanout field
            "max": <int or None>,         # largest peak-group size observed
            "p50": <int or None>,
            "parallel_runs": <int>,       # runs whose peak was >=2
            "parallel_rate": <float or None>,
          },
          "by_area":  {                   # area-label aggregates
            "area:graph":   {"dispatches": N, "blocked": K, "partial": K, "rework": K},
            ...
          },
          "by_area_note": <str or None>,  # explanation if labels are absent
        }

    Best-effort and pure-read: never raises. An empty graph yields zero counts
    and ``None`` percentiles, which the ``report`` subcommand renders cleanly.
    """
    edges = read_graph() if edges is None else edges

    # Index edges by type for cheap lookup.
    by_type = defaultdict(list)
    for e in edges:
        if isinstance(e, dict):
            by_type[e.get("type")].append(e)

    # Index by (problem, session) for cross-edge joins (dispatch start/end, etc.).
    dispatch_starts = {}     # (problem, session) -> earliest start ts
    dispatch_ends_by_problem = defaultdict(list)
    for e in by_type.get("dispatch_started", []):
        key = (e.get("tgt"), e.get("session"))
        prev = dispatch_starts.get(key)
        if prev is None or (e.get("ts") or "") < (prev or ""):
            dispatch_starts[key] = e.get("ts")

    # Per-unit outcomes.
    outcomes = {"solved": 0, "partial": 0, "blocked": 0}
    total_dispatch = 0
    dispatch_to_pr_latencies = []
    pr_opens_by_problem = {}  # (problem, session) -> earliest pr_opened ts
    for e in by_type.get("pr_opened", []):
        key = (e.get("tgt"), e.get("session"))
        prev = pr_opens_by_problem.get(key)
        if prev is None or (e.get("ts") or "") < (prev or ""):
            pr_opens_by_problem[key] = e.get("ts")

    for e in by_type.get("dispatch_completed", []):
        total_dispatch += 1
        outcome = e.get("outcome")
        if outcome in outcomes:
            outcomes[outcome] += 1
        dispatch_ends_by_problem[(e.get("tgt"), e.get("session"))].append(e)

    # dispatch_to_pr per problem-session: first dispatch_started -> first pr_opened.
    for (problem, session), start_ts in dispatch_starts.items():
        pr_ts = pr_opens_by_problem.get((problem, session))
        if not (start_ts and pr_ts):
            continue
        delta = _ms_between(start_ts, pr_ts)
        if delta is not None and delta >= 0:
            dispatch_to_pr_latencies.append(delta)

    # Run wall time — prefer the wall_time_ms field on run_completed; otherwise
    # compute from the earliest dispatch_started → run_completed ts.
    run_wall_times = []
    # Parallel fanout — collected per run from the run_completed `fanout` field
    # (added in #321). Old graphs without the field simply contribute nothing
    # here, and the aggregate reports n=0.
    fanouts = []
    for e in by_type.get("run_completed", []):
        wall = e.get("wall_time_ms")
        if isinstance(wall, (int, float)) and wall >= 0:
            run_wall_times.append(int(wall))
        else:
            start_ts = dispatch_starts.get((e.get("tgt"), e.get("session")))
            if start_ts and e.get("ts"):
                delta = _ms_between(start_ts, e.get("ts"))
                if delta is not None and delta >= 0:
                    run_wall_times.append(delta)
        fan = e.get("fanout")
        if isinstance(fan, int) and fan >= 1:
            fanouts.append(fan)

    # Rework — count events + distinct problems with at least one rework.
    rework_events = by_type.get("rework", [])
    rework_problems = {e.get("tgt") for e in rework_events if e.get("tgt")}

    # Distinct problems = union of all problem nodes that appear in any
    # agent-execution edge (so the rework rate has a sensible denominator).
    problem_targets = set()
    for t in ("dispatch_started", "dispatch_completed", "pr_opened",
              "run_completed", "rework", "solves"):
        for e in by_type.get(t, []):
            if e.get("tgt"):
                problem_targets.add(e.get("tgt"))
    problems_total = len(problem_targets)

    # By-area aggregates from `labeled` edges.
    by_area = defaultdict(lambda: {"dispatches": 0, "blocked": 0,
                                   "partial": 0, "rework": 0})
    labels_by_problem = defaultdict(set)
    for e in by_type.get("labeled", []):
        for lbl in e.get("labels") or []:
            if isinstance(lbl, str) and lbl.startswith("area:"):
                labels_by_problem[e.get("tgt")].add(lbl)

    for e in by_type.get("dispatch_completed", []):
        for lbl in labels_by_problem.get(e.get("tgt"), ()):
            by_area[lbl]["dispatches"] += 1
            if e.get("outcome") == "blocked":
                by_area[lbl]["blocked"] += 1
            elif e.get("outcome") == "partial":
                by_area[lbl]["partial"] += 1
    for e in rework_events:
        for lbl in labels_by_problem.get(e.get("tgt"), ()):
            by_area[lbl]["rework"] += 1

    by_area_note = None
    if not labels_by_problem:
        by_area_note = (
            "No `labeled` edges yet — area aggregates need the orchestrator to "
            "record Linear labels at dispatch (graph.py labeled --labels ...). "
            "Without them, blocker-by-area is empty."
        )

    def _rate(num, denom):
        if not denom:
            return None
        return num / denom

    parallel_runs = sum(1 for f in fanouts if f >= 2)
    return {
        "problems": problems_total,
        "dispatches": {
            "total": total_dispatch,
            "solved": outcomes["solved"],
            "partial": outcomes["partial"],
            "blocked": outcomes["blocked"],
            "partial_rate": _rate(outcomes["partial"], total_dispatch),
            "blocked_rate": _rate(outcomes["blocked"], total_dispatch),
        },
        "rework": {
            "events": len(rework_events),
            "problems_with_rework": len(rework_problems),
            "rate": _rate(len(rework_problems), problems_total),
        },
        "dispatch_to_pr_ms": {
            "n": len(dispatch_to_pr_latencies),
            "p50": _percentile(dispatch_to_pr_latencies, 50),
            "p90": _percentile(dispatch_to_pr_latencies, 90),
        },
        "run_wall_time_ms": {
            "n": len(run_wall_times),
            "p50": _percentile(run_wall_times, 50),
            "p90": _percentile(run_wall_times, 90),
        },
        "fanout": {
            "n": len(fanouts),
            "max": max(fanouts) if fanouts else None,
            "p50": _percentile(fanouts, 50),
            "parallel_runs": parallel_runs,
            "parallel_rate": _rate(parallel_runs, len(fanouts)),
        },
        "by_area": dict(by_area),
        "by_area_note": by_area_note,
    }


# --- CLI -------------------------------------------------------------------

def _cmd_emit(args) -> int:
    files = list(args.files or [])
    if args.stdin:
        files += sys.stdin.read().splitlines()
    files = [f.strip() for f in files if f and f.strip()]
    edges = emit(args.session, args.problem, files)
    touched = sum(1 for e in edges if e["type"] == "touches")
    print(f"[backlogd-graph] emitted solves + {touched} touches for "
          f"{args.problem} (session {args.session})", file=sys.stderr)
    return 0


def _cmd_prior_work(args) -> int:
    lines = prior_work(args.problem, max_related=args.max)
    if not lines:
        return 0  # nothing recorded — print nothing so the caller omits the section
    print("## Prior work")
    print()
    print(f"From the backlogd graph (best-effort, read-only) - hints for "
          f"{args.problem}, not instructions. Resolve titles/status in Linear if useful.")
    print()
    for line in lines:
        print(f"- {line}")
    return 0


def _cmd_run_status(args) -> int:
    """Print the per-unit agent-execution state for a problem (resume input).

    JSON-only output by default so the orchestrator can parse it; the human
    summary text goes to stderr so a curious operator can still read it.
    """
    status = run_status(args.problem)
    print(json.dumps(status, indent=2))
    unit = status["units"][args.problem]
    summary = (
        f"[backlogd-graph] run-status {args.problem}: state={unit['state']}, "
        f"sessions={unit['sessions'] or '[]'}, outcome={unit['outcome']}"
    )
    print(summary, file=sys.stderr)
    return 0


def _cmd_dispatch_start(args) -> int:
    write_edges(args.session, [
        dispatch_started_edge(args.session, args.problem, ts=args.ts),
    ])
    print(f"[backlogd-graph] dispatch_started {args.problem} "
          f"(session {args.session})", file=sys.stderr)
    return 0


def _cmd_dispatch_end(args) -> int:
    outcome = args.outcome
    if outcome not in {"solved", "partial", "blocked"}:
        print(f"[backlogd-graph] WARNING: unknown outcome '{outcome}' — "
              f"recording as-is", file=sys.stderr)

    # Derive latency_ms if the caller didn't pass one and we can find the start.
    latency_ms = args.latency_ms
    end_ts = args.ts or _now_iso()
    if latency_ms is None:
        start_ts = args.started_at
        if start_ts is None:
            for e in read_graph():
                if (e.get("type") == "dispatch_started"
                        and e.get("session") == args.session
                        and e.get("tgt") == problem_node(args.problem)):
                    start_ts = e.get("ts")
                    break
        if start_ts:
            latency_ms = _ms_between(start_ts, end_ts)

    write_edges(args.session, [
        dispatch_completed_edge(args.session, args.problem, outcome,
                                ts=end_ts, latency_ms=latency_ms),
    ])
    ms_note = f", latency={latency_ms}ms" if latency_ms is not None else ""
    print(f"[backlogd-graph] dispatch_completed {args.problem} "
          f"outcome={outcome}{ms_note} (session {args.session})", file=sys.stderr)
    return 0


def _cmd_pr_opened(args) -> int:
    write_edges(args.session, [
        pr_opened_edge(args.session, args.problem, ts=args.ts),
    ])
    print(f"[backlogd-graph] pr_opened {args.problem} "
          f"(session {args.session})", file=sys.stderr)
    return 0


def _cmd_run_end(args) -> int:
    end_ts = args.ts or _now_iso()
    wall_ms = args.wall_time_ms
    if wall_ms is None:
        start_ts = args.started_at
        if start_ts is None:
            # Fall back to the earliest dispatch_started for this problem/session.
            earliest = None
            for e in read_graph():
                if (e.get("type") == "dispatch_started"
                        and e.get("session") == args.session
                        and e.get("tgt") == problem_node(args.problem)):
                    ts = e.get("ts")
                    if ts and (earliest is None or ts < earliest):
                        earliest = ts
            start_ts = earliest
        if start_ts:
            wall_ms = _ms_between(start_ts, end_ts)

    fanout = args.fanout
    if fanout is not None:
        # Clamp defensively; the walk already clamps to [1, 4] but a stray
        # caller shouldn't poison the graph.
        if fanout < 1:
            fanout = 1
        if fanout > 64:  # generous ceiling — the walk's hard cap is 4
            fanout = 64

    write_edges(args.session, [
        run_completed_edge(args.session, args.problem,
                           ts=end_ts, wall_time_ms=wall_ms, fanout=fanout),
    ])
    ms_note = f", wall_time={wall_ms}ms" if wall_ms is not None else ""
    fan_note = f", fanout={fanout}" if fanout is not None else ""
    print(f"[backlogd-graph] run_completed {args.problem}{ms_note}{fan_note} "
          f"(session {args.session})", file=sys.stderr)
    return 0


def _cmd_rework(args) -> int:
    # Hash the notes if provided, so we don't leak text into the graph store.
    notes_hash = args.notes_hash
    if notes_hash is None and args.notes:
        notes_hash = hashlib.sha256(args.notes.encode("utf-8")).hexdigest()[:12]

    # Give each rework event a distinct session-suffix so multiple events for
    # the same problem don't collapse via the (src,tgt,type,session) dedup key.
    ts = args.ts or _now_iso()
    suffix = ts.replace(":", "").replace("-", "")
    event_session = f"{args.session}#rework-{suffix}"

    write_edges(event_session, [
        rework_edge(event_session, args.problem, ts=ts, notes_hash=notes_hash),
    ])
    note = f", notes_hash={notes_hash}" if notes_hash else ""
    print(f"[backlogd-graph] rework {args.problem}{note} "
          f"(session {event_session})", file=sys.stderr)
    return 0


def _cmd_labeled(args) -> int:
    labels = list(args.labels or [])
    if args.stdin:
        labels += [ln.strip() for ln in sys.stdin.read().splitlines() if ln.strip()]
    write_edges(args.session, [
        labeled_edge(args.session, args.problem, labels, ts=args.ts),
    ])
    print(f"[backlogd-graph] labeled {args.problem} labels={labels} "
          f"(session {args.session})", file=sys.stderr)
    return 0


def _format_ms(ms):
    if ms is None:
        return "—"
    ms = int(ms)
    if ms < 1000:
        return f"{ms}ms"
    s = ms / 1000.0
    if s < 60:
        return f"{s:.1f}s"
    m = s / 60.0
    if m < 60:
        return f"{m:.1f}m"
    h = m / 60.0
    return f"{h:.1f}h"


def _format_rate(rate):
    if rate is None:
        return "—"
    return f"{rate*100:.0f}%"


def _cmd_report(args) -> int:
    m = metrics()
    if args.json:
        print(json.dumps(m, indent=2))
        return 0

    d = m["dispatches"]
    rw = m["rework"]
    pr = m["dispatch_to_pr_ms"]
    wt = m["run_wall_time_ms"]
    fn = m["fanout"]

    print("# backlogd — agent-execution metrics")
    print()
    print(f"Problems observed: **{m['problems']}**    "
          f"Dispatches: **{d['total']}**")
    print()
    print("| Metric | Value |")
    print("|---|---|")
    print(f"| Rework rate (problems with ≥1 rework / problems) | "
          f"{_format_rate(rw['rate'])} ({rw['problems_with_rework']}/{m['problems']}, "
          f"{rw['events']} events) |")
    print(f"| Partial rate (dispatches returning `partial`) | "
          f"{_format_rate(d['partial_rate'])} ({d['partial']}/{d['total']}) |")
    print(f"| Blocked rate (dispatches returning `blocked`) | "
          f"{_format_rate(d['blocked_rate'])} ({d['blocked']}/{d['total']}) |")
    print(f"| Dispatch→PR latency p50 (n={pr['n']}) | {_format_ms(pr['p50'])} |")
    print(f"| Dispatch→PR latency p90 (n={pr['n']}) | {_format_ms(pr['p90'])} |")
    print(f"| Run wall time p50 (n={wt['n']}) | {_format_ms(wt['p50'])} |")
    print(f"| Run wall time p90 (n={wt['n']}) | {_format_ms(wt['p90'])} |")
    if fn["n"]:
        parallel_note = (
            f"{fn['parallel_runs']}/{fn['n']} runs ran a parallel group "
            f"({_format_rate(fn['parallel_rate'])})"
        )
        max_fan = fn["max"] if fn["max"] is not None else "—"
        print(f"| Parallel walk (peak group size; #321) | "
              f"max={max_fan}, {parallel_note} |")
    print()
    print("## Blocker frequency by area")
    print()
    if m["by_area"]:
        print("| Area label | Dispatches | Blocked | Partial | Rework |")
        print("|---|---:|---:|---:|---:|")
        rows = sorted(m["by_area"].items(),
                      key=lambda kv: (-kv[1]["blocked"], -kv[1]["partial"], kv[0]))
        for area, counts in rows:
            print(f"| {area} | {counts['dispatches']} | {counts['blocked']} "
                  f"| {counts['partial']} | {counts['rework']} |")
    else:
        note = m.get("by_area_note") or "No area labels recorded yet."
        print(f"_{note}_")
    return 0


def main(argv=None) -> int:
    """CLI entry point. Subcommands:

    Reads:
      * ``prior-work``      — print Prior work block for a problem (best-effort).
      * ``run-status``      — print per-unit agent-execution state as JSON
        (used by ``/backlogd:solve``'s resume reconcile step).
      * ``report``          — print agent-execution metrics summary.

    Agent-execution writes (the new flow):
      * ``dispatch-start``  — record ``dispatch_started`` for a unit.
      * ``dispatch-end``    — record ``dispatch_completed`` w/ outcome + latency.
      * ``pr-opened``       — record ``pr_opened`` for the problem.
      * ``run-end``         — record ``run_completed`` w/ wall time.
      * ``rework``          — record a ``rework`` event for the problem.
      * ``labeled``         — attach Linear labels to a session→problem.

    Legacy write:
      * ``emit``            — append legacy ``solves`` + ``touches`` edges.

    Every subcommand is best-effort by design — any error is logged to stderr
    and the process still exits 0, so wiring these into the scrum loop can
    never block it.
    """
    # Force UTF-8 on stdout/stderr so the markdown report's Unicode (— → ≥)
    # prints cleanly under Windows' default cp1252 console too. Best-effort.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001 — never block the CLI
                pass

    parser = argparse.ArgumentParser(prog="graph.py", description="backlogd graph CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # --- legacy emit -----------------------------------------------------
    pe = sub.add_parser("emit",
                        help="append legacy solves + touches edges (best-effort)")
    pe.add_argument("--session", required=True, help="session id for this run")
    pe.add_argument("--problem", required=True, help="Linear identifier, e.g. NB-266")
    pe.add_argument("--files", nargs="*", default=[], help="touched file paths")
    pe.add_argument("--stdin", action="store_true",
                    help="also read newline-separated paths from stdin")
    pe.set_defaults(func=_cmd_emit)

    # --- reads -----------------------------------------------------------
    pw = sub.add_parser("prior-work",
                        help="print a Prior work block for a problem, or nothing")
    pw.add_argument("--problem", required=True, help="Linear identifier, e.g. NB-266")
    pw.add_argument("--max", type=int, default=5, help="max related problems to list")
    pw.set_defaults(func=_cmd_prior_work)

    pr = sub.add_parser("report",
                        help="print agent-execution metrics (markdown by default)")
    pr.add_argument("--json", action="store_true",
                    help="emit the raw metrics dict as JSON instead of markdown")
    pr.set_defaults(func=_cmd_report)

    rs = sub.add_parser(
        "run-status",
        help="print per-unit agent-execution state for a problem as JSON "
             "(input for /backlogd:solve's resume reconcile)")
    rs.add_argument("--problem", required=True,
                    help="Linear identifier of the unit to inspect, e.g. NB-322")
    rs.set_defaults(func=_cmd_run_status)

    # --- agent-execution writes -----------------------------------------
    ds = sub.add_parser("dispatch-start",
                        help="record a dispatch_started edge for a unit")
    ds.add_argument("--session", required=True)
    ds.add_argument("--problem", required=True, help="unit issue identifier")
    ds.add_argument("--ts", default=None, help="override timestamp (ISO-8601 UTC)")
    ds.set_defaults(func=_cmd_dispatch_start)

    de = sub.add_parser("dispatch-end",
                        help="record a dispatch_completed edge with outcome")
    de.add_argument("--session", required=True)
    de.add_argument("--problem", required=True)
    de.add_argument("--outcome", required=True,
                    choices=["solved", "partial", "blocked"])
    de.add_argument("--ts", default=None, help="completion timestamp (ISO-8601 UTC)")
    de.add_argument("--started-at", default=None,
                    help="explicit dispatch start timestamp (ISO-8601 UTC); "
                         "otherwise inferred from the matching dispatch_started edge")
    de.add_argument("--latency-ms", type=int, default=None,
                    help="explicit latency in milliseconds; otherwise computed")
    de.set_defaults(func=_cmd_dispatch_end)

    po = sub.add_parser("pr-opened", help="record a pr_opened edge")
    po.add_argument("--session", required=True)
    po.add_argument("--problem", required=True)
    po.add_argument("--ts", default=None)
    po.set_defaults(func=_cmd_pr_opened)

    re_ = sub.add_parser("run-end",
                         help="record a run_completed edge with wall time")
    re_.add_argument("--session", required=True)
    re_.add_argument("--problem", required=True)
    re_.add_argument("--ts", default=None)
    re_.add_argument("--started-at", default=None,
                     help="explicit run start timestamp; otherwise the earliest "
                          "dispatch_started for this problem/session")
    re_.add_argument("--wall-time-ms", type=int, default=None)
    re_.add_argument("--fanout", type=int, default=None,
                     help="peak parallel-group size observed during this run "
                          "(1=sequential, ≥2=parallel walk). Recorded on the "
                          "run_completed edge for the metrics aggregate (#321).")
    re_.set_defaults(func=_cmd_run_end)

    rw = sub.add_parser("rework",
                        help="record a rework event for a problem (sent back from In Review)")
    rw.add_argument("--session", required=True,
                    help="reviewer session id (a per-event suffix is appended automatically)")
    rw.add_argument("--problem", required=True)
    rw.add_argument("--ts", default=None)
    rw.add_argument("--notes", default=None,
                    help="rework note text; only its sha256 prefix is stored")
    rw.add_argument("--notes-hash", default=None,
                    help="pre-computed notes hash (use this if you already hashed)")
    rw.set_defaults(func=_cmd_rework)

    lb = sub.add_parser("labeled",
                        help="attach Linear labels to a session→problem (for area aggregates)")
    lb.add_argument("--session", required=True)
    lb.add_argument("--problem", required=True)
    lb.add_argument("--labels", nargs="*", default=[],
                    help="label names (e.g. area:graph problem)")
    lb.add_argument("--stdin", action="store_true",
                    help="also read newline-separated label names from stdin")
    lb.add_argument("--ts", default=None)
    lb.set_defaults(func=_cmd_labeled)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:  # noqa: BLE001 — best-effort: never blow up the caller
        print(f"[backlogd-graph] CLI error: {exc}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
