"""Agent service for deterministic selection and session updates."""

from __future__ import annotations

from lily.agents.models import AgentCatalog, AgentProfile
from lily.agents.repository import FileAgentRepository
from lily.session.models import Session


class AgentServiceError(RuntimeError):
    """Base deterministic service error."""


class AgentNotFoundError(AgentServiceError):
    """Raised when requested agent cannot be resolved."""


class AgentCatalogEmptyError(AgentServiceError):
    """Raised when an operation requires at least one registered agent."""


class AgentService:
    """Deterministic runtime service around the agent repository."""

    def __init__(self, repository: FileAgentRepository) -> None:
        """Store repository dependency.

        Args:
            repository: Agent repository implementation.
        """
        self._repository = repository

    def load_catalog(self) -> AgentCatalog:
        """Load deterministic agent catalog.

        Returns:
            Current agent catalog.
        """
        return self._repository.load_catalog()

    def list_agents(self) -> tuple[AgentProfile, ...]:
        """Return deterministic ordered agent profiles.

        Returns:
            Registered agent profiles.
        """
        return self.load_catalog().agents

    def get_agent(self, agent_id: str) -> AgentProfile | None:
        """Resolve one agent profile by normalized id.

        Args:
            agent_id: Requested agent identifier.

        Returns:
            Matching profile when present.
        """
        return self._repository.get(agent_id.strip().lower())

    def require_agent(self, agent_id: str) -> AgentProfile:
        """Resolve one agent profile or raise deterministic not-found error.

        Args:
            agent_id: Requested agent identifier.

        Returns:
            Matching profile.

        Raises:
            AgentNotFoundError: If the agent does not exist.
        """
        normalized = agent_id.strip().lower()
        profile = self.get_agent(normalized)
        if profile is None:
            raise AgentNotFoundError(f"Agent '{normalized}' was not found.")
        return profile

    def set_active_agent(self, session: Session, agent_id: str) -> AgentProfile:
        """Set the active agent in session state.

        Args:
            session: Session to mutate.
            agent_id: Requested agent identifier.

        Returns:
            Resolved agent profile.
        """
        profile = self.require_agent(agent_id)
        session.active_agent = profile.agent_id
        return profile

    def ensure_active_agent(self, session: Session) -> AgentProfile:
        """Ensure session references a valid active agent.

        Args:
            session: Session to validate/mutate.

        Returns:
            Resolved active agent profile.

        Raises:
            AgentCatalogEmptyError: If no agent profiles exist.
        """
        active = self.get_agent(session.active_agent)
        if active is not None:
            return active
        agents = self.list_agents()
        if not agents:
            raise AgentCatalogEmptyError("No agents are available.")
        session.active_agent = agents[0].agent_id
        return agents[0]
