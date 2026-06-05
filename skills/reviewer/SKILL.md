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

> Example verdict line (the verdict body is a Linear comment, so state is a `- [x]` /
> `- [ ]` checkbox + bold state label, never a status emoji — see
> `output-styles/linear-comment.md`):
>
> ```text
> - [x] **MET** `agents/reviewer.md` exists with restricted tool grant — verified with
>   `Grep -n 'tools:' agents/reviewer.md` showing `Read, Grep, Glob, Bash,
>   mcp__linear__get_issue, mcp__linear__list_comments, mcp__linear__save_comment`
>   and no `Edit, Write`.
> ```

This is the **regression guard**. A deliberately-incomplete solution the developer
reported `solved` cannot pass — the reviewer's verdict has to point at a real command
that proved each AC met, and a missing piece is a missing piece.

**When NB-324 lands** (typed AC kinds — `[test]` / `[manual]` / `[review]`), this
becomes much sharper: `[test]` items will name the command to run, `[manual]` items
will be explicit PO asks, `[review]` items will stay judgement calls. Until then the
reviewer heuristically classifies each `- [ ]` bullet and runs what it can.

Pure-judgement AC ("is this prose clearer?", "is this *good enough*?") is **not**
machine-verifiable — the reviewer marks it **NEEDS-PO** rather than guess. The
distinction matters: hiding a judgement call as a **MET** reintroduces the self-marking
failure the whole role exists to prevent.

## Standards corpus — index-first load order (NB-380)

The reviewer judges every change not only against the AC and the DoD but against the
**standards corpus** — the Accepted ADRs under `docs/standards/adrs/` (an Accepted ADR is
a hard rule; violating one is **UNMET**, same weight as a failed DoD line). The risk this
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

## The fourth verdict outcome — `block` (missing load-bearing standard)

The index walk above closes most reviews cleanly: an applicable standard is honoured or
violated. It has one soft ending — *no* indexed standard applies — and that soft ending is
right **only for a non-consequential change**. The hole it leaves is the dangerous case: a
change that **decides something consequential** (a one-way-door choice — auth model, data
format, state ownership, a public contract) for which **no Accepted standard exists**. "No
applicable standard" then doesn't mean *fine*; it means *the governing standard is missing*,
and silently accepting bakes an ungoverned decision into the corpus by default.

So the reviewer's verdict has a **fourth outcome — `block`** — alongside accepted / sent
back / needs you (the gate's binary `ok` / `needs-changes` rolls a block up as
`needs-changes`, since the gate can't wait on an ADR or the PO):

- **Detect & block, don't invent.** When a consequential decision has no governing Accepted
  standard, the verdict is a **`block`** (not an accept). The reviewer **names the missing
  standard** ("this change decides X; no Accepted standard governs X") and **does NOT invent
  one to unblock** — inventing the rule that clears your own block is the self-marking
  failure the whole role exists to prevent. State the gap; never fill it.
- **Classify the gap, write it into the verdict.** Every block is tagged:
  - **missing standard** — a *durable, cross-issue governance gap* → graduates into an ADR,
    escalates to the PO. **Only this kind enters the corpus.**
  - **missing fact** — a *one-time lookup* (a value, a path, a version) → answered once, no
    ADR, no PO.

  The classification is written into the verdict body (a "Missing standard / fact" section,
  one **NO-STANDARD** line per gap) **so the scrum-master can route it** — see the
  boundaries below.

**Boundary — mechanism here, *threshold* and *routing* elsewhere.** This section (and the
matching `agents/reviewer.md` outcome) introduces the *mechanism*: the `block` outcome plus
the standard/fact classification. Two adjacent decisions live elsewhere, not in this trust
model:

- **The blocking *threshold* — *when* a missing standard rises to a block** vs a
  flagged-assumption-and-proceed — is a **reversibility × blast-radius** calibration: a
  `block` fires **only** on a **one-way door** (irreversible AND wide blast-radius — data
  model, auth/onboarding model, public API shape, the keyless principle); a **two-way door**
  (reversible *or* narrow) gets a **flagged assumption recorded in the verdict** and proceeds.
  This is what keeps a **blank repo usable** — the empty-corpus bootstrap degrades gracefully
  rather than firing fifty blocking questions on issue #1. The calibration itself (the
  threshold + worked examples) is documented operationally in `agents/reviewer.md`
  (*Calibrating the block — reversibility × blast-radius*, NB-386); this trust model states
  *that* it exists and *why* (a wrongful block stalls a usable repo), and the agent doc owns
  *how* it is applied.
