#!/bin/sh
# check-agent-identity-adr.sh — thin structural checker for ADR-001.
#
# Asserts that the visible-agent-identity ADR exists and carries the five
# sections backlogd's ADR shape requires (Status · Context · Considered
# Options · Decision · Consequences). Dependency-free POSIX sh; exits 0 when
# the ADR is well-formed, non-zero (with a diagnostic) otherwise.
#
# Run from the repo root:  sh scripts/ci/check-agent-identity-adr.sh
#
# Established by NB-370 alongside docs/standards/adrs/ — the first entry in
# backlogd's ADR convention.

set -eu

ADR="docs/standards/adrs/ADR-001-visible-agent-identity-in-linear.md"

# Required headings, matched as Markdown headings (one or more leading '#'
# then the literal text). Keep this list in lockstep with the ADR shape.
REQUIRED="Status Context \"Considered Options\" Decision Consequences"

fail=0

if [ ! -f "$ADR" ]; then
  echo "FAIL: ADR not found at $ADR" >&2
  exit 1
fi

# Use eval so the quoted multi-word heading ("Considered Options") survives
# word-splitting as a single token.
eval "set -- $REQUIRED"
for heading in "$@"; do
  # Match a Markdown heading line: leading '#'s, optional space, the text.
  if ! grep -Eq "^#{1,6}[[:space:]]+.*${heading}" "$ADR"; then
    echo "FAIL: $ADR is missing required heading: ${heading}" >&2
    fail=1
  fi
done

if [ "$fail" -ne 0 ]; then
  exit 1
fi

echo "OK: $ADR present with all required sections (Status, Context, Considered Options, Decision, Consequences)"
