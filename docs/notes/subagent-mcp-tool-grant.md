# Subagent MCP tool grant — investigation post-mortem (NB-340)

> Status: **closed.** Investigation done; fix shipped as NB-345 (PR #61, commit
> `656dd59` on `dev`). Defense-in-depth complementary mitigation shipped as NB-346
> (see §7 below). This note exists so the finding doesn't have to be re-derived
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

## 7. NB-346 — defense in depth at the orchestrator (pre-load)

NB-345's all-tools workaround restores the developer's write surface, but the
contract is fragile: any future specialist that wants an explicit `tools:` list
(including the NB-326 reviewer, which deliberately wants a restricted grant) will
hit the same drop. NB-346 (PR #72, merged to `dev`) ships the complementary mitigation:
each `/backlogd:*` command begins with a **§0 "Pre-load deferred tools" step**
that runs a single batched `ToolSearch` call naming the canonical Linear MCP tool
list (see `skills/linear/SKILL.md` → *Deferred tools — pre-load before dispatch*).

The pre-load loads the deferred tools into the orchestrator's context **before**
any subagent dispatch, so the harness's `frontmatter ∩ parent's currently-loaded
deferred tools` intersection (§3 above) no longer strips Linear tools from a
restricted-grant subagent's runtime surface. NB-345 (no `tools:` line on
`agents/developer.md`) and NB-346 (orchestrator pre-load) are complementary, not
alternatives — both ship.

### Controlled test — design + outcome

This is the NB-346 follow-up probe to confirm or refute **hypothesis 1** from §1
above (deferred-tool intersection) under the new mitigation. Per NB-346's
acceptance criteria, the test design is captured here; the first live outcome —
from the 2026-05-29 `/backlogd:review NB-346` run — is recorded below, with the
dedicated Probe-A/B/C controls left for a clean-room run.

**Setup.** A fresh Claude Code session (`/plugin update` + reload first) with the
NB-346 PR merged into the loaded plugin snapshot. Stay in a single parent
context.

**Probe procedure.**

1. **Pre-load step** (orchestrator-side, per the NB-346 mitigation):

   ```
   ToolSearch(select: "mcp__linear__get_issue,mcp__linear__save_issue,mcp__linear__save_comment,mcp__linear__list_comments,mcp__linear__list_issue_statuses,mcp__linear__list_issue_labels,mcp__linear__list_issues,mcp__linear__list_teams,mcp__linear__list_milestones,mcp__linear__get_project,mcp__linear__save_milestone")
   ```

2. **Probe-A** — dispatch a one-shot subagent with an **explicit `tools:` list**
   including `mcp__linear__save_comment`, and ask it to print the exact list of
   tools it actually sees at runtime. Example agent frontmatter (use a scratch
   `.claude/agents/probe-restricted.md` for the test; remove after):

   ```yaml
   ---
   name: probe-restricted
   description: One-shot probe — print runtime tool grant.
   tools: Read, Grep, Glob, Bash, mcp__linear__get_issue, mcp__linear__save_comment
   model: inherit
   ---
   Print the exact list of tools you have available at runtime, one per line,
   then stop. Do not call any tool.
   ```

3. **Probe-B** (control) — same procedure but **without** step 1's pre-load
   (start a fresh session, skip the `ToolSearch`, dispatch Probe-A's frontmatter
   directly). This replicates the pre-NB-346 baseline.

4. **Probe-C** (control) — a general-purpose subagent with **no `tools:` field**
   (matches §2's general-purpose probe), with the pre-load done. Should still
   see the full MCP surface — sanity check that the pre-load itself does not
   degrade the no-`tools:` path.

**Expected outcomes** (if hypothesis 1 is confirmed by the NB-346 mitigation):

| Probe | Pre-load? | Explicit `tools:` includes `mcp__linear__save_comment`? | Expected tool grant |
|---|---|---|---|
| A | yes | yes | `mcp__linear__save_comment` **present** at runtime |
| B | no | yes | `mcp__linear__save_comment` **absent** (pre-NB-346 baseline) |
| C | yes | no (inherit) | Full MCP surface present (sanity check) |

**Recording.** Paste each probe's runtime tool-grant printout into a new sub-
section of this note (or attach the transcript to NB-346). The pre-load ships
regardless of outcome — it is defense in depth — but the result determines
whether `disallowedTools:` (NB-353) plus pre-load is sufficient for the
NB-326 reviewer to ship with a deliberately-restricted grant, or whether
all-tools is still necessary for any subagent that posts to Linear.

**Outcome** (first live result — `/backlogd:review NB-346`, 2026-05-29):

Recorded not from the scratch `probe-restricted.md` agent but from a **live
equivalent of Probe-A**: a real `/backlogd:review` run performed the §0
`ToolSearch` pre-load above, then dispatched the `backlogd:reviewer` subagent —
which carries an explicit, deliberately-restricted `tools:` list including
`mcp__linear__save_comment` (the same shape as Probe-A's frontmatter). The
reviewer **successfully posted and edited its `**[backlogd reviewer]**` comment**
on NB-346, so `mcp__linear__save_comment` was present at its runtime.

- Probe-A grant (live equivalent): `mcp__linear__save_comment` **present** — the
  restricted-grant `backlogd:reviewer` posted its comment after the orchestrator
  pre-load. ✅
- Probe-B grant (no-pre-load control): **not run this session.** The pre-NB-346
  baseline absence is already evidenced by §3 / NB-340 / NB-338 — a developer with
  an explicit `tools:` list received no `mcp__linear__*` at runtime.
- Probe-C grant (no-`tools:` inherit control): **not run** as a dedicated probe;
  §2's general-purpose probe already showed the no-`tools:` path sees the full
  MCP surface.
- Hypothesis 1 (deferred-tool intersection) under NB-346 pre-load: **confirmed** —
  a restricted-grant subagent receives its `mcp__linear__*` tools at runtime once
  the parent pre-loads them via `ToolSearch`.
- Implication for NB-326 reviewer (restricted-grant viability): **viable** — the
  reviewer shipped with a restricted grant and works; this very review exercised
  it end-to-end (pre-load → dispatch → comment posted).

_Recorded by the 2026-05-29 `/backlogd:review NB-346` session (follow-up to
PR #72). Caveat: this is the reviewer's real grant exercising the mechanism, not
the literal scratch `probe-restricted.md`; same code path, but the isolated
Probe-A/B/C controls remain open for a clean-room confirmation._
