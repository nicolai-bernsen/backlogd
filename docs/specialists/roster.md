# Specialist roster — `/backlogd:scope`'s routing table

This file is the **canonical list of backlogd specialists** and the **primary source**
`/backlogd:scope` reads when it picks which developer solves a problem. One row per
specialist, with crisp *select-when* criteria the picker can match against directly —
instead of reasoning over N free-text `description:` blocks in-prompt.

> **Why a catalog.** [`docs/specialists.md`](../specialists.md) explains the
> discovery + description-driven picker shipped in NB-337. As the roster grows past two
> entries, reading every agent's `description:` on every scope run gets expensive and
> inconsistent. This catalog front-loads the routing signal into one scannable table so
> the picker reads it **once**. It is the compound-engineering `persona-catalog.md`
> pattern (EveryInc/compound-engineering-plugin →
> `skills/ce-code-review/references/persona-catalog.md`).

## The catalog

| Specialist | Select when… | Tool-grant style | Hand-off to | Source |
| --- | --- | --- | --- | --- |
| `developer` | **Default** — no specialist's *select-when* matched. Any code-level change, refactor, behaviour change, or anything whose source of truth is source code. | all-tools (no `tools:` line) | n/a | `agents/developer.md` (shipped) |
| `developer-docs` | Problem mentions README, `docs/`, `.md` polish, conventions/contributor pages, narrative prose, voice/tone, or link integrity — and the source of truth is **prose, not code**. Routed by the `agent:docs` label. | reduced (`Read, Grep, Glob, Edit, Write` + `mcp__linear__{get_issue, list_comments, save_comment}`) | n/a | `.claude/agents/developer-docs.md` (per-repo) |

**Columns:**

- **Specialist** — the agent's `name:` frontmatter (always `developer` or `developer-<suffix>`).
  The Linear routing label is `agent:<suffix>` (e.g. `developer-docs` → `agent:docs`); the
  generic `developer` carries **no** `agent:*` label.
- **Select when…** — the labels that should map, file-paths that should trigger, and
  problem-shapes that fit. This is the routing signal the picker matches against.
- **Tool-grant style** — *all-tools* (no `tools:` frontmatter line, so the subagent
  inherits the full surface — see NB-345) or *reduced* (an explicit `tools:` list). Recorded
  so a reviewer can sanity-check that a specialist's grant fits its job.
- **Hand-off to** — the specialist this one routes *onward* to when the work turns out to
  be a different shape. Today both entries are terminal (`n/a`): a mis-routed unit is
  reported back via `STATUS: BLOCKED` for the scrum-master to re-label, not handed
  peer-to-peer.
- **Source** — which discovery root the agent file lives under. `/backlogd:scope` globs
  `${CLAUDE_PLUGIN_ROOT:-.}/agents/developer*.md` (the shipped roster) **then**
  `.claude/agents/developer*.md` (per-repo additions); the per-repo source wins on a name
  clash. The two current specialists deliberately come from different roots —
  `developer-docs` is a per-repo addition, not part of the shipped plugin.

## The catalog is the source of truth; frontmatter mirrors it

Each specialist exists in **two** places, and they must agree:

1. **This catalog row** — what `/backlogd:scope` reads first to route.
2. **The agent file's `description:` frontmatter** — what Claude Code's *native* subagent
   picker reads, and the **fallback** source `/backlogd:scope` scans if this catalog is
   missing or doesn't list a discovered agent.

Keep the row's *select-when* criteria and the file's `description:` saying the same thing.
When they drift, the catalog wins for backlogd's picker; fix the `description:` to match.

## Adding a specialist

> **First, the bar: split agents on tool grants, not on topics.** A separate
> `developer-<suffix>` is justified **ONLY** when it needs a different *capability / tool
> grant* — never merely a domain label. "It works on React" or "it works on data" is a
> **standards-profile** difference (a new file in [`docs/standards/index.json`](../standards/index.json),
> matched by `applies-to`), solved by the single `developer` — **not** a reason to add an
> agent. So do **not** add `developer-react` / `developer-python` and recreate the sprawl;
> add a standards file. Add an agent only when the job needs a tool the generic `developer`
> must not have (or must be denied one it has) — that is why `developer-docs` exists (its
> *reduced* grant, not its docs topic). The full rationale lives in
> [`docs/specialists.md`](../specialists.md) → *The rule: split agents on tool grants, not
> on topics*; the **Tool-grant style** column below is where you record that justification.

1. **Drop the agent file** — `agents/developer-<suffix>.md` (to ship it) or
   `.claude/agents/developer-<suffix>.md` (per-repo only). Clone `agents/developer.md`'s
   six-section structure; see [`docs/specialists.md`](../specialists.md) →
   *Section template*.
2. **Add a row here** — name, *select-when*, tool-grant style, hand-off target, source.
3. Write a crisp `description:` in the file's frontmatter that **mirrors** the row's
   *select-when* (see above).

That's it — no taxonomy, no scoring, no extra frontmatter. `/backlogd:scope` discovers the
file by glob, reads this catalog to route, and applies the `agent:<suffix>` label.

> **If you drop a file but forget the row**, `/backlogd:scope` still works: it discovers the
> agent by glob, falls back to scanning its `description:`, picks it if it fits — and
> **flags the missing catalog row in its report** so the gap gets closed. The catalog is
> the fast path, not a hard gate.
