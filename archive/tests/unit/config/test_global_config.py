"""Unit tests for global Lily config loading."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from lily.config import (
    CheckpointerBackend,
    CompactionBackend,
    ConsolidationBackend,
    EvidenceChunkingMode,
    GlobalConfigError,
    load_global_config,
)


@pytest.mark.unit
def test_load_global_config_defaults_when_missing(tmp_path: Path) -> None:
    """Missing config file should yield deterministic defaults."""
    # Arrange - path to non-existent config
    # Act - load config
    config = load_global_config(tmp_path / "missing.json")

    # Assert - defaults for checkpointer, memory, evidence, compaction, security
    assert config.checkpointer.backend == CheckpointerBackend.SQLITE
    assert config.checkpointer.sqlite_path == ".lily/checkpoints/checkpointer.sqlite"
    assert config.memory_tooling.enabled is False
    assert config.memory_tooling.auto_apply is False
    assert config.evidence.chunking_mode == EvidenceChunkingMode.RECURSIVE
    assert config.evidence.chunk_size == 360
    assert config.evidence.chunk_overlap == 40
    assert config.evidence.token_encoding_name == "cl100k_base"
    assert config.compaction.backend == CompactionBackend.LANGGRAPH_NATIVE
    assert config.compaction.max_tokens == 1000
    assert config.consolidation.enabled is False
    assert config.consolidation.backend == ConsolidationBackend.RULE_BASED
    assert config.consolidation.llm_assisted_enabled is False
    assert config.consolidation.auto_run_every_n_turns == 0
    assert config.security.sandbox.sqlite_path == ".lily/db/security.sqlite"
    assert config.security.sandbox.image.startswith("python:3.13-slim@sha256:")


@pytest.mark.unit
def test_load_global_config_reads_custom_backend(tmp_path: Path) -> None:
    """Config loader should parse explicit backend overrides."""
    # Arrange - config file with memory backend
    config_path = tmp_path / "config.json"
    config_path.write_text(
        ('{"checkpointer":{"backend":"memory","sqlite_path":"ignored.sqlite"}}'),
        encoding="utf-8",
    )

    # Act - load config
    config = load_global_config(config_path)

    # Assert - checkpointer backend is memory
    assert config.checkpointer.backend == CheckpointerBackend.MEMORY


@pytest.mark.unit
@pytest.mark.parametrize(
    ("filename", "content", "expected_fragments"),
    [
        (
            "config.json",
            '{"checkpointer":{"backend":"postgres"}}',
            ("checkpointer.backend", "sqlite", "memory"),
        ),
        (
            "config.json",
            "{not-json",
            ("Invalid global config JSON",),
        ),
        (
            "config.yaml",
            "checkpointer: [unclosed",
            ("Invalid global config YAML",),
        ),
        (
            "config.json",
            '{"security":{"sandbox":{"image":"python:3.13-slim"}}}',
            ("pinned by sha256 digest",),
        ),
    ],
)
def test_load_global_config_rejects_invalid_payloads(
    tmp_path: Path,
    filename: str,
    content: str,
    expected_fragments: tuple[str, ...],
) -> None:
    """Invalid payloads should raise deterministic global config errors."""
    # Arrange - config file with invalid payload.
    config_path = tmp_path / filename
    config_path.write_text(content, encoding="utf-8")

    # Act - load config and capture deterministic error.
    with pytest.raises(GlobalConfigError) as exc_info:
        load_global_config(config_path)
    # Assert - all expected message fragments are present.
    message = str(exc_info.value)
    for fragment in expected_fragments:
        assert fragment in message


@pytest.mark.unit
def test_load_global_config_reads_memory_tooling_flags(tmp_path: Path) -> None:
    """Config loader should parse memory tooling flags."""
    # Arrange - config with memory_tooling enabled and auto_apply
    config_path = tmp_path / "config.json"
    config_path.write_text(
        (
            "{"
            '"memory_tooling":{"enabled":true,"auto_apply":true},'
            '"checkpointer":{"backend":"sqlite","sqlite_path":".lily/checkpoints/checkpointer.sqlite"}'
            "}"
        ),
        encoding="utf-8",
    )

    # Act - load config
    config = load_global_config(config_path)

    # Assert - memory_tooling flags set
    assert config.memory_tooling.enabled is True
    assert config.memory_tooling.auto_apply is True


@pytest.mark.unit
def test_load_global_config_reads_consolidation_flags(tmp_path: Path) -> None:
    """Config loader should parse consolidation flags and backend mode."""
    # Arrange - config with consolidation enabled and langmem_manager
    config_path = tmp_path / "config.json"
    config_path.write_text(
        (
            "{"
            '"consolidation":{"enabled":true,"backend":"langmem_manager","llm_assisted_enabled":true,"auto_run_every_n_turns":3},'
            '"checkpointer":{"backend":"sqlite","sqlite_path":".lily/checkpoints/checkpointer.sqlite"}'
            "}"
        ),
        encoding="utf-8",
    )

    # Act - load config
    config = load_global_config(config_path)

    # Assert - consolidation settings
    assert config.consolidation.enabled is True
    assert config.consolidation.backend == ConsolidationBackend.LANGMEM_MANAGER
    assert config.consolidation.llm_assisted_enabled is True
    assert config.consolidation.auto_run_every_n_turns == 3


@pytest.mark.unit
def test_load_global_config_reads_evidence_chunking_settings(tmp_path: Path) -> None:
    """Config loader should parse evidence chunking settings."""
    # Arrange - config with evidence token chunking settings
    config_path = tmp_path / "config.json"
    config_path.write_text(
        (
            "{"
            '"evidence":{"chunking_mode":"token","chunk_size":512,'
            '"chunk_overlap":64,"token_encoding_name":"cl100k_base"},'
            '"checkpointer":{"backend":"sqlite","sqlite_path":".lily/checkpoints/checkpointer.sqlite"}'
            "}"
        ),
        encoding="utf-8",
    )

    # Act - load config
    config = load_global_config(config_path)

    # Assert - evidence chunking mode and sizes
    assert config.evidence.chunking_mode == EvidenceChunkingMode.TOKEN
    assert config.evidence.chunk_size == 512
    assert config.evidence.chunk_overlap == 64
    assert config.evidence.token_encoding_name == "cl100k_base"


@pytest.mark.unit
def test_load_global_config_reads_compaction_settings(tmp_path: Path) -> None:
    """Config loader should parse compaction backend and token budget settings."""
    # Arrange - config with compaction backend and max_tokens
    config_path = tmp_path / "config.json"
    config_path.write_text(
        (
            "{"
            '"compaction":{"backend":"langgraph_native","max_tokens":1200},'
            '"checkpointer":{"backend":"sqlite","sqlite_path":".lily/checkpoints/checkpointer.sqlite"}'
            "}"
        ),
        encoding="utf-8",
    )

    # Act - load config
    config = load_global_config(config_path)

    # Assert - compaction backend and max_tokens
    assert config.compaction.backend == CompactionBackend.LANGGRAPH_NATIVE
    assert config.compaction.max_tokens == 1200


@pytest.mark.unit
def test_load_global_config_reads_yaml_payload(tmp_path: Path) -> None:
    """Config loader should parse YAML payloads."""
    # Arrange - yaml config file with memory backend
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "checkpointer": {
                    "backend": "memory",
                    "sqlite_path": ".lily/checkpoints/checkpointer.sqlite",
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    # Act - load config
    config = load_global_config(config_path)

    # Assert - checkpointer backend memory
    assert config.checkpointer.backend == CheckpointerBackend.MEMORY
