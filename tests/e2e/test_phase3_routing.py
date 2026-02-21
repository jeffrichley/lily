"""Phase 3 e2e tests for routing and guardrail flows."""

from __future__ import annotations

import pytest

from lily.commands.types import CommandResult


@pytest.mark.integration
def test_tool_dispatch_success_e2e(e2e_env: object) -> None:
    """Builtin tool-dispatch should execute add skill deterministically."""
    # Arrange - bundled add skill configured for tool_dispatch
    env = e2e_env
    env.write_skill(
        root=env.bundled_dir,
        name="add",
        frontmatter={
            "summary": "Add",
            "invocation_mode": "tool_dispatch",
            "command": "add",
            "command_tool_provider": "builtin",
            "command_tool": "add",
            "capabilities": {"declared_tools": ["builtin:add"]},
        },
    )
    env.init()

    # Act - execute add command
    result = env.run("/add 5+7")

    # Assert - deterministic arithmetic output
    assert result.exit_code == 0
    assert "12" in result.stdout


@pytest.mark.integration
def test_tool_dispatch_validation_failure_e2e(e2e_env: object) -> None:
    """Invalid tool payload should return deterministic validation error."""
    # Arrange - bundled add skill configured for tool_dispatch
    env = e2e_env
    env.write_skill(
        root=env.bundled_dir,
        name="add",
        frontmatter={
            "summary": "Add",
            "invocation_mode": "tool_dispatch",
            "command": "add",
            "command_tool_provider": "builtin",
            "command_tool": "add",
            "capabilities": {"declared_tools": ["builtin:add"]},
        },
    )
    env.init()

    # Act - execute invalid payload
    result = env.run("/add bad+payload")

    # Assert - deterministic validation failure code
    assert result.exit_code == 1
    assert "invalid input for tool 'add'" in result.stdout


@pytest.mark.integration
def test_tool_dispatch_provider_error_path_e2e(e2e_env: object) -> None:
    """Unbound provider should return deterministic provider error."""
    # Arrange - bundled skill with unknown provider binding
    env = e2e_env
    env.write_skill(
        root=env.bundled_dir,
        name="badtool",
        frontmatter={
            "summary": "Bad provider",
            "invocation_mode": "tool_dispatch",
            "command": "badtool",
            "command_tool_provider": "unknown",
            "command_tool": "add",
            "capabilities": {"declared_tools": ["unknown:add"]},
        },
    )
    env.init()

    # Act - invoke skill alias
    result = env.run("/badtool 1+1")

    # Assert - provider unbound failure surfaced
    assert result.exit_code == 1
    assert "tool provider 'unknown'" in result.stdout


@pytest.mark.integration
def test_conversation_happy_path_e2e(
    monkeypatch: pytest.MonkeyPatch, e2e_env: object
) -> None:
    """Non-command text should flow through conversation path."""
    # Arrange - stub runtime that emits conversation_reply for non-slash text
    env = e2e_env

    class _StubRuntime:
        def handle_input(self, text: str, session: object) -> CommandResult:
            del session
            if text.startswith("/"):
                return CommandResult.ok("slash-ok", code="slash_ok")
            return CommandResult.ok("hello human", code="conversation_reply")

        def close(self) -> None:
            return

    monkeypatch.setattr(
        "lily.cli.cli._build_runtime_for_workspace",
        lambda **_: _StubRuntime(),
    )
    env.init()

    # Act - send non-command input
    result = env.run("hello there")

    # Assert - conversation reply rendered successfully
    assert result.exit_code == 0
    assert "hello human" in result.stdout


@pytest.mark.integration
def test_conversation_guardrail_denial_e2e(
    monkeypatch: pytest.MonkeyPatch, e2e_env: object
) -> None:
    """Guardrail denial should be surfaced deterministically."""
    # Arrange - stub runtime that emits conversation policy denial
    env = e2e_env

    class _StubRuntime:
        def handle_input(self, text: str, session: object) -> CommandResult:
            del text
            del session
            return CommandResult.error(
                "Policy denied.",
                code="conversation_policy_denied",
            )

        def close(self) -> None:
            return

    monkeypatch.setattr(
        "lily.cli.cli._build_runtime_for_workspace",
        lambda **_: _StubRuntime(),
    )
    env.init()

    # Act - send blocked input
    result = env.run("blocked prompt")

    # Assert - denial code surfaced in CLI output
    assert result.exit_code == 1
    assert "Policy denied." in result.stdout


@pytest.mark.integration
def test_multi_client_parity_run_vs_repl(
    monkeypatch: pytest.MonkeyPatch, e2e_env: object
) -> None:
    """Equivalent scripted flow should match across run and repl transports."""
    # Arrange - stub runtime shared across run/repl invocations
    env = e2e_env

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
    env.init()

    # Act - execute equivalent input via run and repl
    run_result = env.run("same input")
    repl_result = env.repl("same input\nexit\n")

    # Assert - parity in rendered output and successful exit
    assert run_result.exit_code == 0
    assert repl_result.exit_code == 0
    assert "echo:same input" in run_result.stdout
    assert "echo:same input" in repl_result.stdout
