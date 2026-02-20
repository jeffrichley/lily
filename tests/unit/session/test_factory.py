"""Unit tests for session factory."""

from __future__ import annotations

from pathlib import Path

import pytest

from lily.session.factory import SessionFactory, SessionFactoryConfig
from lily.session.models import ModelConfig
from lily.skills.types import InvocationMode, SkillSource


def _write_skill(root: Path, name: str, content: str) -> None:
    skill_dir = root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")


@pytest.mark.unit
def test_create_builds_session_with_snapshot(tmp_path: Path) -> None:
    """SessionFactory should create a session with deterministic snapshot data."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()

    _write_skill(
        bundled_dir,
        "echo",
        """---
summary: Echo skill
invocation_mode: llm_orchestration
---
# Echo
""",
    )

    factory = SessionFactory(
        SessionFactoryConfig(
            bundled_dir=bundled_dir,
            workspace_dir=workspace_dir,
            platform="linux",
            env={},
        )
    )
    session = factory.create(
        active_agent="default",
        model_config=ModelConfig(model_name="stub-model"),
        session_id="session-001",
    )

    assert session.session_id == "session-001"
    assert session.active_agent == "default"
    assert session.model_settings.model_name == "stub-model"
    assert len(session.skill_snapshot.skills) == 1

    entry = session.skill_snapshot.skills[0]
    assert entry.name == "echo"
    assert entry.source == SkillSource.BUNDLED
    assert entry.invocation_mode == InvocationMode.LLM_ORCHESTRATION


@pytest.mark.unit
def test_session_snapshot_does_not_drift_after_filesystem_changes(
    tmp_path: Path,
) -> None:
    """Existing session snapshot should remain stable even if skills on disk change."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()

    _write_skill(
        bundled_dir,
        "echo",
        """---
summary: Echo skill
invocation_mode: llm_orchestration
---
# Echo
""",
    )

    factory = SessionFactory(
        SessionFactoryConfig(
            bundled_dir=bundled_dir,
            workspace_dir=workspace_dir,
            platform="linux",
            env={},
        )
    )

    session = factory.create()
    original_names = [entry.name for entry in session.skill_snapshot.skills]

    _write_skill(
        workspace_dir,
        "new_skill",
        """---
summary: New skill
invocation_mode: llm_orchestration
---
# New
""",
    )

    names_after_fs_change = [entry.name for entry in session.skill_snapshot.skills]
    assert names_after_fs_change == original_names

    new_session = factory.create()
    new_names = [entry.name for entry in new_session.skill_snapshot.skills]
    assert new_names == ["echo", "new_skill"]
