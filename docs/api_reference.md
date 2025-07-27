# API Reference

## CLI Commands

### `generate` - Generate Specifications

Generate a new programming specification from a prompt.

```bash
agentic-spec generate [PROMPT] [OPTIONS]
```

**Arguments:**
- `PROMPT` (optional): Programming task prompt. If not provided, reads from stdin or enters interactive mode.

**Options:**
- `--inherits TEMPLATE...`: Base templates to inherit from
- `--project NAME`: Project name for context (default: "project")
- `--user-role ROLE`: User role context (e.g., "solo developer", "team lead")
- `--target-audience AUDIENCE`: Target audience (e.g., "solo developer", "enterprise team")
- `--tone TONE`: Desired tone ("practical", "detailed", "beginner-friendly")
- `--complexity LEVEL`: Complexity level ("simple", "intermediate", "advanced")
- `--feedback`: Enable interactive feedback collection
- `--dry-run`: Preview generation without saving to file
- `--spec-templates-dir PATH`: YAML spec templates directory (default: "spec-templates")
- `--templates-dir PATH`: Alias for `--spec-templates-dir` (legacy compatibility)
- `--specs-dir PATH`: Generated specs directory (default: "specs")
- `--config PATH`: Path to configuration file
- `--set KEY=VALUE`: Override config values (e.g., `--set prompt_settings.temperature=0.2`)

**Examples:**
```bash
# Basic generation
agentic-spec generate "Add JWT authentication to user API"

# With template inheritance
agentic-spec generate "Add data export" --inherits web-api base-coding-standards

# With context customization
agentic-spec generate "Create dashboard" --user-role "senior developer" --complexity "advanced"

# Interactive mode
agentic-spec generate
# Type multi-line prompt, then Ctrl+D (Unix) or Ctrl+Z (Windows)

# Piped input
echo "Add logging system" | agentic-spec generate

# Configuration override
agentic-spec generate "task" --set prompt_settings.temperature=0.1
```

**Exit Codes:**
- `0`: Success
- `1`: Application error (configuration, template, or generation failure)
- `2`: Invalid command arguments

### `expand` - Expand Implementation Steps

Expand an implementation step into a detailed sub-specification.

```bash
agentic-spec expand SPEC_ID:STEP_INDEX [OPTIONS]
```

**Arguments:**
- `SPEC_ID:STEP_INDEX`: Specification ID and step index to expand (e.g., "abc123:2")

**Options:**
- `--spec-templates-dir PATH`: YAML spec templates directory
- `--specs-dir PATH`: Specs directory
- `--config PATH`: Configuration file path

**Examples:**
```bash
# Expand step 1 of specification abc123
agentic-spec expand abc123:1

# Expand with custom directories
agentic-spec expand def456:0 --specs-dir ./project-specs
```

### `review` - List Specifications

List available specifications for review.

```bash
agentic-spec review [OPTIONS]
```

**Options:**
- `--specs-dir PATH`: Generated specs directory

**Example:**
```bash
agentic-spec review
```

**Output:**
```
📋 Available specifications:
  0: 🚀 JWT authentication implementation (abc123)
  1: 📝 Data export functionality (def456)
  2: ⚙️ Logging system enhancement (ghi789)
```

### `graph` - Visualization

Display specification dependency graph and statistics.

```bash
agentic-spec graph [OPTIONS]
```

**Options:**
- `--specs-dir PATH`: Specs directory

**Example:**
```bash
agentic-spec graph
```

### `publish` - Mark as Implemented

Mark a specification as implemented and update its status.

```bash
agentic-spec publish SPEC_ID [OPTIONS]
```

**Arguments:**
- `SPEC_ID`: Specification ID to publish

**Options:**
- `--specs-dir PATH`: Specs directory

**Example:**
```bash
agentic-spec publish abc123
```

### `templates` - Create Base Templates

Create base templates for common project patterns.

```bash
agentic-spec templates [OPTIONS]
```

**Options:**
- `--project NAME`: Project name (default: "project")
- `--spec-templates-dir PATH`: Templates directory (default: "spec-templates")

**Example:**
```bash
agentic-spec templates --project myproject
```

**Generated Templates:**
- `agentic-spec-foundation.yaml`: Auto-synced project foundation
- `base-coding-standards.yaml`: General coding standards
- `web-api.yaml`: REST API development patterns
- `cli-application.yaml`: Command-line tool patterns
- `data-analysis.yaml`: Data analysis project patterns
- `machine-learning.yaml`: ML project patterns

### `template` - Template Management

Manage and inspect templates.

```bash
agentic-spec template COMMAND [OPTIONS]
```

**Commands:**
- `list`: List available templates
- `info --template NAME`: Show template information

**Examples:**
```bash
# List templates
agentic-spec template list

# Show template details
agentic-spec template info --template web-api
```

