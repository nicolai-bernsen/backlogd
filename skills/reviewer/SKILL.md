---
name: reviewer
description: The trust model behind backlogd's `backlogd:reviewer` subagent — fresh context, restricted tool grant, mandatory machine-verifiable check execution with cited evidence, judge/act split. Use when implementing or modifying `/backlogd:review`, the reviewer agent, or any caller that dispatches the reviewer.
---

# The reviewer trust model

backlogd's verification layer is the product. A confidently-wrong `solved` from the
developer is the one failure mode the rest of the loop cannot catch — it sails through
self-review and only the product owner reading the diff notices. backlogd defends
against that with an **independent reviewer subagent** dispatched by `/backlogd:review`.
This skill is the operating contract behind that subagent — what holds the
independence open, and the rules the orchestrator that dispatches it must follow.

> **Read this file before** modifying `agents/reviewer.md`, `commands/review.md`, or
> any other caller that dispatches the reviewer. The three trust properties below are
> load-bearing — break any one and the verification layer is theatre.

## Three trust properties — why each one matters

### 1. Fresh context

The reviewer is dispatched as a Claude Code subagent via the Agent tool. That gives
it a **fresh context** by construction — it does not inherit the developer's
conversation buffer, the orchestrator's prior turns, or any reasoning chain that
produced the change it is reviewing.

This is the property that makes the verdict worth trusting. Without it, the reviewer
is the same model reading its own chain of thought — by then the wrong answer has
*already* been written down once, in the developer's voice, and confirmation bias is
fully baited. With it, the reviewer sees only the artifacts on Linear and the PR
diff — exactly what the product owner would see if they audited it themselves.

**Implications for the orchestrator that dispatches:**

- **The envelope is the reviewer's entire world.** Pass the spec, the AC, every
  per-unit progress comment, the solution brief, the PR url, the CI signal, and the
  worktree path. Anything you don't put in the envelope is invisible to it.
- **No inline "by the way" context.** If the developer flagged a tricky edge case in
  its progress comment, that belongs in the envelope verbatim. The reviewer does not
  see your conversation; it cannot ask you to clarify.
- **Mirror the developer envelope's discipline.** `commands/solve.md` dispatches the
  developer with a tight inline envelope; `commands/review.md` does the same for the
  reviewer. The two dispatches are structurally identical — fresh agent, fresh
  context, complete envelope.

### 2. Restricted tool grant

The reviewer's tool grant is deliberately narrow. From `agents/reviewer.md`'s
frontmatter:

```yaml
tools: Read, Grep, Glob, Bash, mcp__linear__get_issue, mcp__linear__list_comments, mcp__linear__save_comment
```

It can:

- **read** any file in the worktree (`Read`, `Grep`, `Glob`),
- **run** commands (`Bash`) for machine-verifiable checks — tests, builds, `gh` reads,
  `git` reads — strictly **read-only**: no `git add` / `commit` / `push` / `gh pr
  merge` / `gh pr close`,
- **read** the issue (`get_issue` / `list_comments`),
- **post one comment** on the issue (`save_comment`, edited in place).

It **cannot**:

- edit code (`Edit`, `Write`, `NotebookEdit`),
- change Linear state or restructure issues (`save_issue` — not in the grant),
- merge the PR or transition the issue — those are the orchestrator's job.

This is the **judge / act split**. The reviewer's verdict is its only output; the
scrum-master reads the verdict and *acts* on it (merge, transition, send back). If the
reviewer's verdict says "send it back", that does not happen by the reviewer's hand —
it happens by the scrum-master's. That separation keeps the reviewer honest: it has no
power to "fix it" mid-review and tell itself the AC is now met.

### 3. Machine-verifiable check execution — with cited evidence

The reviewer's contract — written into `agents/reviewer.md` — is to **run** the check,
not trust the developer's word for it. For every `- [ ]` AC bullet that *can* be checked
by a command, the reviewer:

- decides what command would prove or disprove it (file existence, `Grep` for promised
  string, `gh pr checks` rollup, re-run a test command, etc.),
- **runs it** with `Bash` / `Read` / `Grep` / `Glob`,
- **cites the evidence** in the verdict: the command, the output it saw, what it
  proved.

> Example verdict line:
>
>     ✅ `agents/reviewer.md` exists with restricted tool grant — verified with
>     `Grep -n 'tools:' agents/reviewer.md` showing `Read, Grep, Glob, Bash,
>     mcp__linear__get_issue, mcp__linear__list_comments, mcp__linear__save_comment`
>     and no `Edit, Write`.

This is the **regression guard**. A deliberately-incomplete solution the developer
reported `solved` cannot pass — the reviewer's verdict has to point at a real command
that proved each AC met, and a missing piece is a missing piece.

