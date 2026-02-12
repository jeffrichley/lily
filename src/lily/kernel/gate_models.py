"""Layer 3: Gate result payload and schema registration. Pure models; no IO."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from lily.kernel.schema_registry import SchemaRegistry

GATE_RESULT_SCHEMA_ID = "gate_result.v1"


class GateStatus(str, Enum):
    """Gate execution outcome."""

    PASSED = "passed"
    FAILED = "failed"


class GateResultPayload(BaseModel):
    """Payload for gate_result.v1 envelope. Produced by GateEngine."""

    model_config = {"extra": "forbid"}

    gate_id: str
    status: GateStatus
    reason: str | None = None
    log_artifact_ids: list[str] = Field(default_factory=list)
    metrics: dict[str, float] | None = None
    timestamp: datetime


def register_gate_schemas(registry: SchemaRegistry) -> None:
    """Register Layer 3 schema(s) on the given registry."""
    registry.register(GATE_RESULT_SCHEMA_ID, GateResultPayload)


# --- GateSpec and GateRunnerSpec (Phase 3.2) ---


class GateRunnerSpec(BaseModel):
    """Local command runner for a gate. Layer 3 supports local_command only."""

    model_config = {"extra": "forbid"}

    kind: Literal["local_command"] = "local_command"
    argv: list[str] = Field(default_factory=list)
    cwd: str | None = None
    env: dict[str, str] | None = None
    timeout_s: float | None = None


class GateSpec(BaseModel):
    """Verification unit: inputs, runner, required/optional."""

    model_config = {"extra": "forbid"}

    gate_id: str
    name: str
    description: str | None = None
    inputs: list[str] = Field(default_factory=list)
    workspace_required: bool = False
    runner: GateRunnerSpec
    required: bool = True

    @model_validator(mode="after")
    def _runner_must_be_local_command(self) -> "GateSpec":
        if self.runner.kind != "local_command":
            raise ValueError(f"Unsupported gate runner kind: {self.runner.kind!r}")
        return self


def validate_gate_specs_unique(gates: list[GateSpec]) -> None:
    """Raise ValueError if gate_id is duplicated in the list."""
    seen: set[str] = set()
    for g in gates:
        if g.gate_id in seen:
            raise ValueError(f"Duplicate gate_id: {g.gate_id!r}")
        seen.add(g.gate_id)
