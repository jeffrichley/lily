"""Integration tests for skills wiring on the supervisor/runtime invoke path."""

from __future__ import annotations

import json
import logging
from contextlib import closing
from pathlib import Path

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from lily.agents.lily_supervisor import LilySupervisor, echo_tool
from lily.runtime.agent_runtime import AgentRuntime
from lily.runtime.config_loader import ConfigLoadError
from lily.runtime.config_schema import (
    ModelProfileConfig,
    ModelProvider,
    RuntimeConfig,
    SkillsConfig,
)
from lily.runtime.logging_setup import clear_skill_telemetry_handlers
from lily.runtime.model_factory import ModelBuilder, ModelFactory
from lily.runtime.skill_loader import build_skill_bundle
from lily.runtime.skill_retrieve_tool import SKILL_RETRIEVE_TOOL_ID, skill_retrieve


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


pytestmark = pytest.mark.integration


def test_supervisor_load_tools_omits_skill_retrieve_when_skills_disabled(
    tmp_path: Path,
) -> None:
    """Catalog may define skill_retrieve but it is not registered without skills."""
    # Arrange - minimal tool catalog with skill_retrieve and echo_tool definitions
    tools_path = tmp_path / "tools.toml"
    tools_path.write_text(
        "[[definitions]]\n"
        'id = "skill_retrieve"\n'
        'source = "python"\n'
        'target = "lily.runtime.skill_retrieve_tool:skill_retrieve"\n'
        "\n"
        "[[definitions]]\n"
        'id = "echo_tool"\n'
        'source = "python"\n'
        'target = "lily.agents.lily_supervisor:echo_tool"\n',
        encoding="utf-8",
    )
    # Act - resolve catalog while skills subsystem is off
    resolved = LilySupervisor._load_tools_from_catalog(
        tools_path,
        {},
        skills_enabled=False,
    )
    names = [LilySupervisor._resolved_tool_name(t) for t in resolved]
    # Assert - retrieval tool is omitted; other tools remain
    assert SKILL_RETRIEVE_TOOL_ID not in names
    assert "echo_tool" in names


def test_effective_runtime_config_strips_skill_retrieve_when_skills_disabled() -> None:
    """Allowlist must not reference skill_retrieve when the tool is not registered."""
    # Arrange - runtime config whose allowlist includes skill_retrieve
    cfg = RuntimeConfig.model_validate(
        {
            "schema_version": 1,
            "agent": {"name": "t", "system_prompt": "x"},
            "models": {
                "profiles": {
                    "default": {
                        "provider": "openai",
                        "model": "m",
                        "temperature": 0.1,
                        "timeout_seconds": 30,
                    },
                    "long_context": {
                        "provider": "openai",
                        "model": "m2",
                        "temperature": 0.1,
                        "timeout_seconds": 30,
                    },
                },
                "routing": {
                    "enabled": False,
                    "default_profile": "default",
                    "long_context_profile": "long_context",
                    "complexity_threshold": 50,
                },
            },
            "tools": {"allowlist": ["echo_tool", SKILL_RETRIEVE_TOOL_ID]},
            "policies": {
                "max_iterations": 10,
                "max_model_calls": 10,
                "max_tool_calls": 10,
            },
            "logging": {"level": "INFO"},
        }
    )
    # Act - compute effective config for disabled skills
    effective = LilySupervisor._effective_runtime_config(
        cfg,
        skills_enabled=False,
    )
    # Assert - skill_retrieve is stripped; echo_tool remains
    assert SKILL_RETRIEVE_TOOL_ID not in effective.tools.allowlist
    assert "echo_tool" in effective.tools.allowlist


