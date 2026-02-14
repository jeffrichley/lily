"""Per-session execution lane primitives."""

from __future__ import annotations

from threading import Lock
from typing import Callable, TypeVar

_T = TypeVar("_T")

_registry_lock = Lock()
_session_lanes: dict[str, Lock] = {}


def run_in_session_lane(session_id: str, fn: Callable[[], _T]) -> _T:
    """Execute function while holding per-session lane lock."""
    with _registry_lock:
        lane = _session_lanes.get(session_id)
        if lane is None:
            lane = Lock()
            _session_lanes[session_id] = lane
    with lane:
        return fn()


def reset_session_lanes() -> None:
    """Reset all lane locks (test-only helper)."""
    with _registry_lock:
        _session_lanes.clear()
