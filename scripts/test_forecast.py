"""Unit tests for scripts/forecast.py — standard library only (unittest).

Run from the repo root:  python scripts/test_forecast.py

The four edge cases the AC pins down (positive velocity, zero velocity, empty
queue, both zero) sit in ``ForecastEdgeCasesTest``. The splice-logic robustness
checks (no prior block, malformed prior block, surrounding content preserved)
sit in ``SpliceLogicTest``. The console/block "no drift" guarantee is covered by
``ConsoleAndBlockShareNumbersTest``.
"""

import pathlib
import sys
import unittest
from datetime import datetime, timezone

# Make ``import forecast`` work regardless of how this file is invoked.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import forecast  # noqa: E402

FIXED_TS = datetime(2026, 5, 28, 7, 30, 0, tzinfo=timezone.utc)


class ForecastEdgeCasesTest(unittest.TestCase):
    """The four edge cases the AC names explicitly."""

    def test_positive_velocity_typical_case(self):
        # The spec example: 4 in-flight + 8 backlog = 12 queue, velocity 4.1/day.
        # 4.1/day comes from 29 closures in 7 days (29/7 ≈ 4.143). ETA ≈ 2.9 days
        # → rounds to 3.0 at half-day resolution.
        fc = forecast.compute_forecast(
            recent_closed=29, in_flight=4, backlog=8, stalled=1
        )
        self.assertFalse(fc.insufficient_data)
        self.assertAlmostEqual(fc.velocity_per_day, 29 / 7)
        self.assertEqual(fc.active_queue, 12)
        self.assertEqual(fc.eta_days, 3.0)
        block = forecast.render_block(fc, refreshed_at=FIXED_TS)
        self.assertIn("**Velocity (7d):** 4.1 problems/day", block)
        self.assertIn("**Active queue:** 4 in-flight + 8 backlog = 12", block)
        self.assertIn("**Rough ETA to drain:** ~3 days", block)
        self.assertIn("**Stalled:** 1 problem blocked", block)
        self.assertIn("_Last refreshed: 2026-05-28T07:30:00Z_", block)

    def test_zero_velocity_surfaces_insufficient_data(self):
        # Nothing closed this week, queue has work — must surface the exact
        # spec string, not "0 days" or "infinity".
        fc = forecast.compute_forecast(
            recent_closed=0, in_flight=2, backlog=5, stalled=0
        )
        self.assertTrue(fc.insufficient_data)
        self.assertIsNone(fc.eta_days)
        self.assertEqual(fc.velocity_per_day, 0.0)
        block = forecast.render_block(fc, refreshed_at=FIXED_TS)
        self.assertIn(forecast.INSUFFICIENT_DATA_MSG, block)
        # The literal spec wording is load-bearing.
        self.assertIn(
            "insufficient data — close at least one problem this week to get a forecast",
            block,
        )
        # Velocity still renders as 0.0/day (it really is zero).
        self.assertIn("**Velocity (7d):** 0.0 problems/day", block)

    def test_empty_queue_with_positive_velocity_eta_zero(self):
        # Queue is empty but the team has been closing things — ETA is 0 days,
        # the spec's stated behaviour for this combination.
        fc = forecast.compute_forecast(
            recent_closed=7, in_flight=0, backlog=0, stalled=0
        )
        self.assertFalse(fc.insufficient_data)
        self.assertEqual(fc.active_queue, 0)
        self.assertEqual(fc.eta_days, 0.0)
        block = forecast.render_block(fc, refreshed_at=FIXED_TS)
        self.assertIn("**Active queue:** 0 in-flight + 0 backlog = 0", block)
        # Zero days renders without ".0" — "~0 days", not "~0.0 days".
        self.assertIn("**Rough ETA to drain:** ~0 days", block)
        self.assertNotIn(forecast.INSUFFICIENT_DATA_MSG, block)

    def test_both_zero_falls_back_to_insufficient_data(self):
        # No closures, no queue — there is no useful signal either way, so we
        # surface the same insufficient-data message rather than "0 days".
        fc = forecast.compute_forecast(
            recent_closed=0, in_flight=0, backlog=0, stalled=0
        )
        self.assertTrue(fc.insufficient_data)
        self.assertIsNone(fc.eta_days)
        block = forecast.render_block(fc, refreshed_at=FIXED_TS)
        self.assertIn(forecast.INSUFFICIENT_DATA_MSG, block)
        # And rendering must not crash on stalled=0 / queue=0 — both render
        # cleanly.
        self.assertIn("**Stalled:** 0 problems blocked", block)
        self.assertIn("**Active queue:** 0 in-flight + 0 backlog = 0", block)


