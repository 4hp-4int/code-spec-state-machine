"""Command-line interface for agentic specification generator."""

import asyncio
from datetime import datetime
import json
import logging
import logging.handlers
from pathlib import Path
import sys
import uuid

import typer
from typer import Argument, Option
import yaml

from .config import AgenticSpecConfig, get_config_manager, parse_cli_overrides
from .core import SpecGenerator
from .async_db import AsyncSpecManager, SQLiteBackend
from .db import FileBasedSpecStorage
from .exceptions import (
    AgenticSpecError,
    AIServiceError,
    ConfigurationError,
    FileSystemError,
    SpecificationError,
    TemplateError,
    ValidationError,
)
from .graph_visualization import get_spec_stats, print_spec_graph
from .models import ApprovalDB, ApprovalLevel, ContextParameters, TaskStatus
from .prompt_editor import PromptEditor
from .prompt_template_loader import PromptTemplateLoader
from .template_loader import (
    TemplateLoader,
    list_templates,
    render_specification_template,
)
from .template_validator import TemplateValidator
from .templates.base import create_base_templates
from .workflow import TaskWorkflowManager, WorkflowViolationError


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


def get_prompt_input(args_prompt: str | None) -> str:
    """Get prompt from various input sources in order of precedence.

    Args:
        args_prompt: Prompt from command line arguments

    Returns:
        The prompt string from the highest priority source

    Raises:
        ValidationError: If no valid prompt is provided
    """
    logger = logging.getLogger("agentic_spec")

    # 1. Command line argument (highest priority)
    if args_prompt:
        logger.debug("Using command line prompt: %s...", args_prompt[:50])
        return args_prompt

    # 2. Piped input (stdin)
    if not sys.stdin.isatty():
        try:
            prompt = sys.stdin.read().strip()
            if prompt:
                logger.debug("Using piped input prompt")
                return prompt
            logger.warning("Piped input was empty")
        except (KeyboardInterrupt, EOFError) as e:
            logger.info("Piped input interrupted by user")
            msg = "Input cancelled by user"
            raise ValidationError(msg, str(e)) from e
        except OSError as e:
            logger.exception("Error reading piped input")
            msg = "Failed to read piped input"
            raise FileSystemError(msg, str(e)) from e

    # 3. Interactive multiline input (lowest priority)
    print("Enter your prompt (press Ctrl+D on Unix/Ctrl+Z on Windows when done):")
    try:
        lines = []
        while True:
            try:
                line = input()
                lines.append(line)
            except EOFError:
                break
        prompt = "\n".join(lines).strip()
        if prompt:
            logger.debug("Using interactive input prompt")
            return prompt
        logger.warning("Interactive input was empty")
        msg = "No prompt provided"
        raise ValidationError(msg)
    except KeyboardInterrupt:
        logger.info("Interactive input cancelled by user")
        print("\nCancelled.")
        sys.exit(1)


# Create Typer app
app = typer.Typer(
    name="agentic-spec",
    help="AI-powered programming specification generator with inheritance and review",
    add_completion=False,
    no_args_is_help=True,
)


async def initialize_generator(
    spec_templates_dir: Path,
    specs_dir: Path,
    config_file: Path | None = None,
    cli_overrides: list[str] | None = None,
) -> SpecGenerator:
    """Initialize the SpecGenerator with configuration."""
    logger = logging.getLogger("agentic_spec")

    try:
        # Load configuration
        config_manager = get_config_manager(config_file)
        config = config_manager.load_config()
        logger.debug("Configuration loaded successfully")

        # Apply CLI overrides
        if cli_overrides is None:
            cli_overrides = []
        cli_override_dict = parse_cli_overrides(cli_overrides)
        config = config_manager.merge_cli_overrides(config, cli_override_dict)
        logger.debug("Applied %d CLI overrides", len(cli_override_dict))

    except Exception as e:
        logger.exception("Error loading configuration")
        msg = "Failed to load configuration"
        raise ConfigurationError(msg, str(e)) from e

    try:
        # Use config to set paths if not overridden by CLI
        final_spec_templates_dir = (
            Path(spec_templates_dir)
            if spec_templates_dir
            else Path(config.directories.get_spec_templates_dir())
        )
        final_specs_dir = (
            Path(specs_dir) if specs_dir else Path(config.directories.specs_dir)
        )

        # Ensure directories exist
        final_spec_templates_dir.mkdir(parents=True, exist_ok=True)
        final_specs_dir.mkdir(parents=True, exist_ok=True)

        generator = SpecGenerator(final_spec_templates_dir, final_specs_dir, config)
        logger.debug("SpecGenerator initialized successfully")
    except Exception as e:
        logger.exception("Error initializing SpecGenerator")
        msg = "Failed to initialize application"
        raise FileSystemError(msg, str(e)) from e
    else:
        return generator


@app.command("generate")
def generate_spec(
    prompt: str | None = Argument(
        None,
        help="Programming task prompt (optional - can use stdin or interactive input)",
    ),
    inherits: list[str] | None = Option(
        None, "--inherits", help="Base templates to inherit from"
    ),
    project: str = Option("project", "--project", help="Project name for context"),
    user_role: str | None = Option(
        None,
        "--user-role",
        help="User role context (e.g., 'solo developer', 'team lead')",
    ),
    target_audience: str | None = Option(
        None,
        "--target-audience",
        help="Target audience (e.g., 'solo developer', 'enterprise team')",
    ),
    tone: str | None = Option(
        None,
        "--tone",
        help="Desired tone (e.g., 'practical', 'detailed', 'beginner-friendly')",
    ),
    complexity: str | None = Option(
        None,
        "--complexity",
        help="Complexity level (e.g., 'simple', 'intermediate', 'advanced')",
    ),
    feedback: bool = Option(
        False, "--feedback", help="Enable interactive feedback collection"
    ),
    template: str | None = Option(
        None,
        "--template",
        help="Override default template with specific prompt template (e.g., 'feature-addition', 'bug-fix')",
    ),
    interactive_templates: bool = Option(
        False,
        "--interactive-templates",
        help="Show interactive template selection menu instead of using default",
    ),
    dry_run: bool = Option(
        False,
        "--dry-run",
        help="Preview what would be generated without saving to file",
    ),
    spec_templates_dir: str = Option(
        "spec-templates",
        "--spec-templates-dir",
        "--templates-dir",
        help="YAML spec templates directory",
    ),
    specs_dir: str = Option("specs", "--specs-dir", help="Generated specs directory"),
    config: str | None = Option(None, "--config", help="Path to configuration file"),
    set_options: list[str] | None = Option(
        None,
        "--set",
        help="Override config values (e.g., --set prompt_settings.temperature=0.2)",
    ),
):
    """Generate a new programming specification from a prompt.

    The prompt can be provided as an argument, piped via stdin, or entered
    interactively. By default, uses the 'specification-generation' template
    for consistent, high-quality specs.

    Use --template to override the default template, --interactive-templates
    to select from available templates, or --inherits to build upon existing
    YAML templates. Customize generation context with role, audience, tone,
    and complexity options.
    """

    async def _generate():
        logger = logging.getLogger("agentic_spec")

        # Initialize mutable defaults
        inherits_list = inherits if inherits is not None else []
        set_options_list = set_options if set_options is not None else []

        # Convert string paths to Path objects
        spec_templates_dir_path = Path(spec_templates_dir)
        specs_dir_path = Path(specs_dir)
        config_path = Path(config) if config else None

        try:
            try:
                generator = await initialize_generator(
                    spec_templates_dir_path,
                    specs_dir_path,
                    config_path,
                    set_options_list,
                )
            except (ConfigurationError, FileSystemError) as e:
                logger.exception("Failed to initialize")
                print(f"❌ Failed to initialize application: {e.message}")
                raise typer.Exit(1) from None
            except Exception:
                logger.exception("Failed to initialize")
                print("❌ Failed to initialize application")
                raise typer.Exit(1) from None

            # Get prompt input
            final_prompt = get_prompt_input(prompt)
            if not final_prompt:

                def _raise_validation_error():
                    logger.warning("No prompt provided for generation")
                    msg = "No prompt provided"
                    raise ValidationError(msg)

                _raise_validation_error()

            # Handle template selection
            selected_template = await _handle_template_selection(
                template, interactive_templates, generator
            )

            logger.info(
                "Starting specification generation for prompt: %s...",
                final_prompt[:100],
            )

            # Build context parameters from CLI args, defaulting to config
            context_params = ContextParameters(
                user_role=user_role or generator.config.default_context.user_role,
                target_audience=target_audience
                or generator.config.default_context.target_audience,
                desired_tone=tone or generator.config.default_context.desired_tone,
                complexity_level=complexity
                or generator.config.default_context.complexity_level,
                time_constraints=generator.config.default_context.time_constraints,
            )

            prompt_preview = final_prompt[:50]
            ellipsis = "..." if len(final_prompt) > 50 else ""
            print(f"🔄 Generating specification for: {prompt_preview}{ellipsis}")

            # AI generation with fallback handling
            try:
                spec = await generator.generate_spec(
                    final_prompt,
                    inherits_list,
                    project,
                    context_params,
                    custom_template=selected_template,
                )
                logger.info("Specification generated successfully")
            except Exception as e:
                logger.exception("AI generation failed")
                msg = "Failed to generate specification using AI"
                raise AIServiceError(msg, str(e)) from e

            # Handle dry-run vs normal save
            if dry_run:
                print("🔍 DRY RUN MODE - Specification preview:")
                print("=" * 60)
                print(f"📋 Title: {spec.metadata.title}")
                print(f"🆔 ID: {spec.metadata.id}")
                print(f"📁 Project: {spec.context.project}")
                print(f"🏷️  Domain: {spec.context.domain}")
                print(f"📦 Dependencies: {len(spec.context.dependencies)}")
                print(
                    f"✅ Functional Requirements: {len(spec.requirements.functional)}"
                )
                print(f"⚙️  Implementation Steps: {len(spec.implementation)}")
                print("=" * 60)
                print()
                print("📄 Full YAML specification:")
                print("-" * 40)

                # Show the YAML content
                from dataclasses import asdict

                import yaml

                spec_yaml = yaml.dump(
                    asdict(spec), default_flow_style=False, sort_keys=False
                )
                print(spec_yaml)

                print("-" * 40)
                print("💡 Use without --dry-run to save this specification")

            else:
                # Save specification with error handling
                try:
                    spec_path = generator.save_spec(spec)
                    logger.info("Specification saved to %s", spec_path)
                    
                    # Also save to database
                    db_path = Path(specs_dir) / "specifications.db"
                    backend = SQLiteBackend(str(db_path))
                    async with AsyncSpecManager(backend) as manager:
                        await manager.save_spec_to_db(spec)
                        logger.info("Specification saved to database")
                    
                except Exception as e:
                    logger.exception("Error saving specification")
                    msg = "Failed to save specification"
                    raise FileSystemError(msg, str(e)) from e

                print(f"✅ Specification generated: {spec_path}")
                print(f"📋 Spec ID: {spec.metadata.id}")
                print("💾 Saved to database")

            # Auto-review if enabled in config (but skip in dry-run)
            if not dry_run and generator.config.workflow.auto_review:
                try:
                    print("🔍 Reviewing specification...")
                    review_notes = await generator.review_spec(spec)

                    if review_notes:
                        spec.review_notes = review_notes
                        generator.save_spec(spec)  # Save with review notes
                        
                        # Update database with review notes
                        db_path = Path(specs_dir) / "specifications.db"
                        backend = SQLiteBackend(str(db_path))
                        async with AsyncSpecManager(backend) as manager:
                            await manager.save_spec_to_db(spec)
                        
                        logger.info("Review notes added to specification")

                        print("📝 Review feedback:")
                        for note in review_notes:
                            print(f"  • {note}")
                except (AIServiceError, ConnectionError, TimeoutError) as e:
                    logger.warning("Auto-review failed: %s", e)
                    print("⚠️  Auto-review failed, continuing without review")

            # Collect feedback if requested or enabled in config (but skip in dry-run)
            if not dry_run and (feedback or generator.config.workflow.collect_feedback):
                try:
                    feedback_data = generator.prompt_engineer.collect_feedback(
                        output_content=str(spec_path), interactive=True
                    )
                    if feedback_data:
                        spec.feedback_history.append(feedback_data)
                        generator.save_spec(spec)  # Save with feedback
                        
                        # Update database with feedback
                        db_path = Path(specs_dir) / "specifications.db"
                        backend = SQLiteBackend(str(db_path))
                        async with AsyncSpecManager(backend) as manager:
                            await manager.save_spec_to_db(spec)
                        
                        print("💾 Feedback saved with specification")
                        logger.info("User feedback collected and saved")
                except (ValidationError, FileSystemError) as e:
                    logger.warning("Feedback collection failed: %s", e)
                    print("⚠️  Feedback collection failed, continuing without feedback")

            print(
                "\n💡 Next step: Review and approve specification before implementation"
            )

        except ValidationError as e:
            logger.exception("Validation error")
            print(f"❌ {e.message}")
            raise typer.Exit(1) from None
        except AgenticSpecError as e:
            logger.exception("Application error")
            print(f"❌ {e.message}")
            raise typer.Exit(1) from None
        except Exception:
            logger.exception("Unexpected error during generation")
            print("❌ Failed to generate specification")
            raise typer.Exit(1) from None

    asyncio.run(_generate())


