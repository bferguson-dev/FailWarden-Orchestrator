# CHANGELOG

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- Step 1 repository skeleton
- Root documentation placeholders
- `docs/` reference placeholders
- Initial project quality gate script (`check.sh`)
- Step 2 runbook schema contract documentation
- JSON Schema reference for runbook structure
- Validation error code contract
- Valid and invalid sample runbooks for schema testing
- Step 3 runbook compiler with schema, semantic, and template validation
- Typed compiled runbook models for execution-ready representation
- Compile-layer test suite covering major failure modes
- Step 4 SQLite persistence layer for executions, step attempts, and notifications
- SQLite schema version tracking (`schema_version`)
- Persistence test suite for schema creation and record writes
- Step 5 structured audit logging layer with per-execution log files
- Audit log test coverage for required event fields and quoting behavior
- Step 6 SSH executor with normalized execution result contract
- SSH executor test coverage for success, failure, timeout, and host key modes
- Step 7 execution engine for step walking, branching, retries, and terminal states
- Engine test coverage for success path, retry flow, failure escalation path, and audit/persistence writes
- Step 8 escalation fan-out with shared notifier context and outcome capture
- Notifier interface contracts and escalation notification tests
- Step 9 concrete Slack webhook and SMTP email notifier implementations
- Notifier tests for success and failure behaviors
- Step 10 dry-run execution mode with simulated step attempts and branch preview
- Step 11 five shipped runbooks under `runbooks/`
- Step 12 CLI and documentation polish for end-to-end usage
- V1.5 CLI JSON output and improved command help
- V1.5 persisted run summary export and `show-run` command
- V1.5 JSONL audit artifact output per execution
- V1.5 secrets setup guide and updated operator docs
- V1.5 branch-only contribution flow and CI workflow running `./check.sh`
- V1.5 controlled local transport integration coverage for SSH, Slack, and SMTP
- V1.5 release process and `.env.local` example workflow
