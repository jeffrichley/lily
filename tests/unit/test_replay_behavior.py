"""Layer 5: Replay behavior — rerun from step, preserve logs and artifacts."""

from pathlib import Path

from lily.kernel import create_run, run_graph
from lily.kernel.graph_models import ExecutorSpec, GraphSpec, StepSpec
from lily.kernel.run_state import load_run_state, save_run_state_atomic
from lily.kernel.rerun import rerun_from


def _make_step(step_id: str, depends_on: list[str] | None = None) -> StepSpec:
    return StepSpec(
        step_id=step_id,
        name=step_id,
        depends_on=depends_on or [],
        executor=ExecutorSpec(kind="local_command", argv=["python", "-c", "print(1)"]),
    )


def test_downstream_reset_correct(tmp_path: Path):
    """After rerun_from(b), b and c are pending; a and d unchanged."""
    run_id, run_root = create_run(tmp_path)
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            _make_step("a"),
            _make_step("b", depends_on=["a"]),
            _make_step("c", depends_on=["b"]),
            _make_step("d", depends_on=["a"]),
        ],
    )
    state = run_graph(run_root, graph)
    assert state.status == "succeeded"

    state = load_run_state(run_root)
    assert state is not None
    state = rerun_from(state, graph, "b")
    save_run_state_atomic(run_root, state)

    state2 = load_run_state(run_root)
    assert state2 is not None
    assert state2.step_records["a"].status == "succeeded"
    assert state2.step_records["b"].status == "pending"
    assert state2.step_records["c"].status == "pending"
    assert state2.step_records["d"].status == "succeeded"


def test_upstream_unchanged(tmp_path: Path):
    """Rerun from step b leaves step a succeeded and its records intact."""
    run_id, run_root = create_run(tmp_path)
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            _make_step("a"),
            _make_step("b", depends_on=["a"]),
        ],
    )
    state = run_graph(run_root, graph)
    assert state.status == "succeeded"
    a_rec = state.step_records["a"]
    state = load_run_state(run_root)
    assert state is not None
    state = rerun_from(state, graph, "b")
    save_run_state_atomic(run_root, state)
    assert state.step_records["a"].status == "succeeded"
    assert (
        state.step_records["a"].produced_artifact_ids == a_rec.produced_artifact_ids
        or []
    )


def test_artifacts_remain_on_disk(tmp_path: Path):
    """Replay does not delete artifacts; run dir still has artifacts and index."""
    run_id, run_root = create_run(tmp_path)
    graph = GraphSpec(
        graph_id="g1",
        steps=[_make_step("a")],
    )
    state = run_graph(run_root, graph)
    assert state.status == "succeeded"
    artifacts_dir = run_root / "artifacts"
    before = list(artifacts_dir.iterdir()) if artifacts_dir.exists() else []

    state = load_run_state(run_root)
    assert state is not None
    state = rerun_from(state, graph, "a")
    save_run_state_atomic(run_root, state)

    after = list(artifacts_dir.iterdir()) if artifacts_dir.exists() else []
    assert len(after) >= len(before)


def test_run_completes_successfully_after_replay(tmp_path: Path):
    """After rerun_from and save, run_graph can be called again and completes."""
    run_id, run_root = create_run(tmp_path)
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            _make_step("a"),
            _make_step("b", depends_on=["a"]),
        ],
    )
    state = run_graph(run_root, graph)
    assert state.status == "succeeded"

    state = load_run_state(run_root)
    assert state is not None
    state = rerun_from(state, graph, "b")
    save_run_state_atomic(run_root, state)

    state2 = run_graph(run_root, graph)
    assert state2.status == "succeeded"
    assert state2.step_records["a"].status == "succeeded"
    assert state2.step_records["b"].status == "succeeded"


def test_log_paths_preserved_for_reset_steps(tmp_path: Path):
    """rerun_from preserves log_paths on reset steps (Layer 5)."""

    run_id, run_root = create_run(tmp_path)
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            _make_step("a"),
            _make_step("b", depends_on=["a"]),
        ],
    )
    state = run_graph(run_root, graph)
    assert state.status == "succeeded"
    b_logs = state.step_records["b"].log_paths

    state = load_run_state(run_root)
    assert state is not None
    state = rerun_from(state, graph, "b")
    # log_paths preserved (not cleared)
    assert state.step_records["b"].log_paths == b_logs
