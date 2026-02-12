"""Layer 2: Runner resume semantics."""

from pathlib import Path

from lily.kernel.graph_models import ExecutorSpec, GraphSpec, StepSpec
from lily.kernel.run_state import (
    RunState,
    RunStatus,
    StepRunRecord,
    StepStatus,
    save_run_state_atomic,
)
from lily.kernel.runner import run_graph


def test_resume_marks_running_step_interrupted_and_proceeds(tmp_path: Path) -> None:
    """Create state with a running step; runner marks it interrupted and proceeds."""
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            StepSpec(
                step_id="a",
                name="a",
                executor=ExecutorSpec(
                    kind="local_command", argv=["python", "-c", "print(1)"]
                ),
            ),
            StepSpec(
                step_id="b",
                name="b",
                depends_on=["a"],
                executor=ExecutorSpec(
                    kind="local_command", argv=["python", "-c", "print(2)"]
                ),
            ),
        ],
    )
    run_root = tmp_path / "run-1"
    run_root.mkdir(parents=True)
    (run_root / "logs").mkdir()
    (run_root / "artifacts").mkdir()
    (run_root / "tmp").mkdir()

    # Pre-create state with "a" running (simulating crash mid-execution)
    state = RunState(
        run_id="run-1",
        status=RunStatus.RUNNING,
        graph_id="g1",
        current_step_id="a",
        step_records={
            "a": StepRunRecord(step_id="a", status=StepStatus.RUNNING, attempts=0),
            "b": StepRunRecord(step_id="b", status=StepStatus.PENDING, attempts=0),
        },
        updated_at="2024-01-01T00:00:00Z",
    )
    save_run_state_atomic(run_root, state)

    # Run: mark "a" failed (interrupted), no eligible steps, run FAILED
    result = run_graph(run_root, graph)

    assert result.step_records["a"].status == StepStatus.FAILED, (
        "interrupted running step should be marked failed"
    )
    assert result.step_records["a"].last_error == "interrupted", (
        "last_error should be 'interrupted'"
    )
    assert result.status == RunStatus.FAILED, (
        "a failed and b cannot run so run should be FAILED"
    )


def test_resume_with_succeeded_deps_then_running_proceeds(tmp_path: Path) -> None:
    """A succeeded, b was running; resume marks b interrupted, run completes failed."""
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            StepSpec(
                step_id="a",
                name="a",
                executor=ExecutorSpec(
                    kind="local_command", argv=["python", "-c", "print(1)"]
                ),
            ),
            StepSpec(
                step_id="b",
                name="b",
                depends_on=["a"],
                executor=ExecutorSpec(
                    kind="local_command", argv=["python", "-c", "print(2)"]
                ),
            ),
        ],
    )
    run_root = tmp_path / "run-2"
    run_root.mkdir(parents=True)
    (run_root / "logs").mkdir()
    (run_root / "artifacts").mkdir()
    (run_root / "tmp").mkdir()

    state = RunState(
        run_id="run-2",
        status=RunStatus.RUNNING,
        graph_id="g1",
        current_step_id="b",
        step_records={
            "a": StepRunRecord(step_id="a", status=StepStatus.SUCCEEDED, attempts=1),
            "b": StepRunRecord(step_id="b", status=StepStatus.RUNNING, attempts=0),
        },
        updated_at="2024-01-01T00:00:00Z",
    )
    save_run_state_atomic(run_root, state)

    result = run_graph(run_root, graph)

    assert result.step_records["a"].status == StepStatus.SUCCEEDED, (
        "upstream a should remain succeeded"
    )
    assert result.step_records["b"].status == StepStatus.FAILED, (
        "interrupted running step b should be failed"
    )
    assert result.step_records["b"].last_error == "interrupted", (
        "last_error should be 'interrupted'"
    )
    assert result.status == RunStatus.FAILED, (
        "run should be FAILED when current step was interrupted"
    )
