"""Performance gate tests for memory migration risk closure."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.evals._memory_migration_harness import (
    PERFORMANCE_MIN_CASES,
    PERFORMANCE_MIN_PASS_RATE,
    run_performance_benchmark_suite,
)


@pytest.mark.unit
def test_memory_performance_thresholds(tmp_path: Path) -> None:
    """Performance benchmark suite should pass configured thresholds."""
    # Arrange - temp dir for performance run
    # Act - run performance benchmark suite
    report = run_performance_benchmark_suite(temp_dir=tmp_path / "performance")
    # Assert - case count and pass rate meet thresholds
    assert report.total >= PERFORMANCE_MIN_CASES
    assert report.pass_rate >= PERFORMANCE_MIN_PASS_RATE, (
        f"suite={report.suite_id} pass_rate={report.pass_rate:.3f} "
        f"failed={report.failed_case_ids}"
    )


@pytest.mark.unit
def test_memory_performance_report_contains_expected_case_ids(tmp_path: Path) -> None:
    """Performance suite should expose stable case id set for diagnostics."""
    # Arrange - temp dir for performance run
    # Act - run performance benchmark suite
    report = run_performance_benchmark_suite(temp_dir=tmp_path / "performance-cases")

    # Assert - stable suite identity and expected case ids
    assert report.suite_id == "performance_benchmarks"
    expected_case_ids = {
        "performance_command_p95_budget",
        "performance_command_throughput_floor",
        "performance_retrieval_p95_budget",
        "performance_consolidation_runtime_budget",
        "performance_prompt_tokens_compacted",
    }
    actual_case_ids = {result.case_id for result in report.results}
    assert actual_case_ids == expected_case_ids


@pytest.mark.unit
def test_memory_performance_threshold_constants_are_valid() -> None:
    """Configured performance thresholds should be sane and non-zero."""
    # Arrange - constants imported from eval harness
    # Act - evaluate threshold invariants
    # Assert - threshold configuration is valid for gating semantics
    assert PERFORMANCE_MIN_CASES >= 1
    assert 0.0 < PERFORMANCE_MIN_PASS_RATE <= 1.0
