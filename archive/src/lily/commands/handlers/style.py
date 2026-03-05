"""Handler for /style."""

from __future__ import annotations

from pydantic import ValidationError

from lily.commands.parser import CommandCall
from lily.commands.types import CommandResult
from lily.prompting import PersonaStyleLevel
from lily.session.models import Session


class StyleCommand:
    """Deterministic `/style` command handler."""

    def execute(self, call: CommandCall, session: Session) -> CommandResult:
        """Set explicit style override for current session.

        Args:
            call: Parsed command call.
            session: Active session.

        Returns:
            Deterministic success/error envelope.
        """
        if len(call.args) != 1:
            return CommandResult.error(
                "Error: /style requires exactly one value: focus|balanced|playful.",
                code="invalid_args",
                data={"command": "style"},
            )
        raw_style = call.args[0].strip().lower()
        try:
            style = PersonaStyleLevel(raw_style)
        except ValueError:
            return CommandResult.error(
                f"Error: invalid style '{raw_style}'. Use focus|balanced|playful.",
                code="style_invalid",
                data={"style": raw_style},
            )
        except ValidationError:  # pragma: no cover - defensive
            return CommandResult.error(
                f"Error: invalid style '{raw_style}'. Use focus|balanced|playful.",
                code="style_invalid",
                data={"style": raw_style},
            )
        session.active_style = style
        return CommandResult.ok(
            f"Session style set to '{style.value}'.",
            code="style_set",
            data={"style": style.value},
        )
