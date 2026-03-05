"""LangChain-backed agent runtime wrapper for Lily kernel execution."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol, cast
from uuid import uuid4

from langchain.agents import create_agent
from langchain.agents.middleware import (
    ModelCallLimitMiddleware,
    ToolCallLimitMiddleware,
)
from langchain_core.messages import AIMessage, BaseMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from pydantic import BaseModel, ConfigDict

from lily.runtime.config_schema import RuntimeConfig
from lily.runtime.model_factory import ModelFactory
from lily.runtime.model_router import DynamicModelRouter
from lily.runtime.tool_registry import ToolLike, ToolRegistry


class AgentRuntimeError(RuntimeError):
    """Raised when runtime invocation fails policy or parsing expectations."""


class AgentRunResult(BaseModel):
    """Deterministic runtime result contract."""

    model_config = ConfigDict(frozen=True)

    final_output: str
    message_count: int
    conversation_id: str | None = None


AgentBuilder = Callable[..., object]


class _InvokableAgent(Protocol):
    """Structural protocol for compiled LangChain agent invoke surface."""

    def invoke(
        self,
        request: dict[str, object],
        *,
        config: dict[str, object],
    ) -> dict[str, object]:
        """Invoke one request and return mapping output.

        Args:
            request: Structured agent input mapping.
            config: Invocation-level execution configuration.
        """


def _coerce_message_text(message: BaseMessage) -> str:
    """Extract a stable text representation from a LangChain message.

    Args:
        message: LangChain message instance.

    Returns:
        Normalized text content for display/output use.
    """
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(str(item) for item in content)
    return str(content)


class AgentRuntime:
    """Config-driven wrapper over LangChain's `create_agent` kernel."""

    def __init__(
        self,
        config: RuntimeConfig,
        tools: Sequence[ToolLike],
        model_factory: ModelFactory | None = None,
        checkpoint_db_path: Path | None = None,
        agent_builder: AgentBuilder = create_agent,
    ) -> None:
        """Initialize runtime with validated config, tools, and adapters.

        Args:
            config: Validated runtime config object.
            tools: Tool surfaces available to the agent.
            model_factory: Optional model construction override.
            checkpoint_db_path: Optional SQLite path for thread checkpoints.
            agent_builder: Agent builder callable (defaults to create_agent).
        """
        self._config = config
        self._tools = list(tools)
        self._model_factory = model_factory or ModelFactory()
        self._checkpoint_db_path = checkpoint_db_path or (
            Path(".lily") / "runtime-checkpoints.sqlite3"
        )
        self._agent_builder = agent_builder
        self._agent: _InvokableAgent | None = None
        self._checkpoint_conn: sqlite3.Connection | None = None
        self._checkpointer: SqliteSaver | None = None

    def close(self) -> None:
        """Close held checkpoint database connection when present."""
        if self._checkpoint_conn is None:
            return
        self._checkpoint_conn.close()
        self._checkpoint_conn = None
        self._checkpointer = None

    def __del__(self) -> None:
        """Best-effort cleanup for checkpoint connection."""
        try:
            self.close()
        except Exception:
            return

    def _build_checkpointer(self) -> SqliteSaver:
        """Create and memoize SQLite checkpointer for thread persistence.

        Returns:
            LangGraph SQLite saver used as create_agent checkpointer.
        """
        if self._checkpointer is not None:
            return self._checkpointer

        self._checkpoint_db_path.parent.mkdir(parents=True, exist_ok=True)
        self._checkpoint_conn = sqlite3.connect(
            self._checkpoint_db_path,
            check_same_thread=False,
        )
        self._checkpointer = SqliteSaver(self._checkpoint_conn)
        return self._checkpointer

    def _build_agent(self) -> _InvokableAgent:
        """Create and memoize the compiled LangChain agent graph.

        Returns:
            Compiled agent with invoke capability.

        Raises:
            AgentRuntimeError: If builder output does not expose invoke method.
        """
        if self._agent is not None:
            return self._agent

        model_map = self._model_factory.create_models(self._config.models.profiles)
        router = DynamicModelRouter(
            models=model_map,
            routing=self._config.models.routing,
        )
        registry = ToolRegistry.from_tools(self._tools)
        allowlisted_tools = registry.allowlisted(self._config.tools.allowlist)
        middleware = [
            router.build_middleware(),
            ModelCallLimitMiddleware(run_limit=self._config.policies.max_model_calls),
            ToolCallLimitMiddleware(run_limit=self._config.policies.max_tool_calls),
        ]

        built = self._agent_builder(
            model=model_map[self._config.models.routing.default_profile],
            tools=allowlisted_tools,
            system_prompt=self._config.agent.system_prompt,
            middleware=middleware,
            checkpointer=self._build_checkpointer(),
            name=self._config.agent.name,
        )
        if not hasattr(built, "invoke"):
            msg = "Agent builder must return an object with an invoke(...) method."
            raise AgentRuntimeError(msg)
        self._agent = cast(_InvokableAgent, built)
        return self._agent

    def _invoke(
        self,
        user_prompt: str,
        conversation_id: str | None = None,
    ) -> dict[str, object]:
        """Invoke the underlying agent with configured recursion limit.

        Args:
            user_prompt: Raw user prompt text.
            conversation_id: Optional conversation/thread id for resume continuity.

        Returns:
            Raw mapping output from compiled LangChain agent.

        Raises:
            AgentRuntimeError: If invocation output is not a dict payload.
        """
        agent = self._build_agent()
        payload: dict[str, object] = {
            "messages": [{"role": "user", "content": user_prompt}]
        }
        invoke_config: dict[str, object] = {
            "recursion_limit": self._config.policies.max_iterations
        }
        thread_id = conversation_id or f"ephemeral-{uuid4()}"
        invoke_config["configurable"] = {"thread_id": thread_id}

        result = agent.invoke(payload, config=invoke_config)
        if not isinstance(result, dict):
            msg = "Agent invocation returned non-dict output."
            raise AgentRuntimeError(msg)
        return result

    def run(
        self,
        user_prompt: str,
        conversation_id: str | None = None,
    ) -> AgentRunResult:
        """Run one user prompt through the configured LangChain agent.

        Args:
            user_prompt: Prompt text to execute.
            conversation_id: Optional conversation/thread id for resume continuity.

        Returns:
            Deterministic final output + message count contract.

        Raises:
            AgentRuntimeError: If agent output is missing expected messages.
        """
        output = self._invoke(user_prompt, conversation_id=conversation_id)
        raw_messages = output.get("messages")
        if not isinstance(raw_messages, list) or not raw_messages:
            msg = "Agent output missing non-empty 'messages' list."
            raise AgentRuntimeError(msg)

        ai_messages = [
            message for message in raw_messages if isinstance(message, AIMessage)
        ]
        if not ai_messages:
            msg = "Agent output did not include any AI message."
            raise AgentRuntimeError(msg)

        final_output = _coerce_message_text(ai_messages[-1])
        return AgentRunResult(
            final_output=final_output,
            message_count=len(raw_messages),
            conversation_id=conversation_id,
        )
