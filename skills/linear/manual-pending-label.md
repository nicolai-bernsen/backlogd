---
name: linear-manual-pending-label
description: Keep the team's `manual-pending` label in sync with each active problem's `[manual]`-AC state — the signal layer the PO "Waiting on me" saved view filters on. Ensure-label idempotently, re-evaluate per-issue from the unit's `[manual]` acceptance-criteria bullets (parsed by the `extract_kind` normalize-then-match rule), and attach/detach with no console churn. Scope-guarded to issues carrying the `problem` label. Loaded by `/backlogd:scope`, `/backlogd:review`, and `/backlogd:status` at the point they already inspect a problem.
---

# Linear — auto-managed `manual-pending` label

`/backlogd:scope`, `/backlogd:review`, and `/backlogd:status` keep a `manual-pending` label
on the team in sync with each active problem's **`[manual]`-acceptance-criteria state**. The
label is the **signal layer** the PO "Waiting on me" saved view filters on, so the product
owner sees — at a glance, without clicking into any issue — exactly which problems carry a
human-only check (`[manual]` AC) that is the gate between a green run and *needs you*.

This skill describes the algorithm — load it from the three commands at the point they
already inspect a problem (its description and `## Acceptance Criteria`). It is a direct
re-application of the proven `blocked`-label pattern (`skills/linear/blocked-label.md`):
same ensure/attach/detach shape, same scope guard, same idempotency contract — only the
*desired state* differs (a `[manual]` AC instead of an open `blocked-by`).

> **Prerequisite reads.** `skills/linear/SKILL.md` (operating model),
> `skills/linear/references/linear-mcp.md` (exact `mcp__linear__*` calls), and
> `skills/ac/SKILL.md` (typed-AC grammar + the `extract_kind` normalize-then-match rule;
> reference impl `scripts/ac_parse.py`). Resolve workflow states by `type`, never display
> name; `save_*` is upsert (read → capture `id` → write); identity is cached in
> `.backlogd/identity.json`.

## Scope

- **Only `problem`-labelled issues.** Never touch an unrelated, non-`problem` issue.
- **Only active states.** Only re-evaluate when the target issue's state `type` is
  `unstarted` or `started`. Skip `backlog`, `completed`, `canceled`.
- **The unit that carries the `[manual]` AC.** Evaluate and label **per unit**, on the issue
  / sub-issue / Project-Spec-Document unit whose own `## Acceptance Criteria` holds the
  `[manual]` bullet — never a decomposed problem's container, consistent with how `blocked`
  and `agent:*` are placed per-unit. A parent that decomposed its work into sub-issues holds
  no AC of its own and so is never labelled by this skill; each sub-issue is evaluated on its
  own AC.

If either of the first two guards fails, **do nothing** — neither add nor remove
`manual-pending`.

## Step 1 — Ensure the `manual-pending` label exists on the team (idempotent)

Resolve the label from the cached identity (`.backlogd/identity.json` → `labels[]`). If
`manual-pending` is not in the cache:

1. `list_issue_labels({ team, name: "manual-pending" })` to confirm absence (the cache may
   be stale).
2. If still absent, create it:

       create_issue_label({
         team,
         name: "manual-pending",
         color: "#F2994A",
         description: "Auto-applied by backlogd when an active problem has a [manual] acceptance-criterion awaiting PO confirmation."
       })

   `color` is suggested amber (a "waiting on a human" hue, distinct from the `blocked` red);
   if the MCP rejects a specific shade, omit `color` and let Linear assign the default — the
   name is what matters.
3. The new label's `id` lands in the cache the next time the identity refreshes (24-hour
   TTL); a forced refresh is unnecessary for this run.

If `manual-pending` is already in the cache, **skip the calls above** — re-confirming on
every invocation costs GraphQL complexity for a value that almost never changes. (This is
the same created-on-write / never-assume-pre-existence contract `blocked` uses; no API key
or non-MCP path is introduced — `create_issue_label` / `list_issue_labels` / `save_issue`
are all official Linear MCP calls, OAuth-as-the-user.)

## Step 2 — Re-evaluate one unit

Given a target unit (the issue / sub-issue you are already reading in the calling command):

1. **Guard** — confirm the unit carries the `problem` label and its state `type` is
   `unstarted` or `started`. If not, return — leave the labels untouched.
2. **Read its acceptance criteria.** Use the `description` you already have from the calling
   command's `get_issue` read — do not re-fetch. Take the `- [ ]` / `- [x]` bullets under
   the `## Acceptance Criteria` heading.
