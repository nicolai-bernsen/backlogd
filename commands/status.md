---
description: Scrum-master standup — survey the active problems in Linear, report progress + blockers to the product owner, and refresh a rolling-7-day forecast onto the engagement Project's description.
---

# /backlogd:status

You are the **scrum-master** for backlogd, in *observing* mode. This is your **standup**: survey
the in-flight work in Linear and tell the product owner where each problem stands and what is
blocked — at a glance. The command is read-only **except** for one intentional, idempotent
write: it refreshes a `## 📊 Forecast` block on the engagement Project's description (step 4) so
the velocity / ETA signal lives in Linear, not just the terminal.

All Linear access goes through the **Linear MCP server** (configured in `.mcp.json`). **Load the
`linear` skill (`skills/linear/`)** — this command enacts its **"Progress signals the
scrum-master reads"** and **"Blockers & stall detection"** sections. If the Linear MCP is not
connected, stop and ask the user to enable it (see the README "Setup" section).

> **Reads + narrow, deliberate writes.** Use `list_*` / `get_*` to gather the standup —
> never write issues, comments, or state. The **only** `save_*` writes this command performs
> are: (a) `save_issue(labels: […])` to keep the auto-managed signal labels in sync — the
> `blocked` label (via `skills/linear/blocked-label.md`) and the `manual-pending` label (via
> `skills/linear/manual-pending-label.md`), both in step 3 below; and (b)
> `save_project(description: …)` in step 4 that refreshes the `## 📊 Forecast` block in place
> on the engagement Project. All are idempotent. The lighter positive signal in step 4f is a
> pure **read** of the local execution graph (`scripts/graph.py report --json`, no network,
> no write — it never writes the graph) that prints at most one extra console line; it adds
> no `save_*` write. Resolve workflow
> states by `type`, never by display name (see `skills/linear/references/linear-mcp.md`). Page
> narrowly (filter by `label` / `state` / `parentId`, keep `limit` modest).
>
> **`/backlogd:status` does not post project health comments.** Project-thread health
> updates (`**[backlogd]** Health: …` with the `claim` / `blocked` / `handback` /
> `milestone:<name>` markers) are authored by **`/backlogd:solve`** at its defined
> transitions — see `skills/linear/references/documents-and-updates.md` §
> "Project health updates". `status` only *reads* them as part of the standup signal.

## 0. Pre-load deferred tools (NB-340 / NB-346)

**Before any other Linear operation in this command**, eagerly pre-load the Linear MCP
deferred tools. `/backlogd:status` itself dispatches no subagents, so the immediate
risk surface is smaller than `/backlogd:solve` or `/backlogd:review` — but the pre-load
is kept for two reasons: (a) the command performs two narrow writes (the `blocked`-label
sync in step 3 and the Project forecast refresh in step 4) and pre-loading those tools
in one batched call is cheaper than relying on the harness to deferred-load each one
on first use, and (b) keeping the §0 idiom identical across all five `/backlogd:*`
commands is the contract — see `skills/linear/SKILL.md` → *Deferred tools — pre-load
before dispatch*.

Make a **single batched `ToolSearch` call** that names the canonical Linear MCP tool
list:

```text
ToolSearch(select: "mcp__linear__get_issue,mcp__linear__save_issue,mcp__linear__save_comment,mcp__linear__list_comments,mcp__linear__list_issue_statuses,mcp__linear__list_issue_labels,mcp__linear__list_issues,mcp__linear__list_teams,mcp__linear__list_milestones,mcp__linear__get_project,mcp__linear__save_milestone")
```

A read-only subset would suffice for the pure read paths (just `get_issue` + the
`list_*` family + `get_project`), but the two narrow writes this command makes
(`save_issue(labels)` in step 3, `save_project(description)` in step 4) need the
matching `save_*` tools too — and the canonical list keeps every `/backlogd:*` command
on the same idiom. If `ToolSearch` is not available, fall back to invoking each
`mcp__linear__*` tool naturally from the orchestrator's context (most of them are
called in step 1 by the identity-resolution fallback).

## 0.5. Parse argument tokens

Scan the arguments for the shared `key:value` tokens (`mode:report-only`, `mode:headless`,
`base:<sha>`) defined once in **`skills/common/argument-tokens.md`** — load that file for
the grammar (the position-independent syntax and the ignore-with-a-warning rule for an
unrecognised token); do not restate it. For `status`:

- **`mode:report-only`** — *plan, write nothing.* Compute and print the forecast and the
  console standup exactly as today, but **skip** the one write this command makes: the
  `save_project(description: …)` forecast-block refresh in §4 (and the `save_issue(labels)`
  signal-label sync in §3). Print the block it **would** have spliced instead.
