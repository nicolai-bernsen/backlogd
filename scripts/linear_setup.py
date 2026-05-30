"""backlogd Linear config engine — stdlib-only GraphQL, key-safe, idempotent.

This module is the reference implementation behind ``/backlogd:init`` (sub-issue B
shells out to these verbs; the docs in sub-issue C describe them). It brings a
Linear workspace into the canonical shape backlogd's scrum loop expects — the
``problem`` / ``kind:ops`` / ``blocked`` labels, the workflow-state categories the
forecast math reads, and the issue/project templates — without ever being
destructive unless the caller explicitly asks (``delete-label``).

Design (mirrors ``scripts/forecast.py``)
----------------------------------------
The file is split into **pure planning functions** that take already-fetched state
dicts and return a plan/payload (no I/O, no Linear calls, no key handling), and a
**thin network layer** (:func:`graphql`) built on :mod:`urllib.request`. Every verb
fetches what it needs, hands the raw dicts to a pure function, then acts. The split
is what lets the unit tests drive every diff and payload edge case without a
network — they import this module and call the pure functions directly.

Key handling (load-bearing — AC#3)
----------------------------------
The API key is read from the ``LINEAR_API_KEY`` env var, else parsed from
``~/.backlogd/credentials.env`` (``KEY=VALUE`` lines; home resolved via
:meth:`pathlib.Path.home`). It is injected into the HTTP ``Authorization`` header
**inside** :func:`graphql` — never read from ``sys.argv``, never printed, never put
in an exception message. :func:`load_api_key` is the single chokepoint and its
result never leaves the network layer.

Verbs (argparse subcommands; each idempotent; structured JSON to stdout)
------------------------------------------------------------------------
* ``audit``          — read-only; return a plan diff (missing / recase / cruft /
  state_gaps) against the canonical config.
* ``ensure-label``   — create a label if absent (idempotent).
* ``recase-label``   — rename a label to canonical case via ``issueLabelUpdate``
  (preserves the id, so existing applications are kept).
* ``delete-label``   — ``issueLabelDelete`` a named label (the only destructive verb).
* ``ensure-state``   — additive only: create a workflow state in a missing
  category; never rename / reorder / delete an existing state.
* ``ensure-template``— create or update an issue/project/document template. The supplied
  ``templateData`` is Linear's *draft-entity* shape (the entity a template pre-fills), not
  the MCP create-args — a wrong/partial shape is accepted by the ``JSON!`` scalar but does
  **not render** in the UI (NB-392). Applied labels are carried **by name** and resolved to
  a ``labelIds`` array against the live team labels at seed time (no hardcoded id).

GraphQL field/mutation shapes below were confirmed against Linear's live schema
(``packages/sdk/src/schema.graphql``): ``issueLabelCreate``/``issueLabelUpdate`` →
``IssueLabelPayload``; ``issueLabelDelete`` → ``DeletePayload`` (there is no
``issueLabelArchive`` mutation); ``workflowStateCreate`` → ``WorkflowStatePayload``;
``templateCreate``/``templateUpdate`` → ``TemplatePayload`` with ``templateData:
JSON!`` + ``type: String!``.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
from typing import Any, Optional


# --- Constants ------------------------------------------------------------

LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"

# Where the key lives when it isn't already in the environment. Resolved against
# ``Path.home()`` at call time so tests can monkeypatch the home directory.
CREDENTIALS_RELPATH = (".backlogd", "credentials.env")

# Env var name we read the key from first. (We never read the *value* into argv.)
API_KEY_ENV = "LINEAR_API_KEY"

# Canonical labels backlogd seeds (lowercase). ``agent:*`` are runtime-created by
# the scrum loop and deliberately NOT seeded here. Each entry carries the default
# colour/description used when ``ensure-label`` creates it fresh.
CANONICAL_LABELS: dict[str, dict[str, str]] = {
    "problem": {
        "color": "#5e6ad2",
        "description": "A problem for the backlogd scrum team to solve.",
    },
    "kind:ops": {
        "color": "#bec2c8",
        "description": "An ops-only unit — no worktree, no PR; gh/repo-ops only.",
    },
    "blocked": {
        "color": "#eb5757",
        "description": "Auto-managed: this problem is blocked by an open dependency.",
    },
}

# The canonical name a known mis-cased label should be renamed to. Keys are
# compared case-insensitively against live label names; the value is the target.
# (e.g. Linear's default ``Problem`` → our lowercase ``problem``.)
CANONICAL_RECASE: dict[str, str] = {
    "problem": "problem",
}

# Workflow-state categories the forecast/queue math depends on. ``audit`` flags a
# ``state_gap`` for any of these with no live state; ``ensure-state`` can fill one.
CANONICAL_STATE_CATEGORIES: tuple[str, ...] = (
    "backlog",
    "unstarted",
    "started",
    "completed",
    "canceled",
)

# Cruft policy (conservative — see module docstring / spec). ``audit`` *recommends*
# deleting only labels that duplicate a native Linear field — the ``priority:*``
# family (Linear has a native Priority field) — and the default labels below, and
# only the defaults when they carry zero issues. Everything else non-canonical
# goes in ``review`` with no recommendation.
PRIORITY_LABEL_PREFIX = "priority:"
DEFAULT_DELETABLE_LABELS: frozenset[str] = frozenset({"Feature", "Bug", "Improvement"})

# Valid template entity types (``TemplateCreateInput.type``). Used to validate the
# ``ensure-template`` argument before we build a payload.
TEMPLATE_TYPES: tuple[str, ...] = ("issue", "project", "document")


# --- Canonical templates (ADR-003 — the single source of truth) -----------
#
# ADR-003 (Accepted) fixes the *content* of backlogd's three canonical templates;
# this module is the one place those bodies live, so ``/backlogd:init`` (``init.md``
# §4) drives these constants instead of improvising the ``templateData`` inline.
# The bodies below are ADR-003's designed bodies verbatim
# (``docs/standards/adrs/ADR-003-canonical-linear-workspace-configuration.md`` §3,
# "Templates"); the test suite asserts each body's load-bearing content against the
# ADR. Mirrors the ``CANONICAL_LABELS`` pattern above.
#
# **Project-label gap (ADR-003, deliberate non-build).** ADR-003 ships **no project
# label** — nothing in the loop reads one — and the engine has **no project-label
# write verb** (writes go through ``issueLabelCreate``/``issueLabelUpdate`` only;
# Linear project labels are a separate GraphQL type). That is a deliberate "ship
# nothing" decision, not an oversight: a future project label would require adding a
# new write verb *first*. So there is intentionally no ``CANONICAL_PROJECT_LABELS``
# constant here and ``ensure-template`` is the only template surface — see ADR-003 §2
# and "Consequences", and the six-verb ``CliSurfaceTest`` that guards against a 7th.

# Issue template ``Problem`` — body verbatim from ADR-003 §3 (Issue template).
CANONICAL_ISSUE_TEMPLATE_BODY = """## Problem

