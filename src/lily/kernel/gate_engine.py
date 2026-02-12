"""Layer 3: GateEngine — run gates, store logs as artifacts, produce GateResult."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from lily.kernel.artifact_store import ArtifactStore, PutArtifactOptions
from lily.kernel.envelope_validator import EnvelopeValidator
from lily.kernel.gate_models import (
    GATE_RESULT_SCHEMA_ID,
    GateResultPayload,
    GateSpec,
    GateStatus,
)
from lily.kernel.gate_runner import run_local_gate
from lily.kernel.schema_registry import SchemaRegistry


class GateExecuteOptions:
    """Optional execution settings for execute_gate (attempt, producer_id)."""

    def __init__(
        self,
        attempt: int = 1,
        producer_id: str = "kernel",
    ) -> None:
        """Set attempt number and producer_id for gate execution.

        Args:
            attempt: Attempt number (1-based).
            producer_id: Producer ID for stored artifacts.
        """
        self.attempt = attempt
        self.producer_id = producer_id


def execute_gate(
    gate_spec: GateSpec,
    run_root: Path,
    artifact_store: ArtifactStore,
    registry: SchemaRegistry,
    *,
    options: GateExecuteOptions | None = None,
) -> tuple[str, bool]:
    """Run gate, store logs as artifacts, build and store GateResult envelope.

    Args:
        gate_spec: Gate to execute.
        run_root: Run directory.
        artifact_store: Store for gate result and log artifacts.
        registry: Schema registry for validation.
        options: Optional execution options (attempt, producer_id).

    Returns:
        (artifact_id of the stored GateResult envelope, success).
    """
    opts = options or GateExecuteOptions()
    result = run_local_gate(gate_spec, run_root, attempt=opts.attempt)

    log_artifact_ids: list[str] = []
    for key, abs_path_str in result.log_paths.items():
        path = Path(abs_path_str)
        if path.exists() and path.is_file():
            ref = artifact_store.put_file(
                "gate_log",
                path,
                options=PutArtifactOptions(
                    artifact_name=f"{gate_spec.gate_id}_{key}",
                    producer_id=opts.producer_id,
                ),
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
            "producer_id": opts.producer_id,
            "producer_kind": "system",
            "inputs": gate_spec.inputs,
        },
        artifact_name=f"gate_result_{gate_spec.gate_id}",
    )
    validator = EnvelopeValidator(registry)
    artifact_store.get_validated(ref, validator)
    return (ref.artifact_id, result.success)
