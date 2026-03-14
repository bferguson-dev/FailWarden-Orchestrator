# CONTRIBUTING

## Branch and Merge Policy

- This repository is maintained by one owner.
- Direct pushes to `main` are allowed after running `./check.sh`.
- Topic branches and pull requests are optional for larger or riskier changes.

Recommended local setup:

```bash
git config core.hooksPath .githooks
```

Default flow:

1. Make changes.
2. Run `./check.sh`.
3. Push to `main`.

Optional branch flow:

1. Create a branch.
2. Make changes and run `./check.sh`.
3. Push the branch.
4. Open a pull request using `.github/pull_request_template.md`.
5. Merge after CI passes.

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