@app.command("review")
def review_specs(
    templates_dir: str = Option(
        "templates", "--templates-dir", help="Templates directory"
    ),
    specs_dir: str = Option("specs", "--specs-dir", help="Generated specs directory"),
):
    """List available specifications for review.

    Shows all generated specifications in the specs directory with their basic
    information.
    """
    logger = logging.getLogger("agentic_spec")

    try:
        # Convert string to Path object
        specs_dir_path = Path(specs_dir)

        logger.info("Listing specifications in %s", specs_dir_path)
        # List available specs for review
        if not specs_dir_path.exists():
            logger.warning("Specs directory does not exist: %s", specs_dir_path)
            msg = "Specifications directory not found"
            raise FileSystemError(msg)

        specs = list(specs_dir_path.glob("*.yaml"))
        if not specs:
            logger.info("No specifications found for review")
            print("❌ No specifications found")
            return

        print("📋 Available specifications:")

        # Create a spec generator to load specs
        spec_gen = SpecGenerator(Path(templates_dir), specs_dir_path)

        for i, spec_path in enumerate(specs):
            try:
                spec = spec_gen.load_spec(spec_path)
                title = spec.metadata.title
                spec_id = spec.metadata.id
                status_emoji = "🚀" if spec.metadata.status == "implemented" else "📝"
                print(f"  {i}: {status_emoji} {title} ({spec_id})")
            except Exception:
                # Fallback to filename if loading fails
                print(f"  {i}: {spec_path.name}")

        logger.info("Listed %d specifications", len(specs))

    except FileSystemError as e:
        logger.exception("File system error")
        print(f"❌ {e.message}")
        raise typer.Exit(1) from None
    except Exception:
        logger.exception("Error listing specifications")
        print("❌ Failed to list specifications")
        raise typer.Exit(1) from None


@app.command("templates")
def create_templates(
    project: str = Option("project", "--project", help="Project name for context"),
    templates_dir: str = Option(
        "templates", "--templates-dir", help="Templates directory"
    ),
):
    """Create base templates for common project patterns.

    Generates template files for web APIs, CLI applications, data analysis,
    machine learning projects, and coding standards.
    """
    logger = logging.getLogger("agentic_spec")

    try:
        # Convert string to Path object
        templates_dir_path = Path(templates_dir)

        logger.info("Creating base templates in %s", templates_dir_path)
        create_base_templates(templates_dir_path, project)
        print(f"✅ Base templates created in {templates_dir}")
        logger.info("Base templates created successfully")
    except Exception:
        logger.exception("Error creating base templates")
        print("❌ Failed to create base templates")
        raise typer.Exit(1) from None


@app.command("graph")
def show_graph(
    specs_dir: str = Option("specs", "--specs-dir", help="Generated specs directory"),
):
    """Display specification dependency graph and statistics.

    Shows a visual representation of how specifications relate to each other
    and provides statistics about the specification tree.
    """
    print_spec_graph(specs_dir)

    print("\n📈 Statistics:")
    stats = get_spec_stats(specs_dir)
    print(f"  Total specs: {stats['total_specs']}")
    print(f"  Root specs: {stats['root_specs']}")
    print(f"  Leaf specs: {stats['leaf_specs']}")
    print(f"  Max depth: {stats['max_depth']}")
    print(f"  Status breakdown: {stats['status_counts']}")


@app.command("expand")
def expand_step(
    step_id: str = Argument(
        ...,
        help="Step ID in format 'spec_id:step_index' to expand into a detailed "
        "sub-specification",
    ),
    templates_dir: str = Option(
        "templates", "--templates-dir", help="Templates directory"
    ),
    specs_dir: str = Option("specs", "--specs-dir", help="Generated specs directory"),
    config: str | None = Option(None, "--config", help="Path to configuration file"),
    set_options: list[str] = Option([], "--set", help="Override configuration values"),
):
    """Expand an implementation step into a detailed sub-specification.

    Takes a step ID (format: spec_id:step_index) and generates a detailed
    sub-specification for that step, creating a parent-child relationship.
    """

    async def _expand():
        logger = logging.getLogger("agentic_spec")

        # Parse step_id format: spec_id:step_index
        if ":" not in step_id:
            print("❌ Step ID must be in format 'spec_id:step_index'")
            return

        spec_id_part, step_index = step_id.rsplit(":", 1)

        try:
            generator = await initialize_generator(
                templates_dir, specs_dir, config, set_options
            )

            # Find the parent specification
            parent_spec = generator.find_spec_by_id(spec_id_part)
            if not parent_spec:
                print(f"❌ Specification {spec_id_part} not found")
                return

            print(f"🔄 Expanding step {step_id} from spec {spec_id_part[:8]}...")

            # Generate sub-specification
            sub_spec = await generator.generate_sub_spec(parent_spec, step_id)

            if sub_spec:
                # Save both specs (parent updated with child reference, new child spec)
                generator.save_spec(parent_spec)
                sub_spec_path = generator.save_spec(sub_spec)
                
                # Also save both specs to database
                db_path = Path(specs_dir) / "specifications.db"
                backend = SQLiteBackend(str(db_path))
                async with AsyncSpecManager(backend) as manager:
                    await manager.save_spec_to_db(parent_spec)
                    await manager.save_spec_to_db(sub_spec)

                print(f"✅ Sub-specification generated: {sub_spec_path}")
                print(f"📋 Sub-spec ID: {sub_spec.metadata.id}")
                print(f"🔗 Linked to parent step: {step_id}")
                print("💾 Saved to database")

                # Auto-review sub-spec
                print("🔍 Reviewing sub-specification...")
                review_notes = await generator.review_spec(sub_spec)

                if review_notes:
                    sub_spec.review_notes = review_notes
                    generator.save_spec(sub_spec)
                    
                    # Update database with review notes
                    db_path = Path(specs_dir) / "specifications.db"
                    backend = SQLiteBackend(str(db_path))
                    async with AsyncSpecManager(backend) as manager:
                        await manager.save_spec_to_db(sub_spec)

                    print("📝 Review feedback:")
                    for note in review_notes:
                        print(f"  • {note}")
            else:
                print("❌ Failed to generate sub-specification")

        except Exception:
            logger.exception("Error expanding step")
            print("❌ Failed to expand step")
            raise typer.Exit(1) from None

    asyncio.run(_expand())


@app.command("publish")
def publish_spec(
    spec_id: str = Argument(..., help="Specification ID to mark as implemented"),
    specs_dir: str = Option("specs", "--specs-dir", help="Generated specs directory"),
    config: str | None = Option(None, "--config", help="Path to configuration file"),
    set_options: list[str] = Option([], "--set", help="Override configuration values"),
):
    """Mark a specification as implemented and update its status.

    Changes the specification status from 'draft' to 'implemented' and
    updates the specification graph.
    """

    async def _publish():
        logger = logging.getLogger("agentic_spec")

        try:
            generator = await initialize_generator(
                Path("templates"), specs_dir, config, set_options
            )

            # Find the specification
            target_spec = generator.find_spec_by_id(spec_id)
            if not target_spec:
                print(f"❌ Specification {spec_id} not found")
                return

            # Update status to implemented
            target_spec.metadata.status = "implemented"

            # Save the updated spec
            generator.save_spec(target_spec)

            print(f"✅ Specification {spec_id[:8]} published as implemented")
            print("📋 Status updated: draft → implemented")

            # Show updated graph
            print("\n📊 Updated specification graph:")
            print_spec_graph(specs_dir)

        except Exception:
            logger.exception("Error publishing spec")
            print("❌ Failed to publish specification")
            raise typer.Exit(1) from None

    asyncio.run(_publish())


