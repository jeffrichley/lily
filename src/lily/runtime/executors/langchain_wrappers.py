"""LangChain tool interoperability wrappers for Lily tool contracts."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Protocol

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, ConfigDict

from lily.commands.types import CommandResult
from lily.runtime.executors.tool_base import BaseToolContract
from lily.runtime.executors.tool_dispatch import ToolContract
from lily.session.models import Session


class _LangChainToolLike(Protocol):
    """Protocol for LangChain tool-like objects used by wrapper adapter."""

    name: str
    args_schema: type[BaseModel] | None

    def invoke(self, value: object) -> object:
        """Invoke wrapped LangChain tool.

        Args:
            value: Input payload accepted by wrapped tool.
        """


class LangChainWrapperError(RuntimeError):
    """Deterministic wrapper error with stable Lily error code."""

    def __init__(self, *, code: str, message: str) -> None:
        """Store wrapper error payload.

        Args:
            code: Stable error code.
            message: User-facing error message.
        """
        super().__init__(message)
        self.code = code
        self.message = message


class _LangChainDefaultOutput(BaseModel):
    """Default normalized output for wrapped LangChain tools."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    display: str
    data: dict[str, object] | None = None


class LangChainToLilyTool(BaseToolContract):
    """Adapt a LangChain tool object into Lily ``ToolContract``."""

    output_schema = _LangChainDefaultOutput

    def __init__(self, *, tool: _LangChainToolLike, name: str | None = None) -> None:
        """Create adapter for one LangChain tool instance.

        Args:
            tool: LangChain tool-like object with ``invoke`` and optional
                ``args_schema``.
            name: Optional override for stable Lily tool name.

        Raises:
            LangChainWrapperError: If wrapped tool lacks required interface.
        """
        invoke = getattr(tool, "invoke", None)
        if not callable(invoke):
            raise LangChainWrapperError(
                code="langchain_wrapper_invalid",
                message="Error: wrapped LangChain tool missing invoke(...).",
            )
        self._tool = tool
        self.name = name or str(getattr(tool, "name", "langchain_tool"))
        args_schema = getattr(tool, "args_schema", None)
        self.input_schema = (
            args_schema
            if isinstance(args_schema, type) and issubclass(args_schema, BaseModel)
            else self.input_schema
        )

    def parse_payload(self, payload: str) -> dict[str, object]:
        """Parse payload with args-schema awareness.

        Args:
            payload: Raw user payload text.

        Returns:
            Input dictionary matching adapter ``input_schema``.
        """
        if self.input_schema is not type(self).input_schema:
            parsed = _try_parse_json_object(payload)
            if parsed is not None:
                return parsed
            field_names = tuple(self.input_schema.model_fields.keys())
            if len(field_names) == 1:
                return {field_names[0]: payload}
        return super().parse_payload(payload)

    def execute_typed(
        self,
        typed_input: BaseModel,
        *,
        session: Session,
        skill_name: str,
    ) -> dict[str, object]:
        """Invoke wrapped LangChain tool and normalize output.

        Args:
            typed_input: Validated input payload.
            session: Active session context.
            skill_name: Calling skill name.

        Returns:
            Output dictionary matching default normalized output schema.

        Raises:
            LangChainWrapperError: If wrapped invocation fails.
        """
        del session
        del skill_name
        try:
            if self.input_schema is type(self).input_schema:
                result = self._tool.invoke(typed_input.model_dump()["payload"])
            else:
                result = self._tool.invoke(typed_input.model_dump())
        except Exception as exc:  # pragma: no cover - defensive boundary
            raise LangChainWrapperError(
                code="langchain_wrapper_invoke_failed",
                message=f"Error: wrapped LangChain tool invocation failed: {exc}",
            ) from exc
        return _normalize_result(result)


class LilyToLangChainTool:
    """Adapt a Lily ``ToolContract`` into a LangChain ``StructuredTool``."""

    def __init__(
        self,
        *,
        contract: ToolContract,
        session: Session,
        skill_name: str,
        description: str,
    ) -> None:
        """Store adapter context and target tool contract.

        Args:
            contract: Lily tool contract to expose.
            session: Active session context for execution.
            skill_name: Calling skill name.
            description: Tool description for LangChain registry.
        """
        self._contract = contract
        self._session = session
        self._skill_name = skill_name
        self._description = description

    def as_structured_tool(self) -> StructuredTool:
        """Create LangChain StructuredTool for the wrapped Lily tool.

        Returns:
            StructuredTool instance.
        """

        def _invoke(**kwargs: object) -> str:
            typed_input = self._contract.input_schema.model_validate(kwargs)
            raw_output = self._contract.execute_typed(
                typed_input,
                session=self._session,
                skill_name=self._skill_name,
            )
            typed_output = self._contract.output_schema.model_validate(raw_output)
            return self._contract.render_output(typed_output)

        return StructuredTool.from_function(
            func=_invoke,
            name=self._contract.name,
            description=self._description,
            args_schema=self._contract.input_schema,
        )


def invoke_langchain_wrapper_with_envelope(
    *,
    adapter: LangChainToLilyTool,
    payload: str,
    session: Session,
    skill_name: str,
) -> CommandResult:
    """Invoke wrapped LangChain tool and return deterministic Lily envelope.

    Args:
        adapter: Wrapped LangChain tool adapter.
        payload: Raw user payload.
        session: Active session.
        skill_name: Calling skill name.

    Returns:
        Deterministic command result envelope.
    """
    try:
        typed_input = adapter.input_schema.model_validate(
            adapter.parse_payload(payload)
        )
        raw_output = adapter.execute_typed(
            typed_input, session=session, skill_name=skill_name
        )
        typed_output = adapter.output_schema.model_validate(raw_output)
        return CommandResult.ok(
            adapter.render_output(typed_output),
            code="tool_ok",
            data={
                "skill": skill_name,
                "provider": "langchain",
                "tool": adapter.name,
                "output": typed_output.model_dump(mode="json"),
            },
        )
    except LangChainWrapperError as exc:
        return CommandResult.error(
            exc.message,
            code=exc.code,
            data={"tool": adapter.name},
        )


def _try_parse_json_object(payload: str) -> dict[str, object] | None:
    """Parse JSON object payload if possible.

    Args:
        payload: Raw string payload.

    Returns:
        Parsed dictionary, else ``None``.
    """
    text = payload.strip()
    if not text.startswith("{"):
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, Mapping):
        return dict(parsed)
    return None


def _normalize_result(result: object) -> dict[str, object]:
    """Normalize LangChain tool result into default output schema payload.

    Args:
        result: Raw wrapped LangChain result payload.

    Returns:
        Normalized output dictionary.
    """
    if isinstance(result, str):
        return {"display": result}
    if isinstance(result, Mapping):
        result_dict = dict(result)
        return {
            "display": json.dumps(result_dict, sort_keys=True),
            "data": result_dict,
        }
    return {"display": str(result)}
