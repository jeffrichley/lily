"""Agent profile and deterministic catalog contracts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AgentProfile(BaseModel):
    """Normalized agent profile loaded from registry files."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    agent_id: str = Field(min_length=1)
    summary: str = ""
    policy: str = "safe_eval"
    declared_tools: tuple[str, ...] = ()


class AgentCatalog(BaseModel):
    """Deterministic sorted agent catalog snapshot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    agents: tuple[AgentProfile, ...] = ()

    def get(self, agent_id: str) -> AgentProfile | None:
        """Return one profile by exact agent id.

        Args:
            agent_id: Agent identifier.

        Returns:
            Matching profile when present.
        """
        for profile in self.agents:
            if profile.agent_id == agent_id:
                return profile
        return None