<!-- One paragraph: what outcome the product owner wants, and why. State the
problem, not a solution. -->

## Acceptance Criteria

- [ ] [review] <criterion — a verifiable "done" statement>
- [ ] [manual] <a check only a human can confirm, if any>"""

# Project template ``backlogd problem`` — the one-line pointer description ADR-003 §3
# specifies (the milestones are encoded separately, in order, below).
CANONICAL_PROJECT_TEMPLATE_DESCRIPTION = (
    "backlogd problem project — phases as milestones; see the Spec document for the "
    "shaped spec + Acceptance Criteria."
)

# The three project milestones, in order (ADR-003 §3 — Project template table).
CANONICAL_PROJECT_MILESTONES: tuple[str, ...] = ("Investigate", "Implement", "Verify")

# Document template ``Spec`` — body verbatim from ADR-003 §3 (Document template).
CANONICAL_DOCUMENT_TEMPLATE_BODY = """## Problem

<!-- The shaped problem statement (intent). For a promoted Project this replaces
the issue description's spec. -->

## Approach

<!-- How the work is decomposed — units, phases (milestones), dependencies. -->

## Acceptance Criteria

- [ ] [review] <criterion>"""

# The canonical templates ``/backlogd:init`` seeds, keyed by template name. Each entry
# carries everything a single ``ensure-template`` call needs — ``type`` (one of
# ``TEMPLATE_TYPES``), the human ``description`` shown in Linear's template picker, and
# the designed ``templateData`` payload.
#
# **``templateData`` is Linear's draft-entity shape, not the MCP create-args.** Linear's
# ``templateData: JSON!`` is the *draft entity* the template pre-fills, and the API accepts
# any JSON — so a wrong/partial shape is "created" but **does not render** in the Linear UI.
# These shapes were introspected from hand-made templates that DO render (NB-392 live
# re-seed; the earlier NB-371 issue/project shape was rejected by the UI):
#   * issue    — ``{title, description, priority, labels}``. ``title`` (empty — the PO names
#                the problem) and ``priority`` (0 — no preset; ADR-003 §3) are **required for
#                the draft to render**. ``description`` is markdown — Linear auto-converts it
#                to ``descriptionData`` on create (proven live). The ``problem`` label is
#                carried **by name** in ``labels`` and resolved to a ``labelIds`` array
#                against the live team labels **at seed time** by
#                :func:`resolve_template_label_ids` (no hardcoded per-workspace id) — see
#                ``LABEL_NAMES_KEY`` below.
#   * project  — the working project draft shape: ``title`` (empty), ``priority`` (0),
#                ``description`` (the one-line pointer) **and** a minimal ``descriptionData``
#                Prosemirror doc (projects do **not** auto-convert ``description``), the
#                ordered ``projectMilestones`` (name+sortOrder), plus the empty collection
#                arrays the working draft carries — ``labelIds``, ``initiativeIds``,
#                ``memberIds``, ``teamIds``, ``initialIssues``. ``statusId`` is omitted
#                (workspace-specific — a create defaults it).
#   * document — ``{title, content, icon}``; this shape already renders (DO NOT change) —
#                the proven ``save_document`` shape (``documents-and-updates.md`` → Spec
#                role), icon ``:memo:``.

# The marker key under which a template carries applied labels **by name** in
# ``CANONICAL_TEMPLATES``. ``ensure-template`` resolves these names to ``labelIds`` against
# the live team labels at seed time (:func:`resolve_template_label_ids`) and drops this key
# before sending — so no per-workspace label id is ever hardcoded in the engine.
LABEL_NAMES_KEY = "labels"
# The Linear draft-entity key the resolved ids are written under.
LABEL_IDS_KEY = "labelIds"


def _minimal_prosemirror_doc(text: str) -> dict[str, Any]:
    """A minimal Prosemirror ``descriptionData`` doc carrying a single paragraph.

    Linear's rich-text fields (``descriptionData``) are Prosemirror JSON. The issue
    draft auto-converts a markdown ``description`` string, but the **project** draft does
    not — so the project template carries this explicit minimal doc for its one-line
    pointer. The shape (``doc`` → ``paragraph`` → ``text``) matches the working template
    introspected live.
    """
    return {
        "type": "doc",
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": text}]},
        ],
    }


CANONICAL_TEMPLATES: dict[str, dict[str, Any]] = {
    "Problem": {
        "type": "issue",
        "description": "A backlogd problem — states the outcome the PO wants, with typed Acceptance Criteria.",
        "templateData": {
            # Empty title (the PO names the problem) + no priority preset (0). Both are
            # required for the issue draft to render in the Linear UI (NB-392).
            "title": "",
            "priority": 0,
            # Markdown body — Linear auto-converts it to descriptionData on create.
            "description": CANONICAL_ISSUE_TEMPLATE_BODY,
            # Applied label carried BY NAME; resolved to labelIds against the live team
            # labels at seed time (resolve_template_label_ids), never a hardcoded id. Keeps
            # a templated issue pickup-eligible and the engine workspace-portable.
            LABEL_NAMES_KEY: ["problem"],
        },
    },
    "backlogd problem": {
        "type": "project",
        "description": CANONICAL_PROJECT_TEMPLATE_DESCRIPTION,
        "templateData": {
            # Empty title + no priority preset (0) — required for the project draft to
            # render. statusId is deliberately omitted (workspace-specific; a create
            # defaults it).
            "title": "",
            "priority": 0,
            "description": CANONICAL_PROJECT_TEMPLATE_DESCRIPTION,
            # Projects do NOT auto-convert description → descriptionData, so carry a minimal
            # Prosemirror doc for the one-line pointer body.
            "descriptionData": _minimal_prosemirror_doc(
                CANONICAL_PROJECT_TEMPLATE_DESCRIPTION
            ),
            "projectMilestones": [
                {"name": name, "sortOrder": i}
                for i, name in enumerate(CANONICAL_PROJECT_MILESTONES)
            ],
            # The empty collection arrays the working project draft carries.
            LABEL_IDS_KEY: [],
            "initiativeIds": [],
            "memberIds": [],
            "teamIds": [],
            "initialIssues": [],
        },
    },
    "Spec": {
        "type": "document",
        "description": "A backlogd Spec document — shaped Problem, Approach, and Acceptance Criteria.",
        # Document draft shape already renders — DO NOT change (NB-392).
        "templateData": {
            "title": "Spec",
            "content": CANONICAL_DOCUMENT_TEMPLATE_BODY,
            "icon": ":memo:",
        },
    },
}


# --- Key handling (the single chokepoint) ---------------------------------

def _parse_credentials_env(text: str) -> dict[str, str]:
    """Parse ``KEY=VALUE`` lines from a credentials file body.

    Pure and side-effect-free so it's unit-testable. Blank lines and ``#``
    comments are skipped; surrounding whitespace and a single layer of matching
    quotes around the value are stripped. Only the first ``=`` splits the line, so
    values may themselves contain ``=``.
    """
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key:
            out[key] = value
    return out


def load_api_key() -> str:
    """Resolve the Linear personal API key — env first, then credentials file.

    Resolution order:

    1. ``LINEAR_API_KEY`` environment variable, if non-empty.
    2. ``~/.backlogd/credentials.env`` — the ``LINEAR_API_KEY`` entry parsed from
       its ``KEY=VALUE`` lines. Home is resolved via :meth:`pathlib.Path.home`.

    Raises :class:`RuntimeError` with a message that names *where* to put the key
    but **never echoes any key material** — not the value we failed to find, not a
    partial. The caller (the network layer) is the only place the returned value
    is used; it must never be logged or surfaced.
    """
    env_val = os.environ.get(API_KEY_ENV)
    if env_val and env_val.strip():
        return env_val.strip()

    cred_path = pathlib.Path.home().joinpath(*CREDENTIALS_RELPATH)
    if cred_path.is_file():
        try:
            parsed = _parse_credentials_env(cred_path.read_text(encoding="utf-8"))
        except OSError as exc:
            # Surface *that* reading failed and where — but not the contents.
            raise RuntimeError(
                f"could not read credentials file at {cred_path}: {exc.strerror}"
            ) from None
        key = parsed.get(API_KEY_ENV, "").strip()
        if key:
            return key

    raise RuntimeError(
        f"no Linear API key found: set the {API_KEY_ENV} environment variable, "
        f"or add a line `{API_KEY_ENV}=<your-key>` to {cred_path}"
    )


# --- Network layer (thin; the only place the key is used) -----------------

class GraphQLError(RuntimeError):
    """A GraphQL request failed (transport error or ``errors`` in the body).

    Carries the GraphQL ``errors`` list (when present) so callers can inspect it.
    The message is built only from server-provided error text and never includes
    request headers — so the API key can never leak through it.
    """

    def __init__(self, message: str, errors: Optional[list] = None):
        super().__init__(message)
        self.errors = errors or []


def graphql(
    query: str,
    variables: Optional[dict[str, Any]] = None,
    *,
    url: str = LINEAR_GRAPHQL_URL,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Execute a Linear GraphQL operation and return its ``data`` payload.

    This is the **only** function that reads the API key and the only one that
    touches the network. The key is loaded here (:func:`load_api_key`) and set
    straight into the ``Authorization`` header — Linear personal API keys are
    sent **raw** (not ``Bearer ...``). The key is never logged and never placed in
    an exception message.

    Raises :class:`GraphQLError` on a transport failure or when the response body
    carries a top-level ``errors`` array.
    """
    api_key = load_api_key()
    body = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": api_key,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Read the server's error body if any — but never the request we sent
        # (which carries the Authorization header).
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001 — best-effort detail only
            pass
        raise GraphQLError(
            f"Linear API returned HTTP {exc.code}: {detail or exc.reason}"
        ) from None
    except urllib.error.URLError as exc:
        raise GraphQLError(f"could not reach Linear API: {exc.reason}") from None

    if payload.get("errors"):
        messages = "; ".join(
            e.get("message", "unknown error") for e in payload["errors"]
        )
        raise GraphQLError(f"GraphQL errors: {messages}", errors=payload["errors"])
    return payload.get("data", {})


