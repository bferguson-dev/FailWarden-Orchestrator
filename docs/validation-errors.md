# Validation Error Contract (V1)

This file defines how schema and compile-time validation errors should be
reported to operators.

## Error Message Format

Use this format:

`<ERROR_CODE>: <short summary> (path=<yaml_path>, value=<value>)`

Example:

`RBK101: Missing required field 'entry_step' (path=$, value=null)`

## Error Codes

- `RBK1xx` structural/schema errors
- `RBK2xx` graph integrity errors
- `RBK3xx` step policy errors
- `RBK4xx` template/rendering errors

## Required Error Cases

Structural:

- `RBK101` missing top-level required field
- `RBK102` unsupported top-level field
- `RBK103` `steps` is empty
- `RBK104` duplicate step ID
- `RBK105` unsupported step type

Graph:

- `RBK201` `entry_step` not found
- `RBK202` branch target not found
- `RBK203` unreachable step
- `RBK204` cycle detected

Step policy:

- `RBK301` `ssh` missing `on_success` or `on_failure`
- `RBK302` `escalate` includes forbidden branch field
- `RBK307` `end` includes forbidden branch or notifier field
- `RBK303` timeout out of range
- `RBK304` retries out of range
- `RBK305` retry_delay out of range
- `RBK306` `escalate.notify` missing required routing fields

Template:

- `RBK401` undefined template variable
- `RBK402` invalid template syntax
- `RBK403` template used in non-templated field

## Multi-Error Behavior

- Show all validation errors in one pass when possible.
- Preserve file order for stable output.
- Exit non-zero if any error exists.
