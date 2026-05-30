"""backlogd standards index — make the ADR corpus agent-readable & selectively loadable.

Why this exists
---------------
A reviewer must enforce the standards corpus (``docs/standards/adrs/``) on every
change. Loading the full prose ADR set into context each time is the failure this
script prevents: it is slow, it burns the context/token budget (the NB-379 quota
pressure), and a reviewer swimming in N prose ADRs misses the one that applies.

The win is mostly in the **authoring format**, not the storage backend (NB-380): each
ADR carries machine-readable front-matter — a crisp **checkable assertion**, an
**applies-to** scope (domains / file-patterns / decision-types), and a lifecycle
**status**. From that this script generates a single small **committed** artifact,
``docs/standards/index.json`` (id · title · assertion · applies-to · status), that a
reviewer reads *first* — cheap — then filters by scope and opens only the full ADRs
whose rationale it actually needs. Bounded context regardless of corpus size.

v1 is **index/files only — no graph DB, no server** (keyless/serverless principle;
zero third-party deps, same as ``scripts/graph.py``). The Neo4j corpus⨝execution-graph
join (NB-320) is the explicitly-named v2 follow-up and is *not* built here.

Usage
-----
* ``python scripts/standards_index.py``            — regenerate the index (writes the file)
* ``python scripts/standards_index.py --check``    — validate front-matter only; exit
  non-zero if any ADR under ``docs/standards/adrs/`` is missing a required key (writes nothing)
* ``python scripts/standards_index.py --print``    — print the freshly-built index JSON to
  stdout (writes nothing) — handy for the drift checker / debugging

The companion ``scripts/test_standards_index.py`` is the **sync checker**: it rebuilds the
index from the corpus and fails if the committed ``index.json`` has drifted (an ADR added or
edited without regenerating). Run it with ``python -m pytest scripts/test_standards_index.py``
or via the repo's ``python -m unittest discover -s scripts -p 'test_*.py'`` (CI uses the latter).

Front-matter reader
-------------------
Deliberately **not** a general YAML parser — PyYAML is not a guaranteed dependency in CI
(the workflow runs the stdlib only) and the repo's design principle is zero third-party
runtime deps. Instead this reads the leading ``---``-fenced block and parses the small,
fixed subset the ADR convention uses (see ``docs/standards/adrs/TEMPLATE.md``):

* scalar ``key: value`` (optionally quoted),
* inline lists ``key: [a, b, c]``,
* the nested ``applies-to:`` mapping whose three sub-keys (``domains`` /
  ``file-patterns`` / ``decision-types``) are each an inline or block list.

Anything outside that subset is out of scope by design — the front-matter is a fixed,
small schema, not arbitrary YAML.
"""

import argparse
import json
import sys
from pathlib import Path

__all__ = [
    "ADRS_DIR",
    "INDEX_PATH",
    "REQUIRED_KEYS",
    "APPLIES_TO_SUBKEYS",
    "FrontMatterError",
    "split_front_matter",
    "parse_front_matter",
    "read_adr",
    "load_adrs",
    "validate",
    "build_index",
    "render_index",
    "write_index",
]

# --- locations -------------------------------------------------------------

# Resolve relative to this file so the script works from any cwd (CI runs it
# from the repo root, but tests and ad-hoc callers may not).
_REPO_ROOT = Path(__file__).resolve().parent.parent
ADRS_DIR = _REPO_ROOT / "docs" / "standards" / "adrs"
INDEX_PATH = _REPO_ROOT / "docs" / "standards" / "index.json"

# The schema version stamped onto the generated index so a future reader can
# detect format changes. Bump when the index shape changes.
INDEX_VERSION = "backlogd-standards/v1"

# Front-matter keys every ADR must carry. `assertion` + `applies-to` are the
# machine-readable keys NB-380 adds on top of NB-377's id/title/status/date.
REQUIRED_KEYS = ("id", "title", "status", "date", "assertion", "applies-to")

# Of those, the ones that must be a **non-empty scalar string**. `applies-to` is the
# sole exception — it is legitimately a nested mapping (validated separately). A
# value-less ``key:`` parses to ``{}`` via the front-matter reader, so a scalar-required
# key whose value is not a non-empty ``str`` (e.g. a blank ``assertion:``) is treated as
# missing/invalid — semantically it is a missing required key (AC1: must exit non-zero).
SCALAR_REQUIRED_KEYS = ("id", "title", "status", "date", "assertion")

# The three axes of `applies-to`. At least one must be non-empty (a standard
# that applies to nothing is dead weight).
APPLIES_TO_SUBKEYS = ("domains", "file-patterns", "decision-types")

