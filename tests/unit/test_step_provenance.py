"""Layer 5: Step provenance (hashes, duration, executor summary, gate/policy IDs)."""

from pathlib import Path

from lily.kernel import create_run, run_graph
from lily.kernel.gate_models import GateRunnerSpec, GateSpec
from lily.kernel.graph_models import ExecutorSpec, GraphSpec, StepSpec
from lily.kernel.policy_models import SafetyPolicy
from lily.kernel.run_state import StepStatus


def _make_step(step_id: str, depends_on: list[str] | None = None) -> StepSpec:
    return StepSpec(
        step_id=step_id,
        name=step_id,
        depends_on=depends_on or [],
        executor=ExecutorSpec(kind="local_command", argv=["echo", "x"]),
    )


def test_input_hashes_recorded(tmp_path: Path) -> None:
    """When a step has no upstream artifacts, input_artifact_hashes is empty."""
    _run_id, run_root = create_run(tmp_path)
    graph = GraphSpec(
        graph_id="g1",
        steps=[_make_step("a")],
    )
    state = run_graph(run_root, graph)
    rec = state.step_records["a"]
    assert isinstance(rec.input_artifact_hashes, dict), (
        "input_artifact_hashes should be a dict"
    )
    assert rec.input_artifact_hashes == {}, (
        "step with no upstream artifacts should have empty input_artifact_hashes"
    )


def test_output_hashes_recorded(tmp_path: Path) -> None:
    """output_artifact_hashes populated from produced_artifact_ids (empty when none)."""
    _run_id, run_root = create_run(tmp_path)
    graph = GraphSpec(
        graph_id="g1",
        steps=[_make_step("a")],
    )
    state = run_graph(run_root, graph)
    rec = state.step_records["a"]
    assert isinstance(rec.output_artifact_hashes, dict), (
        "output_artifact_hashes should be a dict"
    )
    assert rec.output_artifact_hashes == {}, (
        "step producing no artifacts should have empty output_artifact_hashes"
    )


def test_duration_populated(tmp_path: Path) -> None:
    """duration_ms set after step execution; non-negative elapsed time."""
    _run_id, run_root = create_run(tmp_path)
    graph = GraphSpec(
        graph_id="g1",
        steps=[_make_step("a")],
    )
    state = run_graph(run_root, graph)
    rec = state.step_records["a"]
    assert rec.duration_ms is not None, "duration_ms should be set after step runs"
    assert isinstance(rec.duration_ms, (int, float)), "duration_ms should be numeric"
    assert rec.duration_ms >= 0, "duration_ms should be non-negative"


def test_gate_ids_attached(tmp_path: Path) -> None:
    """When a step has gates, gate_result_ids (and gate_results) are populated."""
    _run_id, run_root = create_run(tmp_path)
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
    assert len(rec.gate_result_ids) == 1, (
        "step with one gate should have one gate_result_id"
    )
    assert rec.gate_result_ids == rec.gate_results, (
        "gate_result_ids and gate_results should match"
    )


def test_policy_ids_attached(tmp_path: Path) -> None:
    """Executor not in allowed_tools populates policy_violation_ids."""
    _run_id, run_root = create_run(tmp_path)
    # Use local_command in step but allow only another tool — triggers
    # tool_not_allowed violation.
    policy = SafetyPolicy(allowed_tools=["other_tool_only"])
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            StepSpec(
                step_id="a",
                name="a",
                depends_on=[],
                executor=ExecutorSpec(
                    kind="local_command",
                    argv=["python", "-c", "print(1)"],
                ),
            ),
        ],
    )
    state = run_graph(run_root, graph, safety_policy=policy)
    rec = state.step_records["a"]
    assert len(rec.policy_violation_ids) == 1, (
        "disallowed tool should produce one policy_violation envelope"
    )
    assert rec.status == StepStatus.FAILED, (
        "step with policy violation should be marked failed"
    )
