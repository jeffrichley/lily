"""Pydantic model for project state."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Phase(str, Enum):
    """Project workflow phase."""

    DISCOVERY = "DISCOVERY"
    SPEC = "SPEC"
    ARCH = "ARCH"
    # Future phases can be added here


class StateModel(BaseModel):
    """Model representing project state stored in .lily/state.json."""

    phase: Phase = Field(..., description="Current workflow phase")
    project_name: str = Field(..., min_length=1, description="Name of the project")
    created_at: datetime = Field(
        ..., description="Project creation timestamp (ISO 8601)"
    )
    last_updated: datetime = Field(
        ..., description="Last modification timestamp (ISO 8601)"
    )
    version: str = Field(
        ..., description="Lily version that created/updated the project"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "phase": "DISCOVERY",
                "project_name": "myproject",
                "created_at": "2026-01-14T10:30:00Z",
                "last_updated": "2026-01-14T10:30:00Z",
                "version": "0.1.0",
            }
        }
    )
