"""Abstract base class for AI service providers."""

from abc import ABC, abstractmethod
from typing import Any


class AIProvider(ABC):
    """Abstract base class for AI service providers.

    This class defines the interface that all AI providers must implement
    to be compatible with the agentic-spec system.
    """

    def __init__(self, config: dict[str, Any]):
        """Initialize the AI provider with configuration.

        Args:
            config: Provider-specific configuration including API keys, endpoints, etc.
        """
        self.config = config
        self._validate_config()

    @abstractmethod
    def _validate_config(self) -> None:
        """Validate the provider-specific configuration.

        Raises:
            ValueError: If the configuration is invalid or missing required fields.
        """

    @abstractmethod
    async def generate_response(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        model: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> str:
        """Generate a response from the AI provider.

        Args:
            prompt: The user prompt to send to the AI
            system_prompt: Optional system prompt to guide the AI behavior
            temperature: Sampling temperature (0.0 to 1.0)
            model: Model name to use (provider-specific)
            tools: Optional tools/functions available to the AI

        Returns:
            The AI-generated response text

        Raises:
            AIServiceError: If the AI service request fails
        """

    @abstractmethod
    def get_default_model(self) -> str:
        """Get the default model name for this provider.

        Returns:
            The default model identifier
        """

    @abstractmethod
    def get_available_models(self) -> list[str]:
        """Get list of available models for this provider.

        Returns:
            List of model identifiers
        """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get the name of this AI provider.

        Returns:
            Human-readable provider name
        """

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is available and properly configured.

        Returns:
            True if the provider can be used, False otherwise
        """
