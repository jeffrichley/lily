"""Core resolver for skills, flows, and tools."""

from pathlib import Path
from typing import List, Optional

from lily.core.registry import SkillRegistry
from lily.types.models import ProjectContext, SkillInfo


class Resolver:
    """Facade for resolving skills, flows, and tools using unified registries."""

    def __init__(self, skill_registry: Optional[SkillRegistry] = None):
        """Initialize resolver with skill registry."""
        self._skill_registry = skill_registry or SkillRegistry()

    def resolve_skill(self, name: str, context: ProjectContext) -> Path:
        """Resolve skill using skill registry."""
        return self._skill_registry.resolve_skill(name, context)

    def resolve_flow(self, name: str, context: ProjectContext) -> Path:
        """Resolve flow (not implemented yet)."""
        raise NotImplementedError("Flow resolution not implemented yet")

    def resolve_tool(self, name: str, context: ProjectContext):
        """Resolve tool (not implemented yet)."""
        raise NotImplementedError("Tool resolution not implemented yet")

    # Convenience methods for discovery (only those actually used in production)
    def discover_skills(self, context: ProjectContext) -> List[SkillInfo]:
        """Discover all skills using skill registry."""
        return self._skill_registry.discover_skills(context)

    def validate_skill_exists(self, name: str, context: ProjectContext) -> bool:
        """Validate that a skill exists."""
        return self._skill_registry.validate_skill_exists(name, context)
