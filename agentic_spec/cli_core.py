"""Core CLI commands for agentic specification generator.

This module contains commands related to specification generation, validation,
and rendering - the fundamental operations of the tool.
"""

import asyncio
import logging
from pathlib import Path
import sys

import typer
from typer import Argument, Option

from .async_db import AsyncSpecManager, SQLiteBackend
from .config import get_config_manager, parse_cli_overrides
from .core import SpecGenerator
from .exceptions import (
    AgenticSpecError,
    AIServiceError,
    ConfigurationError,
    FileSystemError,
    TemplateError,
    ValidationError,
)
from .graph_visualization import get_spec_stats, print_spec_graph
from .models import (
    ContextParameters,
)
from .prompt_template_loader import PromptTemplateLoader

# Create the core command group
core_app = typer.Typer(
    name="core",
    help="Core specification generation and validation commands",
    no_args_is_help=True,
)


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


async def initialize_generator(
    spec_templates_dir: Path,
    specs_dir: Path,
    config_file: Path | None = None,
    discovery_config_file: Path | None = None,
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
        logger.debug(
            "Directories prepared: %s, %s", final_spec_templates_dir, final_specs_dir
        )

        # Initialize generator
        generator = SpecGenerator(
            final_spec_templates_dir,
            final_specs_dir,
            config,
            discovery_config_file,
        )
        logger.debug("SpecGenerator initialized successfully")

    except Exception as e:
        logger.exception("Error initializing generator")
        msg = "Failed to initialize application"
        raise FileSystemError(msg, str(e)) from e
    else:
        return generator


@core_app.command("generate")
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


@core_app.command("review")
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


@core_app.command("graph")
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


@core_app.command("expand")
def expand_step(
    step_id: str = Argument(..., help="Step to expand in format 'spec_id:step_index'"),
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
    """Expand an implementation step into a detailed sub-specification.

    Takes a step from an existing specification and creates a new, more detailed
    specification focused on implementing that specific step.
    """

    async def _expand():
        logger = logging.getLogger("agentic_spec")

        # Initialize mutable defaults
        set_options_list = set_options if set_options is not None else []

        # Parse spec_id and step_index from step_id
        if ":" not in step_id:
            print("❌ Step ID must be in format 'spec_id:step_index'")
            raise typer.Exit(1)

        spec_id, step_index_str = step_id.split(":", 1)
        try:
            step_index = int(step_index_str)
        except ValueError:
            print("❌ Step index must be a number")
            raise typer.Exit(1)

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
                    None,
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

            logger.info("Starting step expansion for %s", step_id)

            try:
                expanded_spec = await generator.expand_step(spec_id, step_index)
                logger.info("Step expansion completed successfully")
            except Exception as e:
                logger.exception("Step expansion failed")
                msg = "Failed to expand step"
                raise AIServiceError(msg, str(e)) from e

            # Save the expanded specification
            try:
                spec_path = generator.save_spec(expanded_spec)
                logger.info("Expanded specification saved to %s", spec_path)

                # Also save to database
                db_path = Path(specs_dir) / "specifications.db"
                backend = SQLiteBackend(str(db_path))
                async with AsyncSpecManager(backend) as manager:
                    await manager.save_spec_to_db(expanded_spec)
                    logger.info("Expanded specification saved to database")

            except Exception as e:
                logger.exception("Error saving expanded specification")
                msg = "Failed to save expanded specification"
                raise FileSystemError(msg, str(e)) from e

            print(f"✅ Step expanded: {spec_path}")
            print(f"📋 New Spec ID: {expanded_spec.metadata.id}")
            print(f"🔗 Parent step: {step_id}")
            print("💾 Saved to database")

        except ValidationError as e:
            logger.exception("Validation error")
            print(f"❌ {e.message}")
            raise typer.Exit(1) from None
        except AgenticSpecError as e:
            logger.exception("Application error")
            print(f"❌ {e.message}")
            raise typer.Exit(1) from None
        except Exception:
            logger.exception("Unexpected error during expansion")
            print("❌ Failed to expand step")
            raise typer.Exit(1) from None

    asyncio.run(_expand())
