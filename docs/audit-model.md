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
