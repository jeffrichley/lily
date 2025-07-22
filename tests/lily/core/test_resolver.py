"""Tests for skill resolution functionality."""

from pathlib import Path

import pytest

from lily.core.resolver import Resolver
from lily.types.exceptions import InvalidSkillError, SkillNotFoundError
from lily.types.models import ProjectContext


class TestResolver:
    """Test skill resolution functionality."""

    def setup_method(self):
        """Set up test context."""
        # Use current directory as base for tests
        self.base_path = Path.cwd()

    def _create_context_for_path(self, project_path: Path) -> ProjectContext:
        """Create context for a specific project path."""
        return ProjectContext(
            project_root=project_path,
            persona="life",
            modules=["chrona"],
            skill_overrides={"summarize": "chrona.summarize_transcript"},
        )

    def test_resolve_skill_returns_path_for_existing_skill(self, tmp_path):
        """Should return the path to an existing skill."""
        # Given: skill exists in local directory
        skills_dir = tmp_path / ".lily" / "skills"
        skills_dir.mkdir(parents=True)
        skill_file = skills_dir / "summarize-text.md"
        skill_file.write_text("---\nname: summarize-text\n---\n")

        resolver = Resolver()  # Uses default registry
        context = self._create_context_for_path(tmp_path)

        # When: resolve_skill() called
        result = resolver.resolve_skill("summarize-text", context)

        # Then: returns path to existing skill
        assert result == skill_file

    def test_resolve_skill_handles_skill_overrides(self, tmp_path):
        """Should resolve skills according to override configuration."""
        # Given: skill override is configured
        module_skills_dir = tmp_path / ".lily" / "modules" / "chrona" / "skills"
        module_skills_dir.mkdir(parents=True)
        skill_file = module_skills_dir / "summarize_transcript.md"
        skill_file.write_text("---\nname: summarize_transcript\n---\n")

        resolver = Resolver()  # Uses default registry
        context = self._create_context_for_path(tmp_path)

        # When: resolve_skill() called with override
        result = resolver.resolve_skill("summarize", context)

        # Then: returns path to overridden skill
        assert result == skill_file

    def test_resolve_skill_raises_error_for_nonexistent_skill(self):
        """Should raise error when skill doesn't exist."""
        resolver = Resolver()  # Uses default registry
        context = self._create_context_for_path(self.base_path)

        # When/Then: resolve_skill() raises error for non-existent skill
        with pytest.raises(SkillNotFoundError) as exc_info:
            resolver.resolve_skill("nonexistent", context)
        assert "Skill 'nonexistent' not found" in str(exc_info.value)

    def test_resolve_skill_finds_skill_in_priority_order(self, tmp_path):
        """Should find skills in configured priority order."""
        # Given: skill exists in global location (lowest priority)
        global_skills_dir = Path.home() / ".lily" / "skills"
        global_skills_dir.mkdir(parents=True, exist_ok=True)
        skill_file = global_skills_dir / "global-skill.md"
        skill_file.write_text("---\nname: global-skill\n---\n")

        resolver = Resolver()  # Uses default registry

        # When: resolve_skill() called
        result = resolver.resolve_skill(
            "global-skill", self._create_context_for_path(tmp_path)
        )

        # Then: returns path to skill found in global location
        assert result == skill_file

        # Clean up
        skill_file.unlink()
        global_skills_dir.rmdir()

    def test_resolve_skill_validates_skill_structure(self, tmp_path):
        """Should reject skills with invalid structure."""
        # Given: skill file with invalid front matter
        skills_dir = tmp_path / ".lily" / "skills"
        skills_dir.mkdir(parents=True)
        skill_file = skills_dir / "invalid-skill.md"
        skill_file.write_text("---\ninvalid: yaml\n---\n")

        resolver = Resolver()  # Uses default registry
        context = self._create_context_for_path(tmp_path)

        # When/Then: resolve_skill() raises error for invalid skill
        with pytest.raises(InvalidSkillError) as exc_info:
            resolver.resolve_skill("invalid-skill", context)
        assert "must contain 'name:' field" in str(exc_info.value)

    def test_resolve_skill_handles_missing_skill_files(self, tmp_path):
        """Should handle cases where skill file doesn't exist."""
        # Given: skill directory exists but file is missing
        skills_dir = tmp_path / ".lily" / "skills"
        skills_dir.mkdir(parents=True)
        # Note: No skill file created

        resolver = Resolver()  # Uses default registry
        context = self._create_context_for_path(tmp_path)

        # When/Then: resolve_skill() raises error for missing file
        with pytest.raises(SkillNotFoundError):
            resolver.resolve_skill("missing-skill", context)
