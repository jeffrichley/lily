"""Base handler contracts for executable dispatcher registry."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from lily.runtime.executables.models import (
    ExecutableKind,
    ExecutableRequest,
    ExecutableResult,
)


@runtime_checkable
class BaseExecutableHandler(Protocol):
    """Protocol implemented by kind-specific executable handlers."""

    kind: ExecutableKind

    def handle(self, request: ExecutableRequest) -> ExecutableResult:
        """Execute one resolved request and return canonical result."""
