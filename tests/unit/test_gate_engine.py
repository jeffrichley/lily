"""Layer 3: GateEngine — envelope creation and storage."""

from pathlib import Path

from lily.kernel import (
    ArtifactStore,
    GateExecuteOptions,
    GateResultPayload,
    GateStatus,
    SchemaRegistry,
    create_run,
    execute_gate,
    register_gate_schemas,
)
from lily.kernel.envelope_validator import EnvelopeValidator
from lily.kernel.gate_models import GateRunnerSpec, GateSpec


def _gate_spec(
    gate_id: str = "g1",
    argv: list[str] | None = None,
) -> GateSpec:
    return GateSpec(
        gate_id=gate_id,
        name="Test gate",
        runner=GateRunnerSpec(
            kind="local_command",
            argv=argv or ["python", "-c", "pass"],
        ),
    )


def test_success_gate_produces_passed_gate_result(workspace_root: Path) -> None:
    """Successful gate produces passed GateResult envelope."""
    run_id, run_root = create_run(workspace_root)
    store = ArtifactStore(run_root, run_id)
    registry = SchemaRegistry()
    register_gate_schemas(registry)

    artifact_id, success = execute_gate(
        _gate_spec(argv=["python", "-c", "print(1)"]),
        run_root,
        store,
        registry,
        options=GateExecuteOptions(attempt=1),
    )

    assert artifact_id
    assert success is True
    refs = store.list(run_id=run_id)
    ref = next(r for r in refs if r.artifact_id == artifact_id)
    assert ref.artifact_type == "gate_result.v1"
    envelope = store.get_envelope(ref)
    assert envelope.meta.schema_id == "gate_result.v1"
    payload = envelope.payload
    assert payload["gate_id"] == "g1"
    assert payload["status"] == "passed"
    assert payload["reason"] is None


def test_failed_gate_produces_failed_gate_result(workspace_root: Path) -> None:
    """Failed gate produces failed GateResult envelope."""
    run_id, run_root = create_run(workspace_root)
    store = ArtifactStore(run_root, run_id)
    registry = SchemaRegistry()
    register_gate_schemas(registry)

    artifact_id, success = execute_gate(
        _gate_spec(argv=["python", "-c", "import sys; sys.exit(2)"]),
        run_root,
        store,
        registry,
        options=GateExecuteOptions(attempt=1),
    )

    assert success is False
    refs = store.list(run_id=run_id)
    ref = next(r for r in refs if r.artifact_id == artifact_id)
    envelope = store.get_envelope(ref)
    payload = envelope.payload
    assert payload["status"] == "failed"
    assert payload["reason"] is not None


def test_envelope_stored_and_validated(workspace_root: Path) -> None:
    """Stored envelope can be validated via registry."""
    run_id, run_root = create_run(workspace_root)
    store = ArtifactStore(run_root, run_id)
    registry = SchemaRegistry()
    register_gate_schemas(registry)

    artifact_id, _ = execute_gate(_gate_spec(), run_root, store, registry)

    refs = store.list(run_id=run_id)
    ref = next(r for r in refs if r.artifact_id == artifact_id)
    validator = EnvelopeValidator(registry)
    meta, model = store.get_validated(ref, validator)
    assert meta.schema_id == "gate_result.v1"
    assert isinstance(model, GateResultPayload)
    assert model.gate_id == "g1"
    assert model.status == GateStatus.PASSED
