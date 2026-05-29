"""Unit tests for scripts/linear_setup.py — standard library only (unittest).

Run from the repo root:  python scripts/test_linear_setup.py
Or under pytest:         pytest scripts/test_linear_setup.py

The network is never touched: every test drives the **pure planning functions**
(``plan_audit`` and friends) with hand-built workspace-state dicts, or mocks
:func:`linear_setup.graphql` with :mod:`unittest.mock`. The four areas the AC
names — missing/recase/cruft diff, lowercase normalization, GraphQL payload
building, and the idempotent empty-plan-on-canonical case — each have a class.

The idempotency test (``CanonicalWorkspaceIdempotentTest``) is selectable with
``pytest scripts/test_linear_setup.py -k idempotent``.
"""

import io
import json
import pathlib
import sys
import unittest
from contextlib import redirect_stdout
from unittest import mock

# Make ``import linear_setup`` work regardless of how this file is invoked.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import linear_setup  # noqa: E402


# --- Fixtures -------------------------------------------------------------

def _label(name, *, id=None, color=None, description=None, issue_count=0):
    """Build a live-label dict shaped like the audit query's ``nodes`` entries."""
    if id is None:
        id = "lbl_" + linear_setup.normalize_label_name(name).replace(":", "_")
    return {
        "id": id,
        "name": name,
        "color": color,
        "description": description,
        "issues": {"nodes": [{"id": f"iss_{n}"} for n in range(issue_count)]},
    }


def _canonical_labels():
    """A label set that is already fully canonical — drives the idempotent case."""
    return [
        _label("problem", id="lbl_problem"),
        _label("kind:ops", id="lbl_ops"),
        _label("blocked", id="lbl_blocked"),
    ]


def _canonical_states():
    """One workflow state per canonical category."""
    return [
        {"id": f"st_{cat}", "name": cat.title(), "type": cat, "position": i}
        for i, cat in enumerate(linear_setup.CANONICAL_STATE_CATEGORIES)
    ]


# --- Lowercase normalization ----------------------------------------------

class NormalizeLabelNameTest(unittest.TestCase):
    """``normalize_label_name`` collapses case + surrounding whitespace."""

    def test_lowercases_and_trims(self):
        self.assertEqual(linear_setup.normalize_label_name("Problem"), "problem")
        self.assertEqual(linear_setup.normalize_label_name("  PROBLEM "), "problem")
        self.assertEqual(linear_setup.normalize_label_name("Kind:Ops"), "kind:ops")

    def test_already_canonical_is_unchanged(self):
        self.assertEqual(linear_setup.normalize_label_name("problem"), "problem")
        self.assertEqual(linear_setup.normalize_label_name("blocked"), "blocked")


# --- audit: missing / recase / cruft diff ---------------------------------