**When NB-324 lands** (typed AC kinds — `[test]` / `[manual]` / `[review]`), this
becomes much sharper: `[test]` items will name the command to run, `[manual]` items
will be explicit PO asks, `[review]` items will stay judgement calls. Until then the
reviewer heuristically classifies each `- [ ]` bullet and runs what it can.

Pure-judgement AC ("is this prose clearer?", "is this *good enough*?") is **not**
machine-verifiable — the reviewer marks it `❔ needs PO` rather than guess. The
distinction matters: hiding a judgement call as a `✅` reintroduces the self-marking
failure the whole role exists to prevent.

## Standards corpus — index-first load order (NB-380)

The reviewer judges every change not only against the AC and the DoD but against the
**standards corpus** — the Accepted ADRs under `docs/standards/adrs/` (an Accepted ADR is
a hard rule; violating one is `❌`, same weight as a failed DoD line). The risk this
introduces is the one NB-380 exists to defuse: if "consult the standards" meant *load all
the prose ADRs into context every review*, the verification layer would get slow, burn the
token/context budget (the NB-379 quota pressure), and — worst — a reviewer swimming in N
prose standards would *miss* the one that applies. With a corpus that grows over time, that
failure gets worse, not better.

**The fix is the authoring format, not a storage backend.** Each ADR carries
machine-readable front-matter — a crisp **checkable `assertion`**, an **`applies-to`** scope
(`domains` / `file-patterns` / `decision-types`), and a lifecycle `status` — and
`scripts/standards_index.py` generates a single small **committed** artifact,
`docs/standards/index.json`, from it. The reviewer's load order (wired into
`agents/reviewer.md`):

1. **Read the compact index first** (`docs/standards/index.json`) — cheap, the only
   standards file always read.
2. **Filter to applicable standards by `applies-to`** — match the diff's changed files
   (glob `file-patterns`), area (`domains`), and decision kind (`decision-types`); **enforce
   only the current `Accepted` set** and skip every non-Accepted `status` — `Proposed`
   (not yet binding), `Superseded`, and `Deprecated` (history). ADRs stay agile: Accepted
   today is a hard rule but reconsiderable — reopen-and-supersede per the template
   lifecycle, so the reviewer enforces only what is *currently* Accepted. Most ADRs are
   irrelevant to any given diff.
3. **Judge against each applicable `assertion`** — usually enough to call met/unmet.
4. **Open a full ADR only when the rationale is needed** — never the whole set.

This keeps the reviewer's context **bounded regardless of corpus size** — the property
that lets the standards gate scale. It is the same regression-guard discipline as property
3: the reviewer cites *which* indexed standards were applicable and how the diff met them.

**Boundary — v1 is index/files only, no graph DB, no server.** This honours the
keyless/serverless principle (ADR-002): the index is a committed JSON file generated by a
zero-dependency stdlib script (mirroring `scripts/graph.py`), and the
`scripts/test_standards_index.py` drift checker fails CI if the committed index diverges
from the corpus. The **named v2 follow-up (NB-320)** — *not* in scope here — unifies this
corpus with the execution graph in Neo4j to query inspection patterns (standards correlated
with rework, domains with a high blocker-rate and no governing standard, which specialist
most hits missing-standard blocks). That cross-run join is where a graph DB finally earns
its place; v1 deliberately ships only the files + index that solve the lookup pain now.

> **Read this section before** adding a standard to `docs/standards/adrs/` or changing how
> the reviewer consults it. Front-matter is the single source of truth: edit it, then
> regenerate the index (`python scripts/standards_index.py`) in the same change — CI's
> drift test enforces the two stay in sync.

## NB-340: tool-grant hazard the orchestrator must work around

A finding from a parallel run (NB-340, Backlog, High) documents that subagent runtime
tool grants may be `frontmatter ∩ parent's currently-loaded deferred tools`. In
plain English: even if the reviewer's frontmatter lists
`mcp__linear__save_comment`, **the subagent may not actually have it at runtime
unless the parent has loaded it first** (via a prior call from the orchestrator's
own context).

This is a Claude Code platform behaviour — not a backlogd bug — but `/backlogd:review`
has to work around it. The mechanism:

- **`/backlogd:review` pre-loads the deferred Linear MCP tools** before any
  `Agent({subagent_type: "reviewer", ...})` dispatch via a single batched
  `ToolSearch` call across the canonical Linear MCP tool list (see step 0 of
  `commands/review.md` and `skills/linear/SKILL.md` → *Deferred tools — pre-load
  before dispatch* for the canonical list). This is the NB-346 mitigation —
  defense in depth at the orchestrator layer so the reviewer's restricted-grant
  `tools:` list receives every Linear tool it names at runtime.
