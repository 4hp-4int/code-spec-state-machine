# Development Workflows

## Development Environment Setup

### Prerequisites

- **Python 3.12+** (uses modern Python features)
- **Git** (for version control)
- **OpenAI API key** (for testing AI features)

### Initial Setup

1. **Clone and install**:
   ```bash
   git clone https://github.com/yourusername/agentic-spec.git
   cd agentic-spec
   make install-dev
   ```

2. **Set up development environment**:
   ```bash
   make dev-setup
   ```
   This configures:
   - Pre-commit hooks with automatic formatting
   - Git hooks for quality control
   - Development dependencies

3. **Configure environment**:
   ```bash
   export OPENAI_API_KEY=your-api-key-here
   ```

4. **Verify setup**:
   ```bash
   make quality-gate
   ```

## Development Workflow

### Daily Development Cycle

1. **Pull latest changes**:
   ```bash
   git pull origin main
   ```

2. **Create feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make changes** following coding standards

4. **Run tests frequently**:
   ```bash
   make test-fast    # Quick tests during development
   make test         # Full test suite before commit
   ```

5. **Commit with quality checks**:
   ```bash
   git add .
   git commit -m "Your commit message"
   # Pre-commit hooks run automatically
   ```

6. **Push and create PR**:
   ```bash
   git push -u origin feature/your-feature-name
   # Create pull request through GitHub interface
   ```

### Make-based Workflow

The project uses a comprehensive Makefile for all development tasks:

#### Installation and Setup
```bash
make install          # Install package in development mode
make install-dev      # Install with development dependencies
make dev-setup        # Set up development environment
```

#### Code Quality
```bash
make format           # Format code using ruff
make lint             # Run linting checks
make lint-fix         # Auto-fix linting issues where possible
make check            # Run both formatting and linting
make quality          # Run comprehensive quality checks
```

#### Testing
```bash
make test             # Run all tests
make test-cov         # Run tests with coverage reporting
make test-fast        # Run tests excluding slow tests
make test-unit        # Run only unit tests
make test-integration # Run only integration tests
```

#### CI/CD and Quality Gates
```bash
make ci               # Run full CI pipeline (format, lint, test)
make pre-commit       # Run pre-commit checks manually
make quality-gate     # All-in-one quality gate
```

#### Utilities
```bash
make clean            # Clean build artifacts and cache files
make build            # Build distribution packages
make help             # Show available commands
make version-check    # Check version information
make analyze          # Run code analysis with statistics
```

#### Specification Workflow
```bash
make spec-commit      # Commit specifications and implementation changes
make spec-publish     # Publish all completed specifications as implemented
make spec-complete    # Complete specification workflow (commit + publish)
```

## Coding Standards

### Python Code Style

The project uses **Ruff** for both linting and formatting:

- **Formatting**: Automatic with `ruff format`
- **Linting**: Comprehensive rules with `ruff check`
- **Import sorting**: Organized imports
- **Type hints**: Required for all functions and methods

### Code Organization

**Module Structure**:
```python
"""Module docstring explaining purpose."""

# Standard library imports
import os
import sys
from pathlib import Path

# Third-party imports
import typer
import yaml

# Local imports
from .config import AgenticSpecConfig
from .exceptions import AgenticSpecError

# Module-level constants
DEFAULT_CONFIG_FILE = "agentic_spec_config.yaml"

# Classes and functions...
```

**Function Structure**:
```python
def function_name(param: str, optional_param: int = 10) -> ReturnType:
    """Brief description of what the function does.

    Args:
        param: Description of parameter
        optional_param: Description with default value

    Returns:
        Description of return value

    Raises:
        SpecificError: When this error occurs
    """
    # Implementation
```

**Class Structure**:
```python
@dataclass
class ExampleClass:
    """Brief description of the class."""

    required_field: str
    optional_field: int = 10

    def method_name(self, param: str) -> str:
        """Method description."""
        # Implementation
```

### Error Handling

**Use Custom Exceptions**:
```python
# Good
if not api_key:
    raise ConfigurationError("OpenAI API key not found")

# Avoid generic exceptions
if not api_key:
    raise ValueError("API key missing")
```

**Exception Context**:
```python
try:
    result = process_template(template_path)
except FileNotFoundError as e:
    msg = f"Template not found: {template_path}"
    raise TemplateError(msg) from e
```

**Async Error Handling**:
```python
async def ai_operation():
    try:
        response = await ai_provider.generate_response(prompt)
        return response
    except Exception as e:
        logger.exception("AI operation failed")
        raise AIServiceError("Failed to generate response") from e
```

## Testing Guidelines

### Test Organization

