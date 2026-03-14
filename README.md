# FailWarden Orchestrator

FailWarden Orchestrator is a constrained, auditable YAML runbook executor for
infrastructure remediation over SSH.

## What This Solves

Ops teams often have documented runbooks, but incident response is still manual,
inconsistent, and hard to audit. This project turns runbook intent into
validated, executable, and traceable automation.

## V1 Scope

Included in V1:

- YAML runbook model with compile-time validation
- Jinja2 variable rendering with strict undefined behavior
- SSH executor for Linux and Windows (PowerShell over SSH)
- Linked-step orchestration with retries, timeout, and branching
- Escalation flow with shared notifier context
- Slack webhook and SMTP email notifiers
- SQLite execution + step + notifier history
- Structured per-execution audit logs
- Dry-run mode with simulated branch preview
- Five shipped runbooks

Explicitly out of scope for V1:

- Additional transports (WinRM, PSRP, HTTP, Ansible)
- Dashboard and metrics stack
- CMDB, approvals, RBAC, multi-tenancy, Vault

## Current Status

- V1 is implemented
- V1.5 is implemented
- Current tagged release: `v0.2.0`
- Default workflow: run `./check.sh`, then push directly to `main`
- Optional workflow: use a branch and PR when you want an isolated reviewable change set

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e '.[dev]'
./check.sh
```

Local env workflow:

```bash
cp .env.local.example .env.local
set -a
source .env.local
set +a
```

Compile a runbook:

```bash
fwo compile --runbook runbooks/linux_service_down.yaml
```

Compile as JSON:

```bash
fwo compile --runbook runbooks/linux_service_down.yaml --json
```

Dry-run preview (no remote execution):

```bash
fwo run \
  --runbook runbooks/linux_service_down.yaml \
  --target linux-web-01 \
  --host 10.0.0.10 \
  --user ubuntu \
  --ssh-key ~/.ssh/failwarden_ed25519 \
  --dry-run
```

Dry-run preview with persisted JSON summary:

```bash
fwo run \
  --runbook runbooks/linux_service_down.yaml \
  --target linux-web-01 \
  --host 10.0.0.10 \
  --user ubuntu \
  --ssh-key ~/.ssh/failwarden_ed25519 \
  --dry-run \
  --summary-json .artifacts/linux-service-down-summary.json
```

Real run:

```bash
fwo run \
  --runbook runbooks/linux_service_down.yaml \
  --target linux-web-01 \
  --host 10.0.0.10 \
  --user ubuntu \
  --ssh-key ~/.ssh/failwarden_ed25519
```

Show a stored execution summary:

```bash
fwo show-run --execution-id <execution_id> --json
```

Optional notifier env vars:

- `FWO_SLACK_WEBHOOK_URL`
- `FWO_SLACK_CHANNEL`
- `FWO_SMTP_HOST`
- `FWO_SMTP_PORT`
- `FWO_SMTP_USERNAME`
- `FWO_SMTP_PASSWORD`
- `FWO_SMTP_FROM`
- `FWO_SMTP_USE_TLS`

Secrets and host-key setup guidance lives in `docs/secrets-setup.md`.
Release/versioning guidance lives in `RELEASE.md`.

## Shipped Runbooks

- `runbooks/linux_service_down.yaml`
- `runbooks/windows_service_down.yaml`
- `runbooks/disk_full.yaml`
- `runbooks/ntp_drift.yaml`
- `runbooks/http_endpoint_down.yaml`

## Repository Layout

- `src/`: package implementation
- `tests/`: unit and integration-style unit tests
- `runbooks/`: shipped runbooks + schema examples
- `docs/`: architecture and design references

## Quality Gates

- `./check.sh` runs format, lint, secret scan, security scan, dependency audit,
  and tests.
- GitHub Actions runs the same `./check.sh` gate in CI.
- `gitleaks` pre-commit hook blocks secret commits.
