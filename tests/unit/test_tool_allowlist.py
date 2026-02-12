"""Layer 4: Tool allowlist enforcement."""

from pathlib import Path

from lily.kernel import ArtifactStore, create_run, run_graph
from lily.kernel.graph_models import ExecutorSpec, GraphSpec, StepSpec
from lily.kernel.policy_models import POLICY_VIOLATION_SCHEMA_ID, SafetyPolicy
from lily.kernel.run_state import RunStatus, StepStatus


def test_allowed_tool_executes(workspace_root: Path) -> None:
    """Executor kind in allowed_tools executes successfully."""
    _run_id, run_root = create_run(workspace_root)
    policy = SafetyPolicy(allowed_tools=["local_command"])
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            StepSpec(
                step_id="a",
                name="a",
                executor=ExecutorSpec(
                    kind="local_command",
                    argv=["python", "-c", "print(1)"],
                ),
            ),
        ],
    )
    state = run_graph(run_root, graph, safety_policy=policy)
    assert state.status == RunStatus.SUCCEEDED, (
        "allowed tool should allow run to succeed"
    )
    assert state.step_records["a"].status == StepStatus.SUCCEEDED, (
        "step with allowed executor should succeed"
    )


def test_disallowed_tool_triggers_policy_violation(workspace_root: Path) -> None:
    """Executor kind not in allowed_tools triggers policy_violation and run fails."""
    _run_id, run_root = create_run(workspace_root)
    policy = SafetyPolicy(allowed_tools=["custom_only"])
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            StepSpec(
                step_id="a",
                name="a",
                executor=ExecutorSpec(
                    kind="local_command",
                    argv=["python", "-c", "print(1)"],
                ),
            ),
        ],
    )
    state = run_graph(run_root, graph, safety_policy=policy)
    assert state.status == RunStatus.FAILED, "disallowed tool should fail run"
    assert state.step_records["a"].status == StepStatus.FAILED, (
        "step with disallowed executor should fail"
    )
    assert "Policy violation" in (state.step_records["a"].last_error or ""), (
        "last_error should mention policy violation"
    )
    assert "not in allowed_tools" in (state.step_records["a"].last_error or ""), (
        "last_error should mention allowed_tools"
    )


def test_policy_violation_envelope_stored(workspace_root: Path) -> None:
    """Disallowed tool produces policy_violation.v1 envelope in artifact store."""
    run_id, run_root = create_run(workspace_root)
    policy = SafetyPolicy(allowed_tools=[])
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            StepSpec(
                step_id="a",
                name="a",
                executor=ExecutorSpec(
                    kind="local_command",
                    argv=["python", "-c", "pass"],
                ),
            ),
        ],
    )
    state = run_graph(run_root, graph, safety_policy=policy)
    assert state.status == RunStatus.FAILED, "disallowed tool should fail run"

    store = ArtifactStore(run_root, run_id)
    refs = store.list(run_id=run_id)
    policy_refs = [r for r in refs if r.artifact_type == POLICY_VIOLATION_SCHEMA_ID]
    assert len(policy_refs) == 1, "one policy_violation.v1 envelope should be stored"
    envelope = store.get_envelope(policy_refs[0])
    assert envelope.meta.schema_id == POLICY_VIOLATION_SCHEMA_ID
    assert envelope.payload["step_id"] == "a"
    assert envelope.payload["violation_type"] == "tool_not_allowed"
    assert "local_command" in envelope.payload["details"]


def test_default_policy_allows_local_command(workspace_root: Path) -> None:
    """When safety_policy is None, default allows local_command."""
    _run_id, run_root = create_run(workspace_root)
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            StepSpec(
                step_id="a",
                name="a",
                executor=ExecutorSpec(
                    kind="local_command",
                    argv=["python", "-c", "print(42)"],
                ),
            ),
        ],
    )
    state = run_graph(run_root, graph)
    assert state.status == RunStatus.SUCCEEDED, (
        "default policy should allow local_command"
    )
    assert state.step_records["a"].status == StepStatus.SUCCEEDED, (
        "step should succeed with default policy"
    )
