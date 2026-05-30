# Subagent MCP tool grant — investigation post-mortem (NB-340)

> Status: **closed.** Investigation done; fix shipped as NB-345 (PR #61, commit
> `656dd59` on `dev`). Defense-in-depth complementary mitigation shipped as NB-346
> (see §7), with a clean-room confirmation in §8 (NB-368). This note exists so the
> finding doesn't have to be re-derived the next time someone wonders why a subagent
> can't see its own MCP tools.

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
| --- | --- | --- |
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

   ```text
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
| --- | --- | --- | --- |
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

*Recorded by the 2026-05-29 `/backlogd:review NB-346` session (follow-up to
PR #72). Caveat: this is the reviewer's real grant exercising the mechanism, not
the literal scratch `probe-restricted.md`; same code path, but the isolated
Probe-A/B/C controls remain open for a clean-room confirmation.*

**→ Closed by §8 (NB-368):** a second, independent session reproduced Probe-A and
ran the Probe-C control cleanly; only the dedicated no-pre-load Probe-B remains open
(see §8).

## 8. NB-368 — clean-room confirmation (second session, dedicated controls)

§7's first result came from a `/backlogd:review NB-346` run that exercised the
reviewer's real grant but left the dedicated Probe-A/B/C controls open. NB-368 ran
them as an explicit two-dispatch experiment in a **separate** session (2026-05-29,
Opus 4.8) — reproducing the result independently and landing the control §7 lacked.

**Procedure (the real production path).** The parent fired the canonical §0
`ToolSearch(select: "mcp__linear__…")` pre-load — verbatim the call documented in
`skills/linear/SKILL.md` — confirmed it loaded the 11 Linear schemas, then dispatched
two probes from the same parent context:

- **Probe A** — `backlogd:reviewer` (the live agent: explicit `tools:` list including
  `mcp__linear__save_comment`, and **no `ToolSearch`** of its own).
- **Control** — `general-purpose` (no `tools:` field). This is §7's "Probe-C".

**Runtime tool grants observed** (the evidence NB-368 AC asks for):

| Dispatch | `tools:` frontmatter | Runtime grant reported | `mcp__linear__*` form |
| --- | --- | --- | --- |
| Probe A (`backlogd:reviewer`) | explicit list incl. `save_comment`; no `ToolSearch` | `Read, Grep, Glob, Bash, mcp__linear__get_issue, mcp__linear__list_comments, mcp__linear__save_comment` | **directly callable** (no `ToolSearch` needed) |
| Control (`general-purpose`) | none (`*`) | base tools **+ `ToolSearch`**; `mcp__linear__*` present but **deferred** | reached only by calling `ToolSearch` first |

**End-to-end write proof.** Probe A did not merely *see* `save_comment` — it **called**
it, posting comment `565ff5a8-85ce-45db-9eb0-629786b38631` to NB-368 (verified
persisted via `list_comments`; author = the OAuth identity). A restricted-grant
specialist completed a real Linear write after the §0 pre-load.

**New mechanistic finding (refines §3).** The two grants differ in *form*, not just
presence: the explicit-list child received its **named** Linear tools **materialised
as directly-callable** (it has no `ToolSearch`, yet wrote successfully), while the
no-`tools:` child received them **deferred**, reachable only via `ToolSearch`. So the
harness honours an explicit `tools:` list's named `mcp__*` entries by loading them
directly — *provided their schemas are already resolved in the session*. §0's
`ToolSearch` is exactly what resolves those schemas. This reconciles §3 (NB-340,
stripped) with §7/§8 (loaded): NB-340's parent had the MCP server *connected* but had
**not** actively `ToolSearch`-resolved the schemas, so there was nothing to
materialise into the explicit-list child — the precise seam NB-368 was filed to test.
The `frontmatter ∩ parent's currently-loaded deferred tools` model in
`skills/linear/SKILL.md` is therefore the empirically-correct one; §3's "statically-
known set" phrasing was the pre-pre-load understanding.

**Verdict: pre-load CONFIRMED (sufficient on the production path).** Every
`/backlogd:*` command runs §0 before any dispatch, and after §0 an explicit-list
specialist demonstrably receives **and uses** its named `mcp__linear__*` tools. The
three trust-layer specialists (`reviewer`, `tester` → `save_comment`; `refiner` →
`save_issue`) are **not** silently stripped in production.

**Honest scope — what is *not* isolated.** This proves §0 *sufficient*. It does not by
itself prove §0 *necessary*: a same-session "explicit list, no pre-load" control (the
original Probe-B) is not constructible — once `ToolSearch` resolves a schema in the
parent it stays resolved, and no available registered agent names a deferred tool
*outside* the §0 set to test against. Necessity is supported by the cross-session
contrast (NB-340/NB-338, pre-§0, stripped) but that carries a possible harness-version
confound. Because the production path **always** runs §0, necessity-vs-sufficiency is
moot for safety — the specialists work on every real invocation. A true clean-room
Probe-B (fresh session, explicit-list agent, §0 deliberately skipped) is the one
remaining footnote, not a blocker.

**Resolution (NB-368's "if confirmed" branch).**

- **Keep** the explicit `tools:` lists on `agents/reviewer.md`, `agents/tester.md`,
  `agents/refiner.md` — the harness-enforced boundary is preserved (the best outcome
  the issue named) and is proven to work behind §0.
- **Keep** the §0 pre-load in all `/backlogd:*` commands — it is what makes the
  explicit-list path work; removing it would risk reintroducing the NB-340 strip.
- `agents/developer.md` keeps **no `tools:` line** as a **deliberate exception**, not
  an inconsistency: it needs a broad grant (`Edit`/`Write`/`Bash`/git *and* Linear) for
  end-to-end code writes, so the contract-in-prose boundary (NB-345) fits it better
  than a restrictive list. The two patterns coexist by design.
- **No double-fix:** nothing from a "losing approach" is in the tree — §0 and the
  explicit lists both stay; `developer.md`'s no-list is pre-existing and now documented
  as intentional.

*Recorded by the 2026-05-29 NB-368 session (Opus 4.8). Evidence: NB-368 comment
`565ff5a8`; both runtime grants tabulated above; §0 present in all five installed
`0.13.0` commands (`scope`/`solve`/`status`/`review`/`release`).*
