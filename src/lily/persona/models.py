"""Persona profile models and deterministic catalog contracts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from lily.prompting import PersonaStyleLevel


class PersonaProfile(BaseModel):
    """Normalized persona profile loaded from persona markdown."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    persona_id: str = Field(min_length=1)
    summary: str = ""
    default_style: PersonaStyleLevel = PersonaStyleLevel.BALANCED
    instructions: str = Field(min_length=1)


class PersonaCatalog(BaseModel):
    """Deterministic sorted persona catalog snapshot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    personas: tuple[PersonaProfile, ...] = ()

    def get(self, persona_id: str) -> PersonaProfile | None:
        """Return one profile by exact persona id.

        Args:
            persona_id: Persona identifier.

        Returns:
            Matching profile when present.
        """
        for profile in self.personas:
            if profile.persona_id == persona_id:
                return profile
        return None
