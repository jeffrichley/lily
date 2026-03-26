"""Integration tests for LangChain-backed agent runtime behavior."""

from __future__ import annotations

from contextlib import closing
from pathlib import Path

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from lily.runtime.agent_runtime import AgentRuntime
from lily.runtime.config_schema import (
    ConversationCompressionConfig,
    ConversationCompressionKeepConfig,
    ConversationCompressionTriggerConfig,
    ModelProfileConfig,
    ModelProvider,
    RuntimeConfig,
    SkillsConfig,
)
from lily.runtime.model_factory import ModelBuilder, ModelFactory
from lily.runtime.skill_catalog_injection_middleware import (
    SystemPromptSkillCatalogMiddleware,
)
from lily.runtime.skill_loader import build_skill_bundle
from lily.runtime.tool_registry import ToolRegistryError

pytestmark = pytest.mark.integration


class ToolCapableFakeModel(FakeMessagesListChatModel):
    """Fake model that supports `bind_tools` for LangChain agent tests."""

    def bind_tools(
        self,
        _tools: object,
        *,
        _tool_choice: object | None = None,
        **_kwargs: object,
    ) -> ToolCapableFakeModel:
        """Return self so create_agent can execute tool-call loop."""
        return self


class _SpyInvokableAgent:
    """Spy invokable capturing invoke payload/config for assertions."""

    def __init__(self) -> None:
        """Initialize empty capture fields."""
        self.request: dict[str, object] | None = None
        self.config: dict[str, object] | None = None

    def invoke(
        self,
        request: dict[str, object],
        *,
        config: dict[str, object],
    ) -> dict[str, object]:
        """Capture invoke call details and return deterministic output."""
        self.request = request
        self.config = config
        return {"messages": [AIMessage(content="SPY")]}


class _SpyAsyncInvokableAgent:
    """Async-only spy invokable capturing ainvoke payload/config."""

    def __init__(self) -> None:
        """Initialize empty capture fields."""
        self.request: dict[str, object] | None = None
        self.config: dict[str, object] | None = None

    async def ainvoke(
        self,
        request: dict[str, object],
        *,
        config: dict[str, object],
    ) -> dict[str, object]:
        """Capture ainvoke details and return deterministic output."""
        self.request = request
        self.config = config
        return {"messages": [AIMessage(content="ASYNC-SPY")]}


def _runtime_config(
    *,
    allowlist: list[str],
    routing_enabled: bool,
    threshold: int = 50,
) -> RuntimeConfig:
    """Build runtime config fixture from inline mapping."""
    return RuntimeConfig.model_validate(
        {
            "schema_version": 1,
            "agent": {"name": "lily", "system_prompt": "You are Lily."},
            "models": {
                "profiles": {
                    "default": {
                        "provider": "openai",
                        "model": "default-model",
                        "temperature": 0.1,
                        "timeout_seconds": 30,
                    },
                    "long_context": {
                        "provider": "openai",
                        "model": "long-model",
                        "temperature": 0.1,
                        "timeout_seconds": 30,
                    },
                },
                "routing": {
                    "enabled": routing_enabled,
                    "default_profile": "default",
                    "long_context_profile": "long_context",
                    "complexity_threshold": threshold,
                },
            },
            "tools": {"allowlist": allowlist},
            "policies": {
                "max_iterations": 10,
                "max_model_calls": 10,
                "max_tool_calls": 10,
            },
            "logging": {"level": "INFO"},
        }
    )


def _model_factory(models: dict[str, BaseChatModel]) -> ModelFactory:
    """Create a model factory that returns deterministic fake models by name."""

    def _builder(profile: ModelProfileConfig) -> BaseChatModel:
        return models[profile.model]

    builders: dict[ModelProvider, ModelBuilder] = {
        ModelProvider.OPENAI: _builder,
        ModelProvider.OLLAMA: _builder,
    }
    return ModelFactory(builders=builders)