class HalfDayRoundingTest(unittest.TestCase):
    """ETA rounds to the nearest half day — pin the boundaries."""

    def test_rounds_quarter_up_to_half(self):
        # 1 / 4 = 0.25, rounds to 0.5 (half-away-from-zero, not banker's).
        fc = forecast.compute_forecast(
            recent_closed=28, in_flight=1, backlog=0, stalled=0
        )
        # velocity = 4/day, queue = 1 → ETA = 0.25 → 0.5
        self.assertEqual(fc.eta_days, 0.5)

    def test_rounds_three_quarter_up_to_one(self):
        # 3 / 4 = 0.75 → 1.0
        fc = forecast.compute_forecast(
            recent_closed=28, in_flight=3, backlog=0, stalled=0
        )
        self.assertEqual(fc.eta_days, 1.0)

    def test_renders_half_day_with_point_five(self):
        fc = forecast.compute_forecast(
            recent_closed=28, in_flight=1, backlog=0, stalled=0
        )
        block = forecast.render_block(fc, refreshed_at=FIXED_TS)
        self.assertIn("~0.5 days", block)


class SpliceLogicTest(unittest.TestCase):
    """Block-replacement: missing/malformed prior block, content preservation."""

    def _block(self, *, recent_closed=29, in_flight=4, backlog=8, stalled=1):
        fc = forecast.compute_forecast(
            recent_closed=recent_closed, in_flight=in_flight,
            backlog=backlog, stalled=stalled,
        )
        return forecast.render_block(fc, refreshed_at=FIXED_TS)

    def test_empty_description_yields_block_only(self):
        out = forecast.splice_forecast_block("", self._block())
        self.assertTrue(out.startswith(forecast.BLOCK_HEADING))
        self.assertIn("**Velocity (7d):** 4.1 problems/day", out)

    def test_no_prior_block_appends_with_blank_line(self):
        existing = "# About\n\nThe Product Management Tool project.\n"
        out = forecast.splice_forecast_block(existing, self._block())
        # The original prose must survive byte-for-byte at the top.
        self.assertTrue(out.startswith("# About\n\nThe Product Management Tool project.\n"))
        # And the block is appended with exactly one blank line between.
        self.assertIn(
            "The Product Management Tool project.\n\n## 📊 Forecast",
            out,
        )

    def test_existing_well_formed_block_replaced_in_place(self):
        existing = (
            "# About\n"
            "\n"
            "The project.\n"
            "\n"
            "## 📊 Forecast\n"
            "\n"
            "- **Velocity (7d):** 1.0 problems/day\n"
            "- **Active queue:** 1 in-flight + 1 backlog = 2\n"
            "- **Rough ETA to drain:** ~2 days\n"
            "- **Stalled:** 0 problems blocked\n"
            "\n"
            "_Last refreshed: 2026-05-20T00:00:00Z_\n"
            "\n"
            "## Footnotes\n"
            "\n"
            "Trailing prose that must survive.\n"
        )
        out = forecast.splice_forecast_block(existing, self._block())
        # Old velocity number must be gone.
        self.assertNotIn("1.0 problems/day", out)
        # New velocity number must be present.
        self.assertIn("4.1 problems/day", out)
        # Content above must survive verbatim.
        self.assertIn("# About\n\nThe project.\n", out)
        # Content below must survive verbatim.
        self.assertIn("## Footnotes\n\nTrailing prose that must survive.\n", out)
        # Exactly one block remains — no duplicates.
        self.assertEqual(out.count("## 📊 Forecast"), 1)

    def test_running_twice_is_idempotent(self):
        # Running splice twice with the same block must yield the same content
        # — the second run is a re-rendering, not a duplication.
        existing = "# Project\n\nProse.\n"
        once = forecast.splice_forecast_block(existing, self._block())
        twice = forecast.splice_forecast_block(once, self._block())
        self.assertEqual(once, twice)
        self.assertEqual(twice.count("## 📊 Forecast"), 1)

    def test_running_twice_updates_timestamp_in_place(self):
        # When the *block* changes (e.g. a new timestamp on a re-run), the
        # description must update in place — never accumulate or duplicate.
        existing = "# Project\n\nProse.\n"
        ts1 = datetime(2026, 5, 28, 7, 30, 0, tzinfo=timezone.utc)
        ts2 = datetime(2026, 5, 28, 8, 0, 0, tzinfo=timezone.utc)
        fc = forecast.compute_forecast(
            recent_closed=29, in_flight=4, backlog=8, stalled=1
        )
        first_pass = forecast.splice_forecast_block(
            existing, forecast.render_block(fc, refreshed_at=ts1)
        )
        second_pass = forecast.splice_forecast_block(
            first_pass, forecast.render_block(fc, refreshed_at=ts2)
        )
        self.assertNotIn("2026-05-28T07:30:00Z", second_pass)
        self.assertIn("2026-05-28T08:00:00Z", second_pass)
        self.assertEqual(second_pass.count("## 📊 Forecast"), 1)
        # The non-block prose survives both passes.
        self.assertIn("# Project\n\nProse.\n", second_pass)

    def test_malformed_prior_block_is_replaced_cleanly(self):
        # A malformed block: heading is present, body is garbage. The next
        # level-2 heading is the terminator, so anything between them goes.
        existing = (
            "# About\n"
            "\n"
            "## 📊 Forecast\n"
            "\n"
            "(this block was hand-edited and lost its shape)\n"
            "random words\n"
            "no footer\n"
            "\n"
            "## Trailing section\n"
            "\n"
            "Must survive.\n"
        )
        out = forecast.splice_forecast_block(existing, self._block())
        self.assertNotIn("hand-edited", out)
        self.assertNotIn("random words", out)
        self.assertIn("## Trailing section\n\nMust survive.\n", out)
        self.assertEqual(out.count("## 📊 Forecast"), 1)
        self.assertIn("**Velocity (7d):** 4.1 problems/day", out)

    def test_block_at_end_of_description_no_trailing_heading(self):
        # The block runs to EOF — no level-2 heading after it. Replacement must
        # still work and not clobber content above.
        existing = (
            "# About\n"
            "\n"
            "Intro prose.\n"
            "\n"
            "## 📊 Forecast\n"
            "\n"
            "- **Velocity (7d):** 0.5 problems/day\n"
            "- **Active queue:** 0 in-flight + 1 backlog = 1\n"
            "- **Rough ETA to drain:** ~2 days\n"
            "- **Stalled:** 0 problems blocked\n"
            "\n"
            "_Last refreshed: 2026-05-20T00:00:00Z_\n"
        )
        out = forecast.splice_forecast_block(existing, self._block())
        self.assertIn("# About\n\nIntro prose.\n", out)
        self.assertIn("4.1 problems/day", out)
        self.assertNotIn("0.5 problems/day", out)
        self.assertEqual(out.count("## 📊 Forecast"), 1)

    def test_h3_heading_inside_block_does_not_terminate(self):
        # A sub-heading (### inside the block) must NOT terminate the span — we
        # only anchor on level-2. (Defensive: today's render uses no sub-headings,
        # but a hand-edit might add one.)
        existing = (
            "# Project\n"
            "\n"
            "## 📊 Forecast\n"
            "\n"
            "- **Velocity (7d):** 1.0 problems/day\n"
            "\n"
            "### Hand-added detail\n"
            "\n"
            "Some extra context the PO typed in.\n"
            "\n"
            "## Other section\n"
            "\n"
            "Survives.\n"
        )
        out = forecast.splice_forecast_block(existing, self._block())
        # The hand-added sub-section was *inside* the block, so it goes too —
        # this matches the spec ("replace the block in place"). We just want
        # the replacement to *stop* at the next level-2 heading, not at the
        # next heading of any level.
        self.assertNotIn("Hand-added detail", out)
        self.assertNotIn("Some extra context", out)
        self.assertIn("## Other section\n\nSurvives.\n", out)

    def test_crlf_line_endings_preserved_outside_block(self):
        # Descriptions edited on Windows may carry CRLF endings — the splice
        # should not silently rewrite them across the whole file.
        existing = "# About\r\n\r\nProse.\r\n"
        out = forecast.splice_forecast_block(existing, self._block())
        # The prefix prose keeps its CRLF endings.
        self.assertTrue(out.startswith("# About\r\n\r\nProse.\r\n"))
        # The freshly rendered block is LF.
        self.assertIn("## 📊 Forecast\n", out)


