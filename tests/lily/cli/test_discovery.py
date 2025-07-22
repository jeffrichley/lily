"""Tests for skill discovery functionality."""

from lily.core.registry import SkillRegistry
from lily.types.models import ProjectContext


class TestSkillRegistry:
    """Test skill discovery functionality."""

    def test_discover_skills_returns_all_valid_skills(self, tmp_path):
        """Should return all valid skills from project."""
        # Given: multiple valid skills exist in different locations
        project_root = tmp_path
        context = ProjectContext(project_root=project_root, persona="default")

        # Create local skill
        skills_dir = project_root / ".lily" / "skills"
        skills_dir.mkdir(parents=True)
        local_skill = skills_dir / "summarize-text.md"
        local_skill.write_text(
            """---
name: summarize-text
description: Summarize text content
tags: [text, summary]
persona: default
kind: atomic
---

## Instructions
Summarize the provided text.
"""
        )

        # Create module skill
        module_skills_dir = project_root / ".lily" / "modules" / "research" / "skills"
        module_skills_dir.mkdir(parents=True)
        module_skill = module_skills_dir / "cite-paper.md"
        module_skill.write_text(
            """---
name: cite-paper
description: Generate citations for papers
tags: [research, citation]
persona: academic
kind: atomic
---

## Instructions
Generate proper citations for academic papers.
"""
        )

        # When: discover_skills() called
        registry = SkillRegistry()
        skills = registry.discover_skills(context)

        # Then: returns all valid skills with correct metadata
        assert len(skills) == 2

        skill_names = [skill.name for skill in skills]
        assert "summarize-text" in skill_names
        assert "cite-paper" in skill_names

        # Verify skill metadata is correctly parsed
        summarize_skill = next(s for s in skills if s.name == "summarize-text")
        assert summarize_skill.description == "Summarize text content"
        assert "text" in summarize_skill.tags
        assert summarize_skill.persona == "default"

    def test_discover_skills_ignores_invalid_files(self, tmp_path):
        """Should only return skills with valid front matter."""
        # Given: mix of valid and invalid skill files
        project_root = tmp_path
        context = ProjectContext(project_root=project_root, persona="default")

        skills_dir = project_root / ".lily" / "skills"
        skills_dir.mkdir(parents=True)

        # Valid skill
        valid_skill = skills_dir / "valid-skill.md"
        valid_skill.write_text(
            """---
name: valid-skill
description: A valid skill
tags: [test]
persona: default
kind: atomic
---

## Instructions
This is valid.
"""
        )

        # Invalid files (should be ignored)
        invalid_files = [
            skills_dir / "no-front-matter.txt",
            skills_dir / "incomplete-front-matter.md",
            skills_dir / "missing-name.md",
        ]

        invalid_files[0].write_text("No front matter at all")
        invalid_files[1].write_text("---\nname: incomplete\n# Missing closing ---")
        invalid_files[2].write_text("---\ndescription: missing name\n---\n")

        # When: discover_skills() called
        registry = SkillRegistry()
        skills = registry.discover_skills(context)

        # Then: only valid skills are returned
        assert len(skills) == 1
        assert skills[0].name == "valid-skill"

    def test_discover_skills_deduplicates_by_name(self, tmp_path):
        """Should return unique skills when duplicates exist."""
        # Given: same skill exists in multiple locations
        project_root = tmp_path
        context = ProjectContext(project_root=project_root, persona="default")

        # Create duplicate skills with same name
        skills_dir = project_root / ".lily" / "skills"
        skills_dir.mkdir(parents=True)

        local_skill = skills_dir / "duplicate-skill.md"
        local_skill.write_text(
            """---
name: duplicate-skill
description: Local version
tags: [local]
persona: default
kind: atomic
---

## Instructions
Local version.
"""
        )

        module_skills_dir = project_root / ".lily" / "modules" / "test" / "skills"
        module_skills_dir.mkdir(parents=True)

        module_skill = module_skills_dir / "duplicate-skill.md"
        module_skill.write_text(
            """---
name: duplicate-skill
description: Module version
tags: [module]
persona: default
kind: atomic
---

## Instructions
Module version.
"""
        )

        # When: discover_skills() called
        registry = SkillRegistry()
        skills = registry.discover_skills(context)

        # Then: only one skill with that name is returned
        assert len(skills) == 1
        assert skills[0].name == "duplicate-skill"

    def test_get_skill_names_returns_skill_names_for_completion(self, tmp_path):
        """Should return skill names for CLI auto-completion."""
        # Given: multiple skills exist
        project_root = tmp_path
        context = ProjectContext(project_root=project_root, persona="default")

        skills_dir = project_root / ".lily" / "skills"
        skills_dir.mkdir(parents=True)

        # Create multiple skills
        for skill_name in ["summarize-text", "brainstorm-ideas", "code-review"]:
            skill_file = skills_dir / f"{skill_name}.md"
            skill_file.write_text(
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

        # When: get_skill_names() called
        registry = SkillRegistry()
        skill_names = registry.get_skill_names(context)

        # Then: returns list of skill names for completion
        assert len(skill_names) == 3
        assert "summarize-text" in skill_names
        assert "brainstorm-ideas" in skill_names
        assert "code-review" in skill_names

    def test_validate_skill_exists_confirms_skill_exists(self, tmp_path):
        """Should confirm when a skill exists for command validation."""
        # Given: valid skill exists
        project_root = tmp_path
        context = ProjectContext(project_root=project_root, persona="default")

        skills_dir = project_root / ".lily" / "skills"
        skills_dir.mkdir(parents=True)

        skill_file = skills_dir / "valid-skill.md"
        skill_file.write_text(
            """---
name: valid-skill
description: A valid skill
tags: [test]
persona: default
kind: atomic
---

## Instructions
This is valid.
"""
        )

        # When: validate_skill_exists() called
        registry = SkillRegistry()
        is_valid = registry.validate_skill_exists("valid-skill", context)

        # Then: returns True for existing skill
        assert is_valid is True

    def test_validate_skill_exists_rejects_nonexistent_skill(self, tmp_path):
        """Should reject non-existent skills for command validation."""
        # Given: no skills exist
        project_root = tmp_path
        context = ProjectContext(project_root=project_root, persona="default")

        # When: validate_skill_exists() called
        registry = SkillRegistry()
        is_valid = registry.validate_skill_exists("non-existent-skill", context)

        # Then: returns False for non-existent skill
        assert is_valid is False

    def test_discover_skills_rejects_mismatched_filename_and_name(self, tmp_path):
        """Should reject skills where filename doesn't match front matter name."""
        # Given: skill file with mismatched name
        project_root = tmp_path
        context = ProjectContext(project_root=project_root, persona="default")

        skills_dir = project_root / ".lily" / "skills"
        skills_dir.mkdir(parents=True)

        # File named "demo-skill.md" but front matter says "different-name"
        skill_file = skills_dir / "demo-skill.md"
        skill_file.write_text(
            """---
name: different-name
description: A skill with mismatched name
tags: [test]
persona: default
kind: atomic
---

## Instructions
This skill has a mismatched name.
"""
        )

        # When: discover_skills() called
        registry = SkillRegistry()
        skills = registry.discover_skills(context)

        # Then: skill is rejected due to name mismatch
        assert len(skills) == 0
