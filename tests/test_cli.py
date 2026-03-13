"""CLI helper tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from failwarden_orchestrator.cli import build_parser, main, parse_vars


def test_parse_vars_success() -> None:
    parsed = parse_vars(["a=1", "service=nginx"])
    assert parsed == {"a": "1", "service": "nginx"}


def test_parse_vars_rejects_invalid_pair() -> None:
    with pytest.raises(ValueError):
        parse_vars(["badpair"])


def test_build_parser_includes_json_flags() -> None:
    parser = build_parser()

    compile_args = parser.parse_args(
        ["compile", "--runbook", "runbooks/linux_service_down.yaml", "--json"]
    )
    run_args = parser.parse_args(
        [
            "run",
            "--runbook",
            "runbooks/linux_service_down.yaml",
            "--target",
            "linux-web-01",
            "--host",
            "127.0.0.1",
            "--user",
            "ubuntu",
            "--dry-run",
            "--json",
        ]
    )

    assert compile_args.json is True
    assert run_args.json is True


def test_main_returns_operator_friendly_validation_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runbook = Path("runbooks/examples/invalid/missing_entry_step.yaml")
    monkeypatch.setattr("sys.argv", ["fwo", "compile", "--runbook", str(runbook)])

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "Runbook validation failed:" in captured.err
    assert "RBK101:" in captured.err
    assert "Traceback" not in captured.err


def test_main_returns_operator_friendly_yaml_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    runbook = tmp_path / "invalid.yaml"
    runbook.write_text("name: bad:\n", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["fwo", "compile", "--runbook", str(runbook)])

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "ERROR:" in captured.err
    assert "Traceback" not in captured.err


def test_main_compile_json_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["fwo", "compile", "--runbook", "runbooks/linux_service_down.yaml", "--json"],
    )

    exit_code = main()

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["name"] == "linux_service_down"
    assert payload["entry_step"] == "check_service"
    assert payload["step_count"] == 5


def test_main_run_json_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "fwo",
            "run",
            "--runbook",
            "runbooks/linux_service_down.yaml",
            "--target",
            "linux-web-01",
            "--host",
            "127.0.0.1",
            "--user",
            "ubuntu",
            "--audit-dir",
            str(tmp_path / "audit"),
            "--db-path",
            str(tmp_path / "fwo.sqlite3"),
            "--dry-run",
            "--json",
        ],
    )

    exit_code = main()

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["final_status"] == "dry_run"
    assert payload["attempts"] == 1
    assert payload["target"] == "linux-web-01"


def test_main_reports_missing_ssh_password_env(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("FWO_TEST_SSH_PASSWORD", raising=False)
    monkeypatch.setattr(
        "sys.argv",
        [
            "fwo",
            "run",
            "--runbook",
            "runbooks/linux_service_down.yaml",
            "--target",
            "linux-web-01",
            "--host",
            "127.0.0.1",
            "--user",
            "ubuntu",
            "--ssh-password-env",
            "FWO_TEST_SSH_PASSWORD",
        ],
    )

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "SSH password env var 'FWO_TEST_SSH_PASSWORD' is not set." in captured.err
