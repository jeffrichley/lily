"""Unit tests for pack schema registration (Layer 6)."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from lily.kernel.gate_models import GATE_RESULT_SCHEMA_ID, register_gate_schemas
from lily.kernel.pack_models import PackDefinition, SchemaRegistration
from lily.kernel.pack_registration import register_pack_schemas
from lily.kernel.schema_registry import SchemaRegistry


class _PayloadA(BaseModel):
    value: str


class _PayloadB(BaseModel):
    count: int


def test_schema_registers_successfully() -> None:
    """Pack schemas register into empty registry."""
    registry = SchemaRegistry()
    pack = PackDefinition(
        name="test",
        version="1.0.0",
        minimum_kernel_version="0.1.0",
        schemas=[
            SchemaRegistration(schema_id="test.artifact.v1", model=_PayloadA),
        ],
    )
    register_pack_schemas(registry, [pack])
    assert registry.get("test.artifact.v1") is _PayloadA


def test_collision_between_packs_fails() -> None:
    """Two packs registering the same schema_id raises ValueError."""
    registry = SchemaRegistry()
    pack_a = PackDefinition(
        name="pack_a",
        version="1.0.0",
        minimum_kernel_version="0.1.0",
        schemas=[SchemaRegistration(schema_id="shared.id.v1", model=_PayloadA)],
    )
    pack_b = PackDefinition(
        name="pack_b",
        version="1.0.0",
        minimum_kernel_version="0.1.0",
        schemas=[SchemaRegistration(schema_id="shared.id.v1", model=_PayloadB)],
    )
    with pytest.raises(ValueError, match=r"Duplicate schema_id.*shared\.id\.v1"):
        register_pack_schemas(registry, [pack_a, pack_b])


def test_kernel_schema_override_blocked() -> None:
    """Registering a pack schema with an ID already used by kernel raises."""
    registry = SchemaRegistry()
    register_gate_schemas(registry)
    pack = PackDefinition(
        name="evil",
        version="1.0.0",
        minimum_kernel_version="0.1.0",
        schemas=[
            SchemaRegistration(schema_id=GATE_RESULT_SCHEMA_ID, model=_PayloadA),
        ],
    )
    with pytest.raises(ValueError, match="Schema already registered"):
        register_pack_schemas(registry, [pack])
