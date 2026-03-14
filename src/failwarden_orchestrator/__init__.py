"""FailWarden Orchestrator package."""

from failwarden_orchestrator.audit import AuditEvent, AuditLogger
from failwarden_orchestrator.compiler import RunbookCompiler
from failwarden_orchestrator.engine import EngineRunResult, ExecutionEngine
from failwarden_orchestrator.executors import (
    BaseExecutor,
    ExecutionResult,
    SSHAuthConfig,
    SSHExecutor,
    SSHTarget,
)
from failwarden_orchestrator.notifiers import (
    BaseNotifier,
    EmailNotifier,
    NotificationContext,
    NotificationSendResult,
    SlackNotifier,
)
from failwarden_orchestrator.persistence import (
    ExecutionRecord,
    NotificationRecord,
    SQLiteAuditStore,
    StepAttemptRecord,
)
from failwarden_orchestrator.reporting import RunSummary, build_run_summary
from failwarden_orchestrator.validation import RunbookValidationError, ValidationIssue

__version__ = "0.2.0"

__all__ = [
    "AuditEvent",
    "AuditLogger",
    "BaseExecutor",
    "BaseNotifier",
    "EmailNotifier",
    "ExecutionRecord",
    "ExecutionResult",
    "EngineRunResult",
    "ExecutionEngine",
    "NotificationRecord",
    "NotificationContext",
    "NotificationSendResult",
    "RunbookCompiler",
    "RunSummary",
    "RunbookValidationError",
    "SSHAuthConfig",
    "SSHExecutor",
    "SSHTarget",
    "SlackNotifier",
    "SQLiteAuditStore",
    "StepAttemptRecord",
    "ValidationIssue",
    "__version__",
    "build_run_summary",
]