# --- Pure helpers ---------------------------------------------------------

def normalize_label_name(name: str) -> str:
    """Normalize a label name for canonical comparison — lowercase + trimmed.

    Canonical labels are lowercase; we compare on the trimmed lowercase form so
    ``Problem``, ``PROBLEM`` and `` problem `` all collapse to ``problem``.
    """
    return name.strip().lower()


def _index_labels_by_normalized(labels: list[dict]) -> dict[str, list[dict]]:
    """Group live label dicts by their normalized name.

    Returns ``{normalized_name: [label, ...]}``. A list (not a single label)
    because two differently-cased labels can collide on the same normalized key —
    the recase planner needs to see all of them.
    """
    index: dict[str, list[dict]] = {}
    for label in labels:
        key = normalize_label_name(label.get("name", ""))
        index.setdefault(key, []).append(label)
    return index


def _label_issue_count_is_zero(label: dict) -> bool:
    """Whether a fetched label has zero issues applied.

    The audit query fetches ``issues(first: 1) { nodes { id } }`` per label
    (``IssueConnection`` exposes no ``totalCount``), so "zero issues" means the
    ``nodes`` list came back empty.
    """
    issues = label.get("issues") or {}
    nodes = issues.get("nodes") or []
    return len(nodes) == 0


# --- Pure planning: audit -------------------------------------------------

