---
description: One-time Linear workspace bootstrap — bring the team into backlogd's canonical shape (labels · workflow states · templates) by driving the local config engine. Opt-in, setup-only, key-free in the orchestrator; the engine reads the Admin key itself. Pass --dryrun to print the plan and touch nothing.
---

# /backlogd:init

You are the **scrum-master** for backlogd, in *bootstrap* mode. This is the **one-time,
opt-in setup pass** that brings a fresh Linear workspace into the canonical shape the
backlogd loop expects — the `problem` / `kind:ops` / `blocked` labels, the workflow-state
categories the forecast math reads, and the issue/project templates — so a new install is
correct-by-construction. The runtime loop (`scope` / `solve` / `status` / `review` /
`release`) stays **key-free / MCP-only**; this command is the *only* place a Linear
**personal API key (Admin scope)** is used, and it is used **by the engine, never by you**.

> **Key-free — load-bearing (AC).** You (the orchestrator) **never** load the API key value
> into your context. You do not read `~/.backlogd/credentials.env`, you do not echo it, you
> do not pass it on a command line. Every Linear *settings* write goes through one channel:
> you shell out to `python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/linear_setup.py" <verb> …` and
> the **engine reads the key itself** (from `$LINEAR_API_KEY`, else
> `~/.backlogd/credentials.env`) inside its network layer. The key never appears in any
> argument you build, in any output you print, or in any value you hold. If you ever find
> yourself about to `Read` the credentials file or interpolate a key into a command —
> **stop**; that is a contract violation.

**Approving the engine's writes (set the operator's expectation).** `init` makes its
label/state/template writes by shelling out to the engine — so in an **interactive** session
Claude Code **prompts the operator to approve** each `python … scripts/linear_setup.py …`
command (approve, or "don't ask again" to clear the rest of the run). That prompt *is* the
consent step; it is normal, not a wart. Running **unattended** (headless, or an
auto-approval/classifier mode), an agent **cannot self-authorize** a live write to a shared
workspace — the operator pre-allows the engine once with a
`Bash(python … scripts/linear_setup.py:*)` rule (e.g. via `/permissions`), or runs `init`
in a normal interactive session. Either way this is the **one-time setup only**; the runtime
loop reaches Linear via the MCP and prompts for nothing.

The engine is **`scripts/linear_setup.py`** (resolve it as
`${CLAUDE_PLUGIN_ROOT:-.}/scripts/linear_setup.py`, the same idiom `/backlogd:solve` uses
for `scripts/graph.py`). Its idempotent verbs are `audit`, `ensure-label`, `recase-label`,
`delete-label`, `ensure-state`, and `ensure-template`; each emits structured JSON to stdout
and is a no-op when the workspace is already canonical. Run it with the repo's Python — on
this repo's Windows host that is typically `python …`; fall back to `py -3 …` if `python`
is unavailable. Read each verb's JSON result rather than guessing from the exit code.

