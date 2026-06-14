"""Presence-anchor tests for NB-358 — the developer declares hidden assumptions
to Linear, pauses briefly, and re-reads once before any code change.

NB-358 adds the second half of the "common ground" idea NB-352 began. NB-352's
Problem-Read declares the *interpretation* (one line, the head of the
``**[backlogd developer]**`` progress comment); NB-358 makes the developer also
declare the *defaults that interpretation rests on* — the un-spelled-out
decisions the product owner did not write down — as a short bounded list in that
same comment, **before any code change**. The developer then takes a brief
bounded pause and performs **exactly one** explicit re-read of its own issue
(``list_comments`` / ``get_issue``) and branches:

- a product-owner comment PRESENT at that re-read that CONTRADICTS a stated
  assumption routes the developer to ``STATUS: NEEDS_CONTEXT`` (stop, write no
  code);
- SILENCE (no contradicting comment) means proceed normally.

Per the PO's option-B design the re-read is a SINGLE check, not a wait loop:
there is no harness clock and the developer never stalls, so an unwatched
(headless / scripted) run is never blocked. The change is a single edit to
``agents/developer.md`` ``<Investigation_Protocol>`` at the Problem-Read step,
reusing the already-permitted optional own-issue ``get_issue`` / ``list_comments``
re-read (no new Linear capability) and the shipped four-value STATUS enum
(NB-348) without redefining either, and it removes the stale
``(future) NB-358 … Not implemented yet`` placeholder comment.

The acceptance criteria pinned here (the durable, presence-anchored facts):

- AC1 the ``<Investigation_Protocol>`` instructs the developer to declare its
  hidden assumptions in the progress comment BEFORE any code change.
- AC2 the instruction lands at the Problem-Read step and the stale
  ``Not implemented yet`` placeholder is removed.
- AC4 after the list and a brief pause, EXACTLY ONE explicit re-read via
  ``list_comments`` / ``get_issue`` happens BEFORE writing code.
- AC5 the re-poll is framed as a SINGLE CHECK, NOT A WAIT LOOP (no harness clock,
  no indefinite block).
- AC7 the ``NEEDS_CONTEXT`` branch is wired to a CONTRADICTING comment at the
  re-read (not to silence).
- AC8/AC9 (partly) the change is confined to ``agents/developer.md`` and the list
  is content of the EXISTING single comment (no new comment / table / status
  emoji / em-dash), in the Linear-comment style.

Anchoring discipline (matching ``test_worklog_tail_schema.py`` and the wider
suite): every assertion targets a DURABLE token — "hidden assumption", the
re-read tool names, the "single check, not a wait loop" phrase, "NEEDS_CONTEXT"
co-occurring with "contradict", "silence … proceed" — never a full sentence or
exact wording (the NB-389 reword-fragility trap). These tokens are the facts the
unit had to land: at HEAD before the change, "hidden assumption(s)", the
re-read-before-code wiring, and the "single check, not a wait loop" framing
appear ZERO times in ``developer.md`` (the only NB-358 mention was the
``Not implemented yet`` placeholder), so each test fails before the change and
passes after it — not a ``True == True`` tautology.

Deliberately NOT covered here (REVIEW / MANUAL scope — a markdown grep cannot
judge these; reported as out-of-test-scope, not silently skipped):

- whether the bound (three or four / cap five) reads as "small and bounded" and
  coheres with the Problem-Read head — the ``[review]`` AC, an editorial call;
- whether the prose reads as graceful-degradation rather than a human-approval
  gate or polling loop — a negative timing property the ``[review]`` AC owns
  (no command can prove "never stalls");
- whether a developer at runtime ACTUALLY surfaces the gap, a watching PO flips
  the run to ``NEEDS_CONTEXT``, and an unwatched run proceeds — the ``[manual]``
  live-behaviour AC.

Why stdlib only: the repo's test convention — CI runs
``python -m unittest discover -s scripts -p 'test_*.py'`` on a bare Python with
no ``pip install``. Files are read as UTF-8.

Run from the repo root:  python scripts/test_hidden_assumptions.py
"""

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEVELOPER = REPO_ROOT / "agents" / "developer.md"


def _read(path):
    """File text (UTF-8), or empty string if absent so the file-exists test owns
    the missing-file failure rather than every test erroring."""
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _investigation_protocol(text):
    """The body of the ``<Investigation_Protocol>`` section, or '' if absent."""
    m = re.search(r"<Investigation_Protocol>(.*?)</Investigation_Protocol>", text, re.S)
    return m.group(1) if m else ""


