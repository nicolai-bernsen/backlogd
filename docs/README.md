# backlogd docs

The **living specification** for backlogd — how the system works, and the conventions for
working in it.

Linear holds the **static** spec (a problem and its acceptance criteria); this `/docs`
directory holds the **living** spec (how the system is built, and why).

## Start here

- **[Overview](overview.md)** — what backlogd is, and the problem → dispatch → result loop.
- **[Conventions](conventions.md)** — branching, Linear usage, and docs conventions.
- **[The /docs living-spec contract](living-spec-contract.md)** — how `/docs` is used as the
  source of truth and living spec. Written generically: it applies to any repository worked
  on by an automated developer.

## In one line

Consult `/docs` before developing; update it when behaviour changes. For any single piece of
work, the work item's `## Acceptance Criteria` section is the binding target.
