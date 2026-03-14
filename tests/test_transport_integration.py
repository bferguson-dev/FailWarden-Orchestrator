"""Controlled local integration tests for SSH, Slack, and SMTP transports."""

from __future__ import annotations

import json
import socket
import socketserver
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import paramiko

from failwarden_orchestrator.executors.ssh import SSHAuthConfig, SSHExecutor, SSHTarget
from failwarden_orchestrator.notifiers import NotificationContext
from failwarden_orchestrator.notifiers.email import EmailNotifier
from failwarden_orchestrator.notifiers.slack import SlackNotifier

SSH_TEST_PASSWORD = "test-password"  # noqa: S105


def sample_context() -> NotificationContext:
    """Create a reusable notification context for integration tests."""
    return NotificationContext(
        execution_id="exec-integration-1",
        runbook_name="linux_service_down",
        target="linux-web-01",
        step_id="escalate_ops",
        failure_reason="service restart failed",
        notify_title="Escalation: linux_service_down",
        notify_message="Manual intervention required",
        slack_enabled=True,
        email_enabled=True,
        slack_channel="#ops-alerts",
        email_to=["ops@example.local"],
        occurred_at="2026-03-13T00:00:00+00:00",
    )


@dataclass(frozen=True)
class _SSHResponse:
    exit_status: int
    stdout: str
    stderr: str = ""


class _SSHServerInterface(paramiko.ServerInterface):
    def __init__(self, command_responses: dict[str, _SSHResponse]) -> None:
        self.command_responses = command_responses
        self.command: str | None = None
        self.command_event = threading.Event()

    def check_auth_password(self, username: str, password: str) -> int:
        if username == "ubuntu" and password == SSH_TEST_PASSWORD:
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username: str) -> str:
        del username
        return "password"

    def check_channel_request(self, kind: str, chanid: int) -> int:
        del chanid
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_exec_request(self, channel, command: bytes) -> bool:
        del channel
        self.command = command.decode("utf-8")
        self.command_event.set()
        return True


class _SSHTestServer:
    def __init__(self, command_responses: dict[str, _SSHResponse]) -> None:
        self.command_responses = command_responses
        self.host_key = paramiko.RSAKey.generate(1024)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen(1)
        self.port = self._sock.getsockname()[1]
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._ready = threading.Event()
        self.error: Exception | None = None

    def start(self) -> None:
        self._thread.start()
        self._ready.wait(timeout=5)

    def close(self) -> None:
        self._sock.close()
        self._thread.join(timeout=5)
        if self.error is not None:
            raise self.error

    def _serve(self) -> None:
        try:
            self._ready.set()
            client, _addr = self._sock.accept()
            with client:
                transport = paramiko.Transport(client)
                transport.add_server_key(self.host_key)
                server = _SSHServerInterface(self.command_responses)
                transport.start_server(server=server)
                channel = transport.accept(timeout=5)
                if channel is None:
                    msg = "SSH test server timed out waiting for a channel."
                    raise RuntimeError(msg)
                if not server.command_event.wait(timeout=5):
                    msg = "SSH test server timed out waiting for exec request."
                    raise RuntimeError(msg)
                response = self.command_responses[server.command or ""]
                if response.stdout:
                    channel.send(response.stdout.encode("utf-8"))
                if response.stderr:
                    channel.send_stderr(response.stderr.encode("utf-8"))
                channel.send_exit_status(response.exit_status)
                time.sleep(0.1)
                channel.close()
                transport.close()
        except Exception as exc:  # noqa: BLE001
            self.error = exc


class _SlackCaptureHandler(BaseHTTPRequestHandler):
    requests: list[dict[str, object]] = []

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        self.__class__.requests.append(
            {
                "path": self.path,
                "headers": dict(self.headers.items()),
                "body": json.loads(body.decode("utf-8")),
            }
        )
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format: str, *args: object) -> None:
        del format, args


