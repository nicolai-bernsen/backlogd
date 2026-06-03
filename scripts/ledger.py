"""backlogd solve ledger — a durable, problem-keyed record of completed runs.

A ``/backlogd:solve`` run today leaves its trace across Linear comments, the PR,
and the execution graph (``scripts/graph.py`` → ``.backlogd/graph/``). The graph
is *session-keyed, edge-level telemetry* with an evolving internal schema,
optimised for metrics. This ledger is the complementary store the PO ruled in
(NB-426): a compact, **problem-keyed, append-only durable run record** with a
**stable read contract**, so a re-run can short-circuit and a later
retrospective can read run history with one cheap local lookup — no Linear
round-trip.

The two stores are a deliberate dual write. To keep them from silently
disagreeing, the orchestrator appends the ledger record at the **same lifecycle
point** the graph records a completed run (``skills/solve/handoff.md`` §2, right
after ``graph.py run-end``). The graph remains the metrics source of truth; the
ledger is the problem-first durable record.

Storage
-------
**Append-only JSONL** — one JSON object per line — at ``.backlogd/ledger.jsonl``
relative to the current working directory (the repository backlogd is operating
on). Override the *directory* with ``BACKLOGD_LEDGER_DIR`` or the *full file
path* with ``BACKLOGD_LEDGER_FILE`` (both used by tests). JSONL is chosen
deliberately: recording a run is a single append of one line, which by
construction cannot truncate or rewrite the records already on disk — the
append-friendliness AC. (The graph, by contrast, rewrites a whole JSON array per
session file; that's fine for its dedup semantics but is not append-only.)

Record shape (``backlogd-ledger/v1``)::

    {
      "v": "backlogd-ledger/v1",
      "problem": "NB-426",            # the problem identifier (the key)
      "units": [                       # the units solved, with their outcomes
        {"identifier": "NB-426", "outcome": "solved"}
      ],
      "pr": "https://github.com/.../pull/131",   # PR reference, or null (ops-only)
      "outcome": "solved",            # the run-level outcome
      "ts": "2026-06-03T05:00:00Z"    # when the run completed (ISO-8601 UTC)
    }

The read contract is stable: ``read_runs(problem)`` returns the list of records
for that problem identifier, oldest-first (file order). Unknown fields on a
record are preserved on read — the schema is additive, exactly like the graph's.

Design notes
------------
* Pure Python standard library — zero third-party dependencies (matches
  ``scripts/graph.py`` and the repo's stdlib-only ``scripts/`` rule).
* Windows-safe — ``pathlib`` throughout.
* Best-effort write — failures are logged to stderr and swallowed; ledger
  persistence must never block the scrum loop (same contract as the graph).
* Append-only — ``record_run`` only ever appends; it never reads-modifies-writes
  the file, so a second recorded run cannot truncate the first.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

__all__ = [
    "LEDGER_VERSION",
    "ledger_path",
    "record_run",
    "read_all",
    "read_runs",
]

LEDGER_VERSION = "backlogd-ledger/v1"
_DEFAULT_DIR = Path(".backlogd")
_DEFAULT_FILENAME = "ledger.jsonl"


# --- location -------------------------------------------------------------

def ledger_path() -> Path:
    """Return the ledger file path.

    Resolution order (read at call time so tests can redirect without
    reimporting):

    1. ``BACKLOGD_LEDGER_FILE`` — an explicit full path to the ledger file.
    2. ``BACKLOGD_LEDGER_DIR`` — a directory; the ledger is ``<dir>/ledger.jsonl``.
    3. Default — ``.backlogd/ledger.jsonl`` relative to the current working
       directory (the repo backlogd is operating on; ``.backlogd/`` is
       gitignored, like the graph store beside it).
    """
    file_override = os.environ.get("BACKLOGD_LEDGER_FILE")
    if file_override:
        return Path(file_override)
    dir_override = os.environ.get("BACKLOGD_LEDGER_DIR")
    base = Path(dir_override) if dir_override else _DEFAULT_DIR
    return base / _DEFAULT_FILENAME


# --- helpers --------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalise_units(units) -> list:
    """Coerce the ``units`` argument into a list of ``{identifier, outcome}`` dicts.

    Accepts either dicts (passed through, keeping any extra keys) or bare
    identifier strings (wrapped as ``{"identifier": s, "outcome": None}``), so
    callers can record a quick list of identifiers or a richer per-unit shape.
    """
    out = []
    for u in units or []:
        if isinstance(u, dict):
            out.append(u)
        elif isinstance(u, str) and u.strip():
            out.append({"identifier": u.strip(), "outcome": None})
    return out


def build_record(problem, units=None, pr=None, outcome=None, ts=None) -> dict:
    """Construct a well-formed ``backlogd-ledger/v1`` run record dict.

    Kept separate from the write so callers (and tests) can build a record
    without touching disk. ``problem`` is the key; ``units`` is the list of
    units solved (dicts or bare identifier strings); ``pr`` is the PR reference
    (or ``None`` on an ops-only run); ``outcome`` is the run-level outcome;
    ``ts`` defaults to now (UTC).
    """
    return {
        "v": LEDGER_VERSION,
        "problem": problem,
        "units": _normalise_units(units),
        "pr": pr,
        "outcome": outcome,
        "ts": ts or _now_iso(),
    }


# --- write (append-only) --------------------------------------------------

def record_run(problem, units=None, pr=None, outcome=None, ts=None) -> dict:
    """Append one completed-run record to the ledger. Best-effort.

    Appends a single JSONL line — it never reads-modifies-writes the file, so a
    second recorded run cannot truncate or overwrite the first (append-only by
    construction). Creates the parent directory if needed. Any failure is logged
    to stderr and swallowed — ledger persistence must never block the scrum
    loop. Returns the record it built (handy for callers and tests) even if the
    write failed.
    """
    record = build_record(problem, units=units, pr=pr, outcome=outcome, ts=ts)
    try:
        path = ledger_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, ensure_ascii=False)
        # Append mode: the OS positions writes at end-of-file; we never rewrite
        # existing bytes. One line per record keeps the file append-only.
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception as exc:  # noqa: BLE001 — best-effort persistence
        print(
            f"[backlogd-ledger] ERROR: record_run failed for '{problem}': {exc}",
            file=sys.stderr,
        )
    return record


# --- read (stable contract) -----------------------------------------------

def read_all() -> list:
    """Return every run record in the ledger, oldest-first (file order).

    A missing or empty ledger returns ``[]`` (never raises). Malformed lines are
    skipped with a stderr warning so one bad append can't poison the read — the
    append-only design means a partial line is the only corruption risk, and
    skipping it preserves every well-formed record around it.
    """
    path = ledger_path()
    if not path.exists():
        return []
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"[backlogd-ledger] WARNING: cannot read {path}: {exc}", file=sys.stderr)
        return []
    records = []
    for lineno, line in enumerate(raw.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            print(
                f"[backlogd-ledger] WARNING: skipping malformed line {lineno} "
                f"in {path}: {exc}",
                file=sys.stderr,
            )
            continue
        if isinstance(obj, dict):
            records.append(obj)
    return records


def read_runs(problem, records=None) -> list:
    """Return the completed-run record(s) for ``problem``, oldest-first.

    This is the ledger's primary read surface (the resume short-circuit and the
    retro's local history both use it): give it a problem identifier, get back
    that problem's run records — each naming the units solved with their
    outcomes, the PR reference, and the run timestamp. Returns ``[]`` when the
    ledger has nothing for the problem. Pure read; never raises.
    """
    records = read_all() if records is None else records
    return [r for r in records
            if isinstance(r, dict) and r.get("problem") == problem]


# --- CLI ------------------------------------------------------------------

def _cmd_record_run(args) -> int:
    units = list(args.units or [])
    if args.stdin:
        units += [ln.strip() for ln in sys.stdin.read().splitlines() if ln.strip()]
    rec = record_run(
        args.problem,
        units=units,
        pr=args.pr,
        outcome=args.outcome,
        ts=args.ts,
    )
    n_units = len(rec["units"])
    pr_note = f", pr={args.pr}" if args.pr else ""
    print(
        f"[backlogd-ledger] recorded run {args.problem} "
        f"(units={n_units}, outcome={args.outcome}{pr_note})",
        file=sys.stderr,
    )
    return 0


def _cmd_read(args) -> int:
    """Print the ledger record(s) as JSON.

    With ``--problem`` → that problem's records (the resume / retro read);
    without → the whole ledger, oldest-first.
    """
    if args.problem:
        print(json.dumps(read_runs(args.problem), indent=2))
    else:
        print(json.dumps(read_all(), indent=2))
    return 0


def main(argv=None) -> int:
    """CLI entry point. Subcommands:

    Write (the new flow — co-located with ``graph.py run-end`` at handoff):
      * ``record-run`` — append one completed-run record for a problem.

    Read (resume short-circuit + retro local history):
      * ``read``       — print a problem's records (``--problem``) or all of them.

    Every subcommand is best-effort by design — any error is logged to stderr
    and the process still exits 0, so wiring these into the scrum loop can never
    block it.
    """
    # Force UTF-8 on stdout/stderr so any Unicode prints cleanly under Windows'
    # default cp1252 console too. Best-effort (mirrors graph.py).
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001 — never block the CLI
                pass

    parser = argparse.ArgumentParser(prog="ledger.py",
                                     description="backlogd solve ledger CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    rr = sub.add_parser("record-run",
                        help="append one completed-run record for a problem")
    rr.add_argument("--problem", required=True,
                    help="problem identifier (the ledger key), e.g. NB-426")
    rr.add_argument("--units", nargs="*", default=[],
                    help="unit identifiers solved (e.g. NB-426 NB-427); for "
                         "per-unit outcomes pass JSON via --units-json instead")
    rr.add_argument("--units-json", default=None,
                    help="JSON array of unit objects "
                         "(e.g. '[{\"identifier\":\"NB-1\",\"outcome\":\"solved\"}]'); "
                         "takes precedence over --units when given")
    rr.add_argument("--pr", default=None, help="PR reference (URL or number)")
    rr.add_argument("--outcome", default=None,
                    help="run-level outcome (e.g. solved)")
    rr.add_argument("--ts", default=None,
                    help="completion timestamp (ISO-8601 UTC); defaults to now")
    rr.add_argument("--stdin", action="store_true",
                    help="also read newline-separated unit identifiers from stdin")
    rr.set_defaults(func=_cmd_record_run)

    rd = sub.add_parser("read",
                        help="print run record(s) as JSON (problem-keyed or all)")
    rd.add_argument("--problem", default=None,
                    help="print only this problem's records; omit for the whole ledger")
    rd.set_defaults(func=_cmd_read)

    args = parser.parse_args(argv)

    # --units-json wins over --units when both are present.
    if getattr(args, "units_json", None):
        try:
            parsed = json.loads(args.units_json)
            if isinstance(parsed, list):
                args.units = parsed
        except json.JSONDecodeError as exc:
            print(f"[backlogd-ledger] WARNING: bad --units-json ({exc}); "
                  f"falling back to --units", file=sys.stderr)

    try:
        return args.func(args)
    except Exception as exc:  # noqa: BLE001 — best-effort: never blow up the caller
        print(f"[backlogd-ledger] CLI error: {exc}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
