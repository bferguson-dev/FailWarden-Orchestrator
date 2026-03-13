# CONTRIBUTING

## Branch and Merge Policy

- Do not push directly to `main`.
- Create a topic branch for every change.
- Open a pull request for all changes.
- Require at least one review before merge.

Recommended local setup:

```bash
git config core.hooksPath .githooks
git checkout -b <topic-branch>
```

Expected flow:

1. Create a branch.
2. Make changes and run `./check.sh`.
3. Push the branch.
4. Open a pull request using `.github/pull_request_template.md`.
5. Merge only after review and passing checks.

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
