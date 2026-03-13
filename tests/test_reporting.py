"""Run summary reporting tests."""

from __future__ import annotations

import json

from failwarden_orchestrator.audit import AuditLogger
from failwarden_orchestrator.persistence import SQLiteAuditStore
from failwarden_orchestrator.reporting import build_run_summary, write_run_summary_json


def test_build_run_summary_includes_artifact_paths(tmp_path) -> None:
    db_path = tmp_path / "fwo.sqlite3"
    audit_dir = tmp_path / "audit"
    store = SQLiteAuditStore(db_path)
    store.initialize()

    store.record_execution_start(
        execution_id="exec-1000",
        runbook_name="linux_service_down",
        runbook_version="1.0",
        target="linux-web-01",
        dry_run=False,
    )
    store.record_step_attempt(
        attempt_id="attempt-1000",
        execution_id="exec-1000",
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
    store.record_execution_end("exec-1000", final_status="success")

    logger = AuditLogger(audit_dir)
    logger.log_execution_start(
        execution_id="exec-1000",
        runbook="linux_service_down",
        target="linux-web-01",
        dry_run=False,
    )

    summary = build_run_summary(store, "exec-1000", audit_dir=audit_dir).to_dict()

    assert summary["execution"]["id"] == "exec-1000"
    assert summary["stats"]["step_attempt_count"] == 1
    assert summary["audit_log_path"].endswith("exec-1000.log")
    assert summary["audit_jsonl_path"].endswith("exec-1000.jsonl")


def test_write_run_summary_json_creates_file(tmp_path) -> None:
    db_path = tmp_path / "fwo.sqlite3"
    store = SQLiteAuditStore(db_path)
    store.initialize()
    store.record_execution_start(
        execution_id="exec-2000",
        runbook_name="disk_full",
        runbook_version="1.0",
        target="linux-db-01",
        dry_run=True,
    )
    store.record_execution_end("exec-2000", final_status="dry_run")

    summary = build_run_summary(store, "exec-2000")
    output_path = write_run_summary_json(tmp_path / "summary.json", summary)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["execution"]["id"] == "exec-2000"
    assert payload["stats"]["notification_count"] == 0
