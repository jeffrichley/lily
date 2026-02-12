"""Layer 5: Artifact replacement — envelope and downstream reset."""

from pathlib import Path

from lily.kernel import create_run, replace_artifact, run_graph
from lily.kernel.artifact_store import ArtifactStore
from lily.kernel.graph_models import ExecutorSpec, GraphSpec, StepSpec
from lily.kernel.run_state import RunStatus, StepStatus

from tests.unit.helpers import build_run_state_with_step_overrides


def _graph_one_step() -> GraphSpec:
    return GraphSpec(
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


def test_replacement_envelope_stored(tmp_path: Path):
    """replace_artifact stores an artifact_replacement.v1 envelope."""
    run_id, run_root = create_run(tmp_path)
    graph = _graph_one_step()
    state = build_run_state_with_step_overrides(
        run_id,
        run_root,
        graph,
        step_overrides={
            "a": {
                "status": StepStatus.SUCCEEDED,
                "produced_artifact_ids": ["old_artifact_1"],
            },
        },
    )
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
    assert len(refs) >= 1, (
        "replace_artifact should store at least one artifact_replacement.v1 envelope"
    )
    envelope = store.get_envelope(refs[0])
    assert envelope.payload["original_artifact_id"] == "old_artifact_1"
    assert envelope.payload["replacement_artifact_id"] == "new_artifact_1"
    assert envelope.payload["reason"] == "test replacement"


def _graph_two_steps() -> GraphSpec:
    return GraphSpec(
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


def test_downstream_steps_reset(tmp_path: Path):
    """replace_artifact triggers rerun_from so producer and downstream are pending."""
    run_id, run_root = create_run(tmp_path)
    graph = _graph_two_steps()
    state = build_run_state_with_step_overrides(
        run_id,
        run_root,
        graph,
        step_overrides={
            "a": {"status": StepStatus.SUCCEEDED, "produced_artifact_ids": ["old_x"]},
            "b": {"status": StepStatus.SUCCEEDED, "produced_artifact_ids": ["out_b"]},
        },
    )
    state = replace_artifact(
        run_root,
        state,
        graph,
        old_id="old_x",
        new_id="new_x",
        reason="inject",
    )

    assert state.step_records["a"].status == StepStatus.PENDING, (
        "replaced step a should be reset to PENDING"
    )
    assert state.step_records["b"].status == StepStatus.PENDING, (
        "downstream step b should be reset to PENDING"
    )
    assert state.step_records["a"].produced_artifact_ids == [], (
        "replaced step artifact ids should be cleared"
    )
    assert state.step_records["b"].produced_artifact_ids == [], (
        "downstream step artifact ids should be cleared"
    )


def test_provenance_chain_intact(tmp_path: Path):
    """After replacement, run_graph can complete and provenance is preserved."""
    run_id, run_root = create_run(tmp_path)
    graph = _graph_two_steps()
    state = build_run_state_with_step_overrides(
        run_id,
        run_root,
        graph,
        step_overrides={
            "a": {"status": StepStatus.SUCCEEDED, "produced_artifact_ids": ["old_art"]},
            "b": {"status": StepStatus.SUCCEEDED},
        },
    )
    state = replace_artifact(
        run_root,
        state,
        graph,
        old_id="old_art",
        new_id="new_art",
        reason="provenance test",
    )

    state2 = run_graph(run_root, graph)
    assert state2.status == RunStatus.SUCCEEDED, (
        "run should complete after replacement and rerun"
    )
    assert state2.step_records["a"].status == StepStatus.SUCCEEDED, (
        "step a should succeed on rerun"
    )
    assert state2.step_records["b"].status == StepStatus.SUCCEEDED, (
        "step b should succeed on rerun"
    )
