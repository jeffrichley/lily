"""YAML/TOML loading and validation for Lily runtime configuration."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from lily.runtime.config_schema import RuntimeConfig


class ConfigLoadError(ValueError):
    """Raised when runtime config cannot be loaded or validated."""


def _read_mapping(path: Path) -> dict[str, Any]:
    """Read one YAML/TOML file and return it as a mapping.

    Args:
        path: Path to the config file to read.

    Returns:
        Parsed top-level mapping from YAML/TOML.

    Raises:
        ConfigLoadError: If file read/parsing fails or root is not a mapping/object.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        msg = f"Unable to read config file '{path}': {exc}"
        raise ConfigLoadError(msg) from exc

    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        try:
            loaded = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            msg = f"Malformed YAML in '{path}': {exc}"
            raise ConfigLoadError(msg) from exc
    elif suffix == ".toml":
        try:
            loaded = tomllib.loads(raw)
        except tomllib.TOMLDecodeError as exc:
            msg = f"Malformed TOML in '{path}': {exc}"
            raise ConfigLoadError(msg) from exc
    else:
        msg = (
            f"Unsupported config file extension for '{path}'. "
            "Expected .yaml, .yml, or .toml."
        )
        raise ConfigLoadError(msg)

    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        msg = f"Config file '{path}' must contain a top-level mapping/object."
        raise ConfigLoadError(msg)
    return loaded


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge override into base recursively and return a new mapping.

    Args:
        base: Base configuration mapping.
        override: Override mapping applied on top of base.

    Returns:
        New recursively merged mapping.
    """
    merged: dict[str, Any] = dict(base)
    for key, override_value in override.items():
        base_value = merged.get(key)
        if isinstance(base_value, dict) and isinstance(override_value, dict):
            merged[key] = _deep_merge(base_value, override_value)
            continue
        merged[key] = override_value
    return merged


def _format_validation_error(error: ValidationError) -> str:
    """Format pydantic validation errors as deterministic field messages.

    Args:
        error: Pydantic validation error to render.

    Returns:
        Human-readable multi-line validation message.
    """
    lines: list[str] = ["Invalid runtime configuration:"]
    for issue in error.errors():
        loc = ".".join(str(part) for part in issue["loc"])
        lines.append(f"- {loc}: {issue['msg']}")
    return "\n".join(lines)


def load_runtime_config(
    base_config_path: str | Path,
    override_config_path: str | Path | None = None,
) -> RuntimeConfig:
    """Load, merge, and validate runtime config from YAML/TOML files.

    Args:
        base_config_path: Path to the base config file.
        override_config_path: Optional path to override config file.

    Returns:
        Fully validated runtime config object.

    Raises:
        ConfigLoadError: If config cannot be read, parsed, or validated.
    """
    base_path = Path(base_config_path)
    base_mapping = _read_mapping(base_path)

    merged_mapping = base_mapping
    if override_config_path is not None:
        override_path = Path(override_config_path)
        override_mapping = _read_mapping(override_path)
        merged_mapping = _deep_merge(base_mapping, override_mapping)

    try:
        return RuntimeConfig.model_validate(merged_mapping)
    except ValidationError as exc:
        raise ConfigLoadError(_format_validation_error(exc)) from exc
