# Documents, health updates & release summaries (write helpers)

The `mcp__linear__*` write recipes backlogd's orchestrator commands use to land three
non-Issue surfaces in Linear — **Project Documents**, **project-thread health updates**,
and **release "Shipped" summaries**. Each helper is an **idempotent upsert** keyed by a
stable marker so a re-run updates in place instead of duplicating. Surface verified
**2026-05-28**; re-verify before relying on a parameter you haven't used recently (see
[`linear-mcp.md`](linear-mcp.md) for the discipline).

> **Orchestrator-owned.** These helpers are called by `/backlogd:scope`, `/backlogd:solve`,
> `/backlogd:review`, and `/backlogd:release` — **not** by the `backlogd:developer`. The
> developer's tool grant is unchanged (`get_issue` / `list_comments` / `save_comment` on
> its own issue only); these helpers stay on the scrum-master side of the boundary.

The load-bearing MCP rules from [`linear-mcp.md`](linear-mcp.md) all apply:

- **Read → capture `id` → write.** `save_*` without an `id` always *creates*. Before every
  update, list / get the record first, capture its `id`, and pass that `id` back.
- **Real newlines, never literal `\n`** in `content` or `body` — Markdown renders directly.
- **Identity cache** (`.backlogd/identity.json`, 24-hour TTL) — read it on entry, don't
  re-fetch team / statuses / labels per call.
- **Page narrowly** — filter `list_*` by the parent id and keep `limit` modest.

## 1. Project Documents — `save_document` upsert

backlogd attaches **one Document per role per Project**. Two roles are defined today:

| Role | Title (canonical) | Icon | Owner | Lives until |
| --- | --- | --- | --- | --- |
| **Spec** | `Spec` | `:memo:` | `/backlogd:scope` writes; refreshed on re-scope | Project closes |
| **Solution brief** | `Solution brief` | `:white_check_mark:` | `/backlogd:solve` (at In Review) and `/backlogd:review` (on accept) | Project closes |

### Call shapes

**Create** (no `id` → new document; required parent is `project`):

```text
save_document({ project: "<project id or slug>", title: "Spec", content: "<markdown>", icon: ":memo:" })
```

**Update in place** (pass `id` → partial update; only `content` changes):

```text
save_document({ id: "<document id>", content: "<markdown>" })
```

**Find existing** (the list filter is `projectId`, not `project`):

```text
list_documents({ projectId: "<project id>" }) → match on title === "Spec" (or "Solution brief")
```

### The `project` / `projectId` asymmetry

This is the footgun. The **write parent** on `save_document` is **`project`** (accepts id
or slug); the **list filter** on `list_documents` is **`projectId`** (id only). Same
concept, two different parameter names depending on the call direction. Bake it into the
helper — don't try to remember it ad hoc.

### Idempotent upsert procedure

1. **Resolve the Project id** for the current problem.
2. **List** existing documents: `list_documents({ projectId })`.
3. **Match** by exact title (`"Spec"` / `"Solution brief"`).
4. **If matched** → capture the document `id` → call `save_document({ id, content })`.
5. **If not matched** → call `save_document({ project, title, content, icon })` to create.

Re-running the helper is safe by construction: step 3 finds the document next time, and
step 4 updates in place. Never write a "Spec (2)" — that's the signal something skipped
the list call.

## 2. Project health updates — project-thread comments

> **Prefer the typed `save_status_update` for new health writes (re-verified 2026-06-05).**
> The Linear MCP now exposes `save_status_update({ type: "project" | "initiative", health,
> body })` — the typed write surface for the Project/Initiative Update panel, and the *only*
> path for **initiative** health. See [`linear-mcp.md`](linear-mcp.md) → *Project Updates &
> health*. The project-thread-comment shape below is the **legacy fallback**; write health
> **one** way per transition — never the comment *and* `save_status_update` for the same
> event, or the thread and the Update panel disagree.

**There is no native Project-Update write on `save_project`** — it has no `health` field,
and there is no `save_project_update` tool. The Project Updates panel in the Linear UI was
not exposed for writes when this comment shape was built (2026-05-28); the typed
`save_status_update` surface above superseded that gap (2026-02-05 Linear MCP release,
re-verified 2026-06-05).

**The comment path** is a comment on the **project thread**:

```text
save_comment({ projectId: "<project id>", body: "<health update markdown>" })
```

### Body shape

Every backlogd-authored health comment follows the same shape so the scrum-master can
detect, dedupe, and update it:

```markdown
**[backlogd]** Health: <on track | at risk | off track>

<one to three lines of narrative — what changed, why the health is what it is>

<!-- marker: <claim | blocked | handback | milestone:<name>> -->
```

- **Badge** (`**[backlogd]**`) — distinguishes scrum-master-authored comments from PO /
  developer / Linear-native ones. Stable, never localised.
- **`Health:` lead line** — `on track` / `at risk` / `off track`, lowercase, matching the
  three values Linear's own Project Update widget exposes (the panel still has to be
  filled by hand for now; this comment carries the same information at the project-thread
  level).
