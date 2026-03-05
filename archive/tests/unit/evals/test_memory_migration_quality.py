"""Phase 7 memory-migration quality gate tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.evals._memory_migration_harness import (
    COMPACTION_MIN_CASES,
    COMPACTION_MIN_PASS_RATE,
    PARITY_MIN_CASES,
    PARITY_MIN_PASS_RATE,
    POLICY_MIN_CASES,
    POLICY_MIN_PASS_RATE,
    RESTART_MIN_CASES,
    RESTART_MIN_PASS_RATE,
    RETRIEVAL_MIN_CASES,
    RETRIEVAL_MIN_PASS_RATE,
    run_compaction_effectiveness_suite,
    run_policy_redline_suite,
    run_restart_continuity_suite,
    run_retrieval_relevance_suite,
    run_store_parity_suite,
)


def _assert_thresholds(*, report: object, min_cases: int, min_pass_rate: float) -> None:
    """Assert one suite report satisfies thresholds."""
    assert hasattr(report, "total")
    assert hasattr(report, "pass_rate")
    assert hasattr(report, "failed_case_ids")
    assert report.total >= min_cases
    assert report.pass_rate >= min_pass_rate, (
        f"suite={report.suite_id} pass_rate={report.pass_rate:.3f} "
        f"failed={report.failed_case_ids}"
    )


@pytest.mark.unit
def test_memory_phase7_restart_continuity_thresholds(tmp_path: Path) -> None:
    """Restart continuity suite should pass configured thresholds."""
    # Arrange - temp dir for restart suite
    # Act - run restart continuity suite
    report = run_restart_continuity_suite(temp_dir=tmp_path / "restart")
    # Assert - thresholds met
    _assert_thresholds(
        report=report,
        min_cases=RESTART_MIN_CASES,
        min_pass_rate=RESTART_MIN_PASS_RATE,
    )


@pytest.mark.unit
def test_memory_phase7_store_parity_thresholds(tmp_path: Path) -> None:
    """Store parity suite should pass configured thresholds."""
    # Arrange - temp dir for parity suite
    # Act - run store parity suite
    report = run_store_parity_suite(temp_dir=tmp_path / "parity")
    # Assert - thresholds met
    _assert_thresholds(
        report=report,
        min_cases=PARITY_MIN_CASES,
        min_pass_rate=PARITY_MIN_PASS_RATE,
    )


@pytest.mark.unit
def test_memory_phase7_policy_redline_thresholds(tmp_path: Path) -> None:
    """Policy redline suite should pass configured thresholds."""
    # Arrange - temp dir for policy suite
    # Act - run policy redline suite
    report = run_policy_redline_suite(temp_dir=tmp_path / "policy")
    # Assert - thresholds met
    _assert_thresholds(
        report=report,
        min_cases=POLICY_MIN_CASES,
        min_pass_rate=POLICY_MIN_PASS_RATE,
    )


@pytest.mark.unit
def test_memory_phase7_retrieval_relevance_thresholds(tmp_path: Path) -> None:
    """Retrieval relevance suite should pass configured thresholds."""
    # Arrange - temp dir for retrieval suite
    # Act - run retrieval relevance suite
    report = run_retrieval_relevance_suite(temp_dir=tmp_path / "retrieval")
    # Assert - thresholds met
    _assert_thresholds(
        report=report,
        min_cases=RETRIEVAL_MIN_CASES,
        min_pass_rate=RETRIEVAL_MIN_PASS_RATE,
    )


@pytest.mark.unit
def test_memory_phase7_compaction_effectiveness_thresholds(tmp_path: Path) -> None:
    """Compaction suite should pass configured thresholds."""
    # Arrange - temp dir for compaction suite
    # Act - run compaction effectiveness suite
    report = run_compaction_effectiveness_suite(temp_dir=tmp_path / "compaction")
    # Assert - thresholds met
    _assert_thresholds(
        report=report,
        min_cases=COMPACTION_MIN_CASES,
        min_pass_rate=COMPACTION_MIN_PASS_RATE,
    )
