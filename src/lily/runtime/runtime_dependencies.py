"""Runtime composition bundles and factory specs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from langgraph.checkpoint.base import BaseCheckpointSaver

from lily.commands.registry import CommandRegistry
from lily.config import SecuritySettings
from lily.jobs import JobExecutor, JobSchedulerRuntime
from lily.memory import EvidenceChunkingSettings
from lily.runtime.conversation import ConversationExecutor
from lily.runtime.security import SecurityPrompt
from lily.runtime.skill_invoker import SkillInvoker
from lily.session.models import HistoryCompactionBackend


@dataclass(frozen=True)
class ToolingSpec:
    """Inputs required to compose tooling/runtime execution stack."""

    security: SecuritySettings
    security_prompt: SecurityPrompt | None
    project_root: Path


@dataclass(frozen=True)
class ToolingBundle:
    """Composed tooling dependencies used by command registry."""

    skill_invoker: SkillInvoker


@dataclass(frozen=True)
class JobsSpec:
    """Inputs required to compose jobs execution and scheduler runtime."""

    workspace_root: Path
    scheduler_enabled: bool


@dataclass(frozen=True)
class JobsBundle:
    """Composed jobs dependencies used by command registry and facade."""

    jobs_executor: JobExecutor
    runs_root: Path
    scheduler_control: JobSchedulerRuntime | None
    scheduler_runtime: JobSchedulerRuntime | None


@dataclass(frozen=True)
class ConversationRuntimeSpec:
    """Inputs required to compose conversation execution runtime."""

    conversation_executor: ConversationExecutor | None
    conversation_checkpointer: BaseCheckpointSaver | None
    compaction_backend: HistoryCompactionBackend
    compaction_max_tokens: int
    evidence_chunking: EvidenceChunkingSettings | None


@dataclass(frozen=True)
class RuntimeDependencies:
    """Fully composed runtime dependencies for thin facade coordination."""

    command_registry: CommandRegistry
    conversation_executor: ConversationExecutor
    jobs_scheduler_runtime: JobSchedulerRuntime | None = None