3. **Decide the desired state — parse, don't substring-match.** For each AC bullet, take the
   text *after* the `- [ ]` / `- [x]` checkbox and run it through the **`extract_kind`
   normalize-then-match rule** from `skills/ac/SKILL.md` (reference impl
   `scripts/ac_parse.py` → `extract_kind` → `(kind, body)`). This **normalizes Linear's
   stored forms first** — unwrap a leading inline code span (`` `[manual]` `` → `[manual]`)
   and markdown-unescape a leading bracket escape (Linear stores an authored `[manual]` as
   `\[manual\]`) — **then** matches `^\[(test|manual|review)\] ` (single trailing space). The unit <!-- markdownlint-disable-line MD038 -->
   **has-a-`[manual]`-AC** iff at least one bullet's extracted `kind` is `manual`.

   > **Why not a naive `[manual]` substring scan?** Linear escapes the leading `[` when it
   > stores a description, so the on-the-wire text reads `\[manual\]`; a bare
   > `contains("[manual]")` would miss it (and the feature would be silently inert), while a
   > `contains` on the escaped form would be brittle and could false-match a `[manual]`
   > appearing mid-body. Mirror `extract_kind` exactly — the same rule the reviewer applies
   > when it walks the AC — so a bullet counts as `[manual]` only when the *leading tag* is
   > `[manual]`, never an incidental occurrence in body text.

4. **Read the current labels** off the unit you already have.
5. **Apply the delta — idempotent on both ends.** Decide by the desired state vs. the
   current `labels` array:

   | Desired | `manual-pending` in `labels`? | Action |
   | --- | --- | --- |
   | has `[manual]` AC | yes | no-op |
   | has `[manual]` AC | no | `save_issue({ id, labels: [...labels, "manual-pending"] })` |
   | no `[manual]` AC | yes | `save_issue({ id, labels: labels.filter(l => l !== "manual-pending") })` |
   | no `[manual]` AC | no | no-op |

   The `labels` parameter accepts names or ids; pass the existing labels back verbatim
   alongside the add/remove of `manual-pending` so the upsert does not drop unrelated labels
   (`problem`, `kind:*`, `agent:*`, `blocked`). Reference the label by **name**
   (`"manual-pending"`) — Linear's MCP resolves it on the team you already pinned via
   identity.

## Idempotency contract

- Re-running any of the three commands on the same unit with the same `[manual]`-AC shape is
  a **no-op** — neither add nor remove fires.
- A `[manual]` AC being added to a problem (or an existing bullet being retyped *to*
  `[manual]`) triggers the **add** path on the next invocation; nothing else changes.
- The last `[manual]` AC being removed or retyped away from `[manual]` triggers the
  **remove** path on the next invocation; nothing else changes.
- A `problem` unit with no `[manual]` AC at all is never labelled `manual-pending` — the
  desired state is "no `[manual]` AC" and the no-op row applies.
- **Confirmation is not text** — confirming a `[manual]` check at review does *not* edit the
  bullet's `[manual]` tag, so the desired state stays "has a `[manual]` AC" by this skill's
  parse alone. The **clear-on-accept** transition is owned by `/backlogd:review` (see below):
  it removes the label as part of the `accepted` close, when every `[manual]` is confirmed
  **MET** and zero **AWAITING-PO** dangle. This skill's pure-AC parse keeps the label
  attached for the whole life of the unit's `[manual]` AC; `review`'s accept is the one
  place it comes off.

## Where to call this from

- **`/backlogd:scope`** — at the **same step-5 insertion point** it runs the `blocked`-label
  helper (after the issue is shaped and saved, alongside any sub-issues just created). Run
  this skill per `problem`-labelled unit the refiner produced; the desired state is "the
  unit's AC carries ≥1 `[manual]` bullet" by the `extract_kind` parse. **Apply** the label
  on units that do.
- **`/backlogd:review`** — on the verdict close. **Clear** the label on the **`accepted`**
  path — the verdict where every `[manual]` is confirmed **MET** and zero **AWAITING-PO**
  remain — by taking the remove path explicitly on the unit (drop
  `manual-pending` from its `labels`). While any `[manual]` is still
  **AWAITING-PO** (the `needs you` verdict), **leave the label attached** —
  that *is* the "waiting on me" state. (`sent back` / `block` leave the unit's AC unchanged,
  so the label state is unchanged too — no write.)
- **`/backlogd:status`** — in the survey, on every `problem`-labelled unit in scope at the
  point the command already reads the issue. `status` is otherwise read-only; this is the
  same deliberate carve-out for the *signal layer* that the `blocked` label already has.
  Re-evaluate per Step 2 and apply at most one `save_issue` per unit; the console standup
  output is unchanged.

Each caller passes the unit (with its `labels` and the `description` / AC it already read)
to this skill. The skill writes at most one `save_issue` per unit per invocation; when the
desired state already matches the current labels, no Linear write fires at all.
