"""Phase 7 quality gate tests."""

from __future__ import annotations

from pathlib import Path

from tests.unit.evals._phase7_harness import (
    CONSISTENCY_MIN_CASES,
    CONSISTENCY_MIN_PASS_RATE,
    FUN_MIN_CASES,
    FUN_MIN_PASS_RATE,
    SAFETY_MIN_CASES,
    SAFETY_MIN_PASS_RATE,
    TASK_MIN_CASES,
    TASK_MIN_PASS_RATE,
    run_fun_delight_suite,
    run_personality_consistency_suite,
    run_safety_redline_suite,
    run_task_effectiveness_suite,
)


def _assert_thresholds(*, report: object, min_cases: int, min_pass_rate: float) -> None:
    """Assert one suite report satisfies thresholds.

    Args:
        report: Suite report object.
        min_cases: Required minimum case count.
        min_pass_rate: Required minimum pass rate.
    """
    assert hasattr(report, "total")
    assert hasattr(report, "pass_rate")
    assert hasattr(report, "failed_case_ids")
    assert report.total >= min_cases
    assert report.pass_rate >= min_pass_rate, (
        f"suite={report.suite_id} pass_rate={report.pass_rate:.3f} "
        f"failed={report.failed_case_ids}"
    )


def test_phase7_personality_consistency_thresholds(tmp_path: Path) -> None:
    """Personality consistency suite should pass configured thresholds."""
    report = run_personality_consistency_suite(temp_dir=tmp_path / "consistency")
    _assert_thresholds(
        report=report,
        min_cases=CONSISTENCY_MIN_CASES,
        min_pass_rate=CONSISTENCY_MIN_PASS_RATE,
    )


def test_phase7_task_effectiveness_thresholds(tmp_path: Path) -> None:
    """Task effectiveness suite should pass configured thresholds."""
    report = run_task_effectiveness_suite(temp_dir=tmp_path / "task")
    _assert_thresholds(
        report=report,
        min_cases=TASK_MIN_CASES,
        min_pass_rate=TASK_MIN_PASS_RATE,
    )


def test_phase7_fun_delight_thresholds(tmp_path: Path) -> None:
    """Fun/delight suite should pass configured thresholds."""
    report = run_fun_delight_suite(temp_dir=tmp_path / "fun")
    _assert_thresholds(
        report=report,
        min_cases=FUN_MIN_CASES,
        min_pass_rate=FUN_MIN_PASS_RATE,
    )


def test_phase7_safety_redline_thresholds(tmp_path: Path) -> None:
    """Safety redline suite should pass configured thresholds."""
    report = run_safety_redline_suite(temp_dir=tmp_path / "safety")
    _assert_thresholds(
        report=report,
        min_cases=SAFETY_MIN_CASES,
        min_pass_rate=SAFETY_MIN_PASS_RATE,
    )
