"""Unit tests for Layer 6 pack models."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from lily.kernel.gate_models import GateRunnerSpec
from lily.kernel.graph_models import ExecutorSpec
from lily.kernel.pack_models import (
    GateTemplate,
    PackDefinition,
    SchemaRegistration,
    StepTemplate,
)
from lily.kernel.policy_models import SafetyPolicy
from lily.kernel.routing_models import (
    RoutingAction,
    RoutingActionType,
    RoutingCondition,
    RoutingRule,
)


class _DummyPayload(BaseModel):
    """Minimal payload for schema registration tests."""

    value: str


def test_valid_pack_definition_passes() -> None:
    """Valid PackDefinition with all optional fields empty passes."""
    pack = PackDefinition(
        name="test_pack",
        version="1.0.0",
        minimum_kernel_version="0.1.0",
    )
    assert pack.name == "test_pack"
    assert pack.version == "1.0.0"
    assert pack.minimum_kernel_version == "0.1.0"
    assert pack.schemas == []
    assert pack.step_templates == []
    assert pack.gate_templates == []
    assert pack.routing_rules == []
    assert pack.default_safety_policy is None


def test_valid_pack_definition_with_contributions_passes() -> None:
    """PackDefinition with schemas, step/gate templates, routing, and safety passes."""
    pack = PackDefinition(
        name="coding",
        version="1.0.0",
        minimum_kernel_version="0.1.0",
        schemas=[
            SchemaRegistration(schema_id="coding.code_patch.v1", model=_DummyPayload),
        ],
        step_templates=[
            StepTemplate(
                template_id="coding.apply_patch.v1",
                output_schema_ids=["coding.code_patch.v1"],
                default_executor=ExecutorSpec(kind="local_command", argv=["echo"]),
            ),
        ],
        gate_templates=[
            GateTemplate(
                template_id="coding.lint.v1",
                runner_spec=GateRunnerSpec(kind="local_command", argv=["true"]),
                required=True,
            ),
        ],
        routing_rules=[
            RoutingRule(
                rule_id="coding.retry_on_fail",
                when=RoutingCondition(step_status="failed"),
                action=RoutingAction(type=RoutingActionType.RETRY_STEP),
            ),
        ],
        default_safety_policy=SafetyPolicy(
            allowed_tools=["local_command"], network_access="deny"
        ),
    )
    assert len(pack.schemas) == 1
    assert pack.schemas[0].schema_id == "coding.code_patch.v1"
    assert len(pack.step_templates) == 1
    assert pack.step_templates[0].template_id == "coding.apply_patch.v1"
    assert len(pack.gate_templates) == 1
    assert pack.gate_templates[0].template_id == "coding.lint.v1"
    assert len(pack.routing_rules) == 1
    assert pack.routing_rules[0].rule_id == "coding.retry_on_fail"
    assert pack.default_safety_policy is not None
    assert pack.default_safety_policy.network_access == "deny"


@pytest.mark.parametrize("invalid_name", ["", "   "], ids=["empty", "whitespace_only"])
def test_pack_definition_missing_name_fails(invalid_name: str) -> None:
    """Empty or missing pack name fails validation."""
    with pytest.raises(ValueError, match="Pack name is required"):
        PackDefinition(
            name=invalid_name,
            version="1.0.0",
            minimum_kernel_version="0.1.0",
        )


@pytest.mark.parametrize("invalid_schema_id", ["no_dot", ""], ids=["no_dot", "empty"])
def test_schema_registration_namespacing_enforced(invalid_schema_id: str) -> None:
    """Schema IDs must be namespaced (contain a dot)."""
    SchemaRegistration(schema_id="domain.artifact.v1", model=_DummyPayload)
    with pytest.raises(ValueError, match="namespaced"):
        SchemaRegistration(schema_id=invalid_schema_id, model=_DummyPayload)


@pytest.mark.parametrize(
    "template_id,output_schema_ids",
    [
        ("no_dot", []),
        ("domain.step.v1", ["bad"]),
    ],
    ids=["template_id_no_dot", "output_schema_id_not_namespaced"],
)
def test_step_template_namespacing_enforced(
    template_id: str, output_schema_ids: list[str]
) -> None:
    """Step template_id and schema IDs in lists must be namespaced."""
    StepTemplate(
        template_id="domain.step.v1",
        input_schema_ids=["domain.in.v1"],
        output_schema_ids=["domain.out.v1"],
    )
    with pytest.raises(ValueError, match="namespaced"):
        StepTemplate(template_id=template_id, output_schema_ids=output_schema_ids)


def test_gate_template_namespacing_enforced() -> None:
    """Gate template_id must be namespaced."""
    GateTemplate(
        template_id="domain.gate.v1",
        runner_spec=GateRunnerSpec(kind="local_command", argv=["true"]),
    )
    with pytest.raises(ValueError, match="namespaced"):
        GateTemplate(
            template_id="no_dot",
            runner_spec=GateRunnerSpec(kind="local_command", argv=["true"]),
        )


def test_pack_definition_with_non_namespaced_schema_fails() -> None:
    """PackDefinition with non-namespaced schema ID fails (validator on schemas)."""
    with pytest.raises(ValueError, match="namespaced"):
        PackDefinition(
            name="p",
            version="1.0.0",
            minimum_kernel_version="0.1.0",
            schemas=[SchemaRegistration(schema_id="x", model=_DummyPayload)],
        )
