"""Tests for shipped Step 11 runbooks."""

from __future__ import annotations

from pathlib import Path

from failwarden_orchestrator.compiler import RunbookCompiler

ROOT = Path(__file__).resolve().parents[1]
RUNBOOKS_DIR = ROOT / "runbooks"

SHIPPED = [
    "linux_service_down.yaml",
    "windows_service_down.yaml",
    "disk_full.yaml",
    "ntp_drift.yaml",
    "http_endpoint_down.yaml",
]


def test_all_shipped_runbooks_exist() -> None:
    missing = [name for name in SHIPPED if not (RUNBOOKS_DIR / name).exists()]
    assert not missing, f"Missing shipped runbooks: {missing}"


def test_all_shipped_runbooks_compile() -> None:
    compiler = RunbookCompiler()
    for name in SHIPPED:
        compiled = compiler.compile_file(RUNBOOKS_DIR / name)
        assert compiled.name
        assert compiled.entry_step in compiled.steps_by_id
