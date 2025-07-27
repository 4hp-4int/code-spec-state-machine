"""Command-line interface for agentic specification generator."""

import asyncio
import logging
import logging.handlers
from pathlib import Path
import sys

import typer
from typer import Argument, Option

from .config import get_config_manager, parse_cli_overrides
from .core import SpecGenerator
from .exceptions import (
    AgenticSpecError,
    AIServiceError,
    ConfigurationError,
    FileSystemError,
    SpecificationError,
    TemplateError,
    ValidationError,
)
from .models import ContextParameters
from .template_loader import (
    TemplateLoader,
    list_templates,
    render_specification_template,
)
from .template_validator import TemplateValidator
from .templates.base import create_base_templates


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
        logger.debug(f"Using command line prompt: {args_prompt[:50]}...")
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
            raise ValidationError("Input cancelled by user", str(e))
        except Exception as e:
            logger.error(f"Error reading piped input: {e}")
            raise FileSystemError("Failed to read piped input", str(e))

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
        raise ValidationError("No prompt provided")
    except KeyboardInterrupt:
        logger.info("Interactive input cancelled by user")
        print("\nCancelled.")
        sys.exit(1)


# Create Typer app
app = typer.Typer(
    name="agentic-spec",
    help="AI-powered programming specification generator with inheritance and review workflows",
    add_completion=False,
    no_args_is_help=True,
)


async def initialize_generator(
    templates_dir: Path,
    specs_dir: Path,
    config_file: Path | None = None,
    cli_overrides: list[str] = [],
) -> SpecGenerator:
    """Initialize the SpecGenerator with configuration."""
    logger = logging.getLogger("agentic_spec")

    try:
        # Load configuration
        config_manager = get_config_manager(config_file)
        config = config_manager.load_config()
        logger.debug("Configuration loaded successfully")

        # Apply CLI overrides
        cli_override_dict = parse_cli_overrides(cli_overrides)
        config = config_manager.merge_cli_overrides(config, cli_override_dict)
        logger.debug(f"Applied {len(cli_override_dict)} CLI overrides")

    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        raise ConfigurationError("Failed to load configuration", str(e))

    try:
        # Use config to set paths if not overridden by CLI
        final_templates_dir = templates_dir or Path(config.directories.templates_dir)
        final_specs_dir = specs_dir or Path(config.directories.specs_dir)

        # Ensure directories exist
        final_templates_dir.mkdir(parents=True, exist_ok=True)
        final_specs_dir.mkdir(parents=True, exist_ok=True)

        generator = SpecGenerator(final_templates_dir, final_specs_dir, config)
        logger.debug("SpecGenerator initialized successfully")
        return generator

    except Exception as e:
        logger.error(f"Error initializing SpecGenerator: {e}")
        raise FileSystemError("Failed to initialize application", str(e))


