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
    # Arrange - registry with one blueprint
    blueprint = _CouncilBlueprint()
    registry = BlueprintRegistry((blueprint,))

    # Act - resolve by known id
    resolved = registry.resolve("council.v1")

    # Assert - same instance and id
    assert resolved is blueprint
    assert resolved.id == "council.v1"


@pytest.mark.unit
def test_registry_raises_deterministic_not_found_error() -> None:
    """Unknown blueprint id should raise stable not-found error code."""
    # Arrange - registry with one blueprint
    registry = BlueprintRegistry((_CouncilBlueprint(),))

    # Act - resolve by unknown id
    try:
        registry.resolve("missing.v1")
    except BlueprintError as exc:
        # Assert - not found code and message
        assert exc.code == BlueprintErrorCode.NOT_FOUND
        assert str(exc) == "Error: blueprint 'missing.v1' is not registered."
        assert exc.data["blueprint"] == "missing.v1"
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected BlueprintError for missing blueprint.")


@pytest.mark.unit
def test_registry_validates_bindings_successfully() -> None:
    """Valid bindings should be coerced into typed bindings model."""
    # Arrange - registry and valid raw bindings
    registry = BlueprintRegistry((_CouncilBlueprint(),))

    # Act - validate bindings for blueprint
    validated = registry.validate_bindings(
        blueprint_id="council.v1",
        raw_bindings={"topic": "security", "specialists": 4},
    )

    # Assert - typed bindings with expected values
    assert isinstance(validated, _Bindings)
    assert validated.topic == "security"
    assert validated.specialists == 4


@pytest.mark.unit
def test_registry_raises_deterministic_bindings_invalid_error() -> None:
    """Invalid bindings should raise stable bindings-invalid error code."""
    # Arrange - registry and invalid raw bindings missing required field
    registry = BlueprintRegistry((_CouncilBlueprint(),))

    # Act - validate invalid bindings
    try:
        registry.validate_bindings(
            blueprint_id="council.v1",
            raw_bindings={"topic": "security"},
        )
    except BlueprintError as exc:
        # Assert - bindings invalid code and validation errors
        assert exc.code == BlueprintErrorCode.BINDINGS_INVALID
        assert str(exc) == "Error: invalid bindings for blueprint 'council.v1'."
        assert exc.data["blueprint"] == "council.v1"
        assert exc.data["validation_errors"]
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected BlueprintError for invalid bindings.")
