"""Execution-ready runbook models produced by the compiler."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

StepType = Literal["ssh", "escalate", "end"]


@dataclass(frozen=True)
class StepBase:
    """Common step fields shared by all step types."""

    id: str
    type: StepType
    name: str


@dataclass(frozen=True)
class SSHExpect:
    """Expected output contract for an SSH step."""

    exit_code: int
    stdout_contains: str | None = None
    stderr_contains: str | None = None


@dataclass(frozen=True)
class SSHStep(StepBase):
    """SSH execution step with explicit branch behavior."""

    command: str
    expect: SSHExpect
    timeout: int
    retries: int
    retry_delay: int
    on_success: str
    on_failure: str


@dataclass(frozen=True)
class EscalateNotify:
    """Notifier routing and text for escalation."""

    slack_enabled: bool
    email_enabled: bool
    slack_channel: str | None = None
    email_to: list[str] | None = None
    title: str | None = None
    message: str | None = None


@dataclass(frozen=True)
class EscalateStep(StepBase):
    """Terminal escalation step that notifies humans."""

    notify: EscalateNotify


@dataclass(frozen=True)
class EndStep(StepBase):
    """Terminal success step with optional human-readable summary."""

    summary: str | None = None


CompiledStep = SSHStep | EscalateStep | EndStep


@dataclass(frozen=True)
class CompiledRunbook:
    """Fully validated, compile-time rendered runbook model."""

    name: str
    description: str
    version: str | None
    vars: dict[str, object]
    entry_step: str
    steps_in_order: list[CompiledStep]
    steps_by_id: dict[str, CompiledStep]
