---
name: solve-gate
description: Per-unit quality gate — dispatch the tester after the developer, then the reviewer in pre-commit-gate mode (both skipped on kind:ops runs), with a formal 2-round hard cap on combined re-dispatches. The reviewer runs markdownlint-cli2 on changed .md the way CI does and runs the developer's enumerated deferred-checks. A contested needs-changes verdict gets exactly one logged dev<->reviewer reconciliation before it spends a rework round or escalates. Surface failing tests + needs-changes verdicts as rework notes back through dispatch.md.
---

# solve — per-unit quality gate

This skill loads from `skills/solve/dispatch.md` **between step 5 ("Confirm its record")
and step 6 ("Record dispatch completion on the graph")** on the
standard path. It owns the developer↔tester↔reviewer loop: dispatch the tester against
the unit, then the reviewer to gate the diff before commit, and either return `ok`
(continue) or `needs-changes` with rework notes so dispatch.md can re-dispatch the
developer — subject to **one** logged dev↔reviewer reconciliation on a contested verdict
(§3.5) and a 2-round hard cap (§4).

It is **skipped on `kind:ops` runs** — `skills/solve/walk.md` routes those through
`skills/solve/ops.md`, which never loads this skill. Both the tester and the reviewer's
`pre-commit-gate` mode share this skip rule — there is no diff to test or gate.

> **Dry run:** in `--dryrun` mode this skill does not run. Render the planned tester
> and reviewer envelopes read-only as part of the per-unit dispatch plan and follow
> `skills/solve/dryrun.md`. No `Agent` call, no comment.
>
> **Resume:** the gate is **idempotent** — on resume, re-dispatch the tester and
> reviewer from scratch against the unit's latest state. `gate_round` resets to 0 and the
> `reconciled` flag (§3.5) resets to `false` per unit on resume.

## 1. Dispatch the tester

Call the `backlogd:tester` subagent with the Agent tool, handing it the unit as an
**inline** envelope. Include the unit's issue id and point it at the developer's
`**[backlogd developer]**` progress comment:

> Test this unit against its acceptance criteria. Prove each testable AC with an
> automated test, name the untestable ones, post your progress to your issue, then
> report.
>
> Work in this worktree — write your tests under it: {$WT}
>
> Unit ({identifier}, issue id {id}): {title}
>
> Acceptance Criteria:
> {the `## Acceptance Criteria` block from the unit description}
>
> Developer's progress comment (what they changed):
> {body of the `**[backlogd developer]**` comment on this unit}

Capture the tester's final structured summary verbatim, including its `failing:` and
`untestable:` lists. Verify the `**[backlogd tester]**` evidence comment landed; do
**not** re-post it. Add at most a one-line orchestrator note if the comment is missing.

## 2. Dispatch the reviewer (pre-commit-gate)

Call the `backlogd:reviewer` subagent with the Agent tool in **`pre-commit-gate`** mode,
handing it the same unit as an **inline** envelope. Include the unit's issue id, the
worktree path, and pointers to both the developer's and tester's progress comments:

