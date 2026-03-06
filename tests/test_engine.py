"""Execution engine tests for Step 7."""

from __future__ import annotations

from collections.abc import Sequence

from failwarden_orchestrator.audit import AuditLogger
from failwarden_orchestrator.engine import ExecutionEngine
from failwarden_orchestrator.executors.base import ExecutionResult
from failwarden_orchestrator.models import (
    CompiledRunbook,
    EndStep,
    EscalateNotify,
    EscalateStep,
    SSHExpect,
    SSHStep,
)
from failwarden_orchestrator.persistence import SQLiteAuditStore


class FakeExecutor:
    """Deterministic executor stub for engine tests."""

    def __init__(self, results: Sequence[ExecutionResult]) -> None:
        self.results = list(results)
        self.calls: list[tuple[str, int]] = []

    def execute(self, command: str, timeout_seconds: int) -> ExecutionResult:
        self.calls.append((command, timeout_seconds))
        if not self.results:
            msg = "No more fake executor results available."
            raise RuntimeError(msg)
        return self.results.pop(0)


def make_runbook(
    *,
    retries: int = 0,
    stdout_contains: str | None = "active",
) -> CompiledRunbook:
    """Create a minimal runbook for engine behavior tests."""
    check = SSHStep(
        id="check_service",
        type="ssh",
        name="Check service",
        command="systemctl is-active nginx",
        expect=SSHExpect(exit_code=0, stdout_contains=stdout_contains),
        timeout=20,
        retries=retries,
        retry_delay=3,
        on_success="done",
        on_failure="escalate_ops",
    )
    done = EndStep(
        id="done",
        type="end",
        name="Done",
        summary="Service recovered",
    )
    escalate = EscalateStep(
        id="escalate_ops",
        type="escalate",
        name="Escalate",
        notify=EscalateNotify(slack_enabled=True, email_enabled=True),
    )

    steps = [check, done, escalate]
    return CompiledRunbook(
        name="linux_service_down",
        description="Test runbook",
        version="1.0",
        vars={},
        entry_step="check_service",
        steps_in_order=steps,
        steps_by_id={step.id: step for step in steps},
    )


def test_engine_success_path_reaches_end() -> None:
    runbook = make_runbook()
    executor = FakeExecutor(
        [
            ExecutionResult(
                success=True,
                output="active",
                error=None,
                exit_status=0,
                duration_ms=100,
                metadata={},
            )
        ]
    )
    engine = ExecutionEngine(executor, id_factory=lambda: "id-1")

    result = engine.run(runbook, target="linux-web-01")

    assert result.final_status == "success"
    assert result.step_path == ["check_service", "done"]
    assert result.attempts == 1
    assert executor.calls == [("systemctl is-active nginx", 20)]


def test_engine_retries_then_succeeds() -> None:
    runbook = make_runbook(retries=1)
    executor = FakeExecutor(
        [
            ExecutionResult(
                success=False,
                output="inactive",
                error="not running",
                exit_status=1,
                duration_ms=120,
                metadata={},
            ),
            ExecutionResult(
                success=True,
                output="active",
                error=None,
                exit_status=0,
                duration_ms=100,
                metadata={},
            ),
        ]
    )
    delays: list[int] = []

    engine = ExecutionEngine(
        executor,
        sleep_fn=lambda seconds: delays.append(seconds),
        id_factory=lambda: "id-2",
    )

    result = engine.run(runbook, target="linux-web-01")

    assert result.final_status == "success"
    assert result.attempts == 2
    assert delays == [3]


def test_engine_branches_to_escalation_after_retries_exhausted() -> None:
    runbook = make_runbook(retries=1)
    executor = FakeExecutor(
        [
            ExecutionResult(
                success=False,
                output="inactive",
                error="first failure",
                exit_status=1,
                duration_ms=110,
                metadata={},
            ),
            ExecutionResult(
                success=False,
                output="inactive",
                error="second failure",
                exit_status=1,
                duration_ms=130,
                metadata={},
            ),
        ]
    )

    engine = ExecutionEngine(
        executor,
        sleep_fn=lambda _seconds: None,
        id_factory=lambda: "id-3",
    )

    result = engine.run(runbook, target="linux-web-01")

    assert result.final_status == "escalated"
    assert result.step_path == ["check_service", "escalate_ops"]
    assert result.attempts == 2


def test_engine_uses_expectation_not_only_exit_code() -> None:
    runbook = make_runbook(retries=0, stdout_contains="active (running)")
    executor = FakeExecutor(
        [
            ExecutionResult(
                success=True,
                output="inactive",
                error=None,
                exit_status=0,
                duration_ms=90,
                metadata={},
            )
        ]
    )

    engine = ExecutionEngine(executor, id_factory=lambda: "id-4")
    result = engine.run(runbook, target="linux-web-01")

    assert result.final_status == "escalated"


def test_engine_writes_persistence_and_audit_artifacts(tmp_path) -> None:
    runbook = make_runbook()
    executor = FakeExecutor(
        [
            ExecutionResult(
                success=True,
                output="active",
                error=None,
                exit_status=0,
                duration_ms=100,
                metadata={},
            )
        ]
    )

    db_path = tmp_path / "fwo.sqlite3"
    audit_dir = tmp_path / "audit"

    store = SQLiteAuditStore(db_path)
    store.initialize()
    logger = AuditLogger(audit_dir)

    engine = ExecutionEngine(
        executor,
        audit_store=store,
        audit_logger=logger,
        id_factory=lambda: "exec-700",
    )

    result = engine.run(runbook, target="linux-web-01")

    execution = store.get_execution(result.execution_id)
    assert execution is not None
    assert execution.status == "success"

    attempts = store.list_step_attempts(result.execution_id)
    assert len(attempts) == 1
    assert attempts[0].branch_taken == "on_success"

    log_path = audit_dir / "exec-700.log"
    assert log_path.exists()
    log_text = log_path.read_text(encoding="utf-8")
    assert "event=execution_start" in log_text
    assert "event=step_attempt" in log_text
    assert "event=execution_end" in log_text
