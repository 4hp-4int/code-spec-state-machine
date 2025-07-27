"""Factory for creating AI provider instances."""

from ..config import AIProviderConfig
from ..exceptions import ConfigurationError
from .base import AIProvider
from .openai_provider import OpenAIProvider


class AIProviderFactory:
    """Factory for creating AI provider instances."""

    _providers = {
        "openai": OpenAIProvider,
    }

    @classmethod
    def create_provider(cls, provider_config: AIProviderConfig) -> AIProvider:
        """Create an AI provider instance from configuration.

        Args:
            provider_config: Configuration for the provider

        Returns:
            Configured AI provider instance

        Raises:
            ConfigurationError: If provider type is unknown or configuration is invalid
        """
        provider_type = provider_config.provider_type.lower()

        if provider_type not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ConfigurationError(
                f"Unknown AI provider type: {provider_type}. "
                f"Available providers: {available}"
            )

        provider_class = cls._providers[provider_type]

        # Convert pydantic model to dict for provider
        config_dict = provider_config.model_dump()

        try:
            return provider_class(config_dict)
        except Exception as e:
            raise ConfigurationError(
                f"Failed to create {provider_type} provider: {e}"
            ) from e

    @classmethod
    def get_available_providers(cls) -> list[str]:
        """Get list of available provider types.

        Returns:
            List of provider type names
        """
        return list(cls._providers.keys())

    @classmethod
    def register_provider(
        cls, provider_type: str, provider_class: type[AIProvider]
    ) -> None:
        """Register a new AI provider type.

        Args:
            provider_type: Name of the provider type
            provider_class: Provider class that inherits from AIProvider
        """
        cls._providers[provider_type.lower()] = provider_class
