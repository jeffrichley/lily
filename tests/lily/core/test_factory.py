"""Tests for Lily factory pattern."""

from pathlib import Path

import pytest

from lily.core.factory import AgentFactory, PetalAgentFactory, ResolverFactory
from lily.types.models import ProjectContext


class TestResolverFactory:
    """Test ResolverFactory class."""

    def test_resolver_factory_creates_working_resolver(self, tmp_path):
        """Should create a resolver that can actually resolve skills."""
        # Given: project with skills and context
        context = ProjectContext(project_root=tmp_path, persona="default", modules=[])

        # Create a skill file
        skills_dir = tmp_path / ".lily" / "skills"
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
Test skill.
"""
        )

        # When: create resolver using factory
        resolver = ResolverFactory.create_resolver(context)

        # Then: resolver can actually resolve skills
        result_path = resolver.resolve_skill("test-skill", context)
        assert result_path == skill_file

    def test_resolver_factory_creates_resolver_with_default_registry(self):
        """Should create resolver with default SkillRegistry when none provided."""
        context = ProjectContext(project_root=Path.cwd(), persona="default", modules=[])

        # When: create resolver without specifying registry
        resolver = ResolverFactory.create_resolver(context)

        # Then: resolver has a working skill registry
        assert resolver is not None
        # Test that it can discover skills (even if none exist)
        skills = resolver.discover_skills(context)
        assert isinstance(skills, list)

    def test_resolver_factory_handles_context_parameters(self, tmp_path):
        """Should create resolver that respects context parameters."""
        # Given: context with specific modules and overrides
        context = ProjectContext(
            project_root=tmp_path,
            persona="academic",
            modules=["research", "chrona"],
            skill_overrides={"summarize": "chrona.summarize_transcript"},
        )

        # When: create resolver with context
        resolver = ResolverFactory.create_resolver(context)

        # Then: resolver is created successfully
        assert resolver is not None
        # Note: Testing actual resolution would require setting up module skills
        # This test verifies the factory doesn't crash with complex contexts


class TestAgentFactory:
    """Test AgentFactory abstract class."""

    def test_agent_factory_is_abstract(self):
        """Should not allow instantiation of abstract factory."""
        with pytest.raises(TypeError):
            AgentFactory()  # type: ignore[abstract]


class TestPetalAgentFactory:
    """Test PetalAgentFactory class."""

    def test_petal_agent_factory_creates_agent_with_context(self):
        """Should create agent that receives and stores context."""
        context = ProjectContext(
            project_root=Path.cwd(), persona="default", modules=["chrona"]
        )

        factory = PetalAgentFactory()
        agent = factory.create_agent(context)

        # Then: agent has correct context and properties
        assert agent is not None
        assert agent.context == context
        assert agent.name == "MockPetalAgent"

    def test_petal_agent_factory_creates_different_agents_for_different_contexts(self):
        """Should create distinct agents for different contexts."""
        context1 = ProjectContext(
            project_root=Path.cwd(), persona="default", modules=["chrona"]
        )
        context2 = ProjectContext(
            project_root=Path.cwd(), persona="academic", modules=["research"]
        )

        factory = PetalAgentFactory()
        agent1 = factory.create_agent(context1)
        agent2 = factory.create_agent(context2)

        # Then: agents are distinct and have correct contexts
        assert agent1 is not agent2
        assert agent1.context == context1
        assert agent2.context == context2
