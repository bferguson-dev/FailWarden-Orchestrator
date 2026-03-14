# Secrets Setup Guide

## Goal

Keep FailWarden secrets out of git while making local and CI setup predictable.

## Recommended Local Layout

- Keep committed defaults in `.env.example`
- Start from `.env.local.example` for a local shell workflow
- Put real values in an ignored file such as `.env.local`
- Load local values into your shell before running `fwo`

Example:

```bash
set -a
source .env.local
set +a
```

Do not commit:

- SSH private keys
- Slack webhook URLs
- SMTP passwords
- real hostnames, IPs, or operator email addresses

## SSH Credentials

Preferred approach:

- Use `--ssh-key ~/.ssh/id_ed25519`
- Protect the key with normal filesystem permissions
- Use an unencrypted automation key dedicated to FailWarden, not your personal key
- Store that key outside the repo and lock down file permissions

Password fallback:

- Store the password in a local environment variable
- Pass the variable name with `--ssh-password-env`

Example:

```bash
export FWO_LINUX_SSH_PASSWORD='local-only-password'
fwo run \
  --runbook runbooks/linux_service_down.yaml \
  --target linux-web-01 \
  --host 10.0.0.10 \
  --user ubuntu \
  --ssh-password-env FWO_LINUX_SSH_PASSWORD
```

## SSH Host Keys

V1 enforces strict host key verification.

Before the first real run, populate `known_hosts` with the target host key:

```bash
ssh-keyscan -H 10.0.0.10 >> ~/.ssh/known_hosts
```

Validate the fingerprint out of band before trusting it.

## Slack Webhook Setup

Required variables:

- `FWO_SLACK_WEBHOOK_URL`
- optional `FWO_SLACK_CHANNEL`

Example:

```bash
export FWO_SLACK_WEBHOOK_URL='https://hooks.slack.com/services/...'
export FWO_SLACK_CHANNEL='#ops-alerts'
```

## SMTP Setup

Common variables:

- `FWO_SMTP_HOST`
- `FWO_SMTP_PORT`
- `FWO_SMTP_USERNAME`
- `FWO_SMTP_PASSWORD`
- `FWO_SMTP_FROM`
- `FWO_SMTP_USE_TLS`

Example:

```bash
export FWO_SMTP_HOST='smtp.example.com'
export FWO_SMTP_PORT='587'
export FWO_SMTP_USERNAME='failwarden'
export FWO_SMTP_PASSWORD='local-only-password'
export FWO_SMTP_FROM='failwarden@example.com'
export FWO_SMTP_USE_TLS='true'
```

## Dry-Run First

Validate local configuration without remote execution:

```bash
fwo run \
  --runbook runbooks/linux_service_down.yaml \
  --target linux-web-01 \
  --host 10.0.0.10 \
  --user ubuntu \
  --ssh-key ~/.ssh/id_ed25519 \
  --dry-run \
  --summary-json .artifacts/linux-service-down-summary.json
```

Inspect the summary:

```bash
fwo show-run --execution-id <execution_id> --json
```

## CI Guidance

- Inject Slack and SMTP secrets through the CI secret store
- Use deploy keys or ephemeral SSH credentials where possible
- Never print secret values in logs
- Run `./check.sh` before opening a PR
