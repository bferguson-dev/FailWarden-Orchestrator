# Execution Model

## Compile Flow

1. Parse YAML into runbook object.
2. Validate structure against JSON Schema.
3. Run semantic checks (graph integrity, branch references, cycles, reachability).
4. Enforce template allowlist and render with `StrictUndefined`.
5. Build typed compiled model.

## Runtime Flow

1. Create execution record (`running`).
2. Start at `entry_step`.
3. For each `ssh` step:
- execute with per-attempt timeout
- evaluate expectation (`exit_code`, optional stdout/stderr contains)
- retry up to `1 + retries` with `retry_delay`
- branch to `on_success` or `on_failure`
4. Terminal behavior:
- `end` => final status `success`
- `escalate` => final status `escalated`
5. Record execution end status.

## Escalation Flow

When `escalate` is reached:

- build shared `NotificationContext`
- fan out to every configured notifier
- record each notifier outcome
- continue shutdown flow even if one notifier fails

## Dry-Run Flow

Dry-run never executes remote commands.

- records execution with `dry_run=true`
- simulates each `ssh` step once
- records branch preview map (`on_success`, `on_failure`)
- follows `on_success` as default preview path
- ends with final status `dry_run`

## Persistence and Audit

- SQLite tables: executions, step_attempts, notifications
- Structured text log file per execution in audit directory
- Structured JSONL audit stream per execution in audit directory
- Correlation key: `execution_id` across DB and log lines
- `show-run` renders persisted execution summaries from SQLite + audit artifacts
