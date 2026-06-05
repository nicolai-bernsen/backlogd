# Linear object model — reference

What each Linear primitive *is*, and how backlogd's concepts map onto them. This is the
concept reference behind [`../SKILL.md`](../SKILL.md); read it when you're unsure what a
Linear term means. For the tools and call rules, see
[`linear-mcp.md`](linear-mcp.md).

## The primitives

Linear has a small, deliberately opinionated object model. The load-bearing unit is the
**Issue** — almost everything else either *contains* issues, *groups* them, *time-boxes*
them, or *relates* them.

| Primitive | Role | What it is |
| --- | --- | --- |
| **Workspace** | container (top) | The whole org. Holds teams, initiatives, and all data. |
| **Team** | container | A unit that owns its own workflow states, labels, cycles, and triage. **Every Issue belongs to exactly one team.** backlogd uses one team. |
| **Initiative** | grouping (hand-curated) | A hand-curated list of Projects representing a goal — membership is curated by hand, not auto-populated (the Initiative *record* is MCP-writable via `save_initiative`; see [`linear-mcp.md`](linear-mcp.md)). In backlogd an **Initiative = a consulting engagement**, grouping that engagement's problem-Projects. |
| **Project** | container + grouping | A unit of work with a **clear outcome and an end** — it is meant to *close*. Has a progress graph, health, updates, and milestones. **A Project is not an epic.** |
| **Project Milestone** | grouping (inside a Project) | A meaningful **phase** of one Project (e.g. Alpha → Beta). Completion = % of its issues done. This is how backlogd represents phases. |
| **Issue** | the atomic unit | A single task with a clear outcome. Needs only a title + state. Belongs to one team; optionally to one project, milestone, cycle. |
| **Sub-issue** | parent/child relation | An Issue whose parent is another Issue. Use only for work "too big for an issue, too small for a project." Roughly one level — don't build deep trees. |
| **Cycle** | time-box | A repeating sprint window. **backlogd does not use cycles in its core loop** (continuous flow). |

Key distinctions for an agent:

- **Project ≠ epic.** It's bound to an outcome and should close. A long-lived "all the
  work" project is an anti-pattern — its progress graph never resolves. backlogd uses
  **one Project per substantial problem**.
- **Milestone = a phase inside one Project**, not a date marker that owns issues
  exclusively. An issue is *assigned to* a milestone but still lives in the project.
- **Cycle is the only time-box** and is orthogonal to projects. backlogd skips it.

## Issue relations

| Relation | Meaning | backlogd use |
| --- | --- | --- |
| **blocks / blocked-by** | Directional hard dependency: "A blocks B" ⇔ "B is blocked-by A". | **The only blocker signal.** Model every real dependency this way. The scrum-master detects stalls from open `blocked-by`. |
| **related** | Non-directional "see also". No effect on scheduling or progress. | Cross-link for context only — **never** for a true dependency. |
| **duplicate** | Marks an issue as a duplicate of another; moves it to the `duplicate` state. | Mark rediscovered work; never delete it (history + links survive). |
| **parent / sub-issue** | Hierarchical "part of". Optional auto-close: parent closes when all sub-issues do. | Decompose one chunky issue. Promote to a Project instead of nesting deeply. |

## Workflow state categories (the load-bearing rule)

Workflow states are per-team and their **display names are customisable**, but every state
belongs to one fixed **category** (`type`). Categories — not names — drive progress math,
"active" detection, and automations. **Always reason about the category, never the
display name.**

| Category (`type`) | Meaning | Counts as "active"? |
| --- | --- | --- |
| `triage` | Unreviewed inbox (opt-in). | No |
| `backlog` | Captured, not committed. | No |
| `unstarted` | Committed, not begun (e.g. "Todo"). | **Yes** |
| `started` | In flight (e.g. "In Progress", "In Review"). | **Yes** |
| `completed` | Done. | No |
| `canceled` | Abandoned. | No |
| `duplicate` | Reserved; auto-applied when marking a duplicate. | No |

- "Active" = `unstarted` ∪ `started`.
- Progress everywhere = **% of issues in the `completed` category** — not a state literally
  named "Done". If a custom state is added, it must sit in the right *category* or progress
  and rollover break.

## Other fields

| Field | Notes for an agent |
| --- | --- |
| **Labels** | Team-scoped. `problem` is backlogd's pickup trigger. Prefer Linear's native fields over inventing label taxonomies. |
| **Priority** | Fixed enum: Urgent / High / Medium / Low / None (`1`–`4`, `0`). Scrum-master orders pickup by it. |
| **Estimate** | Opt-in points. If estimates are off, every issue counts as 1 point — fine for backlogd's one-at-a-time loop. |
| **Assignee** | One per issue. Sub-issues may be assigned independently. |
| **Due date** | A hard external date — distinct from cycle/project dates. Use sparingly; use `blocked-by` for internal ordering, not due dates. |
| **Project status** | The Project's own state category (Backlog / Planned / **In Progress** / Completed / Canceled). The progress graph starts once a Project is `started`. |
| **Project health** | A manual signal on each Project Update: **On track / At risk / Off track** (goes "Update-missing" when stale). The scrum-master's fastest health read. |
| **Project Update** | A structured post (health + rich-text body). The idiomatic, richest "report back" surface — preferred over a comment in the Project form. |

## How progress is computed

- **Milestone progress** = % of its issues in the `completed` category.
- **Project progress** = a graph (Scope / Started / Completed) that begins once the project
  is `started`; it can predict a completion date from velocity. Watch the **Scope** line for
  creep.
- **Cycle progress** = burndown — **not used by backlogd** (no cycles).
- **Scope** = sum of estimates (or issue count when estimates are off).

What the scrum-master should poll, in order: **project status category → health → open
`blocked-by` → state-category counts → latest Project Update → milestone %.**

## backlogd → Linear terminology

| backlogd concept | Linear primitive |
| --- | --- |
| **Problem** (filed by the product owner) | An **Issue** labelled `problem` — promoted to its own **Project** once it's substantial (see SKILL.md). |
| **Decomposition / the work** | **Sub-issues** (Issue form) or **Issues in the Project** (Project form), via `save_issue` `parentId`. |
| **Phase** of a solution | A **Project Milestone** — never an epic/feature/story nesting. |
| **Blocker** | A **`blocked-by`** relation (plus a note in the summary comment). |
| **Progress / "what's done"** | Workflow-state **categories** + the issue **description** (canonical) + (Project form) the **progress graph**. |
| **Status report / result** | A single agent-owned **comment** edited in place, and (Project form) a **Project Update** with **health**. |
| **Pickup queue** | Issues carrying the **`problem`** label, ordered by state then priority. |
| **Engagement** (groups its problems) | An **Initiative** — groups that engagement's problem-Projects (🎯 auto-attach not yet wired). |
| **Sprint / cadence** | None — **continuous flow**, no **Cycles**. |
