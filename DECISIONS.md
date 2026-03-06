# DECISIONS

## Locked V1 Decisions

- Final name: FailWarden Orchestrator (`fwo` CLI)
- Strictly constrained V1 scope with SSH-only transport
- YAML runbook model with compile-before-execute policy
- SQLite-first persistence for low lab overhead
- Explicit linked-step branching in runbook YAML
- Escalation is terminal and notifiers are best-effort fan-out
- Dry-run never executes remote commands
- Code line length limit: 88
- Security-first defaults and clear failure logging

## Workflow Decisions

- `./check.sh` is required in reviewable phases
- `gitleaks` pre-commit scanning is mandatory
- Direct pushes to `main` are blocked locally
- Conventional commit style is used

## ADR Notes

- `why YAML`: separates orchestration intent from Python implementation
- `why SQLite`: auditability without service dependencies
- `why SSH-only`: finishable and testable V1 with one transport story
- `why no dashboard in V1`: avoid UI overhead before core engine maturity
- `why end step`: clear success terminal separate from escalation terminal