class AuditDiffTest(unittest.TestCase):
    """The plan diff buckets the AC names: missing / recase / cruft / state_gaps."""

    def test_missing_canonical_labels_are_reported(self):
        # Empty workspace — all three canonical labels are missing, each carrying
        # its default color + description for the create.
        plan = linear_setup.plan_audit([], _canonical_states(), [])
        missing_names = {m["name"] for m in plan["missing"]}
        self.assertEqual(missing_names, {"problem", "kind:ops", "blocked"})
        problem = next(m for m in plan["missing"] if m["name"] == "problem")
        self.assertEqual(problem["color"], linear_setup.CANONICAL_LABELS["problem"]["color"])
        self.assertIn("description", problem)
        self.assertFalse(plan["ok"])

    def test_recase_detects_capital_problem(self):
        # Linear's default ``Problem`` must be flagged for recase to ``problem``,
        # carrying the live id so the rename preserves applications.
        labels = [_label("Problem", id="lbl_cap")]
        plan = linear_setup.plan_audit(labels, _canonical_states(), [])
        self.assertEqual(len(plan["recase"]), 1)
        entry = plan["recase"][0]
        self.assertEqual(entry["id"], "lbl_cap")
        self.assertEqual(entry["from"], "Problem")
        self.assertEqual(entry["to"], "problem")
        # ``Problem`` (normalized to the canonical name) must NOT also appear as
        # missing — it exists, just mis-cased.
        self.assertNotIn("problem", {m["name"] for m in plan["missing"]})

    def test_priority_labels_are_recommended_cruft(self):
        # priority:* duplicates Linear's native Priority field → recommend delete,
        # regardless of how many issues carry them.
        labels = [
            _label("priority:high", id="lbl_ph", issue_count=12),
            _label("priority:low", id="lbl_pl", issue_count=0),
        ]
        plan = linear_setup.plan_audit(labels, _canonical_states(), [])
        cruft_names = {c["name"] for c in plan["cruft"]}
        self.assertEqual(cruft_names, {"priority:high", "priority:low"})
        for entry in plan["cruft"]:
            self.assertIn("Priority", entry["reason"])

    def test_default_labels_are_cruft_only_when_zero_issues(self):
        # Feature/Bug/Improvement: cruft only when zero issues. A Bug with issues
        # goes to ``review`` (no recommendation), not ``cruft``.
        labels = [
            _label("Feature", id="lbl_feat", issue_count=0),
            _label("Bug", id="lbl_bug", issue_count=3),
            _label("Improvement", id="lbl_imp", issue_count=0),
        ]
        plan = linear_setup.plan_audit(labels, _canonical_states(), [])
        cruft_names = {c["name"] for c in plan["cruft"]}
        review_names = {r["name"] for r in plan["review"]}
        self.assertEqual(cruft_names, {"Feature", "Improvement"})
        self.assertEqual(review_names, {"Bug"})

    def test_other_non_canonical_labels_go_to_review_not_cruft(self):
        # An arbitrary team label is never auto-recommended for deletion.
        labels = [_label("area:graph", id="lbl_area", issue_count=5)]
        plan = linear_setup.plan_audit(labels, _canonical_states(), [])
        self.assertEqual([r["name"] for r in plan["review"]], ["area:graph"])
        self.assertEqual(plan["cruft"], [])

    def test_state_gaps_reported_for_missing_categories(self):
        # Only backlog + started present → the other three categories are gaps.
        states = [
            {"id": "s1", "name": "Backlog", "type": "backlog"},
            {"id": "s2", "name": "In Progress", "type": "started"},
        ]
        plan = linear_setup.plan_audit(_canonical_labels(), states, [])
        self.assertEqual(
            set(plan["state_gaps"]), {"unstarted", "completed", "canceled"}
        )

    def test_canonical_label_not_flagged_as_cruft_or_review(self):
        # The canonical labels themselves must never appear in cruft/review.
        plan = linear_setup.plan_audit(_canonical_labels(), _canonical_states(), [])
        self.assertEqual(plan["cruft"], [])
        self.assertEqual(plan["review"], [])


# --- audit idempotency (selectable with -k idempotent) --------------------

class CanonicalWorkspaceIdempotentTest(unittest.TestCase):
    """On an already-canonical workspace, ``audit`` returns an empty plan."""

    def test_audit_on_canonical_workspace_is_empty_idempotent(self):
        plan = linear_setup.plan_audit(
            _canonical_labels(), _canonical_states(), []
        )
        self.assertEqual(plan["missing"], [])
        self.assertEqual(plan["recase"], [])
        self.assertEqual(plan["cruft"], [])
        self.assertEqual(plan["state_gaps"], [])
        # The aggregate "nothing to do" flag the CLI surfaces.
        self.assertTrue(plan["ok"])

    def test_audit_idempotent_even_with_extra_review_labels(self):
        # Extra team labels land in ``review`` but don't break the canonical
        # invariant — ``ok`` stays True because review carries no recommendation.
        labels = _canonical_labels() + [_label("team:design", id="lbl_td", issue_count=2)]
        plan = linear_setup.plan_audit(labels, _canonical_states(), [])
        self.assertTrue(plan["ok"])
        self.assertEqual([r["name"] for r in plan["review"]], ["team:design"])


