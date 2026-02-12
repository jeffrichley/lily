"""Unit tests for Layer 6 template registry and expansion."""

from __future__ import annotations

import pytest

from lily.kernel.gate_models import GateRunnerSpec, GateSpec
from lily.kernel.graph_models import ExecutorSpec, StepSpec
from lily.kernel.pack_models import GateTemplate, StepTemplate
from lily.kernel.pack_registration import register_pack_templates
from lily.kernel.template_registry import TemplateRegistry


def test_template_registration_works() -> None:
    """Step and gate templates can be registered and retrieved."""
    reg = TemplateRegistry()
    step_t = StepTemplate(
        template_id="domain.step.v1",
        output_schema_ids=["domain.out.v1"],
        default_executor=ExecutorSpec(kind="local_command", argv=["echo"]),
    )
    gate_t = GateTemplate(
        template_id="domain.gate.v1",
        runner_spec=GateRunnerSpec(kind="local_command", argv=["true"]),
        required=True,
    )
    reg.register_step_template(step_t)
    reg.register_gate_template(gate_t)
    assert reg.get_step_template("domain.step.v1") is step_t
    assert reg.get_gate_template("domain.gate.v1") is gate_t


def test_collision_fails() -> None:
    """Registering the same template_id twice raises ValueError."""
    reg = TemplateRegistry()
    t = StepTemplate(template_id="domain.step.v1", output_schema_ids=[])
    reg.register_step_template(t)
    with pytest.raises(ValueError, match="already registered"):
        reg.register_step_template(t)
    # Same for gate
    g = GateTemplate(
        template_id="domain.gate.v1",
        runner_spec=GateRunnerSpec(kind="local_command", argv=["true"]),
    )
    reg.register_gate_template(g)
    with pytest.raises(ValueError, match="already registered"):
        reg.register_gate_template(g)


def test_expansion_produces_valid_step_spec() -> None:
    """Expanding a step template produces a valid StepSpec."""
    reg = TemplateRegistry()
    step_t = StepTemplate(
        template_id="coding.apply.v1",
        input_schema_ids=["coding.in.v1"],
        output_schema_ids=["coding.out.v1"],
        default_executor=ExecutorSpec(kind="local_command", argv=["patch"]),
    )
    reg.register_step_template(step_t)
    spec = reg.expand_step_template(
        "coding.apply.v1",
        step_id="step_1",
        name="Apply patch",
        description="Apply the patch",
        depends_on=["step_0"],
    )
    assert isinstance(spec, StepSpec)
    assert spec.step_id == "step_1"
    assert spec.name == "Apply patch"
    assert spec.description == "Apply the patch"
    assert spec.depends_on == ["step_0"]
    assert spec.output_schema_ids == ["coding.out.v1"]
    assert spec.executor.argv == ["patch"]


def test_expansion_produces_valid_gate_spec() -> None:
    """Expanding a gate template produces a valid GateSpec."""
    reg = TemplateRegistry()
    gate_t = GateTemplate(
        template_id="coding.lint.v1",
        runner_spec=GateRunnerSpec(
            kind="local_command", argv=["ruff", "check"], timeout_s=30.0
        ),
        required=True,
    )
    reg.register_gate_template(gate_t)
    spec = reg.expand_gate_template(
        "coding.lint.v1",
        gate_id="gate_lint",
        name="Lint",
        description="Run linter",
    )
    assert isinstance(spec, GateSpec)
    assert spec.gate_id == "gate_lint"
    assert spec.name == "Lint"
    assert spec.description == "Run linter"
    assert spec.runner.argv == ["ruff", "check"]
    assert spec.required is True


def test_register_pack_templates_collision_across_packs() -> None:
    """Two packs with same step template_id raise when registering."""
    from lily.kernel.pack_models import PackDefinition

    reg = TemplateRegistry()
    t = StepTemplate(template_id="shared.step.v1", output_schema_ids=[])
    pack_a = PackDefinition(
        name="a",
        version="1.0.0",
        minimum_kernel_version="0.1.0",
        step_templates=[t],
    )
    pack_b = PackDefinition(
        name="b",
        version="1.0.0",
        minimum_kernel_version="0.1.0",
        step_templates=[
            StepTemplate(template_id="shared.step.v1", output_schema_ids=[])
        ],
    )
    register_pack_templates(reg, [pack_a])
    with pytest.raises(ValueError, match="already registered"):
        register_pack_templates(reg, [pack_b])
