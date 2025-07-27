# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Agentic Spec is an AI-powered tool for generating detailed programming specifications from high-level prompts. It features template inheritance, automated review workflows, and supports both AI-assisted and basic generation modes.

## Development Commands

### Custom Slash Commands

This project includes a custom slash command for Claude Code:

- `/spec` - Generate programming specifications using agentic-spec
  - `/spec generate "task description"` - Generate a new specification
  - `/spec generate "task" --template feature-addition` - Generate with prompt template
  - `/spec generate "task" --inherits template1 template2` - Generate with template inheritance
  - `/spec browse-templates` - Browse available prompt templates
  - `/spec preview-template template-name` - Preview a prompt template
  - `/spec templates` - Create base templates
  - `/spec review` - List existing specifications
  - `/spec expand spec_id:step_index` - Expand an implementation step into a sub-specification
  - `/spec graph` - Display specification dependency graph

## CLI Commands

### Complete Command Reference

#### Core Commands

**generate** - Generate a new programming specification from a prompt
```bash
# Basic generation
agentic-spec generate "Build a REST API for user management"

# With prompt template
agentic-spec generate "Add JWT authentication" --template feature-addition

# With template inheritance
agentic-spec generate "Add JWT authentication" --inherits web-api base-coding-standards

# With context customization
agentic-spec generate "Create data pipeline" \
  --user-role "data engineer" \
  --target-audience "team" \
  --tone "detailed" \
  --complexity "advanced"

# Interactive input mode
agentic-spec generate  # Then type prompt and press Ctrl+D/Ctrl+Z

# Pipe input from other sources
echo "Implement real-time chat feature" | agentic-spec generate

# Override configuration
agentic-spec generate "Task" --set prompt_settings.temperature=0.2
```

**review** - List available specifications for review
```bash
agentic-spec review
agentic-spec review --specs-dir ./custom-specs
```

**templates** - Create base templates for common project patterns
```bash
agentic-spec templates --project myproject
agentic-spec templates --templates-dir ./custom-templates
```

**graph** - Display specification dependency graph and statistics
```bash
agentic-spec graph
agentic-spec graph --specs-dir ./specs
```

**expand** - Expand an implementation step into a detailed sub-specification
```bash
agentic-spec expand spec_id:0  # Expand first step
agentic-spec expand abc123:2   # Expand third step of spec abc123
```

**publish** - Mark a specification as implemented and update its status
```bash
agentic-spec publish spec_id
agentic-spec publish abc123 --specs-dir ./specs
```

#### Configuration Commands

**config** - Manage application configuration
```bash
# Create default configuration file
agentic-spec config init

# Show current configuration
agentic-spec config show

# Validate configuration file
agentic-spec config validate
```

#### Template Management Commands

**template** - Manage and inspect templates
```bash
# List available templates
agentic-spec template list

# Show template information
agentic-spec template info --template base-coding-standards
```

**validate** - Validate all templates for correctness and structure
```bash
agentic-spec validate
agentic-spec validate --templates-dir ./templates
```

#### Foundation Sync Commands

**sync-foundation** - Sync foundation specification with current codebase state
```bash
agentic-spec sync-foundation
agentic-spec sync-foundation --force  # Force sync even if current
```

**check-foundation** - Check if foundation specification needs to be synced
```bash
agentic-spec check-foundation
```

#### Template Browsing Commands

**browse-templates** - Browse available prompt templates
```bash
agentic-spec browse-templates
```

**preview-template** - Preview a specific prompt template
```bash
agentic-spec preview-template feature-addition
agentic-spec preview-template bug-fix
```

#### Rendering Commands

**render** - Render a specification using a template
```bash
# Render to stdout
agentic-spec render spec_id --template template.html

# Render to file
agentic-spec render spec_id --template template.html --output output.html
```

### Makefile Commands

All development tasks should be run through the Makefile:

```bash
# Installation
make install          # Install package in development mode
make install-dev      # Install with development dependencies

# Code Quality
make format           # Format code using ruff
make lint             # Run linting checks
make check            # Run both formatting and linting checks
make lint-fix         # Auto-fix linting issues where possible
make quality          # Run comprehensive quality checks

# Testing
make test             # Run all tests
make test-cov         # Run tests with coverage reporting
make test-fast        # Run tests excluding slow tests
make test-unit        # Run only unit tests
make test-integration # Run only integration tests

# CI/CD
make ci               # Run full CI pipeline (format, lint, test)
make pre-commit       # Run pre-commit checks
make quality-gate     # All-in-one quality gate

# Utilities
make clean            # Clean build artifacts and cache files
make build            # Build distribution packages
make help             # Show available commands
make version-check    # Check version information
make analyze          # Run code analysis with statistics

# Specification Workflow (IMPORTANT)
make spec-commit      # Commit specifications and implementation changes
make spec-publish     # Publish all completed specifications as implemented
make spec-complete    # Complete specification workflow (commit + publish)
```

