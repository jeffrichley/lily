"""Factory pattern for creating resolvers and agents."""

from abc import ABC, abstractmethod
from typing import Any

from lily.core.registry import SkillRegistry
from lily.core.resolver import Resolver
from lily.types.models import ProjectContext


class ResolverFactory:
    """Factory for creating resolvers with configured registries."""

    @staticmethod
    def create_resolver(_context: ProjectContext) -> Resolver:
        """Create a resolver with registries configured for the given context."""
        skill_registry = SkillRegistry()
        # TODO: Add FlowRegistry and ToolRegistry when implemented
        # TODO: Configure registries based on context when needed
        return Resolver(skill_registry=skill_registry)


class AgentFactory(ABC):
    """Abstract factory for creating agents."""

    @abstractmethod
    def create_agent(self, context: ProjectContext) -> Any:
        """Create an agent for the given context."""
        pass


class PetalAgentFactory(AgentFactory):
    """Factory for creating Petal agents."""

    def create_agent(self, context: ProjectContext) -> Any:
        """Create a Petal agent for the given context."""

        # This is a placeholder implementation
        # In the real implementation, this would create a Petal agent
        # For now, we'll return a mock object
        class MockPetalAgent:
            def __init__(self, context: ProjectContext):
                self.context = context
                self.name = "MockPetalAgent"

        return MockPetalAgent(context)
