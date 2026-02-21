"""Phase 5 e2e tests for security approval lifecycle surfaces."""

from __future__ import annotations

import pytest

from lily.commands.types import CommandResult


@pytest.mark.integration
def test_security_approval_required_and_deny_paths(
    monkeypatch: pytest.MonkeyPatch, e2e_env: object
) -> None:
    """Security alert codes should surface deterministic CLI alerts."""
    # Arrange - stub runtime alternating approval_required then approval_denied
    env = e2e_env

    class _StubRuntime:
        def __init__(self) -> None:
            self._count = 0

        def handle_input(self, text: str, session: object) -> CommandResult:
            del text
            del session
            self._count += 1
            if self._count == 1:
                return CommandResult.error(
                    "Approval required.",
                    code="approval_required",
                )
            return CommandResult.error(
                "Denied.",
                code="approval_denied",
            )

        def close(self) -> None:
            return

    stub = _StubRuntime()
    monkeypatch.setattr(
        "lily.cli.cli._build_runtime_for_workspace",
        lambda **_: stub,
    )
    env.init()

    # Act - invoke twice to traverse required and denied paths
    required = env.run("/skill plugin-demo run")
    denied = env.run("/skill plugin-demo run")

    # Assert - both deterministic security codes are surfaced
    assert required.exit_code == 1
    assert denied.exit_code == 1
    assert "approval_required" in required.stdout
    assert "approval_denied" in denied.stdout


@pytest.mark.integration
def test_security_run_once_always_allow_and_hash_changed_lifecycle(
    monkeypatch: pytest.MonkeyPatch, e2e_env: object
) -> None:
    """Approval lifecycle transitions should remain deterministic at CLI boundary."""
    # Arrange - stub runtime traversing run_once -> always_allow -> hash_changed
    env = e2e_env

    class _StubRuntime:
        def __init__(self) -> None:
            self._count = 0

        def handle_input(self, text: str, session: object) -> CommandResult:
            del text
            del session
            self._count += 1
            if self._count == 1:
                return CommandResult.ok("run once ok", code="tool_ok")
            if self._count == 2:
                return CommandResult.ok("always allow ok", code="tool_ok")
            return CommandResult.error(
                "Hash changed.",
                code="security_hash_mismatch",
            )

        def close(self) -> None:
            return

    stub = _StubRuntime()
    monkeypatch.setattr(
        "lily.cli.cli._build_runtime_for_workspace",
        lambda **_: stub,
    )
    env.init()

    # Act - invoke three times to step through lifecycle
    run_once = env.run("/skill plugin-demo run")
    always_allow = env.run("/skill plugin-demo run")
    hash_changed = env.run("/skill plugin-demo run")

    # Assert - run_once/always_allow succeed, hash_changed fails
    assert run_once.exit_code == 0
    assert always_allow.exit_code == 0
    assert hash_changed.exit_code == 1
    assert "run once ok" in run_once.stdout
    assert "always allow ok" in always_allow.stdout
    assert "security_hash_mismatch" in hash_changed.stdout