- **The scrum-master *routing* of a block** — open a "Define standard for X" sub-issue, mark
  the parent blocked-by it, ask the PO — lives in `commands/review.md` / `commands/solve.md`
  / `skills/scrum/` (a **separate unit, NB-385**). The reviewer's job ends at writing the
  named, classified gap *into the verdict*; the scrum-master reads it and acts (judge / act
  split — property 2). The reviewer never opens the sub-issue or changes state itself.

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

## Specialist-grant contract (NB-413)

NB-340/NB-368 above are about *Linear MCP* tools a subagent may not have at runtime.
NB-413 is the sibling case for the **runnable checks an AC requires** — markdownlint, an
index regen + `--check`, a drift test, a label/issue create. A specialist on a narrow grant
(e.g. a docs specialist with no `Bash`) could be dispatched against such an AC, and the old
behaviour let the un-runnable check fall **silently** to the orchestrator or the pre-commit
gate — relocating the trust boundary upward with nobody deciding it should. The instances:
NB-379 (a docs dispatch with only Read/Grep/Glob/Edit/Write + Linear deferred 12 markdownlint
errors, the index regen, and the drift test to the orchestrator) and NB-381 (a developer on a
`save_comment`-only grant could not create the `kind:improvement` label its AC implied).

**The contract — two complementary halves, neither widening the restricted grants:**

1. **Explicit, enumerated hand-off (the general rule).** A specialist runs every
   AC-required check its grant *can* run, and **enumerates** each one it *cannot* in a
   machine-readable `Deferred-checks:` line in its STATUS report (`agents/developer.md` →
   *The `Deferred-checks:` line*). `Deferred-checks: none` is the honest default when it ran
   everything. The gate is then **obligated to run each enumerated check** and folds a
   failure into `needs-changes` (`skills/solve/gate.md` → *Gate-mandated checks the reviewer
   runs* (b)). This **replaces silent deferral**: the boundary still moves when a grant is
   too narrow, but on purpose and recorded, not by accident.

2. **markdownlint folded into the gate (the common docs check).** The single most common
   un-runnable check — markdownlint on changed `.md` — is run **unconditionally by the
   reviewer** in every pre-commit gate, because the reviewer already holds `Bash` and
   already runs every machine-verifiable check itself. It is invoked **the way CI does**
   (`markdownlint-cli2` pinned to `v0.22.1`, reading `.markdownlint-cli2.jsonc`), trusting
   the printed error count over the process exit code — an ad-hoc invocation can print a
   **false exit-0** while CI still reds (NB-417, where a green tester + reviewer let an
   MD038 through to CI). So a docs specialist need not even enumerate markdownlint: the gate
   always runs it. See `skills/solve/gate.md` → *Gate-mandated checks the reviewer runs* (a).

**Why not just widen every grant?** Rejected. The restricted specialists
(`reviewer`/`tester`/`refiner`) keep narrow grants **by design** (the reviewer's missing
`Edit`/`Write` is what makes its verdict trustworthy — *Restricted tool grant* above), and a
broader `tools:` list is *more* for the NB-340 intersection to silently drop. The generic
`developer` already inherits a broad grant (no `tools:` line, NB-345) and runs its own
checks. Widening the *restricted* roles to self-check would trade away the property that
earns their trust.

**Why not the NB-353 `disallowedTools:` inverted grant?** Evaluated, deferred. Inheriting
the parent surface and *subtracting* (e.g. `disallowedTools: Write, Edit, Bash`) is a smaller
frontmatter with less for the intersection to drop, and is attractive prior art
(Yeachan-Heo/oh-my-claudecode). But its runtime interaction with the NB-340
`frontmatter ∩ loaded-deferred-tools` behaviour is **unverified here** (NB-368 verified the
*positive* `tools:` list path, not the inverted one), and adopting it now would couple this
trust-contract fix to an unproven harness behaviour. It stays a candidate for a focused
follow-up; the enumerated hand-off + gate-runs-markdownlint contract above does not depend on
it.

