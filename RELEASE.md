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
3. Update README or operator docs if behavior, validation, or workflow changed.
4. Stage intentionally and review `git diff --cached`.
5. Run `./check.sh`.
6. Push the branch and open a pull request, or push directly to `main` only if
   the change is intentionally using the solo-maintainer fast path.
7. Tag the release commit with `vX.Y.Z`.

Example:

```bash
git tag v0.2.0
git push origin v0.2.0
```

## Packaging Notes

- Install locally with `python -m pip install -e '.[dev]'`
- CLI entrypoint remains `fwo`
- Use `fwo --version` to confirm the installed package version
- Release readiness still excludes live production validation unless explicitly
  documented otherwise