# Files under the ADR dir that are not ADRs and must be skipped by the index.
_NON_ADR_FILES = {"TEMPLATE.md"}


class FrontMatterError(ValueError):
    """Raised when an ADR's front-matter is missing or malformed."""


# --- front-matter reader (zero-dep, fixed subset) --------------------------

def split_front_matter(text: str):
    """Return the raw front-matter block (string) from a ``---``-fenced header.

    The header must be the very first thing in the file: a line that is exactly
    ``---``, then the YAML body, then a closing ``---`` line. Returns the body
    between the fences (without the fences). Raises ``FrontMatterError`` if there
    is no opening or closing fence.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise FrontMatterError("no opening '---' front-matter fence on line 1")
    body = []
    for line in lines[1:]:
        if line.strip() == "---":
            return "\n".join(body)
        body.append(line)
    raise FrontMatterError("no closing '---' front-matter fence")


def _strip_inline_comment(value: str) -> str:
    """Drop a trailing ``# comment`` from a scalar value, respecting quotes.

    Only strips a ``#`` that is *not* inside a quoted string and is preceded by
    whitespace (so ``ADR-NNN`` and ``#N`` inside text survive). Conservative by
    design — the front-matter schema is small.
    """
    in_single = in_double = False
    for i, ch in enumerate(value):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            if i == 0 or value[i - 1] in " \t":
                return value[:i].rstrip()
    return value


def _unquote(value: str) -> str:
    """Strip one matching pair of surrounding quotes from a scalar, if present."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def _parse_inline_list(value: str) -> list:
    """Parse ``[a, b, "c d"]`` into ``['a', 'b', 'c d']``. Empty ``[]`` -> ``[]``."""
    inner = value.strip()[1:-1].strip()  # drop the surrounding [ ]
    if not inner:
        return []
    return [_unquote(item) for item in _split_top_level_commas(inner)]


def _split_top_level_commas(inner: str) -> list:
    """Split on commas that are not inside quotes."""
    parts, buf = [], []
    in_single = in_double = False
    for ch in inner:
        if ch == "'" and not in_double:
            in_single = not in_single
            buf.append(ch)
        elif ch == '"' and not in_single:
            in_double = not in_double
            buf.append(ch)
        elif ch == "," and not in_single and not in_double:
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf).strip())
    return [p for p in parts if p != ""]


def parse_front_matter(block: str) -> dict:
    """Parse the fixed front-matter subset into a dict.

    Handles top-level ``key: value`` scalars, top-level inline lists, and the
    nested ``applies-to:`` mapping (block- or inline-form, with list sub-values).
    Indented ``key: value`` lines immediately under a mapping key become that
    mapping's entries. Blank lines and ``# comment`` lines are ignored.

    Scalars are coerced: ``~`` / ``null`` -> ``None``. Everything else stays a
    string (or a list for ``[...]`` values).
    """
    result: dict = {}
    current_map_key = None  # the top-level key whose indented block we're inside
    current_map: dict = {}

    raw_lines = block.split("\n")
    for raw in raw_lines:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indented = raw[0] in " \t"
        line = raw.strip()
        if ":" not in line:
            raise FrontMatterError(f"front-matter line has no ':' — {raw!r}")
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()

        if indented:
            # An entry inside the most-recent mapping key (e.g. under applies-to).
            if current_map_key is None:
                raise FrontMatterError(
                    f"indented line with no parent mapping key — {raw!r}")
            current_map[key] = _coerce_scalar_or_list(rest)
            continue

        # A new top-level key — close any open mapping first.
        if current_map_key is not None:
            result[current_map_key] = current_map
            current_map_key, current_map = None, {}

        if rest == "":
            # A bare ``key:`` opens a nested mapping block.
            current_map_key = key
            current_map = {}
        else:
            result[key] = _coerce_scalar_or_list(rest)

    if current_map_key is not None:
        result[current_map_key] = current_map
    return result


def _coerce_scalar_or_list(rest: str):
    """Coerce a value string: inline list, null sentinel, or unquoted scalar.

    Inline comments (`` # …``) are stripped **only** in the contexts where the ADR
    convention actually uses them — after an inline list (``[...]  # e.g. …``) and
    after the null sentinel (``~  # none``). A free-text scalar (notably
    ``assertion:``) keeps a `` #`` verbatim, so an assertion may safely reference a
    `` #N`` issue without being silently truncated.
    """
    if rest.startswith("["):
        # A list, possibly followed by a trailing comment: ``[a, b]  # note``.
        end = rest.rfind("]")
        if end != -1:
            return _parse_inline_list(rest[: end + 1])
        return _parse_inline_list(rest)
    # Null sentinel, tolerating a trailing comment (``~  # none``).
    head = _strip_inline_comment(rest).strip()
    if head in ("~", "null", "Null", "NULL"):
        return None
    return _unquote(rest)


