"""Basic skeleton validation tests for Step 1."""

import json
from pathlib import Path


def test_required_paths_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    expected = [
        root / "README.md",
        root / "ARCHITECTURE.md",
        root / "DECISIONS.md",
        root / "LAB.md",
        root / "ROADMAP.md",
        root / "CHANGELOG.md",
        root / "docs",
        root / "runbooks",
        root / "src",
        root / "tests",
        root / "pyproject.toml",
    ]
    missing = [str(path) for path in expected if not path.exists()]
    assert not missing, f"Missing required skeleton paths: {missing}"


def test_step2_schema_assets_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    expected = [
        root / "docs" / "schema.md",
        root / "docs" / "schema" / "runbook-v1.schema.json",
        root / "docs" / "validation-errors.md",
        root / "runbooks" / "examples" / "valid" / "linux_service_down.yaml",
        root / "runbooks" / "examples" / "valid" / "windows_service_down.yaml",
        root / "runbooks" / "examples" / "invalid" / "missing_entry_step.yaml",
    ]
    missing = [str(path) for path in expected if not path.exists()]
    assert not missing, f"Missing required Step 2 assets: {missing}"


def test_runbook_schema_json_is_valid() -> None:
    schema_path = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "schema"
        / "runbook-v1.schema.json"
    )
    with schema_path.open("r", encoding="utf-8") as handle:
        schema = json.load(handle)
    assert schema["title"] == "FailWarden Runbook V1"
