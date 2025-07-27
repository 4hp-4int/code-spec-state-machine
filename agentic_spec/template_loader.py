"""Template loading system for agentic-spec with Jinja2 support."""

import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

logger = logging.getLogger(__name__)


class TemplateLoader:
    """Handles dynamic loading and rendering of Jinja2 templates."""

    def __init__(self, templates_dir: Path | None = None):
        """Initialize the template loader.

        Args:
            templates_dir: Directory containing templates. Defaults to agentic_spec/templates/
        """
        if templates_dir is None:
            # Default to templates directory in the package
            package_dir = Path(__file__).parent
            templates_dir = package_dir / "templates"

        self.templates_dir = Path(templates_dir)

        # Ensure templates directory exists
        if not self.templates_dir.exists():
            logger.warning("Templates directory not found: %s", self.templates_dir)
            self.templates_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        logger.info(
            "Template loader initialized with directory: %s", self.templates_dir
        )

    def list_available_templates(self) -> list[str]:
        """List all available template files.

        Returns:
            List of template filenames
        """
        try:
            templates = []
            for file_path in self.templates_dir.rglob("*.html"):
                # Convert to relative path from templates directory
                rel_path = file_path.relative_to(self.templates_dir)
                templates.append(str(rel_path))

            logger.debug("Found %d templates: %s", len(templates), templates)
            return sorted(templates)

        except (OSError, PermissionError, UnicodeDecodeError):
            logger.exception("Error listing templates")
            return []

    def load_template(self, template_name: str):
        """Load a template by name.

        Args:
            template_name: Name of the template file (e.g., 'base_template.html')

        Returns:
            Jinja2 Template object

        Raises:
            TemplateNotFound: If template doesn't exist
        """
        try:
            template = self.env.get_template(template_name)
            logger.debug("Successfully loaded template: %s", template_name)
            return template

        except TemplateNotFound as e:
            logger.exception("Template not found: %s", template_name)
            available = self.list_available_templates()
            logger.info("Available templates: %s", available)
            raise e

        except Exception as e:
            logger.exception("Error loading template: %s", template_name)
            raise e

    def render_template(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a template with the given context.

        Args:
            template_name: Name of the template file
            context: Dictionary of variables to pass to the template

        Returns:
            Rendered template as string

        Raises:
            TemplateNotFound: If template doesn't exist
        """
        try:
            template = self.load_template(template_name)
            rendered = template.render(**context)
            logger.debug("Successfully rendered template: %s", template_name)
            return rendered

        except Exception as e:
            logger.exception("Error rendering template: %s", template_name)
            raise e

    def template_exists(self, template_name: str) -> bool:
        """Check if a template exists.

        Args:
            template_name: Name of the template file

        Returns:
            True if template exists, False otherwise
        """
        try:
            self.env.get_template(template_name)
            return True
        except TemplateNotFound:
            return False
        except (TemplateSyntaxError, OSError, UnicodeDecodeError) as e:
            logger.warning("Error checking template existence %s: %s", template_name, e)
            return False

    def get_template_info(self, template_name: str) -> dict[str, Any]:
        """Get information about a template.

        Args:
            template_name: Name of the template file

        Returns:
            Dictionary with template information
        """
        template_path = self.templates_dir / template_name

        info = {
            "name": template_name,
            "exists": self.template_exists(template_name),
            "path": str(template_path),
            "absolute_path": str(template_path.absolute())
            if template_path.exists()
            else None,
        }

        if template_path.exists():
            stat = template_path.stat()
            info.update(
                {
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                }
            )

        return info


def create_default_loader() -> TemplateLoader:
    """Create a template loader with default settings.

    Returns:
        Configured TemplateLoader instance
    """
    return TemplateLoader()


# Convenience functions for common operations
def render_specification_template(
    spec_data: dict[str, Any], template_name: str = "child_template.html"
) -> str:
    """Render a specification using the default template.

    Args:
        spec_data: Specification data dictionary
        template_name: Template to use for rendering

    Returns:
        Rendered HTML string
    """
    loader = create_default_loader()
    return loader.render_template(template_name, spec_data)


def list_templates() -> list[str]:
    """Get list of available templates.

    Returns:
        List of template filenames
    """
    loader = create_default_loader()
    return loader.list_available_templates()
