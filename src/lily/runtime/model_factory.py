"""Model provider dispatch for LangChain chat models."""

from __future__ import annotations

from collections.abc import Callable

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from lily.runtime.config_schema import ModelProfileConfig, ModelProvider

type ModelBuilder = Callable[[ModelProfileConfig], BaseChatModel]


class ModelFactoryError(ValueError):
    """Raised when model construction fails for a configured profile."""


def _build_openai_model(profile: ModelProfileConfig) -> BaseChatModel:
    """Build an OpenAI model from profile settings.

    Args:
        profile: Validated model profile settings.

    Returns:
        Initialized LangChain chat model.
    """
    return init_chat_model(
        model=profile.model,
        model_provider=profile.provider.value,
        temperature=profile.temperature,
        timeout=profile.timeout_seconds,
    )


def _build_ollama_model(profile: ModelProfileConfig) -> BaseChatModel:
    """Build an Ollama model from profile settings.

    Args:
        profile: Validated model profile settings.

    Returns:
        Initialized LangChain chat model.
    """
    return init_chat_model(
        model=profile.model,
        model_provider=profile.provider.value,
        temperature=profile.temperature,
        timeout=profile.timeout_seconds,
    )


class ModelFactory:
    """Build configured chat model instances via provider registry dispatch."""

    def __init__(
        self,
        builders: dict[ModelProvider, ModelBuilder] | None = None,
    ) -> None:
        """Initialize provider->builder dispatch registry.

        Args:
            builders: Optional provider-to-builder override mapping.
        """
        self._builders: dict[ModelProvider, ModelBuilder] = builders or {
            ModelProvider.OPENAI: _build_openai_model,
            ModelProvider.OLLAMA: _build_ollama_model,
        }

    def create_model(self, profile: ModelProfileConfig) -> BaseChatModel:
        """Create one model instance from profile config.

        Args:
            profile: One validated model profile.

        Returns:
            Initialized chat model for the given profile.

        Raises:
            ModelFactoryError: If provider builder is missing or model init fails.
        """
        builder = self._builders.get(profile.provider)
        if builder is None:
            msg = (
                f"No model builder registered for provider '{profile.provider.value}'."
            )
            raise ModelFactoryError(msg)

        try:
            return builder(profile)
        except Exception as exc:  # pragma: no cover - defensive normalization
            msg = (
                f"Failed to initialize model profile '{profile.model}' for provider "
                f"'{profile.provider.value}': {exc}"
            )
            raise ModelFactoryError(msg) from exc

    def create_models(
        self,
        profiles: dict[str, ModelProfileConfig],
    ) -> dict[str, BaseChatModel]:
        """Create all named profile models.

        Args:
            profiles: Mapping of profile name to profile config.

        Returns:
            Mapping of profile name to initialized chat model.
        """
        return {
            profile_name: self.create_model(profile_config)
            for profile_name, profile_config in profiles.items()
        }
