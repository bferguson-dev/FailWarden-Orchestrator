# GitHub Hardening Checklist

Apply these repository settings in GitHub:

## 1) Branch protection for `main`

- Require a pull request before merging
- Require approvals (at least 1)
- Require status checks to pass before merging
- Require signed commits
- Include administrators in protections
- Restrict force pushes
- Restrict deletions

## 2) Security features

- Enable Secret Scanning
- Enable Push Protection for secrets
- Enable Dependabot alerts
- Enable Dependabot security updates

## 3) Optional but recommended

- Enable auto-delete for merged branches
- Enable vulnerability alerts at org and repo level
