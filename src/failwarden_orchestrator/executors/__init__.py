"""Executor interfaces and transport implementations."""

from failwarden_orchestrator.executors.base import BaseExecutor, ExecutionResult
from failwarden_orchestrator.executors.ssh import SSHAuthConfig, SSHExecutor, SSHTarget

__all__ = [
    "BaseExecutor",
    "ExecutionResult",
    "SSHAuthConfig",
    "SSHExecutor",
    "SSHTarget",
]
