# PO daily overview — saved views setup

A 60-second daily check for the product owner. A few Linear saved views plus the forecast on
your engagement Project's description — at a glance, click-free.

## Why

You file problems; agents solve them. Your daily job is to keep the queue moving: notice
blockers, glance at what's in flight, and trust the forecast for the rest. This guide sets
up the saved views and points you at the forecast block so the whole check fits in a
minute, without clicking into any issue.

## View 1 — PO Daily: Active & Blocked

The working surface. Everything the team is touching right now, with blockers floating to
the top.

**Filter**

```text
Label is problem
Status is in: Todo, In Progress, In Review
```

**Group by**

```text
Status
```

**Sort**

```text
Label "blocked" first, then Priority
```

The `blocked` label is auto-managed by backlogd — `/backlogd:scope`, `/backlogd:solve`, and
`/backlogd:status` attach it to any active problem with an open `blocked-by` to a
non-completed/cancelled issue, and detach it when the blockers clear. You never tag it by
hand. See [skills/linear/blocked-label.md](../../skills/linear/blocked-label.md) for the
mechanics.

**Display options**

Open **Display options → Identifier** and toggle it **off**. Issue IDs (your team's prefix
plus a number) carry no meaning for the daily scan; hiding them lets titles lead. Keep
Priority, Assignee, and Labels visible so the `blocked` label is unmistakable.

## View 2 — Done this week

The "what landed" surface. Use it once a day to feel the cadence and catch anything that
slipped through review without you noticing.

**Filter**

```text
Label is problem
Status is Done
Completed at is past week
```

**Sort**

```text
Completed at, descending
```

No grouping needed — the chronological list is the point.

## View 3 — Waiting on me

The "I need a human" surface. The agent team runs to *needs you* whenever a problem carries
a `[manual]` acceptance criterion — a check only you can confirm (a UI render, on-brand-ness,
an external service actually receiving something). This view is the board-level signal for
exactly those problems, so a human-only check is first-class instead of buried in description
prose.

**Filter**

```text
Label is problem
Label is manual-pending
Status is in: Todo, In Progress, In Review
```

**Group by**

```text
Status
```

**Sort**

```text
Priority
```

The `manual-pending` label is auto-managed by backlogd — `/backlogd:scope` attaches it to any
problem whose acceptance criteria carry a `[manual]` item, `/backlogd:status` keeps it in sync
read-only, and `/backlogd:review` clears it once you've confirmed every `[manual]` check at
the verdict (the `accepted` close). You never tag it by hand. See
[skills/linear/manual-pending-label.md](../../skills/linear/manual-pending-label.md) for the
mechanics.

**Display options**

Open **Display options → Identifier** and toggle it **off** (same reasoning as View 1 —
titles lead the scan). Keep Priority, Assignee, and Labels visible so the `manual-pending`
label is unmistakable. An empty list means nothing is waiting on you — the happy state.

## View 4 — Delegated to agent

The "what has the agent picked up" surface. When backlogd starts a problem via
`/backlogd:solve`, it sets the issue's **Delegate** to `backlogd` (you stay the assignee —
delegation is additive, it never displaces you). This view is the board-level signal for
exactly those problems, so "an agent is on it" is visible at a glance without opening any
issue.

**Filter**

```text
Label is problem
Delegate is backlogd
```

`Delegate` lives among Linear's assignee-family fields, so look for it alongside **Assignee**
in the filter menu (the exact label and placement may differ by Linear plan/version — pick
the field whose value is the `backlogd` agent). The value `backlogd` is what `/backlogd:solve`
writes on every pickup; the same predicate drives the MCP-side query
`list_issues(delegate:"backlogd")`.

**Group by**

```text
Status
```

**Sort**

```text
Priority
```

**Display options**

Open **Display options → Identifier** and toggle it **off** (same reasoning as View 1 —
titles lead the scan). Keep Priority, Assignee, and Labels visible. An empty list means the
agent currently has nothing in flight.

The `delegate` write is set by the scrum-master through your normal user-OAuth MCP — there's
no key in the loop and you never set it by hand. It only resolves once the `backlogd` agent
exists in your workspace, so this view assumes the one-time install in
[agent-identity-setup.md](agent-identity-setup.md) is done; without it, `Delegate` has no
`backlogd` option and the view stays empty.

> **Optional stretch — Insights by delegate (unverified).** If your Linear plan includes
> **Insights**, a "Delegated to agent" *count over time* (group an Insights view by Delegate)
> would turn this saved view into a trend — how much the agent is carrying week over week.
> This is **not verified** here and is plausibly plan-gated: Insights and grouping by the
> Delegate dimension may be unavailable on lower tiers. Treat it as a try-it-if-you-have-it
> idea, not a documented step.

## Forecast

backlogd writes a `## 📊 Forecast` block to your engagement Project's **description** every
time `/backlogd:status` runs. Open the Project in Linear; the block sits at the top of the
description.

It looks like this:

```text
## 📊 Forecast

- **Velocity (7d):** 4.1 problems/day
- **Active queue:** 4 in-flight + 8 backlog = 12
- **Rough ETA to drain:** ~3 days
- **Stalled:** 1 problem blocked

_Last refreshed: 2026-05-28T07:30:00Z_
```

**What each line means**

- **Velocity (7d)** — problems moved to Done in the last 7 days, per day. A trailing
  indicator of pace.
- **Active queue** — `in_flight + backlog`. In-flight = problems in Todo, In Progress, or
  In Review. Backlog = unstarted problems still queued.
- **Rough ETA to drain** — `active_queue ÷ velocity`. Optimistic by design — it assumes
  the team keeps shipping at last week's pace.
- **Stalled** — count of problems currently carrying the `blocked` label (same signal View
  1 sorts on).
- **Last refreshed** — UTC timestamp of the most recent `/backlogd:status` run.

**Insufficient data**

When velocity is 0 (nothing closed in the last 7 days), the ETA line reads:

```text
**Rough ETA to drain:** insufficient data — close at least one problem this week to get a forecast
```

That's not a bug — it's the forecast telling you it has no signal yet. Close a problem,
re-run `/backlogd:status`, the number returns.

## What to do daily

Five quick steps, ~60 seconds total.

1. **Scan View 1's blockers section** — the `blocked` rows at the top. Each one is waiting
   on something. Resolve, re-prioritise, or comment "still blocked, here's why" so the
   agent knows you've seen it.
2. **Scan View 1's in-flight rows** — the rest of View 1. On the happy path *In Review* is
   transient — `/backlogd:solve` auto-chains the verdict review and merges a fully-green
   increment to Done (ship-on-green), so a problem sitting in *In Review* usually means it
   needs you: a NEEDS-PO/`[manual]` judgement call, or it was run with `--no-ship`. Open it,
   answer the question, or run `/backlogd:review` to re-verify and merge once it is clear.
3. **Check View 3 — Waiting on me** — the `manual-pending` rows. Each one is gated on a
   human-only `[manual]` check you owe the team. Open it, confirm the check at
   `/backlogd:review`, and the label clears itself on the accepted close. An empty View 3 is
   the happy state.
4. **Glance at View 4 — Delegated to agent** — the `Delegate is backlogd` rows. A one-second
   confirmation of what the agent has actively picked up; nothing here is an action item, it
   just tells you the loop is running. (Skip this step if you haven't installed the agent.)
5. **Glance at the Project's forecast block** — velocity, queue, ETA. If "insufficient
   data" persists past a couple of days, close or cancel something to break the silence.

If the blocker and waiting-on-me lists are calm, you're done. File the next problem when it
occurs to you and let the loop do the rest.
