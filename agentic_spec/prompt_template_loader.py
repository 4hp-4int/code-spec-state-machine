"""Prompt template loading and rendering system."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jinja2


@dataclass
class TemplateMetadata:
    """Metadata for a prompt template."""

    name: str
    description: str
    use_case: str
    file_path: Path


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

    def get_template_metadata(self, template_name: str) -> TemplateMetadata:
        """Extract metadata from a prompt template.

        Args:
            template_name: Name of template (without .md extension)

        Returns:
            Template metadata object

        Raises:
            FileNotFoundError: If template doesn't exist
        """
        if not template_name.endswith(".md"):
            template_name += ".md"

        template_path = self.prompt_templates_dir / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_name}")

        # Read template content to extract description
        content = template_path.read_text(encoding="utf-8")

        # Extract description from first few lines or use predefined mappings
        description, use_case = self._extract_template_info(template_path.stem, content)

        return TemplateMetadata(
            name=template_path.stem,
            description=description,
            use_case=use_case,
            file_path=template_path,
        )

    def list_template_metadata(self) -> list[TemplateMetadata]:
        """List all available prompt templates with metadata.

        Returns:
            List of template metadata objects
        """
        if not self.prompt_templates_dir.exists():
            return []

        metadata_list = []
        for file_path in self.prompt_templates_dir.glob("*.md"):
            try:
                metadata = self.get_template_metadata(file_path.stem)
                metadata_list.append(metadata)
            except Exception:
                # Skip malformed templates
                continue

        return sorted(metadata_list, key=lambda x: x.name)

    def _extract_template_info(
        self, template_name: str, content: str
    ) -> tuple[str, str]:
        """Extract description and use case from template content.

        Args:
            template_name: Name of the template
            content: Template file content

        Returns:
            Tuple of (description, use_case)
        """
        # Predefined metadata for known templates
        template_info = {
            "basic-specification": (
                "Comprehensive specification generation with balanced detail and practicality",
                "Use for general programming tasks requiring complete coverage of all aspects",
            ),
            "feature-addition": (
                "Surgical feature integration with focus on clean architectural alignment",
                "Use when adding new functionality while maintaining existing patterns and quality",
            ),
            "bug-fix": (
                "Minimal-scope bug fixes with maximum safety and regression prevention",
                "Use when fixing specific issues without introducing new problems or feature creep",
            ),
            "refactoring": (
                "Safe incremental code improvements without functional changes",
                "Use when enhancing code quality, structure, or performance while preserving behavior",
            ),
            "specification-generation": (
                "Primary template for AI-powered specification generation",
                "Internal template used by the AI system (not typically user-selected)",
            ),
            "specification-review": (
                "Template for AI-powered specification reviews and feedback",
                "Internal template used for generating review feedback",
            ),
            "step-expansion": (
                "Template for expanding implementation steps into sub-specifications",
                "Internal template used for sub-specification generation",
            ),
            "context-enhancement": (
                "Template for adding contextual information to prompts",
                "Internal template used for context-aware prompt building",
            ),
        }

        if template_name in template_info:
            return template_info[template_name]

        # Fallback: extract description from content
        lines = content.strip().split("\n")
        first_line = lines[0] if lines else ""

        # Try to extract a meaningful description from the first line
        if first_line.startswith("You are"):
            description = first_line
        else:
            description = f"Custom template: {template_name}"

        return description, "Custom template for specific use cases"
