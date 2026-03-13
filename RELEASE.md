# Release Process

## Versioning

FailWarden Orchestrator uses simple semantic versioning:

- `MAJOR`: incompatible contract or workflow changes
- `MINOR`: backward-compatible features and operator-facing improvements
- `PATCH`: backward-compatible fixes only

Current planned line:

- `0.2.x` for V1.5 improvements on top of the existing V1 runtime

## Release Checklist

1. Update `pyproject.toml` version.
2. Update `CHANGELOG.md`.
3. Run `./check.sh`.
4. Push the branch and open a pull request.
5. Merge only after CI is green.
6. Tag the merge commit with `vX.Y.Z`.

Example:

```bash
git tag v0.2.0
git push origin v0.2.0
```

## Packaging Notes

- Install locally with `python -m pip install -e '.[dev]'`
- CLI entrypoint remains `fwo`
- Use `fwo --version` to confirm the installed package version
