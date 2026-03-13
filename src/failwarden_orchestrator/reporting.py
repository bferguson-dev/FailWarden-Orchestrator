"""Run summary reporting helpers."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from failwarden_orchestrator.persistence import SQLiteAuditStore


@dataclass(frozen=True)
class RunSummary:
    """Combined execution, step, notification, and audit artifact summary."""

    execution: dict[str, Any]
    step_attempts: list[dict[str, Any]]
    notifications: list[dict[str, Any]]
    stats: dict[str, int]
    audit_log_path: str | None
    audit_jsonl_path: str | None

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable summary payload."""
        return asdict(self)


def build_run_summary(
    store: SQLiteAuditStore,
    execution_id: str,
    *,
    audit_dir: str | Path | None = None,
) -> RunSummary:
    """Load one execution and related artifacts into a summary payload."""
    execution = store.get_execution(execution_id)
    if execution is None:
        msg = f"Execution '{execution_id}' was not found."
        raise ValueError(msg)

    step_attempts = [asdict(item) for item in store.list_step_attempts(execution_id)]
    notifications = [asdict(item) for item in store.list_notifications(execution_id)]

    audit_log_path = None
    audit_jsonl_path = None
    if audit_dir is not None:
        audit_root = Path(audit_dir)
        log_path = audit_root / f"{execution_id}.log"
        jsonl_path = audit_root / f"{execution_id}.jsonl"
        if log_path.exists():
            audit_log_path = str(log_path)
        if jsonl_path.exists():
            audit_jsonl_path = str(jsonl_path)

    return RunSummary(
        execution=asdict(execution),
        step_attempts=step_attempts,
        notifications=notifications,
        stats={
            "notification_count": len(notifications),
            "step_attempt_count": len(step_attempts),
        },
        audit_log_path=audit_log_path,
        audit_jsonl_path=audit_jsonl_path,
    )


def write_run_summary_json(path: str | Path, summary: RunSummary) -> Path:
    """Write one run summary JSON artifact."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(summary.to_dict(), handle, indent=2, sort_keys=True)
        handle.write("\n")
    return output_path