def test_agent_runtime_executes_tool_call_cycle_and_returns_final_output() -> None:
    """Runs a LangChain tool-call loop and returns the final AI response."""

    # Arrange - configure runtime with one allowlisted tool and tool-capable fake model.
    @tool
    def echo_tool(text: str) -> str:
        """Echo text with a prefix."""
        return f"ECHO:{text}"

    fake_model = ToolCapableFakeModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "echo_tool",
                        "args": {"text": "hello"},
                        "id": "call_1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="All done."),
        ]
    )
    runtime = AgentRuntime(
        config=_runtime_config(allowlist=["echo_tool"], routing_enabled=False),
        tools=[echo_tool],
        model_factory=_model_factory(
            {"default-model": fake_model, "long-model": fake_model}
        ),
    )

    # Act - execute a single runtime prompt.
    with closing(runtime):
        result = runtime.run("run tool please")

    # Assert - runtime returns deterministic final output from final AI message.
    assert result.final_output == "All done."
    assert result.message_count >= 3


def test_agent_runtime_rejects_unknown_allowlisted_tools() -> None:
    """Fails cleanly when the allowlist references missing tools."""
    # Arrange - configure allowlist with an unknown tool name.
    runtime = AgentRuntime(
        config=_runtime_config(allowlist=["missing_tool"], routing_enabled=False),
        tools=[],
        model_factory=_model_factory(
            {
                "default-model": ToolCapableFakeModel(
                    responses=[AIMessage(content="ok")]
                ),
                "long-model": ToolCapableFakeModel(responses=[AIMessage(content="ok")]),
            }
        ),
    )

    # Act - execute runtime with invalid allowlist configuration.
    with closing(runtime), pytest.raises(ToolRegistryError) as err:
        runtime.run("hello")

    # Assert - error surfaces missing tool details.
    assert "unknown tools" in str(err.value)


def test_agent_runtime_dynamic_model_routing_changes_model_by_message_size() -> None:
    """Selects default vs long-context model based on prompt complexity."""

    # Arrange - set threshold where short prompts use default and long prompts use long.
    @tool
    def ping_tool() -> str:
        """Return pong."""
        return "pong"

    default_model = ToolCapableFakeModel(responses=[AIMessage(content="DEFAULT")])
    long_model = ToolCapableFakeModel(responses=[AIMessage(content="LONG")])
    runtime = AgentRuntime(
        config=_runtime_config(
            allowlist=["ping_tool"],
            routing_enabled=True,
            threshold=30,
        ),
        tools=[ping_tool],
        model_factory=_model_factory(
            {"default-model": default_model, "long-model": long_model}
        ),
    )

    # Act - run one short prompt and one long prompt through the same runtime.
    with closing(runtime):
        short_result = runtime.run("short prompt")
        long_result = runtime.run(
            "This prompt is intentionally long enough to exceed the configured "
            "threshold."
        )

    # Assert - routing middleware selects different model profiles.
    assert short_result.final_output == "DEFAULT"
    assert long_result.final_output == "LONG"


def test_agent_runtime_passes_conversation_id_as_thread_id_config() -> None:
    """Adds thread_id to invoke config when conversation id is provided."""

    # Arrange - build runtime with spy agent builder and one allowlisted tool.
    @tool
    def ping_tool() -> str:
        """Return pong."""
        return "pong"

    spy_agent = _SpyInvokableAgent()

    def _spy_agent_builder(**_kwargs: object) -> _SpyInvokableAgent:
        return spy_agent

    runtime = AgentRuntime(
        config=_runtime_config(allowlist=["ping_tool"], routing_enabled=False),
        tools=[ping_tool],
        model_factory=_model_factory(
            {
                "default-model": ToolCapableFakeModel(
                    responses=[AIMessage(content="ignored")]
                ),
                "long-model": ToolCapableFakeModel(
                    responses=[AIMessage(content="ignored")]
                ),
            }
        ),
        agent_builder=_spy_agent_builder,
    )

    # Act - run runtime with explicit conversation id.
    with closing(runtime):
        result = runtime.run("hello", conversation_id="conv-123")

    # Assert - invoke config includes thread_id and result echoes conversation id.
    assert spy_agent.config is not None
    assert spy_agent.config["recursion_limit"] == 10
    assert spy_agent.config["configurable"] == {"thread_id": "conv-123"}
    assert result.conversation_id == "conv-123"