def plan_audit(
    labels: list[dict],
    states: list[dict],
    templates: list[dict],
) -> dict[str, Any]:
    """Compute the ``audit`` plan diff from already-fetched workspace state.

    Pure — no I/O. Takes the three lists the read queries return and produces a
    structured plan the CLI serialises to JSON:

    * ``missing``     — canonical labels with no live label of that (normalized)
      name. Each carries the name + the default color/description we'd create it
      with.
    * ``recase``      — labels present under a known canonical name but with the
      wrong case (e.g. ``Problem`` when canonical is ``problem``). Each carries
      the live id + ``from`` (current name) + ``to`` (canonical name).
    * ``cruft``       — the conservative recommend-delete set: every ``priority:*``
      label (duplicates Linear's native Priority field) plus the default
      ``Feature``/``Bug``/``Improvement`` labels **that have zero issues**. Other
      non-canonical labels go in ``review`` with no recommendation.
    * ``state_gaps``  — canonical state categories with no live workflow state.
    * ``ok``          — ``True`` when every bucket is empty (the workspace is
      already canonical / idempotent no-op).

    The plan is deterministic given its inputs, so the idempotency test can assert
    an all-empty plan for an already-canonical workspace.
    """
    by_norm = _index_labels_by_normalized(labels)

    # --- missing -----------------------------------------------------------
    missing: list[dict] = []
    for canon_name, attrs in CANONICAL_LABELS.items():
        if normalize_label_name(canon_name) not in by_norm:
            missing.append(
                {
                    "name": canon_name,
                    "color": attrs["color"],
                    "description": attrs["description"],
                }
            )

    # --- recase ------------------------------------------------------------
    recase: list[dict] = []
    for norm_key, target in CANONICAL_RECASE.items():
        for label in by_norm.get(normalize_label_name(norm_key), []):
            if label.get("name") != target:
                recase.append(
                    {
                        "id": label.get("id"),
                        "from": label.get("name"),
                        "to": target,
                    }
                )

    # --- cruft + review ----------------------------------------------------
    canonical_norms = {normalize_label_name(n) for n in CANONICAL_LABELS}
    canonical_norms |= {normalize_label_name(t) for t in CANONICAL_RECASE.values()}

    cruft: list[dict] = []
    review: list[dict] = []
    for label in labels:
        name = label.get("name", "")
        norm = normalize_label_name(name)
        if norm in canonical_norms:
            continue  # canonical (or its recase target) — never cruft.
        if norm.startswith(PRIORITY_LABEL_PREFIX):
            cruft.append(
                {
                    "id": label.get("id"),
                    "name": name,
                    "reason": "duplicates Linear's native Priority field",
                }
            )
        elif name in DEFAULT_DELETABLE_LABELS and _label_issue_count_is_zero(label):
            cruft.append(
                {
                    "id": label.get("id"),
                    "name": name,
                    "reason": "default label with zero issues",
                }
            )
        else:
            review.append({"id": label.get("id"), "name": name})

    # --- state gaps --------------------------------------------------------
    present_categories = {s.get("type") for s in states}
    state_gaps = [
        cat for cat in CANONICAL_STATE_CATEGORIES if cat not in present_categories
    ]

    plan = {
        "missing": missing,
        "recase": recase,
        "cruft": cruft,
        "review": review,
        "state_gaps": state_gaps,
    }
    plan["ok"] = not (missing or recase or cruft or state_gaps)
    return plan


# --- Pure planning: ensure-label ------------------------------------------

