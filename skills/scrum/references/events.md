# Scrum events — reference

The five Scrum events mapped to backlogd's commands. This is the concept reference
behind [`../SKILL.md`](../SKILL.md); read it when you need to decide which command a
given moment in the loop belongs to. For the canonical text, see
[`../../../docs/scrum/scrum-guide.md`](../../../docs/scrum/scrum-guide.md) → *Scrum
Events*.

## The five events

The Scrum Guide names a containing event (the Sprint) and four formal events inside
it (Sprint Planning, the Daily Scrum, the Sprint Review, the Sprint Retrospective).
The Scrum Guide says (verbatim):

> *The Sprint is a container for all other events. Each event in Scrum is a formal
> opportunity to inspect and adapt Scrum artifacts. […] Events are used in Scrum to
> create regularity and to minimize the need for meetings not defined in Scrum.*
>
> — *The 2020 Scrum Guide*, Scrum Events.

backlogd maps all five to commands. The Sprint Retrospective lands as
**`/backlogd:retro`** — a milestone-scoped, graph-grounded look-back that files candidate
improvements for the PO to prioritize.

## Mapping

| Scrum event | backlogd command | What the command does |
| --- | --- | --- |
| **The Sprint** (container, fixed length ≤ 1 month) | **Continuous flow — no fixed-length sprint.** | backlogd runs **one problem per loop**: pickup → solve → review → release. The "Sprint" container is the *single problem's loop* from `solve`-claim to `review`-accept. No calendar timebox. See [`../SKILL.md`](../SKILL.md) → *The Sprint — backlogd's continuous-flow interpretation*. |
| **Sprint Planning** — initiates the Sprint; produces the Sprint Backlog (why / what / how) | **`/backlogd:scope`** | Picks a `problem`-labelled issue, writes the spec + `## Acceptance Criteria` into the description, decomposes on discovery (sub-issues + `blocked-by`, or promotes to a Project), sets priority. Produces the Sprint-Backlog-equivalent for that one problem. No solving; no state change to *In Progress*. |
| **Daily Scrum** — 15-minute Developer event to inspect progress toward the Sprint Goal and adapt the plan | **`/backlogd:status`** | Surveys active `problem` issues, reads decomposition / states / `blocked-by`, reports progress + blockers to the PO. **Read-only — writes nothing.** Same inspection function as the Daily Scrum; plan adaptation lives in `solve`, not here. |
| **Sprint Review** — inspects the outcome of the Sprint; stakeholders decide what next | **`/backlogd:review`** | Verifies an *In Review* problem against its `## Acceptance Criteria` and the Definition of Done. All met → Done; gaps → back to *In Progress* with rework notes; genuine judgement call → ask the PO. |
| **Sprint Retrospective** — inspects how the last Sprint went; identifies improvements | **`/backlogd:retro`** | Over a completed **milestone** (primary; cycle-end as a cadence safety-net, and on-demand `--cycle` / `--since` / `--last` selectors), reads the **execution graph** (`scripts/graph.py report --json`: rework, latency, blockers, partials) as objective evidence, detects **cross-issue patterns** no single review can see, classifies each learning (recurring failure → ADR/standard · process problem → framework bug · one-off → noted), and **files the load-bearing ones as candidate `kind:improvement` issues**. The retro proposes; the PO prioritizes. Closes the adaptation pillar. See `skills/retro/SKILL.md`. |

> **`/backlogd:solve` is not a Scrum event.** It is the *execution* of the Sprint
> Backlog produced by `/backlogd:scope` — the Developers' work *during* the Sprint,
> not a ceremony around it. It claims units (move to *In Progress*), dispatches the
> developer subagent per unit in `blocked-by` order, and hands back to *In Review*
> with a PO-facing brief.
>
> **`/backlogd:release` is not a Scrum event either.** It is the engineering counter-
> part to the Increment's "usable" property: it promotes the integration branch to a
> tagged release. In Scrum, releases happen *within* the Sprint — an Increment may
> ship at any time. backlogd's `release` is the mechanical recipe (version bump,
> merge, tag, back-merge) for that shipping.

## When to use which command

| Moment | Use |
| --- | --- |
| A new `problem` was just filed; is it shaped? | `/backlogd:scope` — write the AC, decompose, set priority. |
| The top of the backlog is shaped and ready to execute | `/backlogd:solve` — claim, dispatch developers, hand back to *In Review*. |
| The PO asks "where are we?" — no writes expected | `/backlogd:status` — survey and report. |
| A problem is *In Review* and waiting on a verdict | `/backlogd:review` — verify against AC + DoD; accept or send back. |
| `dev` is green and the PO wants a release cut | `/backlogd:release` — bump, merge, tag. |
| A milestone closed (or the PO wants to "look back on the last few problems") | `/backlogd:retro` — read the graph, detect cross-issue patterns, file candidate improvements. Defaults to the most-recent milestone; `--cycle` / `--since` / `--last` for other scopes. |

## What is intentionally not here

- **Sprint cancellation.** The Scrum Guide allows the PO to cancel a Sprint when the
  Sprint Goal becomes obsolete. backlogd's equivalent — cancelling an in-flight
  problem — is a manual PO action in Linear (set the issue to *Canceled*). There is
  no dedicated command.
- **Refinement meetings.** Backlog refinement in the Scrum Guide is an ongoing
  activity, not an event — backlogd's version is the PO editing problems in Linear
  and `/backlogd:scope` shaping them on pickup. No standing meeting.
- **Estimation ceremonies.** The Scrum Guide does not prescribe story points;
  backlogd does not prescribe estimates either (Linear's `estimate` field is optional
  and backlogd defaults to one-point-per-issue when off — see
  [`../../linear/references/linear-model.md`](../../linear/references/linear-model.md)
  → *Other fields*).

## See also

- [`../SKILL.md`](../SKILL.md) — the playbook these events feed into.
- [`accountabilities.md`](accountabilities.md) — who runs each event in backlogd.
- [`values.md`](values.md) — which value tends to come under pressure at each event.
- [`../../../docs/scrum/scrum-guide.md`](../../../docs/scrum/scrum-guide.md) → *Scrum
  Events* — the canonical text.
- [`../../../docs/scrum/mapping.md`](../../../docs/scrum/mapping.md) — the full
  Scrum → backlogd translation table.
