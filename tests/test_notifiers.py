"""Notifier implementation tests for Step 9."""

from __future__ import annotations

import smtplib
from dataclasses import replace
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from failwarden_orchestrator.notifiers import NotificationContext
from failwarden_orchestrator.notifiers.email import EmailNotifier
from failwarden_orchestrator.notifiers.slack import SlackNotifier


def sample_context() -> NotificationContext:
    """Create a reusable escalation notification context for tests."""
    return NotificationContext(
        execution_id="exec-1000",
        runbook_name="linux_service_down",
        target="linux-web-01",
        step_id="escalate_ops",
        failure_reason="service restart failed",
        notify_title="Escalation: linux_service_down",
        notify_message="Manual intervention required",
        slack_enabled=True,
        email_enabled=True,
        slack_channel="#ops-alerts",
        email_to=["ops@example.local"],
        occurred_at="2026-03-06T00:00:00+00:00",
    )


@patch("failwarden_orchestrator.notifiers.slack.urlopen")
def test_slack_notifier_success(mock_urlopen: MagicMock) -> None:
    response = MagicMock()
    response.status = 200
    mock_urlopen.return_value.__enter__.return_value = response

    notifier = SlackNotifier(
        webhook_url="https://hooks.slack.example/services/T000/B000/XXX",
    )
    result = notifier.send(sample_context())

    assert result.success
    assert result.notifier_type == "slack"
    assert result.destination == "#ops-alerts"


@patch("failwarden_orchestrator.notifiers.slack.urlopen")
def test_slack_notifier_http_error(mock_urlopen: MagicMock) -> None:
    mock_urlopen.side_effect = HTTPError(
        url="https://hooks.slack.example/services/T000/B000/XXX",
        code=500,
        msg="server error",
        hdrs=None,
        fp=None,
    )

    notifier = SlackNotifier(
        webhook_url="https://hooks.slack.example/services/T000/B000/XXX",
    )
    result = notifier.send(sample_context())

    assert not result.success
    assert "HTTP error" in (result.error or "")


@patch("smtplib.SMTP")
def test_email_notifier_success(mock_smtp_cls: MagicMock) -> None:
    smtp_instance = mock_smtp_cls.return_value.__enter__.return_value

    notifier = EmailNotifier(
        smtp_host="smtp.example.local",
        smtp_port=587,
        smtp_username="user",
        smtp_password="test-password",  # noqa: S106
        from_address="failwarden@example.local",
    )
    result = notifier.send(sample_context())

    assert result.success
    smtp_instance.starttls.assert_called_once()
    smtp_instance.login.assert_called_once_with("user", "test-password")
    smtp_instance.send_message.assert_called_once()


@patch("smtplib.SMTP")
def test_email_notifier_smtp_error(mock_smtp_cls: MagicMock) -> None:
    smtp_instance = mock_smtp_cls.return_value.__enter__.return_value
    smtp_instance.send_message.side_effect = smtplib.SMTPException("send failed")

    notifier = EmailNotifier(
        smtp_host="smtp.example.local",
        smtp_port=587,
        smtp_username=None,
        smtp_password=None,
        from_address="failwarden@example.local",
    )
    result = notifier.send(sample_context())

    assert not result.success
    assert "smtp error" in (result.error or "")


def test_email_notifier_requires_recipients() -> None:
    context = replace(sample_context(), email_to=[])
    notifier = EmailNotifier(
        smtp_host="smtp.example.local",
        smtp_port=587,
        smtp_username=None,
        smtp_password=None,
        from_address="failwarden@example.local",
    )

    result = notifier.send(context)
    assert not result.success
    assert "not configured" in (result.error or "")