@app.command("init")
def init_project(
    force: bool = Option(False, "--force", help="Overwrite existing configuration"),
    spec_templates_dir: str = Option(
        "spec-templates",
        "--spec-templates-dir",
        "--templates-dir",
        help="YAML spec templates directory",
    ),
    prompt_templates_dir: str = Option(
        "prompt-templates",
        "--prompt-templates-dir",
        help="Text prompt templates directory",
    ),
    specs_dir: str = Option("specs", "--specs-dir", help="Specs directory"),
):
    """Initialize a new agentic-spec project with interactive setup.

    Creates the project structure, configuration file, and base templates.
    """
    logger = logging.getLogger("agentic_spec")

    try:
        print("🚀 Welcome to agentic-spec!")
        print("Let's set up your project...")
        print()

        # Create directories
        spec_templates_path = Path(spec_templates_dir)
        prompt_templates_path = Path(prompt_templates_dir)
        specs_path = Path(specs_dir)

        print("📁 Creating directories...")
        spec_templates_path.mkdir(exist_ok=True)
        prompt_templates_path.mkdir(exist_ok=True)
        specs_path.mkdir(exist_ok=True)
        logs_path = Path("logs")
        logs_path.mkdir(exist_ok=True)

        print(f"  ✅ {spec_templates_dir}/")
        print(f"  ✅ {prompt_templates_dir}/")
        print(f"  ✅ {specs_dir}/")
        print("  ✅ logs/")
        print()

        # Interactive configuration
        print("⚙️  Let's configure your AI provider...")

        # Ask for AI provider
        provider_choice = typer.prompt(
            "Choose AI provider",
            type=typer.Choice(["openai"], case_sensitive=False),
            default="openai",
        )

        # Ask for API key (optional)
        api_key = typer.prompt(
            "Enter your OpenAI API key (or press Enter to use OPENAI_API_KEY env var)",
            default="",
            hide_input=True,
        )

        # Ask for project name
        project_name = typer.prompt("What's your project name?", default="my-project")

        # Create configuration
        config_data = {
            "ai_settings": {
                "default_provider": provider_choice,
                "providers": {
                    provider_choice: {
                        "provider_type": provider_choice,
                        "default_model": "gpt-4o-mini",
                        "api_key": api_key if api_key else None,
                        "timeout": 120.0,
                    }
                },
            },
            "directories": {
                "spec_templates_dir": spec_templates_dir,
                "prompt_templates_dir": prompt_templates_dir,
                "specs_dir": specs_dir,
                "config_dir": ".",
            },
            "prompt_settings": {
                "model": "gpt-4o-mini",
                "temperature": 0.1,
                "enable_web_search": True,
            },
            "default_context": {
                "user_role": "solo developer",
                "target_audience": "solo developer",
                "desired_tone": "practical",
                "complexity_level": "intermediate",
                "time_constraints": "production ready",
            },
        }

        # Write configuration file
        config_file = Path("agentic_spec_config.yaml")
        if config_file.exists() and not force:
            overwrite = typer.confirm(
                f"Configuration file {config_file} already exists. Overwrite?"
            )
            if not overwrite:
                print("❌ Setup cancelled.")
                return

        with config_file.open("w") as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

        print(f"  ✅ {config_file}")
        print()

        # Create base spec templates
        print("📋 Creating base spec templates...")
        try:
            create_base_templates(spec_templates_path, project_name)
            print("  ✅ Base spec templates created")
        except Exception as e:
            print(f"  ⚠️  Warning: Could not create spec templates: {e}")

        # Create foundation spec automatically
        print("🏗️  Creating foundation specification...")
        try:
            # Initialize a temporary generator to create foundation spec
            config_obj = AgenticSpecConfig(**config_data)
            temp_generator = SpecGenerator(spec_templates_path, specs_path, config_obj)
            success = temp_generator.sync_foundation_spec()
            if success:
                print("  ✅ Foundation spec created")
            else:
                print("  ⚠️  Warning: Could not create foundation spec")
        except Exception as e:
            print(f"  ⚠️  Warning: Could not create foundation spec: {e}")

        # Create basic prompt templates
        print("✏️  Creating basic prompt templates...")
        try:
            _create_basic_prompt_templates(prompt_templates_path, project_name)
            print("  ✅ Prompt templates created")
        except Exception as e:
            print(f"  ⚠️  Warning: Could not create prompt templates: {e}")

        print()
        print("🎉 Project initialized successfully!")
        print()
        print("Next steps:")
        print("  1. Run 'agentic-spec generate \"your first specification\"'")
        print(
            f"  2. Check the {spec_templates_dir}/ directory for YAML inheritance templates"
        )
        print(
            f"  3. Edit prompt templates in {prompt_templates_dir}/ to customize generation"
        )
        print("  4. Use 'agentic-spec review' to see your specifications")
        print()

        if not api_key:
            print("💡 Remember to set your OPENAI_API_KEY environment variable:")
            print("   export OPENAI_API_KEY=your-api-key-here")
            print()

    except Exception as e:
        logger.exception("Error during project initialization")
        print(f"❌ Initialization failed: {e}")
        raise typer.Exit(1) from None


@app.command("config")
def manage_config(
    action: str = Argument(
        ..., help="Configuration action: 'init', 'show', or 'validate'"
    ),
    config: str | None = Option(None, "--config", help="Path to configuration file"),
):
    """Manage application configuration.

    Actions:
    - init: Create a default configuration file
    - show: Display current configuration
    - validate: Check configuration file for errors
    """
    try:
        config_manager = get_config_manager(config)

        if action == "init":
            # Create default config file
            try:
                config_path = config_manager.create_default_config_file()
                print(f"✅ Default configuration created: {config_path}")
                print("📝 Edit the file to customize your workflow settings")
            except FileExistsError:
                print("❌ Configuration file already exists")
                print("💡 Use --force to overwrite existing configuration")

        elif action == "show":
            # Show current configuration
            config_data = config_manager.load_config()
            print("📋 Current Configuration:")
            print("=" * 50)
            config_dict = config_data.model_dump()
            print(json.dumps(config_dict, indent=2))

        elif action == "validate":
            # Validate configuration file
            if config_manager.config_file.exists():
                config_data = config_manager.load_config()
                errors = config_manager.validate_config_schema(config_data.model_dump())
                if errors:
                    print("❌ Configuration validation failed:")
                    for error in errors:
                        print(f"  • {error}")
                else:
                    print("✅ Configuration is valid")
            else:
                print("❌ No configuration file found")

        else:
            print("📋 Configuration Commands:")
            print("  agentic-spec config init     - Create default configuration file")
            print("  agentic-spec config show     - Show current configuration")
            print("  agentic-spec config validate - Validate configuration file")
            print("\n💡 Use --set to override configuration values:")
            print(
                '  agentic-spec generate "task" --set prompt_settings.temperature=0.2'
            )

    except Exception as e:
        logger = logging.getLogger("agentic_spec")
        logger.exception("Error managing config")
        msg = "Failed to manage configuration"
        raise ConfigurationError(msg, str(e)) from e


@app.command("template")
def manage_templates(
    action: str = Argument(..., help="Template action: 'list' or 'info'"),
    template_name: str | None = Option(
        None, "--template", help="Template name for info command"
    ),
    templates_dir: str = Option(
        "templates", "--templates-dir", help="Templates directory"
    ),
):
    """Manage and inspect templates.

    Actions:
    - list: Show all available templates
    - info: Display detailed information about a specific template
    """
    try:
        if action == "list":
            templates = list_templates()
            if templates:
                print("📋 Available Templates:")
                for template in templates:
                    print(f"  • {template}")
            else:
                print("❌ No templates found")

        elif action == "info":
            if not template_name:
                print("❌ Template name required. Use --template <name>")
                return

            loader = TemplateLoader(templates_dir)
            info = loader.get_template_info(template_name)

            print(f"📄 Template Information: {template_name}")
            print(f"  Exists: {'✅' if info['exists'] else '❌'}")
            print(f"  Path: {info['path']}")
            if info["exists"]:
                print(f"  Size: {info['size']} bytes")
                print(f"  Modified: {info['modified']}")

        else:
            print("📋 Template Commands:")
            print("  agentic-spec template list           - List available templates")
            print(
                "  agentic-spec template info --template <name> - Show template information"
            )

    except Exception as e:
        logger = logging.getLogger("agentic_spec")
        logger.exception("Error managing templates")
        msg = "Failed to manage templates"
        raise TemplateError(msg, str(e)) from e


@app.command("validate")
def validate_templates(
    templates_dir: str = Option(
        "templates", "--templates-dir", help="Templates directory"
    ),
):
    """Validate all templates for correctness and structure.

    Checks template syntax, structure, and dependencies to ensure
    they can be used for specification generation.
    """
    try:
        print("🔍 Validating templates...")

        validator = TemplateValidator(templates_dir)
        results = validator.validate_all_templates()

        if not results:
            print("❌ No templates found to validate")
            return

        valid_count = sum(1 for r in results.values() if r["valid"])
        total_count = len(results)

        print(f"📊 Validation Results: {valid_count}/{total_count} templates valid")
        print()

        for template_name, result in results.items():
            status = "✅" if result["valid"] else "❌"
            print(f"{status} {template_name}")

            if result["errors"]:
                for error in result["errors"]:
                    print(f"    ❌ {error}")

            if result["warnings"]:
                for warning in result["warnings"]:
                    print(f"    ⚠️  {warning}")

            print(f"    Type: {result['info'].get('type', 'unknown')}")
            if result["extends"]:
                print(f"    Extends: {result['extends']}")
            if result["blocks"]:
                print(f"    Blocks: {', '.join(result['blocks'])}")
            print()

    except Exception as e:
        logger = logging.getLogger("agentic_spec")
        logger.exception("Error validating templates")
        msg = "Failed to validate templates"
        raise TemplateError(msg, str(e)) from e


