"""Unit tests for Lily CLI command entrypoints."""

from __future__ import annotations

from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch

from lily.cli.cli import app
from lily.commands.types import CommandResult
from tests.unit.cli.cli_shared import _RUNNER, _write_echo_skill


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
@pytest.mark.parametrize(
    ("error_code", "message"),
    (
        ("approval_required", "Approval required."),
        ("approval_denied", "Denied."),
        ("security_hash_mismatch", "Hash changed."),
    ),
)
def test_run_renders_security_alert_panel_for_approval_lifecycle_codes(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    error_code: str,
    message: str,
) -> None:
    """Security lifecycle codes should render explicit security alert panels."""
    # Arrange - temp dirs, echo skill, stub runtime returning security lifecycle code
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    _write_echo_skill(bundled_dir)

    class _StubRuntime:
        def handle_input(self, text: str, session: object) -> CommandResult:
            del text
            del session
            return CommandResult.error(message, code=error_code)

    monkeypatch.setattr(
        "lily.cli.cli._build_runtime_for_workspace",
        lambda **_: _StubRuntime(),
    )

    # Act - run plugin skill command path
    result = _RUNNER.invoke(
        app,
        [
            "run",
            "/skill plugin-demo run",
            "--bundled-dir",
            str(bundled_dir),
            "--workspace-dir",
            str(workspace_dir),
        ],
    )

    # Assert - exit 1 and security alert panel with stable code
    assert result.exit_code == 1
    assert "SECURITY ALERT" in result.stdout
    assert f"Code: {error_code}" in result.stdout
    assert message in result.stdout


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
def test_run_and_repl_render_matching_conversation_output(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Equivalent non-command input should match across run and repl surfaces."""
    # Arrange - temp dirs, echo skill, stub runtime returning conversation_reply text
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()
    _write_echo_skill(bundled_dir)

    class _StubRuntime:
        def handle_input(self, text: str, session: object) -> CommandResult:
            del session
            return CommandResult.ok(f"echo:{text}", code="conversation_reply")

        def close(self) -> None:
            return

    monkeypatch.setattr(
        "lily.cli.cli._build_runtime_for_workspace",
        lambda **_: _StubRuntime(),
    )

    # Act - send same input via run and repl
    run_result = _RUNNER.invoke(
        app,
        [
            "run",
            "same input",
            "--bundled-dir",
            str(bundled_dir),
            "--workspace-dir",
            str(workspace_dir),
        ],
    )
    repl_result = _RUNNER.invoke(
        app,
        [
            "repl",
            "--bundled-dir",
            str(bundled_dir),
            "--workspace-dir",
            str(workspace_dir),
        ],
        input="same input\nexit\n",
    )

    # Assert - both transports succeed with identical deterministic message text
    assert run_result.exit_code == 0
    assert repl_result.exit_code == 0
    assert "echo:same input" in run_result.stdout
    assert "echo:same input" in repl_result.stdout


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
