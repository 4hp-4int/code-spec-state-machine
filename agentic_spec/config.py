"""Configuration system for agentic-spec workflows."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator
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

    spec_templates_dir: str = "spec-templates"
    prompt_templates_dir: str = "prompt-templates"
    specs_dir: str = "specs"
    config_dir: str = "."

    # Legacy support - deprecated
    templates_dir: str | None = None

    def get_spec_templates_dir(self) -> str:
        """Get spec templates directory with legacy fallback."""
        if self.templates_dir is not None:
            # Legacy mode - use old templates_dir
            return self.templates_dir
        return self.spec_templates_dir

    def get_prompt_templates_dir(self) -> str:
        """Get prompt templates directory."""
        return self.prompt_templates_dir


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


class FileCategorization(BaseModel):
    """Configuration for file categorization rules."""

    cli_patterns: list[str] = Field(default_factory=lambda: ["cli", "command", "main"])
    web_ui_patterns: list[str] = Field(
        default_factory=lambda: ["web_ui", "webui", "fastapi", "templates"]
    )
    api_patterns: list[str] = Field(
        default_factory=lambda: ["api", "routes", "endpoints"]
    )
    database_patterns: list[str] = Field(
        default_factory=lambda: ["db", "database", "sqlite", "async_db"]
    )
    migration_patterns: list[str] = Field(
        default_factory=lambda: ["migration", "migrate"]
    )
    test_patterns: list[str] = Field(
        default_factory=lambda: ["test_", "_test", "tests/", "conftest"]
    )
    config_patterns: list[str] = Field(
        default_factory=lambda: ["pyproject.toml", "*.toml", "*.yaml", "*.yml"]
    )
    documentation_patterns: list[str] = Field(
        default_factory=lambda: ["README", "CHANGELOG", "docs/", "*.md", "*.rst"]
    )
    build_patterns: list[str] = Field(
        default_factory=lambda: ["Makefile", "Dockerfile", "*.dockerfile"]
    )

    # Content-based indicators
    cli_content_indicators: list[str] = Field(
        default_factory=lambda: ["typer", "click", "argparse", "@app.command"]
    )
    web_ui_content_indicators: list[str] = Field(
        default_factory=lambda: ["fastapi", "starlette", "@app.route", "HTMLResponse"]
    )
    api_content_indicators: list[str] = Field(
        default_factory=lambda: ["@app.", "APIRouter", "FastAPI"]
    )
    database_content_indicators: list[str] = Field(
        default_factory=lambda: ["sqlite", "aiosqlite", "CREATE TABLE", "async def"]
    )
    migration_content_indicators: list[str] = Field(
        default_factory=lambda: ["migration", "migrate", "schema"]
    )
    test_content_indicators: list[str] = Field(
        default_factory=lambda: ["pytest", "def test_", "class Test"]
    )


class DependencyDetection(BaseModel):
    """Configuration for dependency detection patterns."""

    requirements_files: list[str] = Field(
        default_factory=lambda: [
            "requirements.txt",
            "requirements/*.txt",
            "requirements-*.txt",
        ]
    )
    config_files: list[str] = Field(
        default_factory=lambda: ["pyproject.toml", "setup.py", "setup.cfg"]
    )

    # Package categorization rules
    web_frameworks: list[str] = Field(
        default_factory=lambda: ["fastapi", "uvicorn", "starlette", "flask", "django"]
    )
    database_libs: list[str] = Field(
        default_factory=lambda: [
            "aiosqlite",
            "sqlite3",
            "sqlalchemy",
            "psycopg2",
            "pymongo",
        ]
    )
    template_engines: list[str] = Field(
        default_factory=lambda: ["jinja2", "mako", "chameleon"]
    )
    testing_frameworks: list[str] = Field(
        default_factory=lambda: ["pytest", "pytest-cov", "pytest-asyncio", "unittest"]
    )
    ai_libraries: list[str] = Field(
        default_factory=lambda: ["openai", "anthropic", "transformers", "torch"]
    )
    config_parsers: list[str] = Field(
        default_factory=lambda: ["pyyaml", "toml", "tomllib", "configparser"]
    )
    cli_frameworks: list[str] = Field(
        default_factory=lambda: ["typer", "click", "argparse"]
    )
    visualization_libs: list[str] = Field(
        default_factory=lambda: ["networkx", "matplotlib", "plotly", "seaborn"]
    )

    # Standard library modules to exclude from third-party detection
    stdlib_modules: list[str] = Field(
        default_factory=lambda: [
            "os",
            "sys",
            "re",
            "json",
            "urllib",
            "http",
            "pathlib",
            "typing",
            "asyncio",
            "logging",
            "datetime",
            "collections",
            "itertools",
            "functools",
            "inspect",
            "importlib",
            "unittest",
            "sqlite3",
            "csv",
            "xml",
            "email",
            "html",
            "math",
            "random",
            "string",
            "threading",
            "multiprocessing",
            "subprocess",
            "shutil",
            "tempfile",
            "glob",
            "fnmatch",
            "warnings",
            "traceback",
            "io",
            "contextlib",
            "copy",
            "pickle",
            "struct",
            "zlib",
            "hashlib",
            "hmac",
            "secrets",
            "base64",
            "binascii",
            "uuid",
            "time",
            "calendar",
            "argparse",
            "configparser",
            "tomllib",
        ]
    )


class ProjectAnalysis(BaseModel):
    """Configuration for project analysis behavior."""

    # Skip patterns (support both Windows and Unix paths)
    skip_patterns: list[str] = Field(
        default_factory=lambda: [
            ".venv\\",
            ".venv/",
            "venv\\",
            "venv/",
            "build\\",
            "build/",
            "dist\\",
            "dist/",
            "__pycache__\\",
            "__pycache__/",
            ".git\\",
            ".git/",
            ".pytest_cache\\",
            ".pytest_cache/",
            ".mypy_cache\\",
            ".mypy_cache/",
            "node_modules\\",
            "node_modules/",
        ]
    )

    # Content analysis settings
    content_analysis_enabled: bool = True
    content_analysis_max_size: int = 2000  # bytes

    # Domain inference rules
    domain_patterns: dict[str, str] = Field(
        default_factory=lambda: {
            "full_stack": "Full-stack {language} application with CLI, web UI, and database components",
            "web_cli": "{language} CLI tool with web UI for {domain}",
            "database_cli": "{language} CLI tool with database backend for {domain}",
            "simple_cli": "{language} CLI tool for {domain}",
        }
    )

    # Default project characteristics
    default_language: str = "Python"
    default_domain: str = "AI-powered specification generation"


class SyncFoundationConfig(BaseModel):
    """Configuration for sync-foundation command behavior."""

    file_categorization: FileCategorization = Field(default_factory=FileCategorization)
    dependency_detection: DependencyDetection = Field(
        default_factory=DependencyDetection
    )
    project_analysis: ProjectAnalysis = Field(default_factory=ProjectAnalysis)

    # Foundation template settings
    foundation_template_name: str = Field(
        default="project-foundation", min_length=1, max_length=100
    )
    generate_statistics: bool = True
    include_transitive_dependencies: bool = True
    max_transitive_dependencies: int = Field(default=10, ge=0, le=100)

    # Performance settings
    enable_caching: bool = True
    cache_duration_hours: int = Field(default=24, ge=0, le=168)  # Max 1 week

    @field_validator("foundation_template_name")
    @classmethod
    def validate_template_name(cls, v: str) -> str:
        """Validate foundation template name."""
        if not v.strip():
            raise ValueError("Foundation template name cannot be empty or whitespace")

        # Check for invalid characters
        invalid_chars = {"/", "\\", ":", "*", "?", '"', "<", ">", "|"}
        if any(char in v for char in invalid_chars):
            raise ValueError(
                f"Foundation template name contains invalid characters: {invalid_chars}"
            )

        return v.strip()

    def validate_patterns(self) -> list[str]:
        """Validate all pattern configurations and return list of warnings."""
        warnings = []

        # Validate file categorization patterns
        categorization = self.file_categorization
        all_patterns = (
            categorization.cli_patterns
            + categorization.web_ui_patterns
            + categorization.api_patterns
            + categorization.database_patterns
            + categorization.migration_patterns
            + categorization.test_patterns
            + categorization.config_patterns
            + categorization.documentation_patterns
            + categorization.build_patterns
        )

        # Check for empty patterns
        if not all_patterns:
            warnings.append("No file categorization patterns defined")

        # Check for duplicate patterns across categories
        pattern_counts = {}
        for pattern in all_patterns:
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

        duplicates = [p for p, count in pattern_counts.items() if count > 1]
        if duplicates:
            warnings.append(f"Duplicate patterns found across categories: {duplicates}")

        # Validate dependency detection
        if not self.dependency_detection.requirements_files:
            warnings.append("No requirements file patterns defined")

        # Check for overlap between requirements files and config files
        req_files = set(self.dependency_detection.requirements_files)
        config_files = set(self.dependency_detection.config_files)
        overlap = req_files & config_files
        if overlap:
            warnings.append(
                f"Files listed in both requirements_files and config_files: {overlap}"
            )

        return warnings

    def validate_skip_patterns(self) -> list[str]:
        """Validate skip patterns and return warnings for potential issues."""
        warnings = []
        skip_patterns = self.project_analysis.skip_patterns

        # Check for overly broad patterns
        broad_patterns = ["*", "**", ".*", "*.*"]
        for pattern in skip_patterns:
            if pattern in broad_patterns:
                warnings.append(
                    f"Very broad skip pattern detected: '{pattern}' - may exclude too many files"
                )

        # Check for essential directories being skipped
        essential_dirs = ["src", "lib", "app", "core"]
        for pattern in skip_patterns:
            for essential in essential_dirs:
                if essential in pattern.lower():
                    warnings.append(
                        f"Skip pattern '{pattern}' may exclude essential directory '{essential}'"
                    )

        return warnings


class AgenticSpecConfig(BaseModel):
    """Complete configuration for agentic-spec."""

    prompt_settings: PromptSettings = Field(default_factory=PromptSettings)
    default_context: DefaultContextParameters = Field(
        default_factory=DefaultContextParameters
    )
    workflow: WorkflowSettings = Field(default_factory=WorkflowSettings)
    directories: DirectorySettings = Field(default_factory=DirectorySettings)
    ai_settings: AISettings = Field(default_factory=AISettings)
    sync_foundation: SyncFoundationConfig = Field(default_factory=SyncFoundationConfig)
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
