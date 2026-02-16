"""Gate B baseline eval tests."""

from __future__ import annotations

from pathlib import Path

from tests.unit.evals._baseline_harness import (
    BASELINE_MIN_CASES,
    BASELINE_MIN_PASS_RATE,
    run_baseline_evals,
)


def test_gate_b_baseline_eval_case_count_is_in_range(tmp_path: Path) -> None:
    """Baseline suite should include the documented canonical case count range."""
    report = run_baseline_evals(temp_dir=tmp_path)

    assert report.total >= BASELINE_MIN_CASES
    assert report.total <= 20


def test_gate_b_baseline_thresholds_pass(tmp_path: Path) -> None:
    """Baseline suite should satisfy Gate B pass-rate threshold."""
    report = run_baseline_evals(temp_dir=tmp_path)
    failed_case_ids = [result.case_id for result in report.results if not result.passed]

    assert report.pass_rate >= BASELINE_MIN_PASS_RATE, (
        f"pass_rate={report.pass_rate:.3f} failed_cases={failed_case_ids}"
    )