def test_effective_runtime_config_rejects_skill_retrieve_only_allowlist() -> None:
    """Operator error: skill_retrieve alone in allowlist cannot work with skills off."""
    # Arrange - allowlist contains only skill_retrieve
    cfg = RuntimeConfig.model_validate(
        {
            "schema_version": 1,
            "agent": {"name": "t", "system_prompt": "x"},
            "models": {
                "profiles": {
                    "default": {
                        "provider": "openai",
                        "model": "m",
                        "temperature": 0.1,
                        "timeout_seconds": 30,
                    },
                    "long_context": {
                        "provider": "openai",
                        "model": "m2",
                        "temperature": 0.1,
                        "timeout_seconds": 30,
                    },
                },
                "routing": {
                    "enabled": False,
                    "default_profile": "default",
                    "long_context_profile": "long_context",
                    "complexity_threshold": 50,
                },
            },
            "tools": {"allowlist": [SKILL_RETRIEVE_TOOL_ID]},
            "policies": {
                "max_iterations": 10,
                "max_model_calls": 10,
                "max_tool_calls": 10,
            },
            "logging": {"level": "INFO"},
        }
    )
    # Act - attempt to strip skill_retrieve from allowlist with skills disabled
    with pytest.raises(ConfigLoadError) as err:
        LilySupervisor._effective_runtime_config(cfg, skills_enabled=False)

    # Assert - deterministic operator-facing message
    assert "tools.allowlist cannot include only" in str(err.value)


def test_agent_runtime_skill_trace_records_successful_retrieval(tmp_path: Path) -> None:
    """Catalog + tool-call loop yields trace entries for skill_retrieve success."""
    # Arrange - one skill package and a fake model that calls skill_retrieve
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

    fake_model = ToolCapableFakeModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": SKILL_RETRIEVE_TOOL_ID,
                        "args": {"name": "listed-skill"},
                        "id": "c1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="done"),
        ]
    )
    runtime = AgentRuntime(
        config=_runtime_config(
            allowlist=[SKILL_RETRIEVE_TOOL_ID],
            routing_enabled=False,
        ),
        tools=[skill_retrieve],
        model_factory=_model_factory(
            {"default-model": fake_model, "long-model": fake_model}
        ),
        skill_bundle=bundle,
    )
    # Act - run prompt through agent (tool loop executes skill_retrieve)
    with closing(runtime):
        result = runtime.run("retrieve the skill")

    # Assert - trace records successful retrieval metadata
    assert result.skill_trace.skills_enabled is True
    assert result.skill_trace.catalog_injected is True
    assert len(result.skill_trace.retrievals) == 1
    entry = result.skill_trace.retrievals[0]
    assert entry.outcome == "success"
    assert entry.name == "listed-skill"
    assert entry.reference_subpath is None