```
tests/
├── test_cli.py                 # CLI command testing
├── test_error_handling.py      # Exception and error scenarios
├── test_prompt_engineering.py  # Prompt building and AI integration
└── test_typer_integration.py   # CLI framework integration
```

### Test Patterns

**Unit Tests**:
```python
import pytest
from unittest.mock import Mock, patch

def test_specification_generation():
    """Test basic specification generation."""
    generator = SpecGenerator(...)
    spec = generator.generate_spec("test prompt")

    assert spec.metadata.title
    assert len(spec.implementation) > 0
    assert spec.requirements.functional
```

**Async Tests**:
```python
import pytest

@pytest.mark.asyncio
async def test_ai_integration():
    """Test AI provider integration."""
    provider = OpenAIProvider(config)
    response = await provider.generate_response(messages)

    assert response["choices"]
    assert response["choices"][0]["message"]
```

**CLI Tests**:
```python
from typer.testing import CliRunner
from agentic_spec.cli import app

def test_generate_command():
    """Test generate CLI command."""
    runner = CliRunner()
    result = runner.invoke(app, ["generate", "test prompt"])

    assert result.exit_code == 0
    assert "✅ Specification generated" in result.stdout
```

**Mocking AI Providers**:
```python
@patch("agentic_spec.core.OpenAIProvider")
def test_with_mock_ai(mock_provider):
    """Test specification generation with mocked AI."""
    mock_provider.return_value.generate_response = AsyncMock(
        return_value={"choices": [{"message": {"content": "test response"}}]}
    )

    # Test logic here
```

### Test Data Management

**Fixtures**:
```python
@pytest.fixture
def sample_spec():
    """Sample specification for testing."""
    return ProgrammingSpec(
        metadata=SpecMetadata(id="test123", title="Test Spec"),
        context=SpecContext(project="test", domain="testing"),
        # ... other fields
    )

@pytest.fixture
def temp_dirs():
    """Temporary directories for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        templates_dir = Path(temp_dir) / "templates"
        specs_dir = Path(temp_dir) / "specs"
        templates_dir.mkdir()
        specs_dir.mkdir()
        yield templates_dir, specs_dir
```

**Test Configuration**:
```python
@pytest.fixture
def test_config():
    """Test configuration."""
    return AgenticSpecConfig(
        prompt_settings=PromptSettings(temperature=0.1),
        workflow=WorkflowSettings(auto_review=False),
        # ... other settings
    )
```

## Pre-commit Hooks

### Automatic Code Quality

The project uses pre-commit hooks that run automatically on `git commit`:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff              # Linting with auto-fix
        args: [--fix]
      - id: ruff-format       # Code formatting

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-merge-conflict
```

### How Pre-commit Works

1. **On commit**, hooks run automatically
2. **If hooks modify files**, commit fails with message
3. **Review changes** made by hooks
4. **Re-stage and commit** the formatted code

Example workflow:
```bash
git add file_with_bad_formatting.py
git commit -m "Add new feature"
# Hooks run, fix formatting, commit fails

git add file_with_bad_formatting.py  # Re-stage formatted file
git commit -m "Add new feature"      # Commit succeeds
```

### Manual Pre-commit Execution

```bash
# Run all hooks on all files
pre-commit run --all-files

# Run specific hook
pre-commit run ruff --all-files

