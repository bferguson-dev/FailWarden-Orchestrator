"""Basic skeleton validation tests for Step 1."""

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
