"""Layer 1: Schema registry — schema_id to Pydantic model; validate payloads only."""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from lily.kernel.canonical import JSONReadOnly

T = TypeVar("T", bound=BaseModel)


class SchemaRegistryError(Exception):
    """Raised when schema_id is unknown or validation fails."""

    pass


class SchemaRegistry:
    """In-process registry: schema_id -> Pydantic model. Validates payload only."""

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._models: dict[str, type[BaseModel]] = {}

    def register(
        self,
        schema_id: str,
        model: type[BaseModel],
        *,
        override: bool = False,
    ) -> None:
        """Register model for schema_id. Raises if registered unless override=True.

        Args:
            schema_id: Identifier for the schema.
            model: Pydantic model class for validation.
            override: If True, replace existing registration.

        Raises:
            ValueError: If schema_id already registered and override is False.
        """
        if schema_id in self._models and not override:
            raise ValueError(f"Schema already registered: {schema_id!r}")
        self._models[schema_id] = model

    def get(self, schema_id: str) -> type[BaseModel]:
        """Return the model class for schema_id. Raises if not registered.

        Args:
            schema_id: Identifier for the schema.

        Returns:
            The registered Pydantic model class.

        Raises:
            SchemaRegistryError: If schema_id is not registered.
        """
        if schema_id not in self._models:
            raise SchemaRegistryError(f"Unknown schema_id: {schema_id!r}")
        return self._models[schema_id]

    def validate(self, schema_id: str, payload_obj: JSONReadOnly) -> BaseModel:
        """Validate payload against model for schema_id; return typed instance.

        Args:
            schema_id: Identifier for the schema.
            payload_obj: JSON-compatible payload to validate.

        Returns:
            Validated Pydantic model instance.
        """
        model = self.get(schema_id)
        return model.model_validate(payload_obj)
