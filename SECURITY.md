# Security Policy

## Reporting a vulnerability
Please do not open a public issue for security problems. Use GitHub's private
[security advisory form](https://github.com/Kaushik2210/daily-automation-scripts/security/advisories/new)
and include the script name, what you found, and steps to reproduce.

You can expect an initial reply within a few days.

## Scope and safe use
- Scripts never ship with credentials. Tokens are read from environment variables.
- Scripts that change files default to `--dry-run` and need `--apply`.
- Network and security tools (port scanning, TLS checks and similar) are meant for
  your own machines and services only. Do not point them at systems you don't own
  or have permission to test.
