"""Prompt template loading and rendering system."""

from pathlib import Path
from typing import Any

import jinja2


class PromptTemplateLoader:
    """Loads and renders Jinja2-based prompt templates."""

    def __init__(self, prompt_templates_dir: Path | None = None):
        """Initialize the prompt template loader.

        Args:
            prompt_templates_dir: Directory containing prompt templates
        """
        self.prompt_templates_dir = prompt_templates_dir or Path("prompt-templates")

        # Initialize Jinja2 environment with safe rendering
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.prompt_templates_dir)),
            autoescape=False,  # We want raw text output
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add safety measures
        self.env.globals = {}  # No global functions

    def load_template(self, template_name: str) -> jinja2.Template:
        """Load a prompt template by name.

        Args:
            template_name: Name of template file (with or without .md extension)

        Returns:
            Jinja2 template object

        Raises:
            FileNotFoundError: If template doesn't exist
        """
        # Add .md extension if not present
        if not template_name.endswith(".md"):
            template_name += ".md"

        try:
            return self.env.get_template(template_name)
        except jinja2.TemplateNotFound as e:
            raise FileNotFoundError(
                f"Prompt template not found: {template_name}"
            ) from e

    def render_template(self, template_name: str, **kwargs: Any) -> str:
        """Render a prompt template with given variables.

        Args:
            template_name: Name of template to render
            **kwargs: Template variables

        Returns:
            Rendered prompt text
        """
        template = self.load_template(template_name)

        try:
            return template.render(**kwargs)
        except jinja2.TemplateError as e:
            raise ValueError(f"Error rendering template {template_name}: {e}") from e

    def list_templates(self) -> list[str]:
        """List all available prompt templates.

        Returns:
            List of template names (without .md extension)
        """
        if not self.prompt_templates_dir.exists():
            return []

        templates = []
        for file_path in self.prompt_templates_dir.glob("*.md"):
            templates.append(file_path.stem)

        return sorted(templates)

    def template_exists(self, template_name: str) -> bool:
        """Check if a template exists.

        Args:
            template_name: Name of template to check

        Returns:
            True if template exists
        """
        if not template_name.endswith(".md"):
            template_name += ".md"

        template_path = self.prompt_templates_dir / template_name
        return template_path.exists()
