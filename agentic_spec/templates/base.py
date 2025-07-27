"""Base template generators for common project types."""

from pathlib import Path

import yaml


def create_base_templates(templates_dir: Path, project_name: str = "project"):
    """Create base template files for common project patterns."""

    # Base coding standards
    base_standards = {
        "project": project_name,
        "coding_standards": {
            "python": {
                "style": "PEP 8",
                "docstrings": "Google style",
                "type_hints": "required",
                "testing": "pytest",
            },
            "javascript": {
                "style": "ESLint + Prettier",
                "testing": "Jest",
                "typescript": "recommended",
            },
            "general": {
                "error_handling": "comprehensive with logging",
                "documentation": "inline comments + README",
                "version_control": "semantic commits",
            },
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    }

    with open(templates_dir / "base-coding-standards.yaml", "w") as f:
        yaml.dump(base_standards, f, default_flow_style=False)

    # Web API template
    web_api_template = {
        "domain": "web API",
        "dependencies": ["fastapi", "pydantic", "uvicorn"],
        "patterns": {
            "architecture": "REST API with OpenAPI documentation",
            "error_handling": "HTTP status codes with detailed error responses",
            "validation": "Pydantic models for request/response validation",
            "testing": "pytest with test client",
        },
        "files_involved": ["main.py", "models.py", "routes/", "tests/"],
    }

    with open(templates_dir / "web-api.yaml", "w") as f:
        yaml.dump(web_api_template, f, default_flow_style=False)

    # CLI application template
    cli_template = {
        "domain": "command-line interface",
        "dependencies": ["click", "rich", "typer"],
        "patterns": {
            "argument_parsing": "click or argparse for complex CLIs",
            "output_formatting": "rich for enhanced terminal output",
            "configuration": "YAML or TOML configuration files",
            "testing": "pytest with click.testing.CliRunner",
        },
        "files_involved": ["cli.py", "commands/", "config.py", "tests/"],
    }

    with open(templates_dir / "cli-application.yaml", "w") as f:
        yaml.dump(cli_template, f, default_flow_style=False)

    # Data analysis template
    data_analysis_template = {
        "domain": "data analysis",
        "dependencies": ["pandas", "numpy", "matplotlib", "jupyter"],
        "patterns": {
            "data_loading": "pandas for structured data, numpy for arrays",
            "visualization": "matplotlib/seaborn for plots, plotly for interactive",
            "processing": "vectorized operations, avoid loops",
            "notebooks": "jupyter for exploration, scripts for production",
        },
        "files_involved": ["analysis.py", "data/", "notebooks/", "visualizations/"],
    }

    with open(templates_dir / "data-analysis.yaml", "w") as f:
        yaml.dump(data_analysis_template, f, default_flow_style=False)

    # Machine learning template
    ml_template = {
        "domain": "machine learning",
        "dependencies": ["scikit-learn", "pandas", "numpy", "joblib"],
        "patterns": {
            "model_training": "train/validation/test splits",
            "feature_engineering": "sklearn preprocessing pipelines",
            "model_persistence": "joblib for sklearn models",
            "evaluation": "cross-validation and metrics tracking",
        },
        "files_involved": [
            "train.py",
            "predict.py",
            "models/",
            "features/",
            "evaluation/",
        ],
    }

    with open(templates_dir / "machine-learning.yaml", "w") as f:
        yaml.dump(ml_template, f, default_flow_style=False)
