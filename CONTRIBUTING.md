# CONTRIBUTING

## Branch and Merge Policy

- This repository is maintained by one owner.
- Direct pushes to `main` are allowed only after a clean staged review and a
  passing `./check.sh`.
- Topic branches and pull requests are optional for larger or riskier changes.

Recommended local setup:

```bash
git config core.hooksPath .githooks
```

Default flow:

1. Make changes.
2. Stage intentionally.
3. Run `./check.sh`.
4. Push to `main`.

Optional branch flow:

1. Create a branch.
2. Make changes.
3. Stage intentionally and run `./check.sh`.
4. Push the branch.
5. Open a pull request using `.github/pull_request_template.md`.
6. Merge after CI passes.

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
- Review `git diff --cached` before committing.
- `git diff --cached --check` must pass.
- Pre-commit `gitleaks` must pass.
- If `git-secrets` is installed locally, run `git secrets --scan --cached`
  before commit.

## Required Checks

Before requesting review or pushing to `main`:

```bash
./check.sh
```

`./check.sh` failures are blockers.

The gate expects a commit-ready worktree by default:

- staged changes are reviewed intentionally
- unstaged tracked changes fail the Git hygiene phase
- suspicious staged paths, binaries, large files, and CRLF text are rejected
- Markdown, config syntax, dependency audit, and tests are all part of the
  evidence set

## Security Expectations

- Never commit secrets, keys, or tokens.
- Keep private hostnames, IPs, and personal data out of tracked files.
- Put local sensitive values in ignored `.local.*` files.
- Use the repo-local `.gitleaks.toml` policy for example-only allowlists.
