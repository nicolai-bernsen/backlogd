# Launch post — LinkedIn (draft)

> **Status: DRAFT — publish at 1.0 only.** This is the copy for backlogd's one-time public
> launch on LinkedIn. The launch is spent _once_, at the 1.0 moment — not before. Two things
> gate publishing, and both are deliberately out of this file's scope:
>
> 1. **1.0 works end to end** — the Definition of 1.0 in [ROADMAP.md](ROADMAP.md) is declared
>    met (both gates have shipped: the standards-enforcing independent reviewer and the
>    dogfooded retrospective; what remains is the launch trio + the 1.0.0 bump).
> 2. **The demo recording exists** — recorded per the [demo runbook](demo-runbook.md) and
>    embedded in place of the placeholder slot below.
>
> Until then this stays a draft. The actual publish — pasting to LinkedIn with the recorded
> demo attached — is a human, in-the-world act (the `[manual]` acceptance criterion on
> [NB-398](https://linear.app/nicolai-bernsen/issue/NB-398)); this file exists to make that
> turnkey, not to be posted by anyone but the maintainer at launch.

The copy tells _one consistent story_ with the [README](../README.md): an agent _team_ that
runs real Scrum, any problem type, on your Claude subscription rather than API tokens; value
is _specialists × standards_; the independent reviewer that **blocks on a missing standard**
is the team-vs-single-agent moment. It is a _category_ claim, not a feature race — so it does
not frame backlogd as out-featuring any single-agent runner.

## The post

Paste this block as the LinkedIn post. Drop the recorded demo (see the slot) in as the
post's media, swap the `[demo: …]` line for whatever caption LinkedIn shows beside the
attachment, and publish. Keep the line breaks — they carry the rhythm.

```text
Code review became the bottleneck.

Then I realised Scrum was never about software. It is a loop for any
work that is hard to predict: shape a problem, do the smallest useful
slice, inspect it honestly, adapt. The software was incidental.

So I built an agent team that runs real Scrum — on my Claude
subscription, not API tokens.

It is called backlogd. It is not one agent doing one task. You act as
the Product Owner: you file a *problem*, not a spec. Slash commands play
the Scrum Master; subagent specialists play the Developers. The work can
be anything — "fix the failing pipeline," "write the Q3 board deck,"
"restructure these docs." Code and non-code alike.

The part I am proudest of: every increment goes through an *independent*
reviewer that checks it against its acceptance criteria and a standards
corpus — and when a one-way decision has no governing standard, it
**blocks and asks instead of guessing.** A single agent ships
plausible-wrong work. A team says "we need a rule for this." That one
move is the whole difference.

[demo: asciinema cast — backlogd solving one of its own problems, the
reviewer blocking on a missing standard. See docs/demo-runbook.md.]

How do I know the loop works? backlogd is built by running it on itself.
Its entire backlog is public — you can watch it manage its own
development, file a problem, or pick up an open one.

Honest about where it is: early but real. Both 1.0 gates have shipped —
the standards-enforcing reviewer, and a retrospective loop that reads
its own execution graph and files improvements back into the backlog
(already dogfooded). What is NOT in 1.0 yet, and I say so in the README:
an always-on headless runtime, and the richer agent-identity protocol.
No "production-ready" theatre.

If a team-shaped agent workflow — not a faster task runner — is a
category you have been waiting for, come kick the tyres or file a
problem.

Repo + public backlog: https://github.com/nicolai-bernsen/backlogd

#ClaudeCode #AIagents #Scrum
```

## Alternative hooks

Same body, different opening line — pick by audience. Each still leads with the _insight_,
never "I built a plugin."

```text
A) Code review became the bottleneck. Then I realised Scrum was never
   about software — so I built an agent team that runs it, on my Claude
   subscription, not API tokens.

B) Most "AI dev" tools are one agent doing one task. The thing I kept
   wanting was a team. Scrum already describes how good teams work — so
   I gave a team of agents the loop, not just the task.

C) I stopped writing specs for my agents. I started filing problems —
   and let an agent team run Scrum around them, on my Claude
   subscription, not API tokens.
```

## Short version

For a comment, a repost, or a length-capped channel. ~70 words.

```text
Code review became my bottleneck. Then it clicked: Scrum was never
about software. So I built backlogd — an agent *team* that runs real
Scrum on any problem (code or not), on my Claude subscription, not API
tokens. The hero move: an independent reviewer that blocks on a missing
standard instead of guessing. Early but real, and built by dogfooding
itself — the backlog is public.

https://github.com/nicolai-bernsen/backlogd
```

## Pre-publish checklist (for the maintainer, at 1.0)

- [ ] 1.0 declared in [ROADMAP.md](ROADMAP.md) and the `1.0.0` version bump landed.
- [ ] Demo recorded per [demo-runbook.md](demo-runbook.md); replace the `[demo: …]` slot with
      the attached cast/GIF and a one-line caption.
- [ ] README and this post still tell the same story — re-skim
      [README.md](../README.md) → _Status — honest, and on purpose_ for any drift since this
      draft (version number, what is / is not in 1.0).
- [ ] Repo link resolves and the backlog is public.
- [ ] Word count of the chosen post is comfortably inside LinkedIn's limit; hashtags trimmed
      to taste.
