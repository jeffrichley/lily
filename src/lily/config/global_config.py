"""Global Lily config models and loading helpers."""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class CheckpointerBackend(StrEnum):
    """Supported checkpointer backend identifiers."""

    SQLITE = "sqlite"
    MEMORY = "memory"
    POSTGRES = "postgres"


class CheckpointerSettings(BaseModel):
    """Global checkpointer configuration."""

    model_config = ConfigDict(extra="forbid")

    backend: CheckpointerBackend = CheckpointerBackend.SQLITE
    sqlite_path: str = ".lily/checkpoints/checkpointer.sqlite"
    postgres_dsn: str | None = None


class MemoryToolingSettings(BaseModel):
    """Global LangMem tooling feature flags."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    auto_apply: bool = False


class EvidenceChunkingMode(StrEnum):
    """Supported evidence chunking strategy modes."""

    RECURSIVE = "recursive"
    TOKEN = "token"  # nosec B105


class EvidenceSettings(BaseModel):
    """Global semantic evidence configuration."""

    model_config = ConfigDict(extra="forbid")

    chunking_mode: EvidenceChunkingMode = EvidenceChunkingMode.RECURSIVE
    chunk_size: int = Field(default=360, ge=64, le=4000)
    chunk_overlap: int = Field(default=40, ge=0, le=1000)
    token_encoding_name: str = "cl100k_base"


class ConsolidationBackend(StrEnum):
    """Supported consolidation backend identifiers."""

    RULE_BASED = "rule_based"
    LANGMEM_MANAGER = "langmem_manager"


class CompactionBackend(StrEnum):
    """Supported conversation compaction backend identifiers."""

    RULE_BASED = "rule_based"
    LANGGRAPH_NATIVE = "langgraph_native"


class CompactionSettings(BaseModel):
    """Global conversation compaction configuration."""

    model_config = ConfigDict(extra="forbid")

    backend: CompactionBackend = CompactionBackend.LANGGRAPH_NATIVE
    max_tokens: int = Field(default=1000, ge=1)


class ConsolidationSettings(BaseModel):
    """Global memory consolidation feature flags."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    backend: ConsolidationBackend = ConsolidationBackend.RULE_BASED
    llm_assisted_enabled: bool = False
    auto_run_every_n_turns: int = Field(default=0, ge=0)


class LilyGlobalConfig(BaseModel):
    """Root global Lily configuration model."""

    model_config = ConfigDict(extra="forbid")

    checkpointer: CheckpointerSettings = CheckpointerSettings()
    memory_tooling: MemoryToolingSettings = MemoryToolingSettings()
    evidence: EvidenceSettings = EvidenceSettings()
    compaction: CompactionSettings = CompactionSettings()
    consolidation: ConsolidationSettings = ConsolidationSettings()


class GlobalConfigError(RuntimeError):
    """Raised when global config cannot be decoded or validated."""


def _decode_config_payload(path: Path) -> dict[str, object]:
    """Decode global config payload from JSON or YAML.

    Args:
        path: Config file path.

    Returns:
        Parsed mapping payload.

    Raises:
        GlobalConfigError: If decode fails or payload is not an object.
    """
    raw = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix == ".json":
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise GlobalConfigError(f"Invalid global config JSON: {exc}") from exc
    elif suffix in {".yaml", ".yml"}:
        try:
            payload = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            raise GlobalConfigError(f"Invalid global config YAML: {exc}") from exc
    else:
        try:
            payload = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            raise GlobalConfigError(f"Invalid global config payload: {exc}") from exc
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise GlobalConfigError("Invalid global config payload: root must be an object")
    return payload


def load_global_config(path: Path) -> LilyGlobalConfig:
    """Load global Lily config from disk, defaulting when missing.

    Args:
        path: Config file path.

    Returns:
        Parsed config payload, or defaults when file does not exist.

    Raises:
        GlobalConfigError: If payload decode or validation fails.
    """
    if not path.exists():
        return LilyGlobalConfig()
    payload = _decode_config_payload(path)
    try:
        return LilyGlobalConfig.model_validate(payload)
    except ValidationError as exc:
        raise GlobalConfigError(f"Invalid global config payload: {exc}") from exc