@app.command("sync-foundation")
def sync_foundation_spec(
    templates_dir: str = Option(
        "templates", "--templates-dir", help="Templates directory"
    ),
    specs_dir: str = Option("specs", "--specs-dir", help="Generated specs directory"),
    config: str | None = Option(None, "--config", help="Path to configuration file"),
    set_options: list[str] = Option([], "--set", help="Override configuration values"),
    force: bool = Option(
        False, "--force", help="Force sync even if foundation spec is current"
    ),
):
    """Sync foundation specification with current codebase state.

    Analyzes the current codebase structure, dependencies, and architecture
    to update the agentic-spec-foundation.yaml template with accurate information.
    """

    async def _sync():
        logger = logging.getLogger("agentic_spec")

        try:
            generator = await initialize_generator(
                templates_dir, specs_dir, config, set_options
            )

            print("🔍 Analyzing current codebase...")

            # Check if sync is needed
            if not force and not generator.check_foundation_sync_needed():
                print("✅ Foundation spec is already current")
                return

            print("🔄 Syncing foundation spec with codebase...")
            success = generator.sync_foundation_spec()

            if success:
                print("✅ Foundation spec successfully synced")
                print(
                    f"📄 Updated: {Path(templates_dir) / 'agentic-spec-foundation.yaml'}"
                )

                # Show what was updated
                try:
                    foundation = generator.load_template("agentic-spec-foundation")
                    last_synced = foundation.get("_last_synced", "Unknown")
                    print(f"🕒 Last synced: {last_synced}")

                    deps_count = len(
                        foundation.get("context", {}).get("dependencies", [])
                    )
                    print(f"📦 Dependencies tracked: {deps_count}")
                    print(
                        f"📋 Coding standards: {len(foundation.get('coding_standards', []))}"
                    )
                except (OSError, KeyError, ValueError, TypeError):
                    pass
            else:
                print("❌ Failed to sync foundation spec")

        except Exception as e:
            logger.exception("Error syncing foundation spec")
            msg = "Failed to sync foundation specification"
            raise SpecificationError(msg, str(e)) from e

    asyncio.run(_sync())


@app.command("check-foundation")
def check_foundation_status(
    templates_dir: str = Option(
        "templates", "--templates-dir", help="Templates directory"
    ),
    specs_dir: str = Option("specs", "--specs-dir", help="Generated specs directory"),
    config: str | None = Option(None, "--config", help="Path to configuration file"),
    set_options: list[str] = Option([], "--set", help="Override configuration values"),
):
    """Check if foundation specification needs to be synced.

    Analyzes the foundation spec and determines if it's out of sync
    with the current codebase state.
    """

    async def _check():
        logger = logging.getLogger("agentic_spec")

        try:
            generator = await initialize_generator(
                templates_dir, specs_dir, config, set_options
            )

            print("🔍 Checking foundation spec status...")

            try:
                foundation = generator.load_template("agentic-spec-foundation")
                last_synced = foundation.get("_last_synced")
                sync_version = foundation.get("_sync_version", "unknown")

                print("📄 Foundation Spec Status:")
                print("  Exists: ✅")
                print(f"  Last synced: {last_synced or 'Never'}")
                print(f"  Sync version: {sync_version}")

                needs_sync = generator.check_foundation_sync_needed()
                if needs_sync:
                    print("  Status: ⚠️  Needs sync")
                    print("\n💡 Run 'agentic-spec sync-foundation' to update")
                else:
                    print("  Status: ✅ Current")

            except (OSError, UnicodeDecodeError, KeyError, ValueError):
                print("📄 Foundation Spec Status:")
                print("  Exists: ❌ Not found")
                print("  Status: ⚠️  Needs creation")
                print("\n💡 Run 'agentic-spec sync-foundation' to create")

        except Exception as e:
            logger.exception("Error checking foundation status")
            msg = "Failed to check foundation status"
            raise SpecificationError(msg, str(e)) from e

    asyncio.run(_check())


@app.command("render")
def render_spec(
    spec_id: str = Argument(..., help="Specification ID to render"),
    template_name: str = Option(
        "child_template.html", "--template", help="Template name for rendering"
    ),
    output: Path | None = Option(
        None, "--output", help="Output file path for rendered template"
    ),
    templates_dir: str = Option(
        "templates", "--templates-dir", help="Templates directory"
    ),
    specs_dir: str = Option("specs", "--specs-dir", help="Generated specs directory"),
    config: str | None = Option(None, "--config", help="Path to configuration file"),
    set_options: list[str] = Option([], "--set", help="Override configuration values"),
):
    """Render a specification using a template.

    Takes a specification ID and renders it using the specified template,
    either displaying the result or saving it to a file.
    """

    async def _render():
        logger = logging.getLogger("agentic_spec")

        try:
            generator = await initialize_generator(
                templates_dir, specs_dir, config, set_options
            )

            # Find the specification
            target_spec = generator.find_spec_by_id(spec_id)
            if not target_spec:
                print(f"❌ Specification {spec_id} not found")
                return

            print(
                f"🎨 Rendering specification {spec_id[:8]} with template {template_name}..."
            )

            # Convert spec to dict for template rendering
            from dataclasses import asdict

            spec_dict = asdict(target_spec)

            # Render template
            rendered = render_specification_template(spec_dict, template_name)

            # Save or display result
            if output:
                output.write_text(rendered, encoding="utf-8")
                print(f"✅ Rendered template saved: {output}")
            else:
                print("📄 Rendered Template:")
                print("=" * 50)
                print(rendered)

        except Exception:
            logger.exception("Error rendering template")
            print("❌ Failed to render template")
            raise typer.Exit(1) from None

    asyncio.run(_render())


@app.command("prompt")
def prompt_command(
    action: str = Argument(..., help="Prompt action: 'edit', 'list', or 'new'"),
    name: str | None = Argument(None, help="Name of prompt to edit/create"),
    config_dir: str = Option(".", "--config-dir", help="Configuration directory"),
):
    """Manage prompts using system editor.

    Actions:
    - edit <name>: Edit an existing prompt or create a new one
    - list: Show all available prompts
    - new <name>: Create a new prompt (alias for edit)
    """
    logger = logging.getLogger("agentic_spec")

    try:
        editor = PromptEditor(Path(config_dir))

        if action == "edit" or action == "new":
            if not name:
                print("❌ Prompt name required for edit/new command")
                print("💡 Usage: agentic-spec prompt edit <name>")
                return

            try:
                print(f"📝 Opening prompt '{name}' in editor...")
                updated_content = editor.edit_prompt(name)

                if updated_content.strip():
                    print(f"✅ Prompt '{name}' saved successfully")
                    print(f"📄 Content length: {len(updated_content)} characters")
                else:
                    print(f"⚠️  Prompt '{name}' is empty")

            except FileNotFoundError as e:
                print(f"❌ Prompt file not found: {e}")
                print("💡 A new prompt file will be created when you save")

            except ConfigurationError as e:
                print(f"❌ Editor error: {e.message}")
                print(
                    "💡 Make sure your $EDITOR is set or a default editor is available"
                )

        elif action == "list":
            print("📋 Available prompts:")
            prompts = editor.list_prompts()

            if prompts:
                for i, prompt_name in enumerate(prompts, 1):
                    print(f"  {i}. {prompt_name}")
                print(f"\n💡 Found {len(prompts)} prompt(s)")
                print("💡 Use 'agentic-spec prompt edit <name>' to edit a prompt")
            else:
                print("❌ No prompts found")
                print(
                    "💡 Use 'agentic-spec prompt edit <name>' to create your first prompt"
                )

        else:
            print("📋 Prompt Commands:")
            print("  agentic-spec prompt edit <name>  - Edit or create a prompt")
            print("  agentic-spec prompt list         - List all available prompts")
            print(
                "  agentic-spec prompt new <name>   - Create a new prompt (alias for edit)"
            )
            print()
            print("💡 Prompts are saved in the prompts/ directory as .md files")
            print(
                "💡 Set your $EDITOR environment variable to use your preferred editor"
            )

    except Exception as e:
        logger.exception("Error managing prompts")
        print(f"❌ Failed to manage prompts: {e}")
        raise typer.Exit(1) from None


@app.command("browse-templates")
def browse_templates(
    prompt_templates_dir: str = Option(
        "prompt-templates",
        "--prompt-templates-dir",
        help="Prompt templates directory",
    ),
):
    """Browse available prompt templates with descriptions and use cases."""
    logger = logging.getLogger("agentic_spec")

    try:
        templates_dir = Path(prompt_templates_dir)
        loader = PromptTemplateLoader(templates_dir)

        templates = loader.list_template_metadata()

        if not templates:
            print("❌ No prompt templates found")
            print(f"💡 Check the {prompt_templates_dir}/ directory")
            return

        print("📋 Available Prompt Templates:")
        print("=" * 50)

        # Separate user-facing templates from internal ones
        user_templates = [t for t in templates if not _is_internal_template(t.name)]
        internal_templates = [t for t in templates if _is_internal_template(t.name)]

        if user_templates:
            print("\n🎯 User Templates:")
            for i, template in enumerate(user_templates, 1):
                print(f"  {i}. {template.name}")
                print(f"     📝 {template.description}")
                print(f"     💡 {template.use_case}")
                print()

        if internal_templates:
            print("🔧 Internal Templates (used by the system):")
            for template in internal_templates:
                print(f"  • {template.name}")
                print(f"    📝 {template.description}")
            print()

        print("💡 Use 'agentic-spec preview-template <name>' to see template content")
        print(
            "💡 Use 'agentic-spec generate --template <name> \"your prompt\"' to use a template"
        )

    except Exception as e:
        logger.exception("Error browsing templates")
        print(f"❌ Failed to browse templates: {e}")
        raise typer.Exit(1) from None


@app.command("preview-template")
def preview_template(
    template_name: str = Argument(..., help="Name of template to preview"),
    prompt_templates_dir: str = Option(
        "prompt-templates",
        "--prompt-templates-dir",
        help="Prompt templates directory",
    ),
):
    """Preview the content of a specific prompt template."""
    logger = logging.getLogger("agentic_spec")

    try:
        templates_dir = Path(prompt_templates_dir)
        loader = PromptTemplateLoader(templates_dir)

        # Get template metadata
        try:
            metadata = loader.get_template_metadata(template_name)
        except FileNotFoundError:
            print(f"❌ Template '{template_name}' not found")
            print("💡 Use 'agentic-spec browse-templates' to see available templates")
            raise typer.Exit(1) from None

        # Load and display template content
        content = loader.render_template(template_name)

        print(f"📋 Template: {metadata.name}")
        print("=" * 50)
        print(f"📝 Description: {metadata.description}")
        print(f"💡 Use case: {metadata.use_case}")
        print()
        print("📄 Template Content:")
        print("-" * 30)
        print(content)
        print("-" * 30)
        print()
        print(
            f'💡 Use with: agentic-spec generate --template {template_name} "your prompt"'
        )

    except Exception as e:
        logger.exception("Error previewing template")
        print(f"❌ Failed to preview template: {e}")
        raise typer.Exit(1) from None


