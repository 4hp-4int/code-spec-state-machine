# Architecture Documentation

## System Overview

Agentic Spec is designed as a modular, extensible system with clear separation of concerns. The architecture follows modern Python patterns with type safety, dependency injection, and pluggable components.

```
┌─────────────────────────────────────────────────────────────┐
│                     CLI Interface (cli.py)                  │
│                  Typer-based Commands                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                Core Engine (core.py)                        │
│            SpecGenerator + AI Integration                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
    ┌─────────────────┼─────────────────┐
    │                 │                 │
┌───▼────┐    ┌──────▼─────┐    ┌──────▼─────┐
│Template│    │AI Provider │    │Prompt Eng. │
│System  │    │  System    │    │   System   │
└────────┘    └────────────┘    └────────────┘
```

## Core Components

### 1. CLI Layer (`cli.py`)

**Purpose**: User interface and command orchestration

**Key Features**:
- Typer-based modern CLI with auto-generated help
- Multiple input methods (args, stdin, interactive)
- Configuration management and validation
- Error handling with user-friendly messages

**Design Patterns**:
- **Command pattern**: Each CLI command is a separate function
- **Dependency injection**: Configuration and generators passed to commands
- **Error boundaries**: Graceful error handling with appropriate exit codes

```python
@app.command("generate")
async def generate_spec(
    prompt: str | None = Argument(None),
    inherits: list[str] | None = Option(None),
    # ... other options
):
    # Command implementation
```

### 2. Core Engine (`core.py`)

**Purpose**: Central orchestration of specification generation

**Key Components**:
- `SpecGenerator`: Main class for specification generation
- AI integration with fallback mechanisms
- Template inheritance processing
- Sub-specification expansion logic

**Design Patterns**:
- **Strategy pattern**: Pluggable AI providers
- **Template method**: Common generation workflow with customizable steps
- **Builder pattern**: Incremental specification construction

```python
class SpecGenerator:
    def __init__(self, spec_templates_dir, specs_dir, config):
        self.ai_provider = self._initialize_ai_provider()
        self.prompt_template_loader = PromptTemplateLoader(...)
        self.prompt_engineer = PromptEngineer(...)

    async def generate_spec(self, prompt: str, **kwargs) -> ProgrammingSpec:
        # Generation logic
```

### 3. Data Models (`models.py`)

**Purpose**: Type-safe data structures using dataclasses

**Key Models**:
- `ProgrammingSpec`: Complete specification structure
- `ImplementationStep`: Individual task definition
- `SpecMetadata`: Specification metadata and tracking
- `ContextParameters`: Generation context configuration

**Design Patterns**:
- **Data classes**: Immutable, type-safe data structures
- **Value objects**: Encapsulate related data with validation
- **Factory methods**: Alternative constructors for different use cases

```python
@dataclass
class ProgrammingSpec:
    metadata: SpecMetadata
    context: SpecContext
    requirements: Requirements
    implementation: list[ImplementationStep]
    review_notes: list[str] | None = None
```

### 4. Configuration System (`config.py`)

**Purpose**: Centralized configuration with validation

**Key Features**:
- Pydantic-based configuration with validation
- Hierarchical configuration (file → env → CLI overrides)
- Type-safe configuration access
- Deep merge for complex settings

**Design Patterns**:
- **Settings pattern**: Centralized configuration object
- **Validation pattern**: Pydantic validators ensure correctness
- **Override pattern**: CLI and environment can override file settings

```python
class AgenticSpecConfig(BaseModel):
    prompt_settings: PromptSettings = Field(default_factory=PromptSettings)
    default_context: DefaultContextParameters = Field(...)
    workflow: WorkflowSettings = Field(...)
    directories: DirectorySettings = Field(...)
    ai_settings: AISettings = Field(...)
```

## Template System Architecture

### YAML Spec Templates (`template_loader.py`)

**Purpose**: Inheritance-based specification templates

**Key Features**:
- Deep merge algorithm for template inheritance
- YAML-based template definition
- Template validation and error handling
- Hierarchical template relationships

**Template Inheritance Flow**:
```
Base Template (base-coding-standards.yaml)
         ↓
Domain Template (web-api.yaml)
         ↓
Project Template (my-api-patterns.yaml)
         ↓
Generated Specification
```

