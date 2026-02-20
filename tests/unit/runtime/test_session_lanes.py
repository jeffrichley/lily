"""Unit tests for per-session execution lane behavior."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

import pytest

from lily.commands.types import CommandResult
from lily.runtime.facade import RuntimeFacade
from lily.runtime.session_lanes import reset_session_lanes
from lily.session.models import ModelConfig, Session
from lily.skills.types import SkillSnapshot


@dataclass
class _TrackingRegistry:
    """Test registry tracking concurrent dispatch execution."""

    active: int = 0
    max_active: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)

    def dispatch(self, call: object, session: Session) -> CommandResult:
        del call
        del session
        with self.lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            time.sleep(0.05)
            return CommandResult.ok("ok")
        finally:
            with self.lock:
                self.active -= 1


def _session(session_id: str) -> Session:
    """Create minimal session fixture."""
    return Session(
        session_id=session_id,
        active_agent="default",
        skill_snapshot=SkillSnapshot(version="v-test", skills=()),
        model_config=ModelConfig(),
    )


@pytest.mark.unit
def test_runtime_serializes_same_session_inputs() -> None:
    """Same session should execute one dispatch at a time."""
    reset_session_lanes()
    registry = _TrackingRegistry()
    runtime = RuntimeFacade(command_registry=registry)  # type: ignore[arg-type]
    session = _session("session-a")

    start = threading.Barrier(2)
    t1 = threading.Thread(
        target=lambda: (start.wait(), runtime.handle_input("/skills", session))
    )
    t2 = threading.Thread(
        target=lambda: (start.wait(), runtime.handle_input("/skills", session))
    )
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert registry.max_active == 1


@pytest.mark.unit
def test_runtime_allows_parallel_inputs_across_sessions() -> None:
    """Different sessions should be able to run in parallel lanes."""
    reset_session_lanes()
    registry = _TrackingRegistry()
    runtime = RuntimeFacade(command_registry=registry)  # type: ignore[arg-type]
    session_a = _session("session-a")
    session_b = _session("session-b")

    start = threading.Barrier(2)
    t1 = threading.Thread(
        target=lambda: (start.wait(), runtime.handle_input("/skills", session_a))
    )
    t2 = threading.Thread(
        target=lambda: (start.wait(), runtime.handle_input("/skills", session_b))
    )
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert registry.max_active >= 2
