"""Unit tests for CLI session recovery and init/config flows."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from lily.cli.cli import app
from tests.unit.cli.cli_shared import _RUNNER, _write_echo_skill


@pytest.mark.unit
def test_repl_recovers_corrupt_session_file(tmp_path: Path) -> None:
    """REPL should recover by moving corrupt session aside and creating new session."""
    # Arrange - temp dirs, corrupt session file, echo skill
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    session_file = tmp_path / "session.json"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    _write_echo_skill(bundled_dir)

    session_file.write_text("{not json", encoding="utf-8")

    # Act - start repl with corrupt session
    result = _RUNNER.invoke(
        app,
        [
            "repl",
            "--bundled-dir",
            str(bundled_dir),
            "--workspace-dir",
            str(workspace_dir),
            "--session-file",
            str(session_file),
        ],
        input="exit\n",
    )

    # Assert - recovery message, backup created, new valid session
    assert result.exit_code == 0
    assert "Session file was invalid." in result.stdout
    backups = list(tmp_path.glob("session.json.corrupt-*"))
    assert backups
    payload = json.loads(session_file.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1


@pytest.mark.unit
def test_repl_recovers_unsupported_schema_session_file(tmp_path: Path) -> None:
    """REPL should recover when persisted session schema version is unsupported."""
    # Arrange - temp dirs, unsupported schema session file, echo skill
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    session_file = tmp_path / "session.json"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    _write_echo_skill(bundled_dir)
    session_file.write_text(
        json.dumps({"schema_version": 999, "session": {}}),
        encoding="utf-8",
    )

    # Act - start repl with unsupported schema payload
    result = _RUNNER.invoke(
        app,
        [
            "repl",
            "--bundled-dir",
            str(bundled_dir),
            "--workspace-dir",
            str(workspace_dir),
            "--session-file",
            str(session_file),
        ],
        input="exit\n",
    )

    # Assert - recovery message, reason, backup created, new valid session
    assert result.exit_code == 0
    assert "Session file was invalid." in result.stdout
    assert "Unsupported session schema version" in result.stdout
    backups = list(tmp_path.glob("session.json.corrupt-*"))
    assert backups
    payload = json.loads(session_file.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1


@pytest.mark.unit
def test_run_creates_default_sqlite_checkpointer_file(tmp_path: Path) -> None:
    """`lily run` should initialize default sqlite checkpointer file in local mode."""
    # Arrange - workspace dirs, config with sqlite checkpointer path, echo skill
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / ".lily" / "skills"
    session_file = tmp_path / ".lily" / "session.json"
    config_file = tmp_path / ".lily" / "config.json"
    checkpointer_file = tmp_path / ".lily" / "checkpoints" / "checkpointer.sqlite"
    bundled_dir.mkdir()
    workspace_dir.mkdir(parents=True)
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(
        (
            "{"
            '"checkpointer":{'
            '"backend":"sqlite",'
            f'"sqlite_path":"{checkpointer_file.as_posix()}"'
            "}"
            "}"
        ),
        encoding="utf-8",
    )
    _write_echo_skill(bundled_dir)

    # Act - run /skills with config pointing at sqlite
    result = _RUNNER.invoke(
        app,
        [
            "run",
            "/skills",
            "--bundled-dir",
            str(bundled_dir),
            "--workspace-dir",
            str(workspace_dir),
            "--session-file",
            str(session_file),
            "--config-file",
            str(config_file),
        ],
    )

    # Assert - exit 0 and checkpointer file created
    assert result.exit_code == 0
    assert checkpointer_file.exists()


@pytest.mark.unit
def test_init_bootstraps_workspace_and_default_config(tmp_path: Path) -> None:
    """`lily init` should create workspace directories and default config file."""
    # Arrange - workspace and config paths
    workspace_dir = tmp_path / ".lily" / "skills"
    config_file = tmp_path / ".lily" / "config.yaml"

    # Act - run init
    result = _RUNNER.invoke(
        app,
        [
            "init",
            "--workspace-dir",
            str(workspace_dir),
            "--config-file",
            str(config_file),
        ],
    )

    # Assert - dirs and config created with expected backend
    assert result.exit_code == 0
    assert workspace_dir.exists()
    assert (workspace_dir.parent / "checkpoints").exists()
    assert (workspace_dir.parent / "memory").exists()
    assert config_file.exists()
    payload = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    assert payload["checkpointer"]["backend"] == "sqlite"
    assert payload["compaction"]["backend"] in {"rule_based", "langgraph_native"}


@pytest.mark.unit
def test_init_does_not_overwrite_existing_config_without_flag(tmp_path: Path) -> None:
    """`lily init` should keep existing config unless overwrite flag is set."""
    # Arrange - existing config with memory backend
    workspace_dir = tmp_path / ".lily" / "skills"
    config_file = tmp_path / ".lily" / "config.yaml"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(
        json.dumps(
            {
                "checkpointer": {
                    "backend": "memory",
                    "sqlite_path": ".lily/checkpoints/checkpointer.sqlite",
                }
            }
        ),
        encoding="utf-8",
    )

    # Act - run init without overwrite flag
    result = _RUNNER.invoke(
        app,
        [
            "init",
            "--workspace-dir",
            str(workspace_dir),
            "--config-file",
            str(config_file),
        ],
    )

    # Assert - exit 0 and config unchanged
    assert result.exit_code == 0
    payload = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    assert payload["checkpointer"]["backend"] == "memory"


@pytest.mark.unit
def test_init_uses_existing_json_config_when_yaml_missing(tmp_path: Path) -> None:
    """`lily init` should preserve legacy config.json when already present."""
    # Arrange - existing config.json with memory backend
    workspace_dir = tmp_path / ".lily" / "skills"
    config_file = tmp_path / ".lily" / "config.json"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(
        json.dumps(
            {
                "checkpointer": {
                    "backend": "memory",
                    "sqlite_path": ".lily/checkpoints/checkpointer.sqlite",
                }
            }
        ),
        encoding="utf-8",
    )

    # Act - run init with default config path
    result = _RUNNER.invoke(
        app,
        [
            "init",
            "--workspace-dir",
            str(workspace_dir),
        ],
    )

    # Assert - exit 0, no yaml created, json config unchanged
    assert result.exit_code == 0
    assert not (tmp_path / ".lily" / "config.yaml").exists()
    payload = json.loads(config_file.read_text(encoding="utf-8"))
    assert payload["checkpointer"]["backend"] == "memory"
