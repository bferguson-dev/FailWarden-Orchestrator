"""SSH executor tests for Step 6."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import paramiko
import pytest

from failwarden_orchestrator.executors.ssh import SSHAuthConfig, SSHExecutor, SSHTarget


def make_executor(strict_host_key: bool = True) -> SSHExecutor:
    """Build a reusable SSH executor for tests."""
    return SSHExecutor(
        target=SSHTarget(host="linux-web-01", user="ubuntu", port=22),
        auth=SSHAuthConfig(key_path="/home/test/fake_key"),
        connect_timeout_seconds=5,
        strict_host_key=strict_host_key,
    )


def stub_successful_command(client: MagicMock) -> None:
    """Configure mocked SSH client to return a simple success result."""
    mock_stdout = MagicMock()
    mock_stderr = MagicMock()
    mock_stdout.channel.recv_exit_status.return_value = 0
    mock_stdout.read.return_value = b"ok\n"
    mock_stderr.read.return_value = b""
    client.exec_command.return_value = (MagicMock(), mock_stdout, mock_stderr)


@patch("failwarden_orchestrator.executors.ssh.paramiko.SSHClient")
def test_execute_success_returns_normalized_result(mock_client_cls: MagicMock) -> None:
    executor = make_executor()
    client = mock_client_cls.return_value

    mock_stdout = MagicMock()
    mock_stderr = MagicMock()
    mock_stdout.channel.recv_exit_status.return_value = 0
    mock_stdout.read.return_value = b"active\n"
    mock_stderr.read.return_value = b""
    client.exec_command.return_value = (MagicMock(), mock_stdout, mock_stderr)

    result = executor.execute("systemctl is-active nginx", timeout_seconds=20)

    assert result.success
    assert result.output == "active"
    assert result.error is None
    assert result.exit_status == 0
    assert result.metadata["executor"] == "ssh"
    assert result.metadata["host"] == "linux-web-01"


@patch("failwarden_orchestrator.executors.ssh.paramiko.SSHClient")
def test_execute_failure_exit_code_is_normalized(mock_client_cls: MagicMock) -> None:
    executor = make_executor()
    client = mock_client_cls.return_value

    mock_stdout = MagicMock()
    mock_stderr = MagicMock()
    mock_stdout.channel.recv_exit_status.return_value = 2
    mock_stdout.read.return_value = b""
    mock_stderr.read.return_value = b"service not found\n"
    client.exec_command.return_value = (MagicMock(), mock_stdout, mock_stderr)

    result = executor.execute("systemctl is-active missing", timeout_seconds=20)

    assert not result.success
    assert result.output == ""
    assert result.error == "service not found"
    assert result.exit_status == 2


@patch("failwarden_orchestrator.executors.ssh.paramiko.SSHClient")
def test_execute_network_timeout_returns_transport_failure(
    mock_client_cls: MagicMock,
) -> None:
    executor = make_executor()
    client = mock_client_cls.return_value
    client.connect.side_effect = TimeoutError()

    result = executor.execute("echo ok", timeout_seconds=10)

    assert not result.success
    assert result.exit_status is None
    assert result.metadata["reason"] == "timeout"
    assert "timed out" in (result.error or "")


@patch("failwarden_orchestrator.executors.ssh.paramiko.SSHClient")
def test_execute_ssh_exception_returns_transport_failure(
    mock_client_cls: MagicMock,
) -> None:
    executor = make_executor()
    client = mock_client_cls.return_value
    client.connect.side_effect = paramiko.SSHException("auth failed")

    result = executor.execute("echo ok", timeout_seconds=10)

    assert not result.success
    assert result.exit_status is None
    assert result.metadata["reason"] == "ssh_error"
    assert result.error == "auth failed"


@patch("failwarden_orchestrator.executors.ssh.paramiko.SSHClient")
def test_executor_uses_strict_host_key_policy(mock_client_cls: MagicMock) -> None:
    strict_executor = make_executor(strict_host_key=True)
    stub_successful_command(mock_client_cls.return_value)
    strict_executor.execute("echo ok", timeout_seconds=5)

    strict_client = mock_client_cls.return_value
    policy_arg = strict_client.set_missing_host_key_policy.call_args.args[0]
    assert isinstance(policy_arg, paramiko.RejectPolicy)


def test_executor_rejects_non_strict_host_key_mode() -> None:
    with pytest.raises(ValueError) as exc_info:
        make_executor(strict_host_key=False)
    assert "strict host key verification" in str(exc_info.value)
