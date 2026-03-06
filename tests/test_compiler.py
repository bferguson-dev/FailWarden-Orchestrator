"""Compile-layer tests for Step 3."""

from __future__ import annotations

from pathlib import Path

import pytest

from failwarden_orchestrator.compiler import RunbookCompiler
from failwarden_orchestrator.validation import RunbookValidationError

ROOT = Path(__file__).resolve().parents[1]
VALID_DIR = ROOT / "runbooks" / "examples" / "valid"
INVALID_DIR = ROOT / "runbooks" / "examples" / "invalid"


def issue_codes(error: RunbookValidationError) -> set[str]:
    """Return a set of error codes for easy assertions."""
    return {issue.code for issue in error.issues}


def test_compile_valid_linux_service_down() -> None:
    compiler = RunbookCompiler()
    compiled = compiler.compile_file(VALID_DIR / "linux_service_down.yaml")

    assert compiled.name == "linux_service_down"
    assert compiled.entry_step == "check_service"
    assert "done" in compiled.steps_by_id
    assert compiled.steps_by_id["done"].type == "end"


def test_compile_rejects_missing_entry_step() -> None:
    compiler = RunbookCompiler()
    with pytest.raises(RunbookValidationError) as exc_info:
        compiler.compile_file(INVALID_DIR / "missing_entry_step.yaml")
    assert "RBK101" in issue_codes(exc_info.value)


def test_compile_rejects_duplicate_step_id() -> None:
    compiler = RunbookCompiler()
    with pytest.raises(RunbookValidationError) as exc_info:
        compiler.compile_file(INVALID_DIR / "duplicate_step_id.yaml")
    assert "RBK104" in issue_codes(exc_info.value)


def test_compile_rejects_missing_branch_target() -> None:
    compiler = RunbookCompiler()
    with pytest.raises(RunbookValidationError) as exc_info:
        compiler.compile_file(INVALID_DIR / "missing_branch_target.yaml")
    assert "RBK202" in issue_codes(exc_info.value)


def test_compile_rejects_unsupported_step_type() -> None:
    compiler = RunbookCompiler()
    with pytest.raises(RunbookValidationError) as exc_info:
        compiler.compile_file(INVALID_DIR / "unsupported_step_type.yaml")
    assert "RBK105" in issue_codes(exc_info.value)


def test_compile_rejects_escalate_with_branch() -> None:
    compiler = RunbookCompiler()
    with pytest.raises(RunbookValidationError) as exc_info:
        compiler.compile_file(INVALID_DIR / "escalate_has_branch.yaml")
    assert "RBK102" in issue_codes(exc_info.value)


def test_compile_rejects_end_with_notify() -> None:
    compiler = RunbookCompiler()
    with pytest.raises(RunbookValidationError) as exc_info:
        compiler.compile_file(INVALID_DIR / "end_has_notify.yaml")
    assert "RBK102" in issue_codes(exc_info.value)


def test_compile_rejects_cycle() -> None:
    compiler = RunbookCompiler()
    with pytest.raises(RunbookValidationError) as exc_info:
        compiler.compile_file(INVALID_DIR / "cycle_detected.yaml")
    assert "RBK204" in issue_codes(exc_info.value)


def test_compile_rejects_unreachable_step() -> None:
    compiler = RunbookCompiler()
    with pytest.raises(RunbookValidationError) as exc_info:
        compiler.compile_file(INVALID_DIR / "unreachable_step.yaml")
    assert "RBK203" in issue_codes(exc_info.value)


def test_compile_rejects_undefined_template_variable() -> None:
    compiler = RunbookCompiler()
    with pytest.raises(RunbookValidationError) as exc_info:
        compiler.compile_file(INVALID_DIR / "undefined_template_var.yaml")
    assert "RBK401" in issue_codes(exc_info.value)
