"""Unit tests for global Lily config loading."""

from __future__ import annotations

from pathlib import Path

from lily.config import (
    CheckpointerBackend,
    ConsolidationBackend,
    GlobalConfigError,
    load_global_config,
)


def test_load_global_config_defaults_when_missing(tmp_path: Path) -> None:
    """Missing config file should yield deterministic defaults."""
    config = load_global_config(tmp_path / "missing.json")

    assert config.checkpointer.backend == CheckpointerBackend.SQLITE
    assert config.checkpointer.sqlite_path == ".lily/checkpoints/checkpointer.sqlite"
    assert config.memory_tooling.enabled is False
    assert config.memory_tooling.auto_apply is False
    assert config.consolidation.enabled is False
    assert config.consolidation.backend == ConsolidationBackend.RULE_BASED
    assert config.consolidation.llm_assisted_enabled is False
    assert config.consolidation.auto_run_every_n_turns == 0


def test_load_global_config_reads_custom_backend(tmp_path: Path) -> None:
    """Config loader should parse explicit backend overrides."""
    config_path = tmp_path / "config.json"
    config_path.write_text(
        ('{"checkpointer":{"backend":"memory","sqlite_path":"ignored.sqlite"}}'),
        encoding="utf-8",
    )

    config = load_global_config(config_path)

    assert config.checkpointer.backend == CheckpointerBackend.MEMORY


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