### Jinja2 Prompt Templates (`prompt_template_loader.py`)

**Purpose**: Dynamic AI prompt generation

**Key Features**:
- Jinja2-based template rendering
- Parameterized prompt templates
- Template safety and sandboxing
- Template discovery and validation

**Template Types**:
- `specification-generation.md`: Main spec generation
- `step-expansion.md`: Sub-specification expansion
- `specification-review.md`: AI-powered review
- `feature-addition.md`, `bug-fix.md`, etc.: Specialized prompts

## AI Provider System

### Provider Architecture (`ai_providers/`)

**Purpose**: Pluggable AI integration with multiple providers

**Components**:
- `base.py`: Abstract base class for AI providers
- `openai_provider.py`: OpenAI implementation
- `factory.py`: Provider factory and registration

**Design Patterns**:
- **Strategy pattern**: Interchangeable AI providers
- **Factory pattern**: Provider instantiation and configuration
- **Adapter pattern**: Uniform interface across different AI APIs

```python
class AIProvider(ABC):
    @abstractmethod
    async def generate_response(self, messages: list[dict], **kwargs) -> dict:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass
```

### Provider Factory

```python
class AIProviderFactory:
    _providers: ClassVar[dict[str, type[AIProvider]]] = {
        "openai": OpenAIProvider,
    }

    @classmethod
    def create_provider(cls, provider_type: str, config: dict) -> AIProvider:
        # Factory logic
```

## Prompt Engineering System

### Context Building (`prompt_engineering.py`)

**Purpose**: Intelligent prompt construction with context

**Key Features**:
- Foundation specification integration
- Parent specification context
- Template inheritance context
- Dynamic context parameter injection

**Context Flow**:
```
Project Foundation → Parent Spec Context → Template Context → Generated Prompt
```

### Prompt Enhancement

**Multi-layered approach**:
1. **Base prompt**: User input or template
2. **Context injection**: Project-specific information
3. **Template rendering**: Jinja2 processing
4. **Parameter substitution**: Dynamic values

## Error Handling Architecture

### Exception Hierarchy (`exceptions.py`)

**Purpose**: Structured error handling with informative messages

**Exception Types**:
- `AgenticSpecError`: Base exception class
- `ConfigurationError`: Configuration-related errors
- `TemplateError`: Template processing errors
- `AIServiceError`: AI provider errors
- `FileSystemError`: File operation errors
- `ValidationError`: Data validation errors

**Design Patterns**:
- **Exception hierarchy**: Organized error types
- **Error context**: Rich error information
- **User-friendly messages**: Clear, actionable error descriptions

## File System Organization

### Directory Structure

```
agentic_spec/
├── __init__.py                 # Package initialization
├── cli.py                      # CLI interface (Typer commands)
├── core.py                     # Core generation engine
├── models.py                   # Data models (dataclasses)
├── config.py                   # Configuration system (Pydantic)
├── exceptions.py               # Exception hierarchy
├── prompt_engineering.py       # Prompt building and enhancement
├── template_loader.py          # YAML template inheritance
├── prompt_template_loader.py   # Jinja2 prompt templates
├── template_validator.py       # Template validation
├── graph_visualization.py      # Dependency graph tools
├── ai_providers/               # AI provider system
│   ├── __init__.py
│   ├── base.py                # Abstract provider interface
│   ├── openai_provider.py     # OpenAI implementation
│   └── factory.py             # Provider factory
└── templates/                  # Legacy template support
    ├── __init__.py
    ├── base.py                # Template generation functions
    └── *.html                 # HTML rendering templates
```

### External Directories

```
spec-templates/                 # YAML inheritance templates
├── agentic-spec-foundation.yaml  # Auto-synced foundation
├── base-coding-standards.yaml    # General patterns
├── web-api.yaml                  # Web API patterns
├── cli-application.yaml          # CLI patterns
├── data-analysis.yaml            # Data science patterns
└── machine-learning.yaml         # ML patterns

prompt-templates/               # Jinja2 prompt templates
├── specification-generation.md   # Main generation prompt
├── step-expansion.md             # Sub-spec expansion
├── specification-review.md       # AI review prompts
├── feature-addition.md           # Feature-specific prompts
├── bug-fix.md                    # Bug fix prompts
└── refactoring.md                # Refactoring prompts

specs/                          # Generated specifications
├── 2025-07-27-abc12345.yaml      # Individual specifications
└── ...                           # Timestamped and ID-organized
```

