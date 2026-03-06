# ARCHITECTURE

## Intent

FailWarden Orchestrator keeps V1 small, testable, and auditable.

## Layers

- CLI layer (`fwo compile`, `fwo run`)
- Compile layer (YAML parse, schema, semantic checks, template rendering)
- Execution engine (step walking, retries, timeout passing, branching)
- Executor layer (SSH)
- Notifier layer (Slack and email)
- Persistence layer (SQLite)
- Audit layer (structured log files)

## Core Contracts

- `RunbookCompiler`: produces `CompiledRunbook` or validation errors
- `ExecutionEngine`: runs compiled runbooks deterministically
- `BaseExecutor`: transport contract returning normalized results
- `BaseNotifier`: notifier contract returning normalized outcomes
- `SQLiteAuditStore`: execution and step/notifier persistence
- `AuditLogger`: append-only structured log lines per execution

## Data Flow

1. CLI parses args and vars.
2. Compiler validates and renders runbook.
3. Engine walks steps from `entry_step`.
4. SSH steps execute with timeout + retry policy.
5. Branching chooses next step via `on_success` / `on_failure`.
6. Escalation step fans out to configured notifiers.
7. Persistence and audit layers capture every attempt and outcome.

## V1 Security Posture

- strict host key verification in SSH executor
- no secrets committed in runbooks
- pre-commit secret scanning with `gitleaks`
- conservative defaults and explicit failure recording
