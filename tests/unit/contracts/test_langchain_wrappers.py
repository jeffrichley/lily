"""Conformance tests for LangChain/Lily tool wrapper adapters."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ConfigDict

from lily.runtime.executors.langchain_wrappers import (
    LangChainToLilyTool,
    LilyToLangChainTool,
    invoke_langchain_wrapper_with_envelope,
)
from lily.runtime.executors.tool_base import BaseToolContract
from lily.session.models import ModelConfig, Session
from lily.skills.types import SkillSnapshot


class _SessionInput(BaseModel):
    """Input model for lily-to-langchain adapter fixture."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    left: int
    right: int


class _SessionOutput(BaseModel):
    """Output model for lily-to-langchain adapter fixture."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    display: str


class _AddTool(BaseToolContract):
    """Simple Lily tool fixture."""

    name = "add"
    input_schema = _SessionInput
    output_schema = _SessionOutput

    def parse_payload(self, payload: str) -> dict[str, object]:
        left, right = payload.split("+", maxsplit=1)
        return {"left": int(left), "right": int(right)}

    def execute_typed(
        self,
        typed_input: BaseModel,
        *,
        session: Session,
        skill_name: str,
    ) -> dict[str, object]:
        del session
        del skill_name
        model = _SessionInput.model_validate(typed_input)
        return {"display": str(model.left + model.right)}


class _LcArgs(BaseModel):
    """Args schema for fake LangChain tool."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str


class _FakeLangChainTool:
    """Fake LangChain-style tool with args_schema and invoke."""

    name = "fake_lc"
    args_schema = _LcArgs

    def invoke(self, value: object) -> object:
        if isinstance(value, dict):
            return value["text"].upper()
        return str(value).upper()


class _FailingLangChainTool(_FakeLangChainTool):
    """Fake LangChain tool that always raises."""

    name = "failing_lc"

    def invoke(self, value: object) -> object:
        del value
        raise RuntimeError("boom")


def _session() -> Session:
    """Create minimal session fixture."""
    return Session(
        session_id="contracts-wrappers",
        active_agent="default",
        skill_snapshot=SkillSnapshot(version="v-test", skills=()),
        model_config=ModelConfig(),
    )


@pytest.mark.unit
def test_langchain_to_lily_wrapper_invokes_with_envelope() -> None:
    """LangChain adapter should preserve deterministic Lily envelope shape."""
    adapter = LangChainToLilyTool(tool=_FakeLangChainTool())

    result = invoke_langchain_wrapper_with_envelope(
        adapter=adapter,
        payload='{"text":"hello"}',
        session=_session(),
        skill_name="echo",
    )

    assert result.status.value == "ok"
    assert result.code == "tool_ok"
    assert result.message == "HELLO"


@pytest.mark.unit
def test_langchain_to_lily_wrapper_maps_failure_to_deterministic_code() -> None:
    """Wrapper failures should map to stable LangChain wrapper error code."""
    adapter = LangChainToLilyTool(tool=_FailingLangChainTool())

    result = invoke_langchain_wrapper_with_envelope(
        adapter=adapter,
        payload='{"text":"hello"}',
        session=_session(),
        skill_name="echo",
    )

    assert result.status.value == "error"
    assert result.code == "langchain_wrapper_invoke_failed"


@pytest.mark.unit
def test_lily_to_langchain_wrapper_roundtrip() -> None:
    """Lily contract should be exposed as LangChain StructuredTool."""
    tool = _AddTool()
    adapter = LilyToLangChainTool(
        contract=tool,
        session=_session(),
        skill_name="add",
        description="Adds two ints.",
    )
    structured = adapter.as_structured_tool()

    output = structured.invoke({"left": 2, "right": 40})

    assert output == "42"
