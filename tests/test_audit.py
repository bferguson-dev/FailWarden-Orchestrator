"""Structured audit logging tests for Step 5."""

from __future__ import annotations

import json
from pathlib import Path

from failwarden_orchestrator.audit import AuditLogger


def read_lines(path: Path) -> list[str]:
    """Return all non-empty log lines from a file."""
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_audit_logger_writes_per_execution_file(tmp_path) -> None:
    logger = AuditLogger(tmp_path / "audit")

    path = logger.log_execution_start(
        execution_id="exec-100",
        runbook="linux_service_down",
        target="linux-web-01",
        dry_run=True,
    )

    assert path.exists()
    assert path.name == "exec-100.log"
    assert (tmp_path / "audit" / "exec-100.jsonl").exists()


def test_audit_logger_records_required_fields(tmp_path) -> None:
    logger = AuditLogger(tmp_path / "audit")

    path = logger.log_execution_start(
        execution_id="exec-200",
        runbook="windows_service_down",
        target="win-app-01",
        dry_run=False,
    )
    logger.log_step_attempt(
        execution_id="exec-200",
        runbook="windows_service_down",
        target="win-app-01",
        step_id="check_service",
        step_type="ssh",
        attempt_number=1,
        result="success",
        branch="on_success",
        duration_ms=1200,
        exit_status=0,
        error=None,
    )
    logger.log_notification(
        execution_id="exec-200",
        runbook="windows_service_down",
        target="win-app-01",
        step_id="escalate_ops",
        notifier="slack",
        destination="#ops-alerts",
        result="sent",
        error=None,
    )
    logger.log_escalation(
        execution_id="exec-200",
        runbook="windows_service_down",
        target="win-app-01",
        step_id="escalate_ops",
        reason="service restart failed",
    )
    logger.log_execution_end(
        execution_id="exec-200",
        runbook="windows_service_down",
        target="win-app-01",
        final_status="escalated",
    )

    lines = read_lines(path)
    assert len(lines) == 5

    # Start line carries core identifiers and dry-run state.
    assert "event=execution_start" in lines[0]
    assert "execution_id=exec-200" in lines[0]
    assert "runbook=windows_service_down" in lines[0]
    assert "target=win-app-01" in lines[0]
    assert "dry_run=False" in lines[0]

    # Step attempt line includes step, attempt, result, and branch details.
    assert "event=step_attempt" in lines[1]
    assert "step_id=check_service" in lines[1]
    assert "attempt=1" in lines[1]
    assert "result=success" in lines[1]
    assert "branch=on_success" in lines[1]

    # Notification and escalation lines include escalation context.
    assert "event=notification" in lines[2]
    assert "notifier=slack" in lines[2]
    assert "destination=#ops-alerts" in lines[2]

    assert "event=escalation" in lines[3]
    assert "step_id=escalate_ops" in lines[3]
    assert 'reason="service restart failed"' in lines[3]

    # Final line captures terminal status.
    assert "event=execution_end" in lines[4]
    assert "status=escalated" in lines[4]


def test_audit_logger_quotes_fields_with_spaces(tmp_path) -> None:
    logger = AuditLogger(tmp_path / "audit")
    path = logger.log_notification(
        execution_id="exec-300",
        runbook="disk_full",
        target="linux-db-01",
        step_id="escalate_ops",
        notifier="email",
        destination="on-call@example.local",
        result="failed",
        error="smtp timeout while connecting",
    )

    line = read_lines(path)[0]
    assert 'error="smtp timeout while connecting"' in line


def test_audit_logger_quotes_core_fields_with_spaces(tmp_path) -> None:
    logger = AuditLogger(tmp_path / "audit")
    path = logger.log_execution_start(
        execution_id="exec 400",
        runbook="disk full",
        target="linux db 01",
        dry_run=False,
    )

    line = read_lines(path)[0]
    assert 'execution_id="exec 400"' in line
    assert 'runbook="disk full"' in line
    assert 'target="linux db 01"' in line


def test_audit_logger_writes_jsonl_events(tmp_path) -> None:
    logger = AuditLogger(tmp_path / "audit")
    logger.log_execution_start(
        execution_id="exec-500",
        runbook="linux_service_down",
        target="linux-web-01",
        dry_run=False,
    )

    jsonl_path = tmp_path / "audit" / "exec-500.jsonl"
    payload = json.loads(jsonl_path.read_text(encoding="utf-8").splitlines()[0])
    assert payload["event"] == "execution_start"
    assert payload["execution_id"] == "exec-500"
    assert payload["fields"]["status"] == "running"
