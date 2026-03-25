"""LangChain-backed agent runtime wrapper for Lily kernel execution."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable, Coroutine, Sequence
from pathlib import Path
from typing import Protocol, TypeVar, cast
from uuid import uuid4

import aiosqlite
from langchain.agents import create_agent
from langchain.agents.middleware import (
    ModelCallLimitMiddleware,
    ToolCallLimitMiddleware,
)
from langchain_core.messages import AIMessage, BaseMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from pydantic import BaseModel, ConfigDict, Field

from lily.runtime.config_schema import RuntimeConfig
from lily.runtime.model_factory import ModelFactory
from lily.runtime.model_router import DynamicModelRouter
from lily.runtime.skill_invoke_trace import (
    SkillInvokeTrace,
    SkillRetrievalTraceEntry,
    bind_skill_trace,
    reset_skill_trace,
)
from lily.runtime.skill_loader import SkillBundle
from lily.runtime.skill_retrieve_tool import bind_skill_loader, reset_skill_loader
from lily.runtime.tool_registry import ToolLike, ToolRegistry


class AgentRuntimeError(RuntimeError):
    """Raised when runtime invocation fails policy or parsing expectations."""


class AgentRunResult(BaseModel):
    """Deterministic runtime result contract."""

    model_config = ConfigDict(frozen=True)

    final_output: str
    message_count: int
    conversation_id: str | None = None
    skill_trace: SkillInvokeTrace = Field(default_factory=SkillInvokeTrace)


AgentBuilder = Callable[..., object]
_T = TypeVar("_T")


class _AsyncInvokableAgent(Protocol):
    """Structural protocol for compiled agent async invoke surface."""

    async def ainvoke(
        self,
        request: dict[str, object],
        *,
        config: dict[str, object],
    ) -> dict[str, object]:
        """Asynchronously invoke one request and return mapping output.

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

    def __init__(  # noqa: PLR0913
        self,
        config: RuntimeConfig,
        tools: Sequence[ToolLike],
        model_factory: ModelFactory | None = None,
        checkpoint_db_path: Path | None = None,
        agent_builder: AgentBuilder = create_agent,
        skill_bundle: SkillBundle | None = None,
    ) -> None:
        """Initialize runtime with validated config, tools, and adapters.

        Args:
            config: Validated runtime config object.
            tools: Tool surfaces available to the agent.
            model_factory: Optional model construction override.
            checkpoint_db_path: Optional SQLite path for thread checkpoints.
            agent_builder: Agent builder callable (defaults to create_agent).
            skill_bundle: Optional discovery/loader bundle for catalog injection and
                ``skill_retrieve`` context binding.
        """
        self._config = config
        self._tools = list(tools)
        self._skill_bundle = skill_bundle
        self._model_factory = model_factory or ModelFactory()
        self._checkpoint_db_path = checkpoint_db_path or (
            Path(".lily") / "runtime-checkpoints.sqlite3"
        )
        self._agent_builder = agent_builder
        self._agent: object | None = None
        self._checkpoint_conn: aiosqlite.Connection | None = None
        self._checkpointer: AsyncSqliteSaver | None = None
        self._async_loop: asyncio.AbstractEventLoop | None = None
        self._async_loop_thread: threading.Thread | None = None

    def _ensure_async_loop(self) -> asyncio.AbstractEventLoop:
        """Create and memoize one dedicated async loop thread.

        Returns:
            Running event loop used for async checkpointing/invocation.
        """
        if self._async_loop is not None and self._async_loop.is_running():
            return self._async_loop

        ready = threading.Event()
        loop_holder: dict[str, asyncio.AbstractEventLoop] = {}

        def _loop_runner() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop_holder["loop"] = loop
            ready.set()
            loop.run_forever()
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
            loop.close()

        loop_thread = threading.Thread(target=_loop_runner, daemon=True)
        loop_thread.start()
        ready.wait()

        self._async_loop = loop_holder["loop"]
        self._async_loop_thread = loop_thread
        return self._async_loop

    def _run_on_async_loop(self, coro: Coroutine[object, object, _T]) -> _T:
        """Run one coroutine on runtime-owned background async loop.

        Args:
            coro: Coroutine to execute on loop thread.

        Returns:
            Coroutine result.
        """
        loop = self._ensure_async_loop()
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()

    def close(self) -> None:
        """Close held async checkpoint resources and loop thread."""
        if self._checkpoint_conn is not None:
            self._run_on_async_loop(self._checkpoint_conn.close())
            self._checkpoint_conn = None
        self._checkpointer = None
        self._agent = None
        if self._async_loop is not None:
            self._async_loop.call_soon_threadsafe(self._async_loop.stop)
            if self._async_loop_thread is not None:
                self._async_loop_thread.join(timeout=2.0)
            self._async_loop = None
            self._async_loop_thread = None

    def __del__(self) -> None:
        """Best-effort cleanup for checkpoint connection."""
        try:
            self.close()
        except Exception:
            return

    def _build_checkpointer(self) -> AsyncSqliteSaver:
        """Create and memoize async SQLite checkpointer for thread persistence.

        Returns:
            LangGraph async SQLite saver used as create_agent checkpointer.
        """
        if self._checkpointer is not None:
            return self._checkpointer

        self._checkpoint_db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path = str(self._checkpoint_db_path)

        async def _create_async_checkpointer() -> tuple[
            aiosqlite.Connection, AsyncSqliteSaver
        ]:
            conn = await aiosqlite.connect(db_path)
            return conn, AsyncSqliteSaver(conn)

        conn, checkpointer = self._run_on_async_loop(_create_async_checkpointer())
        self._checkpoint_conn = conn
        self._checkpointer = checkpointer
        return self._checkpointer

    def _build_agent(self) -> object:
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

        system_prompt = self._config.agent.system_prompt
        if (
            self._skill_bundle is not None
            and self._skill_bundle.catalog_markdown.strip()
        ):
            system_prompt = (
                f"{system_prompt.rstrip()}\n\n{self._skill_bundle.catalog_markdown}"
            )

        built = self._agent_builder(
            model=model_map[self._config.models.routing.default_profile],
            tools=allowlisted_tools,
            system_prompt=system_prompt,
            middleware=middleware,
            checkpointer=self._build_checkpointer(),
            name=self._config.agent.name,
        )
        if not hasattr(built, "invoke") and not hasattr(built, "ainvoke"):
            msg = (
                "Agent builder must return an object with invoke(...) or "
                "ainvoke(...) method."
            )
            raise AgentRuntimeError(msg)
        self._agent = cast(object, built)
        return self._agent

    def _invoke(
        self,
        user_prompt: str,
        conversation_id: str | None = None,
    ) -> tuple[dict[str, object], list[SkillRetrievalTraceEntry]]:
        """Invoke the underlying agent with configured recursion limit.

        Args:
            user_prompt: Raw user prompt text.
            conversation_id: Optional conversation/thread id for resume continuity.

        Returns:
            Raw mapping output from compiled LangChain agent and skill retrieval trace
            entries recorded during this invoke.

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

        loader_token = None
        if self._skill_bundle is not None:
            loader_token = bind_skill_loader(self._skill_bundle.loader)

        trace_token, trace_entries = bind_skill_trace()
        try:
            if hasattr(agent, "ainvoke"):
                async_agent = cast(_AsyncInvokableAgent, agent)
                result = self._run_on_async_loop(
                    async_agent.ainvoke(payload, config=invoke_config)
                )
            elif hasattr(agent, "invoke"):
                result = agent.invoke(payload, config=invoke_config)
            else:
                msg = "Built agent exposes neither invoke(...) nor ainvoke(...)."
                raise AgentRuntimeError(msg)
        finally:
            if loader_token is not None:
                reset_skill_loader(loader_token)
            reset_skill_trace(trace_token)

        if not isinstance(result, dict):
            msg = "Agent invocation returned non-dict output."
            raise AgentRuntimeError(msg)
        return result, trace_entries

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
        output, trace_entries = self._invoke(
            user_prompt, conversation_id=conversation_id
        )
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
        skills_enabled = self._skill_bundle is not None
        catalog_injected = bool(
            skills_enabled
            and self._skill_bundle is not None
            and self._skill_bundle.catalog_markdown.strip()
        )
        skill_trace = SkillInvokeTrace(
            skills_enabled=skills_enabled,
            catalog_injected=catalog_injected,
            retrievals=tuple(trace_entries),
        )
        return AgentRunResult(
            final_output=final_output,
            message_count=len(raw_messages),
            conversation_id=conversation_id,
            skill_trace=skill_trace,
        )
