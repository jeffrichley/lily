"""Pydantic model for log entries."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class LogAction(str, Enum):
    """Action type for log entries."""

    CREATED = "created"
    SKIPPED = "skipped"
    REPAIRED = "repaired"
    FAILED = "failed"


class LogEntryModel(BaseModel):
    """Model representing a single log entry in both log.jsonl and log.md."""

    timestamp: datetime = Field(..., description="ISO 8601 format timestamp")
    command: str = Field(..., min_length=1, description="Command name (e.g., 'init')")
    action: LogAction = Field(..., description="Action type")
    files: List[str] = Field(
        default_factory=list, description="List of file paths affected"
    )
    metadata: Optional[Dict[str, str]] = Field(
        default=None,
        description="Additional context (project_name, phase, error messages, etc.)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "timestamp": "2026-01-14T10:30:00Z",
                "command": "init",
                "action": "created",
                "files": [".lily/docs/VISION.md", ".lily/state.json"],
                "metadata": {"project_name": "myproject", "phase": "DISCOVERY"},
            }
        }
    )
