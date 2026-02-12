"""Layer 4: Write path policy enforcement."""

from pathlib import Path

from lily.kernel import create_run, run_graph
from lily.kernel.graph_models import ExecutorSpec, GraphSpec, StepSpec
from lily.kernel.policy_models import POLICY_VIOLATION_SCHEMA_ID, SafetyPolicy
from lily.kernel.run_state import RunStatus, StepStatus
from lily.kernel.artifact_store import ArtifactStore


def test_writing_to_allowed_path_passes(workspace_root: Path):
    """Step writing only to allowed path passes."""
    run_id, run_root = create_run(workspace_root)
    policy = SafetyPolicy(
        allowed_tools=["local_command"],
        allow_write_paths=["artifacts", "tmp"],
        deny_write_paths=[],
    )
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            StepSpec(
                step_id="a",
                name="a",
                executor=ExecutorSpec(
                    kind="local_command",
                    argv=[
                        "python", "-c",
                        "from pathlib import Path; p = Path('tmp/out.txt'); p.parent.mkdir(exist_ok=True); p.write_text('ok')"
                    ],
                    cwd=".",
                ),
            ),
        ],
    )
    state = run_graph(run_root, graph, safety_policy=policy)
    assert state.status == RunStatus.SUCCEEDED
    assert state.step_records["a"].status == StepStatus.SUCCEEDED


def test_writing_to_denied_path_triggers_violation(workspace_root: Path):
    """Step writing to denied path triggers policy violation."""
    run_id, run_root = create_run(workspace_root)
    (run_root / "protected").mkdir(exist_ok=True)
    policy = SafetyPolicy(
        allowed_tools=["local_command"],
        allow_write_paths=["artifacts", "tmp"],
        deny_write_paths=["protected"],
    )
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            StepSpec(
                step_id="a",
                name="a",
                executor=ExecutorSpec(
                    kind="local_command",
                    argv=[
                        "python", "-c",
                        "from pathlib import Path; Path('protected/forbidden.txt').write_text('x')"
                    ],
                    cwd=str(run_root),
                ),
            ),
        ],
    )
    state = run_graph(run_root, graph, safety_policy=policy)
    assert state.status == RunStatus.FAILED
    assert state.step_records["a"].status == StepStatus.FAILED
    assert "Policy violation" in (state.step_records["a"].last_error or "")
    assert "denied" in (state.step_records["a"].last_error or "")


def test_policy_violation_envelope_stored_on_write_denied(workspace_root: Path):
    """Write to denied path produces policy_violation.v1 envelope."""
    run_id, run_root = create_run(workspace_root)
    (run_root / "denied").mkdir(exist_ok=True)
    policy = SafetyPolicy(
        allowed_tools=["local_command"],
        allow_write_paths=[],
        deny_write_paths=["denied"],
    )
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            StepSpec(
                step_id="a",
                name="a",
                executor=ExecutorSpec(
                    kind="local_command",
                    argv=[
                        "python", "-c",
                        "from pathlib import Path; Path('denied/x.txt').write_text('x')"
                    ],
                    cwd=str(run_root),
                ),
            ),
        ],
    )
    state = run_graph(run_root, graph, safety_policy=policy)
    assert state.status == RunStatus.FAILED

    store = ArtifactStore(run_root, run_id)
    refs = store.list(run_id=run_id)
    policy_refs = [r for r in refs if r.artifact_type == POLICY_VIOLATION_SCHEMA_ID]
    assert len(policy_refs) == 1
    envelope = store.get_envelope(policy_refs[0])
    assert envelope.payload["violation_type"] == "write_denied"
    assert "denied" in envelope.payload["details"]