# --- ADR loading -----------------------------------------------------------

def read_adr(path: Path) -> dict:
    """Read one ADR file and return its parsed front-matter dict.

    Raises ``FrontMatterError`` (with the file name) if the header is missing or
    malformed.
    """
    text = path.read_text(encoding="utf-8")
    try:
        block = split_front_matter(text)
        return parse_front_matter(block)
    except FrontMatterError as exc:
        raise FrontMatterError(f"{path.name}: {exc}") from exc


def load_adrs(adrs_dir: Path = None) -> list:
    """Load every ADR's front-matter from ``adrs_dir``, sorted by ``id``.

    Skips non-ADR files (``TEMPLATE.md``). Returns a list of ``(path, front_matter)``
    tuples. Does **not** validate — call ``validate`` for that.
    """
    adrs_dir = ADRS_DIR if adrs_dir is None else Path(adrs_dir)
    out = []
    for path in sorted(adrs_dir.glob("ADR-*.md")):
        if path.name in _NON_ADR_FILES:
            continue
        out.append((path, read_adr(path)))
    out.sort(key=lambda pf: str(pf[1].get("id") or pf[0].name))
    return out


# --- validation ------------------------------------------------------------

def validate(adrs_dir: Path = None) -> list:
    """Validate every ADR's front-matter. Return a list of human-readable errors.

    An empty list means the corpus is valid. Each error names the offending file
    and what is wrong. Checks, per ADR:

    * the front-matter block parses,
    * every key in ``REQUIRED_KEYS`` is present and non-empty,
    * ``applies-to`` is a mapping with the three known sub-keys, each a list, and
      at least one of them non-empty.
    """
    adrs_dir = ADRS_DIR if adrs_dir is None else Path(adrs_dir)
    errors: list = []

    if not adrs_dir.is_dir():
        return [f"ADR directory not found: {adrs_dir}"]

    paths = [p for p in sorted(adrs_dir.glob("ADR-*.md"))
             if p.name not in _NON_ADR_FILES]
    if not paths:
        return [f"no ADR files (ADR-*.md) found under {adrs_dir}"]

    for path in paths:
        name = path.name
        try:
            fm = read_adr(path)
        except FrontMatterError as exc:
            errors.append(str(exc))
            continue

        for key in REQUIRED_KEYS:
            if key not in fm:
                errors.append(f"{name}: missing required front-matter key: {key!r}")
                continue
            if key in SCALAR_REQUIRED_KEYS:
                val = fm[key]
                # A scalar-required key must be a non-empty string. A value-less
                # ``key:`` parses to an empty mapping (``{}``); a blank/quoted-empty
                # value parses to ``""``. Either way it is not a usable value —
                # treat it as missing (AC1: a missing required key exits non-zero).
                if not isinstance(val, str) or not val.strip():
                    errors.append(
                        f"{name}: required key {key!r} is empty or value-less "
                        f"(must be a non-empty string)")

        # applies-to shape (only if present — a missing key is already reported).
        if "applies-to" in fm:
            errors.extend(_validate_applies_to(name, fm["applies-to"]))

    return errors


def _validate_applies_to(name: str, applies_to) -> list:
    errors = []
    if not isinstance(applies_to, dict):
        return [f"{name}: 'applies-to' must be a mapping of "
                f"{', '.join(APPLIES_TO_SUBKEYS)}"]
    unknown = set(applies_to) - set(APPLIES_TO_SUBKEYS)
    if unknown:
        errors.append(f"{name}: 'applies-to' has unknown sub-key(s): "
                      f"{', '.join(sorted(unknown))} "
                      f"(allowed: {', '.join(APPLIES_TO_SUBKEYS)})")
    any_non_empty = False
    for sub in APPLIES_TO_SUBKEYS:
        if sub not in applies_to:
            continue  # an axis may be omitted; treated as []
        val = applies_to[sub]
        if not isinstance(val, list):
            errors.append(f"{name}: 'applies-to.{sub}' must be a list")
            continue
        if val:
            any_non_empty = True
    if not any_non_empty:
        errors.append(f"{name}: 'applies-to' must have at least one non-empty "
                      f"axis ({', '.join(APPLIES_TO_SUBKEYS)})")
    return errors


# --- index build -----------------------------------------------------------