def _is_internal_template(template_name: str) -> bool:
    """Check if a template is internal (used by the system) vs user-facing."""
    internal_templates = {
        "specification-generation",
        "specification-review",
        "step-expansion",
        "context-enhancement",
    }
    return template_name in internal_templates


async def _handle_template_selection(
    template: str | None, interactive_templates: bool, generator: SpecGenerator
) -> str | None:
    """Handle template selection for specification generation.

    Args:
        template: Template name provided via --template option, or None
        interactive_templates: Whether to show interactive template selection
        generator: SpecGenerator instance for accessing configuration

    Returns:
        Selected template name, or None if using default generation
    """
    prompt_loader = PromptTemplateLoader(
        generator.spec_templates_dir.parent
        / generator.config.directories.prompt_templates_dir
    )

    # If template is explicitly provided, validate and use it
    if template:
        if not prompt_loader.template_exists(template):
            available = [
                t
                for t in prompt_loader.list_templates()
                if not _is_internal_template(t)
            ]
            available_str = ", ".join(available) if available else "none"
            raise TemplateError(
                f"Template '{template}' not found. Available templates: {available_str}"
            )

        print(f"✅ Using template: {template}")
        return template

    # If interactive templates is requested, show selection menu
    if interactive_templates:
        available_templates = [
            metadata
            for metadata in prompt_loader.list_template_metadata()
            if not _is_internal_template(metadata.name)
        ]

        if not available_templates:
            print(
                "ℹ️  No user prompt templates available. Using specification-generation template."
            )
            return "specification-generation"

        # Show available templates
        print("\n📋 Available prompt templates:")
        for i, metadata in enumerate(available_templates, 1):
            print(f"  {i}. {metadata.name}")
            print(f"     {metadata.description}")
            print(f"     Use case: {metadata.use_case}")
            print()

        print("  0. Use specification-generation template (default)")
        print()

        # Get user selection
        while True:
            try:
                choice = typer.prompt("Select a template (number)", type=int)
                if choice == 0:
                    print("✅ Using specification-generation template")
                    return "specification-generation"
                if 1 <= choice <= len(available_templates):
                    selected = available_templates[choice - 1]
                    print(f"✅ Using template: {selected.name}")
                    return selected.name
                print(
                    f"❌ Please enter a number between 0 and {len(available_templates)}"
                )
            except (ValueError, typer.Abort):
                print("❌ Please enter a valid number")
            except KeyboardInterrupt:
                print("\n❌ Template selection cancelled")
                raise typer.Abort()

    # Default behavior: use specification-generation template
    if prompt_loader.template_exists("specification-generation"):
        print("✅ Using specification-generation template (default)")
        return "specification-generation"
    print("⚠️  specification-generation template not found. Using default generation.")
    return None


@app.command("task-start")
def start_task(
    step_id: str = Argument(..., help="Step ID in format 'spec_id:step_index'"),
    started_by: str = Option("user", "--by", help="Who is starting the task"),
    notes: str | None = Option(
        None, "--notes", help="Optional notes for starting the task"
    ),
    specs_dir: str = Option("specs", "--specs-dir", help="Generated specs directory"),
    strict_mode: bool = Option(
        True, "--strict/--no-strict", help="Enable strict mode enforcement"
    ),
):
    """Start working on a task."""
    
    async def start_task_async():
        try:
            # Parse spec_id and step_index from step_id
            if ":" not in step_id:
                raise typer.BadParameter("Step ID must be in format 'spec_id:step_index'")

            spec_id, step_index_str = step_id.split(":", 1)
            try:
                step_index = int(step_index_str)
            except ValueError:
                raise typer.BadParameter("Step index must be a number")

            # Connect to database
            db_path = Path(specs_dir) / "specifications.db"
            backend = SQLiteBackend(str(db_path))
            
            async with AsyncSpecManager(backend) as manager:
                # Get specification
                spec = await manager.get_specification(spec_id)
                if not spec:
                    print(f"❌ Specification {spec_id} not found")
                    raise typer.Exit(1)

                # Get tasks for this specification
                tasks = await manager.backend.get_tasks_for_spec(spec_id)
                
                # Find the specific task
                target_task = None
                for task in tasks:
                    if task.step_index == step_index:
                        target_task = task
                        break
                
                if not target_task:
                    print(f"❌ Task at step {step_index} not found for specification {spec_id}")
                    raise typer.Exit(1)

                # Check if task can be started
                if target_task.status not in [TaskStatus.PENDING, TaskStatus.BLOCKED]:
                    print(f"❌ Task {step_id} is already {target_task.status.value}")
                    print(f"   Current status: {target_task.status.value}")
                    if target_task.status == TaskStatus.IN_PROGRESS:
                        print(f"   Started at: {target_task.started_at}")
                    elif target_task.status == TaskStatus.COMPLETED:
                        print(f"   Completed at: {target_task.completed_at}")
                    raise typer.Exit(1)

                # Strict mode enforcement - check if previous tasks are completed
                if strict_mode and step_index > 0:
                    for task in tasks:
                        if task.step_index < step_index and task.status not in [TaskStatus.COMPLETED, TaskStatus.APPROVED]:
                            print(f"❌ Strict mode violation: Task {task.step_index} must be completed before starting task {step_index}")
                            print(f"   Blocking task status: {task.status.value}")
                            print(f"   Use --no-strict to override, or complete task {spec_id}:{task.step_index} first")
                            raise typer.Exit(1)

                # Update task to in_progress
                target_task.status = TaskStatus.IN_PROGRESS
                target_task.started_at = datetime.now()
                if notes:
                    target_task.completion_notes = notes

                await manager.backend.update_task(target_task)

                print(f"✅ Task {step_id} started by {started_by}")
                print(f"📋 Task: {target_task.task}")
                
                if notes:
                    print(f"📝 Notes: {notes}")
                
                print(f"⏰ Started at: {target_task.started_at.strftime('%Y-%m-%d %H:%M:%S')}")

        except typer.BadParameter:
            raise
        except typer.Exit:
            raise
        except Exception as e:
            print(f"❌ Error starting task: {e}")
            raise typer.Exit(1)

    asyncio.run(start_task_async())


