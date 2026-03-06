"""SQLite persistence layer for execution and audit history."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ExecutionRecord:
    """Stored execution summary row."""

    id: str
    runbook_name: str
    runbook_version: str | None
    target: str
    status: str
    dry_run: bool
    started_at: str
    ended_at: str | None


@dataclass(frozen=True)
class StepAttemptRecord:
    """Stored step-attempt row."""

    id: str
    execution_id: str
    step_id: str
    step_type: str
    attempt_number: int
    started_at: str
    ended_at: str
    success: bool
    exit_status: int | None
    duration_ms: int
    branch_taken: str
    command_summary: str
    error_summary: str | None


@dataclass(frozen=True)
class NotificationRecord:
    """Stored notifier outcome row."""

    id: str
    execution_id: str
    step_id: str | None
    notifier_type: str
    destination: str
    status: str
    error_summary: str | None
    sent_at: str


class SQLiteAuditStore:
    """Simple SQLite-backed audit store for orchestrator records."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        """Create tables and enforce schema version for this project."""
        with self._connect() as conn:
            self._apply_schema(conn)

    def record_execution_start(
        self,
        execution_id: str,
        runbook_name: str,
        runbook_version: str | None,
        target: str,
        dry_run: bool,
    ) -> None:
        """Insert a new execution row when a run starts."""
        started_at = _utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO executions (
                    id,
                    runbook_name,
                    runbook_version,
                    target,
                    status,
                    dry_run,
                    started_at,
                    ended_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    execution_id,
                    runbook_name,
                    runbook_version,
                    target,
                    "running",
                    int(dry_run),
                    started_at,
                    None,
                ),
            )

    def record_execution_end(self, execution_id: str, final_status: str) -> None:
        """Update execution row with final status and end time."""
        ended_at = _utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE executions
                SET status = ?, ended_at = ?
                WHERE id = ?
                """,
                (final_status, ended_at, execution_id),
            )

    def record_step_attempt(
        self,
        attempt_id: str,
        execution_id: str,
        step_id: str,
        step_type: str,
        attempt_number: int,
        started_at: str,
        ended_at: str,
        success: bool,
        exit_status: int | None,
        duration_ms: int,
        branch_taken: str,
        command_summary: str,
        error_summary: str | None,
    ) -> None:
        """Insert one step-attempt row."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO step_attempts (
                    id,
                    execution_id,
                    step_id,
                    step_type,
                    attempt_number,
                    started_at,
                    ended_at,
                    success,
                    exit_status,
                    duration_ms,
                    branch_taken,
                    command_summary,
                    error_summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt_id,
                    execution_id,
                    step_id,
                    step_type,
                    attempt_number,
                    started_at,
                    ended_at,
                    int(success),
                    exit_status,
                    duration_ms,
                    branch_taken,
                    command_summary,
                    error_summary,
                ),
            )

    def record_notification(
        self,
        notification_id: str,
        execution_id: str,
        step_id: str | None,
        notifier_type: str,
        destination: str,
        status: str,
        error_summary: str | None,
    ) -> None:
        """Insert one notifier outcome row."""
        sent_at = _utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO notifications (
                    id,
                    execution_id,
                    step_id,
                    notifier_type,
                    destination,
                    status,
                    error_summary,
                    sent_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    notification_id,
                    execution_id,
                    step_id,
                    notifier_type,
                    destination,
                    status,
                    error_summary,
                    sent_at,
                ),
            )

    def get_execution(self, execution_id: str) -> ExecutionRecord | None:
        """Return one execution row or None."""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    id,
                    runbook_name,
                    runbook_version,
                    target,
                    status,
                    dry_run,
                    started_at,
                    ended_at
                FROM executions
                WHERE id = ?
                """,
                (execution_id,),
            ).fetchone()

        if row is None:
            return None

        return ExecutionRecord(
            id=row["id"],
            runbook_name=row["runbook_name"],
            runbook_version=row["runbook_version"],
            target=row["target"],
            status=row["status"],
            dry_run=bool(row["dry_run"]),
            started_at=row["started_at"],
            ended_at=row["ended_at"],
        )

    def list_step_attempts(self, execution_id: str) -> list[StepAttemptRecord]:
        """Return all step attempts for one execution."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    execution_id,
                    step_id,
                    step_type,
                    attempt_number,
                    started_at,
                    ended_at,
                    success,
                    exit_status,
                    duration_ms,
                    branch_taken,
                    command_summary,
                    error_summary
                FROM step_attempts
                WHERE execution_id = ?
                ORDER BY started_at, attempt_number
                """,
                (execution_id,),
            ).fetchall()

        return [
            StepAttemptRecord(
                id=row["id"],
                execution_id=row["execution_id"],
                step_id=row["step_id"],
                step_type=row["step_type"],
                attempt_number=row["attempt_number"],
                started_at=row["started_at"],
                ended_at=row["ended_at"],
                success=bool(row["success"]),
                exit_status=row["exit_status"],
                duration_ms=row["duration_ms"],
                branch_taken=row["branch_taken"],
                command_summary=row["command_summary"],
                error_summary=row["error_summary"],
            )
            for row in rows
        ]

    def list_notifications(self, execution_id: str) -> list[NotificationRecord]:
        """Return all notifier outcomes for one execution."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    execution_id,
                    step_id,
                    notifier_type,
                    destination,
                    status,
                    error_summary,
                    sent_at
                FROM notifications
                WHERE execution_id = ?
                ORDER BY sent_at
                """,
                (execution_id,),
            ).fetchall()

        return [
            NotificationRecord(
                id=row["id"],
                execution_id=row["execution_id"],
                step_id=row["step_id"],
                notifier_type=row["notifier_type"],
                destination=row["destination"],
                status=row["status"],
                error_summary=row["error_summary"],
                sent_at=row["sent_at"],
            )
            for row in rows
        ]

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _apply_schema(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER NOT NULL
            )
            """
        )

        row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
        if row is None:
            self._create_v1_schema(conn)
            conn.execute(
                "INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,)
            )
            return

        current_version = int(row["version"])
        if current_version != SCHEMA_VERSION:
            msg = (
                "Unsupported schema version "
                f"{current_version}. Expected {SCHEMA_VERSION}."
            )
            raise RuntimeError(msg)

    @staticmethod
    def _create_v1_schema(conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS executions (
                id TEXT PRIMARY KEY,
                runbook_name TEXT NOT NULL,
                runbook_version TEXT,
                target TEXT NOT NULL,
                status TEXT NOT NULL,
                dry_run INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS step_attempts (
                id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                step_type TEXT NOT NULL,
                attempt_number INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT NOT NULL,
                success INTEGER NOT NULL,
                exit_status INTEGER,
                duration_ms INTEGER NOT NULL,
                branch_taken TEXT NOT NULL,
                command_summary TEXT NOT NULL,
                error_summary TEXT,
                FOREIGN KEY (execution_id) REFERENCES executions(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                step_id TEXT,
                notifier_type TEXT NOT NULL,
                destination TEXT NOT NULL,
                status TEXT NOT NULL,
                error_summary TEXT,
                sent_at TEXT NOT NULL,
                FOREIGN KEY (execution_id) REFERENCES executions(id)
            )
            """
        )


def _utc_now_iso() -> str:
    """Return UTC timestamp in ISO-8601 string format."""
    return datetime.now(tz=UTC).isoformat(timespec="seconds")
