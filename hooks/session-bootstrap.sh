#!/usr/bin/env sh
# backlogd — SessionStart bootstrap hook.
#
# Gives a fresh Claude Code session a short, accurate backlogd context block: the
# `/backlogd:*` verb summary and the Linear-MCP-only reminder (read from the committed
# hooks/session-bootstrap.md). If the session is inside a backlogd worktree, it also
# surfaces the problem ID (NB-<n>) and the current HEAD subject.
#
# Wired as a SECOND SessionStart hook in hooks/hooks.json (matchers startup, clear),
# alongside the generic identity guard (check-git-identity.sh) — additive, not a replacement.
#
# Contract:
#   - Emits the SessionStart JSON envelope on stdout ONLY in a backlogd checkout.
#   - Silent (no stdout) and exit 0 in any unrelated repo or non-git directory.
#   - Never errors — exits 0 even on empty stdin. No interpreter and no jq dependency.
#
# Output shape (Claude Code SessionStart JSON output):
#   {"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"<text>"}}

# Drain stdin so the hook never blocks; its content is not needed (the startup/clear
# matchers are enforced by hooks.json, not parsed here).
cat >/dev/null 2>&1 || true

# Resolve the directory holding this script, then the bootstrap markdown beside it.
# Works regardless of the caller's cwd (the script may be invoked by absolute path).
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd) || exit 0
bootstrap_md="$script_dir/session-bootstrap.md"

# --- backlogd-context gate -------------------------------------------------------------
# Emit ONLY when cwd is inside a backlogd checkout. Detect via stable, maintainer-neutral
# markers under the git toplevel: the scope command + the linear skill. Anything else
# (non-git dir, unrelated repo) exits cleanly and silently.
toplevel=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
[ -n "$toplevel" ] || exit 0
[ -f "$toplevel/commands/scope.md" ] || exit 0
[ -d "$toplevel/skills/linear" ] || exit 0
[ -f "$bootstrap_md" ] || exit 0

# --- assemble the context text ---------------------------------------------------------
# Start with the committed bootstrap block.
context=$(cat "$bootstrap_md") || exit 0

# Worktree detection: a backlogd worktree branch carries an `nb-<n>-` segment (Linear team
# key `nb`). When the current branch matches, surface NB-<n> + the last commit subject.
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)
case "$branch" in
  *nb-[0-9]*)
    # Extract the first nb-<digits> run and uppercase the team key to NB-<n>.
    num=$(printf '%s\n' "$branch" | sed -n 's/.*[^a-z]nb-\([0-9][0-9]*\).*/\1/p; s/^nb-\([0-9][0-9]*\).*/\1/p' | head -n 1)
    if [ -n "$num" ]; then
      subject=$(git log -1 --pretty=%s 2>/dev/null || true)
      context="$context

---

**Worktree context.** This session is inside a backlogd worktree for problem **NB-$num**.
- Branch: \`$branch\`
- HEAD: $subject"
    fi
    ;;
esac

# --- emit the SessionStart JSON envelope -----------------------------------------------
# JSON-escape the assembled context into a single string value (backslash, double-quote,
# and control chars per RFC 8259), then print the envelope. Pure awk — no jq.
printf '%s' "$context" | awk '
  BEGIN { out = "" }
  {
    if (NR > 1) out = out "\\n"
    line = $0
    esc = ""
    n = length(line)
    for (i = 1; i <= n; i++) {
      c = substr(line, i, 1)
      if (c == "\\") esc = esc "\\\\"
      else if (c == "\"") esc = esc "\\\""
      else if (c == "\t") esc = esc "\\t"
      else if (c == "\r") esc = esc "\\r"
      else esc = esc c
    }
    out = out esc
  }
  END {
    printf "{\"hookSpecificOutput\":{\"hookEventName\":\"SessionStart\",\"additionalContext\":\"%s\"}}\n", out
  }
'

exit 0
