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
from failwarden_orchestrator.notifiers import (
    BaseNotifier,
    NotificationContext,
    NotificationSendResult,
    utc_now_iso,
)
from failwarden_orchestrator.persistence import SQLiteAuditStore


@dataclass(frozen=True)
class EngineRunResult:
    """Summary of one engine run."""

    execution_id: str
    final_status: str
    step_path: list[str]
    attempts: int
    dry_run_branch_map: dict[str, list[str]] | None = None


class ExecutionEngine:
    """Walk runbook steps and execute commands with retry and branching."""

    def __init__(
        self,
        executor: BaseExecutor,
        *,
        audit_store: SQLiteAuditStore | None = None,
        audit_logger: AuditLogger | None = None,
        notifiers: list[BaseNotifier] | None = None,
        sleep_fn: Callable[[int], None] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.executor = executor
        self.audit_store = audit_store
        self.audit_logger = audit_logger
        self.notifiers = notifiers or []
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
        execution_id = self.id_factory()
        step_path: list[str] = []
        attempts = 0
        dry_run_branch_map: dict[str, list[str]] | None = {} if dry_run else None

        if self.audit_store:
            self.audit_store.record_execution_start(
                execution_id=execution_id,
                runbook_name=runbook.name,
                runbook_version=runbook.version,
                target=target,
                dry_run=dry_run,
            )
        if self.audit_logger:
            self.audit_logger.log_execution_start(
                execution_id=execution_id,
                runbook=runbook.name,
                target=target,
                dry_run=dry_run,
            )

        current_step_id = runbook.entry_step
        final_status = "failed"
        last_failure_reason = "unknown_failure"

        while True:
            step = runbook.steps_by_id[current_step_id]
            step_path.append(step.id)

            if dry_run and isinstance(step, SSHStep):
                attempts += 1
                if dry_run_branch_map is not None:
                    dry_run_branch_map[step.id] = [step.on_success, step.on_failure]

                started_at = _utc_now_iso()
                ended_at = _utc_now_iso()
                if self.audit_store:
                    self.audit_store.record_step_attempt(
                        attempt_id=str(uuid4()),
                        execution_id=execution_id,
                        step_id=step.id,
                        step_type=step.type,
                        attempt_number=1,
                        started_at=started_at,
                        ended_at=ended_at,
                        success=True,
                        exit_status=None,
                        duration_ms=0,
                        branch_taken="simulated",
                        command_summary=step.command,
                        error_summary=None,
                    )
                if self.audit_logger:
                    self.audit_logger.log_step_attempt(
                        execution_id=execution_id,
                        runbook=runbook.name,
                        target=target,
                        step_id=step.id,
                        step_type=step.type,
                        attempt_number=1,
                        result="simulated",
                        branch="simulated",
                        duration_ms=0,
                        exit_status=None,
                        error=None,
                    )

                # Dry-run follows on_success path as the preview default.
                current_step_id = step.on_success
                continue

            if isinstance(step, SSHStep):
                next_step_id, step_attempts, failure_reason = self._run_ssh_step(
                    runbook=runbook,
                    target=target,
                    execution_id=execution_id,
                    step=step,
                )
                attempts += step_attempts
                if failure_reason is not None:
                    last_failure_reason = failure_reason
                current_step_id = next_step_id
                continue

            if isinstance(step, EscalateStep):
                if dry_run:
                    final_status = "dry_run"
                else:
                    final_status = "escalated"
                    self._run_escalation(
                        execution_id=execution_id,
                        runbook=runbook,
                        target=target,
                        step=step,
                        failure_reason=last_failure_reason,
                    )
                    if self.audit_logger:
                        self.audit_logger.log_escalation(
                            execution_id=execution_id,
                            runbook=runbook.name,
                            target=target,
                            step_id=step.id,
                            reason=last_failure_reason,
                        )
                break

            if isinstance(step, EndStep):
                final_status = "dry_run" if dry_run else "success"
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
            dry_run_branch_map=dry_run_branch_map,
        )

    def _run_ssh_step(
        self,
        *,
        runbook: CompiledRunbook,
        target: str,
        execution_id: str,
        step: SSHStep,
    ) -> tuple[str, int, str | None]:
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
                    attempt_id=str(uuid4()),
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
                return step.on_success, attempt_number, None

            if has_retry_left:
                self.sleep_fn(step.retry_delay)
                continue

            reason = result.error or "step expectation did not match"
            return step.on_failure, attempt_number, reason

        msg = "Step attempt loop ended unexpectedly."
        raise RuntimeError(msg)

    def _run_escalation(
        self,
        *,
        execution_id: str,
        runbook: CompiledRunbook,
        target: str,
        step: EscalateStep,
        failure_reason: str,
    ) -> None:
        """Build context and fan out to all configured notifiers."""
        context = NotificationContext(
            execution_id=execution_id,
            runbook_name=runbook.name,
            target=target,
            step_id=step.id,
            failure_reason=failure_reason,
            notify_title=step.notify.title,
            notify_message=step.notify.message,
            slack_enabled=step.notify.slack_enabled,
            email_enabled=step.notify.email_enabled,
            slack_channel=step.notify.slack_channel,
            email_to=step.notify.email_to or [],
            occurred_at=utc_now_iso(),
        )

        for notifier in self.notifiers:
            result = self._send_notifier(notifier=notifier, context=context)
            self._record_notification(
                execution_id=execution_id,
                runbook_name=runbook.name,
                target=target,
                step_id=step.id,
                result=result,
            )

    @staticmethod
    def _send_notifier(
        *,
        notifier: BaseNotifier,
        context: NotificationContext,
    ) -> NotificationSendResult:
        """Send notification and normalize any unexpected notifier exception."""
        try:
            return notifier.send(context)
        except Exception as exc:  # noqa: BLE001
            return NotificationSendResult(
                notifier_type=notifier.notifier_type,
                destination="unknown",
                success=False,
                error=str(exc),
            )

    def _record_notification(
        self,
        *,
        execution_id: str,
        runbook_name: str,
        target: str,
        step_id: str,
        result: NotificationSendResult,
    ) -> None:
        """Record one notifier result in persistence and structured audit log."""
        status = "sent" if result.success else "failed"
        if self.audit_store:
            self.audit_store.record_notification(
                notification_id=str(uuid4()),
                execution_id=execution_id,
                step_id=step_id,
                notifier_type=result.notifier_type,
                destination=result.destination,
                status=status,
                error_summary=result.error,
            )

        if self.audit_logger:
            self.audit_logger.log_notification(
                execution_id=execution_id,
                runbook=runbook_name,
                target=target,
                step_id=step_id,
                notifier=result.notifier_type,
                destination=result.destination,
                result=status,
                error=result.error,
            )

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
