"""Unit tests for tooling composition root."""

from __future__ import annotations

from pathlib import Path

import pytest

from lily.config import SecuritySettings
from lily.runtime.executors.llm_orchestration import LlmOrchestrationExecutor
from lily.runtime.executors.tool_dispatch import ToolDispatchExecutor
from lily.runtime.executors.tool_dispatch_components import (
    BuiltinToolProvider,
    McpToolProvider,
    PluginToolProvider,
)
from lily.runtime.runtime_dependencies import ToolingSpec
from lily.runtime.tooling_factory import ToolingFactory
from lily.skills.types import InvocationMode


@pytest.mark.unit
def test_tooling_factory_builds_skill_invoker_with_expected_executors() -> None:
    """Tooling factory should compose llm + tool dispatch executors."""
    # Arrange - factory and deterministic spec
    factory = ToolingFactory()
    spec = ToolingSpec(
        security=SecuritySettings(),
        security_prompt=None,
        project_root=Path.cwd(),
    )

    # Act - build tooling bundle
    bundle = factory.build(spec)

    # Assert - invoker has expected executors mapped by mode
    executor_types = {type(value) for value in bundle.skill_invoker._executors.values()}
    assert LlmOrchestrationExecutor in executor_types
    assert ToolDispatchExecutor in executor_types


@pytest.mark.unit
def test_tooling_factory_binds_expected_executor_modes() -> None:
    """Tooling factory should bind exactly llm_orchestration and tool_dispatch modes."""
    # Arrange - factory and deterministic spec
    factory = ToolingFactory()
    spec = ToolingSpec(
        security=SecuritySettings(),
        security_prompt=None,
        project_root=Path.cwd(),
    )

    # Act - build tooling bundle
    bundle = factory.build(spec)

    # Assert - skill invoker map keys match expected invocation modes
    assert set(bundle.skill_invoker._executors) == {
        InvocationMode.LLM_ORCHESTRATION,
        InvocationMode.TOOL_DISPATCH,
    }


@pytest.mark.unit
def test_tooling_factory_builds_tool_dispatch_with_all_provider_ids() -> None:
    """Tool dispatch executor should include builtin, mcp, and plugin providers."""
    # Arrange - factory and deterministic spec
    factory = ToolingFactory()
    spec = ToolingSpec(
        security=SecuritySettings(),
        security_prompt=None,
        project_root=Path.cwd(),
    )

    # Act - build tooling bundle and resolve dispatch executor
    bundle = factory.build(spec)
    executor = bundle.skill_invoker._executors[InvocationMode.TOOL_DISPATCH]
    assert isinstance(executor, ToolDispatchExecutor)

    # Assert - all expected provider ids are wired
    assert set(executor._providers) == {"builtin", "mcp", "plugin"}
    assert isinstance(executor._providers["builtin"], BuiltinToolProvider)
    assert isinstance(executor._providers["mcp"], McpToolProvider)
    assert isinstance(executor._providers["plugin"], PluginToolProvider)
