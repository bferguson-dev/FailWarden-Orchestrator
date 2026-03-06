"""Validation primitives for readable compiler errors."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationIssue:
    """One compile/validation issue with a stable code and YAML path."""

    code: str
    message: str
    path: str
    value: str

    def format_human(self) -> str:
        """Return the standard operator-facing error format."""
        return f"{self.code}: {self.message} (path={self.path}, value={self.value})"


class RunbookValidationError(Exception):
    """Raised when one or more validation issues are detected."""

    def __init__(self, issues: list[ValidationIssue]) -> None:
        self.issues = issues
        message = "\n".join(issue.format_human() for issue in issues)
        super().__init__(message)
