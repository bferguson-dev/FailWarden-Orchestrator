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
