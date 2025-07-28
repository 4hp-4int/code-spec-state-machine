"""Utility CLI commands for agentic specification generator.

This module contains utility commands that don't fit into other categories,
such as configuration, initialization, and prompt management.
"""

import asyncio
import dataclasses
import json
import logging
import os
from pathlib import Path

import typer
from typer import Argument, Option
import yaml

from .cli_core import initialize_generator
from .config import AgenticSpecConfig, get_config_manager
from .core import SpecGenerator
from .exceptions import ConfigurationError, SyncFoundationConfigError, TemplateError
from .prompt_editor import PromptEditor
from .template_loader import render_specification_template
from .template_validator import TemplateValidator
from .templates.base import create_base_templates

# Create the utility command group
utils_app = typer.Typer(
    name="utils",
    help="Utility and configuration commands",
    no_args_is_help=True,
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

            # Create templates from configuration
            for template_name, template_data in templates_config.get(
                "templates", {}
            ).items():
                template_file = prompt_templates_dir / f"{template_name}.md"
                with template_file.open("w", encoding="utf-8") as f:
                    f.write(template_data["content"].format(project_name=project_name))

        else:
            # Fallback to hardcoded templates if config file doesn't exist
            _create_fallback_prompt_templates(prompt_templates_dir, project_name)

    except Exception:
        # If anything goes wrong, create fallback templates
        _create_fallback_prompt_templates(prompt_templates_dir, project_name)


def _create_fallback_prompt_templates(prompt_templates_dir: Path, project_name: str):
    """Create fallback prompt templates when config file is not available."""
    templates = {
        "basic-specification.md": f"""# Basic Specification Template

Generate a comprehensive programming specification for: {{prompt}}

## Project Context
Project: {project_name}
Domain: General software development
Target: Production-ready implementation

## Requirements
Create detailed specifications including:
- Clear functional requirements
- Implementation steps with acceptance criteria
- File structure and dependencies
- Testing considerations
- Documentation needs

Focus on practical, actionable specifications that a developer can follow immediately.
""",
        "feature-addition.md": f"""# Feature Addition Template

Add a new feature to {project_name}: {{prompt}}

## Integration Focus
- Surgical feature integration with focus on clean architectural alignment
- Minimal disruption to existing functionality
- Clear integration points and dependencies
- Backward compatibility considerations

## Implementation Strategy
- Identify exactly what files need modification
- Define clear interfaces and contracts
- Plan for proper error handling
- Include rollback considerations

Generate a specification that seamlessly integrates the new feature while maintaining system integrity.
""",
        "bug-fix.md": f"""# Bug Fix Template

Fix the following issue in {project_name}: {{prompt}}

## Debugging Approach
- Root cause analysis methodology
- Reproduction steps and test cases
- Impact assessment on related components
- Verification strategy

## Solution Strategy
- Minimal, targeted fix approach
- Regression testing requirements
- Documentation updates needed
- Monitoring and validation steps

Generate a specification focused on reliable, well-tested bug resolution.
""",
    }

    for template_name, content in templates.items():
        template_file = prompt_templates_dir / template_name
        with template_file.open("w", encoding="utf-8") as f:
            f.write(content)


@utils_app.command("init")
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
        try:
            spec_templates_path.mkdir(exist_ok=True)
            prompt_templates_path.mkdir(exist_ok=True)
            specs_path.mkdir(exist_ok=True)
            logs_path = Path("logs")
            logs_path.mkdir(exist_ok=True)
        except OSError as e:
            print(f"❌ Error creating directories: {e}")
            print("💡 Check that you have write permissions in the current directory")
            raise

        print(f"  ✅ {spec_templates_dir}/")
        print(f"  ✅ {prompt_templates_dir}/")
        print(f"  ✅ {specs_dir}/")
        print("  ✅ logs/")
        print()

        # Interactive configuration
        print("⚙️  Let's configure your AI provider...")

        # Ask for AI provider - avoid typer.Choice with single option to prevent errors
        available_providers = ["openai"]
        if len(available_providers) == 1:
            provider_choice = available_providers[0]
            print(f"Using AI provider: {provider_choice}")
        else:
            provider_choice = typer.prompt(
                "Choose AI provider",
                type=typer.Choice(available_providers, case_sensitive=False),
                default="openai",
            )

        # Ask for API key (optional) - handle environment detection gracefully
        existing_key = os.environ.get("OPENAI_API_KEY", "")
        if existing_key:
            print(f"Found OPENAI_API_KEY environment variable (***{existing_key[-4:]})")
            try:
                use_env_key = typer.confirm(
                    "Use existing environment variable?", default=True
                )
                if use_env_key:
                    api_key = ""  # Will use env var
                else:
                    api_key = typer.prompt(
                        "Enter your OpenAI API key",
                        default="",
                        hide_input=True,
                    )
            except (typer.Abort, KeyboardInterrupt):
                # Handle non-interactive environments or user cancellation
                print("Using existing environment variable (non-interactive mode)")
                api_key = ""  # Will use env var
        else:
            try:
                api_key = typer.prompt(
                    "Enter your OpenAI API key (or press Enter to use OPENAI_API_KEY env var later)",
                    default="",
                    hide_input=True,
                )
            except (typer.Abort, KeyboardInterrupt):
                print(
                    "No API key provided - you can set OPENAI_API_KEY environment variable later"
                )
                api_key = ""

        # Ask for project name
        try:
            project_name = typer.prompt(
                "What's your project name?", default="my-project"
            )
        except (typer.Abort, KeyboardInterrupt):
            print("Using default project name: my-project")
            project_name = "my-project"

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

        # Write configuration file - handle file permissions gracefully
        config_file = Path("agentic_spec_config.yaml")
        try:
            if config_file.exists() and not force:
                try:
                    overwrite = typer.confirm(
                        f"Configuration file {config_file} already exists. Overwrite?"
                    )
                    if not overwrite:
                        print("❌ Setup cancelled.")
                        return
                except (typer.Abort, KeyboardInterrupt):
                    print("❌ Setup cancelled (non-interactive mode).")
                    return

            with config_file.open("w") as f:
                yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

            print(f"  ✅ {config_file}")
        except (OSError, PermissionError) as e:
            print(f"  ❌ Error creating config file: {e}")
            print("  💡 Try running from a directory where you have write permissions")
            return
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
                print(
                    "  ⚠️  Warning: Could not create foundation spec (this is optional)"
                )
        except ImportError as e:
            print(f"  ⚠️  Warning: Import error creating foundation spec: {e}")
        except Exception as e:
            print(f"  ⚠️  Warning: Could not create foundation spec: {e}")
            print("  💡 You can create it later with: agentic-spec sync-foundation")

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

    except KeyboardInterrupt:
        print("❌ Initialization cancelled by user.")
        raise typer.Exit(1) from None
    except PermissionError as e:
        logger.exception("Permission error during project initialization")
        print(f"❌ Permission error: {e}")
        print("💡 Try running from a directory where you have write permissions")
        print("💡 Or run with appropriate permissions")
        raise typer.Exit(1) from None
    except OSError as e:
        logger.exception("OS error during project initialization")
        print(f"❌ File system error: {e}")
        print("💡 Check that the directory exists and is writable")
        raise typer.Exit(1) from None
    except Exception as e:
        logger.exception("Error during project initialization")
        print(f"❌ Initialization failed: {e}")
        print("💡 Try running with --force to override existing files")
        print("💡 Ensure you have write permissions in the current directory")
        raise typer.Exit(1) from None


@utils_app.command("config")
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
            validation_passed = True

            # Validate main config
            if config_manager.config_file.exists():
                print("🔍 Validating main configuration...")
                config_data = config_manager.load_config()
                errors = config_manager.validate_config_schema(config_data.model_dump())
                if errors:
                    print("❌ Main configuration validation failed:")
                    for error in errors:
                        print(f"  • {error}")
                    validation_passed = False
                else:
                    print("✅ Main configuration is valid")
            else:
                print("⚠️  No main configuration file found")

            # Validate sync-foundation config if present
            print("\n🔍 Validating sync-foundation configuration...")
            try:
                generator = SpecGenerator(
                    spec_templates_dir=Path("templates"),
                    specs_dir=Path("specs"),
                    config=config_data if config_manager.config_file.exists() else None,
                )

                if generator.sync_foundation_config:
                    print("✅ Sync-foundation configuration loaded successfully")

                    # Run validation checks
                    pattern_warnings = (
                        generator.sync_foundation_config.validate_patterns()
                    )
                    skip_warnings = (
                        generator.sync_foundation_config.validate_skip_patterns()
                    )

                    all_warnings = pattern_warnings + skip_warnings
                    if all_warnings:
                        print("⚠️  Configuration warnings found:")
                        for warning in all_warnings:
                            print(f"  • {warning}")
                    else:
                        print("✅ No configuration warnings found")
                else:
                    print("ℹ️  No sync-foundation config found (using defaults)")

            except SyncFoundationConfigError as e:
                print(f"❌ Sync-foundation configuration error: {e.message}")
                if e.details:
                    print(f"   Details: {e.details}")
                validation_passed = False
            except Exception as e:
                print(f"❌ Unexpected error validating sync-foundation config: {e}")
                validation_passed = False

            # Summary
            print("\n" + "=" * 50)
            if validation_passed:
                print("✅ All configurations are valid!")
            else:
                print("❌ Configuration validation failed!")
                print("💡 Fix the errors above before proceeding")

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


@utils_app.command("validate")
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


@utils_app.command("render")
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
            spec_dict = dataclasses.asdict(target_spec)

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


@utils_app.command("prompt")
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
