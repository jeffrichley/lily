"""Layer 4: Policy violation and safety policy models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from lily.kernel.schema_registry import SchemaRegistry

POLICY_VIOLATION_SCHEMA_ID = "policy_violation.v1"


class SafetyPolicy(BaseModel):
    """Safety policy for sandboxing step execution. Declarative config."""

    model_config = {"extra": "forbid"}

    allow_write_paths: list[str] = Field(default_factory=list)
    deny_write_paths: list[str] = Field(default_factory=list)
    max_diff_size_bytes: int | None = None
    allowed_tools: list[str] = Field(default_factory=list)
    network_access: Literal["allow", "deny"] = "deny"

    @classmethod
    def default_policy(cls) -> "SafetyPolicy":
        """Return a permissive default policy (local_command allowed, deny network)."""
        return cls(
            allow_write_paths=[],
            deny_write_paths=[],
            max_diff_size_bytes=None,
            allowed_tools=["local_command"],
            network_access="deny",
        )


class PolicyViolationPayload(BaseModel):
    """Payload for policy_violation.v1 envelope. Produced on policy enforcement failure."""

    model_config = {"extra": "forbid"}

    step_id: str
    violation_type: str
    details: str
    timestamp: datetime


def register_policy_schemas(registry: SchemaRegistry) -> None:
    """Register Layer 4 policy schema(s) on the given registry."""
    registry.register(POLICY_VIOLATION_SCHEMA_ID, PolicyViolationPayload)
