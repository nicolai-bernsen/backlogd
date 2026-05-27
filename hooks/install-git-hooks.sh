#!/usr/bin/env sh
# backlogd — install the repo's git hooks (the identity guard).
#
# Points git at the committed hooks dir and, optionally, sets the expected identity.
# Idempotent; safe to re-run. Usage:
#   sh hooks/install-git-hooks.sh                 # activate the hook
#   sh hooks/install-git-hooks.sh you@example.com # activate + set expected identity
set -e

root="$(git rev-parse --show-toplevel)"
git -C "$root" config core.hooksPath hooks/git
printf 'backlogd: core.hooksPath -> hooks/git (identity pre-commit hook active).\n'

if [ -n "$1" ]; then
  git -C "$root" config backlogd.expectedEmail "$1"
  printf 'backlogd: backlogd.expectedEmail -> %s\n' "$1"
elif [ -z "$(git -C "$root" config --get backlogd.expectedEmail 2>/dev/null || true)" ]; then
  printf 'backlogd: set your expected identity to arm the guard:\n'
  printf '  git config backlogd.expectedEmail you@example.com\n'
fi