### `validate` - Template Validation

Validate all templates for correctness and structure.

```bash
agentic-spec validate [OPTIONS]
```

**Options:**
- `--spec-templates-dir PATH`: Templates directory

**Example:**
```bash
agentic-spec validate
```

### `init` - Project Initialization

Initialize a new agentic-spec project with interactive setup.

```bash
agentic-spec init [OPTIONS]
```

**Options:**
- `--force`: Overwrite existing configuration
- `--spec-templates-dir PATH`: YAML spec templates directory (default: "spec-templates")
- `--templates-dir PATH`: Alias for `--spec-templates-dir`
- `--prompt-templates-dir PATH`: Text prompt templates directory (default: "prompt-templates")
- `--specs-dir PATH`: Specs directory (default: "specs")

**Example:**
```bash
agentic-spec init --project myproject
```

**Creates:**
- Configuration file (`agentic_spec_config.yaml`)
- Directory structure (`spec-templates/`, `prompt-templates/`, `specs/`)
- Base templates
- Foundation specification

### `config` - Configuration Management

Manage application configuration.

```bash
agentic-spec config COMMAND [OPTIONS]
```

**Commands:**
- `init [--force]`: Create default configuration file
- `show`: Show current configuration
- `validate`: Validate configuration file

**Examples:**
```bash
# Create default config
agentic-spec config init

# Show current configuration
agentic-spec config show

# Validate configuration
agentic-spec config validate
```

### `sync-foundation` - Foundation Sync

Sync foundation specification with current codebase state.

```bash
agentic-spec sync-foundation [OPTIONS]
```

**Options:**
- `--force`: Force sync even if current

**Example:**
```bash
agentic-spec sync-foundation
```

### `check-foundation` - Foundation Check

Check if foundation specification needs to be synced.

```bash
agentic-spec check-foundation [OPTIONS]
```

### `render` - Template Rendering

Render a specification using a template.

```bash
agentic-spec render SPEC_ID [OPTIONS]
```

**Arguments:**
- `SPEC_ID`: Specification ID to render

**Options:**
- `--template PATH`: Template file path
- `--output PATH`: Output file path (default: stdout)

**Example:**
```bash
# Render to stdout
agentic-spec render abc123 --template template.html

# Render to file
agentic-spec render abc123 --template template.html --output output.html
```

## Core Classes and Functions

### SpecGenerator Class

**Location:** `agentic_spec.core`

Main class for generating programming specifications.

```python
class SpecGenerator:
    def __init__(
        self,
        spec_templates_dir: Path,
        specs_dir: Path,
        config: AgenticSpecConfig | None = None
    ):
        """Initialize the specification generator.

        Args:
            spec_templates_dir: Directory containing YAML spec templates
            specs_dir: Directory for generated specifications
            config: Configuration object (optional)
        """
```

**Key Methods:**

#### `generate_spec()`
```python
async def generate_spec(
    self,
    prompt: str,
    inherits: list[str] | None = None,
    project_name: str = "project",
    context_params: ContextParameters | None = None,
    collect_feedback: bool = False,
) -> ProgrammingSpec:
    """Generate a programming specification from a prompt.

    Args:
        prompt: The user's task description
        inherits: List of template names to inherit from
        project_name: Name of the project
        context_params: Additional context parameters
        collect_feedback: Whether to collect user feedback

    Returns:
        Generated programming specification

    Raises:
        AIServiceError: If AI generation fails
        TemplateError: If template processing fails
        ValidationError: If generated spec is invalid
    """
```

#### `generate_sub_spec()`
```python
async def generate_sub_spec(
    self,
    parent_spec: ProgrammingSpec,
    step_id: str
) -> ProgrammingSpec:
    """Generate a sub-specification from a parent specification step.

    Args:
        parent_spec: The parent specification
        step_id: ID of the step to expand (format: "spec_id:step_index")

    Returns:
        Generated sub-specification

    Raises:
        ValueError: If step_id is invalid
        AIServiceError: If AI generation fails
    """
```

#### `save_spec()`
```python
def save_spec(self, spec: ProgrammingSpec) -> Path:
    """Save a specification to the specs directory.

    Args:
        spec: Specification to save

    Returns:
        Path to the saved specification file

    Raises:
        FileSystemError: If saving fails
    """
```

#### `load_spec()`
```python
def load_spec(self, spec_id: str) -> ProgrammingSpec:
    """Load a specification by ID.

    Args:
        spec_id: Specification ID to load

    Returns:
        Loaded specification

    Raises:
        FileNotFoundError: If specification doesn't exist
        ValidationError: If specification is invalid
    """
```

#### `list_specs()`
```python
def list_specs(self) -> list[ProgrammingSpec]:
    """List all available specifications.

    Returns:
        List of specification metadata
    """
```

### Configuration Classes

**Location:** `agentic_spec.config`

