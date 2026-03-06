# FailWarden Orchestrator

FailWarden Orchestrator is a constrained, auditable YAML runbook executor for
infrastructure remediation over SSH.

## Status

Step 3 in progress: compile/validation layer implemented and tested.
Execution engine runtime is still intentionally not implemented yet.

## V1 Boundaries

V1 is intentionally SSH-only, CLI-only, SQLite-backed, and escalation-focused.
It is not a general-purpose automation platform.

Out of scope for V1 includes dashboards, additional executors/transports,
enterprise integrations, RBAC/multi-tenancy, approvals, and checkpoint/resume.

## Project Layout

- `src/`: Python package source
- `tests/`: test suite
- `runbooks/`: shipped runbooks
- `docs/`: architecture and design documents

## Development Checks

Run:

```bash
./check.sh
```

This script runs formatting, linting, security checks, and tests.

Pre-commit secret scanning is also enforced with `gitleaks` via
`.githooks/pre-commit`.