- **If the reviewer reports it could not post its `**[backlogd reviewer]**`
  comment**, treat that as a tool-grant skew, not a reviewer failure. Re-dispatch
  from a fresh session where the pre-load has happened, or fall back to the
  orchestrator copying the reviewer's structured-return verdict into a comment
  itself (audit-trail loss; only as a last resort).

The same hazard applies to any subagent in backlogd that needs an MCP tool — the
developer agent (`agents/developer.md`) is the other case. `/backlogd:solve`'s
dispatch is the symmetric pre-load point.

## How the reviewer fits into the loop

```
/backlogd:solve → developer (one per unit) → [pre-commit gate] → solution brief → In Review
                                                                                      ↓
   ship-on-green auto-chain (happy path, on by default)  ──┐   ┌── /backlogd:review (manual re-entry)
                                                           ↓   ↓
                              reviewer (fresh, restricted) → verdict draft
                                                          ↓
              orchestrator acts (merge → Done on fully-green / send back / surface ❔)
```

The verdict pass has **two triggers, one engine**: `/backlogd:solve`'s ship-on-green final
phase auto-chains it on the happy path (no human gate), and `/backlogd:review` remains the
manual re-entry point the PO can invoke any time. Both dispatch the identical
`verdict`-mode reviewer and act on the identical merge decision.

The same reviewer subagent is dispatched in **two distinct passes**, both honouring the
three trust properties above:

1. **The pre-commit gate** — dispatched *inside* `/backlogd:solve` per unit, before commit,
   in **`pre-commit-gate`** mode (binary `ok` / `needs-changes`; see
   `skills/solve/gate.md`). This is the in-session gate.
2. **The independent verdict** — dispatched after *In Review* against the whole problem, in
   **`verdict`** mode (`accepted` / `sent back` / `needs PO`; see `commands/review.md`). This
   is the fresh-context pass whose `accepted` rollup gates the merge.

The verdict pass is **never** triggered by the reviewer itself — it is initiated either by
the PO running `/backlogd:review`, or **automatically** as `/backlogd:solve`'s ship-on-green
final phase (`skills/solve/ship.md`), which auto-chains the same `verdict`-mode dispatch and
merge decision on the happy path. **Ship-on-green removes the human *trigger*, never the
independent *verification*:** the merge is gated on this independent reviewer's `accepted`
rollup, not on the pre-commit gate alone — the two passes stay separate, and both run.

## Boundaries — what is **not** the reviewer's job

- **Style review.** The reviewer judges *AC satisfaction*, not formatting, naming,
  or "is the code beautiful". Style is the developer's concern (and code-review
  tooling's); over-extending the reviewer here turns the verdict into noise.
- **Definition of Done.** If the team adopts a DoD (see NB-329), it extends *what*
  the reviewer judges, not *how* (still: run checks, cite evidence). The trust
  properties above do not change. NB-329's reviewer adds a DoD walk on top of the
  AC walk — same engine.
- **Re-dispatching the developer.** That's the orchestrator's call from the rollup
  verdict. The reviewer judges and stops.
- **Posting the PO-facing `**[backlogd review]**` rollup.** That comment belongs to
  `/backlogd:review` (the scrum-master). The reviewer posts the
  `**[backlogd reviewer]**` draft; the orchestrator may lift it verbatim into the
  rollup or annotate it. Two distinct badges, two distinct authors, two distinct
  audiences (audit trail vs PO).

## Pitfalls checklist

- ❌ Dispatching the reviewer with implicit "you know what we're working on" context
  → it doesn't. ✅ Inline envelope with every artifact it needs.
- ❌ Treating the developer's `solved` claim as evidence the AC is met → that's
  exactly the self-marking failure mode. ✅ The reviewer runs the check; the
  developer's claim is a hypothesis, not a fact.
- ❌ A `✅` AC line in the verdict with no cited command or file path → unverifiable
  by the PO, indistinguishable from theatre. ✅ Every `✅` carries cited evidence
  (`command → output`, `file:line`, etc.).
- ❌ The reviewer editing a file "to make the AC pass" → blows the judge/act split.
  Its tool grant excludes `Edit`/`Write` precisely so this is not possible. ✅ Send
  it back via the orchestrator.
- ❌ The orchestrator dispatching the reviewer before any `mcp__linear__*` call has
  loaded the deferred tool → reviewer can't post its comment (NB-340). ✅
  `commands/review.md` step 0: pre-load each deferred tool from the orchestrator
  first.
- ❌ Posting both `**[backlogd reviewer]**` and `**[backlogd review]**` from the
  reviewer → double-posting, breaks the in-place edit contract, blurs authorship.
  ✅ Reviewer posts only `**[backlogd reviewer]**`; orchestrator posts only
  `**[backlogd review]**`.