class ConsoleAndBlockShareNumbersTest(unittest.TestCase):
    """The console row and the Linear block render off the same Forecast."""

    def test_console_row_carries_same_numbers_as_block(self):
        fc = forecast.compute_forecast(
            recent_closed=14, in_flight=2, backlog=3, stalled=1
        )
        block = forecast.render_block(fc, refreshed_at=FIXED_TS)
        row = forecast.render_console_row(fc)
        # Velocity 2.0/day appears in both surfaces.
        self.assertIn("2.0 problems/day", block)
        self.assertIn("2.0/day", row)
        # Queue numbers appear in both.
        self.assertIn("2 in-flight + 3 backlog", block)
        self.assertIn("2 in-flight + 3 backlog", row)
        # ETA 2.5 days appears in both (14/7 = 2/day → 5/2 = 2.5).
        self.assertEqual(fc.eta_days, 2.5)
        self.assertIn("2.5", block)
        self.assertIn("2.5", row)

    def test_console_row_under_zero_velocity_includes_insufficient_msg(self):
        fc = forecast.compute_forecast(
            recent_closed=0, in_flight=1, backlog=1, stalled=0
        )
        row = forecast.render_console_row(fc)
        self.assertIn(forecast.INSUFFICIENT_DATA_MSG, row)
        # Queue counts still appear.
        self.assertIn("queue 2", row)


if __name__ == "__main__":
    unittest.main(verbosity=2)
