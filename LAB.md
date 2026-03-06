# LAB

## Purpose

This lab guide defines a minimal environment to validate the five shipped
runbooks safely.

## Topology

- Dev host: Ubuntu (WSL2 acceptable)
- Linux target host over SSH
- Windows target host with OpenSSH enabled and PowerShell available

## Prerequisites

- Python 3.11+
- SSH key access to test hosts
- Optional notifier endpoints:
- Slack incoming webhook
- SMTP server credentials

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e '.[dev]'
```

## Environment Variables

Copy `.env.example` values into local environment or shell profile.

Common values:

- `FWO_DB_PATH=.data/fwo.sqlite3`
- `FWO_AUDIT_DIR=.audit`
- notifier env vars as needed

## Incident Simulation Suggestions

- `linux_service_down`: stop target service with `systemctl stop <service>`
- `windows_service_down`: stop Windows service in PowerShell
- `disk_full`: fill disk with test artifacts, then run cleanup path
- `ntp_drift`: stop timesync service temporarily
- `http_endpoint_down`: stop web service or block local endpoint

## Example Dry-Run Validation

```bash
fwo run \
  --runbook runbooks/linux_service_down.yaml \
  --target linux-web-01 \
  --host 10.0.0.10 \
  --user ubuntu \
  --ssh-key ~/.ssh/id_ed25519 \
  --dry-run
```

## Example Real Validation

```bash
fwo run \
  --runbook runbooks/http_endpoint_down.yaml \
  --target linux-web-01 \
  --host 10.0.0.10 \
  --user ubuntu \
  --ssh-key ~/.ssh/id_ed25519
```

## Reset Notes

- Restart affected services after tests
- Clear temporary disk filler files
- Reset database and audit artifacts if needed:

```bash
rm -rf .data .audit
```