def plan_ensure_label(
    name: str,
    labels: list[dict],
    *,
    color: Optional[str] = None,
    description: Optional[str] = None,
) -> dict[str, Any]:
    """Decide whether ``ensure-label`` must create ``name`` and build its input.

    Idempotent: if a label with the same normalized name already exists, returns
    ``{"action": "noop", ...}`` with the existing label. Otherwise returns
    ``{"action": "create", "input": {...}}`` where ``input`` is the
    ``IssueLabelCreateInput`` (``name`` plus any color/description — falling back
    to the canonical defaults when the name is a known canonical label and no
    explicit value was given).
    """
    by_norm = _index_labels_by_normalized(labels)
    existing = by_norm.get(normalize_label_name(name))
    if existing:
        return {"action": "noop", "name": name, "existing": existing[0]}

    defaults = CANONICAL_LABELS.get(normalize_label_name(name), {})
    create_input: dict[str, Any] = {"name": name}
    resolved_color = color if color is not None else defaults.get("color")
    resolved_desc = description if description is not None else defaults.get("description")
    if resolved_color is not None:
        create_input["color"] = resolved_color
    if resolved_desc is not None:
        create_input["description"] = resolved_desc
    return {"action": "create", "name": name, "input": create_input}


# --- Pure planning: recase-label ------------------------------------------

def plan_recase_label(
    name: str,
    labels: list[dict],
    *,
    to: Optional[str] = None,
) -> dict[str, Any]:
    """Decide whether ``recase-label`` must rename ``name`` to its canonical case.

    The target case is ``to`` when given, else the canonical recase target for the
    normalized name (e.g. ``problem``). Idempotent:

    * label not found            → ``{"action": "noop", "reason": "not_found"}``
    * already canonical case      → ``{"action": "noop", "reason": "already_canonical"}``
    * needs rename                → ``{"action": "update", "id": ..., "input": {"name": target}}``

    The update uses ``issueLabelUpdate(id, input)`` with only ``name`` — which
    preserves the label id and therefore all existing applications.
    """
    norm = normalize_label_name(name)
    target = to if to is not None else CANONICAL_RECASE.get(norm, name.strip().lower())
    by_norm = _index_labels_by_normalized(labels)
    candidates = by_norm.get(norm, [])
    if not candidates:
        return {"action": "noop", "reason": "not_found", "name": name}
    # Prefer an exact-name match to drive the decision; otherwise the first.
    label = next((c for c in candidates if c.get("name") == name), candidates[0])
    if label.get("name") == target:
        return {"action": "noop", "reason": "already_canonical", "name": target}
    return {
        "action": "update",
        "id": label.get("id"),
        "from": label.get("name"),
        "to": target,
        "input": {"name": target},
    }


# --- Pure planning: delete-label ------------------------------------------

def plan_delete_label(name: str, labels: list[dict]) -> dict[str, Any]:
    """Resolve ``name`` to a deletable label id.

    Idempotent: missing label → ``{"action": "noop", "reason": "not_found"}``.
    Found → ``{"action": "delete", "id": ..., "name": ...}``. This is the only
    planner that authorises a destructive mutation; the caller must have invoked
    ``delete-label`` explicitly.
    """
    by_norm = _index_labels_by_normalized(labels)
    candidates = by_norm.get(normalize_label_name(name), [])
    label = next((c for c in candidates if c.get("name") == name), None)
    if label is None and candidates:
        label = candidates[0]
    if label is None:
        return {"action": "noop", "reason": "not_found", "name": name}
    return {"action": "delete", "id": label.get("id"), "name": label.get("name")}


# --- Pure planning: ensure-state ------------------------------------------

def plan_ensure_state(
    category: str,
    name: str,
    states: list[dict],
    *,
    team_id: str,
    color: str = "#95a2b3",
) -> dict[str, Any]:
    """Decide whether ``ensure-state`` must create a state in ``category``.

    **Additive only** — if any live state already has this category (``type``),
    returns ``{"action": "noop", ...}`` and never touches it. There is no rename,
    reorder, or delete path. Otherwise returns ``{"action": "create", "input":
    {...}}`` with a ``WorkflowStateCreateInput`` (``name``, ``type=category``,
    ``color``, ``teamId``).

    Raises :class:`ValueError` for a category outside the canonical set — the
    forecast math only knows the five Linear categories.
    """
    if category not in CANONICAL_STATE_CATEGORIES:
        raise ValueError(
            f"unknown state category {category!r}; "
            f"expected one of {', '.join(CANONICAL_STATE_CATEGORIES)}"
        )
    for state in states:
        if state.get("type") == category:
            return {"action": "noop", "category": category, "existing": state}
    return {
        "action": "create",
        "category": category,
        "input": {
            "name": name,
            "type": category,
            "color": color,
            "teamId": team_id,
        },
    }


# --- Pure planning: ensure-template ---------------------------------------

def plan_ensure_template(
    name: str,
    template_type: str,
    template_data: dict[str, Any],
    templates: list[dict],
    *,
    team_id: Optional[str] = None,
    description: Optional[str] = None,
) -> dict[str, Any]:
    """Build the create-or-update plan for an issue/project template.

    Idempotent on ``(name, type)``: if a live template already matches both, the
    plan is an ``update`` carrying its id and a ``TemplateUpdateInput`` (the
    mutable subset — ``name``, ``templateData``, ``description``). Otherwise it's a
    ``create`` carrying a full ``TemplateCreateInput`` (``name``, ``type``,
    ``templateData`` — the JSON-encoded attributes — plus optional ``teamId`` /
    ``description``).

    Note ``templateData`` is sent as a JSON value (Linear's ``JSON!`` scalar): we
    keep it as a Python dict here and let the network layer serialise the whole
    request body once. Raises :class:`ValueError` for an unknown template type.
    """
    if template_type not in TEMPLATE_TYPES:
        raise ValueError(
            f"unknown template type {template_type!r}; "
            f"expected one of {', '.join(TEMPLATE_TYPES)}"
        )
    match = next(
        (
            t
            for t in templates
            if t.get("name") == name and t.get("type") == template_type
        ),
        None,
    )
    if match is not None:
        update_input: dict[str, Any] = {
            "name": name,
            "templateData": template_data,
        }
        if description is not None:
            update_input["description"] = description
        return {
            "action": "update",
            "id": match.get("id"),
            "name": name,
            "type": template_type,
            "input": update_input,
        }

    create_input: dict[str, Any] = {
        "name": name,
        "type": template_type,
        "templateData": template_data,
    }
    if team_id is not None:
        create_input["teamId"] = team_id
    if description is not None:
        create_input["description"] = description
    return {
        "action": "create",
        "name": name,
        "type": template_type,
        "input": create_input,
    }