#### `AgenticSpecConfig`
```python
class AgenticSpecConfig(BaseModel):
    """Complete configuration for agentic-spec."""

    prompt_settings: PromptSettings = Field(default_factory=PromptSettings)
    default_context: DefaultContextParameters = Field(default_factory=DefaultContextParameters)
    workflow: WorkflowSettings = Field(default_factory=WorkflowSettings)
    directories: DirectorySettings = Field(default_factory=DirectorySettings)
    ai_settings: AISettings = Field(default_factory=AISettings)
    custom_settings: dict[str, Any] = Field(default_factory=dict)
```

#### `PromptSettings`
```python
class PromptSettings(BaseModel):
    """Configuration for AI prompt generation."""

    model: str = "gpt-4.1"
    temperature: float = 0.1
    max_tokens: int | None = None
    enable_web_search: bool = True
    system_prompt_template: str | None = None
```

#### `DefaultContextParameters`
```python
class DefaultContextParameters(BaseModel):
    """Default context parameters for specifications."""

    user_role: str = "solo developer"
    target_audience: str = "solo developer"
    desired_tone: str = "practical"
    complexity_level: str = "intermediate"
    time_constraints: str = "production ready"
```

### Data Models

**Location:** `agentic_spec.models`

#### `ProgrammingSpec`
```python
@dataclass
class ProgrammingSpec:
    """Complete programming specification."""

    metadata: SpecMetadata
    context: SpecContext
    requirements: Requirements
    implementation: list[ImplementationStep]
    review_notes: list[str] | None = None
    context_parameters: ContextParameters | None = None
    feedback_history: list[str] = field(default_factory=list)
```

#### `SpecMetadata`
```python
@dataclass
class SpecMetadata:
    """Specification metadata and tracking information."""

    id: str
    title: str
    inherits: list[str] = field(default_factory=list)
    created: str = field(default_factory=lambda: datetime.now().isoformat())
    version: str = "1.0"
    status: str = "draft"  # draft|implemented|published
    parent_spec_id: str | None = None
    child_spec_ids: list[str] | None = None
```

#### `ImplementationStep`
```python
@dataclass
class ImplementationStep:
    """Individual implementation step in a programming specification."""

    task: str
    details: str
    files: list[str]
    acceptance: str
    estimated_effort: str = "medium"  # low|medium|high
    step_id: str | None = None
    sub_spec_id: str | None = None
```

### Template System

#### `TemplateLoader`

**Location:** `agentic_spec.template_loader`

```python
class TemplateLoader:
    """Loads and processes YAML specification templates."""

    def __init__(self, templates_dir: Path):
        """Initialize template loader.

        Args:
            templates_dir: Directory containing template files
        """

    def load_template(self, template_name: str) -> dict[str, Any]:
        """Load a single template by name.

        Args:
            template_name: Name of template (without .yaml extension)

        Returns:
            Template data as dictionary

        Raises:
            FileNotFoundError: If template doesn't exist
            TemplateError: If template is invalid
        """

    def merge_templates(self, template_names: list[str]) -> dict[str, Any]:
        """Merge multiple templates using deep merge strategy.

        Args:
            template_names: List of template names to merge

        Returns:
            Merged template data

        Raises:
            TemplateError: If any template is invalid or merge fails
        """
```

#### `PromptTemplateLoader`

**Location:** `agentic_spec.prompt_template_loader`

```python
class PromptTemplateLoader:
    """Loads and renders Jinja2-based prompt templates."""

    def __init__(self, prompt_templates_dir: Path | None = None):
        """Initialize the prompt template loader.

        Args:
            prompt_templates_dir: Directory containing prompt templates
        """

    def render_template(self, template_name: str, **kwargs: Any) -> str:
        """Render a prompt template with given variables.

        Args:
            template_name: Name of template to render
            **kwargs: Template variables

        Returns:
            Rendered prompt text

        Raises:
            FileNotFoundError: If template doesn't exist
            ValueError: If template rendering fails
        """

    def list_templates(self) -> list[str]:
        """List all available prompt templates.

        Returns:
            List of template names (without .md extension)
        """
```

### AI Provider System

#### `AIProvider` (Abstract Base)

**Location:** `agentic_spec.ai_providers.base`

```python
class AIProvider(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, config: dict[str, Any]):
        """Initialize the AI provider.

        Args:
            config: Provider-specific configuration
        """

    @abstractmethod
    async def generate_response(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any
    ) -> dict[str, Any]:
        """Generate a response from the AI provider.

        Args:
            messages: List of messages in OpenAI format
            **kwargs: Additional parameters

        Returns:
            Response in OpenAI format

        Raises:
            AIServiceError: If generation fails
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and configured.

        Returns:
            True if provider can be used
        """
```

#### `OpenAIProvider`

