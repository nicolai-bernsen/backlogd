"""backlogd release Shipped-scan — compute which problems shipped in a tag range.

Why this exists
---------------
``/backlogd:release`` §6.5 records *which problems shipped in vX.Y.Z* so Linear (which
cannot see git) carries the same per-issue / Initiative / Project audit trail. Computing
that set used to live as prose in ``commands/release.md`` and it under-detected in two
ways that bit real releases (NB-425):

* It walked ``git log --merges`` only. But the merge commits on the release branch are
  ``Merge pull request #N from nicolai-bernsen/main`` / ``… /release/vX.Y.Z`` — they carry
  **no Linear identity at all**. The commits that *do* carry issue identity are the
  squash-merges onto the integration branch (``feat(#413): …``, ``fix(#418): …``), which is
  exactly what ``--merges`` skips. The "scan the full payload" fix was re-applied by hand
  every release while the script text still said ``--merges``.
* It matched a bare ``NB-N`` pattern. But backlogd's commit convention is conventional-commit
  scope ``feat(#413)`` / ``fix(#418)`` / ``docs(#395)`` — a **bare** ``#N``, no ``NB-`` prefix.
  That pattern matched none of them; at v0.20.0 it dropped NB-413 entirely.

It also over-detected: it swept incidental body mentions of already-shipped issues and
would have counted the trailing GitHub PR number ``(#129)`` as if it were an issue.

This module makes the scan **correct by construction** and lives as a tested pure module
(mirroring :mod:`standards_index` / :mod:`ac_parse`) so the logic cannot silently drift
from the prose again. ``commands/release.md`` *invokes* this module rather than restating
its logic.

What counts as included vs advisory
------------------------------------
A commit record is ``(subject, body, head_branch)``. An issue id is **included** (the
commit *is* this issue's work) when any of these holds:

1. **Conventional-commit scope** — the subject opens ``type(#N):`` (``feat`` / ``fix`` /
   ``docs`` / ``chore`` / …), a bare ``#N`` with no ``NB-`` prefix. ``#N`` here is a Linear
   id, not a GitHub PR.
2. **Bare subject id** — an ``NB-N`` anywhere in the subject (other than the trailing
   ``(#N)`` PR number a squash-merge appends). Only the unambiguous ``NB-N`` form counts
   here; a bare mid-subject ``#N`` is *not* swept as an id, because outside a scope or a
   magic word it is ambiguous and is almost always a GitHub PR number
   (``Merge pull request #130 …``).
3. **Magic-word directive** — ``closes`` / ``fixes`` / ``resolves`` (et al.) immediately
   before an ``NB-N`` or ``#N``, in the subject **or** the body. The magic word
   disambiguates a bare ``#N`` as an issue, so ``#N`` *does* count here. An explicit
   "this commit resolves that issue" statement counts even from the body.
4. **Head-branch segment** — an ``nb-N`` segment in the head-branch name
   (``nicolaibernsen/nb-354-…``), case-insensitive.

An id is **advisory** (an incidental reference, reported separately, *not* included) when an
``NB-N`` appears **only** in the commit body and not via any inclusion rule above — e.g. a
body sentence that mentions a prior, already-shipped issue (``converges with … NB-340``). A
bare ``#N`` in a body is not swept (it is overwhelmingly a PR reference), so it never
becomes a false advisory id either.

The trailing GitHub PR number a squash-merge appends to the subject (``… (#129)``) is
**neither** included nor advisory: it is a PR number, not an issue. It is recognised and
dropped so it can never pollute the audit trail in either direction.

Public surface
--------------
* :func:`scan` — over an iterable of :class:`Commit` records, return a :class:`ScanResult`
  with the ``included`` and ``advisory`` id sets (each a sorted list of ints).
* :func:`parse_log` — parse the delimited ``git log`` stream the CLI reads into
  :class:`Commit` records (the inverse of the format ``release.md`` invokes).
* CLI: ``git log --format=… | python scripts/release_scan.py`` prints the included and
  advisory id lines.

Stdlib only — no third-party deps — matching the repo's other ``scripts/*.py``.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from typing import Iterable

__all__ = [
    "Commit",
    "ScanResult",
    "CONVENTIONAL_TYPES",
    "MAGIC_WORDS",
    "RECORD_SEP",
    "FIELD_SEP",
    "scope_ids",
    "trailing_pr_number",
    "magic_word_ids",
    "branch_ids",
    "bare_subject_ids",
    "body_ids",
    "scan",
    "parse_log",
    "render",
]

# Conventional-commit types whose ``type(#N):`` scope names a Linear issue. The set is
# permissive on purpose: any lowercase word followed by ``(#N):`` at the very start of the
# subject is treated as a scoped conventional commit. Listed here for documentation; the
# scope regex below is what actually matches.
CONVENTIONAL_TYPES = (
    "feat", "fix", "docs", "chore", "refactor", "test", "perf", "build", "ci", "style",
)

# Magic words that, immediately before an id, declare the commit resolves that issue.
# GitHub's closes/fixes/resolves family, plus the past/gerund forms it also honours.
MAGIC_WORDS = (
    "close", "closes", "closed",
    "fix", "fixes", "fixed",
    "resolve", "resolves", "resolved",
)

# Delimiters for the CLI's ``git log --format`` stream. Chosen to never collide with commit
# text: an ASCII Unit Separator between fields and a Record Separator between commits.
FIELD_SEP = "\x1f"
RECORD_SEP = "\x1e"

# --- id regexes ------------------------------------------------------------
# An id token is either ``NB-<n>`` (case-insensitive) or a bare ``#<n>``. We capture the
# numeric part. ``\b`` / explicit boundaries keep ``#1234`` from matching inside a longer
# token.
_NB_OR_HASH = r"(?:NB-|#)(\d+)"

# A conventional-commit scope at the very start of the subject: ``type(#N):`` or
# ``type(#N)!:`` (breaking-change bang). The scope must be a bare ``#N`` — that is the
# backlogd convention. Case-insensitive on the type word.
_SCOPE_RE = re.compile(r"^[a-z][a-z0-9-]*\(#(\d+)\)!?:", re.IGNORECASE)

# The trailing ``(#N)`` a squash-merge appends to the subject — anchored to end-of-string
# (allowing trailing whitespace). This is a GitHub PR number, never an issue id.
_TRAILING_PR_RE = re.compile(r"\(#(\d+)\)\s*$")

# A magic-word directive: a closes/fixes/resolves word, optional whitespace/colon, then an
# id. Case-insensitive. Used on subject and body alike.
_MAGIC_RE = re.compile(
    r"\b(?:" + "|".join(MAGIC_WORDS) + r")\b\s*:?\s*" + _NB_OR_HASH,
    re.IGNORECASE,
)

# An ``nb-<n>`` segment in a head-branch name (``nicolaibernsen/nb-354-slug``),
# case-insensitive. The number is bounded by a non-digit (or string end) so ``nb-354`` does
# not also swallow a following digit run.
_BRANCH_RE = re.compile(r"nb-(\d+)(?:\D|$)", re.IGNORECASE)

# An **unambiguous** Linear id: the ``NB-<n>`` form only. A bare ``#N`` is deliberately NOT
# matched here — outside a conventional-commit scope (``type(#N):``) or a magic-word
# directive (``closes #N``), a bare ``#N`` is ambiguous and is almost always a GitHub PR
# number (``Merge pull request #130 …``, ``Supersedes … #128``), not an issue. So the bare
# sweep tracks only ``NB-N``; ``#N`` is admitted *only* when its context disambiguates it
# (see :func:`scope_ids` / :func:`magic_word_ids`).
_NB_ID_RE = re.compile(r"NB-(\d+)", re.IGNORECASE)


@dataclass(frozen=True)
class Commit:
    """One parsed commit record fed to :func:`scan`.

    ``subject`` is the first commit line; ``body`` is everything after it (may be empty);
    ``head_branch`` is the PR's head-branch name when known (the squash-merge convention
    ``nicolaibernsen/nb-<n>-<slug>``), else an empty string.
    """

    subject: str = ""
    body: str = ""
    head_branch: str = ""


@dataclass
class ScanResult:
    """The outcome of a scan: the included and advisory id sets.

    Both are stored as sets of ints while scanning and exposed sorted for stable output.
    ``advisory`` excludes anything already in ``included`` (an id justified by any inclusion
    rule is included, full stop — it is never also reported as a near-miss).
    """

    included: set = field(default_factory=set)
    advisory: set = field(default_factory=set)

    @property
    def included_sorted(self) -> list:
        return sorted(self.included)

    @property
    def advisory_sorted(self) -> list:
        # An id can be picked up as both an inclusion (e.g. via the subject scope) and a
        # body mention; inclusion always wins, so subtract it here.
        return sorted(self.advisory - self.included)


# --- per-field extractors (pure, individually testable) --------------------

def trailing_pr_number(subject: str):
    """Return the trailing ``(#N)`` PR number as an int, or ``None`` if absent.

    A squash-merge appends ``(#129)`` to the subject; that is a GitHub PR number, never a
    Linear issue id, so it is stripped before any subject id sweep and never enters either
    set.
    """
    m = _TRAILING_PR_RE.search(subject)
    return int(m.group(1)) if m else None


def _subject_without_trailing_pr(subject: str) -> str:
    """The subject with a single trailing ``(#N)`` PR number removed (if present)."""
    return _TRAILING_PR_RE.sub("", subject).rstrip()


def scope_ids(subject: str) -> set:
    """Return the conventional-commit scope id ``{N}`` from ``type(#N):``, or ``set()``."""
    m = _SCOPE_RE.match(subject.strip())
    return {int(m.group(1))} if m else set()


def magic_word_ids(text: str) -> set:
    """Return all ids introduced by a closes/fixes/resolves magic word in ``text``."""
    return {int(m.group(1)) for m in _MAGIC_RE.finditer(text)}


def branch_ids(head_branch: str) -> set:
    """Return all ``nb-N`` ids embedded in a head-branch name (case-insensitive)."""
    return {int(m.group(1)) for m in _BRANCH_RE.finditer(head_branch or "")}


def bare_subject_ids(subject: str) -> set:
    """Return bare **``NB-N``** ids in the subject (the trailing PR number is stripped first).

    This catches a plain ``NB-360 tidy the roster`` subject and any other ``NB-N`` in the
    subject line. It deliberately ignores bare ``#N``: a ``#N`` is admitted only with
    disambiguating context (a ``type(#N):`` scope or a ``closes #N`` directive), so a
    GitHub merge subject like ``Merge pull request #130 …`` contributes nothing here.
    """
    trimmed = _subject_without_trailing_pr(subject)
    return {int(m.group(1)) for m in _NB_ID_RE.finditer(trimmed)}


def body_ids(body: str) -> set:
    """Return every **``NB-N``** id mentioned anywhere in the commit body.

    ``NB-N`` only, for the same reason as :func:`bare_subject_ids`: an undecorated ``#N`` in
    a body is overwhelmingly a GitHub PR reference (``Supersedes … #128``, ``converges with
    PR #124``), not a Linear issue — admitting it would invent false advisory ids. A body
    ``#N`` still counts when introduced by a magic word (handled in :func:`scan` via
    :func:`magic_word_ids`).
    """
    return {int(m.group(1)) for m in _NB_ID_RE.finditer(body or "")}


# --- the scan --------------------------------------------------------------

def scan(commits: Iterable[Commit]) -> ScanResult:
    """Classify every id across all ``commits`` into included vs advisory.

    For each commit:

    * **Included** ids = the union of the subject scope, bare subject ids, magic-word ids
      (subject **and** body), and head-branch ids.
    * **Advisory** ids = body-only mentions that no inclusion rule justified.

    The trailing ``(#N)`` PR number is stripped from the subject first, so it can never be
    counted as either. Inclusion wins globally: an id included by *any* commit is removed
    from the advisory set (see :attr:`ScanResult.advisory_sorted`).
    """
    result = ScanResult()
    for c in commits:
        subject = c.subject or ""
        body = c.body or ""

        # Structural inclusion signals.
        included = set()
        included |= scope_ids(subject)
        included |= bare_subject_ids(subject)
        included |= magic_word_ids(subject)
        included |= magic_word_ids(body)
        included |= branch_ids(c.head_branch)

        # Body mentions are advisory unless an inclusion rule (above) already claimed them.
        body_only = body_ids(body) - included

        result.included |= included
        result.advisory |= body_only

    return result


# --- CLI: parse a delimited ``git log`` stream -----------------------------

def parse_log(stream: str) -> list:
    """Parse the delimited ``git log`` stream into :class:`Commit` records.

    The CLI expects commits separated by :data:`RECORD_SEP` and, within a record, the
    fields ``subject``, ``body``, ``head_branch`` separated by :data:`FIELD_SEP`. The
    ``git log --format`` git emits has no head-branch (git does not know it), so that field
    is typically empty and the branch signal is contributed out-of-band; the field is kept
    so a caller that *does* know the branch (e.g. from ``gh pr view``) can supply it.

    Records with an empty subject (e.g. a trailing separator) are skipped.
    """
    commits = []
    for raw in stream.split(RECORD_SEP):
        raw = raw.strip("\n")
        if not raw.strip():
            continue
        parts = raw.split(FIELD_SEP)
        subject = parts[0] if len(parts) > 0 else ""
        body = parts[1] if len(parts) > 1 else ""
        head_branch = parts[2] if len(parts) > 2 else ""
        if not subject.strip():
            continue
        commits.append(Commit(subject=subject.strip(), body=body, head_branch=head_branch.strip()))
    return commits


def render(result: ScanResult) -> str:
    """Render the scan result to the two-line CLI form the release flow reads.

    ``included: NB-413, NB-418, NB-420`` then ``advisory: NB-315, NB-340, NB-398`` (each
    ``none`` when empty). Stable, sorted, greppable.
    """
    def _fmt(ids):
        return ", ".join(f"NB-{i}" for i in ids) if ids else "none"

    return (
        f"included: {_fmt(result.included_sorted)}\n"
        f"advisory: {_fmt(result.advisory_sorted)}\n"
    )


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
    """CLI entry point: read a delimited ``git log`` stream from stdin, print the sets.

    Usage (the form ``commands/release.md`` invokes)::

        git -C "$WT" log <prev-tag>..vX.Y.Z \\
            --format="%s${FIELD}%b${RECORD}" | python scripts/release_scan.py

    Prints two lines (``included:`` / ``advisory:``) and exits 0. ``--help`` documents the
    delimiter bytes.
    """
    _reconfigure_utf8()
    parser = argparse.ArgumentParser(
        prog="release_scan.py",
        description=(
            "Read a delimited `git log` stream on stdin and print the included + advisory "
            "Linear-issue sets for a release range. Records are separated by the ASCII "
            "Record Separator (0x1e); fields (subject, body, head-branch) by the Unit "
            "Separator (0x1f)."
        ),
    )
    parser.parse_args(argv)
    stream = sys.stdin.read()
    result = scan(parse_log(stream))
    print(render(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