### Development Workflow

```bash
# Initial setup
make install-dev
make dev-setup

# Before committing
make pre-commit

# Full quality check
make quality-gate

# Run specific test suite
make test-unit
make test-integration

# Get detailed output
make format-verbose
make lint-verbose
make test-verbose
```

## Architecture

### Core Components

- **CLI Module** (`cli.py`): Command-line interface with support for multiple input sources (args, stdin, interactive)
- **Core Engine** (`core.py`): Specification generation logic with AI integration and template inheritance
- **Data Models** (`models.py`): Dataclass definitions for specifications, metadata, and implementation steps
- **Template System** (`templates/base.py`): Pre-built templates for common project patterns

### Key Design Patterns

- **Template Inheritance**: Specifications can inherit from multiple base templates using deep merge strategy
- **Async AI Integration**: Uses OpenAI's Responses API with web search for current best practices
- **Graceful Degradation**: Falls back to basic generation when AI is unavailable
- **Input Flexibility**: Supports command-line args, piped input, and interactive multiline input
- **Foundation Sync**: Automated foundation specification syncing with codebase analysis
- **Comprehensive Context**: Parent spec traversal and foundation context for complete awareness
- **Error Handling**: Custom exception hierarchy with informative user messages
- **Typer CLI**: Modern CLI framework with automatic help generation and type validation

### File Structure
```
agentic_spec/
├── cli.py                      # CLI entry point with Typer commands
├── core.py                     # SpecGenerator class and AI integration
├── models.py                   # Data models (dataclasses)
├── config.py                   # Configuration management with Pydantic
├── exceptions.py               # Custom exception hierarchy
├── prompt_engineering.py       # AI prompt building and optimization
├── graph_visualization.py      # Specification dependency graph tools
├── template_loader.py          # Template loading and management
├── template_validator.py       # Template validation system
└── templates/
    ├── base.py                 # Template generation functions
    └── __init__.py

templates/                      # Generated base templates
├── agentic-spec-foundation.yaml    # Auto-synced foundation specification
├── base-coding-standards.yaml      # Coding standards template
├── web-api.yaml                    # Web API project template
├── cli-application.yaml            # CLI application template
├── data-analysis.yaml              # Data analysis template
└── machine-learning.yaml           # ML project template

specs/                          # Generated specifications (created at runtime)

logs/                           # Application logs with rotation

Makefile                        # Development automation commands
```

### AI Integration Details

- Uses OpenAI's Responses API with web search capabilities for current best practices
- System prompts emphasize up-to-date libraries and implementation patterns
- Review system focuses on practical solo developer concerns
- Graceful fallback to basic generation when AI unavailable

### Template System

Templates use YAML format and support deep merging. The inheritance system allows building complex specifications from reusable components. Base templates cover common domains (web APIs, CLIs, data analysis, ML).

### Specification Format

Generated specs include:
- **Metadata**: ID, inheritance chain, timestamps, version
- **Context**: Project info, domain, dependencies, affected files
- **Requirements**: Functional, non-functional, constraints
- **Implementation**: Detailed steps with acceptance criteria and effort estimates
- **Review Notes**: AI-generated feedback and recommendations

## Environment Requirements

- Python 3.12+ (configured in pyproject.toml)
- OpenAI API key for AI features (optional)
- Core Dependencies:
  - PyYAML >= 6.0.2 (YAML parsing and generation)
  - OpenAI >= 1.97.1 (AI integration)
  - Typer >= 0.12.0 (CLI framework)
  - NetworkX >= 3.3 (Graph visualization)
  - Matplotlib >= 3.9.2 (Graph rendering)
  - Jinja2 >= 3.1.0 (Template rendering)
  - pytest-cov >= 6.2.1 (Test coverage)
- Development Dependencies:
  - Ruff >= 0.8.0 (Linting and formatting, replaces Black/flake8)
  - pytest >= 8.4.1 (Testing framework)
  - pytest-asyncio >= 0.23.2,<0.24.0 (Async test support)

## Claude Code Memories

- Always use the agentic-spec tool to generate new specs to follow when working on the project.
- Run project commands through make and the Makefile
- **AUTOMATIC WORKFLOW**: When completing a specification or declaring it done, ALWAYS run `make spec-complete` to commit changes and publish completed specifications. This ensures proper version control and specification tracking.
- Memorize the doc/location structure, keep docs up to date
- Relay the current spec graph after completing sub-specifications or the parent specification
- Always decompose composite task to build full spec trees, unless theres 3 levels of nested decomposition, then get approval