def plan_canonical_templates(
    templates: list[dict],
    *,
    team_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Build the create-or-update plan for **every** canonical template (ADR-003).

    Iterates :data:`CANONICAL_TEMPLATES` — the single source of truth — and returns
    one :func:`plan_ensure_template` plan per entry, in registry order (``Problem``
    issue · ``backlogd problem`` project · ``Spec`` document). This is the surface
    ``/backlogd:init`` §4 drives so the designed ``templateData`` is never improvised
    in command prose; idempotency is inherited from :func:`plan_ensure_template`
    (a live template matching ``(name, type)`` becomes an ``update``).

    Pure — no I/O. ``team_id`` (when given) scopes any *create* to the team.
    """
    plans: list[dict[str, Any]] = []
    for name, spec in CANONICAL_TEMPLATES.items():
        plans.append(
            plan_ensure_template(
                name,
                spec["type"],
                spec["templateData"],
                templates,
                team_id=team_id,
                description=spec.get("description"),
            )
        )
    return plans


# --- Pure: resolve template labels by name → labelIds at seed time --------

def resolve_template_label_ids(
    template_data: dict[str, Any],
    labels: list[dict],
) -> dict[str, Any]:
    """Resolve a template's ``labels`` (by name) to a ``labelIds`` array.

    Linear's draft-entity ``templateData`` for an issue carries applied labels as a
    ``labelIds`` array of ids, **not** label names — but :data:`CANONICAL_TEMPLATES`
    deliberately encodes the ``problem`` label **by name** (under :data:`LABEL_NAMES_KEY`)
    so the engine hardcodes **no per-workspace label id** and stays portable. This pure
    transformer is the seed-time bridge: given the template's ``templateData`` and the
    live team labels (the same list the audit query already fetches), it returns a **new**
    ``templateData`` dict with the ``labels`` names mapped to a ``labelIds`` array and the
    ``labels`` key dropped.

    Matching is case-insensitive on the normalized label name (so ``Problem`` resolves
    ``problem``). If the data carries no ``labels`` key, the input is returned unchanged
    (defensively copied). Any ``labelIds`` already present (e.g. the project template's
    empty array) is preserved and extended.

    Raises :class:`ValueError` naming the unresolved label name(s) if any name has no live
    label — so the caller surfaces a clear error and skips that template rather than
    sending a payload with a missing id.
    """
    out = dict(template_data)
    names = out.pop(LABEL_NAMES_KEY, None)
    if not names:
        return out

    by_norm = _index_labels_by_normalized(labels)
    resolved: list[str] = list(out.get(LABEL_IDS_KEY, []))
    missing: list[str] = []
    for name in names:
        candidates = by_norm.get(normalize_label_name(name), [])
        # Prefer an exact-name match; fall back to the first normalized collision.
        match = next((c for c in candidates if c.get("name") == name), None)
        if match is None and candidates:
            match = candidates[0]
        if match is None or not match.get("id"):
            missing.append(name)
            continue
        resolved.append(match["id"])

    if missing:
        raise ValueError(
            "cannot resolve template label name(s) to a live label id: "
            + ", ".join(repr(n) for n in missing)
            + " — create the label first (e.g. via ensure-label) and re-run"
        )

    out[LABEL_IDS_KEY] = resolved
    return out


# --- GraphQL documents ----------------------------------------------------

# Read query for ``audit``. ``issues(first: 1)`` is the cheapest signal for the
# zero-issue cruft check (IssueConnection has no totalCount). We fetch the team's
# states by team id so a multi-team workspace audits the right board.
_AUDIT_QUERY = """
query BacklogdAudit($teamId: String!, $teamIdC: ID!) {
  issueLabels(first: 250) {
    nodes { id name color description issues(first: 1) { nodes { id } } }
  }
  workflowStates(first: 250, filter: { team: { id: { eq: $teamIdC } } }) {
    nodes { id name type position }
  }
  team(id: $teamId) {
    templates { nodes { id name type } }
  }
}
"""

_LABEL_CREATE_MUTATION = """
mutation BacklogdLabelCreate($input: IssueLabelCreateInput!) {
  issueLabelCreate(input: $input) {
    success
    issueLabel { id name color }
  }
}
"""

_LABEL_UPDATE_MUTATION = """
mutation BacklogdLabelUpdate($id: String!, $input: IssueLabelUpdateInput!) {
  issueLabelUpdate(id: $id, input: $input) {
    success
    issueLabel { id name }
  }
}
"""

_LABEL_DELETE_MUTATION = """
mutation BacklogdLabelDelete($id: String!) {
  issueLabelDelete(id: $id) { success }
}
"""

_STATE_CREATE_MUTATION = """
mutation BacklogdStateCreate($input: WorkflowStateCreateInput!) {
  workflowStateCreate(input: $input) {
    success
    workflowState { id name type }
  }
}
"""

_TEMPLATE_CREATE_MUTATION = """
mutation BacklogdTemplateCreate($input: TemplateCreateInput!) {
  templateCreate(input: $input) {
    success
    template { id name type }
  }
}
"""

_TEMPLATE_UPDATE_MUTATION = """
mutation BacklogdTemplateUpdate($id: String!, $input: TemplateUpdateInput!) {
  templateUpdate(id: $id, input: $input) {
    success
    template { id name type }
  }
}
"""


# --- Network reads (used by the verbs) ------------------------------------

def fetch_workspace_state(team_id: str) -> dict[str, list[dict]]:
    """Fetch the live labels / states / templates the audit + verbs reason over.

    Thin wrapper over :func:`graphql` that flattens the connection ``nodes`` into
    plain lists, so the pure planners receive exactly the shape they expect.
    """
    data = graphql(_AUDIT_QUERY, {"teamId": team_id, "teamIdC": team_id})
    labels = (data.get("issueLabels") or {}).get("nodes") or []
    states = (data.get("workflowStates") or {}).get("nodes") or []
    team = data.get("team") or {}
    templates = (team.get("templates") or {}).get("nodes") or []
    return {"labels": labels, "states": states, "templates": templates}


# --- CLI command handlers -------------------------------------------------

def _emit(obj: Any) -> int:
    """Print ``obj`` as pretty JSON to stdout and return a 0 exit code."""
    print(json.dumps(obj, indent=2, ensure_ascii=False))
    return 0


def _cmd_audit(args: argparse.Namespace) -> int:
    """``audit`` — read-only plan diff to stdout."""
    state = fetch_workspace_state(args.team_id)
    plan = plan_audit(state["labels"], state["states"], state["templates"])
    return _emit({"verb": "audit", "team_id": args.team_id, "plan": plan})


def _cmd_ensure_label(args: argparse.Namespace) -> int:
    """``ensure-label`` — create a label if absent (idempotent)."""
    state = fetch_workspace_state(args.team_id)
    plan = plan_ensure_label(
        args.name, state["labels"], color=args.color, description=args.description
    )
    if plan["action"] == "create":
        if args.scope_team:
            plan["input"].setdefault("teamId", args.team_id)
        data = graphql(_LABEL_CREATE_MUTATION, {"input": plan["input"]})
        result = (data.get("issueLabelCreate") or {})
        return _emit({"verb": "ensure-label", "action": "created", "result": result})
    return _emit({"verb": "ensure-label", "action": "noop", "existing": plan["existing"]})


def _cmd_recase_label(args: argparse.Namespace) -> int:
    """``recase-label`` — rename a label to canonical case, preserving its id."""
    state = fetch_workspace_state(args.team_id)
    plan = plan_recase_label(args.name, state["labels"], to=args.to)
    if plan["action"] == "update":
        data = graphql(
            _LABEL_UPDATE_MUTATION, {"id": plan["id"], "input": plan["input"]}
        )
        result = (data.get("issueLabelUpdate") or {})
        return _emit(
            {"verb": "recase-label", "action": "updated", "from": plan["from"],
             "to": plan["to"], "result": result}
        )
    return _emit({"verb": "recase-label", "action": "noop", "reason": plan["reason"]})


def _cmd_delete_label(args: argparse.Namespace) -> int:
    """``delete-label`` — delete a named label (the only destructive verb)."""
    state = fetch_workspace_state(args.team_id)
    plan = plan_delete_label(args.name, state["labels"])
    if plan["action"] == "delete":
        data = graphql(_LABEL_DELETE_MUTATION, {"id": plan["id"]})
        result = (data.get("issueLabelDelete") or {})
        return _emit(
            {"verb": "delete-label", "action": "deleted", "name": plan["name"],
             "result": result}
        )
    return _emit({"verb": "delete-label", "action": "noop", "reason": plan["reason"]})


def _cmd_ensure_state(args: argparse.Namespace) -> int:
    """``ensure-state`` — additive only; create a state in a missing category."""
    state = fetch_workspace_state(args.team_id)
    plan = plan_ensure_state(
        args.category, args.name, state["states"],
        team_id=args.team_id, color=args.color,
    )
    if plan["action"] == "create":
        data = graphql(_STATE_CREATE_MUTATION, {"input": plan["input"]})
        result = (data.get("workflowStateCreate") or {})
        return _emit({"verb": "ensure-state", "action": "created", "result": result})
    return _emit({"verb": "ensure-state", "action": "noop", "existing": plan["existing"]})


def _cmd_ensure_template(args: argparse.Namespace) -> int:
    """``ensure-template`` — create or update an issue/project template.

    If the supplied ``templateData`` carries applied labels **by name** (the
    :data:`LABEL_NAMES_KEY` marker that :data:`CANONICAL_TEMPLATES` uses), those names are
    resolved to a ``labelIds`` array against the live team labels here — at seed time, with
    the team context already in hand — so no per-workspace label id is hardcoded. An
    unresolved name raises (caught by :func:`main`) so the verb fails loudly rather than
    sending a draft with a missing id.
    """
    try:
        template_data = json.loads(args.data)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"--data is not valid JSON: {exc}") from None
    state = fetch_workspace_state(args.team_id)
    # Resolve any by-name labels to ids against the freshly-fetched team labels.
    template_data = resolve_template_label_ids(template_data, state["labels"])
    plan = plan_ensure_template(
        args.name, args.type, template_data, state["templates"],
        team_id=args.team_id if args.scope_team else None,
        description=args.description,
    )
    if plan["action"] == "update":
        data = graphql(
            _TEMPLATE_UPDATE_MUTATION, {"id": plan["id"], "input": plan["input"]}
        )
        result = (data.get("templateUpdate") or {})
        return _emit({"verb": "ensure-template", "action": "updated", "result": result})
    data = graphql(_TEMPLATE_CREATE_MUTATION, {"input": plan["input"]})
    result = (data.get("templateCreate") or {})
    return _emit({"verb": "ensure-template", "action": "created", "result": result})


# --- CLI wiring -----------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser with the six idempotent verbs.

    Factored out of :func:`main` so ``--help`` rendering and the subcommand list
    are unit-testable (and the AC's ``--help`` check has a stable surface).
    """
    parser = argparse.ArgumentParser(
        prog="linear_setup.py",
        description=(
            "backlogd Linear config engine — bring a workspace into canonical "
            "shape (labels, workflow states, templates). Stdlib-only GraphQL; "
            "key read from $LINEAR_API_KEY or ~/.backlogd/credentials.env."
        ),
    )
    sub = parser.add_subparsers(dest="verb", required=True)

    # audit -----------------------------------------------------------------
    pa = sub.add_parser(
        "audit",
        help="read live labels/states/templates and print a plan diff (read-only)",
    )
    pa.add_argument("--team-id", required=True, help="Linear team id or key")
    pa.set_defaults(func=_cmd_audit)

    # ensure-label ----------------------------------------------------------
    pel = sub.add_parser(
        "ensure-label", help="create a label if absent (idempotent)"
    )
    pel.add_argument("--team-id", required=True, help="Linear team id or key")
    pel.add_argument("--name", required=True, help="label name")
    pel.add_argument("--color", default=None, help="hex color, e.g. #5e6ad2")
    pel.add_argument("--description", default=None, help="label description")
    pel.add_argument(
        "--scope-team", action="store_true",
        help="scope the label to the team (default: workspace-wide)",
    )
    pel.set_defaults(func=_cmd_ensure_label)

    # recase-label ----------------------------------------------------------
    prl = sub.add_parser(
        "recase-label",
        help="rename a label to its canonical case (preserves id/applications)",
    )
    prl.add_argument("--team-id", required=True, help="Linear team id or key")
    prl.add_argument("--name", required=True, help="current label name, e.g. Problem")
    prl.add_argument(
        "--to", default=None,
        help="target name (default: canonical recase, e.g. problem)",
    )
    prl.set_defaults(func=_cmd_recase_label)

    # delete-label ----------------------------------------------------------
    pdl = sub.add_parser(
        "delete-label", help="delete a named label (the only destructive verb)"
    )
    pdl.add_argument("--team-id", required=True, help="Linear team id or key")
    pdl.add_argument("--name", required=True, help="label name to delete")
    pdl.set_defaults(func=_cmd_delete_label)

    # ensure-state ----------------------------------------------------------
    pes = sub.add_parser(
        "ensure-state",
        help="additive only: create a workflow state in a missing category",
    )
    pes.add_argument("--team-id", required=True, help="Linear team id or key")
    pes.add_argument(
        "--category", required=True, choices=list(CANONICAL_STATE_CATEGORIES),
        help="state category (backlog/unstarted/started/completed/canceled)",
    )
    pes.add_argument("--name", required=True, help="display name for the new state")
    pes.add_argument("--color", default="#95a2b3", help="hex color for the state")
    pes.set_defaults(func=_cmd_ensure_state)

    # ensure-template -------------------------------------------------------
    pet = sub.add_parser(
        "ensure-template", help="create or update an issue/project template"
    )
    pet.add_argument("--team-id", required=True, help="Linear team id or key")
    pet.add_argument("--name", required=True, help="template name")
    pet.add_argument(
        "--type", required=True, choices=list(TEMPLATE_TYPES),
        help="template entity type (issue/project/document)",
    )
    pet.add_argument(
        "--data", required=True,
        help="templateData as a JSON string (pre-filled entity attributes)",
    )
    pet.add_argument("--description", default=None, help="template description")
    pet.add_argument(
        "--scope-team", action="store_true",
        help="scope the template to the team (default: shared across teams)",
    )
    pet.set_defaults(func=_cmd_ensure_template)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entry point — parse args, dispatch the verb, surface errors cleanly.

    Each verb emits structured JSON to stdout and returns 0 on success. Network /
    GraphQL failures and bad input return a non-zero exit code with a message on
    stderr that **never contains key material** (the key only ever lives inside
    :func:`graphql`).
    """
    # Force UTF-8 on stdout/stderr so JSON with Unicode prints cleanly under
    # Windows' default cp1252 console too. Best-effort (mirrors graph.py).
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001 — never block the CLI
                pass

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (GraphQLError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


__all__ = [
    "CANONICAL_DOCUMENT_TEMPLATE_BODY",
    "CANONICAL_ISSUE_TEMPLATE_BODY",
    "CANONICAL_LABELS",
    "CANONICAL_PROJECT_MILESTONES",
    "CANONICAL_PROJECT_TEMPLATE_DESCRIPTION",
    "CANONICAL_RECASE",
    "CANONICAL_STATE_CATEGORIES",
    "CANONICAL_TEMPLATES",
    "GraphQLError",
    "LABEL_IDS_KEY",
    "LABEL_NAMES_KEY",
    "build_parser",
    "fetch_workspace_state",
    "graphql",
    "load_api_key",
    "main",
    "normalize_label_name",
    "plan_audit",
    "plan_canonical_templates",
    "plan_delete_label",
    "plan_ensure_label",
    "plan_ensure_state",
    "plan_ensure_template",
    "plan_recase_label",
    "resolve_template_label_ids",
]


if __name__ == "__main__":
    raise SystemExit(main())
