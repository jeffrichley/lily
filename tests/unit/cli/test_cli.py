"""Unit tests for Lily CLI command entrypoints."""

from __future__ import annotations

from pathlib import Path

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

    monkeypatch.setattr("lily.cli.cli._build_runtime", _StubRuntime)

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

    monkeypatch.setattr("lily.cli.cli._build_runtime", _StubRuntime)

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
