"""Tests for skill telemetry log path resolution and handlers."""

from __future__ import annotations

from pathlib import Path

import pytest

from lily.runtime.logging_setup import (
    clear_skill_telemetry_handlers,
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
