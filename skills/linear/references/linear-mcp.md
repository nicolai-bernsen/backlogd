# Linear MCP usage — reference

The exact `mcp__linear__*` tools backlogd uses and the rules that keep automated reads and
writes correct. Read this **before every write**. For what the concepts mean, see
[`linear-model.md`](linear-model.md); for the policy, see [`../SKILL.md`](../SKILL.md).

> **Surface snapshot: 2026-05-28.** The Linear MCP server (configured in `.mcp.json` at the
> repo root) can change upstream. Tool names and parameters below reflect that date.
> **Re-verify** before relying on a parameter you haven't used recently: list the server's
> tools (they surface as `mcp__linear__*`) and check the live parameter schema, and consult
> Linear's own MCP documentation at the server URL in `.mcp.json`. Treat this file as a
> guide, not a contract.
>
> For the write recipes covering Project Documents, project-thread health updates, and
> release "Shipped" summaries, see
> [`documents-and-updates.md`](documents-and-updates.md) — the orchestrator-owned helpers
> built on the surface below.

## Tool surface (the subset backlogd uses)

| Area | Tools | Key parameters |
| --- | --- | --- |
| **Issues** | `list_issues`, `get_issue`, `save_issue`, `list_issue_statuses`, `get_issue_status` | `list_issues`: `label`, `state`, `team`, `project`, `parentId`, `priority`, `query`, `orderBy`, `limit`, `cursor`. `get_issue`: `id`, `includeRelations`. `save_issue`: see below. `list_issue_statuses`: `team` (required) → `[{id, type, name}]`. |
| **Comments** | `list_comments`, `save_comment` | `list_comments`: `issueId`. `save_comment`: `body`, exactly one of `issueId`/`projectId`/`milestoneId`/…, `id` (to edit), `parentId` (to reply). |
| **Projects** | `list_projects`, `get_project`, `save_project` | `list_projects`: `team`, `query`, `includeMilestones`. `save_project`: project fields incl. state/health (re-verify exact keys before writing — see "Project Updates & health"). |
| **Milestones** | `list_milestones`, `get_milestone`, `save_milestone` | `list_milestones`: `project` (required). `save_milestone`: `name`, `project`, target date. |
| **Documents** | `list_documents`, `get_document`, `save_document` | `list_documents`: `projectId`. `save_document` (create): `project`, `title`, `content`, `icon`. `save_document` (update): `id`, `content`. **Asymmetry: write parent is `project`, list filter is `projectId`** — same concept, two parameter names. See [`documents-and-updates.md`](documents-and-updates.md). |
| **Labels** | `list_issue_labels`, `create_issue_label` | `list_issue_labels`: `team`, `name`. |
| **Teams / users** | `list_teams`, `get_team`, `list_users`, `get_user` | `list_teams`: `query`. |
| **Cycles** | `list_cycles` | `teamId` (required). **Not used in the core loop** (no cycles). |

`save_issue` is the workhorse. Relevant parameters:

- **Create vs update:** omit `id` → **create** (then `title` + `team` are required); pass
  `id` → **partial update** (only the fields you pass change).
- **Placement:** `team`, `project`, `parentId` (sub-issue), `cycle`, `milestone`,
  `assignee` (id / name / email / `"me"`), `priority` (`0`–`4`), `labels` (names or ids),
  `state` (type / name / id), `estimate`, `dueDate`.
- **Relations (append-only):** `blockedBy`, `blocks`, `relatedTo` (arrays of identifiers);
  `duplicateOf`; and the inverse removers `removeBlockedBy`, `removeBlocks`,
  `removeRelatedTo`. Relations are set **on the issue** — there is no separate relation tool.
- **`delegate`:** ignore — that's the Agents-platform surface, out of scope.

## backlogd-owned label families

A few label name patterns are **owned by backlogd** — its commands read and write them as
part of the loop. Treat them as reserved; don't reuse the prefixes for unrelated
workspace labels.

