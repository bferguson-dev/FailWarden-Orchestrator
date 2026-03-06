"""SSH executor implementation for Linux and Windows-over-SSH."""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

import paramiko

from failwarden_orchestrator.executors.base import ExecutionResult


@dataclass(frozen=True)
class SSHTarget:
    """Connection target details for SSH execution."""

    host: str
    user: str
    port: int = 22


@dataclass(frozen=True)
class SSHAuthConfig:
    """Authentication settings for SSH connections."""

    key_path: str | None = None
    password: str | None = None


class SSHExecutor:
    """Execute commands over SSH and return normalized results."""

    def __init__(
        self,
        target: SSHTarget,
        auth: SSHAuthConfig,
        *,
        connect_timeout_seconds: int = 10,
        strict_host_key: bool = True,
    ) -> None:
        self.target = target
        self.auth = auth
        self.connect_timeout_seconds = connect_timeout_seconds
        if not strict_host_key:
            msg = "V1 requires strict host key verification."
            raise ValueError(msg)
        self.strict_host_key = strict_host_key

    def execute(self, command: str, timeout_seconds: int) -> ExecutionResult:
        """Run one command over SSH with per-attempt timeout."""
        started = monotonic()
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.RejectPolicy())

        try:
            client.connect(
                hostname=self.target.host,
                port=self.target.port,
                username=self.target.user,
                key_filename=self.auth.key_path,
                password=self.auth.password,
                timeout=self.connect_timeout_seconds,
                banner_timeout=self.connect_timeout_seconds,
                auth_timeout=self.connect_timeout_seconds,
                look_for_keys=False,
                allow_agent=False,
            )
            stdin, stdout, stderr = client.exec_command(
                command,
                timeout=timeout_seconds,
            )  # nosec B601
            del stdin

            exit_status = stdout.channel.recv_exit_status()
            output = stdout.read().decode("utf-8", errors="replace").strip()
            error = stderr.read().decode("utf-8", errors="replace").strip()

            duration_ms = int((monotonic() - started) * 1000)
            success = exit_status == 0
            return ExecutionResult(
                success=success,
                output=output,
                error=error or None,
                exit_status=exit_status,
                duration_ms=duration_ms,
                metadata={
                    "executor": "ssh",
                    "host": self.target.host,
                    "port": self.target.port,
                    "user": self.target.user,
                    "strict_host_key": self.strict_host_key,
                },
            )
        except paramiko.SSHException as exc:
            return self._transport_failure("ssh_error", str(exc), started)
        except TimeoutError:
            return self._transport_failure(
                "timeout", "SSH operation timed out", started
            )
        except OSError as exc:
            return self._transport_failure("network_error", str(exc), started)
        finally:
            client.close()

    def _transport_failure(
        self,
        reason: str,
        message: str,
        started: float,
    ) -> ExecutionResult:
        """Convert transport exceptions into normalized failure results."""
        duration_ms = int((monotonic() - started) * 1000)
        return ExecutionResult(
            success=False,
            output="",
            error=message,
            exit_status=None,
            duration_ms=duration_ms,
            metadata={
                "executor": "ssh",
                "reason": reason,
                "host": self.target.host,
                "port": self.target.port,
                "user": self.target.user,
                "strict_host_key": self.strict_host_key,
            },
        )