The team-resolution reads below go through the **Linear MCP server** (configured in
`.mcp.json`) — that is read-only identity resolution, not a settings write, and it carries
no key. **Load the `linear` skill (`skills/linear/`)** for the identity-cache procedure and
the `mcp__linear__*` calls. If the Linear MCP is not connected, you can still run the engine
verbs (they need only the team id and the engine's own key), but the cache-refresh in §4
needs it — note the degradation and continue.

> **New to backlogd setup?** Creating the Admin key and placing it at
> `~/.backlogd/credentials.env` is documented in
> [`docs/guides/workspace-bootstrap.md`](../docs/guides/workspace-bootstrap.md). Point the
> product owner there whenever the preflight in §0 fails.

## Flags

- **`--dryrun`** — run the preflight and the **audit only**, print the grouped plan, and
  **stop after §1**. No `ensure-*` / `recase-*` / `delete-*` verbs run; nothing is created,
  renamed, or deleted; the identity cache is left untouched. Reads (the audit and team
  resolution) are allowed. Accept the flag in **either position**
  (`/backlogd:init --dryrun`, `/backlogd:init --dryrun NB-…`, or trailing) — match
  `commands/solve.md`'s flag parsing: scan the arguments for `--dryrun`, remember the run is
  a dry run, then strip it and treat any remaining token as the team id/key override.

## 0. Pre-load deferred tools (NB-340 / NB-346)

**Before any other Linear operation in this command**, eagerly pre-load the Linear MCP
deferred tools. `/backlogd:init` dispatches no subagents and its only Linear writes are the
identity-cache reads in §1 and the cache invalidation in §4 (a local file write, not a
Linear write) — so the risk surface is smaller than `solve`/`review`. The pre-load is kept
anyway because keeping the §0 idiom **identical across all `/backlogd:*` commands** is the
contract (see `skills/linear/SKILL.md` → *Deferred tools — pre-load before dispatch*), and a
single batched call is cheaper than deferred-loading each tool on first use.

Make a **single batched `ToolSearch` call** that names the canonical Linear MCP tool list:

```text
ToolSearch(select: "mcp__linear__get_issue,mcp__linear__save_issue,mcp__linear__save_comment,mcp__linear__list_comments,mcp__linear__list_issue_statuses,mcp__linear__list_issue_labels,mcp__linear__list_issues,mcp__linear__list_teams,mcp__linear__list_milestones,mcp__linear__get_project,mcp__linear__save_milestone")
```

This command only *reads* via these (team / status / label resolution in §1) — but the
canonical list keeps every `/backlogd:*` command on the same idiom. `ToolSearch` is itself
read-only and safe under `--dryrun`. If `ToolSearch` is not available (a future Claude Code
version drops it), fall back to invoking each `mcp__linear__*` tool naturally from the
orchestrator's context (the §1 identity fallback calls `list_teams` /
`list_issue_statuses` / `list_issue_labels`).

## 1. Preflight — confirm the engine has a working, Admin-scoped key

Before showing any plan, prove the engine can talk to Linear with sufficient scope —
**without ever seeing the key yourself**.

1. **Resolve the team.** Read the per-repo identity cache first: if `.backlogd/identity.json`
   exists and its `expires_at` is in the future, use the cached `team` (id + key); otherwise
   call `list_teams` (Linear MCP) and pick the team. Remember its id/key as `$TEAM` — the
   engine's `--team-id` accepts either the id or the key. If the user passed a team token as
   the trailing argument, use that as `$TEAM` instead. (Full cache procedure + schema:
   `skills/linear/references/linear-mcp.md` → "Resolve identity before you write".)

2. **Confirm the credential store exists *without reading it*.** Check only for the
   **presence** of `~/.backlogd/credentials.env` (a `Test-Path` / `os.path.exists`-style
   existence check via Bash — never a `Read`, never `cat`), **or** that `LINEAR_API_KEY` is
   set in the environment. Do **not** open the file or print the env value. If **neither** is
   present, print the pointer below and **stop** — there is no key for the engine to use:

   > No Linear Admin key found. `/backlogd:init` needs a personal API key with **Admin**
   > scope, stored at `~/.backlogd/credentials.env` (or exported as `LINEAR_API_KEY`). See
   > [`docs/guides/workspace-bootstrap.md`](../docs/guides/workspace-bootstrap.md) to create
   > and place it, then re-run `/backlogd:init`.

3. **Prove the key works and is Admin-scoped — with a cheap read-only call.** Run the
   engine's read-only `audit` verb as the probe (it performs no writes):

   ```bash
   python "${CLAUDE_PLUGIN_ROOT:-.}/scripts/linear_setup.py" audit --team-id "$TEAM"
   ```

   - **Exit 0 + parseable JSON** → the key is valid and has enough scope to read labels,
     workflow states, and templates. Keep this JSON — it is the §1 audit plan, so you do not
     need to run `audit` twice. Continue.
   - **Non-zero exit** → read the engine's stderr `error:` line (it is key-safe by
     construction — the engine never puts key material in an error). Map it:
     - an HTTP **401 / authentication** error → the key is **missing or invalid**;
     - an HTTP **403 / forbidden / scope** error, or a GraphQL error naming a settings
       field the key may not reach → the key is present but **under-scoped** (not Admin);
     - "no Linear API key found …" → neither the file nor the env var resolved a key.

     In every failure case, print a short diagnosis plus the same pointer to
     [`docs/guides/workspace-bootstrap.md`](../docs/guides/workspace-bootstrap.md) (create
     an **Admin**-scope key; confirm it is at `~/.backlogd/credentials.env`), and **stop**.
     Do **not** proceed to confirm/apply on a failed preflight.

