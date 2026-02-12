"""Layer 2: RunState persistence."""

import json
from pathlib import Path


from lily.kernel.graph_models import ExecutorSpec, GraphSpec, StepSpec
from lily.kernel.run_state import (
    RunStatus,
    StepStatus,
    create_initial_run_state,
    load_run_state,
    save_run_state_atomic,
)


def _make_graph() -> GraphSpec:
    return GraphSpec(
        graph_id="g1",
        steps=[
            StepSpec(
                step_id="a",
                name="step_a",
                executor=ExecutorSpec(kind="local_command", argv=["echo", "x"]),
            ),
        ],
    )


def test_save_then_load_round_trip(tmp_path: Path):
    """Save RunState and load it back; data matches."""
    graph = _make_graph()
    state = create_initial_run_state("run-123", graph)
    state.status = RunStatus.RUNNING
    state.step_records["a"].status = StepStatus.SUCCEEDED
    state.step_records["a"].attempts = 1

    save_run_state_atomic(tmp_path, state)
    loaded = load_run_state(tmp_path)
    assert loaded is not None
    assert loaded.run_id == "run-123"
    assert loaded.status == RunStatus.RUNNING
    assert loaded.step_records["a"].status == StepStatus.SUCCEEDED
    assert loaded.step_records["a"].attempts == 1


def test_load_nonexistent_returns_none(tmp_path: Path):
    """load_run_state returns None when file does not exist."""
    assert load_run_state(tmp_path) is None


def test_atomic_write_file_exists_and_parses(tmp_path: Path):
    """After save, file exists and is valid JSON."""
    graph = _make_graph()
    state = create_initial_run_state("r1", graph)
    save_run_state_atomic(tmp_path, state)

    path = tmp_path / "run_state.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["run_id"] == "r1"
    assert "step_records" in data
    assert "a" in data["step_records"]


def test_create_initial_run_state():
    """create_initial_run_state creates pending records for all steps."""
    graph = _make_graph()
    state = create_initial_run_state("r1", graph)
    assert state.run_id == "r1"
    assert state.graph_id == "g1"
    assert state.status == RunStatus.CREATED
    assert state.current_step_id is None
    assert "a" in state.step_records
    assert state.step_records["a"].status == StepStatus.PENDING
    assert state.step_records["a"].attempts == 0
