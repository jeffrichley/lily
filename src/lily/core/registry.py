"""Unified skill registry for discovery and resolution."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set

import yaml
from rich.console import Console
from rich.logging import RichHandler

from lily.core.strategies import (
    GlobalSkillStrategy,
    LocalSkillStrategy,
    ModuleSkillStrategy,
)
from lily.types.exceptions import InvalidSkillError, SkillNotFoundError
from lily.types.models import ProjectContext, SkillInfo

# Set up rich logging
console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True)],
)
logger = logging.getLogger("lily.core.registry")


class SkillRegistry:
    """Unified registry for skill discovery and resolution."""

    def __init__(self):
        """Initialize skill registry."""
        self._cache: Dict[str, List[SkillInfo]] = {}
        self._cache_file = Path(".lily/skill_cache.yaml")

        # Initialize resolution strategies
        self._strategies = [
            LocalSkillStrategy(),
            ModuleSkillStrategy(),
            GlobalSkillStrategy(),
        ]

    def discover_skills(self, context: ProjectContext) -> List[SkillInfo]:
        """Discover all available skills with metadata."""
        cache_key = str(context.project_root)

        # Check cache first
        if cache_key in self._cache:
            logger.debug(f"Using cached skills for {cache_key}")
            return self._cache[cache_key]

        # Load from cache file if exists
        if self._cache_file.exists():
            try:
                cached_skills = self._load_cache_from_file()
                if cache_key in cached_skills:
                    logger.debug(f"Loaded skills from cache file for {cache_key}")
                    self._cache[cache_key] = cached_skills[cache_key]
                    return self._cache[cache_key]
            except Exception as e:
                logger.warning(f"Failed to load cache file: {e}")

        # Discover skills
        skills = []
        skill_names: Set[str] = set()  # Track skill names to avoid duplicates

        # Discover local skills
        local_skills = self._discover_local_skills(context)
        for skill in local_skills:
            if skill.name not in skill_names:
                skills.append(skill)
                skill_names.add(skill.name)

        # Discover module skills
        module_skills = self._discover_module_skills(context)
        for skill in module_skills:
            if skill.name not in skill_names:
                skills.append(skill)
                skill_names.add(skill.name)

        # Cache results
        self._cache[cache_key] = skills
        self._save_cache_to_file()

        logger.info(f"Discovered {len(skills)} skills")
        return skills

    def resolve_skill(self, name: str, context: ProjectContext) -> Path:
        """Resolve skill path using chain of responsibility pattern."""
        for strategy in self._strategies:
            result = strategy.resolve(name, context)
            if result:
                # Validate the skill file
                self._validate_skill_file(result)
                return result

        raise SkillNotFoundError(f"Skill '{name}' not found")

    def get_skill_info(self, name: str, context: ProjectContext) -> Optional[SkillInfo]:
        """Get skill metadata by name."""
        skills = self.discover_skills(context)
        for skill in skills:
            if skill.name == name:
                return skill
        return None

    def get_skill_names(self, context: ProjectContext) -> List[str]:
        """Get list of skill names for auto-completion."""
        skills = self.discover_skills(context)
        return [skill.name for skill in skills]

    def validate_skill_exists(self, name: str, context: ProjectContext) -> bool:
        """Validate that a skill exists."""
        return self.get_skill_info(name, context) is not None

    def _discover_local_skills(self, context: ProjectContext) -> List[SkillInfo]:
        """Discover skills from .lily/skills/ directory."""
        skills: List[SkillInfo] = []
        skills_dir = context.project_root / ".lily" / "skills"

        if not skills_dir.exists():
            logger.debug(f"Local skills directory does not exist: {skills_dir}")
            return skills

        for skill_file in skills_dir.glob("*.md"):
            try:
                skill_info = self._parse_skill_file(skill_file)
                if skill_info:
                    skills.append(skill_info)
            except Exception as e:
                logger.warning(f"Failed to parse skill file {skill_file}: {e}")

        return skills

    def _discover_module_skills(self, context: ProjectContext) -> List[SkillInfo]:
        """Discover skills from .lily/modules/*/skills/ directories."""
        skills: List[SkillInfo] = []
        modules_dir = context.project_root / ".lily" / "modules"

        if not modules_dir.exists():
            logger.debug(f"Modules directory does not exist: {modules_dir}")
            return skills

        for module_dir in modules_dir.iterdir():
            if module_dir.is_dir():
                module_skills_dir = module_dir / "skills"
                if module_skills_dir.exists():
                    for skill_file in module_skills_dir.glob("*.md"):
                        try:
                            skill_info = self._parse_skill_file(skill_file)
                            if skill_info:
                                skills.append(skill_info)
                        except Exception as e:
                            logger.warning(
                                f"Failed to parse module skill file {skill_file}: {e}"
                            )

        return skills

    def _parse_skill_file(self, skill_file: Path) -> Optional[SkillInfo]:
        """Parse a skill file and extract metadata."""
        if not skill_file.exists():
            return None

        content = skill_file.read_text()

        # Check for front matter
        if not content.startswith("---"):
            logger.debug(f"Skipping {skill_file}: no front matter")
            return None

        # Extract front matter
        lines = content.split("\n")
        front_matter_end = -1

        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                front_matter_end = i
                break

        if front_matter_end == -1:
            logger.debug(f"Skipping {skill_file}: no closing front matter")
            return None

        # Parse front matter
        front_matter_lines = lines[1:front_matter_end]
        front_matter_text = "\n".join(front_matter_lines)

        try:
            metadata = yaml.safe_load(front_matter_text)
        except yaml.YAMLError as e:
            logger.warning(f"Invalid YAML in {skill_file}: {e}")
            return None

        # Extract required fields
        name = metadata.get("name")
        if not name:
            logger.warning(f"Missing 'name' field in {skill_file}")
            return None

        # Validate that filename matches front matter name
        expected_name = skill_file.stem  # filename without extension
        if name != expected_name:
            logger.warning(
                f"Skill name '{name}' doesn't match filename '{expected_name}' in {skill_file}"
            )
            return None

        # Create SkillInfo
        return SkillInfo(
            name=name,
            path=skill_file,
            description=metadata.get("description"),
            tags=metadata.get("tags", []),
            persona=metadata.get("persona"),
            kind=metadata.get("kind", "atomic"),
        )

    def _validate_skill_file(self, skill_path: Path) -> None:
        """Validate skill file has proper structure."""
        if not skill_path.exists():
            raise InvalidSkillError(f"Skill file {skill_path} does not exist")

        content = skill_path.read_text()

        # Check for front matter
        if not content.startswith("---"):
            raise InvalidSkillError(
                f"Skill file {skill_path} must start with front matter (---)"
            )

        # Check for closing front matter
        lines = content.split("\n")

        # Find closing front matter
        front_matter_end = -1
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                front_matter_end = i
                break

        if front_matter_end == -1:
            raise InvalidSkillError(
                f"Skill file {skill_path} must have closing front matter (---)"
            )

        # Extract and validate front matter
        front_matter_lines = lines[1:front_matter_end]
        front_matter_text = "\n".join(front_matter_lines)

        # Basic validation - should contain name field
        if "name:" not in front_matter_text:
            raise InvalidSkillError(
                f"Skill file {skill_path} must contain 'name:' field in front matter"
            )

    def _load_cache_from_file(self) -> Dict[str, List[SkillInfo]]:
        """Load skills from cache file."""
        if not self._cache_file.exists():
            return {}

        try:
            with open(self._cache_file, "r") as f:
                cache_data = yaml.safe_load(f) or {}

            # Convert cached data back to SkillInfo objects
            result = {}
            for project_root, skills_data in cache_data.items():
                skills = []
                for skill_data in skills_data:
                    skill_info = SkillInfo(
                        name=skill_data["name"],
                        path=Path(skill_data["path"]),
                        description=skill_data.get("description"),
                        tags=skill_data.get("tags", []),
                        persona=skill_data.get("persona"),
                        kind=skill_data.get("kind", "atomic"),
                    )
                    skills.append(skill_info)
                result[project_root] = skills

            return result
        except Exception as e:
            logger.warning(f"Failed to load cache file: {e}")
            return {}

    def _save_cache_to_file(self) -> None:
        """Save skills to cache file."""
        try:
            # Ensure cache directory exists
            self._cache_file.parent.mkdir(parents=True, exist_ok=True)

            # Convert SkillInfo objects to serializable format
            cache_data = {}
            for project_root, skills in self._cache.items():
                skills_data = []
                for skill in skills:
                    skill_data = {
                        "name": skill.name,
                        "path": str(skill.path),
                        "description": skill.description,
                        "tags": skill.tags,
                        "persona": skill.persona,
                        "kind": skill.kind,
                    }
                    skills_data.append(skill_data)
                cache_data[project_root] = skills_data

            with open(self._cache_file, "w") as f:
                yaml.dump(cache_data, f)

        except Exception as e:
            logger.warning(f"Failed to save cache file: {e}")

    def clear_cache(self) -> None:
        """Clear the skill cache."""
        self._cache.clear()
        if self._cache_file.exists():
            self._cache_file.unlink()
        logger.info("Skill cache cleared")
