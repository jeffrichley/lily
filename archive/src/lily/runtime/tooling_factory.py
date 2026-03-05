"""Composition root for tooling executors and skill invocation stack."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from lily.runtime.executors.llm_orchestration import LlmOrchestrationExecutor
from lily.runtime.executors.tool_dispatch import (
    AddTool,
    BuiltinToolProvider,
    McpToolProvider,
    MultiplyTool,
    PluginToolProvider,
    SubtractTool,
    ToolContract,
    ToolDispatchExecutor,
)
from lily.runtime.llm_backend import LangChainBackend
from lily.runtime.plugin_runner import DockerPluginRunner
from lily.runtime.runtime_dependencies import ToolingBundle, ToolingSpec
from lily.runtime.security import (
    SecurityApprovalStore,
    SecurityGate,
    SecurityHashService,
    SecurityPreflightScanner,
)
from lily.runtime.skill_invoker import SkillInvoker


class ToolingFactory:
    """Compose deterministic tooling dependencies for runtime command execution."""

    def build(self, spec: ToolingSpec) -> ToolingBundle:
        """Build tooling bundle from composition spec.

        Args:
            spec: Tooling composition spec.

        Returns:
            Composed tooling bundle.
        """
        llm_backend = LangChainBackend()
        tools = cast(
            tuple[ToolContract, ...],
            (
                AddTool(),
                SubtractTool(),
                MultiplyTool(),
            ),
        )
        providers = (
            BuiltinToolProvider(tools=tools),
            McpToolProvider(),
            PluginToolProvider(
                security_gate=SecurityGate(
                    hash_service=SecurityHashService(
                        sandbox=spec.security.sandbox,
                        project_root=Path(spec.project_root),
                    ),
                    preflight=SecurityPreflightScanner(),
                    store=SecurityApprovalStore(
                        sqlite_path=Path(spec.security.sandbox.sqlite_path)
                    ),
                    prompt=spec.security_prompt,
                    sandbox=spec.security.sandbox,
                ),
                runner=DockerPluginRunner(sandbox=spec.security.sandbox),
            ),
        )
        executors = (
            LlmOrchestrationExecutor(llm_backend),
            ToolDispatchExecutor(providers=providers),
        )
        return ToolingBundle(skill_invoker=SkillInvoker(executors=executors))
