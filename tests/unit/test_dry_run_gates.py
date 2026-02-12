"""Layer 5: Dry-run gates mode — run gates without executing steps."""

from pathlib import Path

from lily.kernel import create_run, run_graph
from lily.kernel.artifact_store import ArtifactStore
from lily.kernel.graph_models import ExecutorSpec, GraphSpec, StepSpec
from lily.kernel.gate_models import GateRunnerSpec, GateSpec
from lily.kernel.run_state import load_run_state


def test_gates_execute(tmp_path: Path):
    """With dry_run_gates=True, gates run and produce GateResult artifacts."""
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
                gates=[
                    GateSpec(
                        gate_id="g1",
                        name="g1",
                        inputs=[],
                        runner=GateRunnerSpec(argv=["python", "-c", "print(0)"]),
                        required=True,
                    ),
                ],
            ),
        ],
    )
    run_graph(run_root, graph, dry_run_gates=True)
    store = ArtifactStore(run_root, run_id)
    listed = store.list(artifact_type="gate_result.v1")
    assert len(listed) >= 1


def test_step_status_unchanged(tmp_path: Path):
    """Dry-run does not change step status (all remain pending for new run)."""
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
                gates=[
                    GateSpec(
                        gate_id="g1",
                        name="g1",
                        inputs=[],
                        runner=GateRunnerSpec(argv=["python", "-c", "exit(0)"]),
                        required=True,
                    ),
                ],
            ),
        ],
    )
    state = run_graph(run_root, graph, dry_run_gates=True)
    assert state.step_records["a"].status == "pending"


def test_gate_results_stored(tmp_path: Path):
    """GateResult envelopes are stored in the artifact store."""
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
                gates=[
                    GateSpec(
                        gate_id="g_dry",
                        name="g_dry",
                        inputs=[],
                        runner=GateRunnerSpec(argv=["python", "-c", "print(2)"]),
                        required=True,
                    ),
                ],
            ),
        ],
    )
    run_graph(run_root, graph, dry_run_gates=True)
    store = ArtifactStore(run_root, run_id)
    refs = [r for r in store.list() if r.artifact_type == "gate_result.v1"]
    assert any(r.artifact_name and "g_dry" in r.artifact_name for r in refs)


def test_no_step_execution_logs_created(tmp_path: Path):
    """Dry-run does not create step execution logs (logs/steps/...)."""
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
                gates=[
                    GateSpec(
                        gate_id="g1",
                        name="g1",
                        inputs=[],
                        runner=GateRunnerSpec(argv=["python", "-c", "exit(0)"]),
                        required=True,
                    ),
                ],
            ),
        ],
    )
    run_graph(run_root, graph, dry_run_gates=True)
    state = load_run_state(run_root)
    rec = state.step_records["a"]
    # Step was never run, so no step execution log_paths
    assert rec.log_paths == {}
    assert rec.produced_artifact_ids == []
