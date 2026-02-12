"""Layer 3: GateSpec and GateRunnerSpec validation."""

import pytest
from pydantic import ValidationError

from lily.kernel.gate_models import (
    GateRunnerSpec,
    GateSpec,
    validate_gate_specs_unique,
)


def _local_runner(argv: list[str] | None = None) -> GateRunnerSpec:
    return GateRunnerSpec(kind="local_command", argv=argv or ["true"])


def test_valid_gate_spec_constructs():
    """Valid GateSpec with all fields constructs."""
    spec = GateSpec(
        gate_id="g1",
        name="Check",
        description="Optional",
        inputs=["art-1"],
        workspace_required=False,
        runner=_local_runner(["echo", "ok"]),
        required=True,
    )
    assert spec.gate_id == "g1"
    assert spec.name == "Check"
    assert spec.runner.kind == "local_command"
    assert spec.runner.argv == ["echo", "ok"]
    assert spec.required is True

    minimal = GateSpec(
        gate_id="g2",
        name="Min",
        runner=_local_runner(),
    )
    assert minimal.description is None
    assert minimal.inputs == []
    assert minimal.workspace_required is False
    assert minimal.required is True


def test_missing_fields_fail():
    """Missing required fields raise ValidationError."""
    with pytest.raises(ValidationError):
        GateSpec(
            gate_id="g1",
            # missing name, runner
        )
    with pytest.raises(ValidationError):
        GateSpec(
            name="n",
            runner=_local_runner(),
            # missing gate_id
        )
    with pytest.raises(ValidationError):
        GateSpec(
            gate_id="g1",
            name="n",
            # missing runner
        )


def test_invalid_runner_kind_fails():
    """Runner kind other than local_command raises ValueError (model validator)."""
    with pytest.raises(ValidationError):
        GateSpec(
            gate_id="g1",
            name="n",
            runner=GateRunnerSpec(
                kind="local_command",
                argv=["true"],
            ).model_copy(update={"kind": "llm_judge"}),
        )
    # GateRunnerSpec itself only allows Literal["local_command"], so constructing
    # with kind="llm_judge" would fail at GateRunnerSpec level
    with pytest.raises(ValidationError):
        GateRunnerSpec(kind="llm_judge", argv=[])  # type: ignore[arg-type]


def test_validate_gate_specs_unique():
    """validate_gate_specs_unique raises on duplicate gate_id."""
    gates = [
        GateSpec(gate_id="a", name="A", runner=_local_runner()),
        GateSpec(gate_id="b", name="B", runner=_local_runner()),
    ]
    validate_gate_specs_unique(gates)

    with pytest.raises(ValueError, match="Duplicate gate_id"):
        validate_gate_specs_unique(
            [
                GateSpec(gate_id="x", name="X", runner=_local_runner()),
                GateSpec(gate_id="x", name="Y", runner=_local_runner()),
            ]
        )
