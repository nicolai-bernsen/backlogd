"""backlogd typed-AC kind extraction — the reference implementation the reviewer mirrors.

This module is the canonical *normalize-then-match* for the typed-AC grammar in
``skills/ac/SKILL.md`` (the "Parsing rule" bullet). backlogd has no executable AC
parser at run time — the "parser" is the regex in that skill, applied by the reviewer
subagent (an LLM). This file is what that prose points at: the reviewer mirrors the
behaviour here, exactly as ``/backlogd:status`` mirrors :mod:`forecast`.

Why it exists
-------------
The grammar lets an AC bullet open with a kind tag — ``[test]`` / ``[manual]`` /
``[review]`` — right after the ``- [ ] `` checkbox. The documented matcher is the
regex ``^\\[(test|manual|review)\\] `` (case-sensitive, single trailing space). But
**Linear escapes a bare leading ``[`` when it stores a description**, so an authored
``- [ ] [test] …`` is stored and returned as ``- [ ] \\[test\\] …``; the backtick
workaround ``- [ ] `[test]` …`` round-trips verbatim. Either way the raw regex misses
and the item silently degrades to ``review`` — the feature is inert on any
Linear-stored problem. The fix is a small normalization pass that runs **before** the
regex, mapping all three storage forms of a tag back to the bare ``[kind] `` form:

1. ``[test] …``     — the canonical/bare form authors write.
2. ``\\[test\\] …`` — what Linear actually stores from the bare form (the bug).
3. ```[test]` …``  — the backtick workaround.

Normalization is deliberately *narrow*: it only touches the **leading tag region**, so
backslashes or code spans elsewhere in the body are left untouched. A non-kind token
(``[wip] …``), a tag with no trailing space (``[test]foo``), and an untagged bullet all
fall through to ``review`` with the **original text preserved** byte-for-byte as body —
the additive, backwards-compatible contract the skill pins as non-negotiable.

Public surface
--------------
* :func:`extract_kind` — over one AC-item string (the part after ``- [ ] ``) return
  ``(kind, body)`` where ``kind`` ∈ ``{"test", "manual", "review"}`` and ``body`` is
  the remainder after the ``[kind] `` prefix on a match, or the original text unchanged
  on no match.

Stdlib only — no third-party deps — matching the repo's other ``scripts/*.py``.
"""

from __future__ import annotations

import re

# The three valid kinds, and the default for anything untagged or non-kind.
KINDS = ("test", "manual", "review")
DEFAULT_KIND = "review"

# The canonical matcher — unchanged from skills/ac/SKILL.md. Case-sensitive, exactly
# one trailing space. Normalization happens BEFORE this runs; this regex itself is
# never relaxed.
_KIND_RE = re.compile(r"^\[(test|manual|review)\] ")

# A leading inline code span wrapping the tag region: a backtick run, then the tag
# text (which must itself start with `[`), then a matching backtick run. We only
# unwrap when the span sits at the very start of the item and encloses a bracketed
# token — so ``[test]` foo`` -> ``[test] foo`` while an incidental code span later
# in the body is left alone.
_LEADING_CODE_SPAN_RE = re.compile(r"^(`+)(\[.*?\])\1")


def _strip_leading_code_span(text: str) -> str:
    """Unwrap a leading inline code span around the tag, if present.

    ```[test]` rest`` -> ``[test] rest``. Only the leading span is touched; the rest
    of the string (including any other backticks) is preserved verbatim.
    """
    m = _LEADING_CODE_SPAN_RE.match(text)
    if not m:
        return text
    return m.group(2) + text[m.end():]


def _unescape_leading_brackets(text: str) -> str:
    """Markdown-unescape a backslash-escaped leading bracket tag.

    Linear stores a bare leading ``[test]`` as ``\\[test\\]``. Undo exactly that — a
    ``\\[`` at position 0 and the first following ``\\]`` — without globally stripping
    backslashes from the whole body. If the string does not open with ``\\[`` it is
    returned unchanged.
    """
    if not text.startswith("\\["):
        return text
    # Drop the escaping backslash before the opening bracket, then the one before the
    # first closing bracket. We only rewrite this single leading tag region.
    rest = "[" + text[2:]
    close = rest.find("\\]")
    if close == -1:
        return rest
    return rest[:close] + "]" + rest[close + 2:]


def _normalize_leading_tag(text: str) -> str:
    """Map a tag in any of Linear's storage forms back to the bare ``[kind] `` form.

    Runs the code-span unwrap first (the backtick workaround), then the backslash
    unescape (Linear's default storage). Order matters: a code-spanned tag is stored
    without backslashes, so unwrapping first exposes a clean ``[tag]`` for the regex;
    a bare/escaped tag has no leading code span, so the first pass is a no-op.
    """
    return _unescape_leading_brackets(_strip_leading_code_span(text))


def extract_kind(item_text: str) -> tuple[str, str]:
    """Return ``(kind, body)`` for one AC item's text.

    ``item_text`` is the part of the bullet *after* the ``- [ ] ``/``- [x] `` checkbox.

    ``kind`` is one of ``"test"`` / ``"manual"`` / ``"review"``. Normalization of
    Linear's storage forms (unwrap a leading code span, unescape a leading ``\\[…\\]``)
    runs **before** the canonical ``^\\[(test|manual|review)\\] `` match:

    * On a match → ``kind`` is the tag and ``body`` is the remainder after the
      ``"[kind] "`` prefix (taken from the *normalized* text, so the escaping/code-span
      noise is gone from the returned body).
    * On no match → ``kind = "review"`` and ``body`` is the **original** ``item_text``
      unchanged (full preservation): untagged bullets, non-kind tokens like
      ``[wip]``/``\\[wip\\]``, and a tag with no trailing space (``[test]foo``) all land
      here.
    """
    normalized = _normalize_leading_tag(item_text)
    m = _KIND_RE.match(normalized)
    if m:
        return m.group(1), normalized[m.end():]
    return DEFAULT_KIND, item_text


if __name__ == "__main__":  # pragma: no cover - manual smoke aid
    import sys

    for line in sys.stdin:
        line = line.rstrip("\n")
        kind, body = extract_kind(line)
        print(f"{kind}\t{body}")
