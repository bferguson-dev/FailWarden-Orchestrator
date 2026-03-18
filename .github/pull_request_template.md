## Summary

Describe what changed and why.

## Scope Check

- [ ] Change is in V1 scope or explicitly documented in `ROADMAP.md`
- [ ] No hidden feature creep

## Validation

- [ ] Ran `./check.sh` locally
- [ ] Added or updated tests for behavior changes
- [ ] Updated docs affected by this change
- [ ] Listed what was not verified or intentionally left out of scope

## Security and Data Hygiene

- [ ] No secrets, personal data, or private infrastructure details committed
- [ ] `gitleaks` pre-commit hook passed
- [ ] Reviewed `git diff --cached`
- [ ] Sensitive local files remain in ignored `.local.*` files

## Review Notes

Include key tradeoffs, risks, rollback or compatibility concerns, and
follow-ups.
