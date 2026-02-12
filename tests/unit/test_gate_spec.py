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


@pytest.mark.parametrize(
    "kwargs",
    [
        {"gate_id": "g1"},  # missing name, runner
        {"name": "n", "runner": _local_runner()},  # missing gate_id
        {"gate_id": "g1", "name": "n"},  # missing runner
    ],
    ids=["missing_name_and_runner", "missing_gate_id", "missing_runner"],
)
def test_missing_fields_fail(kwargs):
    """Missing required fields raise ValidationError."""
    with pytest.raises(ValidationError):
        GateSpec(**kwargs)


@pytest.mark.parametrize(
    "case",
    ["gate_spec_invalid_runner", "runner_spec_invalid_kind"],
    ids=["gate_spec_invalid_runner", "runner_spec_invalid_kind"],
)
def test_invalid_runner_kind_fails(case):
    """Runner kind other than local_command raises ValidationError."""
    with pytest.raises(ValidationError):
        if case == "gate_spec_invalid_runner":
            GateSpec(
                gate_id="g1",
                name="n",
                runner=GateRunnerSpec(
                    kind="local_command",
                    argv=["true"],
                ).model_copy(update={"kind": "llm_judge"}),
            )
        else:
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
