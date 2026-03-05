"""Unit tests for deterministic agent service behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from lily.agents import (
    AgentCatalogEmptyError,
    AgentNotFoundError,
    AgentService,
    FileAgentRepository,
)
from lily.session.models import ModelConfig, Session
from lily.skills.types import SkillSnapshot


def _write_agent(root: Path, name: str, summary: str = "Agent profile") -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{name}.md").write_text(
        (
            "---\n"
            f"id: {name}\n"
            f"summary: {summary}\n"
            "---\n"
            f"Agent {name} execution profile.\n"
        ),
        encoding="utf-8",
    )


def _session(*, active_persona: str = "lily", active_agent: str = "default") -> Session:
    return Session(
        session_id="session-test",
        active_persona=active_persona,
        active_agent=active_agent,
        skill_snapshot=SkillSnapshot(version="v-test", skills=()),
        model_config=ModelConfig(),
    )


@pytest.mark.unit
def test_set_active_agent_updates_only_agent_field(tmp_path: Path) -> None:
    """Service should switch active agent without mutating active persona."""
    # Arrange - service with one resolvable agent and split session context
    root = tmp_path / "agents"
    _write_agent(root, "ops")
    service = AgentService(FileAgentRepository(root_dir=root))
    session = _session(active_persona="lily", active_agent="default")

    # Act - set active runtime agent
    profile = service.set_active_agent(session, "ops")

    # Assert - only active_agent changes
    assert profile.agent_id == "ops"
    assert session.active_agent == "ops"
    assert session.active_persona == "lily"


@pytest.mark.unit
def test_set_active_agent_raises_when_agent_missing(tmp_path: Path) -> None:
    """Service should fail deterministically for missing agent id."""
    # Arrange - service without registered agents
    service = AgentService(FileAgentRepository(root_dir=tmp_path / "agents"))
    session = _session()

    # Act - request missing agent and capture deterministic error
    with pytest.raises(AgentNotFoundError) as exc:
        service.set_active_agent(session, "missing")

    # Assert - error references requested missing id
    assert "missing" in str(exc.value)


@pytest.mark.unit
def test_ensure_active_agent_selects_first_when_missing(tmp_path: Path) -> None:
    """Service should deterministically repair missing active agent."""
    # Arrange - service with sorted catalog and missing active agent in session
    root = tmp_path / "agents"
    _write_agent(root, "alpha")
    _write_agent(root, "zeta")
    service = AgentService(FileAgentRepository(root_dir=root))
    session = _session(active_agent="missing")

    # Act - ensure active agent consistency
    profile = service.ensure_active_agent(session)

    # Assert - first sorted agent is selected as deterministic fallback
    assert profile.agent_id == "alpha"
    assert session.active_agent == "alpha"


@pytest.mark.unit
def test_ensure_active_agent_raises_when_catalog_empty(tmp_path: Path) -> None:
    """Service should raise deterministic error when no agents exist."""
    # Arrange - service with empty catalog and invalid active agent
    service = AgentService(FileAgentRepository(root_dir=tmp_path / "agents"))
    session = _session(active_agent="missing")

    # Act - ensure active agent consistency with empty registry
    # Assert - deterministic empty-catalog error is raised
    with pytest.raises(AgentCatalogEmptyError):
        service.ensure_active_agent(session)
