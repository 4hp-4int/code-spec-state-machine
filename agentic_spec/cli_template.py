"""Template CLI commands for agentic specification generator.

This module contains commands related to template management, browsing,
and template operations.
"""

import logging
from pathlib import Path

import typer
from typer import Argument, Option

from .exceptions import TemplateError
from .prompt_template_loader import PromptTemplateLoader
from .template_loader import TemplateLoader
from .templates.base import create_base_templates


def list_templates():
    """List available templates - placeholder implementation."""
    # This would normally scan the templates directory
    return ["base-coding-standards.yaml", "web-api.yaml", "cli-application.yaml"]


def _is_internal_template(name: str) -> bool:
    """Check if a template is internal (used by the system)."""
    internal_prefixes = ["_", "internal-", "system-"]
    return any(name.startswith(prefix) for prefix in internal_prefixes)


# Create the template command group
template_app = typer.Typer(
    name="template",
    help="Template management and browsing commands",
    no_args_is_help=True,
)


@template_app.command("templates")
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


@template_app.command("manage")
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


@template_app.command("browse")
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


@template_app.command("preview")
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