# Skip hooks for emergency commits (not recommended)
git commit --no-verify -m "Emergency fix"
```

## Adding New Features

### Feature Development Process

1. **Generate specification**:
   ```bash
   agentic-spec generate "Add new feature: [description]"
   ```

2. **Review specification**:
   - Check requirements and implementation steps
   - Expand complex steps if needed
   - Get team review if applicable

3. **Implement following specification**:
   - Follow the generated implementation steps
   - Write tests as specified
   - Maintain coding standards

4. **Update documentation**:
   - Update relevant documentation files
   - Add examples if applicable
   - Update API reference if needed

5. **Test thoroughly**:
   ```bash
   make test           # Run all tests
   make quality-gate   # Run quality checks
   ```

6. **Publish specification**:
   ```bash
   agentic-spec publish [spec-id]
   ```

### Adding New CLI Commands

1. **Create command function**:
   ```python
   @app.command("new-command")
   def new_command(
       param: str = Argument(..., help="Required parameter"),
       option: bool = Option(False, "--option", help="Optional flag"),
   ):
       """Brief description of what the command does."""
       try:
           # Command implementation
           print("✅ Command completed successfully")
       except Exception as e:
           logger.exception("Command failed")
           print(f"❌ Failed: {e}")
           raise typer.Exit(1) from None
   ```

2. **Add error handling**:
   ```python
   try:
       result = some_operation()
   except SpecificError as e:
       print(f"❌ {e.message}")
       raise typer.Exit(1) from None
   except Exception as e:
       logger.exception("Unexpected error")
       print(f"❌ Unexpected error: {e}")
       raise typer.Exit(1) from None
   ```

3. **Add tests**:
   ```python
   def test_new_command(cli_runner):
       """Test new CLI command."""
       result = cli_runner.invoke(app, ["new-command", "test-param"])
       assert result.exit_code == 0
       assert "✅ Command completed" in result.stdout
   ```

### Adding New AI Providers

1. **Implement provider interface**:
   ```python
   class NewAIProvider(AIProvider):
       def __init__(self, config: dict):
           self.config = config
           # Initialize provider

       async def generate_response(self, messages: list[dict], **kwargs) -> dict:
           # Implement API call
           pass

       def is_available(self) -> bool:
           # Check if provider is configured and accessible
           pass
   ```

2. **Register in factory**:
   ```python
   # ai_providers/factory.py
   class AIProviderFactory:
       _providers: ClassVar[dict[str, type[AIProvider]]] = {
           "openai": OpenAIProvider,
           "new-provider": NewAIProvider,  # Add here
       }
   ```

3. **Add configuration schema**:
   ```python
   # config.py
   class AISettings(BaseModel):
       providers: dict[str, AIProviderConfig] = Field(
           default_factory=lambda: {
               "openai": AIProviderConfig(...),
               "new-provider": AIProviderConfig(...),  # Add default config
           }
       )
   ```

4. **Add tests**:
   ```python
   def test_new_provider():
       """Test new AI provider."""
       provider = NewAIProvider(config)
       assert provider.is_available()

       response = await provider.generate_response(messages)
       assert response["choices"]
   ```

## Release Process

### Version Management

**Version Bumping**:
1. Update version in `pyproject.toml`
2. Update version references in documentation
3. Create changelog entry

**Release Steps**:
1. **Prepare release**:
   ```bash
   make quality-gate  # Ensure all checks pass
   make test-cov      # Verify test coverage
   ```

2. **Create release commit**:
   ```bash
   git add .
   git commit -m "Release v1.2.3"
   git tag v1.2.3
   ```

3. **Build distribution**:
   ```bash
   make build
   ```

4. **Push release**:
   ```bash
   git push origin main
   git push origin v1.2.3
   ```

### Documentation Updates

**Keep documentation current**:
- Update README.md for major changes
- Update API reference for new functions/classes
- Update usage examples for new features
- Verify all links and examples work

## Debugging and Troubleshooting

### Debug Mode

**Enable debug logging**:
```bash
export AGENTIC_SPEC_LOG_LEVEL=DEBUG
agentic-spec generate "test prompt"
```

**Check log files**:
```bash
tail -f logs/agentic_spec.log
```

### Common Development Issues

**Import Errors**:
```bash
# Reinstall in development mode
make install-dev

# Check Python path
python -c "import agentic_spec; print(agentic_spec.__file__)"
```

**Test Failures**:
```bash
# Run specific test with verbose output
pytest tests/test_cli.py::test_specific_function -v -s

# Run with debugging
pytest --pdb tests/test_cli.py
```

**Pre-commit Issues**:
```bash
# Update hooks
pre-commit autoupdate

# Clear cache
pre-commit clean

# Reinstall hooks
pre-commit install
```

### Performance Profiling

**Profile AI operations**:
```python
import time
start_time = time.time()
result = await ai_provider.generate_response(messages)
duration = time.time() - start_time
logger.info(f"AI call took {duration:.2f} seconds")
```

**Memory profiling**:
```bash
pip install memory-profiler
python -m memory_profiler script.py
```

## Contributing Guidelines

### Code Review Checklist

**Before submitting PR**:
- [ ] All tests pass (`make test`)
- [ ] Code quality checks pass (`make quality-gate`)
- [ ] Documentation updated if needed
- [ ] Specification published if applicable
- [ ] No sensitive data in commits

**Review criteria**:
- [ ] Code follows established patterns
- [ ] Error handling is appropriate
- [ ] Tests cover new functionality
- [ ] Documentation is clear and complete
- [ ] Performance impact is acceptable

### Git Workflow

**Commit Messages**:
- Use clear, descriptive commit messages
- Reference issue numbers when applicable
- Use conventional commit format when possible

**Branch Naming**:
- `feature/description` for new features
- `fix/description` for bug fixes
- `docs/description` for documentation updates
- `refactor/description` for refactoring

**Pull Request Process**:
1. Create feature branch
2. Implement changes with tests
3. Run quality checks locally
4. Create pull request with clear description
5. Address review feedback
6. Squash commits if requested

This development workflow ensures consistent code quality and maintainable development practices across the project.
