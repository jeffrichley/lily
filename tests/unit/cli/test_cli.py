"""Unit tests for Lily CLI command entrypoints."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
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


@pytest.mark.unit
def test_run_single_shot_skills_lists_snapshot(tmp_path: Path) -> None:
    """`lily run /skills` should output deterministic skill list."""
    # Arrange - temp dirs and echo skill
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    _write_echo_skill(bundled_dir)

    # Act - run /skills
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

    # Assert - exit 0 and skill list contains echo
    assert result.exit_code == 0
    assert "echo - Echo" in result.stdout


@pytest.mark.unit
def test_run_single_shot_renders_success(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    """`lily run` should print successful runtime result."""
    # Arrange - temp dirs, echo skill, stub runtime returning ok
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

    # Act - run skill echo hello
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

    # Assert - exit 0 and HELLO in stdout
    assert result.exit_code == 0
    assert "HELLO" in result.stdout


@pytest.mark.unit
def test_run_single_shot_renders_error_and_exit_code(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    """`lily run` should print error and return non-zero exit code."""
    # Arrange - temp dirs, echo skill, stub runtime returning error
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

    # Act - run skill echo hello
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

    # Assert - exit 1 and error message in stdout
    assert result.exit_code == 1
    assert "Error: boom" in result.stdout


@pytest.mark.unit
def test_run_renders_security_alert_panel_for_capability_denied(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    """Security-denied skill errors should render explicit alert panel."""
    # Arrange - temp dirs, echo skill, stub returning capability_denied
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    _write_echo_skill(bundled_dir)

    class _StubRuntime:
        def handle_input(self, text: str, session: object) -> CommandResult:
            del text
            del session
            return CommandResult.error(
                "Security alert: denied",
                code="skill_capability_denied",
            )

    monkeypatch.setattr(
        "lily.cli.cli._build_runtime_for_workspace",
        lambda **_: _StubRuntime(),
    )

    # Act - run skill echo hello
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

    # Assert - exit 1 and security alert panel in stdout
    assert result.exit_code == 1
    assert "Code: skill_capability_denied" in result.stdout
    assert "SECURITY ALERT" in result.stdout


@pytest.mark.unit
def test_run_renders_blueprint_diagnostic_panel_for_compile_failure(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    """Blueprint compile errors should render explicit diagnostic panel."""
    # Arrange - temp dirs, echo skill, stub returning blueprint_compile_failed
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    _write_echo_skill(bundled_dir)

    class _StubRuntime:
        def handle_input(self, text: str, session: object) -> CommandResult:
            del text
            del session
            return CommandResult.error(
                "Error: council compile failed due to unresolved specialists.",
                code="blueprint_compile_failed",
                data={"blueprint": "council.v1"},
            )

    monkeypatch.setattr(
        "lily.cli.cli._build_runtime_for_workspace",
        lambda **_: _StubRuntime(),
    )

    # Act - run jobs run with stub that returns compile failed
    result = _RUNNER.invoke(
        app,
        [
            "run",
            "/jobs run nightly_security_council",
            "--bundled-dir",
            str(bundled_dir),
            "--workspace-dir",
            str(workspace_dir),
        ],
    )

    # Assert - exit 1 and blueprint diagnostic panel in stdout
    assert result.exit_code == 1
    assert "BLUEPRINT DIAGNOSTIC" in result.stdout
    assert "Blueprint Diagnostic" in result.stdout
    assert "Code: blueprint_compile_failed" in result.stdout
    assert "registered dependencies" in result.stdout


@pytest.mark.unit
def test_run_renders_blueprint_diagnostic_panel_for_execution_failure(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    """Blueprint execution errors should render explicit diagnostic panel."""
    # Arrange - temp dirs, echo skill, stub returning blueprint_execution_failed
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    _write_echo_skill(bundled_dir)

    class _StubRuntime:
        def handle_input(self, text: str, session: object) -> CommandResult:
            del text
            del session
            return CommandResult.error(
                "Error: council execution input is invalid.",
                code="blueprint_execution_failed",
                data={"blueprint": "council.v1"},
            )

    monkeypatch.setattr(
        "lily.cli.cli._build_runtime_for_workspace",
        lambda **_: _StubRuntime(),
    )

    # Act - run jobs run with stub that returns execution failed
    result = _RUNNER.invoke(
        app,
        [
            "run",
            "/jobs run nightly_security_council",
            "--bundled-dir",
            str(bundled_dir),
            "--workspace-dir",
            str(workspace_dir),
        ],
    )

    # Assert - exit 1 and blueprint diagnostic in stdout
    assert result.exit_code == 1
    assert "BLUEPRINT DIAGNOSTIC" in result.stdout
    assert "Code: blueprint_execution_failed" in result.stdout
    assert "Review compile/execute logs" in result.stdout


@pytest.mark.unit
def test_repl_exit_parentheses_exits_cleanly(tmp_path: Path) -> None:
    """`lily repl` should treat `exit()` as clean shutdown signal."""
    # Arrange - temp dirs and echo skill
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    _write_echo_skill(bundled_dir)

    # Act - start repl and send exit()
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

    # Assert - exit 0 and bye in stdout
    assert result.exit_code == 0
    assert "bye" in result.stdout


@pytest.mark.unit
def test_run_persona_list_renders_readable_persona_output(tmp_path: Path) -> None:
    """`lily run /persona list` should render persona output without JSON blob."""
    # Arrange - temp dirs and echo skill
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    _write_echo_skill(bundled_dir)

    # Act - run /persona list
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

    # Assert - exit 0 and readable persona names without raw JSON
    assert result.exit_code == 0
    assert "Personas" in result.stdout
    assert "lily" in result.stdout
    assert "chad" in result.stdout
    assert "barbie" in result.stdout
    assert '"persona":' not in result.stdout


@pytest.mark.unit
def test_run_persona_use_renders_human_friendly_panel(tmp_path: Path) -> None:
    """`lily run /persona use` should render friendly panel instead of JSON data."""
    # Arrange - temp dirs, session file, echo skill
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    session_file = tmp_path / "session.json"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    _write_echo_skill(bundled_dir)

    # Act - run /persona use chad
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

    # Assert - exit 0 and friendly panel without raw JSON
    assert result.exit_code == 0
    assert "Persona Updated" in result.stdout
    assert "Active Persona" in result.stdout
    assert "chad" in result.stdout
    assert '"persona":' not in result.stdout


@pytest.mark.unit
def test_run_memory_show_renders_table_instead_of_json(tmp_path: Path) -> None:
    """`/memory show` should render readable memory rows without raw JSON data pane."""
    # Arrange - temp dirs, session file, echo skill
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    session_file = tmp_path / "session.json"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    _write_echo_skill(bundled_dir)

    # Act - remember then memory show
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

    # Act - memory show
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
    # Assert - exit 0 and table-style output without raw JSON
    assert shown.exit_code == 0
    assert "Memory (" in shown.stdout
    assert "favorite" in shown.stdout
    assert "royal" in shown.stdout
    assert "purple" in shown.stdout
    assert '"records":' not in shown.stdout


@pytest.mark.unit
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

    # Act - first /skills call
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
    # Assert - first run shows echo and creates session
    assert first.exit_code == 0
    assert "echo - Echo" in first.stdout
    assert session_file.exists()

    # Arrange - add demo skill to workspace
    demo_dir = workspace_dir / "demo"
    demo_dir.mkdir()
    (demo_dir / "SKILL.md").write_text(
        ("---\nsummary: Demo\ninvocation_mode: llm_orchestration\n---\n# Demo\n"),
        encoding="utf-8",
    )

    # Act - second /skills without reload
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
    # Assert - demo not in list yet
    assert second.exit_code == 0
    assert "echo - Echo" in second.stdout
    assert "demo - Demo" not in second.stdout

    # Act - reload_skills
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
