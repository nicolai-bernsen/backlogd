# Security Policy

## Reporting a vulnerability

Please don't open a public issue for security problems.

Instead, use GitHub's private vulnerability reporting ("Report a vulnerability" under
the repository's Security tab), or email nicolai.bernsen@gmail.com directly.

Include enough detail to reproduce the issue. I'll acknowledge within a few days and
keep you posted on a fix.

## Scope

backlogd orchestrates AI agents and talks to external services (Linear, git hosts).
The most sensitive surface is credential handling — API keys and tokens. If you find a
way for secrets to leak into logs, commits, or agent context, that's worth reporting.

## Supported versions

This is pre-1.0 software. Only the latest commit on `main` is supported.
