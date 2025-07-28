"""Default specification templates for bootstrapping new projects."""

from pathlib import Path

import yaml


def create_default_specification_templates(
    specs_dir: Path, project_name: str = "my-project"
) -> dict[str, str]:
    """Create comprehensive default specification templates for new projects.

    These are actual specifications that users can reference and build upon,
    providing practical examples of common development patterns.

    Returns:
        Dict mapping spec IDs to their file paths
    """
    created_specs = {}

    # 1. Project Setup and Basic Infrastructure
    setup_spec = {
        "metadata": {
            "id": "setup-infrastructure",
            "title": f"Set up basic infrastructure for {project_name}",
            "inherits": ["base-coding-standards"],
            "created": "2025-01-01T00:00:00",
            "version": "1.0",
            "status": "draft",
            "parent_spec_id": None,
            "child_spec_ids": None,
            "author": "template-generator",
            "last_modified": None,
        },
        "context": {
            "project": project_name,
            "domain": "Project Setup and Infrastructure",
            "dependencies": [
                {"name": "python", "version": "3.12+"},
                {"name": "git", "version": "latest"},
                {"name": "make", "version": "latest"},
            ],
            "files_involved": [
                "README.md",
                "pyproject.toml",
                "Makefile",
                ".gitignore",
                "requirements.txt",
                ".github/workflows/",
                "tests/",
                "src/",
            ],
        },
        "requirements": {
            "functional": [
                "Create project structure with clear organization",
                "Set up dependency management with pyproject.toml",
                "Configure development tools (linting, testing, formatting)",
                "Establish CI/CD pipeline with GitHub Actions",
                "Create comprehensive README with setup instructions",
            ],
            "non_functional": [
                "Project should be easy to set up for new developers",
                "All dependencies should be clearly documented",
                "Development workflow should be automated via Makefile",
                "Code quality tools should enforce consistent standards",
            ],
            "constraints": [
                "Use Python 3.12+ for modern language features",
                "Follow semantic versioning for releases",
                "Maintain backwards compatibility in public APIs",
            ],
        },
        "implementation": [
            {
                "task": "Create project directory structure",
                "details": "Set up organized directory structure with src/, tests/, docs/, and config directories",
                "files": ["src/", "tests/", "docs/", "config/", ".gitignore"],
                "acceptance": "Directory structure follows Python packaging best practices",
                "estimated_effort": "low",
                "step_id": "setup-infrastructure:0",
                "sub_spec_id": None,
                "decomposition_hint": "atomic",
            },
            {
                "task": "Configure dependency management",
                "details": "Set up pyproject.toml with project metadata, dependencies, and build configuration",
                "files": ["pyproject.toml", "requirements.txt"],
                "acceptance": "Dependencies are clearly defined and project can be installed with pip",
                "estimated_effort": "low",
                "step_id": "setup-infrastructure:1",
                "sub_spec_id": None,
                "decomposition_hint": "atomic",
            },
            {
                "task": "Set up development automation",
                "details": "Create Makefile with common development tasks (install, test, lint, format, build)",
                "files": ["Makefile"],
                "acceptance": "Common development tasks can be run with simple make commands",
                "estimated_effort": "medium",
                "step_id": "setup-infrastructure:2",
                "sub_spec_id": None,
                "decomposition_hint": "atomic",
            },
            {
                "task": "Configure code quality tools",
                "details": "Set up ruff for linting/formatting, pytest for testing, and pre-commit hooks",
                "files": [".pre-commit-config.yaml", "pytest.ini", "ruff.toml"],
                "acceptance": "Code quality tools run automatically and enforce consistent standards",
                "estimated_effort": "medium",
                "step_id": "setup-infrastructure:3",
                "sub_spec_id": None,
                "decomposition_hint": "atomic",
            },
            {
                "task": "Create CI/CD pipeline",
                "details": "Set up GitHub Actions workflow for testing, linting, and deployment",
                "files": [".github/workflows/ci.yml", ".github/workflows/release.yml"],
                "acceptance": "All commits trigger automated testing and quality checks",
                "estimated_effort": "medium",
                "step_id": "setup-infrastructure:4",
                "sub_spec_id": None,
                "decomposition_hint": "atomic",
            },
            {
                "task": "Write comprehensive README",
                "details": "Create README with project description, setup instructions, usage examples, and contribution guidelines",
                "files": ["README.md", "CONTRIBUTING.md"],
                "acceptance": "New developers can understand and set up the project from README alone",
                "estimated_effort": "medium",
                "step_id": "setup-infrastructure:5",
                "sub_spec_id": None,
                "decomposition_hint": "atomic",
            },
        ],
        "review_notes": [
            "Consider using uv or pipenv for faster dependency resolution if the project grows large",
            "Add security scanning with tools like bandit or safety in the CI pipeline",
            "Consider setting up documentation generation with Sphinx if the project becomes complex",
        ],
    }

    setup_file = specs_dir / "setup-infrastructure.yaml"
    with setup_file.open("w", encoding="utf-8") as f:
        yaml.dump(
            setup_spec, f, default_flow_style=False, sort_keys=False, allow_unicode=True
        )
    created_specs["setup-infrastructure"] = str(setup_file)

    # 2. REST API Development Template
    api_spec = {
        "metadata": {
            "id": "rest-api-example",
            "title": f"Build a REST API for {project_name}",
            "inherits": ["web-api", "base-coding-standards"],
            "created": "2025-01-01T00:00:00",
            "version": "1.0",
            "status": "draft",
            "parent_spec_id": None,
            "child_spec_ids": None,
            "author": "template-generator",
            "last_modified": None,
        },
        "context": {
            "project": project_name,
            "domain": "Web API Development",
            "dependencies": [
                {"name": "fastapi", "version": "0.104+"},
                {"name": "pydantic", "version": "2.0+"},
                {"name": "uvicorn", "version": "0.24+"},
                {"name": "sqlalchemy", "version": "2.0+"},
                {"name": "alembic", "version": "1.12+"},
                {"name": "pytest", "version": "7.0+"},
                {"name": "httpx", "version": "0.25+"},
            ],
            "files_involved": [
                "src/api/",
                "src/models/",
                "src/database/",
                "src/routes/",
                "tests/test_api/",
                "alembic/",
                "main.py",
            ],
        },
        "requirements": {
            "functional": [
                "Create RESTful API endpoints following OpenAPI standards",
                "Implement CRUD operations for core resources",
                "Add request/response validation with Pydantic",
                "Set up database integration with SQLAlchemy",
                "Implement proper error handling and status codes",
                "Add authentication and authorization",
                "Generate interactive API documentation",
            ],
            "non_functional": [
                "API should handle 1000+ concurrent requests",
                "Response times should be under 100ms for simple operations",
                "All endpoints should be fully documented",
                "API should follow REST conventions consistently",
                "Error messages should be user-friendly and informative",
            ],
            "constraints": [
                "Use FastAPI for framework consistency",
                "Follow OpenAPI 3.0 specification",
                "Implement proper HTTP status codes",
                "Use async/await for database operations",
            ],
        },
        "implementation": [
            {
                "task": "Set up FastAPI application structure",
                "details": "Create main FastAPI app with proper configuration, middleware, and routing setup",
                "files": ["main.py", "src/api/app.py", "src/api/config.py"],
                "acceptance": "FastAPI application starts successfully and serves basic endpoints",
                "estimated_effort": "medium",
                "step_id": "rest-api-example:0",
                "sub_spec_id": None,
                "decomposition_hint": "atomic",
            },
            {
                "task": "Design and implement data models",
                "details": "Create Pydantic models for request/response and SQLAlchemy models for database",
                "files": ["src/models/schemas.py", "src/models/database.py"],
                "acceptance": "Data models are defined with proper validation and relationships",
                "estimated_effort": "high",
                "step_id": "rest-api-example:1",
                "sub_spec_id": None,
                "decomposition_hint": "composite: high-effort task requiring breakdown",
            },
            {
                "task": "Set up database connection and migrations",
                "details": "Configure SQLAlchemy, set up Alembic for migrations, create initial schema",
                "files": ["src/database/connection.py", "alembic/", "alembic.ini"],
                "acceptance": "Database can be created and migrations run successfully",
                "estimated_effort": "medium",
                "step_id": "rest-api-example:2",
                "sub_spec_id": None,
                "decomposition_hint": "atomic",
            },
            {
                "task": "Implement core CRUD endpoints",
                "details": "Create REST endpoints for Create, Read, Update, Delete operations",
                "files": ["src/routes/items.py", "src/routes/users.py"],
                "acceptance": "All CRUD operations work correctly with proper status codes",
                "estimated_effort": "high",
                "step_id": "rest-api-example:3",
                "sub_spec_id": None,
                "decomposition_hint": "composite: high-effort task requiring breakdown",
            },
            {
                "task": "Add authentication and authorization",
                "details": "Implement JWT-based authentication with role-based access control",
                "files": ["src/auth/", "src/middleware/auth.py"],
                "acceptance": "Protected endpoints require valid authentication tokens",
                "estimated_effort": "high",
                "step_id": "rest-api-example:4",
                "sub_spec_id": None,
                "decomposition_hint": "composite: high-effort task requiring breakdown",
            },
            {
                "task": "Implement comprehensive error handling",
                "details": "Create custom exception handlers, error response models, and logging",
                "files": ["src/api/exceptions.py", "src/api/handlers.py"],
                "acceptance": "All errors return consistent, informative responses",
                "estimated_effort": "medium",
                "step_id": "rest-api-example:5",
                "sub_spec_id": None,
                "decomposition_hint": "atomic",
            },
            {
                "task": "Write comprehensive tests",
                "details": "Create unit and integration tests for all endpoints and business logic",
                "files": [
                    "tests/test_api/",
                    "tests/conftest.py",
                    "tests/test_models.py",
                ],
                "acceptance": "Test coverage > 90% and all tests pass",
                "estimated_effort": "high",
                "step_id": "rest-api-example:6",
                "sub_spec_id": None,
                "decomposition_hint": "composite: high-effort task requiring breakdown",
            },
        ],
        "review_notes": [
            "Consider adding rate limiting to prevent API abuse",
            "Implement request/response caching for better performance",
            "Add comprehensive logging for debugging and monitoring",
            "Consider using dependency injection for better testability",
        ],
    }

    api_file = specs_dir / "rest-api-example.yaml"
    with api_file.open("w", encoding="utf-8") as f:
        yaml.dump(
            api_spec, f, default_flow_style=False, sort_keys=False, allow_unicode=True
        )
    created_specs["rest-api-example"] = str(api_file)

    # 3. CLI Application Template
    cli_spec = {
        "metadata": {
            "id": "cli-app-example",
            "title": f"Build a CLI application for {project_name}",
            "inherits": ["cli-application", "base-coding-standards"],
            "created": "2025-01-01T00:00:00",
            "version": "1.0",
            "status": "draft",
            "parent_spec_id": None,
            "child_spec_ids": None,
            "author": "template-generator",
            "last_modified": None,
        },
        "context": {
            "project": project_name,
            "domain": "Command Line Interface",
            "dependencies": [
                {"name": "typer", "version": "0.12+"},
                {"name": "rich", "version": "13.0+"},
                {"name": "pydantic", "version": "2.0+"},
                {"name": "pyyaml", "version": "6.0+"},
                {"name": "click", "version": "8.0+"},
            ],
            "files_involved": [
                "src/cli/",
                "src/commands/",
                "src/config/",
                "tests/test_cli/",
                "main.py",
            ],
        },
        "requirements": {
            "functional": [
                "Create intuitive command-line interface with subcommands",
                "Implement configuration management with YAML/TOML files",
                "Add rich output formatting with colors and progress bars",
                "Support both interactive and non-interactive modes",
                "Provide comprehensive help and usage information",
                "Handle command-line arguments and options properly",
            ],
            "non_functional": [
                "CLI should be responsive and feel fast to users",
                "Error messages should be clear and actionable",
                "Help text should be comprehensive but not overwhelming",
                "Commands should follow Unix conventions",
                "Output should be both human and machine readable",
            ],
            "constraints": [
                "Use Typer for modern CLI framework features",
                "Follow Click conventions for consistency",
                "Support --help flag on all commands",
                "Exit with appropriate status codes",
            ],
        },
        "implementation": [
            {
                "task": "Set up CLI application structure",
                "details": "Create main CLI entry points with Typer, organize commands into logical groups",
                "files": ["main.py", "src/cli/app.py", "src/cli/__init__.py"],
                "acceptance": "CLI application runs and shows help information",
                "estimated_effort": "low",
                "step_id": "cli-app-example:0",
                "sub_spec_id": None,
                "decomposition_hint": "atomic",
            },
            {
                "task": "Implement core commands",
                "details": "Create essential commands with proper argument parsing and validation",
                "files": [
                    "src/commands/init.py",
                    "src/commands/config.py",
                    "src/commands/run.py",
                ],
                "acceptance": "Core commands execute successfully with appropriate output",
                "estimated_effort": "high",
                "step_id": "cli-app-example:1",
                "sub_spec_id": None,
                "decomposition_hint": "composite: high-effort task requiring breakdown",
            },
            {
                "task": "Add configuration management",
                "details": "Implement config file loading, validation, and management commands",
                "files": [
                    "src/config/manager.py",
                    "src/config/models.py",
                    "src/config/defaults.py",
                ],
                "acceptance": "Configuration can be loaded, validated, and modified via CLI",
                "estimated_effort": "medium",
                "step_id": "cli-app-example:2",
                "sub_spec_id": None,
                "decomposition_hint": "atomic",
            },
            {
                "task": "Enhanced output formatting",
                "details": "Use Rich library for colored output, progress bars, and formatted tables",
                "files": ["src/cli/output.py", "src/cli/styles.py"],
                "acceptance": "CLI output is visually appealing and informative",
                "estimated_effort": "medium",
                "step_id": "cli-app-example:3",
                "sub_spec_id": None,
                "decomposition_hint": "atomic",
            },
            {
                "task": "Add comprehensive error handling",
                "details": "Implement proper exception handling with user-friendly error messages",
                "files": ["src/cli/exceptions.py", "src/cli/handlers.py"],
                "acceptance": "All errors are caught and displayed clearly to users",
                "estimated_effort": "medium",
                "step_id": "cli-app-example:4",
                "sub_spec_id": None,
                "decomposition_hint": "atomic",
            },
            {
                "task": "Write CLI tests",
                "details": "Create tests using Typer's testing utilities for all commands",
                "files": ["tests/test_cli/", "tests/conftest.py"],
                "acceptance": "All CLI commands are thoroughly tested",
                "estimated_effort": "high",
                "step_id": "cli-app-example:5",
                "sub_spec_id": None,
                "decomposition_hint": "composite: high-effort task requiring breakdown",
            },
        ],
        "review_notes": [
            "Consider adding shell completion support for better user experience",
            "Implement logging configuration for debugging complex operations",
            "Add support for environment variable configuration",
            "Consider adding a plugin system if the CLI needs to be extensible",
        ],
    }

    cli_file = specs_dir / "cli-app-example.yaml"
    with cli_file.open("w", encoding="utf-8") as f:
        yaml.dump(
            cli_spec, f, default_flow_style=False, sort_keys=False, allow_unicode=True
        )
    created_specs["cli-app-example"] = str(cli_file)

    # 4. Testing and Quality Assurance Template
    testing_spec = {
        "metadata": {
            "id": "testing-qa-setup",
            "title": f"Set up comprehensive testing and QA for {project_name}",
            "inherits": ["base-coding-standards"],
            "created": "2025-01-01T00:00:00",
            "version": "1.0",
            "status": "draft",
            "parent_spec_id": None,
            "child_spec_ids": None,
            "author": "template-generator",
            "last_modified": None,
        },
        "context": {
            "project": project_name,
            "domain": "Testing and Quality Assurance",
            "dependencies": [
                {"name": "pytest", "version": "7.0+"},
                {"name": "pytest-cov", "version": "4.0+"},
                {"name": "pytest-asyncio", "version": "0.21+"},
                {"name": "pytest-mock", "version": "3.10+"},
                {"name": "ruff", "version": "0.1+"},
                {"name": "mypy", "version": "1.5+"},
                {"name": "pre-commit", "version": "3.0+"},
            ],
            "files_involved": [
                "tests/",
                "pytest.ini",
                "ruff.toml",
                "mypy.ini",
                ".pre-commit-config.yaml",
                "tox.ini",
            ],
        },
        "requirements": {
            "functional": [
                "Set up comprehensive test suite with unit and integration tests",
                "Configure code coverage reporting with minimum thresholds",
                "Implement static type checking with mypy",
                "Set up linting and formatting with ruff",
                "Create pre-commit hooks for quality gates",
                "Add performance and load testing for critical paths",
            ],
            "non_functional": [
                "Test suite should complete in under 5 minutes",
                "Code coverage should be above 90%",
                "All code should pass static type checking",
                "Linting should enforce consistent code style",
                "Tests should be reliable and not flaky",
            ],
            "constraints": [
                "Use pytest as the primary testing framework",
                "Follow AAA pattern (Arrange, Act, Assert) in tests",
                "Mock external dependencies in unit tests",
                "Use fixtures for common test setup",
            ],
        },
        "implementation": [
            {
                "task": "Configure pytest and test structure",
                "details": "Set up pytest configuration, test directory structure, and common fixtures",
                "files": ["pytest.ini", "tests/conftest.py", "tests/__init__.py"],
                "acceptance": "pytest runs successfully and discovers all tests",
                "estimated_effort": "low",
                "step_id": "testing-qa-setup:0",
                "sub_spec_id": None,
                "decomposition_hint": "atomic",
            },
            {
                "task": "Set up code coverage reporting",
                "details": "Configure pytest-cov for coverage tracking with HTML and terminal reports",
                "files": [".coveragerc", "pytest.ini"],
                "acceptance": "Coverage reports are generated and show accurate metrics",
                "estimated_effort": "low",
                "step_id": "testing-qa-setup:1",
                "sub_spec_id": None,
                "decomposition_hint": "atomic",
            },
            {
                "task": "Configure static type checking",
                "details": "Set up mypy configuration for strict type checking across the codebase",
                "files": ["mypy.ini", "pyproject.toml"],
                "acceptance": "mypy runs without errors on the entire codebase",
                "estimated_effort": "medium",
                "step_id": "testing-qa-setup:2",
                "sub_spec_id": None,
                "decomposition_hint": "atomic",
            },
            {
                "task": "Set up linting and formatting",
                "details": "Configure ruff for linting and formatting with project-specific rules",
                "files": ["ruff.toml", "pyproject.toml"],
                "acceptance": "ruff check and format run successfully on all code",
                "estimated_effort": "medium",
                "step_id": "testing-qa-setup:3",
                "sub_spec_id": None,
                "decomposition_hint": "atomic",
            },
            {
                "task": "Create pre-commit hooks",
                "details": "Set up pre-commit configuration to run quality checks before commits",
                "files": [".pre-commit-config.yaml"],
                "acceptance": "Pre-commit hooks run successfully and prevent bad commits",
                "estimated_effort": "low",
                "step_id": "testing-qa-setup:4",
                "sub_spec_id": None,
                "decomposition_hint": "atomic",
            },
            {
                "task": "Write example tests",
                "details": "Create comprehensive test examples covering different testing patterns",
                "files": [
                    "tests/test_example_unit.py",
                    "tests/test_example_integration.py",
                ],
                "acceptance": "Example tests demonstrate best practices and pass consistently",
                "estimated_effort": "medium",
                "step_id": "testing-qa-setup:5",
                "sub_spec_id": None,
                "decomposition_hint": "atomic",
            },
        ],
        "review_notes": [
            "Consider adding mutation testing with mutpy for test quality assessment",
            "Add property-based testing with hypothesis for edge case discovery",
            "Consider setting up automated security scanning with bandit",
            "Add performance benchmarking for critical code paths",
        ],
    }

    testing_file = specs_dir / "testing-qa-setup.yaml"
    with testing_file.open("w", encoding="utf-8") as f:
        yaml.dump(
            testing_spec,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
    created_specs["testing-qa-setup"] = str(testing_file)

    return created_specs


def create_getting_started_guide(
    specs_dir: Path, project_name: str, created_specs: dict[str, str]
) -> str:
    """Create a getting started guide that references the created specifications."""

    guide_content = f"""# Getting Started with {project_name}

Welcome to your new {project_name} project! This guide will help you get up and running quickly.

## 🚀 Quick Start

Your project has been bootstrapped with several example specifications that demonstrate common development patterns:

### Available Example Specifications

1. **Project Setup** (`setup-infrastructure.yaml`)
   - Sets up basic project structure, dependencies, and CI/CD
   - Perfect starting point for any new project
   - Run: `agentic-spec generate "Set up {project_name} infrastructure" --inherits setup-infrastructure`

2. **REST API Development** (`rest-api-example.yaml`)
   - Complete FastAPI application with database integration
   - Includes authentication, validation, and testing
   - Run: `agentic-spec generate "Build user management API" --inherits rest-api-example`

3. **CLI Application** (`cli-app-example.yaml`)
   - Modern CLI with Typer, Rich output, and configuration management
   - Includes subcommands, error handling, and testing
   - Run: `agentic-spec generate "Build data processing CLI" --inherits cli-app-example`

4. **Testing & QA Setup** (`testing-qa-setup.yaml`)
   - Comprehensive testing framework with coverage and quality tools
   - Includes pre-commit hooks and static analysis
   - Run: `agentic-spec generate "Set up testing for {project_name}" --inherits testing-qa-setup`

## 📖 Usage Examples

### Generate Your First Specification
```bash
# Use a template as starting point
agentic-spec generate "Build a user authentication system" --inherits rest-api-example

# Combine multiple templates
agentic-spec generate "Set up {project_name} with testing" --inherits setup-infrastructure testing-qa-setup

# Start from scratch
agentic-spec generate "Add real-time notifications to the app"
```

### Review and Manage Specifications
```bash
# List all specifications
agentic-spec review

# Show specification details
agentic-spec spec-detail SPEC_ID

# View task breakdown
agentic-spec task-tree SPEC_ID

# Start working on tasks
agentic-spec task-start SPEC_ID:0
agentic-spec task-complete SPEC_ID:0
```

### Visualize Your Project
```bash
# Show specification relationships
agentic-spec graph

# Generate visual graph
agentic-spec graph --output project-graph.png --show-tasks
```

## 🛠️ Development Workflow

1. **Generate specifications** for features or changes
2. **Review and refine** the generated implementation plan
3. **Track progress** using the task management system
4. **Expand complex tasks** into sub-specifications as needed
5. **Publish completed specs** when implementation is done

## 💡 Tips

- **Use inheritance** to leverage existing patterns and standards
- **Start with examples** and modify them for your specific needs
- **Expand high-effort tasks** into detailed sub-specifications
- **Track your progress** with the task management commands
- **Update templates** in `spec-templates/` to match your project needs

## 📚 Learn More

- Check `spec-templates/` for inheritance templates you can use
- Edit `prompt-templates/` to customize how specifications are generated
- Use `agentic-spec --help` to explore all available commands
- Read the documentation for advanced features and configuration

Happy coding! 🎉
"""

    guide_file = specs_dir / "GETTING_STARTED.md"
    with guide_file.open("w", encoding="utf-8") as f:
        f.write(guide_content)

    return str(guide_file)
