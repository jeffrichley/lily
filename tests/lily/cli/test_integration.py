"""Integration tests for CLI functionality."""

from pathlib import Path
from unittest.mock import patch

from lily.cli.commands import DynamicSkillCommand
from lily.core.registry import SkillRegistry
from lily.types.models import ProjectContext, SkillInfo


class TestCLIIntegration:
    """Test CLI integration functionality."""

    def test_skill_discovery_integration_returns_completable_skill_names(
        self, tmp_path
    ):
        """Should return skill names that can be used for CLI completion."""
        # Given: project with skills
        project_root = tmp_path
        context = ProjectContext(project_root=project_root, persona="default")

        # Create skills directory and files
        skills_dir = project_root / ".lily" / "skills"
        skills_dir.mkdir(parents=True)

        skill_files = ["summarize-text.md", "brainstorm-ideas.md", "code-review.md"]
        for skill_file in skill_files:
            skill_path = skills_dir / skill_file
            skill_name = skill_file.replace(".md", "")
            skill_path.write_text(
                f"""---
name: {skill_name}
description: {skill_name} skill
tags: [test]
persona: default
kind: atomic
---

## Instructions
This is {skill_name}.
"""
            )

        # When: discover skills
        registry = SkillRegistry()
        skill_names = registry.get_skill_names(context)

        # Then: returns skill names for completion
        assert len(skill_names) == 3
        assert "summarize-text" in skill_names
        assert "brainstorm-ideas" in skill_names
        assert "code-review" in skill_names

    def test_command_creation_integration_generates_executable_commands(self):
        """Should generate executable CLI commands from discovered skills."""
        # Given: discovered skill
        skill_info = SkillInfo(
            name="test-skill",
            path=Path(".lily/skills/test-skill.md"),
            description="Test skill",
            tags=["test"],
            persona="default",
            kind="atomic",
        )

        with patch("pathlib.Path.exists", return_value=True):
            # When: create command from skill
            command = DynamicSkillCommand.create_command("test-skill", skill_info)

            # Then: generates executable command
            assert command is not None
            assert hasattr(command, "info")

    def test_end_to_end_skill_registration_workflow(self, tmp_path):
        """Should complete full workflow from discovery to command registration."""
        # Given: project with skills
        project_root = tmp_path
        context = ProjectContext(project_root=project_root, persona="default")

        # Create skill file
        skills_dir = project_root / ".lily" / "skills"
        skills_dir.mkdir(parents=True)

        skill_file = skills_dir / "test-skill.md"
        skill_file.write_text(
            """---
name: test-skill
description: Test skill
tags: [test]
persona: default
kind: atomic
---

## Instructions
This is a test skill.
"""
        )

        # When: discover skills and create commands
        registry = SkillRegistry()
        skills = registry.discover_skills(context)

        # Then: skills are discovered
        assert len(skills) == 1
        skill_info = skills[0]
        assert skill_info.name == "test-skill"

        # When: create command from discovered skill
        with patch("pathlib.Path.exists", return_value=True):
            command = DynamicSkillCommand.create_command("test-skill", skill_info)

            # Then: command is created successfully
            assert command is not None

    def test_skill_discovery_handles_mixed_valid_and_invalid_files(self, tmp_path):
        """Should handle projects with both valid and invalid skill files."""
        # Given: project with mixed file types
        project_root = tmp_path
        context = ProjectContext(project_root=project_root, persona="default")

        skills_dir = project_root / ".lily" / "skills"
        skills_dir.mkdir(parents=True)

        # Valid skill file
        valid_skill = skills_dir / "valid-skill.md"
        valid_skill.write_text(
            """---
name: valid-skill
description: Valid skill
tags: [test]
persona: default
kind: atomic
---

## Instructions
Valid skill.
"""
        )

        # Invalid files (should be ignored)
        invalid_files = [
            skills_dir / "not-a-skill.txt",
            skills_dir / "README.md",
            skills_dir / "config.yaml",
        ]

        for invalid_file in invalid_files:
            invalid_file.write_text("This is not a skill file")

        # When: discover skills
        registry = SkillRegistry()
        skills = registry.discover_skills(context)

        # Then: only valid skills are returned
        assert len(skills) == 1
        assert skills[0].name == "valid-skill"

    def test_skill_discovery_respects_project_context(self, tmp_path):
        """Should discover skills based on project context."""
        # Given: project with specific persona and modules
        project_root = tmp_path
        context = ProjectContext(
            project_root=project_root,
            persona="academic",
            modules=["research"],
            skill_overrides={},
        )

        # Create skills in different locations
        skills_dir = project_root / ".lily" / "skills"
        skills_dir.mkdir(parents=True)

        local_skill = skills_dir / "local-skill.md"
        local_skill.write_text(
            """---
name: local-skill
description: Local skill
tags: [local]
persona: default
kind: atomic
---

## Instructions
Local skill.
"""
        )

        module_skills_dir = project_root / ".lily" / "modules" / "research" / "skills"
        module_skills_dir.mkdir(parents=True)

        module_skill = module_skills_dir / "module-skill.md"
        module_skill.write_text(
            """---
name: module-skill
description: Module skill
tags: [module]
persona: academic
kind: atomic
---

## Instructions
Module skill.
"""
        )

        # When: discover skills with context
        registry = SkillRegistry()
        skills = registry.discover_skills(context)

        # Then: discovers skills from both locations
        assert len(skills) == 2
        skill_names = [skill.name for skill in skills]
        assert "local-skill" in skill_names
        assert "module-skill" in skill_names
