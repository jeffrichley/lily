"""Executable adapter for agent catalog/runtime identity operations."""

from __future__ import annotations

from lily.agents.service import AgentNotFoundError, AgentService
from lily.runtime.executables.handlers._common import (
    elapsed_ms,
    error_result,
    require_input_value,
    started_timer,
)
from lily.runtime.executables.handlers.base import BaseExecutableHandler
from lily.runtime.executables.models import (
    ExecutableError,
    ExecutableKind,
    ExecutableRequest,
    ExecutableResult,
    ExecutableStatus,
    ExecutionMetrics,
)
from lily.session.models import Session


class AgentExecutableHandler(BaseExecutableHandler):
    """Adapter handler that executes deterministic agent identity operations."""

    kind = ExecutableKind.AGENT

    def __init__(self, service: AgentService) -> None:
        """Store agent service dependency.

        Args:
            service: Agent runtime service.
        """
        self._service = service

    def handle(self, request: ExecutableRequest) -> ExecutableResult:
        """Execute agent adapter action through canonical envelope."""
        started = started_timer()
        action = str(request.input.get("action", "get")).strip().lower()
        agent_id = (
            str(request.input.get("agent_id") or request.target.executable_id)
            .strip()
            .lower()
        )
        if not agent_id:
            return error_result(
                request=request,
                error=ExecutableError(
                    code="adapter_input_invalid",
                    message="Error: agent adapter input is invalid: missing agent_id.",
                    retryable=False,
                    data={},
                ),
                duration_ms=elapsed_ms(started),
            )

        try:
            if action == "set_active":
                session = require_input_value(
                    request.input,
                    key="session",
                    expected_type=Session,
                )
                profile = self._service.set_active_agent(session, agent_id)
            else:
                profile = self._service.require_agent(agent_id)
        except (TypeError, ValueError) as exc:
            return error_result(
                request=request,
                error=ExecutableError(
                    code="adapter_input_invalid",
                    message=f"Error: agent adapter input is invalid: {exc}",
                    retryable=False,
                    data={"agent_id": agent_id, "action": action},
                ),
                duration_ms=elapsed_ms(started),
            )
        except AgentNotFoundError as exc:
            return error_result(
                request=request,
                error=ExecutableError(
                    code="agent_not_found",
                    message=str(exc),
                    retryable=False,
                    data={"agent_id": agent_id},
                ),
                duration_ms=elapsed_ms(started),
            )

        return ExecutableResult(
            run_id=request.run_id,
            step_id=request.step_id,
            status=ExecutableStatus.OK,
            output={
                "agent_id": profile.agent_id,
                "summary": profile.summary,
                "policy": profile.policy,
                "declared_tools": profile.declared_tools,
                "action": action,
            },
            references=(f"agent://{profile.agent_id}",),
            artifacts=(),
            metrics=ExecutionMetrics(duration_ms=elapsed_ms(started)),
            error=None,
        )
