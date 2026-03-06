"""SQLite persistence tests for Step 4."""

from __future__ import annotations

import sqlite3

import pytest

from failwarden_orchestrator.persistence import SCHEMA_VERSION, SQLiteAuditStore


def test_initialize_creates_schema_and_version(tmp_path) -> None:
    db_path = tmp_path / "fwo.sqlite3"
    store = SQLiteAuditStore(db_path)

    store.initialize()

    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    assert row is not None
    assert row[0] == SCHEMA_VERSION


def test_record_execution_lifecycle(tmp_path) -> None:
    db_path = tmp_path / "fwo.sqlite3"
    store = SQLiteAuditStore(db_path)
    store.initialize()

    execution_id = "exec-001"
    store.record_execution_start(
        execution_id=execution_id,
        runbook_name="linux_service_down",
        runbook_version="1.0",
        target="linux-web-01",
        dry_run=False,
    )

    execution = store.get_execution(execution_id)
    assert execution is not None
    assert execution.id == execution_id
    assert execution.status == "running"
    assert execution.ended_at is None

    store.record_execution_end(execution_id, final_status="success")
    ended = store.get_execution(execution_id)
    assert ended is not None
    assert ended.status == "success"
    assert ended.ended_at is not None


def test_record_step_attempt_and_notification(tmp_path) -> None:
    db_path = tmp_path / "fwo.sqlite3"
    store = SQLiteAuditStore(db_path)
    store.initialize()

    execution_id = "exec-002"
    store.record_execution_start(
        execution_id=execution_id,
        runbook_name="windows_service_down",
        runbook_version="1.0",
        target="win-app-01",
        dry_run=True,
    )

    store.record_step_attempt(
        attempt_id="attempt-001",
        execution_id=execution_id,
        step_id="check_service",
        step_type="ssh",
        attempt_number=1,
        started_at="2026-03-06T07:00:00+00:00",
        ended_at="2026-03-06T07:00:01+00:00",
        success=True,
        exit_status=0,
        duration_ms=1000,
        branch_taken="on_success",
        command_summary="systemctl is-active nginx",
        error_summary=None,
    )

    attempts = store.list_step_attempts(execution_id)
    assert len(attempts) == 1
    assert attempts[0].step_id == "check_service"
    assert attempts[0].success

    store.record_notification(
        notification_id="notif-001",
        execution_id=execution_id,
        step_id="escalate_ops",
        notifier_type="slack",
        destination="#ops-alerts",
        status="sent",
        error_summary=None,
    )

    notifications = store.list_notifications(execution_id)
    assert len(notifications) == 1
    assert notifications[0].notifier_type == "slack"
    assert notifications[0].status == "sent"


def test_foreign_key_enforced_for_step_attempt(tmp_path) -> None:
    db_path = tmp_path / "fwo.sqlite3"
    store = SQLiteAuditStore(db_path)
    store.initialize()

    with pytest.raises(sqlite3.IntegrityError):
        store.record_step_attempt(
            attempt_id="attempt-bad",
            execution_id="missing-execution",
            step_id="check_service",
            step_type="ssh",
            attempt_number=1,
            started_at="2026-03-06T07:00:00+00:00",
            ended_at="2026-03-06T07:00:01+00:00",
            success=False,
            exit_status=1,
            duration_ms=1000,
            branch_taken="on_failure",
            command_summary="systemctl is-active nginx",
            error_summary="no execution",
        )
