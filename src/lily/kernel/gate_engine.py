"""Layer 3: GateEngine — run gates, store logs as artifacts, produce GateResult envelopes."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from lily.kernel.artifact_store import ArtifactStore
from lily.kernel.envelope_validator import EnvelopeValidator
from lily.kernel.gate_models import (
    GATE_RESULT_SCHEMA_ID,
    GateResultPayload,
    GateSpec,
    GateStatus,
)
from lily.kernel.gate_runner import run_local_gate
from lily.kernel.schema_registry import SchemaRegistry


def execute_gate(
    gate_spec: GateSpec,
    run_root: Path,
    artifact_store: ArtifactStore,
    registry: SchemaRegistry,
    attempt: int = 1,
    producer_id: str = "kernel",
) -> tuple[str, bool]:
    """
    Run gate, store logs as artifacts, build and store GateResult envelope.
    Returns (artifact_id of the stored GateResult envelope, success).
    """
    result = run_local_gate(gate_spec, run_root, attempt=attempt)

    log_artifact_ids: list[str] = []
    for key, abs_path_str in result.log_paths.items():
        path = Path(abs_path_str)
        if path.exists() and path.is_file():
            ref = artifact_store.put_file(
                artifact_type="gate_log",
                source_path=path,
                artifact_name=f"{gate_spec.gate_id}_{key}",
                producer_id=producer_id,
            )
            log_artifact_ids.append(ref.artifact_id)

    status = GateStatus.PASSED if result.success else GateStatus.FAILED
    payload = GateResultPayload(
        gate_id=gate_spec.gate_id,
        status=status,
        reason=result.error_message,
        log_artifact_ids=log_artifact_ids,
        metrics=None,
        timestamp=datetime.now(UTC),
    )

    ref = artifact_store.put_envelope(
        GATE_RESULT_SCHEMA_ID,
        payload,
        meta_fields={
            "producer_id": producer_id,
            "producer_kind": "system",
            "inputs": gate_spec.inputs,
        },
        artifact_name=f"gate_result_{gate_spec.gate_id}",
    )
    validator = EnvelopeValidator(registry)
    artifact_store.get_validated(ref, validator)
    return (ref.artifact_id, result.success)
