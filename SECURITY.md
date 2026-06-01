# Security policy

## Reporting a vulnerability

Please do not file security issues as public GitHub issues.

Instead, send a description to <simon.filler@tu-dortmund.de>. Include:

- A description of the issue and its potential impact.
- Steps to reproduce, or a minimal proof-of-concept.
- Affected version / commit hash.
- Whether you would like to be credited in the fix announcement.

You can expect an initial acknowledgement within 7 days. Triage and a fix timeline follow once the report is confirmed.

## Scope

In scope:

- The Python application code in `talktrace_ai/`.
- The launcher scripts (`start.sh`, `start.bat`, `dev.sh`, `dev.bat`).
- Bundled configuration defaults in `talktrace_ai/config/`.

Out of scope:

- Vulnerabilities in upstream dependencies (please report to the dependency directly; we will pin/upgrade once a fix is available).
- Vulnerabilities in third-party LLM providers reachable from the app.
- Issues that require physical access to the user's machine.

## Supported versions

Only the latest tagged release receives security fixes.