# --- GraphQL payload building ---------------------------------------------

class EnsureLabelPlanTest(unittest.TestCase):
    """``plan_ensure_label`` — idempotent create / noop + input building."""

    def test_creates_with_canonical_defaults_when_absent(self):
        plan = linear_setup.plan_ensure_label("problem", [])
        self.assertEqual(plan["action"], "create")
        self.assertEqual(plan["input"]["name"], "problem")
        # Falls back to the canonical color/description for a known label.
        self.assertEqual(
            plan["input"]["color"], linear_setup.CANONICAL_LABELS["problem"]["color"]
        )
        self.assertIn("description", plan["input"])

    def test_explicit_color_and_description_win_over_defaults(self):
        plan = linear_setup.plan_ensure_label(
            "problem", [], color="#000000", description="custom"
        )
        self.assertEqual(plan["input"]["color"], "#000000")
        self.assertEqual(plan["input"]["description"], "custom")

    def test_noop_when_label_present_case_insensitively(self):
        plan = linear_setup.plan_ensure_label("problem", [_label("Problem")])
        self.assertEqual(plan["action"], "noop")
        self.assertEqual(plan["existing"]["name"], "Problem")

    def test_unknown_label_has_no_default_attrs(self):
        plan = linear_setup.plan_ensure_label("custom:thing", [])
        self.assertEqual(plan["action"], "create")
        self.assertEqual(plan["input"], {"name": "custom:thing"})


class RecaseLabelPlanTest(unittest.TestCase):
    """``plan_recase_label`` — rename to canonical case, id preserved."""

    def test_update_renames_capital_problem_keeping_id(self):
        plan = linear_setup.plan_recase_label("Problem", [_label("Problem", id="lbl_1")])
        self.assertEqual(plan["action"], "update")
        self.assertEqual(plan["id"], "lbl_1")
        self.assertEqual(plan["input"], {"name": "problem"})
        # The update payload carries ONLY name — never teamId — so the id (and all
        # existing applications) survive.
        self.assertNotIn("teamId", plan["input"])

    def test_noop_when_already_canonical(self):
        plan = linear_setup.plan_recase_label("problem", [_label("problem")])
        self.assertEqual(plan["action"], "noop")
        self.assertEqual(plan["reason"], "already_canonical")

    def test_noop_when_not_found(self):
        plan = linear_setup.plan_recase_label("Problem", [])
        self.assertEqual(plan["action"], "noop")
        self.assertEqual(plan["reason"], "not_found")

    def test_explicit_target_overrides_canonical(self):
        plan = linear_setup.plan_recase_label(
            "Feature", [_label("Feature", id="lbl_f")], to="feature"
        )
        self.assertEqual(plan["action"], "update")
        self.assertEqual(plan["input"], {"name": "feature"})


class DeleteLabelPlanTest(unittest.TestCase):
    """``plan_delete_label`` — the only destructive planner."""

    def test_resolves_id_for_delete(self):
        plan = linear_setup.plan_delete_label("priority:high", [_label("priority:high", id="lbl_p")])
        self.assertEqual(plan["action"], "delete")
        self.assertEqual(plan["id"], "lbl_p")

    def test_noop_when_absent(self):
        plan = linear_setup.plan_delete_label("ghost", [])
        self.assertEqual(plan["action"], "noop")
        self.assertEqual(plan["reason"], "not_found")


