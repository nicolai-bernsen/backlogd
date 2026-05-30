<!--
backlogd Solution-brief template — Project-form only.

`/backlogd:solve` writes this Document at *In Review* on a Project-form problem,
as the PO-facing brief that lives alongside the per-unit `**[backlogd developer]**`
work logs. Single-Issue problems keep the brief as a comment on the issue
(`**[backlogd]** Solution brief`) — they do not get a Document.

Re-running `/backlogd:solve` updates this Document in place by `id` (one
`Solution brief` per Project — see
`skills/linear/references/documents-and-updates.md`).

`/backlogd:review` may append accept/sent-back notes to this same Document on
verdict; the audit trail is one Document per Project, edited over the loop.
-->

# Solution brief

{One- to two-paragraph summary in plain product terms: what the PO now has, what
problem it solves, and where to look.}

## What changed

- {Bullet 1 — outcome-level change, not code-level detail.}
- {Bullet 2 — keep it terse; the PR diff + per-unit work logs carry the depth.}

## How it was verified

- {How the AC was demonstrated — `[test]` commands run, `[manual]` checks confirmed, `[review]` judgements made. Cite the evidence so `/backlogd:review` can see it at a glance.}
- {CI signal, smoke runs, manual sweeps — whatever shows the increment clears the Definition of Done.}

## Follow-ups

- {Optional — known gaps, deferred work, or anything the PO should track next. Include any `DONE_WITH_CONCERNS` concerns a unit flagged (carried forward by `skills/solve/capture.md`) and any `untestable:` items the gate surfaced. Omit the section entirely if there is nothing.}
