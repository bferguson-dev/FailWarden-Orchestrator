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
