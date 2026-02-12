"""Layer 5: Environment snapshot envelope and capture."""

from pathlib import Path

from lily.kernel.artifact_store import ArtifactStore
from lily.kernel.env_snapshot import (
    ENVIRONMENT_SNAPSHOT_SCHEMA_ID,
    EnvironmentSnapshotPayload,
    capture_environment_snapshot,
    register_observability_schemas,
)
from lily.kernel.run import KERNEL_VERSION
from lily.kernel.schema_registry import SchemaRegistry


def test_envelope_validates():
    """EnvironmentSnapshotPayload validates with required fields."""
    from datetime import UTC, datetime

    payload = EnvironmentSnapshotPayload(
        python_version="3.12.0",
        platform="Linux-1.2.3-x86_64",
        kernel_version="0.1.0",
        uv_lock_hash=None,
        timestamp=datetime.now(UTC),
    )
    assert payload.python_version == "3.12.0"
    assert payload.kernel_version == "0.1.0"
    registry = SchemaRegistry()
    register_observability_schemas(registry)
    validated = registry.validate(
        ENVIRONMENT_SNAPSHOT_SCHEMA_ID, payload.model_dump(mode="json")
    )
    assert validated.python_version == payload.python_version


def test_snapshot_fields_populated(tmp_path: Path):
    """capture_environment_snapshot populates python_version, platform, kernel_version, timestamp."""
    payload = capture_environment_snapshot(tmp_path, kernel_version=KERNEL_VERSION)
    assert payload.python_version
    assert payload.platform
    assert payload.kernel_version == KERNEL_VERSION
    assert payload.timestamp is not None
    assert payload.uv_lock_hash is None  # no uv.lock in tmp_path


def test_uv_lock_hash_optional(tmp_path: Path):
    """When uv.lock is absent, uv_lock_hash is None."""
    payload = capture_environment_snapshot(tmp_path, kernel_version="0.1.0")
    assert payload.uv_lock_hash is None


def test_uv_lock_hash_when_present(tmp_path: Path):
    """When uv.lock exists, uv_lock_hash is its sha256 hex."""
    (tmp_path / "uv.lock").write_text("content")
    payload = capture_environment_snapshot(tmp_path, kernel_version="0.1.0")
    assert payload.uv_lock_hash is not None
    assert len(payload.uv_lock_hash) == 64
    assert all(c in "0123456789abcdef" for c in payload.uv_lock_hash)


def test_stored_artifact_retrievable(tmp_path: Path):
    """Snapshot envelope can be stored via ArtifactStore and retrieved."""
    run_id = "run-snap"
    run_root = tmp_path / ".iris" / "runs" / run_id
    run_root.mkdir(parents=True)
    (run_root / "artifacts").mkdir()
    store = ArtifactStore(run_root, run_id)
    registry = SchemaRegistry()
    register_observability_schemas(registry)
    payload = capture_environment_snapshot(tmp_path, kernel_version=KERNEL_VERSION)
    ref = store.put_envelope(
        ENVIRONMENT_SNAPSHOT_SCHEMA_ID,
        payload,
        meta_fields={"producer_id": "kernel", "producer_kind": "system", "inputs": []},
        artifact_name="environment_snapshot",
    )
    envelope = store.get_envelope(ref)
    assert envelope.meta.schema_id == ENVIRONMENT_SNAPSHOT_SCHEMA_ID
    assert envelope.payload["python_version"] == payload.python_version
    assert envelope.payload["kernel_version"] == payload.kernel_version


def test_run_state_references_snapshot(tmp_path: Path):
    """run_graph creates RunState with environment_snapshot_ref set."""
    from lily.kernel import create_run, run_graph
    from lily.kernel.graph_models import ExecutorSpec, GraphSpec, StepSpec
    from lily.kernel.run_state import load_run_state

    workspace_root = tmp_path
    run_id, run_root = create_run(workspace_root)
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            StepSpec(
                step_id="a",
                name="a",
                depends_on=[],
                executor=ExecutorSpec(kind="local_command", argv=["echo", "1"]),
            ),
        ],
    )
    state = run_graph(run_root, graph)
    assert state.environment_snapshot_ref is not None
    loaded = load_run_state(run_root)
    assert loaded is not None
    assert loaded.environment_snapshot_ref == state.environment_snapshot_ref
