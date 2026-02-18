"""Blueprint registry and binding validation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ValidationError

from lily.blueprints.models import (
    Blueprint,
    BlueprintError,
    BlueprintErrorCode,
    normalize_raw_bindings,
    validate_blueprint_contract,
)


class BlueprintRegistry:
    """Deterministic registry for code-defined blueprints."""

    def __init__(self, blueprints: tuple[Blueprint, ...]) -> None:
        """Create blueprint registry keyed by stable blueprint id.

        Args:
            blueprints: Registered blueprint implementations.

        Raises:
            ValueError: If duplicate blueprint ids are registered.
        """
        self._blueprints: dict[str, Blueprint] = {}
        for blueprint in blueprints:
            validate_blueprint_contract(blueprint)
            blueprint_id = blueprint.id.strip()
            if blueprint_id in self._blueprints:
                raise ValueError(
                    f"Duplicate blueprint id '{blueprint_id}' is not allowed."
                )
            self._blueprints[blueprint_id] = blueprint

    def resolve(self, blueprint_id: str) -> Blueprint:
        """Resolve one blueprint by exact id.

        Args:
            blueprint_id: Target blueprint id.

        Returns:
            Matching blueprint implementation.

        Raises:
            BlueprintError: If id is unknown.
        """
        normalized = blueprint_id.strip()
        blueprint = self._blueprints.get(normalized)
        if blueprint is None:
            raise BlueprintError(
                BlueprintErrorCode.NOT_FOUND,
                f"Error: blueprint '{normalized}' is not registered.",
                data={"blueprint": normalized},
            )
        return blueprint

    def validate_bindings(
        self,
        *,
        blueprint_id: str,
        raw_bindings: Mapping[str, Any],
    ) -> BaseModel:
        """Validate raw bindings against blueprint binding schema.

        Args:
            blueprint_id: Target blueprint id.
            raw_bindings: Raw mapping payload for bindings.

        Returns:
            Validated bindings model instance.

        Raises:
            BlueprintError: If bindings schema validation fails.
        """
        blueprint = self.resolve(blueprint_id)
        payload = normalize_raw_bindings(raw_bindings)
        try:
            return blueprint.bindings_schema.model_validate(payload)
        except ValidationError as exc:
            raise BlueprintError(
                BlueprintErrorCode.BINDINGS_INVALID,
                f"Error: invalid bindings for blueprint '{blueprint.id}'.",
                data={
                    "blueprint": blueprint.id,
                    "validation_errors": exc.errors(),
                },
            ) from exc
