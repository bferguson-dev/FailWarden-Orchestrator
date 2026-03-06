# Execution Model (Draft)

## Current Scope

Step 3 introduces compile-time behavior only. Runtime execution behavior is
still pending later phases.

## Compile-Time Flow (Implemented)

1. Load YAML runbook file.
2. Validate structure against JSON Schema.
3. Run semantic checks:
- unique step IDs
- valid `entry_step`
- branch targets exist
- no cycles
- no unreachable steps
4. Enforce template allowlist.
5. Render allowed templates using Jinja2 `StrictUndefined`.
6. Build typed in-memory runbook model.

## Runtime Flow (Not Yet Implemented)

Step walking, retries, timeout enforcement, and branch execution will be added
in later phases.

## Persistence Status (Step 4)

SQLite storage is now available for:

- execution start/end rows
- step-attempt rows
- notifier outcome rows

## Audit Status (Step 5)

Structured text audit logging is now available with one log file per execution.

## Executor Status (Step 6)

SSH executor implementation is now available with normalized command result
objects (`success`, `output`, `error`, `exit_status`, `duration_ms`,
`metadata`).

## Engine Status (Step 7)

Execution engine is now implemented for:

- step walking from `entry_step`
- expectation checks against command results
- per-step retries with retry delay
- branch selection (`on_success`, `on_failure`)
- terminal handling for `end` and `escalate`

Current limits:

- dry-run mode is deferred to Step 10

## Escalation Status (Step 8)

Escalation fan-out is now implemented:

- builds a shared notification context object
- attempts every configured notifier
- records notifier outcomes in SQLite and audit logs
- does not crash execution if one notifier fails

Current limits:

- concrete Slack and email notifier implementations are deferred to Step 9
