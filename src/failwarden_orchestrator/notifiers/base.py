"""Notifier contracts and shared escalation context model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True)
class NotificationContext:
    """Shared escalation context sent to all notifier implementations."""

    execution_id: str
    runbook_name: str
    target: str
    step_id: str
    failure_reason: str
    notify_title: str | None
    notify_message: str | None
    slack_enabled: bool
    email_enabled: bool
    slack_channel: str | None
    email_to: list[str]
    occurred_at: str


@dataclass(frozen=True)
class NotificationSendResult:
    """Normalized result from one notifier send attempt."""

    notifier_type: str
    destination: str
    success: bool
    error: str | None


class BaseNotifier(Protocol):
    """Interface contract for notifier implementations."""

    notifier_type: str

    def send(self, context: NotificationContext) -> NotificationSendResult:
        """Send one notification and return normalized outcome."""
        ...


def utc_now_iso() -> str:
    """Return UTC timestamp in ISO-8601 format for notification context."""
    return datetime.now(tz=UTC).isoformat(timespec="seconds")
