"""CLI helper tests."""

from __future__ import annotations

import pytest

from failwarden_orchestrator.cli import parse_vars


def test_parse_vars_success() -> None:
    parsed = parse_vars(["a=1", "service=nginx"])
    assert parsed == {"a": "1", "service": "nginx"}


def test_parse_vars_rejects_invalid_pair() -> None:
    with pytest.raises(ValueError):
        parse_vars(["badpair"])
