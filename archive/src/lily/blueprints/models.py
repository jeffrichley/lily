"""Blueprint runtime contracts and deterministic error types."""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict


class BlueprintErrorCode(StrEnum):
    """Stable blueprint registry/runtime error codes."""

    NOT_FOUND = "blueprint_not_found"
    BINDINGS_INVALID = "blueprint_bindings_invalid"
    COMPILE_FAILED = "blueprint_compile_failed"
    EXECUTION_FAILED = "blueprint_execution_failed"
    CONTRACT_INVALID = "blueprint_contract_invalid"


class BlueprintError(RuntimeError):
    """Blueprint failure with stable deterministic code."""

    def __init__(
        self,
        code: BlueprintErrorCode,
        message: str,
        *,
        data: dict[str, object] | None = None,
    ) -> None:
        """Create blueprint error.

        Args:
            code: Stable blueprint error code.
            message: Human-readable error message.
            data: Optional structured payload for diagnostics.
        """
        super().__init__(message)
        self.code = code
        self.data = data or {}


class BlueprintRunStatus(StrEnum):
    """Deterministic run status values for blueprint executions."""

    OK = "ok"
    ERROR = "error"


class BlueprintRunEnvelope(BaseModel):
    """Shared Run Contract R0 envelope for blueprint execution results."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: BlueprintRunStatus
    artifacts: tuple[str, ...] = ()
    approvals_requested: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
    payload: dict[str, object] = {}


class Blueprint(Protocol):
    """Protocol for code-defined blueprints."""

    id: str
    version: str
    summary: str
    bindings_schema: type[BaseModel]
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]

    def compile(self, bindings: BaseModel) -> object:
        """Compile blueprint with validated bindings.

        Args:
            bindings: Validated blueprint bindings payload.
        """


def validate_blueprint_contract(blueprint: Blueprint) -> None:
    """Validate one blueprint definition for registry admission.

    Args:
        blueprint: Blueprint implementation under validation.

    Raises:
        BlueprintError: If blueprint contract fields are invalid.
    """
    if not getattr(blueprint, "id", "").strip():
        raise BlueprintError(
            BlueprintErrorCode.CONTRACT_INVALID,
            "Error: blueprint id is required.",
        )
    if not getattr(blueprint, "version", "").strip():
        raise BlueprintError(
            BlueprintErrorCode.CONTRACT_INVALID,
            f"Error: blueprint '{blueprint.id}' is missing version.",
            data={"blueprint": blueprint.id},
        )
    if not getattr(blueprint, "summary", "").strip():
        raise BlueprintError(
            BlueprintErrorCode.CONTRACT_INVALID,
            f"Error: blueprint '{blueprint.id}' is missing summary.",
            data={"blueprint": blueprint.id},
        )
    _require_schema(blueprint, "bindings_schema")
    _require_schema(blueprint, "input_schema")
    _require_schema(blueprint, "output_schema")
    compile_fn = getattr(blueprint, "compile", None)
    if not callable(compile_fn):
        raise BlueprintError(
            BlueprintErrorCode.CONTRACT_INVALID,
            f"Error: blueprint '{blueprint.id}' is missing compile(bindings).",
            data={"blueprint": blueprint.id},
        )


def _require_schema(blueprint: Blueprint, field: str) -> None:
    """Validate one schema field on blueprint contract.

    Args:
        blueprint: Blueprint implementation under validation.
        field: Target field name to validate.

    Raises:
        BlueprintError: If schema field is not a Pydantic BaseModel subclass.
    """
    schema = getattr(blueprint, field, None)
    if (
        not isinstance(schema, type)
        or not issubclass(schema, BaseModel)
        or schema is BaseModel
    ):
        raise BlueprintError(
            BlueprintErrorCode.CONTRACT_INVALID,
            (
                f"Error: blueprint '{blueprint.id}' has invalid {field}; "
                "expected BaseModel subclass."
            ),
            data={"blueprint": blueprint.id, "field": field},
        )


def normalize_raw_bindings(raw_bindings: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize raw bindings to plain dict with deterministic key ordering.

    Args:
        raw_bindings: Raw mapping payload supplied by caller.

    Returns:
        Plain dictionary copy for validation.
    """
    return {str(key): value for key, value in sorted(raw_bindings.items())}
