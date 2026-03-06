# Audit Model (V1 Draft With Step 4 Storage)

Step 4 introduces SQLite persistence for execution and step history.

## SQLite Tables

### `schema_version`

- `version` (integer, single-row)

### `executions`

- `id` (text, primary key)
- `runbook_name` (text, required)
- `runbook_version` (text, nullable)
- `target` (text, required)
- `status` (text, required)
- `dry_run` (integer bool, required)
- `started_at` (text ISO timestamp, required)
- `ended_at` (text ISO timestamp, nullable)

### `step_attempts`

- `id` (text, primary key)
- `execution_id` (text, FK `executions.id`)
- `step_id` (text, required)
- `step_type` (text, required)
- `attempt_number` (integer, required)
- `started_at` (text ISO timestamp, required)
- `ended_at` (text ISO timestamp, required)
- `success` (integer bool, required)
- `exit_status` (integer, nullable)
- `duration_ms` (integer, required)
- `branch_taken` (text, required)
- `command_summary` (text, required)
- `error_summary` (text, nullable)

### `notifications`

- `id` (text, primary key)
- `execution_id` (text, FK `executions.id`)
- `step_id` (text, nullable)
- `notifier_type` (text, required)
- `destination` (text, required)
- `status` (text, required)
- `error_summary` (text, nullable)
- `sent_at` (text ISO timestamp, required)

## Notes

- Foreign keys are enabled on each DB connection.
- Step 4 stores records only. Query/report surfaces will be extended later.

## Structured Audit Log Files (Step 5)

Step 5 adds per-execution structured text logs.

- Log directory: configured by runtime (default planned: `.audit/`)
- Log file name: `<execution_id>.log`
- One event per line
- Append-only per execution run

### Event Fields

Every line includes:

- `ts`
- `level`
- `event`
- `execution_id`
- `runbook`
- `target`

Event-specific fields include:

- step fields: `step_id`, `step_type`, `attempt`, `result`, `branch`, `duration_ms`
- escalation fields: `reason`
- notifier fields: `notifier`, `destination`, `result`, `error`
- terminal execution field: `status`