> The preflight doubles as the audit fetch: the `audit` JSON you just captured *is* the
> plan §1 renders. You shelled out once; the engine read the key once, inside itself; your
> context still holds no key.

## 2. Audit — render the plan, grouped

Parse the `plan` object from the §1 `audit` JSON. Its shape (from
`scripts/linear_setup.py`) is:

```json
{
  "verb": "audit",
  "team_id": "...",
  "plan": {
    "missing":    [ { "name": "kind:ops", "color": "#…", "description": "…" }, … ],
    "recase":     [ { "id": "…", "from": "Problem", "to": "problem" }, … ],
    "cruft":      [ { "id": "…", "name": "priority:high", "reason": "duplicates Linear's native Priority field" }, … ],
    "review":     [ { "id": "…", "name": "dx-size:M" }, … ],
    "state_gaps": [ "backlog", … ],
    "ok": false
  }
}
```

Show it to the product owner **grouped**, in this order, so the safe/destructive split is
obvious before anything runs:

- **Create** — canonical labels in `missing` that the engine will add
  (`problem` / `kind:ops` / `blocked` as applicable). *Safe / additive.*
- **Recase** — `recase` renames (e.g. `Problem` → `problem`), each preserving the label id
  and therefore its existing applications. *Safe.*
- **State gaps** — categories in `state_gaps` with no live workflow state; the engine can
  fill each additively (never rename/reorder/delete an existing state). *Safe / additive.*
- **Templates** — the **three** canonical templates (ADR-003) §3 will **ensure** (idempotent
  create-or-update): the `Problem` **issue** template (applies the `problem` label), the
  `backlogd problem` **project** template (Investigate → Implement → Verify milestones), and
  the `Spec` **document** template (`:memo:`). The engine's `audit` plan does not diff
  templates, so present these as "will ensure (idempotent)" rather than as a computed diff.
  *Safe / additive.*