def test_agent_runtime_omits_thread_config_when_conversation_id_absent() -> None:
    """Preserves one-shot behavior by omitting configurable thread_id."""

    # Arrange - build runtime with spy agent builder and one allowlisted tool.
    @tool
    def ping_tool() -> str:
        """Return pong."""
        return "pong"

    spy_agent = _SpyInvokableAgent()

    def _spy_agent_builder(**_kwargs: object) -> _SpyInvokableAgent:
        return spy_agent

    runtime = AgentRuntime(
        config=_runtime_config(allowlist=["ping_tool"], routing_enabled=False),
        tools=[ping_tool],
        model_factory=_model_factory(
            {
                "default-model": ToolCapableFakeModel(
                    responses=[AIMessage(content="ignored")]
                ),
                "long-model": ToolCapableFakeModel(
                    responses=[AIMessage(content="ignored")]
                ),
            }
        ),
        agent_builder=_spy_agent_builder,
    )

    # Act - run runtime without explicit conversation id.
    with closing(runtime):
        result = runtime.run("hello")

    # Assert - invoke config keeps recursion limit only and result id is None.
    assert spy_agent.config is not None
    assert spy_agent.config["recursion_limit"] == 10
    assert "configurable" in spy_agent.config
    assert "thread_id" in dict(spy_agent.config["configurable"])
    assert result.conversation_id is None


def test_agent_runtime_supports_async_invokable_agent() -> None:
    """Uses `ainvoke` when the compiled agent exposes async-only invocation."""

    # Arrange - build runtime with async-only spy agent builder.
    @tool
    def ping_tool() -> str:
        """Return pong."""
        return "pong"

    spy_agent = _SpyAsyncInvokableAgent()

    def _spy_agent_builder(**_kwargs: object) -> _SpyAsyncInvokableAgent:
        return spy_agent

    runtime = AgentRuntime(
        config=_runtime_config(allowlist=["ping_tool"], routing_enabled=False),
        tools=[ping_tool],
        model_factory=_model_factory(
            {
                "default-model": ToolCapableFakeModel(
                    responses=[AIMessage(content="ignored")]
                ),
                "long-model": ToolCapableFakeModel(
                    responses=[AIMessage(content="ignored")]
                ),
            }
        ),
        agent_builder=_spy_agent_builder,
    )

    # Act - run runtime and exercise async invocation bridge.
    with closing(runtime):
        result = runtime.run("hello", conversation_id="conv-async")

    # Assert - async spy captured config and produced deterministic output.
    assert spy_agent.config is not None
    assert spy_agent.config["configurable"] == {"thread_id": "conv-async"}
    assert result.final_output == "ASYNC-SPY"


def test_agent_runtime_persists_history_for_same_conversation_id(
    tmp_path: Path,
) -> None:
    """Reuses checkpointed history when same conversation id is provided."""

    # Arrange - use deterministic fake model and on-disk checkpoint DB.
    @tool
    def ping_tool() -> str:
        """Return pong."""
        return "pong"

    fake_model = ToolCapableFakeModel(
        responses=[AIMessage(content="FIRST"), AIMessage(content="SECOND")]
    )
    runtime = AgentRuntime(
        config=_runtime_config(allowlist=["ping_tool"], routing_enabled=False),
        tools=[ping_tool],
        model_factory=_model_factory(
            {"default-model": fake_model, "long-model": fake_model}
        ),
        checkpoint_db_path=tmp_path / "checkpoints.sqlite3",
    )

    # Act - run twice with same conversation id.
    with closing(runtime):
        first = runtime.run("my name is Jeff", conversation_id="conv-remember")
        second = runtime.run("what is my name", conversation_id="conv-remember")

    # Assert - second run includes prior messages from checkpoint history.
    assert first.final_output == "FIRST"
    assert second.final_output == "SECOND"
    assert second.message_count > first.message_count


