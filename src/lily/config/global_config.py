"""Global Lily config models and loading helpers."""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path

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
    TOKEN = "token"  # nosec B105 - chunker mode label, not credential data


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
    consolidation: ConsolidationSettings = ConsolidationSettings()


class GlobalConfigError(RuntimeError):
    """Raised when global config cannot be decoded or validated."""


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
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GlobalConfigError(f"Invalid global config JSON: {exc}") from exc
    try:
        return LilyGlobalConfig.model_validate(payload)
    except ValidationError as exc:
        raise GlobalConfigError(f"Invalid global config payload: {exc}") from exc
