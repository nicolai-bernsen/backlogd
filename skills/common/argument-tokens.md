---
name: argument-tokens
description: The shared $ARGUMENTS token grammar every long-running /backlogd:* verb parses — mode:report-only, mode:headless, base:<sha>. Defined once here and referenced (never restated) by commands/{scope,solve,status,review,release}.md. Load this when a verb hits its "Parse argument tokens" step, or when adding/changing a token.
---

# backlogd argument tokens — the shared verb grammar

This is the **single source of truth** for the `key:value` tokens every long-running
`/backlogd:*` verb accepts. The five verb command files
(`commands/{scope,solve,status,review,release}.md`) each carry a short **"Parse argument
tokens"** step that **loads this file** — they do **not** restate the grammar, so the
contract cannot drift. Adopted from EveryInc/compound-engineering-plugin's pattern: one
token grammar, parsed the same way by every verb.

## The grammar

- A **token** is `key:value` — a lowercase `key`, a colon, then a `value` with no spaces.
  Three tokens are defined (the table below). `mode:` takes an enum value
  (`report-only` / `headless`); `base:` takes a git ref.
- **Position-independent.** Tokens may appear in **any position** in the arguments, in any
  order, before or after the issue identifier (the order-independent, any-position rule).
  Scan the whole argument string for them; do not assume a fixed slot. The leftover
  non-token argument (if any) is the issue identifier the verb already expects.
- **Composable.** More than one token may be passed at once (e.g.
  `mode:report-only mode:headless` or `base:<sha> mode:headless`); each is honoured
  independently by the verbs that recognise it.
- **Unrecognised tokens — ignore with a warning.** A `key:value`-shaped token whose key is
  not one of the three below (or a `mode:` value outside the enum) is **not** an error and
  does **not** halt the verb: ignore it and emit a one-line warning naming the token, then
  continue (the unrecognised-token / unknown-token rule). This keeps the grammar
  forward-compatible — a future token a stale verb does not yet know about degrades to a
  warning, never a hard stop. A plain word with no colon is treated as the issue
  identifier, not a token, and is never warned about.
- **Backwards compatible — additive only.** A verb invoked with **no tokens** behaves
  **exactly as it does today**. The tokens add behaviour; they never change the
  no-token path.

## The three tokens

Each token's meaning is uniform; the per-verb column says which verbs **honour** it versus
treat it as a documented **no-op** (accepted, warn-noted, no behaviour change).

- **`mode:report-only`** — *plan, write nothing.* The verb prints the actions it **would**
  take and writes nothing to Linear or git: no `mcp__linear__save_*` (state, description,
  relations, comments, projects, documents), no `git worktree add` / `commit` / `push` /
  `gh pr create` / `gh pr merge`, no `save_project`, no merge, no tag, and no graph write.
  Reads are allowed. This is the **cross-verb generalisation of NB-317's `--dryrun`**.
  - **scope** — print the spec + `## Acceptance Criteria` + the decomposition it would
    write; create no issues/sub-issues, set no relations, apply no labels.
  - **solve** — **identical to NB-317's `--dryrun`**: follow `skills/solve/dryrun.md`
    verbatim. `--dryrun` is the documented **alias** for `mode:report-only` on solve (see
    "Aliases" below); there is **no behavioural fork** between them.
  - **status** — print the forecast it computed and the console standup; **skip** the
    `save_project(description: …)` forecast-block refresh (the one write status makes).
  - **review** — print the verdict it would post (the `**[backlogd review]**` rollup) and
    the merge / state-transition it would make; **do not** dispatch the reviewer's side
    effects and **do not** merge, transition, or release the claim.
  - **release** — print the promote / version-bump / tag / back-merge / Linear-write plan;
    touch nothing (no branch, no commit, no PR, no tag, no Shipped comment).
- **`mode:headless`** — *never raise an interactive prompt.* Where a verb would normally
  pause for a product-owner decision via an `AskUserQuestion`-style prompt, it instead
  **fails fast with a one-line reason and stops** — it does **NOT** proceed with a silent
  default. An unattended run (a script, a `/loop`, a cron job) that hits a genuine product
  decision must surface and stop, so the run never hangs unattended and never guesses past
  a real decision.
  - **scope** — on a genuine ambiguity the refiner surfaces (an ambiguity question), fail
    fast with the reason instead of asking.
  - **solve** — on any PO-surfacing point — a developer `BLOCKED` blocker, a NEEDS-PO /
    unconfirmed `[manual]` *needs-you* judgement call, or a missing-standard *block* — fail
    fast with the one-line reason instead of pausing for the PO.
  - **review** — same as solve's PO-surfacing set: a *needs you* (NEEDS-PO / AWAITING-PO)
    or a NO-STANDARD missing-standard *block* fails fast instead of asking the PO.
  - **status** — documented **no-op**: status already only reports and never prompts.
  - **release** — documented **no-op**: release prompts only for the bump type, which is
    supplied as an argument in an unattended run; nothing else prompts.
- **`base:<sha>`** — *scope the work against a specific git base* instead of the
  integration-branch HEAD. `<sha>` is any git ref (a commit SHA, a tag, a branch). It is
  meaningful **only where a verb opens a worktree** — today that is **solve** only, where
  the worktree + branch are cut off `<sha>` instead of `origin/{integration}`. Every other
  verb (`scope`, `status`, `review`, `release`) does **not** open a worktree, so `base:` is
  **warn-ignored** there: accept it, emit the one-line warning that this verb does not open
  a worktree, and continue unchanged.

## Aliases

- **`--dryrun` ≡ `mode:report-only` on solve.** `solve`'s existing `--dryrun` flag is a
  documented, retained alias for `mode:report-only`; both follow the same contract in
  `skills/solve/dryrun.md` with **no behavioural fork**. `solve` recognises both spellings
  and treats them identically (its existing `--no-ship` / `--steal` flags are unaffected).
  This problem (NB-356) does **not** deprecate `--dryrun`.

## How a verb parses these (the shared procedure)

Each verb's **"Parse argument tokens"** step does exactly this, then continues its own loop:

1. Scan the whole argument string for `key:value` tokens (any position, any order).
2. For each recognised token, record the decision and carry it into the verb's loop:
   `mode:report-only` → run the verb's report-only plan (per the per-verb row above);
   `mode:headless` → on a would-prompt point, fail fast with a one-line reason;
   `base:<sha>` → on solve, cut the worktree off `<sha>`; elsewhere warn-ignore.
3. For each `key:value`-shaped token that is **not** recognised (unknown key, or a `mode:`
   value outside the enum), emit a one-line warning naming it and continue (do not halt).
4. Treat the remaining non-token word (if any) as the issue identifier the verb expects.

A verb with no tokens skips straight past step 2 and behaves exactly as today.
