"""Skill resolution strategies."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from lily.types.models import ProjectContext


class SkillResolutionStrategy(ABC):
    """Abstract base for skill resolution strategies."""

    @abstractmethod
    def resolve(self, name: str, context: ProjectContext) -> Optional[Path]:
        """Resolve a skill by name. Returns None if not found."""
        pass


class LocalSkillStrategy(SkillResolutionStrategy):
    """Strategy for resolving skills in local .lily/skills/ directory."""

    def resolve(self, name: str, context: ProjectContext) -> Optional[Path]:
        """Resolve skill from local skills directory."""
        skills_dir = context.project_root / ".lily" / "skills"
        skill_file = skills_dir / f"{name}.md"

        if skill_file.exists():
            return skill_file
        return None


class ModuleSkillStrategy(SkillResolutionStrategy):
    """Strategy for resolving skills in module skills directories."""

    def resolve(self, name: str, context: ProjectContext) -> Optional[Path]:
        """Resolve skill from module skills directories."""
        # Check for skill overrides first
        if name in context.skill_overrides:
            override_name = context.skill_overrides[name]
            # Handle module.skill_name format
            if "." in override_name:
                module_name, skill_name = override_name.split(".", 1)
                return self._find_in_module(module_name, skill_name, context)

        # Check in all modules
        for module_name in context.modules:
            skill_file = self._find_in_module(module_name, name, context)
            if skill_file:
                return skill_file

        return None

    def _find_in_module(
        self, module_name: str, skill_name: str, context: ProjectContext
    ) -> Optional[Path]:
        """Find skill in specific module."""
        module_skills_dir = (
            context.project_root / ".lily" / "modules" / module_name / "skills"
        )
        skill_file = module_skills_dir / f"{skill_name}.md"

        if skill_file.exists():
            return skill_file
        return None


class GlobalSkillStrategy(SkillResolutionStrategy):
    """Strategy for resolving skills in global ~/.lily/skills/ directory."""

    def resolve(self, name: str, _context: ProjectContext) -> Optional[Path]:
        """Resolve skill from global skills directory."""
        global_skills_dir = Path.home() / ".lily" / "skills"
        skill_file = global_skills_dir / f"{name}.md"

        if skill_file.exists():
            return skill_file
        return None