class EnsureStatePlanTest(unittest.TestCase):
    """``plan_ensure_state`` — additive only; never touches existing states."""

    def test_creates_state_in_missing_category(self):
        plan = linear_setup.plan_ensure_state(
            "started", "In Progress", [], team_id="team_1"
        )
        self.assertEqual(plan["action"], "create")
        self.assertEqual(
            plan["input"],
            {"name": "In Progress", "type": "started", "color": "#95a2b3", "teamId": "team_1"},
        )

    def test_noop_when_category_already_present(self):
        # Additive only: a started state already exists, so we never create a
        # second one (and never rename the existing one).
        states = [{"id": "s1", "name": "Doing", "type": "started"}]
        plan = linear_setup.plan_ensure_state(
            "started", "In Progress", states, team_id="team_1"
        )
        self.assertEqual(plan["action"], "noop")
        self.assertEqual(plan["existing"]["name"], "Doing")

    def test_rejects_unknown_category(self):
        with self.assertRaises(ValueError):
            linear_setup.plan_ensure_state(
                "in-review", "Review", [], team_id="team_1"
            )


class EnsureTemplatePlanTest(unittest.TestCase):
    """``plan_ensure_template`` — create/update with templateData + type shape."""

    def test_create_builds_full_input_with_templatedata_and_type(self):
        data = {"title": "", "description": "## Acceptance Criteria\n"}
        plan = linear_setup.plan_ensure_template(
            "Problem template", "issue", data, [], team_id="team_1"
        )
        self.assertEqual(plan["action"], "create")
        # The create input must carry the confirmed schema fields: name, type,
        # templateData (JSON value), and the optional teamId.
        self.assertEqual(plan["input"]["name"], "Problem template")
        self.assertEqual(plan["input"]["type"], "issue")
        self.assertEqual(plan["input"]["templateData"], data)
        self.assertEqual(plan["input"]["teamId"], "team_1")

    def test_update_when_name_and_type_match(self):
        existing = [{"id": "tpl_1", "name": "Problem template", "type": "issue"}]
        data = {"title": "updated"}
        plan = linear_setup.plan_ensure_template(
            "Problem template", "issue", data, existing
        )
        self.assertEqual(plan["action"], "update")
        self.assertEqual(plan["id"], "tpl_1")
        self.assertEqual(plan["input"]["templateData"], data)
        # TemplateUpdateInput must not carry ``type`` (it's immutable on update).
        self.assertNotIn("type", plan["input"])

    def test_project_template_type_is_distinct_from_issue(self):
        # Same name, different type → still a create (no match on (name, type)).
        existing = [{"id": "tpl_1", "name": "Standard", "type": "issue"}]
        plan = linear_setup.plan_ensure_template(
            "Standard", "project", {"name": "x"}, existing, team_id="team_1"
        )
        self.assertEqual(plan["action"], "create")
        self.assertEqual(plan["input"]["type"], "project")

    def test_rejects_unknown_template_type(self):
        with self.assertRaises(ValueError):
            linear_setup.plan_ensure_template("X", "epic", {}, [])


# --- Credentials parsing --------------------------------------------------

class CredentialsParsingTest(unittest.TestCase):
    """``_parse_credentials_env`` — KEY=VALUE lines, comments, quotes."""

    def test_parses_key_value_lines(self):
        text = "LINEAR_API_KEY=lin_abc123\nOTHER=value\n"
        parsed = linear_setup._parse_credentials_env(text)
        self.assertEqual(parsed["LINEAR_API_KEY"], "lin_abc123")
        self.assertEqual(parsed["OTHER"], "value")

    def test_skips_comments_and_blanks(self):
        text = "# a comment\n\nLINEAR_API_KEY=lin_x\n\n# trailing\n"
        parsed = linear_setup._parse_credentials_env(text)
        self.assertEqual(parsed, {"LINEAR_API_KEY": "lin_x"})

    def test_strips_surrounding_quotes(self):
        text = 'LINEAR_API_KEY="lin_quoted"\n'
        self.assertEqual(
            linear_setup._parse_credentials_env(text)["LINEAR_API_KEY"], "lin_quoted"
        )

    def test_value_may_contain_equals(self):
        text = "LINEAR_API_KEY=lin_a=b=c\n"
        self.assertEqual(
            linear_setup._parse_credentials_env(text)["LINEAR_API_KEY"], "lin_a=b=c"
        )


