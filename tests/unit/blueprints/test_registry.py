"""Unit tests for blueprint registry and binding validation."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ConfigDict

from lily.blueprints import BlueprintError, BlueprintErrorCode, BlueprintRegistry


class _Bindings(BaseModel):
    """Bindings schema fixture."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    topic: str
    specialists: int


class _Input(BaseModel):
    """Input schema fixture."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    prompt: str


class _Output(BaseModel):
    """Output schema fixture."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    report: str


class _CouncilBlueprint:
    """Minimal blueprint fixture."""

    id = "council.v1"
    version = "1.0.0"
    summary = "Parallel specialists then synthesize."
    bindings_schema = _Bindings
    input_schema = _Input
    output_schema = _Output

    def compile(self, bindings: BaseModel) -> object:
        """Return deterministic compile payload for tests."""
        return {"compiled": True, "bindings": bindings.model_dump()}


@pytest.mark.unit
def test_registry_resolves_known_blueprint_deterministically() -> None:
    """Known blueprint id should resolve to registered blueprint object."""
    blueprint = _CouncilBlueprint()
    registry = BlueprintRegistry((blueprint,))

    resolved = registry.resolve("council.v1")

    assert resolved is blueprint
    assert resolved.id == "council.v1"


@pytest.mark.unit
def test_registry_raises_deterministic_not_found_error() -> None:
    """Unknown blueprint id should raise stable not-found error code."""
    registry = BlueprintRegistry((_CouncilBlueprint(),))

    try:
        registry.resolve("missing.v1")
    except BlueprintError as exc:
        assert exc.code == BlueprintErrorCode.NOT_FOUND
        assert str(exc) == "Error: blueprint 'missing.v1' is not registered."
        assert exc.data["blueprint"] == "missing.v1"
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected BlueprintError for missing blueprint.")


@pytest.mark.unit
def test_registry_validates_bindings_successfully() -> None:
    """Valid bindings should be coerced into typed bindings model."""
    registry = BlueprintRegistry((_CouncilBlueprint(),))

    validated = registry.validate_bindings(
        blueprint_id="council.v1",
        raw_bindings={"topic": "security", "specialists": 4},
    )

    assert isinstance(validated, _Bindings)
    assert validated.topic == "security"
    assert validated.specialists == 4


@pytest.mark.unit
def test_registry_raises_deterministic_bindings_invalid_error() -> None:
    """Invalid bindings should raise stable bindings-invalid error code."""
    registry = BlueprintRegistry((_CouncilBlueprint(),))

    try:
        registry.validate_bindings(
            blueprint_id="council.v1",
            raw_bindings={"topic": "security"},
        )
    except BlueprintError as exc:
        assert exc.code == BlueprintErrorCode.BINDINGS_INVALID
        assert str(exc) == "Error: invalid bindings for blueprint 'council.v1'."
        assert exc.data["blueprint"] == "council.v1"
        assert exc.data["validation_errors"]
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected BlueprintError for invalid bindings.")
