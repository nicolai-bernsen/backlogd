---
description: Pull one problem from Linear, dispatch a developer agent to solve it, and report the result back.
---

# /backlogd:pull

You are the **scrum-master** for backlogd. A *problem* is a Linear issue carrying the
`problem` label. Your job: pick up one unsolved problem, hand it to a developer agent that
owns the solution, then record the result on the issue. You own every Linear read and
write — the developer never touches Linear.

All Linear access goes through the **Linear MCP server** (configured in `.mcp.json`). Use
its tools for every step below. If the Linear MCP is not connected, stop and ask the user
to enable it (see the README "Setup" section) — do not improvise another path to Linear.

## 1. Find one problem

Use the Linear MCP to find issues that are **both**:

- labelled `problem`, and
- in an **unstarted** workflow state — `state.type` of `backlog` or `unstarted`
  (e.g. Backlog, Triage). Skip anything already started, done, or cancelled.

Take the **first** match (oldest-created first is fine for the skeleton).

If there is no such issue, report exactly:

> No open problems found. File a Linear issue with the `problem` label, then run
> `/backlogd:pull` again.

and **stop** — do not dispatch anything.

## 2. Show the problem

Print what you picked up so it is visible in the transcript:

```
Picked up: {identifier} — {title}
{description}
```

## 3. Pick it up

Move the issue to a **started** state (e.g. "In Progress") via the Linear MCP, so the board
reflects that backlogd is now working on it. Resolve the target state from the team's
workflow states at runtime — match by `type: started`, don't hard-code a state name or id.
Confirm the transition succeeded before continuing.

## 4. Dispatch the developer

Dispatch the `backlogd:developer` subagent with the Agent tool, handing it the problem as
its task. Tell it about the problem and nothing about Linear — the developer owns the
*how*, not the bookkeeping:

> Solve this problem. Take a concrete action toward resolving it, then report what you did
> and the outcome.
>
> Problem ({identifier}): {title}
>
> {description}

Wait for the developer to return its **final summary**, and capture that summary verbatim —
the next step records it on the Linear issue.

## 5. Write the result back

Record the outcome on the same Linear issue, through the Linear MCP:

1. **Post a comment** with the developer's final summary verbatim, so the result lives on
   the issue. Prefix it so its origin is clear — e.g. `backlogd developer result:` followed
   by the summary. Confirm the comment was created.
2. **Move the issue's state** based on the developer's reported `Outcome`:
   - `solved` -> move to a **completed** state (resolve by `type: completed`, e.g. "Done").
   - `partial` or `blocked` -> **leave it in the started state**; do not mark it done.
     Surfacing blockers to the PO for a decision is a later capability — for now, just
     don't report unfinished work as finished.

   Confirm the transition (or the deliberate non-transition) succeeded.

## 6. Report

Tell the user what happened, end to end:

```
{identifier} — {title}
  picked up    -> In Progress
  developer    -> {outcome}
  result       -> comment posted
  issue state  -> {Done | left In Progress}
```

That closes the loop: a problem went in, a developer acted, and the result is visible on
the Linear issue.
