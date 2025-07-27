"""Template validation system for agentic-spec Jinja2 templates."""

import logging
from pathlib import Path
import re
from typing import Any

from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError, meta
from jinja2.nodes import Block, Extends, Include

logger = logging.getLogger(__name__)


class TemplateValidationError(Exception):
    """Raised when template validation fails."""


class TemplateValidator:
    """Validates Jinja2 templates for structure and inheritance."""

    def __init__(self, templates_dir: Path | None = None):
        """Initialize the template validator.

        Args:
            templates_dir: Directory containing templates. Defaults to agentic_spec/templates/
        """
        if templates_dir is None:
            package_dir = Path(__file__).parent
            templates_dir = package_dir / "templates"

        self.templates_dir = Path(templates_dir)

        # Initialize Jinja2 environment for parsing
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Define required blocks for different template types
        self.required_blocks = {
            "base": ["content", "title"],
            "child": [],  # Child templates inherit requirements from parent
            "standalone": ["content"],
        }

        logger.info(
            "Template validator initialized with directory: %s", self.templates_dir
        )

    def validate_template(self, template_name: str) -> dict[str, Any]:
        """Validate a single template.

        Args:
            template_name: Name of the template file

        Returns:
            Dictionary with validation results
        """
        result = {
            "template_name": template_name,
            "valid": False,
            "errors": [],
            "warnings": [],
            "info": {},
            "blocks": [],
            "extends": None,
            "includes": [],
            "variables": [],
        }

        try:
            # Check if template file exists
            template_path = self.templates_dir / template_name
            if not template_path.exists():
                result["errors"].append(
                    f"Template file does not exist: {template_path}"
                )
                return result

            # Parse template
            source = template_path.read_text(encoding="utf-8")
            ast = self.env.parse(source, template_name)

            # Extract template metadata
            result["blocks"] = self._extract_blocks(ast)
            result["extends"] = self._extract_extends(ast)
            result["includes"] = self._extract_includes(ast)
            result["variables"] = self._extract_variables(source)

            # Determine template type
            template_type = self._determine_template_type(
                result["extends"], result["blocks"]
            )
            result["info"]["type"] = template_type

            # Validate syntax
            try:
                self.env.get_template(template_name)
                result["info"]["syntax_valid"] = True
            except TemplateSyntaxError as e:
                result["errors"].append(f"Syntax error: {e}")
                result["info"]["syntax_valid"] = False

            # Validate structure
            self._validate_structure(result, template_type)

            # Validate inheritance chain
            if result["extends"]:
                self._validate_inheritance(result)

            # Check for common issues
            self._check_common_issues(result, source)

            # Set overall validity
            result["valid"] = len(result["errors"]) == 0

            logger.debug(
                "Validation completed for %s: %s",
                template_name,
                "valid" if result["valid"] else "invalid",
            )

        except Exception as e:
            result["errors"].append(f"Validation error: {e!s}")
            logger.exception("Error validating template: %s", template_name)

        return result

    def validate_all_templates(self) -> dict[str, dict[str, Any]]:
        """Validate all templates in the templates directory.

        Returns:
            Dictionary mapping template names to validation results
        """
        results = {}

        try:
            # Find all HTML template files
            for template_path in self.templates_dir.rglob("*.html"):
                rel_path = template_path.relative_to(self.templates_dir)
                template_name = str(rel_path)

                results[template_name] = self.validate_template(template_name)

            # Validate inheritance relationships across all templates
            self._validate_global_inheritance(results)

            logger.info("Validated %d templates", len(results))

        except Exception:
            logger.exception("Error during bulk validation")

        return results

    def _extract_blocks(self, ast) -> list[str]:
        """Extract block names from template AST."""
        blocks = []

        def visit_blocks(node):
            if isinstance(node, Block):
                blocks.append(node.name)
            for child in node.iter_child_nodes():
                visit_blocks(child)

        visit_blocks(ast)
        return blocks

    def _extract_extends(self, ast) -> str | None:
        """Extract parent template name from extends directive."""
        for node in ast.body:
            if isinstance(node, Extends):
                if hasattr(node.template, "value"):
                    return node.template.value
                return str(node.template)
        return None

    def _extract_includes(self, ast) -> list[str]:
        """Extract included template names."""
        includes = []

        def visit_includes(node):
            if isinstance(node, Include):
                if hasattr(node.template, "value"):
                    includes.append(node.template.value)
                else:
                    includes.append(str(node.template))
            for child in node.iter_child_nodes():
                visit_includes(child)

        visit_includes(ast)
        return includes

    def _extract_variables(self, source: str) -> list[str]:
        """Extract variable names used in template."""
        try:
            ast = self.env.parse(source)
            variables = meta.find_undeclared_variables(ast)
            return list(variables)
        except (TemplateSyntaxError, AttributeError, ValueError) as e:
            logger.warning("Could not extract variables: %s", e)
            return []

    def _determine_template_type(self, extends: str | None, blocks: list[str]) -> str:
        """Determine the type of template based on its structure."""
        if extends:
            return "child"
        if blocks:
            return "base"
        return "standalone"

    def _validate_structure(self, result: dict[str, Any], template_type: str):
        """Validate template structure based on type."""
        required = self.required_blocks.get(template_type, [])
        blocks = result["blocks"]

        # Check for required blocks
        missing_blocks = set(required) - set(blocks)
        if missing_blocks:
            result["errors"].extend(
                [f"Missing required block: {block}" for block in missing_blocks]
            )

        # Type-specific validations
        if template_type == "base":
            if "content" not in blocks:
                result["warnings"].append(
                    "Base template should define a 'content' block"
                )

        elif template_type == "child":
            if not result["extends"]:
                result["errors"].append("Child template must extend a parent template")

    def _validate_inheritance(self, result: dict[str, Any]):
        """Validate template inheritance chain."""
        parent_name = result["extends"]

        if not parent_name:
            return

        # Check if parent exists
        parent_path = self.templates_dir / parent_name
        if not parent_path.exists():
            result["errors"].append(f"Parent template not found: {parent_name}")
            return

        # Validate parent template
        try:
            parent_source = parent_path.read_text(encoding="utf-8")
            parent_ast = self.env.parse(parent_source, parent_name)
            parent_blocks = self._extract_blocks(parent_ast)

            # Check if child blocks override existing parent blocks
            child_blocks = set(result["blocks"])
            parent_blocks_set = set(parent_blocks)

            # Warn about blocks that don't exist in parent
            unknown_blocks = child_blocks - parent_blocks_set
            if unknown_blocks:
                result["warnings"].extend(
                    [
                        f"Block '{block}' not defined in parent template"
                        for block in unknown_blocks
                    ]
                )

        except (OSError, TemplateSyntaxError, UnicodeDecodeError) as e:
            result["errors"].append(f"Error validating parent template: {e}")

    def _validate_global_inheritance(self, results: dict[str, dict[str, Any]]):
        """Validate inheritance relationships across all templates."""
        # Build inheritance tree
        inheritance_tree = {}

        for template_name, result in results.items():
            if result["extends"]:
                parent = result["extends"]
                if parent not in inheritance_tree:
                    inheritance_tree[parent] = []
                inheritance_tree[parent].append(template_name)

        # Check for circular dependencies
        for template_name in results:
            if self._has_circular_dependency(template_name, inheritance_tree, set()):
                results[template_name]["errors"].append(
                    "Circular dependency detected in inheritance chain"
                )

    def _has_circular_dependency(
        self, template: str, tree: dict[str, list[str]], visited: set[str]
    ) -> bool:
        """Check for circular dependencies in inheritance tree."""
        if template in visited:
            return True

        visited.add(template)
        children = tree.get(template, [])

        for child in children:
            if self._has_circular_dependency(child, tree, visited.copy()):
                return True

        return False

    def _check_common_issues(self, result: dict[str, Any], source: str):
        """Check for common template issues."""
        # Check for hardcoded values that should be variables
        hardcoded_patterns = [
            (
                r"\b\d{4}-\d{2}-\d{2}\b",
                "Hardcoded date found, consider using a variable",
            ),
            (
                r"http://[^\s]+",
                "Hardcoded HTTP URL found, consider using HTTPS or variable",
            ),
        ]

        for pattern, message in hardcoded_patterns:
            if re.search(pattern, source):
                result["warnings"].append(message)

        # Check for missing docstring/comments
        if not re.search(r"{#.*?#}", source, re.DOTALL):
            result["warnings"].append("Template lacks comments/documentation")

        # Check for potential XSS issues (unescaped variables)
        unescaped_vars = re.findall(r"{{\s*([^|}\s]+)\s*}}", source)
        if unescaped_vars:
            result["warnings"].append(
                f"Found {len(unescaped_vars)} potentially unescaped variables"
            )


def validate_template_file(template_path: Path) -> dict[str, Any]:
    """Validate a single template file.

    Args:
        template_path: Path to the template file

    Returns:
        Validation results dictionary
    """
    templates_dir = template_path.parent
    template_name = template_path.name

    validator = TemplateValidator(templates_dir)
    return validator.validate_template(template_name)


def validate_templates_directory(templates_dir: Path) -> dict[str, dict[str, Any]]:
    """Validate all templates in a directory.

    Args:
        templates_dir: Directory containing templates

    Returns:
        Dictionary mapping template names to validation results
    """
    validator = TemplateValidator(templates_dir)
    return validator.validate_all_templates()
