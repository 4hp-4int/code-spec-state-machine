"""Base template generators for common project types."""

from pathlib import Path

import yaml


def create_base_templates(templates_dir: Path, project_name: str = "project"):
    """Create base template files for common project patterns.

    Creates full specification templates that users can inherit from,
    not just metadata snippets. These are complete specifications with
    all sections (metadata, context, requirements, implementation).
    """

    # Base coding standards specification template
    base_standards_spec = {
        "metadata": {
            "id": "base-coding-standards",
            "title": f"Coding standards and conventions for {project_name}",
            "inherits": [],
            "created": "2025-01-01T00:00:00",
            "version": "1.0",
            "status": "template",
            "parent_spec_id": None,
            "child_spec_ids": None,
            "author": "template-generator",
            "last_modified": None,
        },
        "context": {
            "project": project_name,
            "domain": "Development Standards and Best Practices",
            "dependencies": [
                {"name": "ruff", "version": "0.1+"},
                {"name": "pytest", "version": "7.0+"},
                {"name": "mypy", "version": "1.5+"},
                {"name": "pre-commit", "version": "3.0+"},
            ],
            "files_involved": [
                "pyproject.toml",
                "ruff.toml",
                "mypy.ini",
                ".pre-commit-config.yaml",
                "pytest.ini",
            ],
        },
        "requirements": {
            "functional": [
                "Enforce consistent code style across all Python files",
                "Require type hints for all public APIs",
                "Implement comprehensive testing with >90% coverage",
                "Use Google-style docstrings for documentation",
                "Follow semantic versioning for releases",
            ],
            "non_functional": [
                "Code should be readable and self-documenting",
                "All functions should have clear type signatures",
                "Error messages should be informative and actionable",
                "Code should follow the principle of least surprise",
            ],
            "constraints": [
                "Follow PEP 8 style guidelines",
                "Use ruff for linting and formatting",
                "Require pytest for all testing",
                "Use mypy for static type checking",
            ],
        },
        "implementation": [
            {
                "task": "Configure code formatting and linting",
                "details": "Set up ruff configuration for consistent code style",
                "files": ["ruff.toml", "pyproject.toml"],
                "acceptance": "All code passes ruff check and format",
                "estimated_effort": "low",
                "step_id": "base-coding-standards:0",
                "sub_spec_id": None,
                "decomposition_hint": "atomic",
            },
            {
                "task": "Set up type checking",
                "details": "Configure mypy for strict type checking",
                "files": ["mypy.ini", "pyproject.toml"],
                "acceptance": "All code passes mypy without errors",
                "estimated_effort": "medium",
                "step_id": "base-coding-standards:1",
                "sub_spec_id": None,
                "decomposition_hint": "atomic",
            },
            {
                "task": "Configure testing framework",
                "details": "Set up pytest with coverage reporting",
                "files": ["pytest.ini", "pyproject.toml"],
                "acceptance": "Tests run successfully with coverage reports",
                "estimated_effort": "low",
                "step_id": "base-coding-standards:2",
                "sub_spec_id": None,
                "decomposition_hint": "atomic",
            },
        ],
        "review_notes": [
            "Consider adding additional linting rules for specific project needs",
            "Ensure all team members understand the coding standards",
            "Update standards as project requirements evolve",
        ],
    }

    with (templates_dir / "base-coding-standards.yaml").open(
        "w", encoding="utf-8"
    ) as f:
        yaml.dump(
            base_standards_spec,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

    # Web API specification template
    web_api_spec = {
        "metadata": {
            "id": "web-api",
            "title": f"Web API development template for {project_name}",
            "inherits": ["base-coding-standards"],
            "created": "2025-01-01T00:00:00",
            "version": "1.0",
            "status": "template",
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
            ],
            "files_involved": [
                "main.py",
                "src/api/",
                "src/models/",
                "src/routes/",
                "tests/test_api/",
                "alembic/",
            ],
        },
        "requirements": {
            "functional": [
                "Create RESTful API endpoints following OpenAPI standards",
                "Implement request/response validation with Pydantic",
                "Add comprehensive error handling with proper HTTP status codes",
                "Generate interactive API documentation",
                "Support async operations for better performance",
            ],
            "non_functional": [
                "API should handle 1000+ concurrent requests",
                "Response times should be under 100ms for simple operations",
                "All endpoints should be fully documented",
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
                "details": "Create main FastAPI app with configuration and routing",
                "files": ["main.py", "src/api/app.py", "src/api/config.py"],
                "acceptance": "FastAPI application starts and serves basic endpoints",
                "estimated_effort": "medium",
                "step_id": "web-api:0",
                "sub_spec_id": None,
                "decomposition_hint": "atomic",
            },
            {
                "task": "Implement data models and validation",
                "details": "Create Pydantic models for request/response validation",
                "files": ["src/models/schemas.py", "src/models/database.py"],
                "acceptance": "Data models validate input/output correctly",
                "estimated_effort": "high",
                "step_id": "web-api:1",
                "sub_spec_id": None,
                "decomposition_hint": "composite: high-effort task requiring breakdown",
            },
            {
                "task": "Add comprehensive error handling",
                "details": "Implement custom exception handlers and error responses",
                "files": ["src/api/exceptions.py", "src/api/handlers.py"],
                "acceptance": "All errors return consistent, informative responses",
                "estimated_effort": "medium",
                "step_id": "web-api:2",
                "sub_spec_id": None,
                "decomposition_hint": "atomic",
            },
        ],
        "review_notes": [
            "Consider adding rate limiting to prevent API abuse",
            "Implement request/response caching for better performance",
            "Add comprehensive logging for debugging and monitoring",
        ],
    }

    with (templates_dir / "web-api.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(
            web_api_spec,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

    # CLI application specification template
    cli_app_spec = {
        "metadata": {
            "id": "cli-application",
            "title": f"CLI application development template for {project_name}",
            "inherits": ["base-coding-standards"],
            "created": "2025-01-01T00:00:00",
            "version": "1.0",
            "status": "template",
            "parent_spec_id": None,
            "child_spec_ids": None,
            "author": "template-generator",
            "last_modified": None,
        },
        "context": {
            "project": project_name,
            "domain": "Command Line Interface Development",
            "dependencies": [
                {"name": "typer", "version": "0.12+"},
                {"name": "rich", "version": "13.0+"},
                {"name": "pydantic", "version": "2.0+"},
                {"name": "pyyaml", "version": "6.0+"},
            ],
            "files_involved": [
                "main.py",
                "src/cli/",
                "src/commands/",
                "src/config/",
                "tests/test_cli/",
            ],
        },
        "requirements": {
            "functional": [
                "Create intuitive command-line interface with subcommands",
                "Implement configuration management with YAML files",
                "Add rich output formatting with colors and progress bars",
                "Support both interactive and non-interactive modes",
                "Provide comprehensive help and usage information",
            ],
            "non_functional": [
                "CLI should be responsive and feel fast to users",
                "Error messages should be clear and actionable",
                "Help text should be comprehensive but not overwhelming",
                "Commands should follow Unix conventions",
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
                "details": "Create main CLI entry points with Typer",
                "files": ["main.py", "src/cli/app.py"],
                "acceptance": "CLI application runs and shows help information",
                "estimated_effort": "low",
                "step_id": "cli-application:0",
                "sub_spec_id": None,
                "decomposition_hint": "atomic",
            },
            {
                "task": "Implement core commands",
                "details": "Create essential commands with argument parsing",
                "files": ["src/commands/", "src/cli/"],
                "acceptance": "Core commands execute successfully",
                "estimated_effort": "high",
                "step_id": "cli-application:1",
                "sub_spec_id": None,
                "decomposition_hint": "composite: high-effort task requiring breakdown",
            },
            {
                "task": "Add configuration management",
                "details": "Implement config file loading and validation",
                "files": ["src/config/manager.py", "src/config/models.py"],
                "acceptance": "Configuration can be loaded and validated",
                "estimated_effort": "medium",
                "step_id": "cli-application:2",
                "sub_spec_id": None,
                "decomposition_hint": "atomic",
            },
        ],
        "review_notes": [
            "Consider adding shell completion support",
            "Implement logging configuration for debugging",
            "Add support for environment variable configuration",
        ],
    }

    with (templates_dir / "cli-application.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(
            cli_app_spec,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

    # Data analysis specification template
    data_analysis_spec = {
        "metadata": {
            "id": "data-analysis",
            "title": f"Data analysis template for {project_name}",
            "inherits": ["base-coding-standards"],
            "created": "2025-01-01T00:00:00",
            "version": "1.0",
            "status": "template",
            "parent_spec_id": None,
            "child_spec_ids": None,
            "author": "template-generator",
            "last_modified": None,
        },
        "context": {
            "project": project_name,
            "domain": "Data Analysis and Visualization",
            "dependencies": [
                {"name": "pandas", "version": "2.0+"},
                {"name": "numpy", "version": "1.24+"},
                {"name": "matplotlib", "version": "3.7+"},
                {"name": "seaborn", "version": "0.12+"},
                {"name": "jupyter", "version": "1.0+"},
            ],
            "files_involved": [
                "src/analysis/",
                "notebooks/",
                "data/",
                "visualizations/",
                "reports/",
            ],
        },
        "requirements": {
            "functional": [
                "Load and clean data from various sources",
                "Perform exploratory data analysis",
                "Create informative visualizations",
                "Generate automated reports",
                "Implement reproducible analysis pipelines",
            ],
            "non_functional": [
                "Analysis should handle datasets up to 1GB",
                "Visualizations should be publication-ready",
                "Code should be well-documented and reproducible",
                "Results should be validated and tested",
            ],
            "constraints": [
                "Use pandas for data manipulation",
                "Use matplotlib/seaborn for visualizations",
                "Avoid loops in favor of vectorized operations",
                "Use Jupyter notebooks for exploration only",
            ],
        },
        "implementation": [
            {
                "task": "Set up data loading pipeline",
                "details": "Create functions to load data from various sources",
                "files": ["src/analysis/data_loader.py"],
                "acceptance": "Data can be loaded consistently from all sources",
                "estimated_effort": "medium",
                "step_id": "data-analysis:0",
                "sub_spec_id": None,
                "decomposition_hint": "atomic",
            },
            {
                "task": "Implement analysis functions",
                "details": "Create reusable analysis and statistical functions",
                "files": ["src/analysis/statistics.py", "src/analysis/transforms.py"],
                "acceptance": "Analysis functions work correctly and are tested",
                "estimated_effort": "high",
                "step_id": "data-analysis:1",
                "sub_spec_id": None,
                "decomposition_hint": "composite: high-effort task requiring breakdown",
            },
            {
                "task": "Create visualization toolkit",
                "details": "Build standardized plotting functions",
                "files": ["src/analysis/plotting.py", "src/analysis/themes.py"],
                "acceptance": "Visualizations are consistent and publication-ready",
                "estimated_effort": "medium",
                "step_id": "data-analysis:2",
                "sub_spec_id": None,
                "decomposition_hint": "atomic",
            },
        ],
        "review_notes": [
            "Consider adding interactive visualizations with plotly",
            "Implement data validation and quality checks",
            "Add automated testing for analysis functions",
        ],
    }

    with (templates_dir / "data-analysis.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(
            data_analysis_spec,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

    # Machine learning specification template
    ml_spec = {
        "metadata": {
            "id": "machine-learning",
            "title": f"Machine learning template for {project_name}",
            "inherits": ["data-analysis", "base-coding-standards"],
            "created": "2025-01-01T00:00:00",
            "version": "1.0",
            "status": "template",
            "parent_spec_id": None,
            "child_spec_ids": None,
            "author": "template-generator",
            "last_modified": None,
        },
        "context": {
            "project": project_name,
            "domain": "Machine Learning and Model Development",
            "dependencies": [
                {"name": "scikit-learn", "version": "1.3+"},
                {"name": "pandas", "version": "2.0+"},
                {"name": "numpy", "version": "1.24+"},
                {"name": "joblib", "version": "1.3+"},
                {"name": "optuna", "version": "3.4+"},
            ],
            "files_involved": [
                "src/models/",
                "src/features/",
                "src/evaluation/",
                "src/training/",
                "models/",
                "experiments/",
            ],
        },
        "requirements": {
            "functional": [
                "Implement feature engineering pipelines",
                "Train and validate machine learning models",
                "Implement hyperparameter optimization",
                "Create model evaluation and metrics tracking",
                "Build model persistence and loading system",
            ],
            "non_functional": [
                "Models should achieve defined performance metrics",
                "Training should be reproducible with fixed seeds",
                "Feature engineering should be reusable",
                "Model evaluation should be comprehensive",
            ],
            "constraints": [
                "Use scikit-learn for standard ML algorithms",
                "Implement proper train/validation/test splits",
                "Use joblib for model persistence",
                "Follow MLOps best practices",
            ],
        },
        "implementation": [
            {
                "task": "Build feature engineering pipeline",
                "details": "Create preprocessing and feature extraction functions",
                "files": [
                    "src/features/preprocessing.py",
                    "src/features/engineering.py",
                ],
                "acceptance": "Features can be extracted consistently and reliably",
                "estimated_effort": "high",
                "step_id": "machine-learning:0",
                "sub_spec_id": None,
                "decomposition_hint": "composite: high-effort task requiring breakdown",
            },
            {
                "task": "Implement model training framework",
                "details": "Create training loops with cross-validation",
                "files": ["src/training/trainer.py", "src/training/validation.py"],
                "acceptance": "Models can be trained and validated systematically",
                "estimated_effort": "high",
                "step_id": "machine-learning:1",
                "sub_spec_id": None,
                "decomposition_hint": "composite: high-effort task requiring breakdown",
            },
            {
                "task": "Build evaluation and metrics system",
                "details": "Create comprehensive model evaluation toolkit",
                "files": ["src/evaluation/metrics.py", "src/evaluation/reports.py"],
                "acceptance": "Model performance can be evaluated comprehensively",
                "estimated_effort": "medium",
                "step_id": "machine-learning:2",
                "sub_spec_id": None,
                "decomposition_hint": "atomic",
            },
        ],
        "review_notes": [
            "Consider adding automated hyperparameter tuning",
            "Implement model versioning and experiment tracking",
            "Add support for ensemble methods",
        ],
    }

    with (templates_dir / "machine-learning.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(
            ml_spec, f, default_flow_style=False, sort_keys=False, allow_unicode=True
        )