- **Cruft to review** — `cruft` (the conservative recommend-delete set: `priority:*` labels
  that duplicate Linear's native Priority field, and unused default labels) plus `review`
  (other non-canonical labels the engine flags but does **not** recommend touching).
  **Destructive — nothing here runs without an explicit per-group yes in §2/confirm.**

If `plan.ok` is `true`, the workspace is already canonical for labels + states — say so
("Workspace already canonical — no label/state changes needed") and note that §3 will still
re-ensure the three templates idempotently (a no-op when they already match) unless this is a
`--dryrun`.

**`--dryrun` stops here.** Print the grouped plan, state explicitly that no verbs were run
and nothing was changed, and **stop** — do not enter §3 (Confirm) or beyond.

## 3. Confirm — safe set by default, destructive only on an explicit yes

Decide what will run. The split mirrors the engine's own safety model:

- **Safe / additive set — apply by default, no prompt:** every `missing` label (via
  `ensure-label`), every `recase` rename (via `recase-label`), every `state_gaps` fill (via
  `ensure-state`), and the three canonical templates (via `ensure-template`). These are
  idempotent and non-destructive; running them on an already-canonical workspace is a no-op.

- **Destructive set — ask per group, default NO:** the `cruft` deletions (and never the
  `review` list — that is informational only). Ask the product owner **per group** — group
  the cruft by `reason` (e.g. all `priority:*` "duplicates native Priority field" together;
  unused defaults together) and ask once per group, with the **default answer No**. Apply a
  group's `delete-label` calls **only** on an explicit yes for that group. A non-answer, an
  empty answer, or anything other than an affirmative leaves that group **untouched**.
  Never batch destructive deletes behind a single blanket yes, and never delete anything in
  `review`.

> **Nothing destructive without an explicit yes.** `delete-label` is the engine's only
> destructive verb; it runs only for a cruft group the product owner affirmatively approved
> in this step. If the product owner cannot be prompted in this run, treat every destructive
> group as **declined** and apply only the safe set.

## 4. Apply — run the confirmed verbs, report each outcome

Run the confirmed verbs by shelling out to the engine (key-free — the engine reads the key
itself). Resolve `$ENGINE = ${CLAUDE_PLUGIN_ROOT:-.}/scripts/linear_setup.py` and pass
`--team-id "$TEAM"` to every call. Read each verb's JSON result (`{"verb", "action", …}`)
and report the outcome; `action: "noop"` is a success, not a failure.

- **Create labels** — for each `missing` entry:

  ```bash
  python "$ENGINE" ensure-label --team-id "$TEAM" --name "<name>" --color "<color>" --description "<description>"
  ```

  (The engine fills canonical color/description defaults when you omit them for a known
  canonical label; passing the values from the audit plan is fine too.) Result `action` is
  `created` or `noop`.

- **Recase labels** — for each `recase` entry (`recase-label` finds the label by name and
  renames it to its canonical case, preserving the id):

  ```bash
  python "$ENGINE" recase-label --team-id "$TEAM" --name "<from>" --to "<to>"
  ```

  Result `action` is `updated` or `noop` (`reason: already_canonical` / `not_found`).

- **Fill state gaps** — for each `state_gaps` category, additively create one state in that
  category (additive only — the engine refuses to rename/reorder/delete existing states).
  Choose a sensible display name for the category (e.g. `backlog`→"Backlog",
  `unstarted`→"Todo", `started`→"In Progress", `completed`→"Done", `canceled`→"Canceled"):

  ```bash
  python "$ENGINE" ensure-state --team-id "$TEAM" --category "<category>" --name "<display name>"
  ```

  Result `action` is `created` or `noop`. (The engine validates the category against its
  canonical set — `backlog · unstarted · started · completed · canceled`; the two `started`
  display states and `duplicate` are not auto-created here, so flag any of those that are
  genuinely absent for the product owner to add in the UI rather than failing the run.)

- **Ensure templates** — create-or-update the **three canonical templates** (idempotent on
  `name`+`type`). The designed `templateData` bodies are **fixed by ADR-003** and encoded
  **once, in the engine** (`CANONICAL_TEMPLATES` in `scripts/linear_setup.py`) — the single
  source of truth. **Do not improvise the JSON inline here**: read each template's `type`
  and `templateData` from `CANONICAL_TEMPLATES` and pass that payload through verbatim, so
  the command and the engine never drift. The three are:

  | Name | `--type` | What it seeds (ADR-003 §3) |
  | --- | --- | --- |
  | `Problem` | `issue` | `## Problem` + `## Acceptance Criteria` body (typed-AC bullets); **applies the `problem` label** (encoded by name) so a templated issue is pickup-eligible by construction |
  | `backlogd problem` | `project` | Milestones **Investigate → Implement → Verify** (in order) + the one-line pointer description |
  | `Spec` | `document` | The `## Problem` / `## Approach` / `## Acceptance Criteria` body with the `:memo:` icon |

  ```bash
  python "$ENGINE" ensure-template --team-id "$TEAM" --name "Problem"          --type issue    --data "<CANONICAL_TEMPLATES['Problem'].templateData>"
  python "$ENGINE" ensure-template --team-id "$TEAM" --name "backlogd problem" --type project  --data "<CANONICAL_TEMPLATES['backlogd problem'].templateData>"
  python "$ENGINE" ensure-template --team-id "$TEAM" --name "Spec"             --type document --data "<CANONICAL_TEMPLATES['Spec'].templateData>"
  ```

  Result `action` is `created` or `updated`. (`--type document` is a valid template type
  and needs **no new verb** — `ensure-template` already forwards the freeform `templateData:
  JSON!`. If a template payload is rejected, report it and continue with the rest — do not
  abort the whole apply.)

  > **`templateData` is Linear's draft-entity shape, and the label is resolved by the
  > engine.** `templateData` is the *draft entity* a template pre-fills (e.g. an issue's
  > `title` / `priority` / `description` / `labelIds`), **not** the MCP create-args — the
  > engine encodes the shapes that actually render (NB-392). You pass the `Problem`
  > template's `problem` label through **by name** exactly as it sits in `CANONICAL_TEMPLATES`;
  > `ensure-template` resolves that name to the workspace's live label **id** at seed time
  > (so no per-workspace id is ever hardcoded). If the `problem` label does not yet exist,
  > the verb fails loudly naming it — so `ensure-label` runs **before** `ensure-template`.
  >
  > **Created ≠ renders.** Whether Linear actually *renders* the stored `templateData` is the
  > freeform-`JSON!` gap ADR-003 names — a `[manual]` fact only a human observing the Linear
  > UI can confirm (issue body + applied label; project milestones; document body + icon).
  > Verify each template visually in the Linear UI after this run.
  >
  > **No project label is seeded (ADR-003, deliberate).** Nothing in the loop reads a project
  > label, and the engine has no project-label write verb — so `init` ships none. A future
  > project label would require **adding a write verb to the engine first**; it is not a
  > silent omission. (See ADR-003 §2 + Consequences.)

- **Delete cruft** — **only** for groups the product owner affirmatively approved in §3:

  ```bash
  python "$ENGINE" delete-label --team-id "$TEAM" --name "<name>"
  ```

  Result `action` is `deleted` or `noop` (`reason: not_found`). Skip entirely for any
  declined or unprompted group.

Collect the per-verb outcomes (created / updated / recased / deleted / noop, and any
errors) for the §5 report. If an individual verb errors, surface its key-safe `error:` line
and continue with the remaining verbs — one failed label should not abort the rest.

## 5. Finish — invalidate the identity cache and summarise

1. **Invalidate the repo identity cache.** The recase in §4 may have renamed `Problem` →
   `problem`; the next backlogd run must re-resolve labels rather than trust a stale cache.
   **Delete `.backlogd/identity.json`** (a local file in the repo root — remove it if it
   exists; a missing file is fine) so the next `/backlogd:scope` / `solve` / `status`
   rebuilds it with the recased label. This is a local filesystem action, not a Linear
   write, and it carries no key. (Skip under `--dryrun` — but `--dryrun` already stopped at
   §2, so this only runs on a real apply.)

2. **Print the summary report.** Show what the bootstrap did, end to end:

```text
Bootstrapped: {team} workspace
  preflight  -> key OK (Admin scope) | stopped: {missing key | under-scoped} → see docs/guides/workspace-bootstrap.md
  labels     -> {c} created, {r} recased, {d} deleted ({n} cruft groups declined)
  states     -> {s} created | all categories present
  templates  -> {t} ensured (Problem issue + backlogd problem project + Spec document)
  cruft      -> {x} deleted on explicit yes | none (declined / none offered)
  cache      -> .backlogd/identity.json invalidated (next run re-resolves the recased label)
Runtime stays key-free — only /backlogd:init touched the key (via the engine). Next: /backlogd:scope
```

Under `--dryrun`, the run stops at §2; the report there is the grouped plan plus an explicit
"dry run — no verbs run, nothing changed, cache untouched" line, and `Next: re-run
/backlogd:init (without --dryrun) to apply` instead of the apply summary above.

## Boundaries

- **Setup-only, key-free orchestrator.** This command is the single bootstrap entry point;
  the runtime loop never reads the key. You shell out to the engine for every settings
  write — you never read the credential file, never echo the key, never place it on a
  command line. (AC.)
- **Idempotent + reversible-by-default.** Re-running on a canonical workspace is a no-op.
  The only destructive verb (`delete-label`) runs solely for a cruft group the product owner
  explicitly approved this run; everything else is additive or a rename that preserves ids.
- **Stop on a failed preflight.** No plan is shown and no verb runs if the engine cannot
  authenticate with an Admin-scoped key — point the product owner at the bootstrap guide and
  stop.
