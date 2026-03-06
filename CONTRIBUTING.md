# CONTRIBUTING

## Branch and Merge Policy

- Do not commit directly to `main` after the bootstrap phase.
- Open a pull request for all changes.
- Require at least one review before merge.

## Commit Policy

Use Conventional Commits:

- `feat: ...`
- `fix: ...`
- `docs: ...`
- `refactor: ...`
- `test: ...`
- `chore: ...`

Rules:

- Keep subject concise and specific.
- Commits must be signed.
- Pre-commit `gitleaks` must pass.

## Required Checks

Before requesting review:

```bash
./check.sh
```

`./check.sh` failures are blockers.

## Security Expectations

- Never commit secrets, keys, or tokens.
- Keep private hostnames, IPs, and personal data out of tracked files.
- Put local sensitive values in ignored `.local.*` files.