@app.command("task-complete")
def complete_task(
    step_id: str = Argument(..., help="Step ID in format 'spec_id:step_index'"),
    completed_by: str = Option("user", "--by", help="Who completed the task"),
    notes: str | None = Option(None, "--notes", help="Completion notes"),
    specs_dir: str = Option("specs", "--specs-dir", help="Generated specs directory"),
):
    """Mark a task as completed."""
    
    async def complete_task_async():
        try:
            # Parse spec_id and step_index from step_id
            if ":" not in step_id:
                raise typer.BadParameter("Step ID must be in format 'spec_id:step_index'")

            spec_id, step_index_str = step_id.split(":", 1)
            try:
                step_index = int(step_index_str)
            except ValueError:
                raise typer.BadParameter("Step index must be a number")

            # Connect to database
            db_path = Path(specs_dir) / "specifications.db"
            backend = SQLiteBackend(str(db_path))
            
            async with AsyncSpecManager(backend) as manager:
                # Get specification
                spec = await manager.get_specification(spec_id)
                if not spec:
                    print(f"❌ Specification {spec_id} not found")
                    raise typer.Exit(1)

                # Get tasks for this specification
                tasks = await manager.backend.get_tasks_for_spec(spec_id)
                
                # Find the specific task
                target_task = None
                for task in tasks:
                    if task.step_index == step_index:
                        target_task = task
                        break
                
                if not target_task:
                    print(f"❌ Task at step {step_index} not found for specification {spec_id}")
                    raise typer.Exit(1)

                # Check if task can be completed
                if target_task.status != TaskStatus.IN_PROGRESS:
                    print(f"❌ Task {step_id} is not in progress")
                    print(f"   Current status: {target_task.status.value}")
                    if target_task.status == TaskStatus.COMPLETED:
                        print(f"   Already completed at: {target_task.completed_at}")
                    elif target_task.status == TaskStatus.PENDING:
                        print(f"   Task must be started first: agentic-spec task-start {step_id}")
                    raise typer.Exit(1)

                # Update task to completed
                target_task.status = TaskStatus.COMPLETED
                target_task.completed_at = datetime.now()
                if notes:
                    if target_task.completion_notes:
                        target_task.completion_notes += f"\n\nCompletion notes by {completed_by}: {notes}"
                    else:
                        target_task.completion_notes = f"Completion notes by {completed_by}: {notes}"

                await manager.backend.update_task(target_task)

                print(f"✅ Task {step_id} completed by {completed_by}")
                print(f"📋 Task: {target_task.task}")
                
                if notes:
                    print(f"📝 Completion notes: {notes}")
                
                print(f"⏰ Completed at: {target_task.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Calculate duration if we have start time
                if target_task.started_at:
                    duration = target_task.completed_at - target_task.started_at
                    hours = duration.total_seconds() / 3600
                    print(f"⌛ Duration: {hours:.1f} hours")

        except typer.BadParameter:
            raise
        except typer.Exit:
            raise
        except Exception as e:
            print(f"❌ Error completing task: {e}")
            raise typer.Exit(1)

    asyncio.run(complete_task_async())


@app.command("task-approve")
def approve_task(
    step_id: str = Argument(..., help="Step ID in format 'spec_id:step_index'"),
    approved_by: str = Option("user", "--by", help="Who is approving the task"),
    level: str = Option(
        "self", "--level", help="Approval level: self, peer, ai, admin"
    ),
    comments: str | None = Option(None, "--comments", help="Approval comments"),
    override_reason: str | None = Option(
        None, "--override", help="Override reason if needed"
    ),
    specs_dir: str = Option("specs", "--specs-dir", help="Generated specs directory"),
):
    """Approve a completed task."""
    
    async def approve_task_async():
        try:
            # Validate approval level
            try:
                approval_level = ApprovalLevel(level.lower())
            except ValueError:
                valid_levels = [level.value for level in ApprovalLevel]
                print(f"❌ Invalid approval level. Valid levels: {', '.join(valid_levels)}")
                raise typer.Exit(1)

            # Parse spec_id and step_index from step_id
            if ":" not in step_id:
                raise typer.BadParameter("Step ID must be in format 'spec_id:step_index'")

            spec_id, step_index_str = step_id.split(":", 1)
            try:
                step_index = int(step_index_str)
            except ValueError:
                raise typer.BadParameter("Step index must be a number")

            # Connect to database
            db_path = Path(specs_dir) / "specifications.db"
            backend = SQLiteBackend(str(db_path))
            
            async with AsyncSpecManager(backend) as manager:
                # Get specification
                spec = await manager.get_specification(spec_id)
                if not spec:
                    print(f"❌ Specification {spec_id} not found")
                    raise typer.Exit(1)

                # Get tasks for this specification
                tasks = await manager.backend.get_tasks_for_spec(spec_id)
                
                # Find the specific task
                target_task = None
                for task in tasks:
                    if task.step_index == step_index:
                        target_task = task
                        break
                
                if not target_task:
                    print(f"❌ Task at step {step_index} not found for specification {spec_id}")
                    raise typer.Exit(1)

                # Check if task can be approved
                if target_task.status != TaskStatus.COMPLETED:
                    print(f"❌ Task {step_id} is not completed")
                    print(f"   Current status: {target_task.status.value}")
                    if target_task.status == TaskStatus.PENDING:
                        print(f"   Task must be started and completed first")
                    elif target_task.status == TaskStatus.IN_PROGRESS:
                        print(f"   Task must be completed first: agentic-spec task-complete {step_id}")
                    raise typer.Exit(1)

                # Create approval record
                approval = ApprovalDB(
                    id=str(uuid.uuid4()),
                    task_id=target_task.id,
                    level=approval_level,
                    approved_by=approved_by,
                    approved_at=datetime.now(),
                    comments=comments,
                    override_reason=override_reason,
                )

                await manager.backend.create_approval(approval)

                # Update task status to approved
                target_task.status = TaskStatus.APPROVED
                target_task.approved_at = datetime.now()
                await manager.backend.update_task(target_task)

                print(f"✅ Task {step_id} approved by {approved_by} ({level})")
                print(f"📋 Task: {target_task.task}")
                
                if comments:
                    print(f"💬 Comments: {comments}")
                if override_reason:
                    print(f"⚠️  Override reason: {override_reason}")
                
                print(f"⏰ Approved at: {approval.approved_at.strftime('%Y-%m-%d %H:%M:%S')}")

        except typer.BadParameter:
            raise
        except typer.Exit:
            raise
        except Exception as e:
            print(f"❌ Error approving task: {e}")
            raise typer.Exit(1)

    asyncio.run(approve_task_async())


@app.command("task-reject")
def reject_task(
    step_id: str = Argument(..., help="Step ID in format 'spec_id:step_index'"),
    rejected_by: str = Option("user", "--by", help="Who is rejecting the task"),
    reason: str = Option(..., "--reason", help="Rejection reason"),
    specs_dir: str = Option("specs", "--specs-dir", help="Generated specs directory"),
):
    """Reject a task, requiring rework."""
    
    async def reject_task_async():
        try:
            # Parse spec_id and step_index from step_id
            if ":" not in step_id:
                raise typer.BadParameter("Step ID must be in format 'spec_id:step_index'")

            spec_id, step_index_str = step_id.split(":", 1)
            try:
                step_index = int(step_index_str)
            except ValueError:
                raise typer.BadParameter("Step index must be a number")

            # Connect to database
            db_path = Path(specs_dir) / "specifications.db"
            backend = SQLiteBackend(str(db_path))
            
            async with AsyncSpecManager(backend) as manager:
                # Get specification
                spec = await manager.get_specification(spec_id)
                if not spec:
                    print(f"❌ Specification {spec_id} not found")
                    raise typer.Exit(1)

                # Get tasks for this specification
                tasks = await manager.backend.get_tasks_for_spec(spec_id)
                
                # Find the specific task
                target_task = None
                for task in tasks:
                    if task.step_index == step_index:
                        target_task = task
                        break
                
                if not target_task:
                    print(f"❌ Task at step {step_index} not found for specification {spec_id}")
                    raise typer.Exit(1)

                # Check if task can be rejected
                if target_task.status not in [TaskStatus.COMPLETED, TaskStatus.APPROVED]:
                    print(f"❌ Task {step_id} cannot be rejected")
                    print(f"   Current status: {target_task.status.value}")
                    print(f"   Only completed or approved tasks can be rejected")
                    raise typer.Exit(1)

                # Update task to rejected and reset to pending for rework
                target_task.status = TaskStatus.REJECTED
                target_task.rejected_at = datetime.now()
                if target_task.completion_notes:
                    target_task.completion_notes += f"\n\nRejected by {rejected_by}: {reason}"
                else:
                    target_task.completion_notes = f"Rejected by {rejected_by}: {reason}"

                await manager.backend.update_task(target_task)

                print(f"❌ Task {step_id} rejected by {rejected_by}")
                print(f"📋 Task: {target_task.task}")
                print(f"📝 Reason: {reason}")
                print(f"⏰ Rejected at: {target_task.rejected_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"🔄 Task requires rework - reset to rejected status")

        except typer.BadParameter:
            raise
        except typer.Exit:
            raise
        except Exception as e:
            print(f"❌ Error rejecting task: {e}")
            raise typer.Exit(1)

    asyncio.run(reject_task_async())


@app.command("task-block")
def block_task(
    step_id: str = Argument(..., help="Step ID in format 'spec_id:step_index'"),
    blocked_by: str = Option("user", "--by", help="Who is blocking the task"),
    blockers: list[str] = Option(
        ..., "--blocker", help="Blocking issues (can specify multiple)"
    ),
    notes: str | None = Option(
        None, "--notes", help="Additional notes about the block"
    ),
    specs_dir: str = Option("specs", "--specs-dir", help="Generated specs directory"),
):
    """Block a task due to external dependencies or issues."""
    
    async def block_task_async():
        try:
            # Parse spec_id and step_index from step_id
            if ":" not in step_id:
                raise typer.BadParameter("Step ID must be in format 'spec_id:step_index'")

            spec_id, step_index_str = step_id.split(":", 1)
            try:
                step_index = int(step_index_str)
            except ValueError:
                raise typer.BadParameter("Step index must be a number")

            # Connect to database
            db_path = Path(specs_dir) / "specifications.db"
            backend = SQLiteBackend(str(db_path))
            
            async with AsyncSpecManager(backend) as manager:
                # Get tasks for this specification
                tasks = await manager.backend.get_tasks_for_spec(spec_id)
                
                # Find the specific task
                target_task = None
                for task in tasks:
                    if task.step_index == step_index:
                        target_task = task
                        break
                
                if not target_task:
                    print(f"❌ Task at step {step_index} not found for specification {spec_id}")
                    raise typer.Exit(1)

                # Update task to blocked
                target_task.status = TaskStatus.BLOCKED
                target_task.blocked_at = datetime.now()
                target_task.blockers = blockers
                if notes:
                    if target_task.completion_notes:
                        target_task.completion_notes += f"\n\nBlocked by {blocked_by}: {notes}"
                    else:
                        target_task.completion_notes = f"Blocked by {blocked_by}: {notes}"

                await manager.backend.update_task(target_task)

                print(f"🚫 Task {step_id} blocked by {blocked_by}")
                print(f"📋 Task: {target_task.task}")
                print(f"🔒 Blockers: {', '.join(blockers)}")
                if notes:
                    print(f"📝 Notes: {notes}")
                print(f"⏰ Blocked at: {target_task.blocked_at.strftime('%Y-%m-%d %H:%M:%S')}")

        except typer.BadParameter:
            raise
        except typer.Exit:
            raise
        except Exception as e:
            print(f"❌ Error blocking task: {e}")
            raise typer.Exit(1)

    asyncio.run(block_task_async())


@app.command("task-unblock")
def unblock_task(
    step_id: str = Argument(..., help="Step ID in format 'spec_id:step_index'"),
    unblocked_by: str = Option("user", "--by", help="Who is unblocking the task"),
    resolution: str = Option(
        ..., "--resolution", help="How the blockers were resolved"
    ),
    specs_dir: str = Option("specs", "--specs-dir", help="Generated specs directory"),
):
    """Unblock a task and return it to pending status."""
    
    async def unblock_task_async():
        try:
            if ":" not in step_id:
                raise typer.BadParameter("Step ID must be in format 'spec_id:step_index'")

            spec_id, step_index_str = step_id.split(":", 1)
            step_index = int(step_index_str)

            db_path = Path(specs_dir) / "specifications.db"
            backend = SQLiteBackend(str(db_path))
            
            async with AsyncSpecManager(backend) as manager:
                tasks = await manager.backend.get_tasks_for_spec(spec_id)
                target_task = next((t for t in tasks if t.step_index == step_index), None)
                
                if not target_task:
                    print(f"❌ Task at step {step_index} not found")
                    raise typer.Exit(1)

                if target_task.status != TaskStatus.BLOCKED:
                    print(f"❌ Task {step_id} is not blocked (status: {target_task.status.value})")
                    raise typer.Exit(1)

                target_task.status = TaskStatus.PENDING
                target_task.unblocked_at = datetime.now()
                target_task.blockers = []
                if target_task.completion_notes:
                    target_task.completion_notes += f"\n\nUnblocked by {unblocked_by}: {resolution}"
                else:
                    target_task.completion_notes = f"Unblocked by {unblocked_by}: {resolution}"

                await manager.backend.update_task(target_task)

                print(f"✅ Task {step_id} unblocked by {unblocked_by}")
                print(f"🔓 Resolution: {resolution}")
                print(f"⏰ Unblocked at: {target_task.unblocked_at.strftime('%Y-%m-%d %H:%M:%S')}")

        except (typer.BadParameter, typer.Exit):
            raise
        except Exception as e:
            print(f"❌ Error unblocking task: {e}")
            raise typer.Exit(1)

    asyncio.run(unblock_task_async())


@app.command("task-override")
def override_strict_mode(
    step_id: str = Argument(..., help="Step ID in format 'spec_id:step_index'"),
    override_by: str = Option("user", "--by", help="Who is overriding strict mode"),
    reason: str = Option(..., "--reason", help="Reason for override"),
    specs_dir: str = Option("specs", "--specs-dir", help="Generated specs directory"),
):
    """Override strict mode to start a task out of sequence."""
    
    async def override_task_async():
        try:
            if ":" not in step_id:
                raise typer.BadParameter("Step ID must be in format 'spec_id:step_index'")

            spec_id, step_index_str = step_id.split(":", 1)
            step_index = int(step_index_str)

            db_path = Path(specs_dir) / "specifications.db"
            backend = SQLiteBackend(str(db_path))
            
            async with AsyncSpecManager(backend) as manager:
                tasks = await manager.backend.get_tasks_for_spec(spec_id)
                target_task = next((t for t in tasks if t.step_index == step_index), None)
                
                if not target_task:
                    print(f"❌ Task at step {step_index} not found")
                    raise typer.Exit(1)

                if target_task.status != TaskStatus.PENDING:
                    print(f"❌ Task {step_id} is not pending (status: {target_task.status.value})")
                    raise typer.Exit(1)

                # Start the task with override
                target_task.status = TaskStatus.IN_PROGRESS
                target_task.started_at = datetime.now()
                if target_task.completion_notes:
                    target_task.completion_notes += f"\n\nStrict mode override by {override_by}: {reason}"
                else:
                    target_task.completion_notes = f"Strict mode override by {override_by}: {reason}"

                await manager.backend.update_task(target_task)

                print(f"⚠️  Strict mode overridden for task {step_id}")
                print(f"👤 Override by: {override_by}")
                print(f"📝 Reason: {reason}")
                print("🚀 Task has been started with override")
                print(f"⏰ Started at: {target_task.started_at.strftime('%Y-%m-%d %H:%M:%S')}")

        except (typer.BadParameter, typer.Exit):
            raise
        except Exception as e:
            print(f"❌ Error overriding strict mode: {e}")
            raise typer.Exit(1)

    asyncio.run(override_task_async())


@app.command("task-status")
def show_task_status(
    step_id: str = Argument(..., help="Step ID in format 'spec_id:step_index'"),
    specs_dir: str = Option("specs", "--specs-dir", help="Generated specs directory"),
):
    """Show detailed status information for a task."""
    
    async def show_task_status_async():
        try:
            if ":" not in step_id:
                raise typer.BadParameter("Step ID must be in format 'spec_id:step_index'")

            spec_id, step_index_str = step_id.split(":", 1)
            step_index = int(step_index_str)

            db_path = Path(specs_dir) / "specifications.db"
            backend = SQLiteBackend(str(db_path))
            
            async with AsyncSpecManager(backend) as manager:
                # Get specification and tasks
                spec = await manager.get_specification(spec_id)
                if not spec:
                    print(f"❌ Specification {spec_id} not found")
                    raise typer.Exit(1)

                tasks = await manager.backend.get_tasks_for_spec(spec_id)
                target_task = next((t for t in tasks if t.step_index == step_index), None)
                
                if not target_task:
                    print(f"❌ Task at step {step_index} not found")
                    raise typer.Exit(1)

                # Get approvals for this task
                approvals = await manager.backend.get_approvals_for_task(target_task.id)

                print(f"📋 Task Status: {step_id}")
                print(f"   Task: {target_task.task}")
                print(f"   Status: {target_task.status.value}")
                print(f"   Estimated Effort: {target_task.estimated_effort}")
                print(f"   Files: {', '.join(target_task.files)}")

                print("\n🚦 Actions Available:")
                can_start = target_task.status in [TaskStatus.PENDING, TaskStatus.BLOCKED]
                can_complete = target_task.status == TaskStatus.IN_PROGRESS
                can_approve = target_task.status == TaskStatus.COMPLETED
                print(f"   Can start: {'✅' if can_start else '❌'}")
                print(f"   Can complete: {'✅' if can_complete else '❌'}")
                print(f"   Can approve: {'✅' if can_approve else '❌'}")

                if target_task.started_at:
                    print("\n⏱️  Timing:")
                    print(f"   Started: {target_task.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    if target_task.completed_at:
                        print(f"   Completed: {target_task.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
                        duration = target_task.completed_at - target_task.started_at
                        hours = duration.total_seconds() / 3600
                        print(f"   Duration: {hours:.1f} hours")
                    if target_task.time_spent_minutes:
                        print(f"   Time Spent: {target_task.time_spent_minutes} minutes")

                if target_task.completion_notes:
                    print(f"\n📝 Notes: {target_task.completion_notes}")

                if target_task.blockers:
                    print("\n🚫 Blockers:")
                    for blocker in target_task.blockers:
                        print(f"   • {blocker}")

                if approvals:
                    print("\n✅ Approvals:")
                    for approval in approvals:
                        print(f"   • {approval.level.value} by {approval.approved_by} at {approval.approved_at.strftime('%Y-%m-%d %H:%M:%S')}")
                        if approval.comments:
                            print(f"     💬 {approval.comments}")
                        if approval.override_reason:
                            print(f"     ⚠️  Override: {approval.override_reason}")

        except (typer.BadParameter, typer.Exit):
            raise
        except Exception as e:
            print(f"❌ Error getting task status: {e}")
            raise typer.Exit(1)

    asyncio.run(show_task_status_async())


@app.command("workflow-status")
def show_workflow_status(
    spec_id: str = Argument(..., help="Specification ID"),
    specs_dir: str = Option("specs", "--specs-dir", help="Generated specs directory"),
    strict_mode: bool = Option(
        True, "--strict/--no-strict", help="Show status with strict mode context"
    ),
):
    """Show comprehensive workflow status for a specification."""
    import asyncio
    from .async_db import AsyncSpecManager, SQLiteBackend
    
    async def get_workflow_status_async():
        db_path = Path(specs_dir) / "specifications.db"
        backend = SQLiteBackend(str(db_path))
        
        async with AsyncSpecManager(backend) as manager:
            # Get specification
            spec = await manager.get_specification(spec_id)
            if not spec:
                raise ValueError(f"Specification {spec_id} not found")
            
            # Get tasks
            tasks = await manager.backend.get_tasks_for_spec(spec_id)
            
            # Calculate status
            total_tasks = len(tasks)
            completed_tasks = sum(1 for task in tasks if task.status in [TaskStatus.COMPLETED, TaskStatus.APPROVED])
            completion_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            
            # Count tasks by status
            status_counts = {}
            for task in tasks:
                status = task.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Find next available task
            next_available_task = None
            for task in tasks:
                if task.status.value == "pending":
                    next_available_task = f"{task.id}: {task.task}"
                    break
            
            return {
                "spec_title": spec.title,
                "workflow_status": spec.workflow_status.value,
                "is_completed": spec.is_completed,
                "completion_percentage": completion_percentage,
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "pending_tasks": total_tasks - completed_tasks,
                "strict_mode": strict_mode,
                "status_counts": status_counts,
                "next_available_task": next_available_task,
                "required_approval_levels": [],  # Empty for now
                "tasks": [
                    {
                        "id": task.id,
                        "step_id": task.id,  # Use task.id as step_id
                        "task": task.task,
                        "status": task.status.value,
                        "is_completed": task.is_completed,
                        "estimated_effort": task.estimated_effort,
                        "can_start": task.status.value == "pending",  # Simple logic for now
                        "required_approval_levels": [],  # Empty for now
                    }
                    for task in tasks
                ],
            }
    
    try:
        status = asyncio.run(get_workflow_status_async())

        print(f"📊 Workflow Status: {spec_id}")
        print(f"   Title: {status['spec_title']}")
        print(f"   Total Tasks: {status['total_tasks']}")
        print(f"   Completion: {status['completion_percentage']}%")
        print(
            f"   Strict Mode: {'✅ Enabled' if status['strict_mode'] else '❌ Disabled'}"
        )

        print("\n📈 Task Breakdown:")
        for status_name, count in status["status_counts"].items():
            if count > 0:
                emoji = {
                    "pending": "⏳",
                    "in_progress": "🚀",
                    "completed": "✅",
                    "approved": "🎉",
                    "rejected": "❌",
                    "blocked": "🚫",
                }.get(status_name, "📋")
                print(f"   {emoji} {status_name.replace('_', ' ').title()}: {count}")

        if status["next_available_task"]:
            print(f"\n🎯 Next Available Task: {status['next_available_task']}")

        print("\n📋 All Tasks:")
        for task in status["tasks"]:
            status_emoji = {
                "pending": "⏳",
                "in_progress": "🚀",
                "completed": "✅",
                "approved": "🎉",
                "rejected": "❌",
                "blocked": "🚫",
            }.get(task["status"], "📋")

            availability = "🟢" if task["can_start"] else "🔴"
            print(f"   {status_emoji} {availability} {task['step_id']}: {task['task']}")

            if task.get("time_spent_minutes"):
                print(f"     ⏱️  {task['time_spent_minutes']} minutes")
            if task.get("blockers"):
                print(f"     🚫 Blocked by: {', '.join(task['blockers'])}")

        print(
            f"\n📝 Required Approvals: {', '.join(status['required_approval_levels'])}"
        )

    except Exception as e:
        print(f"❌ Error getting workflow status: {e}")
        raise typer.Exit(1)


@app.command("migrate-bulk")
def migrate_bulk(
    specs_dir: str = Option("specs", "--specs-dir", help="Specifications directory"),
    templates_dir: str = Option(
        "templates", "--templates-dir", help="Templates directory"
    ),
    dry_run: bool = Option(False, "--dry-run", help="Validate without migrating"),
    verbose: bool = Option(False, "--verbose", help="Show detailed progress"),
):
    """Migrate all specifications to database."""
    try:
        specs_path = Path(specs_dir)
        templates_path = Path(templates_dir)

        generator = SpecGenerator(templates_path, specs_path)

        print("🔄 Starting bulk migration of specifications...")

        def progress_callback(msg: str):
            if verbose or "Discovered" in msg or "completed" in msg:
                print(f"   {msg}")

        # Run async migration
        async def run_migration():
            return await generator.migrate_specifications(
                full_migration=True,
                dry_run=dry_run,
                progress_callback=progress_callback,
            )

        results = asyncio.run(run_migration())

        # Display results
        action = "Validated" if dry_run else "Migrated"
        print(f"\n📊 {action} Specifications:")
        print(f"   Total files: {results['total_files']}")
        print(f"   Valid files: {results['valid_files']}")
        print(f"   {action.lower()} files: {results['migrated_files']}")
        print(f"   Errors: {len(results['errors'])}")
        print(f"   Warnings: {len(results['warnings'])}")

        success_rate = results["migrated_files"] / max(results["total_files"], 1) * 100
        print(f"   Success rate: {success_rate:.1f}%")

        if results["errors"]:
            print(f"\n❌ Errors ({len(results['errors'])}):")
            for error in results["errors"][:5]:  # Show first 5
                file_name = Path(error["file"]).name
                print(f"   {file_name}: {error['error'][:80]}...")
            if len(results["errors"]) > 5:
                print(f"   ... and {len(results['errors']) - 5} more errors")

        if results["warnings"] and verbose:
            print(f"\n⚠️  Warnings ({len(results['warnings'])}):")
            for warning in results["warnings"][:3]:  # Show first 3
                file_name = Path(warning["file"]).name
                print(f"   {file_name}: {warning['warning'][:80]}...")

        if results["errors"]:
            print("\n💡 Use --verbose for detailed output")
            if not dry_run:
                print("💡 Run with --dry-run first to validate before migrating")

        if results["migrated_files"] == results["total_files"]:
            print(f"\n✅ All specifications {action.lower()} successfully!")
        elif results["migrated_files"] > 0:
            print(
                f"\n⚠️  Partial success: {results['migrated_files']}/{results['total_files']} files {action.lower()}"
            )
        else:
            print(f"\n❌ No files were {action.lower()} successfully")
            raise typer.Exit(1)

    except Exception as e:
        print(f"❌ Error during bulk migration: {e}")
        raise typer.Exit(1)


@app.command("migrate-incremental")
def migrate_incremental(
    specs_dir: str = Option("specs", "--specs-dir", help="Specifications directory"),
    templates_dir: str = Option(
        "templates", "--templates-dir", help="Templates directory"
    ),
    dry_run: bool = Option(False, "--dry-run", help="Validate without migrating"),
    verbose: bool = Option(False, "--verbose", help="Show detailed progress"),
):
    """Migrate only new or changed specifications to database."""
    try:
        specs_path = Path(specs_dir)
        templates_path = Path(templates_dir)

        generator = SpecGenerator(templates_path, specs_path)

        print("🔄 Starting incremental migration of specifications...")

        def progress_callback(msg: str):
            if verbose or "Discovered" in msg or "completed" in msg:
                print(f"   {msg}")

        # Run async migration
        async def run_migration():
            return await generator.migrate_specifications(
                full_migration=False,  # Incremental mode
                dry_run=dry_run,
                progress_callback=progress_callback,
            )

        results = asyncio.run(run_migration())

        # Display results
        action = "Validated" if dry_run else "Migrated"
        print(f"\n📊 {action} Specifications (Incremental):")
        print(f"   Total files checked: {results['total_files']}")
        print(f"   Valid files: {results['valid_files']}")
        print(f"   {action.lower()} files: {results['migrated_files']}")
        print(f"   Errors: {len(results['errors'])}")
        print(f"   Warnings: {len(results['warnings'])}")

        if results["total_files"] == 0:
            print("   🎉 No changes detected - all files up to date!")
        else:
            success_rate = (
                results["migrated_files"] / max(results["total_files"], 1) * 100
            )
            print(f"   Success rate: {success_rate:.1f}%")

        if results["errors"] and verbose:
            print("\n❌ Errors:")
            for error in results["errors"]:
                file_name = Path(error["file"]).name
                print(f"   {file_name}: {error['error'][:100]}...")

        if results["migrated_files"] > 0:
            print("\n✅ Incremental migration completed successfully!")
        elif results["total_files"] == 0:
            print("\n✅ No migration needed - all files up to date!")
        else:
            print(f"\n❌ No files were {action.lower()} successfully")
            raise typer.Exit(1)

    except Exception as e:
        print(f"❌ Error during incremental migration: {e}")
        raise typer.Exit(1)


@app.command("migration-status")
def migration_status(
    specs_dir: str = Option("specs", "--specs-dir", help="Specifications directory"),
):
    """Show current migration status."""
    try:
        specs_path = Path(specs_dir)

        # Check for migration state file
        state_file = specs_path / ".migration_state.json"
        db_file = specs_path / "specifications.db"

        print("📊 Migration Status:")

        if not state_file.exists():
            print("   ❌ No migration state found")
            print(
                "   💡 Run 'migrate-bulk' or 'migrate-incremental' to start migration"
            )
            return

        # Load migration state
        try:
            with open(state_file, encoding="utf-8") as f:
                state = json.load(f)

            print(f"   📁 Tracked files: {len(state)}")

            # Get latest migration time
            latest_time = None
            for file_info in state.values():
                modified = file_info.get("modified", 0)
                if latest_time is None or modified > latest_time:
                    latest_time = modified

            if latest_time:
                import datetime

                latest_dt = datetime.datetime.fromtimestamp(latest_time)
                print(
                    f"   🕐 Last migration check: {latest_dt.strftime('%Y-%m-%d %H:%M:%S')}"
                )

        except (json.JSONDecodeError, KeyError) as e:
            print(f"   ❌ Error reading migration state: {e}")

        # Check database file
        if db_file.exists():
            print(f"   💾 Database file: {db_file}")
            print(f"   📊 Database size: {db_file.stat().st_size / 1024:.1f} KB")
        else:
            print("   ❌ No database file found")
            print("   💡 Use 'migrate-bulk' to create database")

        # Count YAML files
        yaml_files = list(specs_path.glob("*.yaml"))
        spec_count = 0
        for file_path in yaml_files:
            if file_path.name not in ["yaml-to-db-mapping.yaml", "migration-plan.yaml"]:
                spec_count += 1

        print(f"   📄 YAML specifications: {spec_count}")

        # Suggest actions
        if not db_file.exists():
            print("\n💡 Suggestions:")
            print("   • Run 'agentic-spec migrate-bulk --dry-run' to validate")
            print("   • Run 'agentic-spec migrate-bulk' to create database")
        else:
            print("\n💡 Suggestions:")
            print("   • Run 'agentic-spec migrate-incremental' to sync changes")
            print("   • Run 'agentic-spec migration-report' for detailed analysis")

    except Exception as e:
        print(f"❌ Error checking migration status: {e}")
        raise typer.Exit(1)


@app.command("migration-report")
def migration_report(
    specs_dir: str = Option("specs", "--specs-dir", help="Specifications directory"),
    output_format: str = Option(
        "table", "--format", help="Output format: table, yaml, json"
    ),
    save_file: str = Option(None, "--save", help="Save report to file"),
):
    """Generate detailed migration report."""
    try:
        specs_path = Path(specs_dir)

        # Basic file analysis
        yaml_files = list(specs_path.glob("*.yaml"))
        spec_files = []
        doc_files = []

        for file_path in yaml_files:
            if file_path.name in ["yaml-to-db-mapping.yaml", "migration-plan.yaml"]:
                doc_files.append(file_path)
            else:
                spec_files.append(file_path)

        # Load migration state if exists
        state_file = specs_path / ".migration_state.json"
        migration_state = {}
        if state_file.exists():
            try:
                with open(state_file, encoding="utf-8") as f:
                    migration_state = json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        # Generate report data
        from datetime import datetime

        report = {
            "generated_at": datetime.now().isoformat(),
            "specs_directory": str(specs_path),
            "summary": {
                "total_yaml_files": len(yaml_files),
                "specification_files": len(spec_files),
                "documentation_files": len(doc_files),
                "tracked_files": len(migration_state),
                "database_exists": (specs_path / "specifications.db").exists(),
            },
            "files": [],
        }

        # Analyze each spec file
        for file_path in spec_files:
            file_info = {
                "name": file_path.name,
                "size": file_path.stat().st_size,
                "modified": file_path.stat().st_mtime,
                "tracked": str(file_path) in migration_state,
            }

            # Try to get spec ID and title
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if isinstance(data, dict) and "metadata" in data:
                        file_info["spec_id"] = data["metadata"].get("id", "unknown")
                        file_info["title"] = data["metadata"].get("title", "unknown")
                        file_info["status"] = data["metadata"].get("status", "unknown")
            except:
                file_info["spec_id"] = "unknown"
                file_info["title"] = "parse_error"
                file_info["status"] = "error"

            report["files"].append(file_info)

        # Output report
        if output_format.lower() == "json":
            report_str = json.dumps(report, indent=2, default=str)
        elif output_format.lower() == "yaml":
            report_str = yaml.dump(report, default_flow_style=False, sort_keys=False)
        else:  # table format
            report_str = _format_migration_report_table(report)

        if save_file:
            save_path = Path(save_file)
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(report_str)
            print(f"📄 Report saved to: {save_path}")
        else:
            print(report_str)

    except Exception as e:
        print(f"❌ Error generating migration report: {e}")
        raise typer.Exit(1)


def _format_migration_report_table(report: dict) -> str:
    """Format migration report as a table."""
    lines = []
    lines.append("📊 Migration Report")
    lines.append("=" * 50)

    summary = report["summary"]
    lines.append(f"📁 Specifications Directory: {report['specs_directory']}")
    lines.append(f"🕐 Generated: {report['generated_at']}")
    lines.append("")

    lines.append("📈 Summary:")
    lines.append(f"   Total YAML files: {summary['total_yaml_files']}")
    lines.append(f"   Specification files: {summary['specification_files']}")
    lines.append(f"   Documentation files: {summary['documentation_files']}")
    lines.append(f"   Tracked files: {summary['tracked_files']}")
    lines.append(f"   Database exists: {'✅' if summary['database_exists'] else '❌'}")
    lines.append("")

    lines.append("📋 Files:")
    lines.append(
        f"{'Name':<30} {'Spec ID':<12} {'Status':<12} {'Tracked':<8} {'Size':<8}"
    )
    lines.append("-" * 80)

    for file_info in report["files"]:
        name = file_info["name"][:28]
        spec_id = str(file_info["spec_id"])[:10]
        status = str(file_info["status"])[:10]
        tracked = "✅" if file_info["tracked"] else "❌"
        size = f"{file_info['size'] / 1024:.1f}KB"

        lines.append(f"{name:<30} {spec_id:<12} {status:<12} {tracked:<8} {size:<8}")

    return "\n".join(lines)


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