# --- Key handling: env first, then file; never via argv or logs -----------

class LoadApiKeyTest(unittest.TestCase):
    """``load_api_key`` — env-first resolution + file fallback."""

    def test_env_var_takes_precedence(self):
        with mock.patch.dict("os.environ", {"LINEAR_API_KEY": "lin_env"}, clear=False):
            self.assertEqual(linear_setup.load_api_key(), "lin_env")

    def test_falls_back_to_credentials_file(self):
        # No env var → read ~/.backlogd/credentials.env (home monkeypatched).
        fake_home = mock.MagicMock()
        fake_path = mock.MagicMock()
        fake_home.joinpath.return_value = fake_path
        fake_path.is_file.return_value = True
        fake_path.read_text.return_value = "LINEAR_API_KEY=lin_file\n"
        env = {k: v for k, v in __import__("os").environ.items() if k != "LINEAR_API_KEY"}
        with mock.patch.dict("os.environ", env, clear=True), \
                mock.patch("pathlib.Path.home", return_value=fake_home):
            self.assertEqual(linear_setup.load_api_key(), "lin_file")

    def test_raises_when_no_key_anywhere_without_leaking(self):
        fake_home = mock.MagicMock()
        fake_path = mock.MagicMock()
        fake_home.joinpath.return_value = fake_path
        fake_path.is_file.return_value = False
        env = {k: v for k, v in __import__("os").environ.items() if k != "LINEAR_API_KEY"}
        with mock.patch.dict("os.environ", env, clear=True), \
                mock.patch("pathlib.Path.home", return_value=fake_home):
            with self.assertRaises(RuntimeError) as ctx:
                linear_setup.load_api_key()
        # The error names where to put the key but contains no key material.
        self.assertIn("LINEAR_API_KEY", str(ctx.exception))


class KeySafetyTest(unittest.TestCase):
    """AC#3 — the key never reaches argv and never appears in any output."""

    def test_argv_is_never_read_for_the_key(self):
        # Static guarantee: no verb defines a --key/--api-key/--token argument,
        # and the source never indexes sys.argv for a key. We assert the parser
        # exposes no such option on any subparser.
        parser = linear_setup.build_parser()
        forbidden = {"--key", "--api-key", "--apikey", "--token", "--secret"}
        # Walk every subparser's option strings.
        subparsers_action = next(
            a for a in parser._actions if isinstance(a, __import__("argparse")._SubParsersAction)
        )
        for sub in subparsers_action.choices.values():
            opt_strings = {opt for act in sub._actions for opt in act.option_strings}
            self.assertEqual(
                opt_strings & forbidden, set(),
                f"a subcommand exposed a key argument: {opt_strings & forbidden}",
            )

    def test_graphql_sets_key_in_authorization_header_raw(self):
        # The key is loaded *inside* graphql and set raw (not Bearer) on the
        # Authorization header — and the function never prints it.
        captured = {}

        class _FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return json.dumps({"data": {"ok": True}}).encode("utf-8")

        def _fake_urlopen(req, timeout=None):
            captured["headers"] = dict(req.header_items())
            captured["body"] = req.data
            return _FakeResp()

        buf = io.StringIO()
        with mock.patch.object(linear_setup, "load_api_key", return_value="lin_secret"), \
                mock.patch("urllib.request.urlopen", _fake_urlopen), \
                redirect_stdout(buf):
            data = linear_setup.graphql("query { x }", {"v": 1})

        self.assertEqual(data, {"ok": True})
        # Authorization header carries the RAW key (no "Bearer " prefix).
        auth = captured["headers"].get("Authorization")
        self.assertEqual(auth, "lin_secret")
        # graphql prints nothing — the key cannot leak to stdout.
        self.assertEqual(buf.getvalue(), "")

    def test_graphql_error_message_excludes_the_key(self):
        # When the server returns GraphQL errors, the raised message is built from
        # server text only — never the request headers / key.
        class _FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return json.dumps(
                    {"errors": [{"message": "Entity not found"}]}
                ).encode("utf-8")

        def _fake_urlopen(req, timeout=None):
            return _FakeResp()

        with mock.patch.object(linear_setup, "load_api_key", return_value="lin_secret"), \
                mock.patch("urllib.request.urlopen", _fake_urlopen):
            with self.assertRaises(linear_setup.GraphQLError) as ctx:
                linear_setup.graphql("query { x }")
        self.assertNotIn("lin_secret", str(ctx.exception))
        self.assertIn("Entity not found", str(ctx.exception))