def _normalise_applies_to(applies_to) -> dict:
    """Return applies-to as a full mapping with all three axes as lists.

    Missing axes become ``[]`` so the index shape is uniform regardless of how
    sparsely the ADR filled it in.
    """
    applies_to = applies_to if isinstance(applies_to, dict) else {}
    return {sub: list(applies_to.get(sub) or []) for sub in APPLIES_TO_SUBKEYS}


def build_index(adrs_dir: Path = None) -> dict:
    """Build the compact index dict from the corpus front-matter.

    Shape::

        {
          "version": "backlogd-standards/v1",
          "standards": [
            {"id", "title", "status", "assertion", "applies-to": {...}}, ...
          ]
        }

    ``standards`` is sorted by ``id`` for a stable, diff-friendly artifact. This
    is the payload a reviewer reads first (cheap) before opening any full ADR.
    Raises ``FrontMatterError`` if an ADR's header is malformed.
    """
    entries = []
    for _path, fm in load_adrs(adrs_dir):
        entries.append({
            "id": fm.get("id"),
            "title": fm.get("title"),
            "status": fm.get("status"),
            "assertion": fm.get("assertion"),
            "applies-to": _normalise_applies_to(fm.get("applies-to")),
        })
    entries.sort(key=lambda e: str(e.get("id") or ""))
    return {"version": INDEX_VERSION, "standards": entries}


def render_index(index: dict) -> str:
    """Render the index dict to the canonical on-disk JSON string.

    Pretty-printed with a trailing newline so the committed file is stable and
    diff-friendly (and so the drift checker compares apples to apples).
    """
    return json.dumps(index, indent=2, ensure_ascii=False) + "\n"


def write_index(adrs_dir: Path = None, index_path: Path = None) -> Path:
    """Build the index and write it to ``index_path``. Returns the path written."""
    index_path = INDEX_PATH if index_path is None else Path(index_path)
    index = build_index(adrs_dir)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(render_index(index), encoding="utf-8")
    return index_path


# --- CLI -------------------------------------------------------------------

def _reconfigure_utf8():
    """Force UTF-8 on stdout/stderr so diagnostics print cleanly on Windows."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001 — never block the CLI
                pass


def main(argv=None) -> int:
    """CLI entry point.

    * default        — regenerate ``docs/standards/index.json`` from the corpus.
    * ``--check``     — validate front-matter; exit non-zero on any missing/empty
      required key or malformed ``applies-to`` (writes nothing).
    * ``--print``     — print the freshly-built index JSON to stdout (writes nothing).

    Exit codes: ``0`` on success; ``1`` on a validation failure (``--check``) or a
    malformed-front-matter build error.
    """
    _reconfigure_utf8()
    parser = argparse.ArgumentParser(
        prog="standards_index.py",
        description="Generate / validate the backlogd standards index from ADR front-matter.",
    )
    parser.add_argument("--check", action="store_true",
                        help="validate front-matter only; exit non-zero if any ADR is "
                             "missing a required key (writes nothing)")
    parser.add_argument("--print", dest="print_only", action="store_true",
                        help="print the freshly-built index JSON to stdout (writes nothing)")
    parser.add_argument("--adrs-dir", default=None,
                        help="override the ADR directory (default: docs/standards/adrs)")
    parser.add_argument("--index-path", default=None,
                        help="override the index output path (default: docs/standards/index.json)")
    args = parser.parse_args(argv)

    adrs_dir = Path(args.adrs_dir) if args.adrs_dir else None

    if args.check:
        errors = validate(adrs_dir)
        if errors:
            print("Standards front-matter validation FAILED:", file=sys.stderr)
            for e in errors:
                print(f"  - {e}", file=sys.stderr)
            print(f"\n{len(errors)} problem(s). Fix the front-matter (see "
                  f"docs/standards/adrs/TEMPLATE.md).", file=sys.stderr)
            return 1
        n = len(load_adrs(adrs_dir))
        print(f"OK: {n} ADR(s) carry all required front-matter keys "
              f"({', '.join(REQUIRED_KEYS)}).")
        return 0

    # Build path (default and --print both need a valid corpus).
    try:
        index = build_index(adrs_dir)
    except FrontMatterError as exc:
        print(f"Cannot build index — malformed front-matter: {exc}", file=sys.stderr)
        return 1

    if args.print_only:
        print(render_index(index), end="")
        return 0

    index_path = Path(args.index_path) if args.index_path else None
    written = write_index(adrs_dir, index_path)
    print(f"Wrote {written} — {len(index['standards'])} standard(s) indexed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
