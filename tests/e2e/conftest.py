"""Shared fixtures/helpers for end-to-end CLI tests."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from lily.cli.cli import app


@dataclass(frozen=True)
class E2EEnv:
    """E2E test environment with isolated workspace and CLI runner."""

    root: Path
    bundled_dir: Path
    workspace_dir: Path
    session_file: Path
    config_file: Path
    runner: CliRunner

    def init(self, *extra: str) -> object:
        """Invoke `lily init` in this test environment."""
        return self.runner.invoke(
            app,
            [
                "init",
                "--workspace-dir",
                str(self.workspace_dir),
                "--config-file",
                str(self.config_file),
                *extra,
            ],
        )

    def run(self, text: str, *extra: str) -> object:
        """Invoke `lily run` in this test environment."""
        return self.runner.invoke(
            app,
            [
                "run",
                text,
                "--bundled-dir",
                str(self.bundled_dir),
                "--workspace-dir",
                str(self.workspace_dir),
                "--session-file",
                str(self.session_file),
                "--config-file",
                str(self.config_file),
                *extra,
            ],
        )

    def repl(self, script: str, *extra: str) -> object:
        """Invoke `lily repl` in this test environment."""
        return self.runner.invoke(
            app,
            [
                "repl",
                "--bundled-dir",
                str(self.bundled_dir),
                "--workspace-dir",
                str(self.workspace_dir),
                "--session-file",
                str(self.session_file),
                "--config-file",
                str(self.config_file),
                *extra,
            ],
            input=script,
        )

    def write_skill(
        self, *, root: Path, name: str, frontmatter: dict[str, Any]
    ) -> Path:
        """Write one `SKILL.md` with frontmatter in target root."""
        skill_dir = root / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        content = (
            "---\n"
            + yaml.safe_dump(frontmatter, sort_keys=False).strip()
            + "\n---\n# "
            + name
            + "\n"
        )
        path = skill_dir / "SKILL.md"
        path.write_text(content, encoding="utf-8")
        return path

    def read_session_payload(self) -> dict[str, object]:
        """Read persisted session JSON payload."""
        return json.loads(self.session_file.read_text(encoding="utf-8"))


@pytest.fixture
def e2e_env(tmp_path: Path) -> E2EEnv:
    """Create isolated e2e workspace/bundled directories."""
    runner = CliRunner()
    root = tmp_path / "env"
    bundled_dir = root / "bundled"
    workspace_dir = root / "workspace" / "skills"
    session_file = root / "workspace" / "session.json"
    config_file = root / "workspace" / "config.yaml"
    bundled_dir.mkdir(parents=True, exist_ok=True)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    return E2EEnv(
        root=root,
        bundled_dir=bundled_dir,
        workspace_dir=workspace_dir,
        session_file=session_file,
        config_file=config_file,
        runner=runner,
    )
