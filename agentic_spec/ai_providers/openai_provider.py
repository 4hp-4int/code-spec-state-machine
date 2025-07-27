"""OpenAI AI provider implementation."""

import os
from typing import Any

from ..exceptions import AIServiceError
from .base import AIProvider

try:
    from openai import AsyncOpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class OpenAIProvider(AIProvider):
    """OpenAI AI provider implementation."""

    def __init__(self, config: dict[str, Any]):
        """Initialize OpenAI provider.

        Args:
            config: Configuration including api_key, base_url, etc.
        """
        super().__init__(config)
        if OPENAI_AVAILABLE:
            self.client = AsyncOpenAI(
                api_key=self.config.get("api_key"),
                base_url=self.config.get("base_url"),
                timeout=self.config.get("timeout", 120.0),
            )
        else:
            self.client = None

    def _validate_config(self) -> None:
        """Validate OpenAI configuration."""
        if not OPENAI_AVAILABLE:
            raise ValueError(
                "OpenAI library not available. Install with: pip install openai"
            )

        api_key = self.config.get("api_key") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API key not provided in config or OPENAI_API_KEY environment variable"
            )

    async def generate_response(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        model: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> str:
        """Generate response using OpenAI API."""
        if not self.client:
            raise AIServiceError("OpenAI client not available")

        try:
            model = model or self.get_default_model()

            # Check if this is a Responses API call (with tools)
            if tools:
                response = await self.client.responses.create(
                    model=model,
                    tools=tools,
                    input=f"{system_prompt}\n\n{prompt}" if system_prompt else prompt,
                    temperature=temperature,
                )
                return response.output_text
            # Standard chat completion
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
            )
            return response.choices[0].message.content or ""

        except Exception as e:
            raise AIServiceError(f"OpenAI API error: {e}") from e

    def get_default_model(self) -> str:
        """Get default OpenAI model."""
        return self.config.get("default_model", "gpt-4o-mini")

    def get_available_models(self) -> list[str]:
        """Get available OpenAI models."""
        return [
            "gpt-4.1",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
        ]

    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return "OpenAI"

    @property
    def is_available(self) -> bool:
        """Check if OpenAI provider is available."""
        if not OPENAI_AVAILABLE:
            return False

        try:
            api_key = self.config.get("api_key") or os.getenv("OPENAI_API_KEY")
            return bool(api_key)
        except Exception:
            return False
