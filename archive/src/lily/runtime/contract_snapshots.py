"""Deterministic contract-envelope snapshot builders."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from lily.commands.types import CommandResult
from lily.runtime.executors.llm_orchestration import LlmOrchestrationExecutor
from lily.runtime.executors.tool_dispatch import (
    AddTool,
    BuiltinToolProvider,
    ToolContract,
    ToolDispatchExecutor,
)
from lily.runtime.llm_backend.base import (
    BackendUnavailableError,
    LlmBackend,
    LlmRunRequest,
    LlmRunResponse,
)
from lily.session.models import ModelConfig, Session
from lily.skills.types import InvocationMode, SkillEntry, SkillSnapshot, SkillSource


class _UnavailableBackend(LlmBackend):
    """Test backend that deterministically fails as unavailable."""

    def run(self, request: LlmRunRequest) -> LlmRunResponse:
        """Raise backend unavailable error for deterministic snapshot coverage.

        Args:
            request: Normalized LLM run request.

        Raises:
            BackendUnavailableError: Always raised for snapshot fixture behavior.
        """
        del request
        raise BackendUnavailableError("offline")


def build_contract_snapshot_payload() -> dict[str, object]:
    """Build deterministic contract snapshot payload.

    Returns:
        Snapshot payload with stable envelope examples.
    """
    session = Session(
        session_id="snapshot-session",
        active_agent="default",
        skill_snapshot=SkillSnapshot(version="v-snapshot", skills=()),
        model_config=ModelConfig(model_name="openai:test"),
    )
    add_entry = SkillEntry(
        name="add",
        source=SkillSource.BUNDLED,
        path=Path("/skills/add/SKILL.md"),
        invocation_mode=InvocationMode.TOOL_DISPATCH,
        command_tool_provider="builtin",
        command_tool="add",
    )
    dispatch = ToolDispatchExecutor(
        providers=(
            BuiltinToolProvider(
                tools=cast(
                    tuple[ToolContract, ...],
                    (AddTool(),),
                )
            ),
        )
    )
    llm_entry = SkillEntry(
        name="echo",
        source=SkillSource.BUNDLED,
        path=Path("/skills/echo/SKILL.md"),
        invocation_mode=InvocationMode.LLM_ORCHESTRATION,
    )
    llm = LlmOrchestrationExecutor(_UnavailableBackend())

    envelopes = {
        "tool_ok": _serialize_result(dispatch.execute(add_entry, session, "2+2")),
        "tool_input_invalid": _serialize_result(
            dispatch.execute(add_entry, session, "bad input")
        ),
        "llm_backend_unavailable": _serialize_result(
            llm.execute(llm_entry, session, "hello")
        ),
    }
    payload = {"version": 1, "envelopes": envelopes}
    return cast(
        dict[str, object],
        json.loads(json.dumps(payload, sort_keys=True)),
    )


def write_contract_snapshot(path: Path) -> None:
    """Write contract snapshot payload to disk.

    Args:
        path: Snapshot output file path.
    """
    payload = build_contract_snapshot_payload()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _serialize_result(result: CommandResult) -> dict[str, object]:
    """Serialize one command result for snapshot fixture.

    Args:
        result: Command result payload.

    Returns:
        JSON-compatible envelope mapping.
    """
    return {
        "status": result.status.value,
        "code": result.code,
        "message": result.message,
        "data": result.data or {},
    }
