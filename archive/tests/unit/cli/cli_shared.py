"""Shared fixtures/helpers for CLI command entrypoint tests."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

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
