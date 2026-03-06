"""Execution engine for compiled runbooks."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from failwarden_orchestrator.audit import AuditLogger
from failwarden_orchestrator.executors.base import BaseExecutor, ExecutionResult
from failwarden_orchestrator.models import (
    CompiledRunbook,
    EndStep,
    EscalateStep,
    SSHStep,
)
from failwarden_orchestrator.persistence import SQLiteAuditStore


@dataclass(frozen=True)
class EngineRunResult:
    """Summary of one engine run."""

    execution_id: str
    final_status: str
    step_path: list[str]
    attempts: int


class ExecutionEngine:
    """Walk runbook steps and execute commands with retry and branching."""

    def __init__(
        self,
        executor: BaseExecutor,
        *,
        audit_store: SQLiteAuditStore | None = None,
        audit_logger: AuditLogger | None = None,
        sleep_fn: Callable[[int], None] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.executor = executor
        self.audit_store = audit_store
        self.audit_logger = audit_logger
        self.sleep_fn = sleep_fn or time.sleep
        self.id_factory = id_factory or (lambda: str(uuid4()))

    def run(
        self,
        runbook: CompiledRunbook,
        target: str,
        *,
        dry_run: bool = False,
    ) -> EngineRunResult:
        """Execute one compiled runbook against one target host."""
        if dry_run:
            msg = "Dry-run execution belongs to Step 10 and is not enabled yet."
            raise ValueError(msg)

        execution_id = self.id_factory()
        step_path: list[str] = []
        attempts = 0

        if self.audit_store:
            self.audit_store.record_execution_start(
                execution_id=execution_id,
                runbook_name=runbook.name,
                runbook_version=runbook.version,
                target=target,
                dry_run=False,
            )
        if self.audit_logger:
            self.audit_logger.log_execution_start(
                execution_id=execution_id,
                runbook=runbook.name,
                target=target,
                dry_run=False,
            )

        current_step_id = runbook.entry_step
        final_status = "failed"

        while True:
            step = runbook.steps_by_id[current_step_id]
            step_path.append(step.id)

            if isinstance(step, SSHStep):
                next_step_id, step_attempts = self._run_ssh_step(
                    runbook=runbook,
                    target=target,
                    execution_id=execution_id,
                    step=step,
                )
                attempts += step_attempts
                current_step_id = next_step_id
                continue

            if isinstance(step, EscalateStep):
                final_status = "escalated"
                if self.audit_logger:
                    self.audit_logger.log_escalation(
                        execution_id=execution_id,
                        runbook=runbook.name,
                        target=target,
                        step_id=step.id,
                        reason="escalation_step_reached",
                    )
                break

            if isinstance(step, EndStep):
                final_status = "success"
                break

            msg = f"Unsupported step type encountered at runtime: {step.type}"
            raise RuntimeError(msg)

        if self.audit_store:
            self.audit_store.record_execution_end(
                execution_id=execution_id,
                final_status=final_status,
            )
        if self.audit_logger:
            self.audit_logger.log_execution_end(
                execution_id=execution_id,
                runbook=runbook.name,
                target=target,
                final_status=final_status,
            )

        return EngineRunResult(
            execution_id=execution_id,
            final_status=final_status,
            step_path=step_path,
            attempts=attempts,
        )

    def _run_ssh_step(
        self,
        *,
        runbook: CompiledRunbook,
        target: str,
        execution_id: str,
        step: SSHStep,
    ) -> tuple[str, int]:
        total_attempts = 1 + step.retries

        for attempt_number in range(1, total_attempts + 1):
            started_at = _utc_now_iso()
            result = self.executor.execute(
                command=step.command,
                timeout_seconds=step.timeout,
            )
            ended_at = _utc_now_iso()

            matches_expectation = self._matches_expectation(step=step, result=result)
            has_retry_left = attempt_number < total_attempts
            if matches_expectation:
                branch_taken = "on_success"
            elif has_retry_left:
                branch_taken = "retry"
            else:
                branch_taken = "on_failure"

            if self.audit_store:
                self.audit_store.record_step_attempt(
                    attempt_id=self.id_factory(),
                    execution_id=execution_id,
                    step_id=step.id,
                    step_type=step.type,
                    attempt_number=attempt_number,
                    started_at=started_at,
                    ended_at=ended_at,
                    success=matches_expectation,
                    exit_status=result.exit_status,
                    duration_ms=result.duration_ms,
                    branch_taken=branch_taken,
                    command_summary=step.command,
                    error_summary=result.error,
                )

            if self.audit_logger:
                result_label = "success" if matches_expectation else "failure"
                self.audit_logger.log_step_attempt(
                    execution_id=execution_id,
                    runbook=runbook.name,
                    target=target,
                    step_id=step.id,
                    step_type=step.type,
                    attempt_number=attempt_number,
                    result=result_label,
                    branch=branch_taken,
                    duration_ms=result.duration_ms,
                    exit_status=result.exit_status,
                    error=result.error,
                )

            if matches_expectation:
                return step.on_success, attempt_number

            if has_retry_left:
                self.sleep_fn(step.retry_delay)
                continue

            return step.on_failure, attempt_number

        msg = "Step attempt loop ended unexpectedly."
        raise RuntimeError(msg)

    @staticmethod
    def _matches_expectation(step: SSHStep, result: ExecutionResult) -> bool:
        """Check whether command result satisfies runbook expectation."""
        if result.exit_status != step.expect.exit_code:
            return False

        if step.expect.stdout_contains is not None:
            if step.expect.stdout_contains not in result.output:
                return False

        if step.expect.stderr_contains is not None:
            stderr = result.error or ""
            if step.expect.stderr_contains not in stderr:
                return False

        return True


def _utc_now_iso() -> str:
    """Return UTC timestamp in ISO-8601 string format."""
    return datetime.now(tz=UTC).isoformat(timespec="seconds")
