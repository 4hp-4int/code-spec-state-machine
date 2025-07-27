# Agentic Specification Generator

An AI-powered tool for generating detailed programming specifications from high-level prompts, with inheritance support and automated review workflows.

## Features

- **AI-Powered Generation**: Uses OpenAI's API to create detailed programming specifications
- **Template Inheritance**: Build specifications by inheriting from base templates
- **Automated Review**: AI-powered specification review for solo developers
- **Flexible Input**: Command-line args, stdin, or interactive input
- **Multiple Output Formats**: YAML specifications with structured data
- **Extensible Templates**: Pre-built templates for common project types

## Installation

```bash
python setup.py install
```

For AI features, install with OpenAI support:

```bash
pip install ".[ai]"
```

## Quick Start

1. **Create base templates**:
   ```bash
   agentic-spec templates --project myproject
   ```

2. **Generate a specification**:
   ```bash
   agentic-spec generate "Build a REST API for user management"
   ```

3. **Use template inheritance**:
   ```bash
   agentic-spec generate "Add JWT authentication" --inherits web-api base-coding-standards
   ```

4. **Pipe input from other tools**:
   ```bash
   echo "Implement real-time chat feature" | agentic-spec generate
   ```

## Command Reference

### Generate Specifications

```bash
agentic-spec generate [PROMPT] [OPTIONS]
```

**Options:**
- `--inherits TEMPLATE [TEMPLATE...]`: Inherit from base templates
- `--project NAME`: Set project name (default: project)
- `--templates-dir PATH`: Templates directory (default: templates)
- `--specs-dir PATH`: Generated specs directory (default: specs)

**Examples:**
```bash
# Basic generation
agentic-spec generate "Build a CLI tool for file processing"

# With inheritance
agentic-spec generate "Add data visualization" --inherits data-analysis base-coding-standards

# Interactive input
agentic-spec generate
# (then type your prompt and press Ctrl+D/Ctrl+Z)
```

### Create Templates

```bash
agentic-spec templates [OPTIONS]
```

Creates base templates including:
- `base-coding-standards.yaml`: General coding standards
- `web-api.yaml`: REST API development patterns
- `cli-application.yaml`: Command-line tool patterns
- `data-analysis.yaml`: Data analysis project patterns
- `machine-learning.yaml`: ML project patterns

### Review Specifications

```bash
agentic-spec review [OPTIONS]
```

Lists available specifications for review.

## Template System

Templates use YAML format and support inheritance. Example template:

```yaml
# templates/my-template.yaml
domain: "web development"
dependencies: ["fastapi", "sqlalchemy", "alembic"]
patterns:
  architecture: "MVC with dependency injection"
  database: "SQLAlchemy ORM with Alembic migrations"
  testing: "pytest with fixtures"
files_involved: ["main.py", "models/", "routes/", "tests/"]
```

Use in specifications:
```bash
agentic-spec generate "Add user authentication" --inherits my-template
```

## Configuration

The tool automatically detects:
- Project structure and language
- Existing dependencies and frameworks
- Coding standards from the codebase

Customize behavior through:
- Template files in `templates/` directory
- Command-line arguments
- Environment variables (OpenAI API key)

## Output Format

Generated specifications include:

- **Metadata**: ID, inheritance chain, timestamps
- **Context**: Project info, domain, dependencies
- **Requirements**: Functional, non-functional, constraints
- **Implementation**: Step-by-step tasks with acceptance criteria
- **Review Notes**: AI-generated feedback and recommendations

Example output structure:
```yaml
metadata:
  id: abc12345
  inherits: ["web-api", "base-coding-standards"]
  created: "2025-07-26T10:30:00"
  version: "1.0"
  status: "draft"

context:
  project: "myproject"
  domain: "user management API"
  dependencies: ["fastapi", "sqlalchemy", "pydantic"]
  files_involved: ["models/user.py", "routes/auth.py"]

requirements:
  functional:
    - "User registration with email validation"
    - "JWT-based authentication"
  non_functional:
    - "Response time < 200ms"
    - "Password hashing with bcrypt"

implementation:
  - task: "Create User model"
    details: "SQLAlchemy model with email, password hash"
    files: ["models/user.py"]
    acceptance: "Model passes validation tests"
    estimated_effort: "low"

review_notes:
  - "Consider rate limiting for auth endpoints"
  - "Add email uniqueness constraint to database"
```

## Development

The tool is designed to evolve with your project needs. Key extension points:

- **Custom Templates**: Add project-specific templates
- **AI Prompts**: Customize system prompts for domain-specific generation
- **Output Formats**: Extend beyond YAML to other formats
- **Integration**: Embed in larger development workflows

## Requirements

- Python 3.8+
- PyYAML
- OpenAI API key (for AI features)

## License

MIT License - see LICENSE file for details.
