# PO daily overview — saved views setup

A 60-second daily check for the product owner. Two Linear saved views plus the forecast on
your engagement Project's description — at a glance, click-free.

## Why

You file problems; agents solve them. Your daily job is to keep the queue moving: notice
blockers, glance at what's in flight, and trust the forecast for the rest. This guide sets
up the two saved views and points you at the forecast block so the whole check fits in a
minute, without clicking into any issue.

## View 1 — PO Daily: Active & Blocked

The working surface. Everything the team is touching right now, with blockers floating to
the top.

**Filter**

```
Label is problem
Status is in: Todo, In Progress, In Review
```

**Group by**

```
Status
```

**Sort**

```
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

```
Label is problem
Status is Done
Completed at is past week
```

**Sort**

```
Completed at, descending
```

No grouping needed — the chronological list is the point.

## Forecast

backlogd writes a `## 📊 Forecast` block to your engagement Project's **description** every
time `/backlogd:status` runs. Open the Project in Linear; the block sits at the top of the
description.

It looks like this:

```
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

```
**Rough ETA to drain:** insufficient data — close at least one problem this week to get a forecast
```

That's not a bug — it's the forecast telling you it has no signal yet. Close a problem,
re-run `/backlogd:status`, the number returns.

## What to do daily

Three steps, ~60 seconds total.

1. **Scan View 1's blockers section** — the `blocked` rows at the top. Each one is waiting
   on something. Resolve, re-prioritise, or comment "still blocked, here's why" so the
   agent knows you've seen it.
2. **Scan View 1's in-flight rows** — the rest of View 1. Anything stuck in In Review
   longer than feels right? Run `/backlogd:review` on it.
3. **Glance at the Project's forecast block** — velocity, queue, ETA. If "insufficient
   data" persists past a couple of days, close or cancel something to break the silence.

If all three are calm, you're done. File the next problem when it occurs to you and let the
loop do the rest.
