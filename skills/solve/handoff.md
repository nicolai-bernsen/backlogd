---
name: solve-handoff
description: Hand a solved problem back to the product owner — push the branch, open the PR into the integration branch, post a high-level PO-facing solution brief, and move the problem to In Review (the PO accepts via /backlogd:review).
---

# solve — handoff at In Review

> **Dry run:** in `--dryrun` mode, this section does not run — the dry run exits after
> printing the plan (see `skills/solve/dryrun.md`). No push, no PR, no comment, no
> *In Review* transition.

When every unit is `completed`, the problem is solved. Do **not** mark it Done —
`/backlogd:review` (or the PO) accepts later. Instead:

## 1. Push the branch and open the PR

Push the branch and open the PR into the integration branch (reuse an existing PR on a
re-run); put the issue identifier in the title/body so Linear links the PR to the problem:

    git -C "$WT" push -u origin {gitBranchName}
    gh pr create --base {integration} --head {gitBranchName} --title "…(#{identifier})" --body "…"

(No `gh` available? Push the branch and ask the PO to open the PR.)

## 2. Post a high-level, PO-facing solution brief

Post one comment on the problem issue, edited in place, with the `**[backlogd]**` badge.
Write it for a product owner who owns the solution but is not reviewing code:

```
**[backlogd]** Solution brief

Problem: {one line — what was asked}
What was solved: {the outcome, in plain terms}
How (high level): {approach — 2–4 bullets, no code-level detail}
Artifacts: {files/areas changed, links, or what the PO now has}
{Needs your eyes: {anything for the PO to decide} — omit if nothing}
```

(On a single-issue problem it sits alongside the developer's `**[backlogd developer]**`
work-log comment — a PO summary plus the work log, not a duplicate.)

## 3. Move the problem to In Review

Move the problem to the *In Review* state (resolved in `skills/solve/identity.md`), then
**stop** — the run is complete. `/backlogd:review` (or the PO) verifies the AC and merges
the PR to land it.