## Data Flow Architecture

### Specification Generation Flow

```
1. User Input (CLI) → 2. Configuration Loading → 3. Template Processing
         ↓                        ↓                        ↓
4. Context Building → 5. Prompt Engineering → 6. AI Generation
         ↓                        ↓                        ↓
7. Response Parsing → 8. Validation → 9. Specification Creation
         ↓                        ↓                        ↓
10. Review Generation → 11. File Saving → 12. Status Tracking
```

### Template Inheritance Flow

```
1. Template Discovery → 2. Dependency Resolution → 3. Deep Merge
         ↓                        ↓                        ↓
4. Validation → 5. Context Integration → 6. Final Template
```

### AI Provider Flow

```
1. Provider Selection → 2. Configuration → 3. Request Preparation
         ↓                        ↓                        ↓
4. API Call → 5. Response Processing → 6. Error Handling
         ↓                        ↓                        ↓
7. Fallback Logic → 8. Result Validation → 9. Output Generation
```

## Key Design Decisions

### 1. Async/Await Architecture
- **Rationale**: AI API calls are I/O bound and benefit from async
- **Implementation**: Core engine uses async/await throughout
- **Benefits**: Better performance for multiple AI calls

### 2. Dataclass-based Models
- **Rationale**: Type safety without external dependencies
- **Implementation**: All data structures use `@dataclass`
- **Benefits**: Immutability, type checking, automatic methods

### 3. Pluggable AI Providers
- **Rationale**: Flexibility to support different AI services
- **Implementation**: Abstract base class with factory pattern
- **Benefits**: Easy to add new providers, testing with mocks

### 4. Template Inheritance System
- **Rationale**: Reusable patterns across projects
- **Implementation**: Deep merge algorithm with YAML templates
- **Benefits**: Consistency, customization, maintainability

### 5. Jinja2 Prompt Templates
- **Rationale**: Dynamic, parameterized AI prompts
- **Implementation**: Separate template directory with sandboxing
- **Benefits**: Customizable prompts, template reuse

## Testing Architecture

### Test Organization

```
tests/
├── test_cli.py                 # CLI command testing
├── test_error_handling.py      # Exception and error flow testing
├── test_prompt_engineering.py  # Prompt building and context testing
└── test_typer_integration.py   # CLI integration and UX testing
```

### Testing Patterns

**Mocking Strategy**:
- Mock AI providers for deterministic testing
- Mock file system operations for isolation
- Mock configuration for different scenarios

**Test Types**:
- **Unit tests**: Individual component testing
- **Integration tests**: Cross-component workflows
- **CLI tests**: Command-line interface validation
- **Error tests**: Exception handling verification

## Performance Considerations

### Async Operations
- AI API calls are async for better concurrency
- File operations remain sync (simpler, adequate performance)
- Configuration loading is cached

### Caching Strategy
- Template loading is cached after first read
- Configuration is cached per CLI invocation
- AI responses are not cached (always fresh results)

### Memory Management
- Specifications are processed one at a time
- Templates are loaded on-demand
- Large responses are streamed when possible

## Security Considerations

### AI Integration
- API keys handled through environment variables
- No sensitive data logged or cached
- Prompt injection protection through structured prompts

### File System
- Path traversal protection in template loading
- Validation of user-provided paths
- Safe YAML loading (no arbitrary code execution)

### Template Safety
- Jinja2 templates run in sandboxed environment
- No access to filesystem or imports from templates
- User input is properly escaped

## Extension Points

### Adding New AI Providers
1. Implement `AIProvider` abstract base class
2. Register in `AIProviderFactory._providers`
3. Add configuration schema to `AIProviderConfig`

### Adding New Template Types
1. Create new Jinja2 template in `prompt-templates/`
2. Add template loading logic in `PromptTemplateLoader`
3. Update prompt engineering to use new template

### Adding New CLI Commands
1. Add command function with Typer decorators
2. Implement command logic using existing components
3. Add error handling and user feedback

### Custom Output Formats
1. Extend specification models if needed
2. Add rendering logic in core engine
3. Update CLI to support new format options

This architecture provides a solid foundation for extending the tool while maintaining clean separation of concerns and type safety throughout the system.
