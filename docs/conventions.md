# backlogd — conventions

Conventions for working in this repository. Lightweight by design — they grow as problems
are solved.

## The two specifications

- **Linear is the static spec.** A unit of work is defined by its Linear issue: the
  description (intent) and the `## Acceptance Criteria` section (the binding "done" contract).
  For **promoted Project-form** problems, the spec + `## Acceptance Criteria` live in the
  Project's **"Spec" Document** instead — the description carries a summary + a pointer.
  Single-Issue and sub-issue forms keep the description-canonical model unchanged.
- **`/docs` is the living spec.** Consult it before developing; update it when behaviour
  changes. See the [living-spec contract](living-spec-contract.md).

## Branching & PRs

- Flow: `feature → dev → main`. `main` is release-only; `dev` is the integration branch.
- Branch from `dev`, named `nicolaibernsen/nb-<n>-<slug>`; open the PR **into `dev`**;
  squash-merge.
- `main` is reached by promoting `dev` — that promotion is a release.
- See [CONTRIBUTING](../CONTRIBUTING.md) for the full flow.

## Linear

- A **problem** is a Linear issue carrying the `problem` label — that, and only that, is what
  the scrum-master picks up.
- All Linear access goes through the official Linear MCP server — there are no API keys.

## Docs

- Keep pages concise (roughly one screen). Prefer true-and-short over exhaustive-and-stale.
- Document **observable behaviour** — what agents and users do — not internal tooling.
