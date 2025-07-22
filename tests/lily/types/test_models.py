"""Tests for Lily Pydantic models."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from lily.types.models import FlowMetadata, ProjectContext, SkillMetadata


class TestProjectContext:
    """Test ProjectContext Pydantic model."""

    def test_project_context_validation_valid_path(self):
        """Test that ProjectContext accepts valid project root."""
        context = ProjectContext(
            project_root=Path.cwd(),
            persona="life",
            modules=["chrona"],
            skill_overrides={"summarize": "chrona.summarize_transcript"},
        )
        assert context.project_root == Path.cwd()
        assert context.persona == "life"
        assert context.modules == ["chrona"]
        assert context.skill_overrides == {"summarize": "chrona.summarize_transcript"}

    def test_project_context_validation_invalid_path(self):
        """Test that ProjectContext rejects invalid project root."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectContext(project_root=Path("/nonexistent"), persona="life")
        assert "does not exist" in str(exc_info.value)

    def test_project_context_defaults(self):
        """Test that ProjectContext has correct defaults."""
        context = ProjectContext(project_root=Path.cwd(), persona="life")
        assert context.modules == []
        assert context.skill_overrides == {}


class TestSkillMetadata:
    """Test SkillMetadata Pydantic model."""

    def test_skill_metadata_validation_valid(self):
        """Test that SkillMetadata accepts valid data."""
        metadata = SkillMetadata(
            name="summarize-text",
            description="Summarizes text content",
            personas=["life", "research"],
            tags=["summarization", "markdown"],
            kind="atomic",
        )
        assert metadata.name == "summarize-text"
        assert metadata.description == "Summarizes text content"
        assert metadata.personas == ["life", "research"]
        assert metadata.tags == ["summarization", "markdown"]
        assert metadata.kind == "atomic"

    def test_skill_metadata_validation_invalid_kind(self):
        """Test that SkillMetadata rejects invalid kind."""
        with pytest.raises(ValidationError) as exc_info:
            SkillMetadata(
                name="summarize-text",
                description="Summarizes text content",
                kind="invalid",
            )
        assert "must be one of" in str(exc_info.value)

    def test_skill_metadata_defaults(self):
        """Test that SkillMetadata has correct defaults."""
        metadata = SkillMetadata(
            name="summarize-text", description="Summarizes text content", kind="atomic"
        )
        assert metadata.personas == []
        assert metadata.tags == []
        assert metadata.tools is None


class TestFlowMetadata:
    """Test FlowMetadata Pydantic model."""

    def test_flow_metadata_validation_valid(self):
        """Test that FlowMetadata accepts valid data."""
        metadata = FlowMetadata(
            name="summarize-and-tweet",
            description="Summarizes content and creates a tweet",
            steps=[{"skill": "summarize"}, {"skill": "write_tweet"}],
            personas=["chrona", "research"],
        )
        assert metadata.name == "summarize-and-tweet"
        assert metadata.description == "Summarizes content and creates a tweet"
        assert len(metadata.steps) == 2
        assert metadata.personas == ["chrona", "research"]

    def test_flow_metadata_defaults(self):
        """Test that FlowMetadata has correct defaults."""
        metadata = FlowMetadata(
            name="simple-flow", description="A simple flow", steps=[{"skill": "test"}]
        )
        assert metadata.personas == []
