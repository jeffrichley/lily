"""Pydantic model for project configuration."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConfigModel(BaseModel):
    """Model representing project-level Lily configuration stored in .lily/config.json."""

    version: str = Field(..., description="Config schema version (semantic versioning)")
    project_name: str = Field(..., min_length=1, description="Project name")
    created_at: datetime = Field(
        ..., description="Config creation timestamp (ISO 8601)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "version": "0.1.0",
                "project_name": "myproject",
                "created_at": "2026-01-14T10:30:00Z",
            }
        }
    )
