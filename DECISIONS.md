# DECISIONS

## Locked Decisions

- Final project name: FailWarden Orchestrator
- Short name: fwo
- V1 boundary is strict and intentionally constrained
- SSH is the only transport in V1
- Escalation is terminal in V1
- Dry-run performs no remote execution
- Line length limit: 88
- `./check.sh` is required during reviewable phase gates
- `gitleaks` runs before every commit via pre-commit hook
- Direct pushes to `main` are blocked locally by pre-push hook
- Security is a top-level requirement for all phases
- Code style targets readability for average infrastructure engineers
- Sensitive local files must use `.local.*` naming and stay out of Git

## ADR Process

Major decisions are recorded when made, not retroactively.