class DeveloperFileExistsTest(unittest.TestCase):
    def test_developer_file_exists(self):
        self.assertTrue(DEVELOPER.is_file(), f"{DEVELOPER} must exist")


class DeclaresHiddenAssumptionsBeforeCodeTest(unittest.TestCase):
    """AC1 — the developer declares its hidden assumptions in the progress comment
    BEFORE any code change.

    Pre-change anchor: "hidden assumption" appears ZERO times in ``developer.md`` @
    HEAD, so this fails before NB-358."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(DEVELOPER)
        cls.lower = cls.text.lower()

    def test_mentions_hidden_assumptions(self):
        self.assertIn(
            "hidden assumption", self.lower,
            "agents/developer.md must instruct the developer to declare its "
            "'hidden assumptions' (AC1)",
        )

    def test_assumptions_are_declared_before_any_code_change(self):
        """The 'hidden assumptions' instruction sits in a 'before any code change'
        window, so the list is declared up front, not at report-back."""
        idx = self.lower.find("hidden assumption")
        self.assertNotEqual(idx, -1, "no 'hidden assumption' anchor (AC1)")
        window = self.lower[max(0, idx - 300): idx + 600]
        self.assertIn(
            "before any code change", window,
            "the hidden-assumptions instruction must say it happens BEFORE any "
            "code change (AC1)",
        )

    def test_assumptions_go_into_the_developer_comment(self):
        """The list is content of the existing ``**[backlogd developer]**`` comment,
        not a new surface — the badge token appears in the same window. Whitespace-
        tolerant so a line wrap inside the badge (``[backlogd\\n developer]``) does not
        break the anchor."""
        idx = self.lower.find("hidden assumption")
        window = self.text[max(0, idx - 400): idx + 600]
        self.assertRegex(
            window,
            r"\[backlogd\s+developer\]",
            "the hidden-assumptions list must be content of the existing "
            "**[backlogd developer]** progress comment (AC1/AC9)",
        )


class PlaceholderRemovedTest(unittest.TestCase):
    """AC2 — the stale ``(future) NB-358 … Not implemented yet`` placeholder is gone.

    Pre-change anchor: "Not implemented yet" appears in the placeholder @ HEAD, so
    this fails before NB-358."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(DEVELOPER)

    def test_not_implemented_yet_placeholder_is_removed(self):
        self.assertNotIn(
            "Not implemented yet", self.text,
            "the stale '(future) NB-358 … Not implemented yet' placeholder must be "
            "removed (AC2)",
        )

    def test_no_future_nb358_placeholder_comment_remains(self):
        """The specific HTML-comment placeholder shape must not survive."""
        self.assertIsNone(
            re.search(r"\(future\)\s*NB-358", self.text),
            "no '(future) NB-358' placeholder comment may remain (AC2)",
        )


class LandsAtProblemReadStepTest(unittest.TestCase):
    """AC2/AC8 — the instruction lands at the Problem-Read step (inside
    ``<Investigation_Protocol>``), the successor to the NB-352 head."""

    @classmethod
    def setUpClass(cls):
        cls.protocol = _investigation_protocol(_read(DEVELOPER))
        cls.protocol_lower = cls.protocol.lower()

    def test_protocol_section_present(self):
        self.assertTrue(
            self.protocol, "agents/developer.md must have an <Investigation_Protocol>")

    def test_assumptions_instruction_is_in_the_protocol(self):
        self.assertIn(
            "hidden assumption", self.protocol_lower,
            "the hidden-assumptions instruction must live inside "
            "<Investigation_Protocol> (AC2/AC8)",
        )

    def test_follows_the_problem_read_head(self):
        """The assumptions instruction appears AFTER the Problem-Read head line, so
        it reads as the head's successor (the defaults the interpretation rests on)."""
        pr_idx = self.protocol_lower.find("reading this as:")
        ha_idx = self.protocol_lower.find("hidden assumption")
        self.assertNotEqual(pr_idx, -1, "no Problem-Read head to anchor on (AC8)")
        self.assertNotEqual(ha_idx, -1, "no hidden-assumptions instruction (AC8)")
        self.assertLess(
            pr_idx, ha_idx,
            "the hidden-assumptions list must follow the Problem-Read head (AC8)",
        )


