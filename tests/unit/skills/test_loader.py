"""Unit tests for deterministic skills loader behavior."""

from __future__ import annotations

from pathlib import Path

from lily.skills.loader import SkillSnapshotRequest, build_skill_snapshot
from lily.skills.types import SkillSource


def _write_skill(root: Path, name: str, content: str) -> None:
    """Write one skill fixture under root.

    Args:
        root: Root directory to place skill folder in.
        name: Skill folder name.
        content: `SKILL.md` content.
    """
    skill_dir = root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")


def test_loader_precedence_workspace_over_bundled(tmp_path: Path) -> None:
    """Workspace skill should win over bundled skill with same name."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()

    _write_skill(
        bundled_dir,
        "echo",
        """---
summary: bundled echo
invocation_mode: llm_orchestration
---
# Echo
""",
    )
    _write_skill(
        workspace_dir,
        "echo",
        """---
summary: workspace echo
invocation_mode: llm_orchestration
---
# Echo
""",
    )

    snapshot = build_skill_snapshot(
        SkillSnapshotRequest(
            bundled_dir=bundled_dir,
            workspace_dir=workspace_dir,
            platform="linux",
            env={},
        )
    )

    assert [entry.name for entry in snapshot.skills] == ["echo"]
    assert snapshot.skills[0].source == SkillSource.WORKSPACE
    assert snapshot.skills[0].summary == "workspace echo"
    assert any(diag.code == "precedence_conflict" for diag in snapshot.diagnostics)


def test_loader_no_fallback_when_high_precedence_ineligible(tmp_path: Path) -> None:
    """Ineligible higher-precedence winner should not fall back to bundled variant."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()

    _write_skill(
        bundled_dir,
        "echo",
        """---
summary: bundled echo
invocation_mode: llm_orchestration
---
# Echo
""",
    )
    _write_skill(
        workspace_dir,
        "echo",
        """---
summary: workspace echo ineligible on linux
invocation_mode: llm_orchestration
eligibility:
  os: [darwin]
---
# Echo
""",
    )

    snapshot = build_skill_snapshot(
        SkillSnapshotRequest(
            bundled_dir=bundled_dir,
            workspace_dir=workspace_dir,
            platform="linux",
            env={},
        )
    )

    assert [entry.name for entry in snapshot.skills] == []
    assert any(
        diag.code == "ineligible" and diag.skill_name == "echo"
        for diag in snapshot.diagnostics
    )
    assert any(diag.code == "precedence_conflict" for diag in snapshot.diagnostics)
