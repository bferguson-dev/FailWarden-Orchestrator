"""SMTP email notifier implementation."""

from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from failwarden_orchestrator.notifiers.base import (
    NotificationContext,
    NotificationSendResult,
)


@dataclass(frozen=True)
class EmailNotifier:
    """Send escalation notifications through SMTP."""

    smtp_host: str
    smtp_port: int
    smtp_username: str | None
    smtp_password: str | None
    from_address: str
    use_tls: bool = True
    timeout_seconds: int = 10

    notifier_type: str = "email"

    def send(self, context: NotificationContext) -> NotificationSendResult:
        """Send one email and return normalized outcome."""
        recipients = context.email_to
        if not context.email_enabled:
            return NotificationSendResult(
                notifier_type=self.notifier_type,
                destination=",".join(recipients) if recipients else "disabled",
                success=False,
                error="email notifications are disabled for this escalation",
            )
        if not recipients:
            return NotificationSendResult(
                notifier_type=self.notifier_type,
                destination="none",
                success=False,
                error="email recipients are not configured",
            )

        message = self._build_message(context, recipients)

        try:
            with smtplib.SMTP(
                host=self.smtp_host,
                port=self.smtp_port,
                timeout=self.timeout_seconds,
            ) as smtp:
                if self.use_tls:
                    smtp.starttls()
                if self.smtp_username and self.smtp_password:
                    smtp.login(self.smtp_username, self.smtp_password)
                smtp.send_message(message)
            return NotificationSendResult(
                notifier_type=self.notifier_type,
                destination=",".join(recipients),
                success=True,
                error=None,
            )
        except smtplib.SMTPException as exc:
            return NotificationSendResult(
                notifier_type=self.notifier_type,
                destination=",".join(recipients),
                success=False,
                error=f"smtp error: {exc}",
            )
        except OSError as exc:
            return NotificationSendResult(
                notifier_type=self.notifier_type,
                destination=",".join(recipients),
                success=False,
                error=f"network error: {exc}",
            )

    def _build_message(
        self,
        context: NotificationContext,
        recipients: list[str],
    ) -> EmailMessage:
        """Create a plain operational email from escalation context."""
        subject = context.notify_title or "FailWarden escalation"
        body_message = context.notify_message or "Automation requires human attention"
        body = (
            f"Runbook: {context.runbook_name}\n"
            f"Target: {context.target}\n"
            f"Execution ID: {context.execution_id}\n"
            f"Step: {context.step_id}\n"
            f"Occurred At: {context.occurred_at}\n"
            f"Failure Reason: {context.failure_reason}\n\n"
            f"Details: {body_message}\n"
        )

        message = EmailMessage()
        message["From"] = self.from_address
        message["To"] = ", ".join(recipients)
        message["Subject"] = subject
        message.set_content(body)
        return message
