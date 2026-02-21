"""Unit tests for tooling composition root."""

from __future__ import annotations

from pathlib import Path

import pytest

from lily.config import SecuritySettings
from lily.runtime.executors.llm_orchestration import LlmOrchestrationExecutor
from lily.runtime.executors.tool_dispatch import ToolDispatchExecutor
from lily.runtime.runtime_dependencies import ToolingSpec
from lily.runtime.tooling_factory import ToolingFactory


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