@app.command("generate")
def generate_spec(
    prompt: str | None = Argument(
        None,
        help="Programming task prompt (optional - can use stdin or interactive input)",
    ),
    inherits: list[str] = Option(
        [], "--inherits", help="Base templates to inherit from"
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
    templates_dir: Path = Option(
        Path("templates"), "--templates-dir", help="Templates directory"
    ),
    specs_dir: Path = Option(
        Path("specs"), "--specs-dir", help="Generated specs directory"
    ),
    config: Path | None = Option(None, "--config", help="Path to configuration file"),
    set_options: list[str] = Option(
        [],
        "--set",
        help="Override configuration values (e.g., --set prompt_settings.temperature=0.2)",
    ),
):
    """Generate a new programming specification from a prompt.

    The prompt can be provided as an argument, piped via stdin, or entered interactively.
    Use --inherits to build upon existing templates, and customize the generation context
    with role, audience, tone, and complexity options.
    """

    async def _generate():
        logger = logging.getLogger("agentic_spec")

        try:
            generator = await initialize_generator(
                templates_dir, specs_dir, config, set_options
            )

            # Get prompt input
            final_prompt = get_prompt_input(prompt)
            if not final_prompt:
                logger.warning("No prompt provided for generation")
                raise ValidationError("No prompt provided")

            logger.info(
                f"Starting specification generation for prompt: {final_prompt[:100]}..."
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

            print(
                f"🔄 Generating specification for: {final_prompt[:50]}{'...' if len(final_prompt) > 50 else ''}"
            )

            # AI generation with fallback handling
            try:
                spec = await generator.generate_spec(
                    final_prompt, inherits, project, context_params
                )
                logger.info("Specification generated successfully")
            except Exception as e:
                logger.error(f"AI generation failed: {e}")
                raise AIServiceError(
                    "Failed to generate specification using AI", str(e)
                )

            # Save specification with error handling
            try:
                spec_path = generator.save_spec(spec)
                logger.info(f"Specification saved to {spec_path}")
            except Exception as e:
                logger.error(f"Error saving specification: {e}")
                raise FileSystemError("Failed to save specification", str(e))

            print(f"✅ Specification generated: {spec_path}")
            print(f"📋 Spec ID: {spec.metadata.id}")

            # Auto-review if enabled in config
            if generator.config.workflow.auto_review:
                try:
                    print("🔍 Reviewing specification...")
                    review_notes = await generator.review_spec(spec)

                    if review_notes:
                        spec.review_notes = review_notes
                        generator.save_spec(spec)  # Save with review notes
                        logger.info("Review notes added to specification")

                        print("📝 Review feedback:")
                        for note in review_notes:
                            print(f"  • {note}")
                except Exception as e:
                    logger.warning(f"Auto-review failed: {e}")
                    print("⚠️  Auto-review failed, continuing without review")

            # Collect feedback if requested or enabled in config
            if feedback or generator.config.workflow.collect_feedback:
                try:
                    feedback_data = generator.prompt_engineer.collect_feedback(
                        output_content=str(spec_path), interactive=True
                    )
                    if feedback_data:
                        spec.feedback_history.append(feedback_data)
                        generator.save_spec(spec)  # Save with feedback
                        print("💾 Feedback saved with specification")
                        logger.info("User feedback collected and saved")
                except Exception as e:
                    logger.warning(f"Feedback collection failed: {e}")
                    print("⚠️  Feedback collection failed, continuing without feedback")

            print(
                "\n💡 Next step: Review and approve specification before implementation"
            )

        except ValidationError:
            # Re-raise validation errors as they have user-friendly messages
            raise
        except AgenticSpecError:
            # Re-raise our custom errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error during generation: {e}")
            raise SpecificationError("Failed to generate specification", str(e))

    asyncio.run(_generate())


@app.command("review")
def review_specs(
    templates_dir: Path = Option(
        Path("templates"), "--templates-dir", help="Templates directory"
    ),
    specs_dir: Path = Option(
        Path("specs"), "--specs-dir", help="Generated specs directory"
    ),
):
    """List available specifications for review.

    Shows all generated specifications in the specs directory with their basic information.
    """
    logger = logging.getLogger("agentic_spec")

    try:
        logger.info(f"Listing specifications in {specs_dir}")
        # List available specs for review
        if not specs_dir.exists():
            logger.warning(f"Specs directory does not exist: {specs_dir}")
            raise FileSystemError("Specifications directory not found")

        specs = list(specs_dir.glob("*.yaml"))
        if not specs:
            logger.info("No specifications found for review")
            print("❌ No specifications found")
            return

        print("📋 Available specifications:")
        for i, spec_path in enumerate(specs):
            print(f"  {i}: {spec_path.name}")

        logger.info(f"Listed {len(specs)} specifications")

    except FileSystemError:
        raise
    except Exception as e:
        logger.error(f"Error listing specifications: {e}")
        raise FileSystemError("Failed to list specifications", str(e))


@app.command("templates")
def create_templates(
    project: str = Option("project", "--project", help="Project name for context"),
    templates_dir: Path = Option(
        Path("templates"), "--templates-dir", help="Templates directory"
    ),
):
    """Create base templates for common project patterns.

    Generates template files for web APIs, CLI applications, data analysis,
    machine learning projects, and coding standards.
    """
    logger = logging.getLogger("agentic_spec")

    try:
        logger.info(f"Creating base templates in {templates_dir}")
        create_base_templates(templates_dir, project)
        print(f"✅ Base templates created in {templates_dir}")
        logger.info("Base templates created successfully")
    except Exception as e:
        logger.error(f"Error creating base templates: {e}")
        raise TemplateError("Failed to create base templates", str(e))


@app.command("graph")
def show_graph(
    specs_dir: Path = Option(
        Path("specs"), "--specs-dir", help="Generated specs directory"
    ),
):
    """Display specification dependency graph and statistics.

    Shows a visual representation of how specifications relate to each other
    and provides statistics about the specification tree.
    """
    from .graph_visualization import get_spec_stats, print_spec_graph

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
        help="Step ID in format 'spec_id:step_index' to expand into a detailed sub-specification",
    ),
    templates_dir: Path = Option(
        Path("templates"), "--templates-dir", help="Templates directory"
    ),
    specs_dir: Path = Option(
        Path("specs"), "--specs-dir", help="Generated specs directory"
    ),
    config: Path | None = Option(None, "--config", help="Path to configuration file"),
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

                print(f"✅ Sub-specification generated: {sub_spec_path}")
                print(f"📋 Sub-spec ID: {sub_spec.metadata.id}")
                print(f"🔗 Linked to parent step: {step_id}")

                # Auto-review sub-spec
                print("🔍 Reviewing sub-specification...")
                review_notes = await generator.review_spec(sub_spec)

                if review_notes:
                    sub_spec.review_notes = review_notes
                    generator.save_spec(sub_spec)

                    print("📝 Review feedback:")
                    for note in review_notes:
                        print(f"  • {note}")
            else:
                print("❌ Failed to generate sub-specification")

        except Exception as e:
            logger.error(f"Error expanding step: {e}")
            raise SpecificationError("Failed to expand step", str(e))

    asyncio.run(_expand())


@app.command("publish")
def publish_spec(
    spec_id: str = Argument(..., help="Specification ID to mark as implemented"),
    specs_dir: Path = Option(
        Path("specs"), "--specs-dir", help="Generated specs directory"
    ),
    config: Path | None = Option(None, "--config", help="Path to configuration file"),
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
            from .graph_visualization import print_spec_graph

            print_spec_graph(specs_dir)

        except Exception as e:
            logger.error(f"Error publishing spec: {e}")
            raise SpecificationError("Failed to publish specification", str(e))

    asyncio.run(_publish())


@app.command("config")
def manage_config(
    action: str = Argument(
        ..., help="Configuration action: 'init', 'show', or 'validate'"
    ),
    config: Path | None = Option(None, "--config", help="Path to configuration file"),
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
            import json

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
        logger.error(f"Error managing config: {e}")
        raise ConfigurationError("Failed to manage configuration", str(e))


@app.command("template")
def manage_templates(
    action: str = Argument(..., help="Template action: 'list' or 'info'"),
    template_name: str | None = Option(
        None, "--template", help="Template name for info command"
    ),
    templates_dir: Path = Option(
        Path("templates"), "--templates-dir", help="Templates directory"
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
        logger.error(f"Error managing templates: {e}")
        raise TemplateError("Failed to manage templates", str(e))


@app.command("validate")
def validate_templates(
    templates_dir: Path = Option(
        Path("templates"), "--templates-dir", help="Templates directory"
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
        logger.error(f"Error validating templates: {e}")
        raise TemplateError("Failed to validate templates", str(e))


@app.command("sync-foundation")
def sync_foundation_spec(
    templates_dir: Path = Option(
        Path("templates"), "--templates-dir", help="Templates directory"
    ),
    specs_dir: Path = Option(
        Path("specs"), "--specs-dir", help="Generated specs directory"
    ),
    config: Path | None = Option(None, "--config", help="Path to configuration file"),
    set_options: list[str] = Option([], "--set", help="Override configuration values"),
    force: bool = Option(False, "--force", help="Force sync even if foundation spec is current"),
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
                print(f"📄 Updated: {templates_dir / 'agentic-spec-foundation.yaml'}")
                
                # Show what was updated
                try:
                    foundation = generator.load_template("agentic-spec-foundation")
                    print(f"🕒 Last synced: {foundation.get('_last_synced', 'Unknown')}")
                    print(f"📦 Dependencies tracked: {len(foundation.get('context', {}).get('dependencies', []))}")
                    print(f"📋 Coding standards: {len(foundation.get('coding_standards', []))}")
                except Exception:
                    pass
            else:
                print("❌ Failed to sync foundation spec")
                
        except Exception as e:
            logger.error(f"Error syncing foundation spec: {e}")
            raise SpecificationError("Failed to sync foundation specification", str(e))
    
    asyncio.run(_sync())


@app.command("check-foundation")
def check_foundation_status(
    templates_dir: Path = Option(
        Path("templates"), "--templates-dir", help="Templates directory"
    ),
    specs_dir: Path = Option(
        Path("specs"), "--specs-dir", help="Generated specs directory"
    ),
    config: Path | None = Option(None, "--config", help="Path to configuration file"),
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
                print(f"  Exists: ✅")
                print(f"  Last synced: {last_synced or 'Never'}")
                print(f"  Sync version: {sync_version}")
                
                needs_sync = generator.check_foundation_sync_needed()
                if needs_sync:
                    print("  Status: ⚠️  Needs sync")
                    print("\n💡 Run 'agentic-spec sync-foundation' to update")
                else:
                    print("  Status: ✅ Current")
                    
            except Exception:
                print("📄 Foundation Spec Status:")
                print("  Exists: ❌ Not found")
                print("  Status: ⚠️  Needs creation")
                print("\n💡 Run 'agentic-spec sync-foundation' to create")
                
        except Exception as e:
            logger.error(f"Error checking foundation status: {e}")
            raise SpecificationError("Failed to check foundation status", str(e))
    
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
    templates_dir: Path = Option(
        Path("templates"), "--templates-dir", help="Templates directory"
    ),
    specs_dir: Path = Option(
        Path("specs"), "--specs-dir", help="Generated specs directory"
    ),
    config: Path | None = Option(None, "--config", help="Path to configuration file"),
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

        except Exception as e:
            logger.error(f"Error rendering template: {e}")
            raise TemplateError("Failed to render template", str(e))

    asyncio.run(_render())


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
        logger.error(f"Application error: {e.message}")
        if e.details:
            logger.debug(f"Error details: {e.details}")
        print(f"❌ {e.message}")
        sys.exit(1)
    except Exception as e:
        logger = logging.getLogger("agentic_spec")
        logger.critical(f"Unexpected error: {e}", exc_info=True)
        print("❌ Unexpected error occurred. Check logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
