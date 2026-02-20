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
    report = run_performance_benchmark_suite(temp_dir=tmp_path / "performance")
    assert report.total >= PERFORMANCE_MIN_CASES
    assert report.pass_rate >= PERFORMANCE_MIN_PASS_RATE, (
        f"suite={report.suite_id} pass_rate={report.pass_rate:.3f} "
        f"failed={report.failed_case_ids}"
    )
