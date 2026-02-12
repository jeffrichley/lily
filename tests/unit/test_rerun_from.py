"""Layer 2: rerun_from utility."""

from lily.kernel.graph_models import ExecutorSpec, GraphSpec, StepSpec
from lily.kernel.rerun import rerun_from
from lily.kernel.run_state import RunState, RunStatus, StepRunRecord, StepStatus


def _make_step(step_id: str, depends_on: list[str] | None = None) -> StepSpec:
    return StepSpec(
        step_id=step_id,
        name=step_id,
        depends_on=depends_on or [],
        executor=ExecutorSpec(kind="local_command", argv=["echo", "x"]),
    )


def test_downstream_detection_correct() -> None:
    """Downstream of a step includes itself and all steps that depend on it."""
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            _make_step("a"),
            _make_step("b", depends_on=["a"]),
            _make_step("c", depends_on=["b"]),
            _make_step("d", depends_on=["a"]),
        ],
    )
    state = RunState(
        run_id="r1",
        status=RunStatus.SUCCEEDED,
        graph_id="g1",
        step_records={
            "a": StepRunRecord(
                step_id="a", status=StepStatus.SUCCEEDED, produced_artifact_ids=["x"]
            ),
            "b": StepRunRecord(
                step_id="b", status=StepStatus.SUCCEEDED, produced_artifact_ids=["y"]
            ),
            "c": StepRunRecord(
                step_id="c", status=StepStatus.SUCCEEDED, produced_artifact_ids=["z"]
            ),
            "d": StepRunRecord(
                step_id="d", status=StepStatus.SUCCEEDED, produced_artifact_ids=["w"]
            ),
        },
    )

    result = rerun_from(state, graph, "b")

    assert result.step_records["a"].status == StepStatus.SUCCEEDED, (
        "upstream a unchanged"
    )
    assert result.step_records["a"].produced_artifact_ids == ["x"], (
        "upstream a artifacts unchanged"
    )
    assert result.step_records["b"].status == StepStatus.PENDING, (
        "target b reset to PENDING"
    )
    assert result.step_records["b"].produced_artifact_ids == [], "b artifacts cleared"
    assert result.step_records["c"].status == StepStatus.PENDING, (
        "downstream c reset to PENDING"
    )
    assert result.step_records["c"].produced_artifact_ids == [], "c artifacts cleared"
    assert result.step_records["d"].status == StepStatus.SUCCEEDED, (
        "sibling d unchanged"
    )
    assert result.step_records["d"].produced_artifact_ids == ["w"], (
        "d artifacts unchanged"
    )


def test_statuses_reset_as_expected() -> None:
    """Reset steps have status pending, attempts 0, cleared timestamps and errors."""
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            _make_step("a"),
            _make_step("b", depends_on=["a"]),
        ],
    )
    state = RunState(
        run_id="r1",
        status=RunStatus.SUCCEEDED,
        graph_id="g1",
        step_records={
            "a": StepRunRecord(
                step_id="a",
                status=StepStatus.SUCCEEDED,
                attempts=1,
                started_at="2024-01-01T00:00:00Z",
                finished_at="2024-01-01T00:01:00Z",
                last_error=None,
                produced_artifact_ids=["x"],
                log_paths={"stdout": "logs/steps/a/1/stdout.txt"},
            ),
            "b": StepRunRecord(
                step_id="b",
                status=StepStatus.FAILED,
                attempts=2,
                started_at="2024-01-01T00:01:00Z",
                finished_at="2024-01-01T00:02:00Z",
                last_error="oops",
                produced_artifact_ids=[],
                log_paths={"stderr": "logs/steps/b/2/stderr.txt"},
            ),
        },
    )

    result = rerun_from(state, graph, "a")

    assert result.step_records["a"].status == StepStatus.PENDING, (
        "rerun_from(a) resets a to PENDING"
    )
    assert result.step_records["a"].attempts == 0, "attempts should be reset"
    assert result.step_records["a"].started_at is None, "started_at cleared"
    assert result.step_records["a"].finished_at is None, "finished_at cleared"
    assert result.step_records["a"].last_error is None, "last_error cleared"
    assert result.step_records["a"].produced_artifact_ids == [], "artifact ids cleared"
    # Layer 5: log_paths preserved for audit
    assert result.step_records["a"].log_paths == {
        "stdout": "logs/steps/a/1/stdout.txt"
    }, "log_paths preserved"
    assert result.step_records["b"].status == StepStatus.PENDING, (
        "downstream b also reset (depends on a)"
    )
    assert result.step_records["b"].attempts == 0, "b attempts reset"
