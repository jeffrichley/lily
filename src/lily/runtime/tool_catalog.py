"""Tool catalog schema and YAML/TOML loader for registry definitions."""

from __future__ import annotations

import tomllib
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal, cast

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class ToolCatalogLoadError(ValueError):
    """Raised when tool catalog config cannot be loaded or validated."""


class ToolSource(StrEnum):
    """Supported tool definition source types."""

    PYTHON = "python"
    MCP = "mcp"


class PythonToolDefinition(BaseModel):
    """One Python-backed tool definition entry."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, pattern=r"^[a-z0-9_]+$")
    source: Literal[ToolSource.PYTHON]
    target: str = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_target_format(self) -> PythonToolDefinition:
        """Ensure Python resolver target follows module:attribute format.

        Returns:
            Validated model instance.

        Raises:
            ValueError: If target is not in `module.path:attribute` format.
        """
        if ":" not in self.target:
            msg = "target must be in 'module.path:attribute' format"
            raise ValueError(msg)
        return self


class McpToolDefinition(BaseModel):
    """One MCP-backed tool definition entry."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, pattern=r"^[a-z0-9_]+$")
    source: Literal[ToolSource.MCP]
    server: str = Field(min_length=1)
    remote_tool: str = Field(min_length=1)


type ToolDefinition = Annotated[
    PythonToolDefinition | McpToolDefinition,
    Field(discriminator="source"),
]


class ToolCatalog(BaseModel):
    """Tool catalog root model containing tool definitions."""

    model_config = ConfigDict(extra="forbid")

    definitions: list[ToolDefinition] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_unique_ids(self) -> ToolCatalog:
        """Reject duplicate tool ids across all source types.

        Returns:
            Validated catalog model instance.

        Raises:
            ValueError: If duplicate tool ids are present.
        """
        seen: set[str] = set()
        duplicates: set[str] = set()
        for definition in self.definitions:
            definition_id = definition.id
            if definition_id in seen:
                duplicates.add(definition_id)
                continue
            seen.add(definition_id)

        if duplicates:
            duplicate_list = ", ".join(sorted(duplicates))
            msg = f"Duplicate tool definition ids: {duplicate_list}"
            raise ValueError(msg)
        return self


def _read_mapping(path: Path) -> dict[str, object]:
    """Read one YAML/TOML file and ensure top-level object mapping.

    Args:
        path: Config file path to read.

    Returns:
        Parsed top-level mapping.

    Raises:
        ToolCatalogLoadError: If file read/parsing fails or root is not a mapping.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        msg = f"Unable to read tool catalog file '{path}': {exc}"
        raise ToolCatalogLoadError(msg) from exc

    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        try:
            loaded = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            msg = f"Malformed YAML in '{path}': {exc}"
            raise ToolCatalogLoadError(msg) from exc
    elif suffix == ".toml":
        try:
            loaded = tomllib.loads(raw)
        except tomllib.TOMLDecodeError as exc:
            msg = f"Malformed TOML in '{path}': {exc}"
            raise ToolCatalogLoadError(msg) from exc
    else:
        msg = (
            f"Unsupported tool catalog file extension for '{path}'. "
            "Expected .yaml, .yml, or .toml."
        )
        raise ToolCatalogLoadError(msg)

    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        msg = f"Tool catalog file '{path}' must contain a top-level mapping/object."
        raise ToolCatalogLoadError(msg)
    return cast(dict[str, object], loaded)


def _format_validation_error(error: ValidationError) -> str:
    """Format pydantic validation errors as deterministic field messages.

    Args:
        error: Pydantic validation error payload.

    Returns:
        Deterministic multi-line error text.
    """
    lines: list[str] = ["Invalid tool catalog configuration:"]
    for issue in error.errors():
        raw_loc = ".".join(str(part) for part in issue["loc"])
        loc = raw_loc or "definitions"
        lines.append(f"- {loc}: {issue['msg']}")
    return "\n".join(lines)


def load_tool_catalog(path: str | Path) -> ToolCatalog:
    """Load, parse, and validate tool catalog definitions from YAML/TOML.

    Args:
        path: Tool catalog config file path.

    Returns:
        Parsed and validated tool catalog model.

    Raises:
        ToolCatalogLoadError: If config cannot be read, parsed, or validated.
    """
    catalog_path = Path(path)
    raw_mapping = _read_mapping(catalog_path)

    try:
        return ToolCatalog.model_validate(raw_mapping)
    except ValidationError as exc:
        raise ToolCatalogLoadError(_format_validation_error(exc)) from exc
