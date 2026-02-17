"""Regression snapshot tests for deterministic contract envelopes."""

from __future__ import annotations

import json
from pathlib import Path

from lily.runtime.contract_snapshots import build_contract_snapshot_payload


def test_contract_envelope_snapshot_matches_fixture() -> None:
    """Generated envelope snapshots should match checked-in fixture."""
    expected_path = Path("tests/contracts/contract_envelopes.snapshot.json")
    expected = json.loads(expected_path.read_text(encoding="utf-8"))

    actual = build_contract_snapshot_payload()

    assert actual == expected
