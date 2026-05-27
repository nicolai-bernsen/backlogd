#!/usr/bin/env sh
# backlogd — git identity guard (shared by the pre-commit hook and the SessionStart hook).
#
# Compares the active `git config user.email` against the per-repo expected identity
# in `git config backlogd.expectedEmail`. It is OPT-IN and generic: if the expected
# identity is unset, the check is a no-op — so it never fires for unrelated repos or
# for users who haven't configured it. backlogd sets it locally; other users set their own.
#
# Exit 0 = OK (match, or no expected identity configured).
# Exit 1 = mismatch (the caller decides whether to warn or hard-block).
#
# Why this exists: a git worktree whose path doesn't match a personal `includeIf`
# silently falls back to the machine's global (e.g. work) email, so commits can land
# under the wrong identity. This asserts identity rather than trusting `includeIf`.

expected="$(git config --get backlogd.expectedEmail 2>/dev/null || true)"
[ -z "$expected" ] && exit 0   # not configured → no-op (opt-in)

actual="$(git config --get user.email 2>/dev/null || true)"
if [ "$actual" != "$expected" ]; then
  printf 'backlogd: git identity mismatch — user.email is "%s", expected "%s".\n' "${actual:-<unset>}" "$expected" >&2
  printf '  Fix:  git config user.email "%s"\n' "$expected" >&2
  printf '  (change the expectation with: git config backlogd.expectedEmail <addr>)\n' >&2
  exit 1
fi
exit 0
