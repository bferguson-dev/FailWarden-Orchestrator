# Runbook Authoring Guide

## References

- Schema contract: `docs/schema.md`
- JSON schema: `docs/schema/runbook-v1.schema.json`
- Validation errors: `docs/validation-errors.md`

## Required Top-Level Fields

- `name`
- `description`
- `vars`
- `entry_step`
- `steps`

## Step Type Rules

- `ssh`: executable step with explicit `on_success` and `on_failure`
- `end`: terminal success step
- `escalate`: terminal handoff step with notifier routing

## Authoring Guidelines

- Use plain language step names.
- Keep commands small and inspectable.
- Keep branching explicit and safe.
- Keep secrets out of YAML.
- Prefer deterministic command checks over broad shell logic.

## Validation Workflow

Compile before running:

```bash
fwo compile --runbook runbooks/linux_service_down.yaml
```

Dry-run before real execution:

```bash
fwo run \
  --runbook runbooks/linux_service_down.yaml \
  --target linux-web-01 \
  --host 10.0.0.10 \
  --user ubuntu \
  --ssh-key ~/.ssh/id_ed25519 \
  --dry-run
```

## Shipped Runbooks

- `runbooks/linux_service_down.yaml`
- `runbooks/windows_service_down.yaml`
- `runbooks/disk_full.yaml`
- `runbooks/ntp_drift.yaml`
- `runbooks/http_endpoint_down.yaml`
