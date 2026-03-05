"""Tool-dispatch skill executor with typed input/output contracts."""

from __future__ import annotations

from pydantic import BaseModel, ValidationError

from lily.commands.types import CommandResult
from lily.runtime.executors.tool_dispatch_components import (
    AddTool,
    BuiltinToolProvider,
    McpToolProvider,
    MultiplyTool,
    PluginToolProvider,
    ProviderExecutionError,
    ProviderPolicyDeniedError,
    SubtractTool,
    ToolContract,
    ToolExecutionError,
    ToolProvider,
)
from lily.session.models import Session
from lily.skills.types import InvocationMode, SkillEntry

__all__ = [
    "AddTool",
    "BuiltinToolProvider",
    "McpToolProvider",
    "MultiplyTool",
    "PluginToolProvider",
    "SubtractTool",
    "ToolDispatchExecutor",
]


class ToolDispatchExecutor:
    """Execute `tool_dispatch` skills by typed contract-bound tool invocation."""

    mode = InvocationMode.TOOL_DISPATCH

    def __init__(self, providers: tuple[ToolProvider, ...]) -> None:
        """Build deterministic provider registry keyed by provider id.

        Args:
            providers: Registered tool providers.
        """
        self._providers = {provider.provider_id: provider for provider in providers}

    def execute(
        self, entry: SkillEntry, session: Session, user_text: str
    ) -> CommandResult:
        """Dispatch to configured command tool for entry.

        Args:
            entry: Skill entry selected from snapshot.
            session: Active session.
            user_text: User payload for skill execution.

        Returns:
            Deterministic command-tool execution result.
        """
        tool, error = self._resolve_tool(entry, session)
        if error is not None:
            return error
        assert tool is not None

        typed_input, error = self._validate_input(tool, entry, user_text)
        if error is not None:
            return error
        assert typed_input is not None

        typed_output, error = self._validate_output(tool, entry, typed_input, session)
        if error is not None:
            return error
        assert typed_output is not None

        return CommandResult.ok(
            tool.render_output(typed_output),
            code="tool_ok",
            data={
                "skill": entry.name,
                "provider": entry.command_tool_provider,
                "tool": tool.name,
                "output": typed_output.model_dump(),
            },
        )

    def _resolve_tool(
        self,
        entry: SkillEntry,
        session: Session,
    ) -> tuple[ToolContract | None, CommandResult | None]:
        """Resolve provider + tool for one skill invocation.

        Args:
            entry: Skill entry selected from snapshot.
            session: Active session context.

        Returns:
            Tuple of resolved tool and optional error result.
        """
        provider, tool_name, precheck_error = self._resolve_provider_and_tool_name(
            entry
        )
        if precheck_error is not None:
            return None, precheck_error
        assert provider is not None
        assert tool_name is not None
        try:
            tool = provider.resolve_tool(
                tool_name,
                session=session,
                skill_name=entry.name,
            )
        except ProviderPolicyDeniedError as exc:
            return None, _error_result(
                message=f"Security alert: provider policy denied '{tool_name}'.",
                code="provider_policy_denied",
                data={
                    "skill": entry.name,
                    "provider": entry.command_tool_provider,
                    "tool": tool_name,
                    "reason": str(exc),
                },
            )
        except ProviderExecutionError as exc:
            return None, _error_result(
                message=exc.message,
                code=exc.code,
                data=exc.data,
            )
        except Exception as exc:  # pragma: no cover - defensive provider boundary
            return None, _error_result(
                message=f"Error: provider execution failed for '{tool_name}'.",
                code="provider_execution_failed",
                data={
                    "skill": entry.name,
                    "provider": entry.command_tool_provider,
                    "tool": tool_name,
                    "reason": str(exc),
                },
            )
        if tool is None:
            return None, _error_result(
                message=(
                    f"Error: tool '{tool_name}' is not registered for provider "
                    f"'{entry.command_tool_provider}' (skill '{entry.name}')."
                ),
                code="provider_tool_unregistered",
                data={
                    "skill": entry.name,
                    "provider": entry.command_tool_provider,
                    "tool": tool_name,
                },
            )
        return tool, None

    def _resolve_provider_and_tool_name(
        self,
        entry: SkillEntry,
    ) -> tuple[ToolProvider | None, str | None, CommandResult | None]:
        """Resolve provider binding and command tool name.

        Args:
            entry: Skill entry selected from snapshot.

        Returns:
            Tuple of provider, tool name, and optional error.
        """
        tool_name = entry.command_tool
        if not tool_name:
            return (
                None,
                None,
                _error_result(
                    message=(
                        f"Error: skill '{entry.name}' is missing command_tool "
                        "for tool_dispatch."
                    ),
                    code="command_tool_missing",
                    data={"skill": entry.name},
                ),
            )
        provider = self._providers.get(entry.command_tool_provider)
        if provider is None:
            return (
                None,
                None,
                _error_result(
                    message=(
                        f"Error: tool provider '{entry.command_tool_provider}' is not "
                        f"registered for skill '{entry.name}'."
                    ),
                    code="provider_unbound",
                    data={
                        "skill": entry.name,
                        "provider": entry.command_tool_provider,
                    },
                ),
            )
        return provider, tool_name, None

    @staticmethod
    def _validate_input(
        tool: ToolContract,
        entry: SkillEntry,
        user_text: str,
    ) -> tuple[BaseModel | None, CommandResult | None]:
        """Validate tool input payload.

        Args:
            tool: Resolved tool contract.
            entry: Calling skill entry.
            user_text: Raw user payload.

        Returns:
            Tuple of validated input model and optional error result.
        """
        try:
            raw_input = tool.parse_payload(user_text)
            typed_input = tool.input_schema.model_validate(raw_input)
            return typed_input, None
        except ValidationError as exc:
            return None, CommandResult.error(
                f"Error: invalid input for tool '{tool.name}'.",
                code="tool_input_invalid",
                data={
                    "skill": entry.name,
                    "provider": entry.command_tool_provider,
                    "tool": tool.name,
                    "validation_errors": exc.errors(),
                },
            )

    @staticmethod
    def _validate_output(
        tool: ToolContract,
        entry: SkillEntry,
        typed_input: BaseModel,
        session: Session,
    ) -> tuple[BaseModel | None, CommandResult | None]:
        """Validate tool output payload.

        Args:
            tool: Resolved tool contract.
            entry: Calling skill entry.
            typed_input: Validated input payload.
            session: Active session context.

        Returns:
            Tuple of validated output model and optional error result.
        """
        try:
            raw_output = tool.execute_typed(
                typed_input,
                session=session,
                skill_name=entry.name,
            )
            typed_output = tool.output_schema.model_validate(raw_output)
            return typed_output, None
        except ToolExecutionError as exc:
            return None, CommandResult.error(
                exc.message,
                code=exc.code,
                data=exc.data,
            )
        except ValidationError as exc:
            return None, CommandResult.error(
                f"Error: invalid output from tool '{tool.name}'.",
                code="tool_output_invalid",
                data={
                    "skill": entry.name,
                    "provider": entry.command_tool_provider,
                    "tool": tool.name,
                    "validation_errors": exc.errors(),
                },
            )


def _error_result(
    *,
    message: str,
    code: str,
    data: dict[str, object],
) -> CommandResult:
    """Build deterministic error envelope for tool dispatch failures.

    Args:
        message: Human-readable error message.
        code: Deterministic machine-readable error code.
        data: Structured error payload.

    Returns:
        CommandResult error envelope.
    """
    return CommandResult.error(message, code=code, data=data)