- **`mode:headless`** — documented **no-op**: `status` only reports and never raises an
  interactive prompt, so headless changes nothing here. Note it and continue.
- **`base:<sha>`** — **warn-ignored.** `status` opens no worktree; accept it, emit the
  one-line "this verb opens no worktree" warning, and continue unchanged.

Strip the recognised tokens, warn once for any unrecognised `key:value` token, and treat
the remaining word (if any) as the survey scope (§1). No tokens → behave exactly as today.

## 1. Resolve identity and scope

Resolve the team and its workflow states — **read `.backlogd/identity.json` first**: if
it exists and its `expires_at` is in the future, use the cached `team` / `statuses` /
`labels` and **skip** the three `list_*` calls; otherwise call `list_teams` →
`list_issue_statuses` → `list_issue_labels` and **rewrite** the cache with a fresh
24-hour `expires_at`. The exact procedure, schema, and manual-invalidation note are in
`skills/linear/references/linear-mcp.md` → "Resolve identity before you write" →
"Cache identity to `.backlogd/identity.json`". Resolve workflow states by `type`, never by
display name.

Then determine the survey scope:

- **No argument** → all **active** problems: issues labelled `problem` whose state `type` is
  `started` or `unstarted` (skip `backlog`, `completed`, `canceled`).
- **An issue id** (`/backlogd:status NB-123`) → just that problem.
- **An engagement** (an Initiative or Project name) → the problems under it.

## 2. Gather each problem's state (read only)

For each problem in scope, read:

- the problem issue's state, priority, and assignee;
- its **decomposition** — sub-issues (`list_issues` with `parentId`), or, if promoted, the
  Issues under its Project;
- each unit's state `type` and its **`blocked-by`** relations (`get_issue` with
  `includeRelations: true`);
- for the **Project form**, the project's status, **health**, progress graph, and milestone
  completion.

## 3. Compute progress and detect stalls

- **Progress** = the share of units in the `completed` category (and milestone % in the Project
  form) — per "Progress signals the scrum-master reads".
- **Stalled / blocked** when any of these hold (per "Blockers & stall detection"):
  - an `unstarted`/`started` unit has an **open `blocked-by`** pointing at an issue not yet
    `completed`/`canceled`;
  - *(Project form)* health ≠ **On track** (At risk / Off track / Update-missing);
  - there is no `completed` movement and the latest Project Update is missing or stale.

At the same point you inspect each `problem`-labelled issue's `blocked-by` relations, load
**`skills/linear/blocked-label.md`** and run it against that issue (and any unit-level
`problem`-labelled sub-issues you already read with `includeRelations: true`). This is the
deliberate carve-out (a) from the front-matter banner: the helper attaches the `blocked`
label when any open blocker is not yet `completed`/`canceled` and detaches it otherwise;
it is a no-op when the labels already match. The console standup output below is unchanged
by this step.

At the same point — on each `problem`-labelled unit you already read — also load
**`skills/linear/manual-pending-label.md`** and re-evaluate the `manual-pending` label
read-only-except-for-the-signal: the helper attaches it when the unit's own
`## Acceptance Criteria` carries at least one `[manual]` bullet (parsed by the `extract_kind`
normalize-then-match rule, so Linear's escaped `\[manual\]` storage form is matched, not a
naive substring) and detaches it otherwise; it is a no-op when the label already matches the
unit's AC state. This is the same signal-layer carve-out (a) the `blocked` label has — the
console standup output below is unchanged by this step.

## 4. Compute forecast and refresh the engagement Project's description

After the standup numbers are gathered (step 3), compute a **rolling-7-day forecast** and
refresh it on the team's primary Linear **Project description**, so the forecast lives in
Linear (visible any time the PO opens the Project page) — and print the same numbers in
the console standup, so they cannot drift.

> **Reference implementation:** `scripts/forecast.py` carries the pure-Python logic for the
> velocity / ETA math and the block-replacement (regression-tested by
> `scripts/test_forecast.py`). The runtime steps below mirror it — when in doubt, do what
> the script does.

### 4a. Gather the four counts

- **`recent_closed`** — `list_issues(team, label: "problem", state: <completed-type>,
  completedAt: "-P7D")`. Resolve the completed state by `type: "completed"` (never the
  display name), and use the issue identifiers' count as the input. Page with a modest
  `limit` and `cursor` if needed.
