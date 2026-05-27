# The /docs living-spec contract

Generic guidance for any repository worked on by an automated developer. It defines how
`/docs` is used as the **living specification**, and how that relates to the **static
specification** carried by the work item being implemented.

## Two specifications

A unit of work has two specifications, and they play different roles:

- **Static spec — the work item.** The tracked issue being implemented *is* the
  specification for that unit of work. Its description states the problem and intent, and
  its `## Acceptance Criteria` section is the **canonical, binding contract** for "done." It
  is fixed for the life of the work item — the immovable target.
- **Living spec — `/docs`.** The repository's `/docs` directory is the **source of truth**
  for how the system actually works: architecture, conventions, and the decisions behind
  them. It evolves continuously as the system changes.

The static spec says *what to build now*; the living spec says *how this system is built*.
The developer reconciles the two: satisfy the work item's acceptance criteria **in a way
that is consistent with the living spec**, then keep the living spec true afterwards.

## Rules

1. **Consult `/docs` before developing.** Before writing code for a work item, read the
   parts of `/docs` relevant to the area being changed. Treat it as the authority on
   existing architecture and conventions; do not contradict it without cause.
2. **Update `/docs` when behaviour changes.** When the work changes how the system behaves —
   a new capability, a changed contract, a new convention — update the affected `/docs` page
   in the same change, so the living spec stays true. Documentation drift is a defect.
3. **The work item's `## Acceptance Criteria` is the binding target.** When `/docs` and the
   work item disagree about *what to build now*, the acceptance criteria win for that unit of
   work — then reconcile `/docs` (update it, or record the divergence) so the two agree again.

## When a repository has no `/docs`

If the repository has no `/docs` directory, treat the work item — its description and
`## Acceptance Criteria` section — as the **sole** source of truth. Do **not** create a
`/docs` directory without an explicit instruction to do so. Proceed with the work, and note
the absence of a living spec in the progress report so a human can decide whether one should
exist.

## Keeping it lightweight

The living spec earns its keep by being read. Keep pages concise and current rather than
exhaustive: a short page that is true beats a long one that has rotted. Add depth only when a
real decision or a recurring confusion warrants it.
