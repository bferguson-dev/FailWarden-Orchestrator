"""Base executor contract and normalized execution result."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class ExecutionResult:
    """Normalized command execution result used by orchestration logic."""

    success: bool
    output: str
    error: str | None
    exit_status: int | None
    duration_ms: int
    metadata: dict[str, object] = field(default_factory=dict)


class BaseExecutor(Protocol):
    """Common interface for all transport executors."""

    def execute(
        self,
        command: str,
        timeout_seconds: int,
    ) -> ExecutionResult:
        """Execute one command and return normalized result."""
        ...