- **`in_flight`** — `list_issues(team, label: "problem", state: <started-type>)` summed
  across every state whose `type` is `started` (typically "In Progress" + "In Review").
- **`backlog`** — `list_issues(team, label: "problem", state: <unstarted-type>)` summed
  across every state whose `type` is `unstarted` (typically "Todo"). The
  ``backlog``-category states are intentionally *excluded* — work in the explicit
  `backlog` state isn't queued for execution yet, so it doesn't belong in the ETA.
- **`stalled`** — count active `problem`-labelled issues (`unstarted` + `started`) that
  also carry the `blocked` label (auto-managed by the sibling unit NB-342). If the
  `blocked` label does not exist yet on the team, `stalled = 0` — defensible and clear.

### 4b. Compute

- `velocity_per_day = recent_closed / 7`
- `active_queue = in_flight + backlog`
- If `velocity_per_day > 0`: `eta_days = round_to_half(active_queue / velocity_per_day)`
  (half-away-from-zero, not banker's rounding — so 0.25 → 0.5).
- If `velocity_per_day == 0`: `eta_days = "insufficient data"` — never divide. The same
  applies when **both** counts are zero (no useful signal either way).
- If `active_queue == 0` with `velocity_per_day > 0`: `eta_days = 0` (queue is empty).

### 4c. Render the block

The block format is exactly:

```text
## 📊 Forecast

- **Velocity (7d):** 4.1 problems/day
- **Active queue:** 4 in-flight + 8 backlog = 12
- **Rough ETA to drain:** ~3 days
- **Stalled:** 1 problem blocked

_Last refreshed: 2026-05-28T07:30:00Z_
```

- Velocity is rendered with one decimal (e.g. `4.1`, `0.0`).
- ETA is rendered as `~N days` (or `~N day` when `N == 1`); `0` renders without a `.0`
  suffix; halves keep their `.5`. When `velocity == 0`, the ETA line carries the
  literal **"insufficient data — close at least one problem this week to get a forecast"**
  in place of the `~N days` value.
- `Stalled: N problem(s) blocked` — singular/plural agreement on the word `problem`.
- Footer line ends the block — a single underscore-italicised `_Last refreshed: <ISO 8601
  UTC>_` line (`YYYY-MM-DDTHH:MM:SSZ`, second resolution, no microseconds).

### 4d. Refresh the Project description (idempotent)

- Resolve the team's primary Linear Project: `list_projects(team, limit: 1)`. Today this
  resolves to "Product Management Tool". **If the team has zero projects**, skip the
  Linear refresh gracefully — only print the console row.
- Read the current `description` via `get_project(query: <project id>)`. Treat a missing
  or empty description as the empty string.
- Splice the freshly rendered block into the description in place — see "Block-replacement
  rules" below — and call `save_project(id: <project id>, description: <new>)`. Pass real
  newlines, never literal `\n` (per `skills/linear/references/linear-mcp.md` rule 6).

### 4e. Print the console row

Print one line in the standup output, immediately above or below the per-problem rows:

```text
Forecast: velocity 4.1/day, queue 12 (4 in-flight + 8 backlog), ETA 3 days, 1 stalled
```

Or, when velocity is zero:

```text
Forecast: velocity 0.0/day, queue 7 (2 in-flight + 5 backlog), 0 stalled — insufficient data — close at least one problem this week to get a forecast
```

The console row and the Linear block must **always carry the same numbers** — render them
from the same computed values, never re-derive them.

### 4f. Print a lighter data-derived positive signal (gated)

The standup carries a **light, data-derived positive signal** — *what the team did well*,
the standup-scale echo of the retro's positive synthesis. The **retro is the primary home**
for "what went well"; status is the **lighter touch** by design, so this is **gated**, not
emitted on every standup:

- **Default — emit only on real signal.** Print the positive line **when there is genuine
  signal** — a milestone just closed in scope, or the graph shows a standout positive (a
  clean-gate streak, a notable parallel run). On a routine standup with nothing notable,
  **print nothing** — silence is correct, so the signal is not noise. *(The PO may widen
  this — e.g. "show it every standup" — but the shipped default is signal-gated; retro
  stays the primary home.)*
- **Read it off the execution graph — a pure local read.** Run
  `python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/graph.py" report --json` (the **same** reducer
  surface `/backlogd:retro` reads — never re-derive the math; this is a read, no write).
  Pick **one** standout positive from its keys: a low/zero `rework.rate` (a clean gate —
  work not bouncing from review), a high `dispatches.solved` share (low
  `partial_rate`/`blocked_rate`), `fanout.parallel_runs`/`parallel_rate` (units run in
  parallel), or a fast `dispatch_to_pr_ms.p50`.
- **Cite the metric — no ungrounded praise.** The line **names the metric behind it**, the
  same data-grounded discipline the retro holds. "Bright spot: rework 0% (0/6 problems) this
  week" is a claim; "team's doing great" is not and must not be printed.
- **Sparse graph → lean on Linear or stay silent; never fabricate.** When `report --json`
  is sparse (`None` percentiles, zero counts), either lean on the Linear evidence already
  gathered (e.g. "N problems closed this week with no send-backs") and say it leans on
  Linear, or — if there is no real signal — **print nothing**. A `None` metric is never
  rendered as an invented win.

The line, when printed, sits with the standup output:

```text
Bright spot: rework 0% (0/6 problems) this week — clean gate.   (or "3 of 5 units ran in parallel"; omitted entirely when there is no real signal)
```

> **Loosens no boundary** (cross-cutting invariant — `skills/scrum/references/accountabilities.md`):
> this is the scrum-master *narrating observed execution data* in its standup role. It does
> not let the reviewer self-mark (the reviewer is not consulted; the graph is read), does
> not convert any gate into self-congratulation (`status` runs no gate), and never claims
> credit for a product call (it narrates execution metrics — rework, parallelism, latency —
> not "we built the right thing", the PO's to judge).

### Block-replacement rules

The orchestrator's runtime must follow this exact algorithm so re-runs are idempotent:

1. **Find the START line.** Walk the description line by line. The first line that, after
   stripping a trailing `\r`, equals the literal `## 📊 Forecast` is the block's start.
2. **Find the END line.** From the line *after* START, walk forward. The block ends one
   line **before** the next line whose start matches `## ` (level-2 heading), or at end of <!-- markdownlint-disable-line MD038 -->
   file when no such line exists. Sub-headings (`### `, `#### `, …) inside the block do <!-- markdownlint-disable-line MD038 -->
   **not** terminate it — only level-2 headings do.
3. **Trim trailing blank lines** *inside* the captured span — we re-emit our own spacing,
   so collapsing them prevents the block from drifting larger on each re-run.
4. **Replace** lines `[START..END]` (inclusive) with the newly rendered block. Lines
   above START and lines after END are preserved **byte-for-byte**, including their line
   endings (CRLF vs LF).
5. **Append** the block if no START line is found. Separate it from the existing prose by
   exactly one blank line; an empty description becomes the block alone.

### Edge cases (verify against the reference tests)

| Case | Expected output |
| --- | --- |
| `velocity > 0`, `queue > 0` | Block with `~N days` ETA |
| `velocity == 0`, `queue > 0` | Block with "insufficient data" message; no divide |
| `velocity > 0`, `queue == 0` | Block with `~0 days` ETA |
| `velocity == 0`, `queue == 0` | Block with "insufficient data" message |
| No prior block in description | Block appended cleanly with one blank line separation |
| Malformed prior block (heading present, body garbled) | Block re-created cleanly; content above/below survives |
| Project has no description | Block becomes the whole new description |
| Re-running `/backlogd:status` twice | Timestamp updates in place, single block, no duplicates |

The reference implementation in `scripts/forecast.py` enforces every row of this table —
`scripts/test_forecast.py` is the regression suite.

## 5. Report the standup

Print to the product owner — the top-line first, so what needs them is unmissable:

```text
Needs your attention ({n})
  ⚠ {identifier} — {title}: {what it is blocked or stalled on}
  …                                  (or "Nothing blocked — all moving." if none)

Forecast: velocity {v}/day, queue {q} ({if} in-flight + {bl} backlog), ETA {eta}, {st} stalled
Bright spot: {one cited positive signal from §4f}   (line omitted entirely when there is no real signal)

Standup ({n} active problems)
  {identifier} — {title}   [{state}]   {x/y units done | milestone %}
     in flight: {unit(s) currently started, or "—"}
     blocked:   {open blocked-by, or "none"}
  …
```

Group problems under their engagement (Initiative) or Project where promoted. Keep it
scannable — this is a glance, not a dump. The `Bright spot:` line (§4f) is **gated** — it
prints only on real signal (a milestone just closed, or a standout graph positive) and is
omitted entirely on a routine standup, so the glance stays a glance.

## 6. Stop

This command **only reports** about the in-flight work — the Project description refresh
in step 4 is the single intentional write, and it is idempotent. The command never
changes state, posts comments, or dispatches a developer — reach for `/backlogd:scope`
to shape a problem and `/backlogd:solve` to act on one.