class _SMTPCaptureHandler(socketserver.StreamRequestHandler):
    messages: list[str] = []

    def handle(self) -> None:
        self.wfile.write(b"220 localhost ESMTP\r\n")
        data_mode = False
        message_lines: list[str] = []

        while True:
            raw_line = self.rfile.readline()
            if not raw_line:
                break
            line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
            upper = line.upper()

            if data_mode:
                if line == ".":
                    self.__class__.messages.append("\n".join(message_lines))
                    self.wfile.write(b"250 message accepted\r\n")
                    data_mode = False
                    message_lines = []
                else:
                    message_lines.append(line)
                continue

            if upper.startswith("EHLO") or upper.startswith("HELO"):
                self.wfile.write(b"250-localhost\r\n250 OK\r\n")
            elif upper.startswith("MAIL FROM"):
                self.wfile.write(b"250 OK\r\n")
            elif upper.startswith("RCPT TO"):
                self.wfile.write(b"250 OK\r\n")
            elif upper == "DATA":
                self.wfile.write(b"354 End data with <CR><LF>.<CR><LF>\r\n")
                data_mode = True
            elif upper == "QUIT":
                self.wfile.write(b"221 Bye\r\n")
                break
            else:
                self.wfile.write(b"250 OK\r\n")


def _start_http_server() -> tuple[HTTPServer, threading.Thread]:
    server = HTTPServer(("127.0.0.1", 0), _SlackCaptureHandler)
    _SlackCaptureHandler.requests = []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _start_smtp_server() -> tuple[socketserver.TCPServer, threading.Thread]:
    class _SMTPServer(socketserver.TCPServer):
        allow_reuse_address = True

    _SMTPCaptureHandler.messages = []
    server = _SMTPServer(("127.0.0.1", 0), _SMTPCaptureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _write_known_hosts(
    tmp_path: Path, host: str, port: int, host_key: paramiko.PKey
) -> None:
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir(parents=True, exist_ok=True)
    known_hosts = ssh_dir / "known_hosts"
    host_keys = paramiko.HostKeys()
    host_keys.add(f"[{host}]:{port}", host_key.get_name(), host_key)
    host_keys.save(str(known_hosts))


def test_ssh_executor_can_run_against_local_paramiko_server(
    tmp_path: Path,
    monkeypatch,
) -> None:
    server = _SSHTestServer(
        {
            "systemctl is-active nginx": _SSHResponse(exit_status=0, stdout="active\n"),
        }
    )
    server.start()
    _write_known_hosts(tmp_path, "127.0.0.1", server.port, server.host_key)
    monkeypatch.setenv("HOME", str(tmp_path))

    executor = SSHExecutor(
        target=SSHTarget(host="127.0.0.1", user="ubuntu", port=server.port),
        auth=SSHAuthConfig(password=SSH_TEST_PASSWORD),  # noqa: S106
        connect_timeout_seconds=5,
        strict_host_key=True,
    )

    result = executor.execute("systemctl is-active nginx", timeout_seconds=5)
    server.close()

    assert result.success
    assert result.output == "active"
    assert result.exit_status == 0


def test_slack_notifier_can_post_to_local_http_endpoint() -> None:
    server, thread = _start_http_server()
    context = sample_context()
    notifier = SlackNotifier(
        webhook_url=f"http://127.0.0.1:{server.server_port}/services/test",
    )

    result = notifier.send(context)

    server.shutdown()
    server.server_close()
    thread.join(timeout=5)

    assert result.success
    assert len(_SlackCaptureHandler.requests) == 1
    assert _SlackCaptureHandler.requests[0]["body"]["channel"] == "#ops-alerts"
    assert "linux_service_down" in _SlackCaptureHandler.requests[0]["body"]["text"]


def test_email_notifier_can_send_to_local_smtp_server() -> None:
    server, thread = _start_smtp_server()
    context = sample_context()
    notifier = EmailNotifier(
        smtp_host="127.0.0.1",
        smtp_port=server.server_address[1],
        smtp_username=None,
        smtp_password=None,
        from_address="failwarden@example.local",
        use_tls=False,
    )

    result = notifier.send(context)

    server.shutdown()
    server.server_close()
    thread.join(timeout=5)

    assert result.success
    assert len(_SMTPCaptureHandler.messages) == 1
    assert "Subject: Escalation: linux_service_down" in _SMTPCaptureHandler.messages[0]
    assert "Manual intervention required" in _SMTPCaptureHandler.messages[0]