class ExactlyOneReReadBeforeCodeTest(unittest.TestCase):
    """AC4 — after the list and a brief pause, EXACTLY ONE explicit re-read via
    ``list_comments`` / ``get_issue`` happens BEFORE writing code.

    Pre-change anchor: the re-read-before-code wiring appears ZERO times @ HEAD."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(DEVELOPER)
        cls.lower = cls.text.lower()

    def test_names_a_re_read_tool(self):
        self.assertTrue(
            "list_comments" in self.text or "get_issue" in self.text,
            "the re-read must name list_comments / get_issue (AC4)",
        )

    def test_names_the_re_read_action(self):
        self.assertRegex(
            self.lower,
            r"(re-?read|re-?poll|re-?check|read again|check.{0,30}comment)",
            "the step must name the re-read / re-poll action (AC4)",
        )

    def test_re_read_happens_before_writing_code(self):
        """A 'before … code' clause sits near the re-read, so the single check
        precedes any code change."""
        m = re.search(r"(re-?read|re-?poll|re-?check)", self.lower)
        self.assertIsNotNone(m, "no re-read anchor (AC4)")
        window = self.lower[max(0, m.start() - 400): m.start() + 400]
        self.assertIn(
            "before", window,
            "the re-read must be specified as happening BEFORE writing code (AC4)",
        )

    def test_exactly_one_re_read_count_is_named(self):
        """AC4 says the prompt requires **exactly one** explicit re-read — the COUNT
        is the contract, not merely that some re-read occurs. Anchor the count word
        ('exactly one' / 'a single' / 'one ... re-read') in a window with a re-read
        verb so it pins the NB-358 re-poll specifically.

        Load-bearing / non-tautological: at HEAD 'exactly one' occurs (frontmatter,
        'exactly one comment', the STATUS 'exactly one of four values') but NEVER in a
        window with a re-read / re-poll verb, so this fails before the change and
        passes after it. (The looser whole-file count check is
        ``SingleCheckNotAWaitLoopTest.test_framed_as_one_check``, which is
        coincidentally green at HEAD; this windowed form is the one that bites.)"""
        anchored = False
        for m in re.finditer(r"(exactly one|a single|one re-?read)", self.lower):
            window = self.lower[max(0, m.start() - 200): m.start() + 300]
            if re.search(r"re-?read|re-?poll", window):
                anchored = True
                break
        self.assertTrue(
            anchored,
            "the prompt must name the re-read COUNT as exactly one / a single re-read, "
            "co-occurring with the re-read verb (AC4)",
        )

    def test_combined_self_contained_check(self):
        """Mirrors the AC4 ``python -c`` gate exactly so the contract and the
        regression test agree."""
        ok = (
            ("list_comments" in self.text or "get_issue" in self.text)
            and re.search(
                r"(re-?read|re-?poll|re-?check|read again|check.{0,30}comment)",
                self.lower)
            and "before" in self.lower
        )
        self.assertTrue(ok, "AC4 self-contained check must pass")


class SingleCheckNotAWaitLoopTest(unittest.TestCase):
    """AC5/AC6 — the re-poll is a SINGLE CHECK, NOT A WAIT LOOP: no harness clock,
    no indefinite block, and silence means proceed (never stalls).

    Pre-change anchor: "single check" / "not a wait loop" appear ZERO times @ HEAD."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(DEVELOPER)
        cls.lower = cls.text.lower()

    def test_framed_as_one_check(self):
        self.assertRegex(
            self.lower,
            r"(exactly one|a single|one re-?read|once|single check|not a (wait )?loop)",
            "the re-poll must be framed as a single check / exactly one re-read (AC5)",
        )

    def test_explicitly_not_a_loop(self):
        """The 'not a (wait) loop' framing is present, ruling out repeated polling.
        Whitespace-tolerant (``\\s+``) so a line wrap inside the phrase does not break
        the anchor — the durable fact is the words, not their exact spacing."""
        self.assertRegex(
            self.lower,
            r"not\s+a\s+(wait\s+)?loop",
            "the re-poll must be stated as NOT a wait loop (AC5)",
        )

    def test_no_harness_clock(self):
        """The prose disclaims a harness clock / timer, so the pause is prompt-level."""
        self.assertRegex(
            self.lower,
            r"no harness clock",
            "the step must state there is NO harness clock (AC5/AC6)",
        )

    def test_silence_means_proceed(self):
        """Silence at the one re-read means proceed — graceful degradation, not a
        human-approval gate, so an unwatched run is never stalled."""
        self.assertIn(
            "silence", self.lower,
            "the step must address SILENCE at the re-read (AC6)",
        )
        # 'silence' and a 'proceed' verb co-occur in one window.
        idx = self.lower.find("silence means proceed")
        if idx == -1:
            idx = self.lower.find("silence")
        window = self.lower[max(0, idx - 200): idx + 300]
        self.assertIn(
            "proceed", window,
            "silence at the re-read must route to PROCEED (AC6)",
        )

    def test_never_stalls_unwatched(self):
        """The prose makes explicit that an unwatched / headless / scripted run is
        never stalled (no watching PO required to continue)."""
        self.assertRegex(
            self.lower,
            r"never (stall|block)|not (stall|block)|never stalled",
            "the step must state the run is NEVER stalled on silence (AC6)",
        )


