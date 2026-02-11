"""Layer 1: Schema registry — map schema_id to Pydantic model; validate payloads only."""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class SchemaRegistryError(Exception):
    """Raised when schema_id is unknown or validation fails."""

    pass


class SchemaRegistry:
    """In-process registry: schema_id -> Pydantic model class. Validates payload only."""

    def __init__(self) -> None:
        self._models: dict[str, type[BaseModel]] = {}

    def register(
        self,
        schema_id: str,
        model: type[BaseModel],
        *,
        override: bool = False,
    ) -> None:
        """Register a model class for schema_id. Raises if already registered unless override=True."""
        if schema_id in self._models and not override:
            raise ValueError(f"Schema already registered: {schema_id!r}")
        self._models[schema_id] = model

    def get(self, schema_id: str) -> type[BaseModel]:
        """Return the model class for schema_id. Raises if not registered."""
        if schema_id not in self._models:
            raise SchemaRegistryError(f"Unknown schema_id: {schema_id!r}")
        return self._models[schema_id]

    def validate(self, schema_id: str, payload_obj: Any) -> BaseModel:
        """Validate payload_obj against the model for schema_id; return typed instance."""
        model = self.get(schema_id)
        return model.model_validate(payload_obj)