def test_skill_telemetry_emits_retrieval_flow_events(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Key F7 telemetry events appear during catalog + retrieval success path."""
    # Arrange - one skill package, telemetry logger at INFO, tool-call fake model
    clear_skill_telemetry_handlers()
    caplog.set_level(logging.INFO, "lily.skill.telemetry")
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

    fake_model = ToolCapableFakeModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": SKILL_RETRIEVE_TOOL_ID,
                        "args": {"name": "listed-skill"},
                        "id": "c1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="done"),
        ]
    )
    runtime = AgentRuntime(
        config=_runtime_config(
            allowlist=[SKILL_RETRIEVE_TOOL_ID],
            routing_enabled=False,
        ),
        tools=[skill_retrieve],
        model_factory=_model_factory(
            {"default-model": fake_model, "long-model": fake_model}
        ),
        skill_bundle=bundle,
    )
    # Act - run prompt so discovery, catalog injection, and retrieval all fire
    with closing(runtime):
        runtime.run("retrieve the skill")

    # Assert - JSON telemetry lines include discovery, catalog, and retrieval flow
    telemetry_names = {
        json.loads(rec.getMessage())["event"]
        for rec in caplog.records
        if rec.name == "lily.skill.telemetry"
    }
    assert "skill_discovered" in telemetry_names
    assert "skill_catalog_injected" in telemetry_names
    assert "skill_selected" in telemetry_names
    assert "skill_loaded" in telemetry_names
    assert "skill_executed" in telemetry_names


def test_agent_runtime_skill_trace_records_policy_denial(tmp_path: Path) -> None:
    """Denied retrieval surfaces as error outcome in trace (no content leak)."""
    # Arrange - skill exists but is denylisted; model still invokes retrieval
    skills_root = tmp_path / "skills"
    pkg = skills_root / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "SKILL.md").write_text(
        '---\nname: blocked-skill\ndescription: "Blocked."\n---\n# Body\n',
        encoding="utf-8",
    )
    cfg = SkillsConfig(
        enabled=True,
        roots={"repository": [str(skills_root.relative_to(tmp_path))]},
        scopes_precedence=["repository", "user", "system"],
        denylist=["blocked-skill"],
    )
    bundle = build_skill_bundle(cfg, tmp_path)
    assert bundle is not None

    fake_model = ToolCapableFakeModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": SKILL_RETRIEVE_TOOL_ID,
                        "args": {"name": "blocked-skill"},
                        "id": "c1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="stopped"),
        ]
    )
    runtime = AgentRuntime(
        config=_runtime_config(
            allowlist=[SKILL_RETRIEVE_TOOL_ID],
            routing_enabled=False,
        ),
        tools=[skill_retrieve],
        model_factory=_model_factory(
            {"default-model": fake_model, "long-model": fake_model}
        ),
        skill_bundle=bundle,
    )
    # Act - execute prompt so the agent runs the denylisted retrieval tool call
    with closing(runtime):
        result = runtime.run("try blocked skill")

    # Assert - trace shows error outcome with policy detail
    assert len(result.skill_trace.retrievals) == 1
    denied = result.skill_trace.retrievals[0]
    assert denied.outcome == "error"
    assert denied.detail is not None
    assert "blocked-skill" in denied.detail


def test_agent_runtime_no_skill_bundle_neutral_trace() -> None:
    """Skills disabled yields empty trace and no catalog flag."""
    # Arrange - runtime without skill bundle (skills off)
    runtime = AgentRuntime(
        config=_runtime_config(allowlist=["echo_tool"], routing_enabled=False),
        tools=[echo_tool],
        model_factory=_model_factory(
            {
                "default-model": ToolCapableFakeModel(
                    responses=[AIMessage(content="ok")]
                ),
                "long-model": ToolCapableFakeModel(responses=[AIMessage(content="ok")]),
            }
        ),
        skill_bundle=None,
    )
    # Act - run without skills bundle
    with closing(runtime):
        result = runtime.run("hello")

    # Assert - neutral skill trace
    assert result.skill_trace.skills_enabled is False
    assert result.skill_trace.catalog_injected is False
    assert result.skill_trace.retrievals == ()


def test_skills_enabled_empty_registry_catalog_not_injected(tmp_path: Path) -> None:
    """skills.enabled with no discoverable packages keeps catalog_injected false."""
    # Arrange - enabled skills with an empty root (no SKILL.md packages)
    empty_root = tmp_path / "empty"
    empty_root.mkdir()
    cfg = SkillsConfig(
        enabled=True,
        roots={"repository": [str(empty_root.relative_to(tmp_path))]},
        scopes_precedence=["repository", "user", "system"],
    )
    bundle = build_skill_bundle(cfg, tmp_path)
    assert bundle is not None

    runtime = AgentRuntime(
        config=_runtime_config(
            allowlist=[SKILL_RETRIEVE_TOOL_ID], routing_enabled=False
        ),
        tools=[skill_retrieve],
        model_factory=_model_factory(
            {
                "default-model": ToolCapableFakeModel(
                    responses=[AIMessage(content="noop")]
                ),
                "long-model": ToolCapableFakeModel(
                    responses=[AIMessage(content="noop")]
                ),
            }
        ),
        skill_bundle=bundle,
    )
    # Act - run with empty skill index
    with closing(runtime):
        result = runtime.run("x")

    # Assert - skills on but no catalog text to inject
    assert result.skill_trace.skills_enabled is True
    assert result.skill_trace.catalog_injected is False
