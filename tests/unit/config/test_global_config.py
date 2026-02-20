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
    config = load_global_config(tmp_path / "missing.json")

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
    config_path = tmp_path / "config.json"
    config_path.write_text(
        ('{"checkpointer":{"backend":"memory","sqlite_path":"ignored.sqlite"}}'),
        encoding="utf-8",
    )

    config = load_global_config(config_path)

    assert config.checkpointer.backend == CheckpointerBackend.MEMORY


@pytest.mark.unit
def test_load_global_config_reads_postgres_contract_fields(tmp_path: Path) -> None:
    """Config loader should parse postgres contract fields when provided."""
    config_path = tmp_path / "config.json"
    config_path.write_text(
        (
            "{"
            '"checkpointer":{"backend":"postgres","postgres_dsn":"postgresql://x:y@z/db"}'
            "}"
        ),
        encoding="utf-8",
    )

    config = load_global_config(config_path)

    assert config.checkpointer.backend == CheckpointerBackend.POSTGRES
    assert config.checkpointer.postgres_dsn == "postgresql://x:y@z/db"


@pytest.mark.unit
def test_load_global_config_rejects_invalid_json(tmp_path: Path) -> None:
    """Invalid JSON should raise deterministic global config error."""
    config_path = tmp_path / "config.json"
    config_path.write_text("{not-json", encoding="utf-8")

    try:
        load_global_config(config_path)
    except GlobalConfigError as exc:
        assert "Invalid global config JSON" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected GlobalConfigError")


@pytest.mark.unit
def test_load_global_config_reads_memory_tooling_flags(tmp_path: Path) -> None:
    """Config loader should parse memory tooling flags."""
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

    config = load_global_config(config_path)

    assert config.memory_tooling.enabled is True
    assert config.memory_tooling.auto_apply is True


@pytest.mark.unit
def test_load_global_config_reads_consolidation_flags(tmp_path: Path) -> None:
    """Config loader should parse consolidation flags and backend mode."""
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

    config = load_global_config(config_path)

    assert config.consolidation.enabled is True
    assert config.consolidation.backend == ConsolidationBackend.LANGMEM_MANAGER
    assert config.consolidation.llm_assisted_enabled is True
    assert config.consolidation.auto_run_every_n_turns == 3


@pytest.mark.unit
def test_load_global_config_reads_evidence_chunking_settings(tmp_path: Path) -> None:
    """Config loader should parse evidence chunking settings."""
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

    config = load_global_config(config_path)

    assert config.evidence.chunking_mode == EvidenceChunkingMode.TOKEN
    assert config.evidence.chunk_size == 512
    assert config.evidence.chunk_overlap == 64
    assert config.evidence.token_encoding_name == "cl100k_base"


@pytest.mark.unit
def test_load_global_config_reads_compaction_settings(tmp_path: Path) -> None:
    """Config loader should parse compaction backend and token budget settings."""
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

    config = load_global_config(config_path)

    assert config.compaction.backend == CompactionBackend.LANGGRAPH_NATIVE
    assert config.compaction.max_tokens == 1200


@pytest.mark.unit
def test_load_global_config_reads_yaml_payload(tmp_path: Path) -> None:
    """Config loader should parse YAML payloads."""
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

    config = load_global_config(config_path)

    assert config.checkpointer.backend == CheckpointerBackend.MEMORY


@pytest.mark.unit
def test_load_global_config_rejects_invalid_yaml(tmp_path: Path) -> None:
    """Invalid YAML should raise deterministic global config error."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text("checkpointer: [unclosed", encoding="utf-8")

    try:
        load_global_config(config_path)
    except GlobalConfigError as exc:
        assert "Invalid global config YAML" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected GlobalConfigError")


@pytest.mark.unit
def test_load_global_config_rejects_unpinned_security_image(tmp_path: Path) -> None:
    """Security sandbox image must be pinned by sha256 digest."""
    config_path = tmp_path / "config.json"
    config_path.write_text(
        '{"security":{"sandbox":{"image":"python:3.13-slim"}}}',
        encoding="utf-8",
    )

    try:
        load_global_config(config_path)
    except GlobalConfigError as exc:
        assert "pinned by sha256 digest" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected GlobalConfigError")
