"""Unit tests for Lily CLI command entrypoints."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from _pytest.monkeypatch import MonkeyPatch
from typer.testing import CliRunner

from lily.cli.cli import app
from lily.commands.types import CommandResult

_RUNNER = CliRunner()


def _write_echo_skill(root: Path) -> None:
    """Create bundled echo skill fixture.

    Args:
        root: Bundled skills root path.
    """
    skill_dir = root / "echo"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        """---
summary: Echo
invocation_mode: llm_orchestration
---
# Echo
""",
        encoding="utf-8",
    )


def test_run_single_shot_skills_lists_snapshot(tmp_path: Path) -> None:
    """`lily run /skills` should output deterministic skill list."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    _write_echo_skill(bundled_dir)

    result = _RUNNER.invoke(
        app,
        [
            "run",
            "/skills",
            "--bundled-dir",
            str(bundled_dir),
            "--workspace-dir",
            str(workspace_dir),
        ],
    )

    assert result.exit_code == 0
    assert "echo - Echo" in result.stdout


def test_run_single_shot_renders_success(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    """`lily run` should print successful runtime result."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    _write_echo_skill(bundled_dir)

    class _StubRuntime:
        def handle_input(self, text: str, session: object) -> CommandResult:
            del text
            del session
            return CommandResult.ok("HELLO")

    monkeypatch.setattr(
        "lily.cli.cli._build_runtime_for_workspace",
        lambda **_: _StubRuntime(),
    )

    result = _RUNNER.invoke(
        app,
        [
            "run",
            "/skill echo hello",
            "--bundled-dir",
            str(bundled_dir),
            "--workspace-dir",
            str(workspace_dir),
        ],
    )

    assert result.exit_code == 0
    assert "HELLO" in result.stdout


def test_run_single_shot_renders_error_and_exit_code(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    """`lily run` should print error and return non-zero exit code."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    _write_echo_skill(bundled_dir)

    class _StubRuntime:
        def handle_input(self, text: str, session: object) -> CommandResult:
            del text
            del session
            return CommandResult.error("Error: boom")

    monkeypatch.setattr(
        "lily.cli.cli._build_runtime_for_workspace",
        lambda **_: _StubRuntime(),
    )

    result = _RUNNER.invoke(
        app,
        [
            "run",
            "/skill echo hello",
            "--bundled-dir",
            str(bundled_dir),
            "--workspace-dir",
            str(workspace_dir),
        ],
    )

    assert result.exit_code == 1
    assert "Error: boom" in result.stdout


def test_repl_exit_parentheses_exits_cleanly(tmp_path: Path) -> None:
    """`lily repl` should treat `exit()` as clean shutdown signal."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    _write_echo_skill(bundled_dir)

    result = _RUNNER.invoke(
        app,
        [
            "repl",
            "--bundled-dir",
            str(bundled_dir),
            "--workspace-dir",
            str(workspace_dir),
        ],
        input="exit()\n",
    )

    assert result.exit_code == 0
    assert "bye" in result.stdout


def test_run_persona_list_renders_readable_persona_output(tmp_path: Path) -> None:
    """`lily run /persona list` should render persona output without JSON blob."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    _write_echo_skill(bundled_dir)

    result = _RUNNER.invoke(
        app,
        [
            "run",
            "/persona list",
            "--bundled-dir",
            str(bundled_dir),
            "--workspace-dir",
            str(workspace_dir),
        ],
    )

    assert result.exit_code == 0
    assert "Personas" in result.stdout
    assert "lily" in result.stdout
    assert "chad" in result.stdout
    assert "barbie" in result.stdout
    assert '"persona":' not in result.stdout


def test_run_persona_use_renders_human_friendly_panel(tmp_path: Path) -> None:
    """`lily run /persona use` should render friendly panel instead of JSON data."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    session_file = tmp_path / "session.json"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    _write_echo_skill(bundled_dir)

    result = _RUNNER.invoke(
        app,
        [
            "run",
            "/persona use chad",
            "--bundled-dir",
            str(bundled_dir),
            "--workspace-dir",
            str(workspace_dir),
            "--session-file",
            str(session_file),
        ],
    )

    assert result.exit_code == 0
    assert "Persona Updated" in result.stdout
    assert "Active Persona" in result.stdout
    assert "chad" in result.stdout
    assert '"persona":' not in result.stdout


def test_run_memory_show_renders_table_instead_of_json(tmp_path: Path) -> None:
    """`/memory show` should render readable memory rows without raw JSON data pane."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    session_file = tmp_path / "session.json"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    _write_echo_skill(bundled_dir)

    remember = _RUNNER.invoke(
        app,
        [
            "run",
            "/remember favorite color is dark royal purple",
            "--bundled-dir",
            str(bundled_dir),
            "--workspace-dir",
            str(workspace_dir),
            "--session-file",
            str(session_file),
        ],
    )
    assert remember.exit_code == 0

    shown = _RUNNER.invoke(
        app,
        [
            "run",
            "/memory show",
            "--bundled-dir",
            str(bundled_dir),
            "--workspace-dir",
            str(workspace_dir),
            "--session-file",
            str(session_file),
        ],
    )
    assert shown.exit_code == 0
    assert "Memory (" in shown.stdout
    assert "favorite" in shown.stdout
    assert "royal" in shown.stdout
    assert "purple" in shown.stdout
    assert '"records":' not in shown.stdout


def test_run_persists_session_and_requires_reload_for_new_skills(
    tmp_path: Path,
) -> None:
    """Run mode should persist snapshot and keep it stable until /reload_skills."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    session_file = tmp_path / "session.json"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    _write_echo_skill(bundled_dir)

    first = _RUNNER.invoke(
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
        ],
    )
    assert first.exit_code == 0
    assert "echo - Echo" in first.stdout
    assert session_file.exists()

    demo_dir = workspace_dir / "demo"
    demo_dir.mkdir()
    (demo_dir / "SKILL.md").write_text(
        ("---\nsummary: Demo\ninvocation_mode: llm_orchestration\n---\n# Demo\n"),
        encoding="utf-8",
    )

    second = _RUNNER.invoke(
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
        ],
    )
    assert second.exit_code == 0
    assert "echo - Echo" in second.stdout
    assert "demo - Demo" not in second.stdout

    reload_result = _RUNNER.invoke(
        app,
        [
            "run",
            "/reload_skills",
            "--bundled-dir",
            str(bundled_dir),
            "--workspace-dir",
            str(workspace_dir),
            "--session-file",
            str(session_file),
        ],
    )
    assert reload_result.exit_code == 0
    assert "Reloaded skills for current session." in reload_result.stdout

    third = _RUNNER.invoke(
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
        ],
    )
    assert third.exit_code == 0
    assert "demo - Demo" in third.stdout


def test_repl_recovers_corrupt_session_file(tmp_path: Path) -> None:
    """REPL should recover by moving corrupt session aside and creating new session."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    session_file = tmp_path / "session.json"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    _write_echo_skill(bundled_dir)

    session_file.write_text("{not json", encoding="utf-8")

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

    assert result.exit_code == 0
    assert "Session file was invalid." in result.stdout
    backups = list(tmp_path.glob("session.json.corrupt-*"))
    assert backups
    payload = json.loads(session_file.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1


def test_run_creates_default_sqlite_checkpointer_file(tmp_path: Path) -> None:
    """`lily run` should initialize default sqlite checkpointer file in local mode."""
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

    assert result.exit_code == 0
    assert checkpointer_file.exists()


def test_init_bootstraps_workspace_and_default_config(tmp_path: Path) -> None:
    """`lily init` should create workspace directories and default config file."""
    workspace_dir = tmp_path / ".lily" / "skills"
    config_file = tmp_path / ".lily" / "config.yaml"

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

    assert result.exit_code == 0
    assert workspace_dir.exists()
    assert (workspace_dir.parent / "checkpoints").exists()
    assert (workspace_dir.parent / "memory").exists()
    assert config_file.exists()
    payload = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    assert payload["checkpointer"]["backend"] == "sqlite"
    assert payload["compaction"]["backend"] in {"rule_based", "langgraph_native"}


def test_init_does_not_overwrite_existing_config_without_flag(tmp_path: Path) -> None:
    """`lily init` should keep existing config unless overwrite flag is set."""
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

    assert result.exit_code == 0
    payload = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    assert payload["checkpointer"]["backend"] == "memory"


def test_init_uses_existing_json_config_when_yaml_missing(tmp_path: Path) -> None:
    """`lily init` should preserve legacy config.json when already present."""
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

    result = _RUNNER.invoke(
        app,
        [
            "init",
            "--workspace-dir",
            str(workspace_dir),
        ],
    )

    assert result.exit_code == 0
    assert not (tmp_path / ".lily" / "config.yaml").exists()
    payload = json.loads(config_file.read_text(encoding="utf-8"))
    assert payload["checkpointer"]["backend"] == "memory"
