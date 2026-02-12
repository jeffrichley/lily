"""Layer 3: Runner integration with gates."""

from pathlib import Path

from lily.kernel.gate_models import GateRunnerSpec, GateSpec
from lily.kernel.graph_models import ExecutorSpec, GraphSpec, StepSpec
from lily.kernel.run_state import RunStatus, StepStatus
from lily.kernel.runner import run_graph


def _run_root(tmp_path: Path, name: str) -> Path:
    r = tmp_path / name
    r.mkdir(parents=True)
    (r / "logs").mkdir()
    (r / "artifacts").mkdir()
    (r / "tmp").mkdir()
    return r


def test_step_succeeds_and_gates_pass_run_continues(tmp_path: Path):
    """Step succeeds and gates pass -> run continues."""
    gate = GateSpec(
        gate_id="g1",
        name="Pass gate",
        runner=GateRunnerSpec(kind="local_command", argv=["python", "-c", "pass"]),
    )
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            StepSpec(
                step_id="a",
                name="a",
                executor=ExecutorSpec(
                    kind="local_command", argv=["python", "-c", "print(1)"]
                ),
                gates=[gate],
            ),
        ],
    )
    run_root = _run_root(tmp_path, "run-1")
    state = run_graph(run_root, graph)

    assert state.status == RunStatus.SUCCEEDED, "run with passing gate should succeed"
    assert state.step_records["a"].status == StepStatus.SUCCEEDED, (
        "step a should succeed"
    )
    assert len(state.step_records["a"].gate_results) == 1, (
        "one gate should produce one gate_result"
    )


def test_required_gate_fails_run_fails(tmp_path: Path):
    """Required gate fails -> run fails."""
    gate = GateSpec(
        gate_id="fail-gate",
        name="Fail gate",
        required=True,
        runner=GateRunnerSpec(
            kind="local_command",
            argv=["python", "-c", "import sys; sys.exit(3)"],
        ),
    )
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            StepSpec(
                step_id="a",
                name="a",
                executor=ExecutorSpec(
                    kind="local_command", argv=["python", "-c", "print(1)"]
                ),
                gates=[gate],
            ),
        ],
    )
    run_root = _run_root(tmp_path, "run-2")
    state = run_graph(run_root, graph)

    assert state.status == RunStatus.FAILED, "required gate failure should fail run"
    assert state.step_records["a"].status == StepStatus.FAILED, (
        "step with failing required gate should be FAILED"
    )
    assert "gate failed" in (state.step_records["a"].last_error or ""), (
        "last_error should mention gate failed"
    )
    assert len(state.step_records["a"].gate_results) == 1, (
        "gate result should still be recorded"
    )


def test_non_required_gate_fails_run_continues(tmp_path: Path):
    """Non-required gate fails -> run continues."""
    gate = GateSpec(
        gate_id="opt-fail",
        name="Optional fail",
        required=False,
        runner=GateRunnerSpec(
            kind="local_command",
            argv=["python", "-c", "import sys; sys.exit(1)"],
        ),
    )
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            StepSpec(
                step_id="a",
                name="a",
                executor=ExecutorSpec(
                    kind="local_command", argv=["python", "-c", "print(1)"]
                ),
                gates=[gate],
            ),
        ],
    )
    run_root = _run_root(tmp_path, "run-3")
    state = run_graph(run_root, graph)

    assert state.status == RunStatus.SUCCEEDED, (
        "non-required gate failure should not fail run"
    )
    assert state.step_records["a"].status == StepStatus.SUCCEEDED, (
        "step should succeed despite optional gate failure"
    )
    assert len(state.step_records["a"].gate_results) == 1, (
        "optional gate result should be recorded"
    )


def test_gate_results_recorded_in_run_state(tmp_path: Path):
    """Gate result artifact IDs are recorded in StepRunRecord."""
    g1 = GateSpec(
        gate_id="g1",
        name="One",
        runner=GateRunnerSpec(kind="local_command", argv=["python", "-c", "pass"]),
    )
    g2 = GateSpec(
        gate_id="g2",
        name="Two",
        runner=GateRunnerSpec(kind="local_command", argv=["python", "-c", "pass"]),
    )
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            StepSpec(
                step_id="a",
                name="a",
                executor=ExecutorSpec(
                    kind="local_command", argv=["python", "-c", "print(1)"]
                ),
                gates=[g1, g2],
            ),
        ],
    )
    run_root = _run_root(tmp_path, "run-4")
    state = run_graph(run_root, graph)

    assert state.status == RunStatus.SUCCEEDED, "run with two gates should succeed"
    rec = state.step_records["a"]
    assert len(rec.gate_results) == 2, "two gates should produce two gate_result ids"
    assert all(len(aid) > 0 for aid in rec.gate_results), (
        "gate_result ids should be non-empty"
    )