**Location:** `agentic_spec.ai_providers.openai_provider`

```python
class OpenAIProvider(AIProvider):
    """OpenAI API provider implementation."""

    def __init__(self, config: dict[str, Any]):
        """Initialize OpenAI provider.

        Args:
            config: OpenAI configuration including api_key, model, etc.
        """

    async def generate_response(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any
    ) -> dict[str, Any]:
        """Generate response using OpenAI API.

        Args:
            messages: Conversation messages
            **kwargs: Additional OpenAI parameters

        Returns:
            OpenAI API response
        """
```

### Exception Classes

**Location:** `agentic_spec.exceptions`

#### `AgenticSpecError`
```python
class AgenticSpecError(Exception):
    """Base exception for all agentic-spec errors."""

    def __init__(self, message: str, details: str | None = None):
        """Initialize exception.

        Args:
            message: User-friendly error message
            details: Technical details (optional)
        """
        self.message = message
        self.details = details
        super().__init__(message)
```

#### Specific Exception Types
- `ConfigurationError`: Configuration-related errors
- `TemplateError`: Template processing errors
- `AIServiceError`: AI provider errors
- `FileSystemError`: File operation errors
- `ValidationError`: Data validation errors
- `SpecificationError`: Specification processing errors

### Utility Functions

#### Configuration Management

```python
def load_config(config_file: Path | None = None) -> AgenticSpecConfig:
    """Load configuration from file with validation.

    Args:
        config_file: Path to configuration file (optional)

    Returns:
        Validated configuration object

    Raises:
        ConfigurationError: If configuration is invalid
    """

def parse_cli_overrides(cli_args: list[str]) -> dict[str, Any]:
    """Parse CLI configuration overrides in key=value format.

    Args:
        cli_args: List of key=value strings

    Returns:
        Dictionary of configuration overrides
    """
```

#### Template Management

```python
def create_base_templates(
    templates_dir: Path,
    project_name: str = "project"
) -> None:
    """Create base templates for common project patterns.

    Args:
        templates_dir: Directory to create templates in
        project_name: Name of the project

    Raises:
        FileSystemError: If template creation fails
    """
```

## Error Codes and Messages

### CLI Exit Codes

- **0**: Success
- **1**: Application error (configuration, template, AI, or file system error)
- **2**: Invalid command arguments (Typer framework)

### Common Error Messages

**Configuration Errors:**
- `"OpenAI API key not found"`: Set `OPENAI_API_KEY` environment variable
- `"Configuration file not found"`: Run `agentic-spec config init`
- `"Invalid configuration"`: Check configuration syntax with `agentic-spec config validate`

**Template Errors:**
- `"Template not found: {name}"`: Check available templates with `agentic-spec template list`
- `"Template validation failed"`: Check template syntax with `agentic-spec validate`
- `"Template inheritance cycle detected"`: Fix circular template dependencies

**AI Service Errors:**
- `"AI service unavailable"`: Check API key and network connection
- `"AI generation failed"`: Try again or check prompt complexity
- `"Rate limit exceeded"`: Wait and retry

**File System Errors:**
- `"Permission denied"`: Check file/directory permissions
- `"Directory not found"`: Ensure required directories exist
- `"Invalid path"`: Check path syntax and existence

## Examples and Usage Patterns

### Basic Specification Generation

```python
from agentic_spec.core import SpecGenerator
from agentic_spec.config import load_config

# Initialize
config = load_config()
generator = SpecGenerator(
    spec_templates_dir=Path("spec-templates"),
    specs_dir=Path("specs"),
    config=config
)

# Generate specification
spec = await generator.generate_spec(
    prompt="Add JWT authentication to user API",
    inherits=["web-api", "base-coding-standards"],
    project_name="ecommerce-api"
)

# Save specification
spec_path = generator.save_spec(spec)
print(f"Specification saved: {spec_path}")
```

### Custom AI Provider

```python
from agentic_spec.ai_providers.base import AIProvider

class CustomAIProvider(AIProvider):
    def __init__(self, config: dict[str, Any]):
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url")

    async def generate_response(self, messages: list[dict], **kwargs) -> dict:
        # Implement custom API call
        response = await self.call_custom_api(messages, **kwargs)
        return self.format_response(response)

    def is_available(self) -> bool:
        return bool(self.api_key and self.base_url)

# Register provider
from agentic_spec.ai_providers.factory import AIProviderFactory
AIProviderFactory._providers["custom"] = CustomAIProvider
```

### Template Inheritance

```python
from agentic_spec.template_loader import TemplateLoader

loader = TemplateLoader(Path("spec-templates"))

# Load and merge templates
merged = loader.merge_templates([
    "base-coding-standards",
    "web-api",
    "security-patterns"
])

print(f"Merged template: {merged}")
```

This API reference provides comprehensive documentation for all public interfaces in the agentic-spec system.
