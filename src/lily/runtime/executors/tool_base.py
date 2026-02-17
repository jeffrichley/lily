"""Optional base class for deterministic tool contracts."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict

from lily.session.models import Session


class DefaultToolInput(BaseModel):
    """Default input payload schema for string-based tools."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    payload: str


class DefaultToolOutput(BaseModel):
    """Default output payload schema with display string."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    display: str
    data: dict[str, Any] | None = None


class BaseToolContract:
    """Optional tool base class with default parse/execute/render behavior."""

    name: str = "tool"
    input_schema: type[BaseModel] = DefaultToolInput
    output_schema: type[BaseModel] = DefaultToolOutput

    def parse_payload(self, payload: str) -> dict[str, Any]:
        """Parse raw payload string using default one-field contract.

        Args:
            payload: Raw user payload text.

        Returns:
            Candidate input dictionary for input schema validation.
        """
        return {"payload": payload}

    def execute_typed(
        self,
        typed_input: BaseModel,
        *,
        session: Session,
        skill_name: str,
    ) -> dict[str, Any]:
        """Execute typed tool logic.

        Args:
            typed_input: Validated input payload.
            session: Active session context.
            skill_name: Calling skill name.

        Raises:
            NotImplementedError: When subclass does not override execution behavior.
        """
        del typed_input
        del session
        del skill_name
        raise NotImplementedError("Tool must override execute_typed(...)")

    def render_output(self, typed_output: BaseModel) -> str:
        """Render output with sensible defaults.

        Args:
            typed_output: Validated output payload model.

        Returns:
            Deterministic display text.
        """
        payload = typed_output.model_dump(mode="json")
        display = payload.get("display")
        if isinstance(display, str) and display.strip():
            return display
        return json.dumps(payload, sort_keys=True)
