"""Layer 5: Step provenance (hashes, duration, executor summary, gate/policy IDs)."""

from pathlib import Path

from lily.kernel import create_run, run_graph
from lily.kernel.graph_models import ExecutorSpec, GraphSpec, StepSpec


def _make_step(step_id: str, depends_on: list[str] | None = None) -> StepSpec:
    return StepSpec(
        step_id=step_id,
        name=step_id,
        depends_on=depends_on or [],
        executor=ExecutorSpec(kind="local_command", argv=["echo", "x"]),
    )


def test_input_hashes_recorded(tmp_path: Path):
    """When a step has no upstream artifacts, input_artifact_hashes is empty."""
    run_id, run_root = create_run(tmp_path)
    graph = GraphSpec(
        graph_id="g1",
        steps=[_make_step("a")],
    )
    state = run_graph(run_root, graph)
    rec = state.step_records["a"]
    assert isinstance(rec.input_artifact_hashes, dict)
    assert rec.input_artifact_hashes == {}


def test_output_hashes_recorded(tmp_path: Path):
    """output_artifact_hashes is populated from produced_artifact_ids (empty when none produced)."""
    run_id, run_root = create_run(tmp_path)
    graph = GraphSpec(
        graph_id="g1",
        steps=[_make_step("a")],
    )
    state = run_graph(run_root, graph)
    rec = state.step_records["a"]
    assert isinstance(rec.output_artifact_hashes, dict)
    assert rec.output_artifact_hashes == {}


def test_duration_populated(tmp_path: Path):
    """duration_ms is set after step execution."""
    run_id, run_root = create_run(tmp_path)
    graph = GraphSpec(
        graph_id="g1",
        steps=[_make_step("a")],
    )
    state = run_graph(run_root, graph)
    rec = state.step_records["a"]
    assert rec.duration_ms is not None
    assert rec.duration_ms >= 0


def test_gate_ids_attached(tmp_path: Path):
    """When a step has gates, gate_result_ids (and gate_results) are populated."""
    from lily.kernel.gate_models import GateRunnerSpec, GateSpec

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
    state = run_graph(run_root, graph)
    rec = state.step_records["a"]
    assert len(rec.gate_result_ids) == 1
    assert rec.gate_result_ids == rec.gate_results


def test_policy_ids_attached(tmp_path: Path):
    """When a policy violation occurs, policy_violation_ids is populated."""
    from lily.kernel.policy_models import SafetyPolicy

    run_id, run_root = create_run(tmp_path)
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            StepSpec(
                step_id="a",
                name="a",
                depends_on=[],
                executor=ExecutorSpec(kind="nonexistent_tool", argv=[]),
            ),
        ],
    )
    policy = SafetyPolicy(allowed_tools=["local_command"])
    state = run_graph(run_root, graph, safety_policy=policy)
    rec = state.step_records["a"]
    assert len(rec.policy_violation_ids) == 1
    assert rec.status == "failed"