def test_agent_runtime_compression_compacts_persisted_history(
    tmp_path: Path,
) -> None:
    """Ensures enabled compression keeps checkpoint history compact.

    This does not attempt to assert exact message list structure (LangChain agent
    internals may add intermediate messages), but it validates that the persisted
    history does not grow unbounded across repeated runs for the same
    conversation_id.
    """

    # Arrange - enable compression and reuse checkpoint DB.
    @tool
    def ping_tool() -> str:
        """Return pong."""
        return "pong"

    # Provide enough responses to cover:
    # - 1 agent model call per turn
    # - 0-1 summarization model call per turn when thresholds are exceeded
    fake_model = ToolCapableFakeModel(
        responses=[AIMessage(content="OK")] * 20,
    )

    config = _runtime_config(allowlist=["ping_tool"], routing_enabled=False)
    config = config.model_copy(
        update={
            "policies": config.policies.model_copy(
                update={
                    "conversation_compression": ConversationCompressionConfig(
                        enabled=True,
                        trigger=ConversationCompressionTriggerConfig(
                            kind="messages",
                            threshold=3,
                        ),
                        keep=ConversationCompressionKeepConfig(
                            kind="messages",
                            value=1,
                        ),
                    )
                }
            )
        }
    )

    runtime = AgentRuntime(
        config=config,
        tools=[ping_tool],
        model_factory=_model_factory(
            {"default-model": fake_model, "long-model": fake_model}
        ),
        checkpoint_db_path=tmp_path / "checkpoints.sqlite3",
    )

    # Act - run multiple turns through the same conversation id.
    with closing(runtime):
        first = runtime.run("turn 1", conversation_id="conv-compress")
        second = runtime.run("turn 2", conversation_id="conv-compress")
        third = runtime.run("turn 3", conversation_id="conv-compress")

    # Assert - the agent output is stable and the persisted message history
    # does not expand linearly with number of turns.
    assert first.final_output == "OK"
    assert second.final_output == "OK"
    assert third.final_output == "OK"

    assert second.message_count > first.message_count
    assert third.message_count <= second.message_count + 2


def test_agent_runtime_skill_catalog_injection_uses_middleware(
    tmp_path: Path,
) -> None:
    """Middleware strategy should not mutate build-time system_prompt."""
    # Arrange - filesystem skill package and bundle for one skill
    skills_root = tmp_path / "skills"
    pkg = skills_root / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "SKILL.md").write_text(
        '---\nname: listed-skill\ndescription: "Listed."\n---\n# Body\n',
        encoding="utf-8",
    )
    cfg = SkillsConfig(
        enabled=True,
        roots={"repository": [str(skills_root.relative_to(tmp_path))]},
        scopes_precedence=["repository", "user", "system"],
    )
    bundle = build_skill_bundle(cfg, tmp_path)
    assert bundle is not None

    @tool
    def ping_tool() -> str:
        """Return pong."""
        return "pong"

    captured: dict[str, object] = {}
    spy_agent = _SpyInvokableAgent()

    def _spy_agent_builder(**kwargs: object) -> _SpyInvokableAgent:
        captured.clear()
        captured.update(kwargs)
        return spy_agent

    runtime = AgentRuntime(
        config=_runtime_config(
            allowlist=["ping_tool"], routing_enabled=False
        ).model_copy(update={"skills": cfg}),
        tools=[ping_tool],
        model_factory=_model_factory(
            {
                "default-model": ToolCapableFakeModel(
                    responses=[AIMessage(content="SPY")]
                ),
                "long-model": ToolCapableFakeModel(
                    responses=[AIMessage(content="ignored")]
                ),
            }
        ),
        agent_builder=_spy_agent_builder,
        skill_bundle=bundle,
    )

    # Act - run once so the agent is built with the augmented system prompt
    with closing(runtime):
        result = runtime.run("hello")

    # Assert - create_agent received base prompt *without* catalog injection.
    assert captured.get("system_prompt") is not None
    assert "You are Lily." in str(captured["system_prompt"])
    assert "Skill catalog" not in str(captured["system_prompt"])
    assert "listed-skill" not in str(captured["system_prompt"])

    middleware_list = captured.get("middleware")
    assert isinstance(middleware_list, list)
    assert any(
        isinstance(m, SystemPromptSkillCatalogMiddleware) for m in middleware_list
    )
    assert result.final_output == "SPY"