> Gate this unit's pre-commit diff against its acceptance criteria and the Definition of
> Done. Mode: **pre-commit-gate**. Inspect the worktree diff, judge each AC + DoD line,
> roll up to `ok` / `needs-changes`, post your progress to your issue, then report.
>
> Run the **mandatory gate checks** in *Gate-mandated checks the reviewer runs* below —
> markdownlint-cli2 on every changed `.md` the way CI does, plus every check the developer
> enumerated under `Deferred-checks:` in its report. Any of these failing is
> `needs-changes`.
>
> Worktree to inspect: {$WT}
>
> Unit ({identifier}, issue id {id}): {title}
>
> Acceptance Criteria:
> {the `## Acceptance Criteria` block from the unit description}
>
> Developer's progress comment (what they changed):
> {body of the `**[backlogd developer]**` comment on this unit}
>
> Developer's enumerated deferred checks (run each — see below):
> {the `Deferred-checks:` line from the developer's STATUS report, or "none"}
>
> Tester's progress comment (what they proved):
> {body of the `**[backlogd tester]**` comment on this unit}

Capture the reviewer's final structured summary verbatim, including its `verdict:`
(`ok` / `needs-changes`) and any `notes:`. Verify the `**[backlogd reviewer]**` comment
landed; do **not** re-post it.

## 2.5 Gate-mandated checks the reviewer runs

The reviewer holds `Bash` in its grant, so the gate makes it the single place where two
classes of check are **always run before commit** — closing the silent-deferral gap a
specialist on a narrow grant otherwise leaves (NB-413). Both feed the *same*
`ok` / `needs-changes` rollup as the AC + DoD walk; neither is advisory.

**(a) markdownlint on every changed `.md`, the way CI does (Fold-in NB-417).** CI runs
`markdownlint-cli2` **pinned to `v0.22.1`** via `.pre-commit-config.yaml`, reading the
repo's `.markdownlint-cli2.jsonc` automatically. The reviewer **must invoke it the same
way** — an ad-hoc `npx markdownlint-cli2` on a different version, or with a flag set that
bypasses the repo config, can print a **false exit-0** while CI still reds (observed live
on NB-417: tester + independent reviewer both passed a diff that then tripped MD038 in CI).
So:

- Run `npx --yes markdownlint-cli2@v0.22.1 <each changed .md>` from the worktree root —
  the **same pinned rev** the `.pre-commit-config.yaml` markdownlint-cli2 hook uses, so the
  gate matches CI exactly (if that pin is bumped, bump it here too). It auto-discovers
  `.markdownlint-cli2.jsonc`. Scope to the diff's changed `.md` set, not the whole tree
  (CI lints everything; the gate only needs to clear what this unit touched).
- **Trust the printed `Summary: N error(s)` / per-file findings over the process exit
  code.** A non-zero error count is a `needs-changes` even if the shell reported exit 0;
  cite the offending `file:line rule` in the rollup notes.
- A unit that changed **no** `.md` skips this check (nothing to lint) — say so.

**(b) The developer's enumerated deferred checks.** A specialist whose tool grant could
not run a check its AC required declares each one in a machine-readable `Deferred-checks:`
line in its STATUS report (see `agents/developer.md` → *The `Deferred-checks:` line —
enumerated deferred-check hand-off*). For **each** entry the developer enumerated, the
reviewer runs the named command and treats a failure as `needs-changes`, citing the
command and its result. An
empty / `none` `Deferred-checks:` line means the specialist ran everything itself — there
is nothing to pick up. This is the explicit, enumerated hand-off that **replaces today's
silent deferral**: the trust boundary moves on purpose, recorded in the report, not by
accident.

> **Why the reviewer and not the orchestrator.** The reviewer already runs every
> machine-verifiable check itself with cited evidence (`agents/reviewer.md`), already holds
> `Bash`, and already rolls up to `ok` / `needs-changes`. Folding these two classes into
> its existing walk needs no new tool grant and keeps one place responsible for "was every
> runnable check actually run before commit". The orchestrator stays the actor on the
> verdict; the reviewer stays the judge.

## 3. Act on gate verdicts (unified)

Combine the tester's `failing:` + `untestable:` lists and the reviewer's `verdict:` +
`notes:` into a single decision. The reviewer's `verdict:` **already folds in** the
*Gate-mandated checks* (markdownlint on changed `.md`, the developer's enumerated
deferred-checks) — a red from either of those is part of the reviewer's
`needs-changes`, so there is no separate channel to merge here:

- **Both `ok`** (tester `failing: []` and reviewer `verdict: ok`) — gate returns
  **`ok`**. If the tester captured `untestable:` items, carry them forward so
  `skills/solve/handoff.md` can surface them in the PO-facing solution brief under
  *"Needs your eyes"*. Untestable items do **not** auto-block.
- **Either is red** (tester `failing:` non-empty **or** reviewer `verdict:
  needs-changes` — including a markdownlint red or a failed deferred-check) — gate returns
  **`needs-changes`** with combined rework notes: failing-test names (and the AC each one
  proves) plus the reviewer's notes — **subject to the one-shot reconciliation in §3.5 and
  the cap in §4 below**.

## 3.5 Verdict reconciliation — one structured dev↔reviewer exchange

A reviewer `needs-changes` is not always a settled fact: the developer may have evidence the
reviewer missed, or read an AC differently. Today that disagreement has nowhere to go inside
the gate — the developer either silently complies with the rework note or the verdict goes
straight up. This step adds **exactly one** bounded, logged dev↔reviewer exchange at the
verdict seam **before** a contested `needs-changes` spends a rework round or escalates — it
**extends** the existing 2-round channel, it does **not** open a new unbounded loop.

It runs **only when the reviewer's verdict is `needs-changes`** (a unit the developer
believes passes). A purely test-driven red (tester `failing:` non-empty) is objective — a
failing test is reconciled by fixing the code, not by debating the reviewer — so reconciliation
applies to the **reviewer's verdict**, not to failing tests. Run it like this:

1. **Offer the developer one rebuttal.** Re-dispatch the **same developer** specialist in a
   lightweight **`reconcile`** turn (Agent tool, inline envelope) carrying the reviewer's
   `needs-changes` notes and a pointer to the `**[backlogd reviewer]**` comment. Ask it to
   either **concede** (accept the notes — it will fix them on the next rework round) or file
   **one structured rebuttal**: which note it contests, the evidence (a cite to the diff, a
   test, or the AC text), and what it believes the correct verdict is. The developer appends
   this to its own `**[backlogd developer]**` work-log comment (it owns no other surface) —
   so the exchange is **logged and inspectable**. The developer does **not** set state, does
   **not** mark the unit resolved, and does **not** merge — it only states its case.
2. **The reviewer reconsiders once.** If the developer conceded (or filed no rebuttal),
   skip straight to §4 with the original `needs-changes`. If it filed a rebuttal,
   re-dispatch the **same reviewer** in `pre-commit-gate` mode with the rebuttal appended to
   the envelope, asking it to **reconsider that one verdict** in light of the developer's
   evidence and return a fresh `verdict:` (+ `notes:`). The reviewer records its
   reconsidered verdict in its `**[backlogd reviewer]**` comment. **The reviewer keeps sole
   authority over the verdict** — it may hold `needs-changes` or flip to `ok`; the developer
   cannot overrule it, and the orchestrator does not flip it for either party.
3. **Act on the reconciled verdict.** If the reviewer flipped to `ok`, the gate proceeds as
   *both `ok`* in §3 (the dispute is resolved in the developer's favour, on the reviewer's
   own authority). If the reviewer held `needs-changes`, fall through to §4 with the
   (possibly narrowed) notes — the dispute is resolved in the reviewer's favour, and the
   normal rework/cap path takes over.

**Bounded to one exchange per unit.** Reconciliation runs **at most once per unit**, on the
**first** `needs-changes` the reviewer returns. Track it with a per-unit
`reconciled` flag (starts `false`, set `true` after the exchange). A second or later
`needs-changes` skips §3.5 entirely and goes straight to §4 — there is no second debate, no
unbounded loop. The reconcile turn and the reviewer's reconsideration are **not** rework
rounds: they do **not** increment `gate_round` (§4). Only an actual developer re-dispatch to
*change the diff* spends a round.

> **Why this preserves who-decides-what.** The seam is **two-way** — the developer can talk
> back to a verdict it believes is wrong, once — but it **removes no boundary**: the
> reviewer still owns the verdict (it is never forced to flip), the developer still owns
> only the *how* (it states its case but never self-marks or merges), and the PO still owns
> the escalation that follows an unresolved `needs-changes` (via the §4 cap → `blocked`).
> The whole exchange is logged on the two specialists' own work-log comments, so it is
> inspectable. (Cross-checked against `skills/scrum/references/accountabilities.md`: the
> reviewer judges, the developer owns the *how*, the scrum-master acts on the verdict, the
> PO resolves true escalations — none of those move here.)

## 4. Enforce the 2-round hard cap

Combined across tester-failure re-dispatches **and** reviewer needs-changes
re-dispatches, the gate caps re-dispatches at **2 rounds** per unit. Use a small
explicit counter:

- `gate_round` starts at **0** when the gate first runs for a unit.
- On every `needs-changes` outcome that would re-dispatch the developer, **increment
  `gate_round`** before handing back to dispatch.md.
- On the **3rd would-be re-dispatch** (i.e. when incrementing would push `gate_round`
  past 2), return **`blocked`** (not `needs-changes`) with the accumulated notes from
  all rounds. dispatch.md's step 7 treats a gate `blocked` exactly like a developer
  `STATUS: BLOCKED` (it routes through `skills/solve/capture.md`'s `BLOCKED` branch):
  leave the unit in progress, surface to the product owner via the orchestrator's pause
  path (see `commands/solve.md` step 6 + dispatch.md step 7), and stop the run.

The counter is per-unit and lives in the scrum-master's working context across the
loop; nothing is persisted.

## 5. Hand back to dispatch.md

Return one of:

- **`ok`** — continue to dispatch.md step 6. Carry any `untestable:` items forward for
  the handoff brief.
- **`needs-changes`** — return combined rework notes (after the §3.5 reconciliation has
  run, if this was the first contested verdict); dispatch.md re-enters its step 3
  (resolved-specialist dispatch) with those notes prepended, then re-enters this skill.
  `gate_round` has been incremented.
- **`blocked`** — the 2-round cap is exhausted; return accumulated notes. dispatch.md
  step 7 treats this like a developer `STATUS: BLOCKED` (the `BLOCKED` branch in
  `skills/solve/capture.md`), the orchestrator pauses, and the run stops.
