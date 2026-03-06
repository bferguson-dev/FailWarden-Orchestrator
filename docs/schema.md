# Runbook Schema (V1 Contract)

This document defines the V1 runbook shape and validation contract.

## Goals

- Keep runbooks readable by operators.
- Keep execution decisions explicit in YAML.
- Fail early with human-readable validation errors.

## File Format

- Encoding: UTF-8
- Format: YAML (`.yml` or `.yaml`)
- Root type: mapping/object

## Top-Level Fields

Required fields:

- `name` (string)
- `description` (string)
- `vars` (mapping)
- `entry_step` (string)
- `steps` (list of step objects)

Optional fields:

- `version` (string)

## Step Types (V1)

Supported values for `type`:

- `ssh`
- `escalate`
- `end`

No other step types are valid in V1.

## SSH Step Shape

Required fields:

- `id` (string, unique across runbook)
- `type` (must be `ssh`)
- `name` (string)
- `command` (string, template-capable)
- `expect` (object)
- `timeout` (integer, seconds, min 1, max 3600)
- `retries` (integer, min 0, max 10)
- `retry_delay` (integer, seconds, min 0, max 3600)
- `on_success` (string, step id)
- `on_failure` (string, step id)

`expect` fields (V1):

- `exit_code` (integer)
- `stdout_contains` (optional string)
- `stderr_contains` (optional string)

## Escalate Step Shape

Required fields:

- `id` (string, unique)
- `type` (must be `escalate`)
- `name` (string)
- `notify` (object)

Required `notify` fields:

- `slack_enabled` (boolean)
- `email_enabled` (boolean)

Optional `notify` fields:

- `slack_channel` (string)
- `email_to` (list of strings)
- `title` (string, template-capable)
- `message` (string, template-capable)

Escalate steps are terminal in V1 and must not define `on_success` or
`on_failure`.

## End Step Shape

Required fields:

- `id` (string, unique)
- `type` (must be `end`)
- `name` (string)

Optional fields:

- `summary` (string, template-capable)

End steps are terminal in V1 and must not define `on_success`, `on_failure`,
or `notify`.

## Template Rendering Rules

Jinja rendering uses `StrictUndefined`.

Template-capable fields (allowlist):

- top-level `vars` values
- `steps[].command`
- `steps[].notify.title`
- `steps[].notify.message`
- `steps[].summary`

Template-disabled fields:

- step ids and types
- branch targets (`on_success`, `on_failure`)
- retry/timeout numbers

## Compile-Time Validation Rules

The compiler must fail before execution when any rule is violated.

Structural checks:

- Required top-level fields must exist.
- `steps` must be non-empty.
- Step IDs must be unique.
- `entry_step` must match an existing step ID.
- Step `type` must be one of supported V1 values.

Graph checks:

- Every branch target must exist.
- No unreachable steps are allowed.
- Cycles are rejected in V1.

Step policy checks:

- `ssh` steps must include both `on_success` and `on_failure`.
- `escalate` steps must include `notify` routing and no branch fields.
- `end` steps must not include branch or notifier fields.
- Timeout/retry values must be in allowed ranges.

Template checks:

- Missing template variables are compile errors.
- Invalid template syntax is a compile error.

## Example Files

See runbook examples in:

- `runbooks/` (shipped runbooks)
- `runbooks/examples/valid/`
- `runbooks/examples/invalid/`

## Reference Schema

A JSON Schema reference for structural checks is in:

- `docs/schema/runbook-v1.schema.json`

Note: graph-level checks (cycles, unreachable steps, branch existence) require
semantic validation beyond JSON Schema.
