"""Transcript widget for chat-style TUI rendering."""

from __future__ import annotations

from textual.widgets import RichLog


class TranscriptLog(RichLog):
    """RichLog extension with plain-text history for assertions and UX."""

    history: list[str]

    def append_entry(self, speaker: str, message: str) -> None:
        """Append one transcript line and retain plain-text history.

        Args:
            speaker: Label for the message speaker.
            message: Message text to append.
        """
        normalized = message.strip()
        rendered = f"[{speaker}] {normalized}"
        if not hasattr(self, "history"):
            self.history = []
        self.history.append(rendered)
        self.write(rendered)
