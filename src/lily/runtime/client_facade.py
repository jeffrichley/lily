"""Reusable client-facing facade for Lily runtime/session execution."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from lily.commands.types import CommandResult
from lily.session.models import Session


class RuntimeInputHandler(Protocol):
    """Protocol for runtime handlers that process one input against a session."""

    def handle_input(self, text: str, session: Session) -> CommandResult:
        """Handle one input turn for the provided session.

        Args:
            text: Raw user input text.
            session: Active session state.
        """

    def close(self) -> None:
        """Release runtime resources."""


class ClientRuntimeFacade:
    """Client-facing execution facade for one session/runtime lifecycle."""

    def __init__(
        self,
        *,
        session_builder: Callable[[], Session],
        runtime_builder: Callable[[], RuntimeInputHandler],
        session_persistor: Callable[[Session], None],
    ) -> None:
        """Store lifecycle callbacks used to build and drive execution.

        Args:
            session_builder: Builds or loads active session.
            runtime_builder: Builds runtime handler.
            session_persistor: Persists session after each turn.
        """
        self._session_builder = session_builder
        self._runtime_builder = runtime_builder
        self._session_persistor = session_persistor
        self._session: Session | None = None
        self._runtime: RuntimeInputHandler | None = None

    def run_input(self, text: str) -> CommandResult:
        """Run one input turn and persist session state.

        Args:
            text: Raw user input text.

        Returns:
            Deterministic command result.
        """
        runtime = self._ensure_runtime()
        session = self._ensure_session()
        result = runtime.handle_input(text, session)
        self._session_persistor(session)
        return result

    def start(self) -> None:
        """Eagerly initialize session and runtime.

        Useful for clients that need startup validation/messages before first input.
        """
        self._ensure_session()
        self._ensure_runtime()

    def close(self) -> None:
        """Close runtime if initialized."""
        if self._runtime is None:
            return
        maybe_close = getattr(self._runtime, "close", None)
        if callable(maybe_close):
            maybe_close()

    def _ensure_runtime(self) -> RuntimeInputHandler:
        """Build runtime lazily and reuse across turns.

        Returns:
            Active runtime handler.
        """
        if self._runtime is None:
            self._runtime = self._runtime_builder()
        return self._runtime

    def _ensure_session(self) -> Session:
        """Build/load session lazily and reuse across turns.

        Returns:
            Active session object.
        """
        if self._session is None:
            self._session = self._session_builder()
        return self._session
