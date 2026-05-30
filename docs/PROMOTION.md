# Promotion plan

backlogd's on-repo discoverability surfaces are set up (NB-313 / NB-314). This
document covers where to take it from here — the **external** outreach the PO
publishes.

## Target communities

| Community | Channel | What to submit |
| --- | --- | --- |
| `awesome-claude-code` | PR to the repo | Add backlogd under *Tools / Workflow* |
| `awesome-claude-code-plugins` | PR to the repo | Add backlogd as a Linear-backed scrum plugin |
| Claude Code plugin directory | Pending official directory | Submit listing once available |
| r/ClaudeAI | Reddit | Launch post — see Draft A |
| Hacker News | Show HN | Launch post — see Draft B |
| X / Twitter | Personal account | Launch thread — see Draft C |

## Sequencing

1. **Awesome lists first.** Open PRs to `awesome-claude-code(-plugins)` — low
   effort, high signal. These pages are linked from many "discovering Claude
   Code" guides.
2. **Reddit launch (Draft A).** Once at least one awesome-list PR lands, post
   on r/ClaudeAI.
3. **Show HN (Draft B).** Two days after the Reddit post — gives Reddit a
   window of its own.
4. **X thread (Draft C).** Same day as Show HN. Amplifies it.
5. **Watch Discussions + issue tracker.** Triage incoming questions; nudge
   first-time contributors toward the `good first issue` queue.

---

## Draft A — r/ClaudeAI

> **Title:** I built a Claude Code plugin that turns Claude into a problem-driven scrum team (Linear-backed)
>
> **Body:**
>
> I wanted Claude Code to feel less like an assistant and more like a small
> team I could hand work to. So I built `backlogd` — a Claude Code plugin
> where you file a *problem* in Linear and Claude takes it from there.
>
> The loop:
>
> 1. You file a Linear issue with the `problem` label — one sentence is enough.
> 2. `/backlogd:scope` shapes it: writes acceptance criteria, decomposes into
>    sub-issues if it earns it, sets priority, stops.
> 3. `/backlogd:solve` picks it up: walks dependencies, dispatches an
>    isolated developer per unit, posts updates back to Linear, opens a PR
>    when there's code.
> 4. `/backlogd:review` gates the PR. `/backlogd:release` promotes dev → main.
>
> Claude is the scrum master, the developer, and the release engineer. You're
> the PO — you accept results, not code reviews.
>
> No API keys: Linear access is via the official Linear MCP (OAuth).
>
> Repo: <https://github.com/nicolai-bernsen/backlogd>
>
> Curious what people think — especially anyone using Linear with Claude Code
> already.

## Draft B — Show HN

> **Title:** Show HN: backlogd — a Linear-backed problem-driven scrum team for Claude Code
>
> **Body:**
>
> `backlogd` is a Claude Code plugin that turns Claude into a one-person
> scrum team backed by Linear.
>
> File a problem (one Linear issue with the `problem` label). Run
> `/backlogd:scope` — Claude writes acceptance criteria and decomposes the
> work. Run `/backlogd:solve` — Claude walks the dependency graph, dispatches
> an isolated worktree per sub-issue, commits, opens a PR, and posts a
> PO-facing solution brief back to Linear. `/backlogd:review` gates the PR;
> `/backlogd:release` promotes dev → main.
>
> Self-dogfooded: backlogd's own backlog (including the `/backlogd:release`
> command itself) was filed → scoped → solved → released using its own loop.
> v0.8.1 was released hands-off by `/backlogd:release`.
>
> Architecture notes:
>
> - Official Linear MCP — no API keys.
> - Hybrid write split, tool-enforced: orchestrator owns Linear structure;
>   developer subagent only writes its own progress comment on its own issue.
> - Worktree isolation per problem so parallel sessions can't yank each
>   other's HEAD.
>
> Repo: <https://github.com/nicolai-bernsen/backlogd>
>
> Built as a clean-room public companion to a private SDD framework I use
> day-to-day. Feedback welcome.

## Draft C — X / Twitter thread

> 1/ I built a Claude Code plugin that turns Claude into a small scrum team.
>
> You file a problem in Linear. Claude scopes it, solves it, opens the PR,
> and writes the release. You stay the PO. 🧵
>
> 2/ The loop is four commands:
>
>     /backlogd:scope    — shape a problem (AC + decomposition)
>     /backlogd:solve    — execute (worktree → commit → PR)
>     /backlogd:review   — gate the PR
>     /backlogd:release  — dev → main
>
> 3/ Why Linear? It's the control plane. Comments are the audit trail. State
> transitions are the workflow. No bespoke state files — Linear holds
> everything.
>
> No API keys either — Linear access is via the official MCP (OAuth).
>
> 4/ Self-dogfooded. backlogd's own release command was filed → scoped →
> solved → released through its own loop. Including the time it had to fix
> its own broken §6.
>
> 5/ Public, clean-room: <https://github.com/nicolai-bernsen/backlogd>
>
> Drop a ⭐ if it looks useful — curious what people build with it.

---

## Asset checklist

- [x] Repo description set (NB-313).
- [x] Repo topics added (NB-313).
- [x] Discussions enabled (NB-313).
- [x] Releases published for `v0.1.1` → `v0.8.2` (NB-313).
- [ ] Social preview image uploaded via *GitHub → Settings → Social preview*
      (asset committed at `.github/social-preview.png`; `gh` has no API for
      this upload — **PO step**).
- [x] `CODE_OF_CONDUCT.md` + `.github/ISSUE_TEMPLATE/*` on `main` (NB-314).
- [x] `good first issue` issues filed (NB-314 — gh#42, gh#43).
- [x] Promotion plan + drafts (this file — NB-315).
- [ ] Awesome-list PRs (PO step).
- [ ] r/ClaudeAI + Show HN + X — see drafts above (PO step).

## Notes for the PO

- The drafts above are intentionally first-person and editable — refine the
  voice and concrete examples before posting.
- Recommend posting **after** the social preview is uploaded — otherwise the
  shared OG cards look bare and the launch loses credibility on first
  impression.
- Discussions is enabled but empty — seed it with a *"Welcome / what are you
  using backlogd for?"* thread before the launch push so newcomers land on
  something alive.
- Only one launch channel per day. Don't bunch them — each post deserves its
  own conversation.
