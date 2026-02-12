"""Layer 6: Pack (extension) models. Declarative; no domain logic in kernel."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

from lily.kernel.gate_models import GateRunnerSpec, GateSpec
from lily.kernel.graph_models import ExecutorSpec, RetryPolicy, TimeoutPolicy
from lily.kernel.policy_models import SafetyPolicy
from lily.kernel.routing_models import RoutingRule


def _require_namespaced_id(value: str, kind: str) -> str:
    """Require at least one dot (e.g. domain.name.v1). Raises ValueError if invalid."""
    if "." not in value or not value.strip():
        raise ValueError(
            f"{kind} must be namespaced (e.g. domain.name.v1), got: {value!r}"
        )
    return value


class SchemaRegistration(BaseModel):
    """Registration of an artifact schema for the schema registry."""

    model_config = {"arbitrary_types_allowed": True}

    schema_id: str
    model: type[BaseModel]

    @field_validator("schema_id")
    @classmethod
    def _schema_id_namespaced(cls, v: str) -> str:
        return _require_namespaced_id(v, "schema_id")


class StepTemplate(BaseModel):
    """Blueprint for generating StepSpec. Kernel only executes StepSpec."""

    template_id: str
    input_schema_ids: list[str] = Field(default_factory=list)
    output_schema_ids: list[str] = Field(default_factory=list)
    default_executor: ExecutorSpec = Field(default_factory=ExecutorSpec)
    default_retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    default_timeout_policy: TimeoutPolicy = Field(default_factory=TimeoutPolicy)
    default_gates: list[GateSpec] = Field(default_factory=list)

    @field_validator("template_id")
    @classmethod
    def _template_id_namespaced(cls, v: str) -> str:
        return _require_namespaced_id(v, "template_id")

    @field_validator("input_schema_ids", "output_schema_ids")
    @classmethod
    def _schema_ids_namespaced(cls, v: list[str]) -> list[str]:
        for sid in v:
            _require_namespaced_id(sid, "schema_id")
        return v


class GateTemplate(BaseModel):
    """Blueprint for generating GateSpec. Kernel only runs GateSpec."""

    template_id: str
    runner_spec: GateRunnerSpec
    required: bool = True

    @field_validator("template_id")
    @classmethod
    def _template_id_namespaced(cls, v: str) -> str:
        return _require_namespaced_id(v, "template_id")


class PackDefinition(BaseModel):
    """Structured representation of a pack. Declarative; import must not cause side effects."""

    name: str
    version: str
    minimum_kernel_version: str
    schemas: list[SchemaRegistration] = Field(default_factory=list)
    step_templates: list[StepTemplate] = Field(default_factory=list)
    gate_templates: list[GateTemplate] = Field(default_factory=list)
    routing_rules: list[RoutingRule] = Field(default_factory=list)
    default_safety_policy: SafetyPolicy | None = None

    @field_validator("name")
    @classmethod
    def _name_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Pack name is required")
        return v

    @model_validator(mode="after")
    def _schemas_and_templates_namespaced(self) -> "PackDefinition":
        for s in self.schemas:
            _require_namespaced_id(s.schema_id, "schema_id")
        for st in self.step_templates:
            _require_namespaced_id(st.template_id, "template_id")
        for gt in self.gate_templates:
            _require_namespaced_id(gt.template_id, "template_id")
        return self
