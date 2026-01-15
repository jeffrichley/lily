"""Pydantic models for artifact index."""

from datetime import datetime
from enum import Enum
from typing import List

from pydantic import BaseModel, ConfigDict, Field, RootModel


class ArtifactType(str, Enum):
    """Type of artifact."""

    USER_FACING = "user-facing"
    SYSTEM = "system"


class ArtifactModel(BaseModel):
    """Model representing a single artifact in the index."""

    file_path: str = Field(..., description="Relative path from project root")
    artifact_type: ArtifactType = Field(..., description="Type of artifact")
    last_modified: datetime = Field(
        ..., description="Last modification timestamp (ISO 8601)"
    )
    hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="SHA-256 hash (64 hex characters)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_path": ".lily/docs/VISION.md",
                "artifact_type": "user-facing",
                "last_modified": "2026-01-14T10:30:00Z",
                "hash": "abc123def456...",
            }
        }
    )


class IndexModel(RootModel[List[ArtifactModel]]):
    """Model representing the complete artifact index as a list of artifacts."""

    root: List[ArtifactModel] = Field(
        default_factory=list, description="List of artifacts"
    )

    def __iter__(self):
        """Allow iteration over artifacts."""
        return iter(self.root)

    def __len__(self):
        """Return number of artifacts."""
        return len(self.root)

    def __getitem__(self, index):
        """Allow indexing artifacts."""
        return self.root[index]

    def append(self, artifact: ArtifactModel) -> None:
        """Add an artifact to the index."""
        self.root.append(artifact)

    model_config = ConfigDict(
        json_schema_extra={
            "example": [
                {
                    "file_path": ".lily/docs/VISION.md",
                    "artifact_type": "user-facing",
                    "last_modified": "2026-01-14T10:30:00Z",
                    "hash": "abc123...",
                }
            ]
        }
    )
