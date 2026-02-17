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
    assert snapshot.skills[0].instructions == "# Echo"
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


def test_loader_rejects_underdeclared_tool_capability(tmp_path: Path) -> None:
    """tool_dispatch skill should fail when command tool is undeclared."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()

    _write_skill(
        bundled_dir,
        "add",
        """---
summary: add
invocation_mode: tool_dispatch
command_tool: add
capabilities:
  declared_tools: [subtract]
---
# Add
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
        diag.code == "malformed_frontmatter" and diag.skill_name == "add"
        for diag in snapshot.diagnostics
    )


def test_loader_rejects_tool_dispatch_without_capabilities(tmp_path: Path) -> None:
    """tool_dispatch skill should fail when capabilities are missing."""
    bundled_dir = tmp_path / "bundled"
    workspace_dir = tmp_path / "workspace"
    bundled_dir.mkdir()
    workspace_dir.mkdir()

    _write_skill(
        bundled_dir,
        "add",
        """---
summary: add
invocation_mode: tool_dispatch
command_tool: add
---
# Add
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
        diag.code == "malformed_frontmatter" and diag.skill_name == "add"
        for diag in snapshot.diagnostics
    )
