"""Conformance tests for optional base tool defaults."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from lily.runtime.executors.tool_base import BaseToolContract
from lily.session.models import ModelConfig, Session
from lily.skills.types import SkillSnapshot


class _EchoOutput(BaseModel):
    """Output model for echo tool test fixture."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    display: str


class _EchoTool(BaseToolContract):
    """Echo tool overriding only execute_typed."""

    name = "echo"
    output_schema = _EchoOutput

    def execute_typed(
        self,
        typed_input: BaseModel,
        *,
        session: Session,
        skill_name: str,
    ) -> dict[str, object]:
        del session
        del skill_name
        payload = typed_input.model_dump()
        return {"display": str(payload["payload"]).upper()}


def _session() -> Session:
    """Create minimal session fixture."""
    return Session(
        session_id="contracts-tool-base",
        active_agent="default",
        skill_snapshot=SkillSnapshot(version="v-test", skills=()),
        model_config=ModelConfig(),
    )


def test_base_tool_defaults_allow_execute_only_override() -> None:
    """Tool should work by overriding execute only; parse/render defaults apply."""
    tool = _EchoTool()
    typed_input = tool.input_schema.model_validate(tool.parse_payload("hello"))
    raw_output = tool.execute_typed(typed_input, session=_session(), skill_name="echo")
    typed_output = tool.output_schema.model_validate(raw_output)

    assert tool.render_output(typed_output) == "HELLO"


def test_base_tool_default_execute_raises_not_implemented() -> None:
    """Default execute method should force explicit behavior declaration."""
    tool = BaseToolContract()
    typed_input = tool.input_schema.model_validate(tool.parse_payload("hello"))
    try:
        tool.execute_typed(
            typed_input,
            session=_session(),
            skill_name="default",
        )
    except NotImplementedError as exc:
        assert "override execute_typed" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected NotImplementedError")
