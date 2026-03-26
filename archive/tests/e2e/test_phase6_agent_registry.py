"""Phase 6 e2e tests for real agent registry command behavior."""

from __future__ import annotations

from pathlib import Path

import pytest


def _write_agent(root: Path, name: str, summary: str) -> None:
    """Write one structured agent contract for e2e runtime loading.

    Args:
        root: Agent registry root path.
        name: Agent identifier.
        summary: Agent summary text.
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{name}.agent.yaml").write_text(
        (f"id: {name}\nsummary: {summary}\npolicy: safe_eval\ndeclared_tools: []\n"),
        encoding="utf-8",
    )


@pytest.mark.e2e
def test_agent_list_use_show_reads_structured_registry(e2e_env: object) -> None:
    """`/agent list|use|show` should resolve from workspace agent contracts."""
    # Arrange - workspace agent registry with two agents
    env = e2e_env
    agents_dir = env.workspace_dir.parent / "agents"
    _write_agent(agents_dir, "ops", "Operational executor")
    _write_agent(agents_dir, "research", "Research executor")
    env.init()

    # Act - list, switch, and show active agent
    listed = env.run("/agent list")
    used = env.run("/agent use research")
    shown = env.run("/agent show")

    # Assert - commands succeed and show real agent data
    assert listed.exit_code == 0
    assert "ops" in listed.stdout
    assert "research" in listed.stdout
    assert used.exit_code == 0
    assert "research" in used.stdout
    assert shown.exit_code == 0
    assert "research" in shown.stdout
    payload = env.read_session_payload()
    session = payload["session"]
    assert session["active_agent"] == "research"


@pytest.mark.e2e
def test_persona_and_agent_state_are_independent(e2e_env: object) -> None:
    """`/persona` and `/agent` commands should not mutate each other's state."""
    # Arrange - workspace agent registry and initialized workspace
    env = e2e_env
    agents_dir = env.workspace_dir.parent / "agents"
    _write_agent(agents_dir, "ops", "Operational executor")
    env.init()

    # Act - switch agent then persona in one REPL flow and inspect both
    result = env.repl(
        "/agent use ops\n/persona use chad\n/agent show\n/persona show\nexit\n"
    )

    # Assert - active agent remains ops and active persona remains chad
    assert result.exit_code == 0
    payload = env.read_session_payload()
    session = payload["session"]
    assert session["active_agent"] == "ops"
    assert session["active_persona"] == "chad"
