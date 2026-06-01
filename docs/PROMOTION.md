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
| r/ClaudeAI | Reddit | Launch post — Draft A (held locally) |
| Hacker News | Show HN | Launch post — Draft B (held locally) |
| X / Twitter | Personal account | Launch thread — Draft C (held locally) |

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

## Launch-post drafts

The verbatim launch copy — **Draft A** (r/ClaudeAI), **Draft B** (Show HN),
**Draft C** (X / Twitter), and the LinkedIn post — is kept **out of this public
tree** until launch: spend-once copy whose value is the launch moment. The
maintainer holds it locally (gitignored `.launch/`), and it also lives on the
relevant Linear problems. The plan and sequencing above stay public; the copy
goes live when it's posted.

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
- [x] Promotion plan (this file — NB-315); launch-post drafts held locally (`.launch/`).
- [ ] Awesome-list PRs (PO step).
- [ ] r/ClaudeAI + Show HN + X — drafts held locally in `.launch/` (PO step).

## Notes for the PO

- The launch drafts (held locally in `.launch/`) are intentionally first-person
  and editable — refine the voice and concrete examples before posting.
- Recommend posting **after** the social preview is uploaded — otherwise the
  shared OG cards look bare and the launch loses credibility on first
  impression.
- Discussions is enabled but empty — seed it with a *"Welcome / what are you
  using backlogd for?"* thread before the launch push so newcomers land on
  something alive.
- Only one launch channel per day. Don't bunch them — each post deserves its
  own conversation.
