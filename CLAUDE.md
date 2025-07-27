# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Agentic Spec is an AI-powered tool for generating detailed programming specifications from high-level prompts. It features template inheritance, automated review workflows, and supports both AI-assisted and basic generation modes.

## Development Commands

### Custom Slash Commands

This project includes a custom slash command for Claude Code:

- `/spec` - Generate programming specifications using agentic-spec
  - `/spec generate "task description"` - Generate a new specification
  - `/spec generate "task" --inherits template1 template2` - Generate with template inheritance
  - `/spec templates` - Create base templates
  - `/spec review` - List existing specifications

## Development Commands

### Installation and Setup
```bash
# Install package in development mode
python setup.py install

# Install with AI features (requires OpenAI API key)
pip install ".[ai]"

# Install development dependencies
pip install ".[dev]"
```

### Running the Application
```bash
# Generate specification from prompt
agentic-spec generate "Build a REST API for user management"

# Generate with template inheritance
agentic-spec generate "Add JWT authentication" --inherits web-api base-coding-standards

# Create base templates
agentic-spec templates --project myproject

# Interactive input mode
agentic-spec generate
# (then type prompt and press Ctrl+D/Ctrl+Z)

# Pipe input from other sources
echo "Implement real-time chat feature" | agentic-spec generate

# Review existing specifications
agentic-spec review
```

### Development Tools
```bash
# Code formatting
black agentic_spec/

# Linting
flake8 agentic_spec/

# Run tests
pytest

# Package testing
python -m agentic_spec.cli generate "test prompt"
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

### File Structure
```
agentic_spec/
├── cli.py              # CLI entry point and argument handling
├── core.py             # SpecGenerator class and AI integration
├── models.py           # Data models (dataclasses)
└── templates/
    ├── base.py         # Template generation functions
    └── __init__.py

templates/              # Generated base templates
├── base-coding-standards.yaml
├── web-api.yaml
├── cli-application.yaml
├── data-analysis.yaml
└── machine-learning.yaml

specs/                  # Generated specifications (created at runtime)
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
- Dependencies: PyYAML, OpenAI client
- Development dependencies: black, flake8, pytest

## Claude Code Memories

- Always use the agentic-spec tool to generate new specs to follow when working on the project.