# --- Verb dispatch over a mocked network ----------------------------------

class VerbDispatchTest(unittest.TestCase):
    """End-to-end verb dispatch with ``graphql`` mocked — JSON to stdout, no net."""

    def _run(self, argv, graphql_returns):
        """Run ``main(argv)`` with ``graphql`` returning queued payloads in order."""
        buf = io.StringIO()
        with mock.patch.object(
            linear_setup, "graphql", side_effect=list(graphql_returns)
        ), redirect_stdout(buf):
            code = linear_setup.main(argv)
        return code, buf.getvalue()

    def test_audit_emits_plan_json(self):
        fetch = {
            "issueLabels": {"nodes": _canonical_labels()},
            "workflowStates": {"nodes": _canonical_states()},
            "team": {"templates": {"nodes": []}},
        }
        code, out = self._run(["audit", "--team-id", "team_1"], [fetch])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["verb"], "audit")
        self.assertTrue(payload["plan"]["ok"])

    def test_ensure_label_noop_does_not_mutate(self):
        # Label already present → only the read query runs; no create mutation.
        fetch = {
            "issueLabels": {"nodes": [_label("problem", id="lbl_p")]},
            "workflowStates": {"nodes": []},
            "team": {"templates": {"nodes": []}},
        }
        code, out = self._run(
            ["ensure-label", "--team-id", "team_1", "--name", "problem"], [fetch]
        )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["action"], "noop")

    def test_recase_label_updates_when_miscased(self):
        fetch = {
            "issueLabels": {"nodes": [_label("Problem", id="lbl_cap")]},
            "workflowStates": {"nodes": []},
            "team": {"templates": {"nodes": []}},
        }
        mutate = {"issueLabelUpdate": {"success": True, "issueLabel": {"id": "lbl_cap", "name": "problem"}}}
        code, out = self._run(
            ["recase-label", "--team-id", "team_1", "--name", "Problem"],
            [fetch, mutate],
        )
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["action"], "updated")
        self.assertEqual(payload["to"], "problem")

    def test_main_returns_nonzero_on_graphql_error(self):
        # A GraphQLError from the fetch must surface as a non-zero exit, not crash.
        with mock.patch.object(
            linear_setup, "graphql", side_effect=linear_setup.GraphQLError("boom")
        ):
            code = linear_setup.main(["audit", "--team-id", "team_1"])
        self.assertEqual(code, 1)


# --- CLI surface (the --help AC) ------------------------------------------

class CliSurfaceTest(unittest.TestCase):
    """The parser lists all six verbs (mirrors the --help AC)."""

    def test_parser_exposes_all_six_verbs(self):
        parser = linear_setup.build_parser()
        subparsers_action = next(
            a for a in parser._actions
            if isinstance(a, __import__("argparse")._SubParsersAction)
        )
        self.assertEqual(
            set(subparsers_action.choices),
            {"audit", "ensure-label", "recase-label", "delete-label",
             "ensure-state", "ensure-template"},
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