| Family | Owner | Meaning |
| --- | --- | --- |
| `problem` | PO files / backlogd reads | The opt-in pickup signal — backlogd only picks up issues carrying this label. |
| `agent:<suffix>` | `/backlogd:scope` writes / `/backlogd:solve` reads | The picked specialist developer for an issue (`agent:docs` → `developer-docs`). PO can flip the label to override. Created on first use (Linear's MCP auto-creates labels passed in `save_issue.labels`). See `docs/specialists.md`. |

## Load-bearing rules

### 1. Resolve identity before you write

State display names are team-scoped and customisable — there is no guaranteed "In
Progress". Before any state change:

1. `list_teams` → resolve the user's team for this run. backlogd assumes one team per
   workspace; the call returns the user's team(s) and the run picks the right one. Don't
   hardcode a team name — every installer is on their own.
2. `list_issue_statuses({ team })` → get `[{id, type, name}]`. **Match on `type`**
   (`unstarted`/`started`/`completed`/…), never on the display name. When a target type has
   more than one state (e.g. `started` = "In Progress" + "In Review"), pick the
   **lowest-position** one for a forward transition.
3. `list_issue_labels` / `list_users` as needed.

> **Note — pre-load deferred tools first (NB-346).** Every `/backlogd:*` command's §0
> step batches a `ToolSearch` call across the canonical `mcp__linear__*` tool list
> *before* this identity-resolution step runs. The pre-load loads the deferred tools
> into the parent's context so a subagent dispatched with an explicit `tools:` list
> receives them at runtime — see `../SKILL.md` → *Deferred tools — pre-load before
> dispatch* for the canonical list and the batched call shape. The identity-resolution
> calls below (`list_teams`, `list_issue_statuses`, `list_issue_labels`) also serve as
> the natural-invocation fallback if `ToolSearch` is unavailable: simply calling them
> here loads each into the parent's context for any later subagent dispatch.

#### Cache identity to `.backlogd/identity.json` (24-hour TTL)

These three `list_*` calls return values that are **stable across hundreds of runs** —
teams, workflow states, and labels rarely change — but the GraphQL layer has a
complexity cap (see "Page narrowly" below), so re-fetching them every invocation
compounds. **Cache the resolved identity** to a per-repo file with a TTL; on entry, read
the cache first and only re-fetch when it is missing or stale.

**Location.** `.backlogd/identity.json`, relative to the repository root (the `.backlogd/`
directory is gitignored, so the cache never enters the public tree).

**Schema.** Top-level keys are exactly:

```json
{
  "team": { "id": "<uuid>", "name": "<team name>" },
  "statuses": [
    { "id": "<uuid>", "name": "Backlog",     "type": "backlog" },
    { "id": "<uuid>", "name": "Todo",        "type": "unstarted" },
    { "id": "<uuid>", "name": "In Progress", "type": "started" },
    { "id": "<uuid>", "name": "In Review",   "type": "started" },
    { "id": "<uuid>", "name": "Done",        "type": "completed" },
    { "id": "<uuid>", "name": "Canceled",    "type": "canceled" }
  ],
  "labels":   [ { "id": "<uuid>", "name": "problem" }, ... ],
  "expires_at": "<ISO-8601 UTC, 24h from write>"
}
```

**Procedure (each backlogd command on entry, before any other Linear call).**

1. **Read** `.backlogd/identity.json`. If the file exists, parse it and compare
   `expires_at` to *now* (UTC). If `expires_at` is in the future, the cache is **fresh** —
   use `team`, `statuses`, and `labels` from it directly and **skip** the three `list_*`
   calls below.
2. **Repopulate** if missing, unparseable, or stale: call `list_teams` →
   `list_issue_statuses({ team })` → `list_issue_labels({ team })`, project them into the
   schema above, set `expires_at` to *now + 24 hours* (ISO-8601, UTC, e.g. emitted by
   `date -u --iso-8601=seconds`), and **rewrite** `.backlogd/identity.json` (overwrite the
   whole file — it's a snapshot, not append-only). Create the `.backlogd/` directory if it
   does not exist.
3. **Resolve roles** from the cached `statuses` exactly as before — match on `type`, never
   on display name. The cache stores the raw `{id, name, type}` triples, not the role
   labels (pickup / review / accepted / …), so command-specific role resolution stays in
   each command's prose.

**Manual invalidation.** Delete `.backlogd/identity.json` to force a refresh on the next
run. Do this if you rename a workflow state, add a label backlogd should know about, or
otherwise reshape the team's Linear identity inside the 24-hour window — the cache will
not pick it up until it expires or you remove the file.

**Best-effort writes.** A failure to write the cache (e.g. read-only filesystem,
permission error) must **never** block the run — fall through with the freshly-resolved
identity for the current invocation, and try again next time.

### 2. `save_*` is upsert — read → capture `id` → write (idempotency)

This is the single biggest footgun. Calling `save_issue` (or `save_comment`,
`save_project`, …) **without an `id` always creates a new record.** A pickup loop that
re-runs and re-creates instead of updating will spawn duplicate issues and comments.

> **Rule:** before changing an existing record, `get_*`/`list_*` it first, capture its
> `id`, and pass that `id` back into `save_*`. Never write blind.

This makes the loop safe to re-run: a second pass updates in place instead of duplicating.

### 3. The description is canonical; comments are for narration

Linear comments are editable and **not reliable to read back** as state. Keep the
authoritative "what's done" in the issue **description** (`save_issue(id, description:…)`).
For progress narration, keep **one** agent-owned summary comment and **edit it in place**:
post once with `save_comment`, capture the returned comment `id`, and on later updates call
`save_comment(id, body:…)` rather than posting new comments. Don't scan free-form comments
to reconstruct state.

### 4. Project Updates & health

**Verified 2026-05-28: there is no native Project-Update write in the MCP.** `save_project`
has no `health` field and there is no `save_project_update` tool — the Project Updates
panel in the Linear UI is not currently exposed for writes. The path that works is a
project-thread comment via `save_comment({ projectId, body })` using the
`**[backlogd]** Health:` body shape (with a stable trailing transition marker for
idempotent dedupe). See
[`documents-and-updates.md`](documents-and-updates.md) for the exact body shape, health
derivation rules, and the milestone-completion variant. Re-verify on the snapshot date
before relying on this finding — if Linear ships a write surface, prefer it.

### 5. Git sync — let git events move state

backlogd's issues are linked to git by **branch name**. Use Linear's suggested branch name
(`nicolaibernsen/nb-<n>-<slug>` — it encodes the issue identifier), and put a **magic word**
in the PR (e.g. `Fixes`/`Closes` + the issue identifier). Linear then auto-transitions on
git events: **branch pushed → In Progress, PR opened → In Review, merged → Done.** Prefer
these events over redundant `save_issue(state:…)` calls — only set state via the API when
there is no corresponding git event. Before working an issue, check whether it already has
a linked branch/PR (and its state `type`) so a re-run resumes rather than redoes.

### 6. Send real newlines, never literal `\n`

`description` and `body` take **Markdown with literal newlines and characters** — do not
escape them. Emitting a literal backslash-`n` renders as broken markdown in Linear. (The
server's own instructions say the same.)

### 7. Page narrowly

The GraphQL layer under the MCP has a query-complexity cap. Filter `list_*` calls (by
`label`, `state`, `team`, `parentId`) and keep `limit` modest rather than fetching wide and
filtering client-side. Use `cursor` to page when needed.

### 8. Pure MCP client

backlogd talks to Linear only through `mcp__linear__*`. The Linear **Agents platform**
(agent `delegate`, agent sessions, webhooks, timing windows) is **out of scope** for v1 —
do not implement or depend on it.

## Pitfalls checklist

- ❌ `save_issue` with no `id` to "update" → **duplicate issue**. ✅ Read first, pass `id`.
- ❌ Transition by display name (`state: "In Progress"`) hardcoded → breaks if renamed.
  ✅ Resolve by `type`.
- ❌ Modelling a dependency as `relatedTo` → invisible to stall detection. ✅ Use
  `blockedBy`/`blocks`.
- ❌ Spamming a new progress comment each cycle → noise, unreliable history. ✅ One comment,
  edited in place by `id`; canonical state in the description.
- ❌ Literal `\n` in `body`/`description` → broken render. ✅ Real newlines.
- ❌ Redundant `state` writes that fight the git integration. ✅ Let push/PR/merge drive
  state.
- ❌ Wide `list_issues` with no filters → complexity-cap errors. ✅ Filter + small `limit`.
- ❌ Re-running `list_teams` / `list_issue_statuses` / `list_issue_labels` every invocation →
  paid GraphQL complexity for values that almost never change. ✅ Read
  `.backlogd/identity.json` first; only repopulate when missing/stale (24-hour TTL).
