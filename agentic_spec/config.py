"""Configuration system for agentic-spec workflows."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError
import yaml


class PromptSettings(BaseModel):
    """Configuration for AI prompt generation."""

    model: str = "gpt-4.1"
    temperature: float = 0.1
    max_tokens: int | None = None
    enable_web_search: bool = True
    system_prompt_template: str | None = None


class DefaultContextParameters(BaseModel):
    """Default context parameters for specifications."""

    user_role: str = "solo developer"
    target_audience: str = "solo developer"
    desired_tone: str = "practical"
    complexity_level: str = "intermediate"
    time_constraints: str = "production ready"


class WorkflowSettings(BaseModel):
    """Configuration for workflow behavior."""

    auto_review: bool = True
    collect_feedback: bool = False
    save_intermediate_steps: bool = True
    enable_step_ids: bool = True
    max_recursion_depth: int = 3


class DirectorySettings(BaseModel):
    """Configuration for directory paths."""

    templates_dir: str = "templates"
    specs_dir: str = "specs"
    config_dir: str = "."


class AIProviderConfig(BaseModel):
    """Configuration for a specific AI provider."""

    provider_type: str  # e.g., "openai", "anthropic", "local"
    api_key: str | None = None
    base_url: str | None = None
    default_model: str | None = None
    timeout: float = 120.0
    custom_settings: dict[str, Any] = Field(default_factory=dict)


class AISettings(BaseModel):
    """Configuration for AI providers."""

    default_provider: str = "openai"
    providers: dict[str, AIProviderConfig] = Field(
        default_factory=lambda: {
            "openai": AIProviderConfig(
                provider_type="openai",
                default_model="gpt-4o-mini",
            )
        }
    )


class AgenticSpecConfig(BaseModel):
    """Complete configuration for agentic-spec."""

    prompt_settings: PromptSettings = Field(default_factory=PromptSettings)
    default_context: DefaultContextParameters = Field(
        default_factory=DefaultContextParameters
    )
    workflow: WorkflowSettings = Field(default_factory=WorkflowSettings)
    directories: DirectorySettings = Field(default_factory=DirectorySettings)
    ai_settings: AISettings = Field(default_factory=AISettings)
    custom_settings: dict[str, Any] = Field(default_factory=dict)


class ConfigManager:
    """Manages loading, validation, and merging of configuration."""

    def __init__(self, config_file: Path | None = None):
        self.config_file = config_file or Path("agentic_spec_config.yaml")
        self._config: AgenticSpecConfig | None = None

    def load_config(self) -> AgenticSpecConfig:
        """Load configuration from file with validation."""
        if self._config is not None:
            return self._config

        # Start with defaults
        config_data = {}

        # Load from file if it exists
        if self.config_file.exists():
            try:
                with self.config_file.open() as f:
                    file_config = yaml.safe_load(f) or {}
                config_data = self._deep_merge(config_data, file_config)
            except yaml.YAMLError as e:
                msg = f"Invalid YAML in config file {self.config_file}: {e}"
                raise ValueError(msg) from e
            except (OSError, UnicodeDecodeError, PermissionError) as e:
                msg = f"Error reading config file {self.config_file}: {e}"
                raise ValueError(msg) from e

        # Validate and create config object
        try:
            self._config = AgenticSpecConfig(**config_data)
        except ValidationError as e:
            msg = f"Configuration validation failed: {e}"
            raise ValueError(msg) from e

        return self._config

    def merge_cli_overrides(
        self, config: AgenticSpecConfig, cli_overrides: dict[str, Any]
    ) -> AgenticSpecConfig:
        """Merge CLI overrides with loaded configuration."""
        if not cli_overrides:
            return config

        # Convert config to dict, merge overrides, then reconstruct
        config_dict = config.model_dump()
        merged_dict = self._deep_merge(config_dict, cli_overrides)

        try:
            return AgenticSpecConfig(**merged_dict)
        except ValidationError as e:
            msg = f"Configuration validation failed after CLI overrides: {e}"
            raise ValueError(msg) from e

    def _deep_merge(
        self, target: dict[str, Any], source: dict[str, Any]
    ) -> dict[str, Any]:
        """Deep merge two dictionaries."""
        result = target.copy()

        for key, value in source.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def save_config(
        self, config: AgenticSpecConfig, file_path: Path | None = None
    ) -> Path:
        """Save configuration to YAML file."""
        output_path = file_path or self.config_file

        # Convert to dict and save
        config_dict = config.model_dump()

        with output_path.open("w") as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)

        return output_path

    def create_default_config_file(self, force: bool = False) -> Path:
        """Create a default configuration file."""
        if self.config_file.exists() and not force:
            msg = f"Configuration file {self.config_file} already exists"
            raise FileExistsError(msg)

        default_config = AgenticSpecConfig()
        return self.save_config(default_config)

    def validate_config_schema(self, config_dict: dict[str, Any]) -> list[str]:
        """Validate configuration against schema and return error messages."""
        try:
            AgenticSpecConfig(**config_dict)
            return []
        except ValidationError as e:
            return [str(error) for error in e.errors()]


def parse_cli_overrides(cli_args: list[str]) -> dict[str, Any]:
    """Parse CLI configuration overrides in key=value format."""
    overrides = {}

    for arg in cli_args:
        if "=" not in arg:
            continue

        key, value = arg.split("=", 1)

        # Handle nested keys (e.g., prompt_settings.temperature=0.2)
        keys = key.split(".")
        current = overrides

        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        # Try to parse value as appropriate type
        final_key = keys[-1]
        try:
            # Try parsing as int
            if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
                current[final_key] = int(value)
            # Try parsing as float
            elif "." in value and all(
                part.isdigit() for part in value.split(".") if part
            ):
                current[final_key] = float(value)
            # Try parsing as boolean
            elif value.lower() in ("true", "false"):
                current[final_key] = value.lower() == "true"
            # Keep as string
            else:
                current[final_key] = value
        except ValueError:
            current[final_key] = value

    return overrides


# Global configuration instance
_config_manager: ConfigManager | None = None


def get_config_manager(config_file: Path | None = None) -> ConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None or config_file is not None:
        _config_manager = ConfigManager(config_file)
    return _config_manager


def load_config(config_file: Path | None = None) -> AgenticSpecConfig:
    """Convenience function to load configuration."""
    return get_config_manager(config_file).load_config()
