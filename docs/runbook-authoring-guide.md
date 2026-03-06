# Runbook Authoring Guide (Draft)

This guide captures V1 authoring rules for readable and safe runbooks.

## Use These References First

- Schema contract: `docs/schema.md`
- JSON Schema: `docs/schema/runbook-v1.schema.json`
- Error contract: `docs/validation-errors.md`
- Examples: `runbooks/examples/valid/` and `runbooks/examples/invalid/`

## V1 Authoring Basics

- Keep step names operational and plain language.
- Use explicit branch targets in every `ssh` step.
- Keep commands short and inspectable.
- Keep secrets out of YAML. Use runtime values from env or injected vars.
- Prefer predictable commands over clever shell expressions.
