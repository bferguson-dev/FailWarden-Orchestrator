"""Structured audit logging for runbook executions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class AuditEvent:
    """One structured audit event written to an execution log."""

    timestamp: str
    level: str
    event: str
    execution_id: str
    runbook: str
    target: str
    fields: dict[str, object]


class AuditLogger:
    """Writes human-readable structured log lines per execution."""

    def __init__(self, audit_dir: str | Path) -> None:
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)

    def log_execution_start(
        self,
        execution_id: str,
        runbook: str,
        target: str,
        dry_run: bool,
    ) -> Path:
        """Create or append the execution log with a start event."""
        return self._write_event(
            event="execution_start",
            execution_id=execution_id,
            runbook=runbook,
            target=target,
            fields={
                "dry_run": dry_run,
                "status": "running",
            },
        )

    def log_step_attempt(
        self,
        execution_id: str,
        runbook: str,
        target: str,
        step_id: str,
        step_type: str,
        attempt_number: int,
        result: str,
        branch: str,
        duration_ms: int,
        exit_status: int | None,
        error: str | None,
    ) -> Path:
        """Write one step-attempt outcome event."""
        return self._write_event(
            event="step_attempt",
            execution_id=execution_id,
            runbook=runbook,
            target=target,
            fields={
                "step_id": step_id,
                "step_type": step_type,
                "attempt": attempt_number,
                "result": result,
                "branch": branch,
                "duration_ms": duration_ms,
                "exit_status": exit_status,
                "error": error,
            },
        )

    def log_notification(
        self,
        execution_id: str,
        runbook: str,
        target: str,
        step_id: str,
        notifier: str,
        destination: str,
        result: str,
        error: str | None,
    ) -> Path:
        """Write one notifier delivery outcome event."""
        return self._write_event(
            event="notification",
            execution_id=execution_id,
            runbook=runbook,
            target=target,
            fields={
                "step_id": step_id,
                "notifier": notifier,
                "destination": destination,
                "result": result,
                "error": error,
            },
        )

    def log_escalation(
        self,
        execution_id: str,
        runbook: str,
        target: str,
        step_id: str,
        reason: str,
    ) -> Path:
        """Write an explicit escalation event for operator traceability."""
        return self._write_event(
            event="escalation",
            execution_id=execution_id,
            runbook=runbook,
            target=target,
            fields={
                "step_id": step_id,
                "reason": reason,
            },
        )

    def log_execution_end(
        self,
        execution_id: str,
        runbook: str,
        target: str,
        final_status: str,
    ) -> Path:
        """Write terminal execution status event."""
        return self._write_event(
            event="execution_end",
            execution_id=execution_id,
            runbook=runbook,
            target=target,
            fields={
                "status": final_status,
            },
        )

    def _write_event(
        self,
        event: str,
        execution_id: str,
        runbook: str,
        target: str,
        fields: dict[str, object],
    ) -> Path:
        event_data = AuditEvent(
            timestamp=_utc_now_iso(),
            level="INFO",
            event=event,
            execution_id=execution_id,
            runbook=runbook,
            target=target,
            fields=fields,
        )
        line = self._format_event(event_data)
        log_path = self.audit_dir / f"{execution_id}.log"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{line}\n")
        return log_path

    @staticmethod
    def _format_event(event: AuditEvent) -> str:
        parts = [
            f"ts={_quote(event.timestamp)}",
            f"level={_quote(event.level)}",
            f"event={_quote(event.event)}",
            f"execution_id={_quote(event.execution_id)}",
            f"runbook={_quote(event.runbook)}",
            f"target={_quote(event.target)}",
        ]
        for key, value in event.fields.items():
            parts.append(f"{key}={_quote(value)}")
        return " ".join(parts)


def _quote(value: object) -> str:
    """Return a safe text representation for one log field value."""
    if value is None:
        return "null"
    text = str(value)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    needs_quotes = any(char.isspace() for char in escaped) or "=" in escaped
    if needs_quotes:
        return f'"{escaped}"'
    return escaped


def _utc_now_iso() -> str:
    """Return UTC timestamp in ISO-8601 string format."""
    return datetime.now(tz=UTC).isoformat(timespec="seconds")
