# Security Policy

## Reporting a vulnerability

Please don't open a public issue for security problems.

Instead, use GitHub's private vulnerability reporting ("Report a vulnerability" under
the repository's Security tab), or email <nicolai.bernsen@gmail.com> directly.

Include enough detail to reproduce the issue. I'll acknowledge within a few days and
keep you posted on a fix.

## Scope

backlogd orchestrates AI agents and talks to external services (Linear, git hosts).
The most sensitive surface is credential handling — API keys and tokens. If you find a
way for secrets to leak into logs, commits, or agent context, that's worth reporting.

The runtime loop is key-free: it reaches Linear only through the official Linear MCP
(OAuth), so no API key is ever read by the scrum-master commands or the agents they
dispatch. The single exception is the optional, one-time `/backlogd:init` bootstrap. It
reads a local Linear Admin API key from `~/.backlogd/credentials.env` (or the
`LINEAR_API_KEY` environment variable) — a path **outside** the repo. The key is read
only by the setup engine's network layer (`scripts/linear_setup.py`); the orchestrator
never loads the key value into agent context, never echoes it, and never places it on a
command line, and the key is never logged or committed. A leak of that key into logs,
commits, or agent context would be a reportable issue.

## Supported versions

This is pre-1.0 software. Only the latest commit on `main` is supported.
