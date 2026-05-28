# Subagent MCP tool grant — investigation post-mortem (NB-340)

> Status: **closed.** Investigation done; fix shipped as NB-345 (PR #61, commit
> `656dd59` on `dev`). This note exists so the finding doesn't have to be re-derived
> the next time someone wonders why a subagent can't see its own MCP tools.

## 1. What was observed

During the parallel run of NB-338 and NB-339 (specialist-roster work), both dispatched
`backlogd:developer` subagents independently reported the same thing in their final
structured summary: their **runtime tool grant did not include any `mcp__linear__*`
tool**, despite `agents/developer.md` listing them in its `tools:` frontmatter line.
Each subagent had only `Read, Grep, Glob, Bash, Edit, Write` available — so the
mandatory Step 0 / Step 5 `save_comment` contract was physically impossible to honour.

Both runs hit the same wall, in separate isolated contexts, on the same day. That
ruled out a one-off flake and made it an actual platform/config question.

Three hypotheses were ranked at the time:

1. **Deferred-tool intersection** — the harness intersects an explicit `tools:` list
   with statically-known tools, and `mcp__*` tools (resolved at MCP-server-connect
   time) aren't in that set.
2. **Session-snapshot caching** — the subagent inherits a snapshot of the parent's
   tool surface from some earlier moment, before MCP tools had loaded.
3. **MCP never propagates** — the Agent dispatch boundary just doesn't carry MCP
   tools across, regardless of frontmatter.

Hypothesis 1 was the leading candidate going in.

## 2. The controlled test (from NB-345's session)

A separate session ran a controlled probe before shipping the fix. Two subagents were
dispatched back-to-back from the same parent context and each asked to report the
exact list of tools it actually saw at runtime:

- **`backlogd:developer`** (frontmatter with an explicit `tools:` list naming
  `mcp__linear__save_comment` etc.) — reported only `Read, Grep, Glob, Bash, Edit,
  Write`. No `mcp__linear__*`, no `ToolSearch`.
- **`general-purpose`** (no explicit `tools:` field — equivalent to `*`) — reported
  the full tool surface including every `mcp__linear__*` tool and `ToolSearch`.

Same parent, same session, same MCP servers connected. The only variable was the
presence or absence of an explicit `tools:` frontmatter list. That isolates the cause.

## 3. Confirmed hypothesis — and the refinement

**Hypothesis 1 is confirmed, and refined**: when an agent file declares an explicit
`tools:` list, the Claude Code harness intersects that list with its **statically-
known tool set** at dispatch time. `mcp__*` tools are deferred (they only exist after
the MCP server connects) and are **not** in the static set, so they get silently
dropped from the intersection — even when named one-for-one in the frontmatter.

`ToolSearch` is also deferred, so it gets dropped too. That closes the in-session
escape hatch: an explicit-list subagent has no way to discover and load the MCP
tools at runtime, because the tool that would let it do so was also dropped.

Hypothesis 2 (snapshot caching) and hypothesis 3 (MCP never propagates) are both
**refuted** by the general-purpose probe: in the same session, on the same dispatch,
a no-`tools:` subagent saw the full MCP surface. So the surface does propagate; it's
the explicit list that strips it.

## 4. Decision — backlogd-side workaround (NB-345)

Filed and shipped as **NB-345** ([PR #61](https://github.com/nicolai-bernsen/backlogd/pull/61), commit
`656dd59` on `dev`): drop the `tools:` line from `agents/developer.md` so the dispatch
inherits the full tool surface (including `mcp__linear__*` and `ToolSearch`).

The trade-off, named in the commit message:

- **Lose** the structural enforcement of the developer's tool boundary that the
  explicit list provided (the harness used to physically prevent any tool outside
  the list).
- **Gain** the functional capability the contract requires: the developer can post
  and edit its own progress comment on its own Linear issue.

Mitigations carried in:

- The boundary moves into the **system prompt as an explicit contract**: "you have
  these tools at runtime, but the contract forbids their use except for
  `save_comment` on your own issue." Any other `mcp__linear__save_*` call is named
  as a contract violation.
- The orchestrator's **post-dispatch review** stays as the second line of defence.

Acceptable for a personal single-user tool; flagged in the commit for revisit if the
threat model ever changes.

## 5. AC coverage map

NB-340's six acceptance criteria, and where each was satisfied:

| AC | Status | Where |
|---|---|---|
| 1. Reproduce/refute the finding in a fresh session via a controlled test | Satisfied | NB-345 session probe (general-purpose vs. backlogd:developer) |
| 2. Confirm or rule out hypothesis 1 | Satisfied (confirmed, refined) | Same probe |
| 3. Capture the verified behaviour in a `docs/notes/...` markdown | Satisfied | **This file** |
| 4. Decide platform-report vs. backlogd-side workaround | Satisfied (workaround) | NB-345 commit message |
| 5. If backlogd-side change, file a follow-up problem | Satisfied | NB-345 (shipped) |
| 6. If no change, update `skills/solve/dispatch.md` Step 5 | N/A | Branch didn't fire — a change was made |

## 6. Live-verification footnote

The very dispatch that wrote this note ran in a session that was initialised
**before** NB-345's fix landed in its loaded plugin snapshot, so its own
`backlogd:developer` runtime tool grant is still the 6-tool subset (`Read, Grep,
Glob, Bash, Edit, Write`) — no `mcp__linear__save_comment`. That's why this note
exists at all, rather than the developer simply posting it as a Linear comment on
its own issue: the contract was physically out of reach for this dispatch.

Future fresh sessions (after `/plugin update` + reload) will load the post-fix
`agents/developer.md` with no `tools:` line, see the full MCP surface, and honour
the Step 0 / Step 5 / single-comment-edited-in-place contract normally.