The decision lives here (the trust model) and is mirrored in
`skills/linear/SKILL.md` → *Specialist-grant contract*, alongside the NB-340 tool-grant
lineage it extends.

## How the reviewer fits into the loop

```text
/backlogd:solve → developer (one per unit) → [pre-commit gate] → solution brief → In Review
                                                                                      ↓
   ship-on-green auto-chain (happy path, on by default)  ──┐   ┌── /backlogd:review (manual re-entry)
                                                           ↓   ↓
                              reviewer (fresh, restricted) → verdict draft
                                                          ↓
              orchestrator acts (merge → Done on fully-green / send back / surface needs-PO / route no-standard block)
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
   **`verdict`** mode (`accepted` / `sent back` / `needs PO` / `block`; see
   `commands/review.md`). This is the fresh-context pass whose `accepted` rollup gates the
   merge — a `block` (missing load-bearing standard) holds the merge until the scrum-master
   routes the gap (NB-385).

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
- **Restating the block *threshold* in this trust model.** The reviewer *detects* a missing
  load-bearing standard, emits the `block` outcome (above), and **applies** the
  reversibility × blast-radius calibration (one-way doors block; two-way doors proceed with a
  flagged assumption) — but *that operational threshold + its worked examples live in
  `agents/reviewer.md`* (*Calibrating the block*, NB-386), not here. This skill is the trust
  model (why the outcome exists, why a wrongful block hurts a blank repo); the agent doc owns
  *how* the reviewer calibrates each call.
- **Routing a block.** Acting on a `block` — opening a "Define standard for X" sub-issue,
  marking the parent blocked-by it, asking the PO, deciding ADR-vs-answer-once — is the
  **scrum-master's** job (`commands/review.md` / `commands/solve.md` / `skills/scrum/`,
  **NB-385**). The reviewer writes the named, classified gap *into the verdict* and stops —
  judge / act split. It does not open the sub-issue or change state.

## Pitfalls checklist

Each pitfall pairs the **Wrong** move with the **Right** one (no status emoji — these are
prose do/don't pairs, kept consistent with the no-emoji rule the verdict surfaces follow):

- **Wrong:** dispatching the reviewer with implicit "you know what we're working on"
  context (it doesn't). **Right:** inline envelope with every artifact it needs.
- **Wrong:** treating the developer's `solved` claim as evidence the AC is met (that's
  exactly the self-marking failure mode). **Right:** the reviewer runs the check; the
  developer's claim is a hypothesis, not a fact.
- **Wrong:** a **MET** AC line in the verdict with no cited command or file path
  (unverifiable by the PO, indistinguishable from theatre). **Right:** every **MET**
  carries cited evidence (`command → output`, `file:line`, etc.).
- **Wrong:** the reviewer editing a file "to make the AC pass" (blows the judge/act split;
  its tool grant excludes `Edit`/`Write` precisely so this is not possible). **Right:**
  send it back via the orchestrator.
- **Wrong:** the orchestrator dispatching the reviewer before any `mcp__linear__*` call has
  loaded the deferred tool (reviewer can't post its comment, NB-340). **Right:**
  `commands/review.md` step 0 pre-loads each deferred tool from the orchestrator first.
- **Wrong:** posting both `**[backlogd reviewer]**` and `**[backlogd review]**` from the
  reviewer (double-posting, breaks the in-place edit contract, blurs authorship).
  **Right:** reviewer posts only `**[backlogd reviewer]**`; orchestrator posts only
  `**[backlogd review]**`.
- **Wrong:** a consequential, ungoverned decision passed as "no applicable standard for
  this diff" (an ungoverned one-way-door silently baked into the corpus). **Right:** a
  consequential decision with no governing Accepted standard is a `block` — name the
  missing standard.
- **Wrong:** the reviewer *inventing* the missing standard to clear its own block
  (self-marking; it just authored the rule it then judged itself against). **Right:** state
  the gap, classify it (standard / fact), and hand it to the scrum-master to route (NB-385),
  never fill it.
