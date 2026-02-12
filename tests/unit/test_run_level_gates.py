"""Layer 3: Run-level gates (after all steps succeed)."""

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


def test_run_level_gate_passes_run_succeeded(tmp_path: Path):
    """Run-level gate passes -> run succeeded."""
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
        ],
        run_gates=[
            GateSpec(
                gate_id="run-gate",
                name="Run gate",
                runner=GateRunnerSpec(
                    kind="local_command", argv=["python", "-c", "pass"]
                ),
            ),
        ],
    )
    run_root = _run_root(tmp_path, "run-1")
    state = run_graph(run_root, graph)

    assert state.status == RunStatus.SUCCEEDED, (
        "run-level gate pass should yield run succeeded"
    )
    assert state.step_records["a"].status == StepStatus.SUCCEEDED, (
        "step a should succeed"
    )


def test_required_run_level_gate_fails_run_failed(tmp_path: Path):
    """Required run-level gate fails -> run failed."""
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
        ],
        run_gates=[
            GateSpec(
                gate_id="run-fail",
                name="Run fail",
                required=True,
                runner=GateRunnerSpec(
                    kind="local_command",
                    argv=["python", "-c", "import sys; sys.exit(2)"],
                ),
            ),
        ],
    )
    run_root = _run_root(tmp_path, "run-2")
    state = run_graph(run_root, graph)

    assert state.status == RunStatus.FAILED, (
        "required run-level gate failure should fail run"
    )
    assert state.step_records["a"].status == StepStatus.SUCCEEDED, (
        "steps should still succeed before run gate"
    )
