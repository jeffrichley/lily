"""Layer 5: Artifact replacement — envelope and downstream reset."""

from pathlib import Path

from lily.kernel import create_run, replace_artifact, run_graph
from lily.kernel.artifact_store import ArtifactStore
from lily.kernel.graph_models import ExecutorSpec, GraphSpec, StepSpec
from lily.kernel.run_state import load_run_state


def test_replacement_envelope_stored(tmp_path: Path):
    """replace_artifact stores an artifact_replacement.v1 envelope."""
    run_id, run_root = create_run(tmp_path)
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            StepSpec(
                step_id="a",
                name="a",
                depends_on=[],
                executor=ExecutorSpec(
                    kind="local_command", argv=["python", "-c", "print(1)"]
                ),
            ),
        ],
    )
    state = run_graph(run_root, graph)
    state = load_run_state(run_root)
    assert state is not None
    # Manually set produced_artifact_ids so we have something to replace
    state.step_records["a"].produced_artifact_ids = ["old_artifact_1"]
    from lily.kernel.run_state import save_run_state_atomic

    save_run_state_atomic(run_root, state)

    state = replace_artifact(
        run_root,
        state,
        graph,
        old_id="old_artifact_1",
        new_id="new_artifact_1",
        reason="test replacement",
    )

    store = ArtifactStore(run_root, run_id)
    refs = store.list(artifact_type="artifact_replacement.v1")
    assert len(refs) >= 1
    envelope = store.get_envelope(refs[0])
    assert envelope.payload["original_artifact_id"] == "old_artifact_1"
    assert envelope.payload["replacement_artifact_id"] == "new_artifact_1"
    assert envelope.payload["reason"] == "test replacement"


def test_downstream_steps_reset(tmp_path: Path):
    """replace_artifact triggers rerun_from so producer and downstream are pending."""
    run_id, run_root = create_run(tmp_path)
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            StepSpec(
                step_id="a",
                name="a",
                depends_on=[],
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
    state = run_graph(run_root, graph)
    state = load_run_state(run_root)
    assert state is not None
    state.step_records["a"].produced_artifact_ids = ["old_x"]
    state.step_records["a"].status = "succeeded"
    state.step_records["b"].produced_artifact_ids = ["out_b"]
    state.step_records["b"].status = "succeeded"
    from lily.kernel.run_state import save_run_state_atomic

    save_run_state_atomic(run_root, state)

    state = replace_artifact(
        run_root,
        state,
        graph,
        old_id="old_x",
        new_id="new_x",
        reason="inject",
    )

    assert state.step_records["a"].status == "pending"
    assert state.step_records["b"].status == "pending"
    assert state.step_records["a"].produced_artifact_ids == []
    assert state.step_records["b"].produced_artifact_ids == []


def test_provenance_chain_intact(tmp_path: Path):
    """After replacement, run_graph can complete and provenance is preserved."""
    run_id, run_root = create_run(tmp_path)
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            StepSpec(
                step_id="a",
                name="a",
                depends_on=[],
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
    state = run_graph(run_root, graph)
    state = load_run_state(run_root)
    assert state is not None
    state.step_records["a"].produced_artifact_ids = ["old_art"]
    state.step_records["a"].status = "succeeded"
    state.step_records["b"].status = "succeeded"
    from lily.kernel.run_state import save_run_state_atomic

    save_run_state_atomic(run_root, state)

    state = replace_artifact(
        run_root,
        state,
        graph,
        old_id="old_art",
        new_id="new_art",
        reason="provenance test",
    )

    state2 = run_graph(run_root, graph)
    assert state2.status == "succeeded"
    assert state2.step_records["a"].status == "succeeded"
    assert state2.step_records["b"].status == "succeeded"
