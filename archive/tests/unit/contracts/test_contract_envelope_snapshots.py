"""Regression snapshot tests for deterministic contract envelopes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lily.runtime.contract_snapshots import (
    build_contract_snapshot_payload,
    write_contract_snapshot,
)


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


@pytest.mark.unit
def test_contract_snapshot_payload_has_expected_envelope_keys() -> None:
    """Snapshot payload should expose the deterministic envelope key set."""
    # Arrange - no external fixture setup required
    # Act - build contract snapshot payload
    payload = build_contract_snapshot_payload()

    # Assert - stable metadata and envelope keys
    assert payload["version"] == 1
    envelopes = payload["envelopes"]
    assert isinstance(envelopes, dict)
    assert set(envelopes) == {
        "tool_ok",
        "tool_input_invalid",
        "llm_backend_unavailable",
    }


@pytest.mark.unit
def test_write_contract_snapshot_creates_parent_and_roundtrips_payload(
    tmp_path: Path,
) -> None:
    """Snapshot writer should create parent dirs and persist exact payload."""
    # Arrange - nested output path
    output = tmp_path / "contracts" / "out" / "snapshot.json"
    expected = build_contract_snapshot_payload()

    # Act - write snapshot
    write_contract_snapshot(output)

    # Assert - file created and payload roundtrips exactly
    assert output.exists()
    persisted = json.loads(output.read_text(encoding="utf-8"))
    assert persisted == expected
