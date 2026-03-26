"""Tests for skill telemetry log path resolution and handlers."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from lily.runtime.logging_setup import (
    clear_skill_telemetry_handlers,
    configure_lily_package_logging,
    configure_skill_telemetry_handlers,
    resolve_skill_telemetry_log_path,
)
from lily.runtime.skill_events import emit_skill_selected

pytestmark = pytest.mark.unit


def test_resolve_skill_telemetry_default_path(tmp_path: Path) -> None:
    """Default log path sits beside the config directory under ``logs``."""
    # Arrange - runtime config under tmp_path/config/
    cfg = tmp_path / "config" / "agent.toml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text("schema_version = 1\n", encoding="utf-8")
    # Act - resolve with no override
    resolved = resolve_skill_telemetry_log_path(cfg, relative_override=None)
    # Assert - file lives at tmp_path/logs/skill-telemetry.jsonl
    assert resolved == (tmp_path / "logs" / "skill-telemetry.jsonl").resolve()


def test_resolve_skill_telemetry_relative_override(tmp_path: Path) -> None:
    """Optional override resolves relative to the runtime config directory."""
    # Arrange - agent.toml at tmp_path root
    cfg = tmp_path / "agent.toml"
    cfg.write_text("schema_version = 1\n", encoding="utf-8")
    # Act - resolve with a nested relative path
    resolved = resolve_skill_telemetry_log_path(
        cfg,
        relative_override="custom/telemetry.jsonl",
    )
    # Assert - path is under tmp_path/custom/
    assert resolved == (tmp_path / "custom" / "telemetry.jsonl").resolve()


def test_configure_skill_telemetry_handlers_writes_jsonl(tmp_path: Path) -> None:
    """File handler records one JSON line per telemetry emit."""
    # Arrange - destination log and clean handler state after prior tests
    log_path = tmp_path / "skill-telemetry.jsonl"
    # Act - install handler, emit one event, tear down handlers
    try:
        configure_skill_telemetry_handlers(log_path, echo_to_stderr=False)
        emit_skill_selected(requested_name="demo", reference_subpath=None)
    finally:
        clear_skill_telemetry_handlers()
    # Assert - JSONL contains the event type and skill name
    body = log_path.read_text(encoding="utf-8")
    assert "skill_selected" in body
    assert "demo" in body


def test_configure_lily_package_logging_sets_descendant_effective_level() -> None:
    """``lily.*`` loggers inherit ``[logging].level`` from the ``lily`` parent."""
    # Arrange - clean ``lily`` root after any prior tests
    try:
        # Act - set package threshold to ERROR; child logger uses default NOTSET
        configure_lily_package_logging("ERROR")
        child = logging.getLogger("lily.runtime.unit_test_probe")
        # Assert - child inherits effective ERROR from ``lily`` parent
        assert child.level == logging.NOTSET
        assert child.getEffectiveLevel() == logging.ERROR
    finally:
        logging.getLogger("lily").setLevel(logging.NOTSET)


def test_skill_telemetry_still_emits_when_lily_package_level_is_error(
    tmp_path: Path,
) -> None:
    """Telemetry logger keeps INFO emission when package level is ERROR."""
    # Arrange - ERROR on ``lily`` plus telemetry file handler only
    log_path = tmp_path / "telemetry.jsonl"
    try:
        configure_lily_package_logging("ERROR")
        configure_skill_telemetry_handlers(log_path, echo_to_stderr=False)
        # Act - emit one retrieval-selected telemetry record
        emit_skill_selected(requested_name="probe", reference_subpath=None)
        # Assert - JSONL still receives the line despite package ERROR
        body = log_path.read_text(encoding="utf-8")
        assert "skill_selected" in body
        assert "probe" in body
    finally:
        clear_skill_telemetry_handlers()
        logging.getLogger("lily").setLevel(logging.NOTSET)
