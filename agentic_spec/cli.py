"""Command-line interface for agentic specification generator."""

import logging
import logging.handlers
from pathlib import Path
import sys

import typer
import yaml

from . import cli_db as db_commands
from . import cli_utils as utils_commands

# Import CLI modules
from .cli_core import core_app
from .cli_db import db_app
from .cli_template import template_app
from .cli_utils import utils_app
from .cli_workflow import workflow_app
from .exceptions import (
    AgenticSpecError,
)


def _create_basic_prompt_templates(prompt_templates_dir: Path, project_name: str):
    """Create basic prompt templates for common use cases."""
    import importlib.resources

    # Try to load templates from configuration file
    try:
        # Get the path to the templates configuration file
        templates_package = importlib.resources.files("agentic_spec.templates")
        config_file = templates_package / "basic_prompt_templates.yaml"

        if config_file.is_file():
            # Read and parse the YAML configuration
            config_content = config_file.read_text(encoding="utf-8")
            templates_config = yaml.safe_load(config_content)

            # Process each template from the configuration
            for template_key, template_data in templates_config.get(
                "templates", {}
            ).items():
                filename = f"{template_key}.md"
                content = template_data.get("content", "")

                # Replace the project_name placeholder
                content = content.replace("{{project_name}}", project_name)

                # Write the template file
                template_path = prompt_templates_dir / filename
                template_path.write_text(content.strip(), encoding="utf-8")

            return

    except (ImportError, OSError, yaml.YAMLError) as e:
        # Fall back to default templates if configuration loading fails
        logger = logging.getLogger("agentic_spec")
        logger.warning("Failed to load prompt templates from configuration: %s", e)

    # Fallback: Create default templates if configuration is not available
    _create_default_prompt_templates(prompt_templates_dir, project_name)


def _create_default_prompt_templates(prompt_templates_dir: Path, project_name: str):
    """Create default prompt templates as fallback."""
    # Basic specification generation prompt
    basic_prompt = f"""You are generating a programming specification for the {project_name} project.

Context:
- Project: {{{{project_name}}}}
- Domain: {{{{domain}}}}
- User Role: {{{{user_role}}}}
- Target Audience: {{{{target_audience}}}}

Generate a comprehensive specification that includes:
1. Clear functional and non-functional requirements
2. Detailed implementation steps with effort estimates
3. Files that will be modified or created
4. Acceptance criteria for each task

Focus on practical, actionable specifications that can guide implementation.

Task: {{{{user_prompt}}}}"""

    # Feature addition prompt
    feature_prompt = f"""You are adding a new feature to the {project_name} project.

Context:
- Project: {{{{project_name}}}}
- Existing codebase: {{{{existing_files}}}}
- Architecture: {{{{architecture_notes}}}}

For this feature addition:
1. Consider integration with existing code
2. Maintain current coding standards
3. Include necessary tests
4. Plan for documentation updates

Focus on clean integration and maintaining code quality.

Feature to add: {{{{user_prompt}}}}"""

    # Bug fix prompt
    bugfix_prompt = f"""You are creating a specification to fix a bug in the {project_name} project.

Context:
- Project: {{{{project_name}}}}
- Bug description: {{{{user_prompt}}}}
- Affected components: {{{{affected_files}}}}

For this bug fix:
1. Identify root cause and scope
2. Plan minimal, targeted changes
3. Include regression testing
4. Consider edge cases

Focus on precise fixes without introducing new issues.

Bug to fix: {{{{user_prompt}}}}"""

    # Refactoring prompt
    refactor_prompt = f"""You are planning a refactoring task for the {project_name} project.

Context:
- Project: {{{{project_name}}}}
- Code to refactor: {{{{target_code}}}}
- Goal: {{{{user_prompt}}}}

For this refactoring:
1. Preserve existing functionality
2. Improve code quality/maintainability
3. Plan incremental changes
4. Ensure comprehensive testing

Focus on safe, incremental improvements.

Refactoring goal: {{{{user_prompt}}}}"""

    # Write the prompt templates
    templates = {
        "basic-specification.md": basic_prompt,
        "feature-addition.md": feature_prompt,
        "bug-fix.md": bugfix_prompt,
        "refactoring.md": refactor_prompt,
    }

    for filename, content in templates.items():
        template_path = prompt_templates_dir / filename
        template_path.write_text(content.strip(), encoding="utf-8")


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure logging for the CLI application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Configure logging format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Set up root logger
    logger = logging.getLogger("agentic_spec")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(log_format)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "agentic_spec.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(log_format)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger


# Create Typer app
app = typer.Typer(
    name="agentic-spec",
    help="AI-powered programming specification generator with inheritance and review",
    add_completion=False,
    no_args_is_help=True,
)

# Register sub-apps
app.add_typer(core_app, name="core")
app.add_typer(workflow_app, name="workflow")
app.add_typer(template_app, name="template")
app.add_typer(db_app, name="database")
app.add_typer(utils_app, name="utils")

# Import core commands for direct access
from .cli_core import expand_step, generate_spec, review_specs, show_graph
from .cli_template import (
    browse_templates,
    create_templates,
    manage_templates,
    preview_template,
)
from .cli_workflow import (
    approve_task,
    block_task,
    check_foundation_status,
    complete_task,
    override_strict_mode,
    publish_spec,
    reject_task,
    show_task_status,
    show_workflow_status,
    start_task,
    sync_foundation_spec,
    unblock_task,
)

app.command("generate")(generate_spec)
app.command("review")(review_specs)
app.command("graph")(show_graph)
app.command("expand")(expand_step)
app.command("task-start")(start_task)
app.command("task-complete")(complete_task)
app.command("workflow-status")(show_workflow_status)
app.command("publish")(publish_spec)
app.command("task-approve")(approve_task)
app.command("task-reject")(reject_task)
app.command("task-block")(block_task)
app.command("task-unblock")(unblock_task)
app.command("task-override")(override_strict_mode)
app.command("task-status")(show_task_status)
app.command("sync-foundation")(sync_foundation_spec)
app.command("check-foundation")(check_foundation_status)
app.command("templates")(create_templates)
app.command("template")(manage_templates)
app.command("browse-templates")(browse_templates)
app.command("preview-template")(preview_template)
app.command("migrate-bulk")(db_commands.migrate_bulk)
app.command("migrate-incremental")(db_commands.migrate_incremental)
app.command("migration-status")(db_commands.migration_status)
app.command("migration-report")(db_commands.migration_report)
app.command("init")(utils_commands.init_project)
app.command("config")(utils_commands.manage_config)
app.command("validate")(utils_commands.validate_templates)
app.command("render")(utils_commands.render_spec)
app.command("prompt")(utils_commands.prompt_command)


def main():
    """CLI entry point - synchronous wrapper for Typer."""
    try:
        # Initialize logging early
        logger = setup_logging()
        logger.info("Starting agentic-spec CLI")

        app()

    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(1)
    except AgenticSpecError as e:
        logger = logging.getLogger("agentic_spec")
        logger.exception("Application error")
        if e.details:
            logger.debug("Error details: %s", e.details)
        print(f"❌ {e.message}")
        sys.exit(1)
    except (SystemExit, KeyboardInterrupt):
        raise
    except (
        RuntimeError,
        ValueError,
        TypeError,
        AttributeError,
        ImportError,
        OSError,
    ) as e:
        logger = logging.getLogger("agentic_spec")
        logger.critical("Unexpected error: %s", e, exc_info=True)
        print("❌ Unexpected error occurred. Check logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
