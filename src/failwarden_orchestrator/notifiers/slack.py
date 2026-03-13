"""Slack webhook notifier implementation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from failwarden_orchestrator.notifiers.base import (
    NotificationContext,
    NotificationSendResult,
)


@dataclass(frozen=True)
class SlackNotifier:
    """Send escalation notifications to Slack incoming webhooks."""

    webhook_url: str
    default_channel: str | None = None
    timeout_seconds: int = 10

    notifier_type: str = "slack"

    def send(self, context: NotificationContext) -> NotificationSendResult:
        """Send one Slack message and return normalized outcome."""
        if not context.slack_enabled:
            return NotificationSendResult(
                notifier_type=self.notifier_type,
                destination=context.slack_channel or self.default_channel or "disabled",
                success=False,
                error="slack notifications are disabled for this escalation",
            )

        channel = context.slack_channel or self.default_channel
        destination = channel or "default"
        parsed = urlparse(self.webhook_url)
        if not self._is_supported_webhook_url(parsed.scheme, parsed.hostname):
            return NotificationSendResult(
                notifier_type=self.notifier_type,
                destination=destination,
                success=False,
                error="webhook_url must use https unless targeting localhost",
            )

        payload = {
            "text": self._build_text(context),
        }
        if channel:
            payload["channel"] = channel

        data = json.dumps(payload).encode("utf-8")
        request = Request(  # noqa: S310
            url=self.webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310  # nosec B310
                status = getattr(response, "status", 200)
            if 200 <= int(status) < 300:
                return NotificationSendResult(
                    notifier_type=self.notifier_type,
                    destination=destination,
                    success=True,
                    error=None,
                )
            return NotificationSendResult(
                notifier_type=self.notifier_type,
                destination=destination,
                success=False,
                error=f"unexpected HTTP status: {status}",
            )
        except HTTPError as exc:
            return NotificationSendResult(
                notifier_type=self.notifier_type,
                destination=destination,
                success=False,
                error=f"HTTP error: {exc.code}",
            )
        except URLError as exc:
            return NotificationSendResult(
                notifier_type=self.notifier_type,
                destination=destination,
                success=False,
                error=f"network error: {exc.reason}",
            )

    @staticmethod
    def _build_text(context: NotificationContext) -> str:
        """Build concise incident-style Slack text."""
        title = context.notify_title or "FailWarden escalation"
        message = context.notify_message or "Automation requires human attention"
        return (
            f"{title}\n"
            f"runbook={context.runbook_name} target={context.target} "
            f"execution_id={context.execution_id} step={context.step_id}\n"
            f"reason={context.failure_reason}\n"
            f"message={message}"
        )

    @staticmethod
    def _is_supported_webhook_url(scheme: str, hostname: str | None) -> bool:
        """Allow HTTPS everywhere and HTTP only for explicit local testing."""
        if scheme == "https":
            return True
        return scheme == "http" and hostname in {"127.0.0.1", "localhost", "::1"}
