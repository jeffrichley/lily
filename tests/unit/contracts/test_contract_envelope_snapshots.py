"""Regression snapshot tests for deterministic contract envelopes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lily.runtime.contract_snapshots import build_contract_snapshot_payload


@pytest.mark.unit
def test_contract_envelope_snapshot_matches_fixture() -> None:
    """Generated envelope snapshots should match checked-in fixture."""
    # Arrange - load expected snapshot from fixture
    expected_path = Path("tests/contracts/contract_envelopes.snapshot.json")
    expected = json.loads(expected_path.read_text(encoding="utf-8"))

    # Act - build current contract snapshot payload
    actual = build_contract_snapshot_payload()

    # Assert - payload matches fixture
    assert actual == expected
