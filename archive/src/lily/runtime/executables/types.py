"""Protocol and type aliases for executable resolver/dispatcher contracts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from lily.runtime.executables.handlers.base import BaseExecutableHandler
from lily.runtime.executables.models import (
    ExecutableKind,
    ExecutableRef,
    ExecutableRequest,
    ExecutableResult,
)


@runtime_checkable
class ExecutableResolver(Protocol):
    """Resolve caller request intent to a final executable reference."""

    def resolve(self, request: ExecutableRequest) -> ExecutableRef:
        """Resolve request target to one executable reference."""


ExecutableHandlerMap = Mapping[
    ExecutableKind,
    BaseExecutableHandler,
]


@runtime_checkable
class ExecutableDispatcher(Protocol):
    """Dispatch resolved executable requests to registered handlers."""

    def dispatch(self, request: ExecutableRequest) -> ExecutableResult:
        """Dispatch one request and return canonical execution result."""
