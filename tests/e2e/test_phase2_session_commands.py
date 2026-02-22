"""Phase 2 e2e tests for session and command continuity flows."""

from __future__ import annotations

import pytest


@pytest.mark.e2e
def test_repl_restart_continuity(e2e_env: object) -> None:
    """Persona/style changes should persist across REPL restarts."""
    # Arrange - initialized workspace and first REPL session
    env = e2e_env
    env.init()

    # Act - set persona/style then reopen REPL and inspect persona state
    first = env.repl("/persona use chad\n/style playful\nexit\n")
    second = env.repl("/persona show\nexit\n")

    # Assert - persona/style survive restart
    assert first.exit_code == 0
    assert second.exit_code == 0
    assert "chad" in second.stdout
    assert "playful" in second.stdout


@pytest.mark.e2e
def test_slash_alias_command_e2e(e2e_env: object) -> None:
    """Frontmatter `command` alias should execute its mapped skill."""
    # Arrange - bundled alias skill
    env = e2e_env
    env.write_skill(
        root=env.bundled_dir,
        name="sum",
        frontmatter={
            "summary": "Sum alias",
            "invocation_mode": "tool_dispatch",
            "command": "sum",
            "command_tool_provider": "builtin",
            "command_tool": "add",
            "capabilities": {"declared_tools": ["builtin:add"]},
        },
    )
    env.init()

    # Act - invoke alias command
    result = env.run("/sum 20+42")

    # Assert - deterministic computed output
    assert result.exit_code == 0
    assert "62" in result.stdout


@pytest.mark.e2e
def test_reload_skills_after_filesystem_change(e2e_env: object) -> None:
    """`/reload_skills` should pick up newly added workspace skills."""
    # Arrange - initialized workspace with no adder skill yet
    env = e2e_env
    env.init()
    before = env.run("/skills")
    env.write_skill(
        root=env.workspace_dir,
        name="adder",
        frontmatter={
            "summary": "Workspace add",
            "invocation_mode": "tool_dispatch",
            "command": "adder",
            "command_tool_provider": "builtin",
            "command_tool": "add",
            "capabilities": {"declared_tools": ["builtin:add"]},
        },
    )
    # Act - reload skills and list again
    reload_result = env.run("/reload_skills")
    after = env.run("/skills")

    # Assert - new workspace skill appears after reload
    assert before.exit_code == 0
    assert reload_result.exit_code == 0
    assert after.exit_code == 0
    assert "adder - Workspace add" in after.stdout


@pytest.mark.e2e
def test_reload_persona_command_e2e(e2e_env: object) -> None:
    """`/reload_persona` should execute successfully for active persona repository."""
    # Arrange - initialized workspace
    env = e2e_env
    env.init()

    # Act - reload personas
    result = env.run("/reload_persona")

    # Assert - command succeeds
    assert result.exit_code == 0


@pytest.mark.e2e
def test_corrupt_session_recovery_e2e(e2e_env: object) -> None:
    """Corrupt session should be recovered with backup and new session payload."""
    # Arrange - corrupt persisted session payload
    env = e2e_env
    env.session_file.parent.mkdir(parents=True, exist_ok=True)
    env.session_file.write_text("{not json", encoding="utf-8")

    # Act - start REPL so recovery path executes
    result = env.repl("exit\n")

    # Assert - recovery message, backup file, and new session file
    assert result.exit_code == 0
    assert "Session file was invalid." in result.stdout
    backups = tuple(env.session_file.parent.glob("session.json.corrupt-*"))
    assert backups
    assert env.session_file.exists()


@pytest.mark.e2e
def test_invalid_config_falls_back_to_defaults(e2e_env: object) -> None:
    """Invalid config should warn and continue with defaults."""
    # Arrange - invalid config and one bundled skill
    env = e2e_env
    env.config_file.parent.mkdir(parents=True, exist_ok=True)
    env.config_file.write_text("{bad yaml", encoding="utf-8")
    env.write_skill(
        root=env.bundled_dir,
        name="echo",
        frontmatter={
            "summary": "Echo",
            "invocation_mode": "llm_orchestration",
        },
    )

    # Act - run a command with invalid config
    result = env.run("/skills")

    # Assert - fallback warning emitted and command still succeeds
    assert result.exit_code == 0
    assert "Global config" in result.stdout
