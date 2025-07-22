"""Pydantic models for Lily data structures."""

from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ProjectContext(BaseModel):
    """Project context configuration."""

    project_root: Path = Field(..., description="Root directory of the project")
    persona: str = Field(..., description="Active persona name")
    modules: List[str] = Field(default_factory=list, description="List of module names")
    skill_overrides: Dict[str, str] = Field(
        default_factory=dict, description="Skill name overrides"
    )

    @field_validator("project_root")
    @classmethod
    def validate_project_root(cls, v):
        """Validate that project root exists."""
        if not v.exists():
            raise ValueError(f"Project root {v} does not exist")
        return v


class SkillInfo(BaseModel):
    """Information about a discovered skill."""

    name: str = Field(..., description="Skill name")
    path: Path = Field(..., description="Path to skill file")
    description: Optional[str] = Field(None, description="Skill description")
    tags: List[str] = Field(default_factory=list, description="Skill tags")
    persona: Optional[str] = Field(None, description="Default persona for skill")
    kind: str = Field(..., description="Skill type (atomic, flow, etc.)")


class SkillMetadata(BaseModel):
    """Metadata for a skill."""

    name: str = Field(..., description="Skill name")
    description: str = Field(..., description="Skill description")
    personas: List[str] = Field(default_factory=list, description="Compatible personas")
    tags: List[str] = Field(default_factory=list, description="Skill tags")
    kind: str = Field(..., description="Skill type (atomic, flow, etc.)")
    tools: Optional[List[str]] = Field(default=None, description="Required tools")

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, v):
        """Validate skill kind."""
        valid_kinds = ["atomic", "flow", "composite"]
        if v not in valid_kinds:
            raise ValueError(f"Kind must be one of {valid_kinds}")
        return v


class FlowMetadata(BaseModel):
    """Metadata for a flow."""

    name: str = Field(..., description="Flow name")
    description: str = Field(..., description="Flow description")
    steps: List[Dict[str, str]] = Field(..., description="Flow steps")
    personas: List[str] = Field(default_factory=list, description="Compatible personas")
