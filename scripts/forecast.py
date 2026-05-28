"""backlogd forecast — rolling-7-day velocity, queue, ETA, and the Linear Project block.

This module is the reference implementation behind step 4 of ``/backlogd:status``
(``commands/status.md``): the orchestrator's MCP-capable session computes a forecast
from Linear and refreshes the team's primary Project description in place with a
``## 📊 Forecast`` section.

The numbers are deliberately simple — no smoothing, no trend, no projection past a
linear extrapolation — because the value of the signal is *visible and current*, not
*precise*. If precision matters, look at the Project itself.

Public surface
--------------
* :func:`compute_forecast` — turn raw counts (``recent_closed``, ``in_flight``,
  ``backlog``, ``stalled``) into a ``Forecast`` dataclass with rendered strings.
* :func:`render_block` — format a ``Forecast`` as the ``## 📊 Forecast`` markdown
  block (without surrounding blank lines).
* :func:`splice_forecast_block` — idempotently splice/append a forecast block into
  an existing project description. Robust to missing/malformed prior blocks and
  preserves all surrounding content byte-for-byte.

All functions are pure — no I/O, no Linear calls, no time-of-day side effects (the
caller passes the timestamp). They run on plain strings/ints so the unit tests
can drive every edge case without a network.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


# --- Block markers --------------------------------------------------------

# The heading line that identifies our block in the Project description. The
# emoji is part of the literal — preserve it byte-for-byte across reads/writes.
BLOCK_HEADING = "## 📊 Forecast"

# A level-2 heading on its own line ends our block. We anchor only on level-2
# (``## ``) — deeper headings (``### `` and below) inside our block stay inside.
_HEADING_PREFIX = "## "

# "Insufficient data" message — surfaced when velocity is zero. The exact wording
# is load-bearing (it's what the AC tests for); render and console output share it.
INSUFFICIENT_DATA_MSG = (
    "insufficient data — close at least one problem this week to get a forecast"
)

# Window for the rolling velocity calculation, in days. Spec-fixed at 7.
WINDOW_DAYS = 7


# --- Result type ----------------------------------------------------------

@dataclass(frozen=True)
class Forecast:
    """A computed forecast — the numbers the block + console row share.

    Both the Linear block and the console standup render off this single object,
    so they cannot drift. ``eta_days`` is ``None`` when velocity is zero (the
    ``insufficient_data`` flag carries that case); otherwise it's a float rounded
    to the nearest half day (0.5 increments).
    """

    recent_closed: int
    in_flight: int
    backlog: int
    stalled: int
    velocity_per_day: float
    eta_days: Optional[float]
    insufficient_data: bool

    @property
    def active_queue(self) -> int:
        """Total problems in ``unstarted`` + ``started`` state categories."""
        return self.in_flight + self.backlog


# --- Core computation -----------------------------------------------------

def _round_to_half(x: float) -> float:
    """Round ``x`` to the nearest 0.5 — the ETA's spec'd resolution.

    Python's built-in :func:`round` uses banker's rounding, which makes 0.25 → 0.0
    and 0.75 → 1.0 — we want half-away-from-zero so 0.25 → 0.5. The simplest fix
    is to scale by 2, round-half-away-from-zero by hand, then scale back.
    """
    scaled = x * 2.0
    floored = int(scaled)
    frac = scaled - floored
    if frac >= 0.5:
        floored += 1 if scaled >= 0 else -1
    elif frac <= -0.5:
        floored -= 1
    return floored / 2.0


def compute_forecast(
    recent_closed: int,
    in_flight: int,
    backlog: int,
    stalled: int,
    *,
    window_days: int = WINDOW_DAYS,
) -> Forecast:
    """Compute a :class:`Forecast` from the raw Linear counts.

    Parameters
    ----------
    recent_closed:
        Count of ``problem``-labelled issues whose state moved to ``completed``
        in the last ``window_days``. Drives the velocity numerator.
    in_flight:
        Count of ``problem``-labelled issues whose state category is ``started``.
    backlog:
        Count of ``problem``-labelled issues whose state category is ``unstarted``.
    stalled:
        Count of active ``problem`` issues currently carrying the ``blocked``
        label (the auto-managed label from NB-342's sibling work). Surfaced as
        the "Stalled" row in the block — does not affect the ETA math.
    window_days:
        Velocity window. Defaults to 7; exposed for tests.

    Returns
    -------
    Forecast
        A populated dataclass — rendering happens in :func:`render_block`.
    """
    velocity = recent_closed / window_days
    active_queue = in_flight + backlog
    if velocity <= 0:
        # Zero velocity — surface "insufficient data" regardless of queue size.
        # We *could* still produce an ETA for an empty queue, but a "0 days, no
        # one is working" reading is more misleading than helpful.
        return Forecast(
            recent_closed=recent_closed,
            in_flight=in_flight,
            backlog=backlog,
            stalled=stalled,
            velocity_per_day=0.0,
            eta_days=None,
            insufficient_data=True,
        )
    eta = _round_to_half(active_queue / velocity)
    return Forecast(
        recent_closed=recent_closed,
        in_flight=in_flight,
        backlog=backlog,
        stalled=stalled,
        velocity_per_day=velocity,
        eta_days=eta,
        insufficient_data=False,
    )


# --- Rendering ------------------------------------------------------------

def _fmt_velocity(v: float) -> str:
    """Render velocity at one decimal place — ``4.1``, ``0.0``."""
    return f"{v:.1f}"


def _fmt_eta(eta: Optional[float], *, insufficient_data: bool) -> str:
    """Render the ETA line value, including the half-day handling.

    Returns a fragment for the "Rough ETA to drain" row's *value half*. The
    caller wraps it in the row's prose; this function owns the shape of the
    number itself (or the insufficient-data message).
    """
    if insufficient_data or eta is None:
        return INSUFFICIENT_DATA_MSG
    # Whole numbers render without the .0; halves keep .5.
    if eta == int(eta):
        n = int(eta)
        return f"~{n} day" if n == 1 else f"~{n} days"
    return f"~{eta} days"


def _fmt_iso_utc(ts: datetime) -> str:
    """Format a datetime as ISO-8601 UTC with a trailing ``Z``.

    The block's footer uses this — second resolution, no microseconds, no
    offset suffix beyond ``Z``. Naive datetimes are treated as UTC.
    """
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    else:
        ts = ts.astimezone(timezone.utc)
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def render_block(fc: Forecast, *, refreshed_at: datetime) -> str:
    """Render a :class:`Forecast` as the ``## 📊 Forecast`` markdown block.

    The return value is the block body — no leading or trailing blank lines.
    Splicing into a description handles the spacing around it.

    The format matches the spec example byte-for-byte (modulo dynamic numbers)
    so the rendered block is stable across re-runs and grep-able.
    """
    velocity_line = (
        f"- **Velocity (7d):** {_fmt_velocity(fc.velocity_per_day)} problems/day"
    )
    queue_line = (
        f"- **Active queue:** {fc.in_flight} in-flight + {fc.backlog} backlog "
        f"= {fc.active_queue}"
    )
    eta_line = (
        f"- **Rough ETA to drain:** {_fmt_eta(fc.eta_days, insufficient_data=fc.insufficient_data)}"
    )
    stalled_word = "problem" if fc.stalled == 1 else "problems"
    stalled_line = f"- **Stalled:** {fc.stalled} {stalled_word} blocked"
    footer = f"_Last refreshed: {_fmt_iso_utc(refreshed_at)}_"
    return (
        f"{BLOCK_HEADING}\n"
        "\n"
        f"{velocity_line}\n"
        f"{queue_line}\n"
        f"{eta_line}\n"
        f"{stalled_line}\n"
        "\n"
        f"{footer}"
    )


def render_console_row(fc: Forecast) -> str:
    """Render the matching console row for ``/backlogd:status``.

    The console standup prints this on a single ``Forecast: …`` line so the
    operator sees the same numbers the Linear block carries. Sharing the source
    object (:class:`Forecast`) is how we guarantee no drift.
    """
    if fc.insufficient_data:
        return (
            f"Forecast: velocity 0.0/day, queue {fc.active_queue} "
            f"({fc.in_flight} in-flight + {fc.backlog} backlog), "
            f"{fc.stalled} stalled — {INSUFFICIENT_DATA_MSG}"
        )
    return (
        f"Forecast: velocity {_fmt_velocity(fc.velocity_per_day)}/day, "
        f"queue {fc.active_queue} ({fc.in_flight} in-flight + {fc.backlog} backlog), "
        f"ETA {_fmt_eta(fc.eta_days, insufficient_data=False).lstrip('~')}, "
        f"{fc.stalled} stalled"
    )


# --- Block splicing -------------------------------------------------------

def _find_block_span(lines: list[str]) -> Optional[tuple[int, int]]:
    """Locate an existing ``## 📊 Forecast`` block.

    Returns ``(start, end)`` — *inclusive* line indices — or ``None`` when no
    block is present. ``end`` is the index of the block's **last** line, *not*
    the next-heading line: callers slice ``[start : end + 1]``.

    A block runs from its ``## 📊 Forecast`` line up to (but not including) the
    next level-2 heading, or end-of-file when there isn't one. Trailing blank
    lines immediately before the next heading / EOF are *included* in the
    span — we strip them when re-rendering so the splice doesn't accumulate
    blank lines across re-runs.
    """
    start: Optional[int] = None
    for i, line in enumerate(lines):
        if line.rstrip("\r") == BLOCK_HEADING:
            start = i
            break
    if start is None:
        return None
    # Walk forward to the next level-2 heading.
    end_exclusive = len(lines)
    for j in range(start + 1, len(lines)):
        # Match ``## `` at start-of-line — but the heading line itself counts
        # only once (we already matched it). Anything starting with ``## `` here
        # is a sibling heading, so the block ends just before it.
        if lines[j].startswith(_HEADING_PREFIX):
            end_exclusive = j
            break
    # Trim trailing blank lines from the captured block (we'll re-emit our own
    # spacing) — but only the ones inside the block, never beyond it.
    end = end_exclusive - 1
    while end > start and lines[end].strip() == "":
        end -= 1
    return (start, end)


def splice_forecast_block(description: str, block: str) -> str:
    """Splice ``block`` into ``description`` idempotently.

    Three cases the regression tests pin down:

    1. **No existing block.** Append the block to the description, separated by
       a single blank line. An empty description becomes the block alone.
    2. **Existing well-formed block.** Replace from the ``## 📊 Forecast`` line
       through the line before the next level-2 heading (or EOF), preserving the
       lines above the block and below the next heading byte-for-byte.
    3. **Malformed prior block.** A *malformed* block here means the heading is
       present but the body is gibberish or missing — the same span-detection
       rules apply: we replace whatever sits between the heading and the next
       level-2 heading. The freshly rendered block always supersedes the old
       contents in place.

    ``description`` and ``block`` may use either ``\\n`` or ``\\r\\n`` line
    endings — the function preserves the input's endings on the *surrounding*
    content but always emits ``\\n`` inside the freshly rendered block (the
    ``render_block`` output is LF-only by construction).
    """
    if not description.strip():
        # Empty starting description — the block is the whole new description.
        # Strip any surrounding whitespace from the block; we want a clean file.
        return block.strip() + "\n"

    # Split preserving line endings so we can rebuild without rewriting them.
    # ``splitlines(keepends=True)`` keeps ``\r\n`` / ``\n`` on each line so the
    # round-trip is faithful for content we *don't* touch.
    lines_with_eol = description.splitlines(keepends=True)
    lines_no_eol = [_strip_eol(line) for line in lines_with_eol]

    span = _find_block_span(lines_no_eol)
    if span is None:
        # No prior block — append. Ensure exactly one blank line of separation
        # without rewriting the line endings of the existing prose. We keep the
        # original description verbatim, then add a blank line + the block.
        # If the description already ends in a newline (it usually does), we
        # add only one more newline before the block; otherwise we add two.
        if description.endswith("\n"):
            sep = "\n"
        else:
            sep = "\n\n"
        return f"{description}{sep}{block.strip()}\n"

    start, end = span
    # Reconstruct: prefix (above block) + freshly rendered block + suffix (below
    # block). The suffix starts at the line *after* the block's last line.
    prefix_lines = lines_with_eol[:start]
    suffix_lines = lines_with_eol[end + 1:]

    # The block is rendered with LF newlines and no trailing newline — give it
    # one so the suffix sits on its own line(s). Insert a blank line between the
    # block and the suffix when the suffix is non-empty, so the next heading is
    # visually separated.
    prefix = "".join(prefix_lines)
    suffix = "".join(suffix_lines)

    rendered = block.rstrip("\n") + "\n"
    if suffix.strip():
        # Ensure exactly one blank line between block and suffix.
        suffix_lead = suffix.lstrip("\r\n")
        return f"{prefix}{rendered}\n{suffix_lead}"
    # Trailing block (no content below) — keep a single newline at end-of-file.
    return f"{prefix}{rendered}"


def _strip_eol(line: str) -> str:
    """Strip a single trailing CRLF or LF from a line (keep nothing else)."""
    if line.endswith("\r\n"):
        return line[:-2]
    if line.endswith("\n"):
        return line[:-1]
    return line


__all__ = [
    "BLOCK_HEADING",
    "INSUFFICIENT_DATA_MSG",
    "WINDOW_DAYS",
    "Forecast",
    "compute_forecast",
    "render_block",
    "render_console_row",
    "splice_forecast_block",
]
