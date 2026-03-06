#!/usr/bin/env bash
set -euo pipefail

# FailWarden Orchestrator quality gate script.
#
# Goals:
# - Keep checks easy to read for infrastructure engineers.
# - Run the same baseline checks in every reviewable phase.
# - Fail fast on formatting, lint, security, or test issues.

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"
RUFF_AUTO_FIX="${RUFF_AUTO_FIX:-1}"
PIP_AUDIT_FAIL_ON_VULNS="${PIP_AUDIT_FAIL_ON_VULNS:-1}"

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: $PYTHON_BIN was not found."
  exit 2
fi

if [[ ! -d "$VENV_DIR" ]]; then
  echo "[setup] Creating virtual environment at $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "[setup] Installing or upgrading project tooling"
python -m pip install -U pip >/dev/null
python -m pip install -e '.[dev]' >/dev/null

echo "[format] ruff format"
ruff format .

if [[ "$RUFF_AUTO_FIX" == "1" ]]; then
  echo "[lint] ruff check with auto-fix"
  ruff check . --fix || true
fi

echo "[lint] ruff check enforce"
ruff check .

echo "[secrets] gitleaks detect"
gitleaks detect --source . --no-banner --redact

echo "[security] bandit"
# Security scan focuses on runtime code. Test assertions are expected.
bandit -r src

echo "[deps] pip-audit"
set +e
pip-audit
AUDIT_RC=$?
set -e
if [[ "$PIP_AUDIT_FAIL_ON_VULNS" == "1" && "$AUDIT_RC" != "0" ]]; then
  echo "FAIL: pip-audit found vulnerabilities."
  exit 11
fi

echo "[tests] pytest"
pytest

echo "OK: all checks passed"