- **Trailing transition marker** — one of `claim` / `blocked` / `handback` /
  `milestone:<name>`. Encodes *what happened* so a re-run can find this comment again and
  edit it instead of posting a new one.

### Milestone-completion variant

When a milestone closes, post on the **milestone thread** (not the project thread):

```text
save_comment({ milestoneId: "<milestone uuid>", body: "**[backlogd]** Milestone <name> complete — <narrative>\n\n<!-- marker: milestone:<name> -->" })
```

Resolve milestone names to ids via `list_milestones({ project })` first.

### Health derivation rules

Health is **derived from existing stall signals**, not a new piece of state the
scrum-master invents:

| Health | Trigger |
| --- | --- |
| **on track** | No open `blocked-by`, recent forward motion, no stalled units. |
| **at risk** | One open `blocked-by` *or* a single stalled unit *or* a milestone slipping. |
| **off track** | Multiple open `blocked-by`, repeated rework, or a Project past its target. |

Reuse the stall-detection logic the scrum-master already runs in `/backlogd:status` — do
not duplicate the rules per command.

### Idempotency by marker dedupe

> **Verified live 2026-06-03 ([ADR-008](../../../docs/standards/adrs/ADR-008-live-surface-verification.md)).**
> `list_comments({ projectId })` lists the project thread — a probe returned the prior
> `**[backlogd]**`-badged comments by their trailing markers, so project-thread marker-dedupe
> works. (This corrects the 2026-05-28 [`linear-mcp.md`](linear-mcp.md) snapshot's
> `issueId`-only reading, which was itself an unverified assumption.)

1. **List** existing comments on the project thread:
   `list_comments({ projectId, orderBy: "updatedAt", limit: <small> })`.
2. **Filter** to comments whose body starts with `**[backlogd]**`.
3. **Match** on the trailing `<!-- marker: ... -->` value.
4. **If matched** → capture the comment `id` → call `save_comment({ id, body })`.
5. **If not matched** → create with `save_comment({ projectId, body })`.

A claim comment (`marker: claim`) is updated; it never becomes a second claim comment.

## 3. Release "Shipped" summaries

When `/backlogd:release` cuts a tag, it posts a per-issue Shipped summary so each closed
problem records *which release shipped it*, and (where applicable) rolls the summary up
to the Project / Initiative.

### Per-included-issue comment

```text
save_comment({
  issueId: "<NB-N>",
  body: "**[backlogd]** Shipped in vX.Y.Z — <gh release url>"
})
```

- One-line body keeps the issue's comment history tidy.
- `Shipped in vX.Y.Z` is the **stable marker** — the dedupe key for the upsert (versions
  never collide).

### Project / Initiative roll-up

Where the release touches **one** Project or Initiative, post a single roll-up so the
container records the same fact:

```text
save_comment({ projectId: "<project id>",       body: "**[backlogd]** Shipped in vX.Y.Z — <gh release url>" })
save_comment({ initiativeId: "<initiative id>", body: "**[backlogd]** Shipped in vX.Y.Z — <gh release url>" })
```

`save_comment` accepts exactly one parent — `issueId | projectId | initiativeId |
documentId | milestoneId` — so roll-ups are independent calls, not multi-target writes.

### Idempotency by `Shipped in vX.Y.Z` marker detection

1. **List** existing comments on the target (`list_comments({ issueId | projectId |
   initiativeId })`). The **`issueId`** and **`projectId`** filters are **verified live
   2026-06-03** (ADR-008 — see the note under *Project health updates*); `initiativeId` is
   the same parent family but was not separately probed — re-verify if a release ever rolls
   up to an Initiative.
2. **Filter** to bodies containing `Shipped in vX.Y.Z` *for the exact version being cut*.
3. **If matched** → skip (the release already wrote this comment; do not edit the URL).
4. **If not matched** → create with `save_comment({ <parent>, body })`.

Skipping rather than editing is intentional — release summaries are an audit record, not
a working comment. A re-run of `/backlogd:release` for the same version is a no-op on the
comment surface; only a *new* version posts new summaries.

## Pitfalls

- ❌ `save_document({ project, ... })` with no upstream `list_documents` → second run
  creates a duplicate document. ✅ List by `projectId`, match by title, capture `id`,
  pass `id` back.
- ❌ Confusing `project` (write parent) with `projectId` (list filter) → schema-validation
  error on one call or the other. ✅ Both are the same concept; just match the parameter
  name to the tool.
- ❌ Trying to write a Project Update directly (`save_project_update`, `save_project({
  health })`) → no such surface. ✅ Use `save_comment({ projectId })` with the
  `**[backlogd]** Health:` body shape.
- ❌ Posting a fresh health comment every status pass → noisy project thread, broken
  dedupe. ✅ Find the prior comment by `marker`, update it in place.
- ❌ Editing a `Shipped in vX.Y.Z` comment after the fact → mutates an audit record.
  ✅ Treat them as immutable; only post once per version per target.
- ❌ Hardcoding state / milestone names to derive health → breaks when a team renames a
  state. ✅ Derive from `type` / blocked-by counts (the rules above).