class NeedsContextOnContradictionTest(unittest.TestCase):
    """AC7 — a PO comment PRESENT at the re-read that CONTRADICTS a stated assumption
    routes to ``STATUS: NEEDS_CONTEXT`` (stop, write no code), and only then — not on
    silence.

    Pre-change anchor: "contradict" near a NEEDS_CONTEXT branch appears ZERO times @
    HEAD in this step (the only HEAD NEEDS_CONTEXT mentions are the STATUS enum)."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(DEVELOPER)
        cls.lower = cls.text.lower()

    def test_status_and_contradict_both_present(self):
        """Mirrors the AC7 ``python -c`` gate exactly (whole-file co-presence), so the
        contract gate and this test agree. NOTE: this loose whole-file form is
        coincidentally satisfiable at HEAD (the unrelated ``<Final_Checklist>`` 'No
        internal contradiction' line + the STATUS enum); the LOAD-BEARING,
        non-tautological anchor is ``test_contradiction_is_wired_to_needs_context``
        below, which windows the tokens together and fails at HEAD."""
        ok = "NEEDS_CONTEXT" in self.text and "contradict" in self.lower
        self.assertTrue(ok, "AC7 self-contained check must pass")

    def test_contradiction_is_wired_to_needs_context(self):
        """The CONTRADICTION-at-the-re-read branch routes to ``STATUS: NEEDS_CONTEXT``.

        Anchored on the contradiction that sits IN the new step: the ``contradict``
        token must co-occur in ONE window with both ``NEEDS_CONTEXT`` and an
        assumption/re-read token. This deliberately excludes the unrelated
        ``<Final_Checklist>`` 'No internal contradiction' line (which exists @HEAD and
        is nowhere near an assumption/re-read token), so the anchor pins the NB-358
        wiring rather than a pre-existing coincidence."""
        # Find the 'contradict' occurrence that belongs to the assumptions step: the
        # one whose window also mentions an assumption / re-read token.
        anchored = False
        for m in re.finditer(r"contradict", self.lower):
            window_text = self.text[max(0, m.start() - 400): m.start() + 400]
            window_low = window_text.lower()
            if "NEEDS_CONTEXT" in window_text and (
                "assumption" in window_low
                or re.search(r"re-?read|re-?poll|re-?check", window_low)
            ):
                anchored = True
                break
        self.assertTrue(
            anchored,
            "a contradicting PO comment at the re-read of a stated ASSUMPTION must "
            "route to STATUS: NEEDS_CONTEXT — the 'contradict' / 'NEEDS_CONTEXT' / "
            "'assumption-or-re-read' tokens must co-occur in one window (AC7)",
        )


class ConfinedAndReusesStatusEnumTest(unittest.TestCase):
    """AC8 — reuses the shipped four-value STATUS enum (NB-348) without redefining it,
    and reuses the already-permitted optional own-issue re-read (no new capability)."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(DEVELOPER)
        cls.lower = cls.text.lower()

    def test_status_enum_not_redefined(self):
        """The four STATUS values still appear exactly once each as the enum line in
        <Output_Format>; the new step references NEEDS_CONTEXT but does not add a new
        STATUS line."""
        # The canonical enum line lists all four values together.
        self.assertIn(
            "STATUS: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT", self.text,
            "the shipped four-value STATUS enum line must remain intact (AC8)",
        )

    def test_reuses_permitted_own_issue_re_read(self):
        """The step frames the re-read as the optional own-issue re-read the
        constraints already permit (no new Linear capability granted)."""
        idx = self.lower.find("hidden assumption")
        window = self.lower[max(0, idx - 100): idx + 1600]
        self.assertTrue(
            "permit" in window or "no new" in window or "already" in window,
            "the re-read must be framed as the already-permitted own-issue read, "
            "granting no new Linear capability (AC8)",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
