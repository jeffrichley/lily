"""Primary chat screen for Lily textual interface."""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Input

from lily.ui.widgets.transcript import TranscriptLog


class ChatScreen(Screen[None]):
    """Single-screen chat UI with transcript and prompt input."""

    def compose(self) -> ComposeResult:
        """Build screen widget tree.

        Yields:
            Vertical layout containing transcript and input widgets.
        """
        yield Vertical(
            TranscriptLog(id="transcript", wrap=True, highlight=False, markup=False),
            Input(id="prompt_input", placeholder="Ask Lily something..."),
        )

    def on_mount(self) -> None:
        """Focus prompt input and display startup message."""
        prompt_input = self.query_one("#prompt_input", Input)
        prompt_input.focus()
        self.query_one("#transcript", TranscriptLog).append_entry(
            "system",
            "Lily TUI ready. Press Enter to send.",
        )

    @on(Input.Submitted)
    def _handle_prompt_submitted(self, event: Input.Submitted) -> None:
        """Handle prompt submission and append both user and assistant messages.

        Args:
            event: Input submission event carrying entered text.
        """
        prompt = event.value.strip()
        if not prompt:
            return

        event.input.value = ""
        transcript = self.query_one("#transcript", TranscriptLog)
        transcript.append_entry("you", prompt)

        app_runner = self.app
        if not hasattr(app_runner, "run_prompt_for_ui"):
            transcript.append_entry("error", "App does not implement prompt runner.")
            return

        try:
            response = app_runner.run_prompt_for_ui(prompt)
        except Exception as exc:  # pragma: no cover - defensive UI surface
            transcript.append_entry("error", str(exc))
            return

        transcript.append_entry("lily", response)
