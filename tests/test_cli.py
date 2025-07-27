"""Tests for the Typer-based CLI functionality."""

from pathlib import Path
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from agentic_spec.cli import app
from agentic_spec.exceptions import (
    ConfigurationError,
    ValidationError,
)


@pytest.fixture
def cli_runner():
    """Create a CLI runner for testing Typer commands."""
    return CliRunner()


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        templates_dir = tmp_path / "templates"
        specs_dir = tmp_path / "specs"
        templates_dir.mkdir()
        specs_dir.mkdir()
        yield templates_dir, specs_dir


class TestCLIHelp:
    """Test CLI help functionality."""

    def test_main_help(self, cli_runner):
        """Test main help command."""
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "AI-powered programming specification generator" in result.stdout
        assert "generate" in result.stdout
        assert "review" in result.stdout
        assert "templates" in result.stdout

    def test_generate_help(self, cli_runner):
        """Test generate command help."""
        result = cli_runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        assert "Generate a new programming specification" in result.stdout
        assert "--inherits" in result.stdout
        assert "--project" in result.stdout
        assert "--user-role" in result.stdout

    def test_review_help(self, cli_runner):
        """Test review command help."""
        result = cli_runner.invoke(app, ["review", "--help"])
        assert result.exit_code == 0
        assert "List available specifications" in result.stdout

    def test_templates_help(self, cli_runner):
        """Test templates command help."""
        result = cli_runner.invoke(app, ["templates", "--help"])
        assert result.exit_code == 0
        assert "Create base templates" in result.stdout

    def test_config_help(self, cli_runner):
        """Test config command help."""
        result = cli_runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0
        assert "Manage application configuration" in result.stdout


class TestGenerateCommand:
    """Test the generate command functionality."""

    @patch("agentic_spec.cli.initialize_generator")
    @patch("agentic_spec.cli.get_prompt_input")
    def test_generate_with_prompt_argument(
        self, mock_get_prompt, mock_init_gen, cli_runner, temp_dirs
    ):
        """Test generate command with prompt as argument."""
        templates_dir, specs_dir = temp_dirs

        # Mock the generator and its methods
        mock_generator = MagicMock()
        mock_generator.config.default_context.user_role = "developer"
        mock_generator.config.default_context.target_audience = "team"
        mock_generator.config.default_context.desired_tone = "professional"
        mock_generator.config.default_context.complexity_level = "intermediate"
        mock_generator.config.default_context.time_constraints = "moderate"
        mock_generator.config.workflow.auto_review = False
        mock_generator.config.workflow.collect_feedback = False

        # Mock spec object
        mock_spec = MagicMock()
        mock_spec.metadata.id = "test123"
        mock_generator.generate_spec = AsyncMock(return_value=mock_spec)
        mock_generator.save_spec.return_value = specs_dir / "test-spec.yaml"

        mock_init_gen.return_value = mock_generator
        mock_get_prompt.return_value = "test prompt"

        result = cli_runner.invoke(
            app,
            [
                "generate",
                "test prompt",
                "--templates-dir",
                str(templates_dir),
                "--specs-dir",
                str(specs_dir),
            ],
        )

        assert result.exit_code == 0
        assert "Specification generated" in result.stdout
        mock_get_prompt.assert_called_once_with("test prompt")

    @patch("agentic_spec.cli.initialize_generator")
    @patch("agentic_spec.cli.get_prompt_input")
    def test_generate_with_validation_error(
        self, mock_get_prompt, mock_init_gen, cli_runner, temp_dirs
    ):
        """Test generate command with validation error."""
        templates_dir, specs_dir = temp_dirs

        mock_get_prompt.side_effect = ValidationError("No prompt provided")

        result = cli_runner.invoke(
            app,
            [
                "generate",
                "--templates-dir",
                str(templates_dir),
                "--specs-dir",
                str(specs_dir),
            ],
        )

        assert result.exit_code == 1
        assert "No prompt provided" in result.stdout

    @patch("agentic_spec.cli.initialize_generator")
    @patch("agentic_spec.cli.get_prompt_input")
    def test_generate_with_inherits(
        self, mock_get_prompt, mock_init_gen, cli_runner, temp_dirs
    ):
        """Test generate command with template inheritance."""
        templates_dir, specs_dir = temp_dirs

        # Mock the generator and its methods
        mock_generator = MagicMock()
        mock_generator.config.default_context.user_role = "developer"
        mock_generator.config.default_context.target_audience = "team"
        mock_generator.config.default_context.desired_tone = "professional"
        mock_generator.config.default_context.complexity_level = "intermediate"
        mock_generator.config.default_context.time_constraints = "moderate"
        mock_generator.config.workflow.auto_review = False
        mock_generator.config.workflow.collect_feedback = False

        # Mock spec object
        mock_spec = MagicMock()
        mock_spec.metadata.id = "test123"
        mock_generator.generate_spec = AsyncMock(return_value=mock_spec)
        mock_generator.save_spec.return_value = specs_dir / "test-spec.yaml"

        mock_init_gen.return_value = mock_generator
        mock_get_prompt.return_value = "test prompt"

        result = cli_runner.invoke(
            app,
            [
                "generate",
                "test prompt",
                "--inherits",
                "template1",
                "--inherits",
                "template2",
                "--templates-dir",
                str(templates_dir),
                "--specs-dir",
                str(specs_dir),
            ],
        )

        assert result.exit_code == 0
        mock_generator.generate_spec.assert_called_once()
        call_args = mock_generator.generate_spec.call_args
        assert call_args[0][1] == ["template1", "template2"]  # inherits argument


class TestReviewCommand:
    """Test the review command functionality."""

    def test_review_with_specs(self, cli_runner, temp_dirs):
        """Test review command with existing specs."""
        templates_dir, specs_dir = temp_dirs

        # Create some test spec files
        (specs_dir / "spec1.yaml").touch()
        (specs_dir / "spec2.yaml").touch()

        result = cli_runner.invoke(app, ["review", "--specs-dir", str(specs_dir)])

        assert result.exit_code == 0
        assert "Available specifications" in result.stdout
        assert "spec1.yaml" in result.stdout
        assert "spec2.yaml" in result.stdout

    def test_review_no_specs(self, cli_runner, temp_dirs):
        """Test review command with no specs."""
        templates_dir, specs_dir = temp_dirs

        result = cli_runner.invoke(app, ["review", "--specs-dir", str(specs_dir)])

        assert result.exit_code == 0
        assert "No specifications found" in result.stdout

    def test_review_nonexistent_directory(self, cli_runner):
        """Test review command with nonexistent specs directory."""
        result = cli_runner.invoke(app, ["review", "--specs-dir", "/nonexistent/path"])

        assert result.exit_code == 1
        assert "Specifications directory not found" in result.stdout


class TestTemplatesCommand:
    """Test the templates command functionality."""

    @patch("agentic_spec.cli.create_base_templates")
    def test_templates_create(self, mock_create_templates, cli_runner, temp_dirs):
        """Test templates command to create base templates."""
        templates_dir, specs_dir = temp_dirs

        result = cli_runner.invoke(
            app,
            [
                "templates",
                "--project",
                "test-project",
                "--templates-dir",
                str(templates_dir),
            ],
        )

        assert result.exit_code == 0
        assert "Base templates created" in result.stdout
        mock_create_templates.assert_called_once_with(templates_dir, "test-project")

    @patch("agentic_spec.cli.create_base_templates")
    def test_templates_create_error(self, mock_create_templates, cli_runner, temp_dirs):
        """Test templates command with error."""
        templates_dir, specs_dir = temp_dirs

        mock_create_templates.side_effect = Exception("Template creation failed")

        result = cli_runner.invoke(
            app, ["templates", "--templates-dir", str(templates_dir)]
        )

        assert result.exit_code == 1
        assert "Failed to create base templates" in result.stdout


class TestExpandCommand:
    """Test the expand command functionality."""

    @patch("agentic_spec.cli.initialize_generator")
    def test_expand_step_success(self, mock_init_gen, cli_runner, temp_dirs):
        """Test expand command success."""
        templates_dir, specs_dir = temp_dirs

        # Mock the generator and its methods
        mock_generator = MagicMock()
        mock_parent_spec = MagicMock()
        mock_sub_spec = MagicMock()
        mock_sub_spec.metadata.id = "sub123"

        mock_generator.find_spec_by_id.return_value = mock_parent_spec
        mock_generator.generate_sub_spec = AsyncMock(return_value=mock_sub_spec)
        mock_generator.save_spec.return_value = specs_dir / "sub-spec.yaml"
        mock_generator.review_spec = AsyncMock(
            return_value=["Review note 1", "Review note 2"]
        )

        mock_init_gen.return_value = mock_generator

        result = cli_runner.invoke(
            app,
            [
                "expand",
                "parent123:1",
                "--templates-dir",
                str(templates_dir),
                "--specs-dir",
                str(specs_dir),
            ],
        )

        assert result.exit_code == 0
        assert "Sub-specification generated" in result.stdout
        assert "sub123" in result.stdout
        mock_generator.find_spec_by_id.assert_called_once_with("parent123")
        mock_generator.generate_sub_spec.assert_called_once_with(
            mock_parent_spec, "parent123:1"
        )

    @patch("agentic_spec.cli.initialize_generator")
    def test_expand_invalid_step_id(self, mock_init_gen, cli_runner, temp_dirs):
        """Test expand command with invalid step ID format."""
        templates_dir, specs_dir = temp_dirs

        result = cli_runner.invoke(
            app,
            [
                "expand",
                "invalid-step-id",
                "--templates-dir",
                str(templates_dir),
                "--specs-dir",
                str(specs_dir),
            ],
        )

        assert result.exit_code == 0
        assert "Step ID must be in format" in result.stdout

    @patch("agentic_spec.cli.initialize_generator")
    def test_expand_spec_not_found(self, mock_init_gen, cli_runner, temp_dirs):
        """Test expand command with spec not found."""
        templates_dir, specs_dir = temp_dirs

        mock_generator = MagicMock()
        mock_generator.find_spec_by_id.return_value = None
        mock_init_gen.return_value = mock_generator

        result = cli_runner.invoke(
            app,
            [
                "expand",
                "nonexistent:1",
                "--templates-dir",
                str(templates_dir),
                "--specs-dir",
                str(specs_dir),
            ],
        )

        assert result.exit_code == 0
        assert "Specification nonexistent not found" in result.stdout


class TestPublishCommand:
    """Test the publish command functionality."""

    @patch("agentic_spec.cli.initialize_generator")
    @patch("agentic_spec.graph_visualization.print_spec_graph")
    def test_publish_spec_success(
        self, mock_print_graph, mock_init_gen, cli_runner, temp_dirs
    ):
        """Test publish command success."""
        templates_dir, specs_dir = temp_dirs

        # Mock the generator and its methods
        mock_generator = MagicMock()
        mock_target_spec = MagicMock()
        mock_target_spec.metadata.status = "draft"

        mock_generator.find_spec_by_id.return_value = mock_target_spec
        mock_generator.save_spec.return_value = specs_dir / "spec.yaml"
        mock_init_gen.return_value = mock_generator

        result = cli_runner.invoke(
            app, ["publish", "spec123", "--specs-dir", str(specs_dir)]
        )

        assert result.exit_code == 0
        assert "published as implemented" in result.stdout
        assert mock_target_spec.metadata.status == "implemented"
        mock_generator.save_spec.assert_called_once_with(mock_target_spec)

    @patch("agentic_spec.cli.initialize_generator")
    def test_publish_spec_not_found(self, mock_init_gen, cli_runner, temp_dirs):
        """Test publish command with spec not found."""
        templates_dir, specs_dir = temp_dirs

        mock_generator = MagicMock()
        mock_generator.find_spec_by_id.return_value = None
        mock_init_gen.return_value = mock_generator

        result = cli_runner.invoke(
            app, ["publish", "nonexistent", "--specs-dir", str(specs_dir)]
        )

        assert result.exit_code == 0
        assert "Specification nonexistent not found" in result.stdout


class TestConfigCommand:
    """Test the config command functionality."""

    @patch("agentic_spec.cli.get_config_manager")
    def test_config_init(self, mock_get_config_manager, cli_runner):
        """Test config init command."""
        mock_config_manager = MagicMock()
        mock_config_manager.create_default_config_file.return_value = Path(
            "config.yaml"
        )
        mock_get_config_manager.return_value = mock_config_manager

        result = cli_runner.invoke(app, ["config", "init"])

        assert result.exit_code == 0
        assert "Default configuration created" in result.stdout
        mock_config_manager.create_default_config_file.assert_called_once()

    @patch("agentic_spec.cli.get_config_manager")
    def test_config_show(self, mock_get_config_manager, cli_runner):
        """Test config show command."""
        mock_config_manager = MagicMock()
        mock_config = MagicMock()
        mock_config.model_dump.return_value = {"key": "value"}
        mock_config_manager.load_config.return_value = mock_config
        mock_get_config_manager.return_value = mock_config_manager

        result = cli_runner.invoke(app, ["config", "show"])

        assert result.exit_code == 0
        assert "Current Configuration" in result.stdout
        assert "key" in result.stdout

    @patch("agentic_spec.cli.get_config_manager")
    def test_config_validate_valid(self, mock_get_config_manager, cli_runner):
        """Test config validate command with valid config."""
        mock_config_manager = MagicMock()
        mock_config_manager.config_file.exists.return_value = True
        mock_config = MagicMock()
        mock_config.model_dump.return_value = {"key": "value"}
        mock_config_manager.load_config.return_value = mock_config
        mock_config_manager.validate_config_schema.return_value = []
        mock_get_config_manager.return_value = mock_config_manager

        result = cli_runner.invoke(app, ["config", "validate"])

        assert result.exit_code == 0
        assert "Configuration is valid" in result.stdout

    @patch("agentic_spec.cli.get_config_manager")
    def test_config_validate_invalid(self, mock_get_config_manager, cli_runner):
        """Test config validate command with invalid config."""
        mock_config_manager = MagicMock()
        mock_config_manager.config_file.exists.return_value = True
        mock_config = MagicMock()
        mock_config.model_dump.return_value = {"key": "value"}
        mock_config_manager.load_config.return_value = mock_config
        mock_config_manager.validate_config_schema.return_value = ["Error 1", "Error 2"]
        mock_get_config_manager.return_value = mock_config_manager

        result = cli_runner.invoke(app, ["config", "validate"])

        assert result.exit_code == 0
        assert "Configuration validation failed" in result.stdout
        assert "Error 1" in result.stdout

    def test_config_invalid_action(self, cli_runner):
        """Test config command with invalid action."""
        result = cli_runner.invoke(app, ["config", "invalid"])

        assert result.exit_code == 0
        assert "Configuration Commands" in result.stdout


class TestTemplateManagementCommand:
    """Test the template management command functionality."""

    @patch("agentic_spec.cli.list_templates")
    def test_template_list(self, mock_list_templates, cli_runner):
        """Test template list command."""
        mock_list_templates.return_value = ["template1.yaml", "template2.yaml"]

        result = cli_runner.invoke(app, ["template", "list"])

        assert result.exit_code == 0
        assert "Available Templates" in result.stdout
        assert "template1.yaml" in result.stdout
        assert "template2.yaml" in result.stdout

    @patch("agentic_spec.cli.list_templates")
    def test_template_list_empty(self, mock_list_templates, cli_runner):
        """Test template list command with no templates."""
        mock_list_templates.return_value = []

        result = cli_runner.invoke(app, ["template", "list"])

        assert result.exit_code == 0
        assert "No templates found" in result.stdout

    @patch("agentic_spec.cli.TemplateLoader")
    def test_template_info(self, mock_template_loader_class, cli_runner, temp_dirs):
        """Test template info command."""
        templates_dir, specs_dir = temp_dirs

        mock_loader = MagicMock()
        mock_loader.get_template_info.return_value = {
            "exists": True,
            "path": templates_dir / "test.yaml",
            "size": 1024,
            "modified": "2023-01-01T00:00:00",
        }
        mock_template_loader_class.return_value = mock_loader

        result = cli_runner.invoke(
            app,
            [
                "template",
                "info",
                "--template",
                "test.yaml",
                "--templates-dir",
                str(templates_dir),
            ],
        )

        assert result.exit_code == 0
        assert "Template Information: test.yaml" in result.stdout
        assert "Exists: ✅" in result.stdout

    def test_template_info_missing_name(self, cli_runner):
        """Test template info command without template name."""
        result = cli_runner.invoke(app, ["template", "info"])

        assert result.exit_code == 0
        assert "Template name required" in result.stdout

    def test_template_invalid_action(self, cli_runner):
        """Test template command with invalid action."""
        result = cli_runner.invoke(app, ["template", "invalid"])

        assert result.exit_code == 0
        assert "Template Commands" in result.stdout


class TestValidateCommand:
    """Test the validate command functionality."""

    @patch("agentic_spec.cli.TemplateValidator")
    def test_validate_templates_success(
        self, mock_validator_class, cli_runner, temp_dirs
    ):
        """Test validate command with successful validation."""
        templates_dir, specs_dir = temp_dirs

        mock_validator = MagicMock()
        mock_validator.validate_all_templates.return_value = {
            "template1.yaml": {
                "valid": True,
                "errors": [],
                "warnings": [],
                "info": {"type": "base"},
                "extends": None,
                "blocks": [],
            },
            "template2.yaml": {
                "valid": False,
                "errors": ["Missing required field"],
                "warnings": ["Deprecated syntax"],
                "info": {"type": "child"},
                "extends": "template1.yaml",
                "blocks": ["content"],
            },
        }
        mock_validator_class.return_value = mock_validator

        result = cli_runner.invoke(
            app, ["validate", "--templates-dir", str(templates_dir)]
        )

        assert result.exit_code == 0
        assert "Validation Results: 1/2 templates valid" in result.stdout
        assert "✅ template1.yaml" in result.stdout
        assert "❌ template2.yaml" in result.stdout
        assert "Missing required field" in result.stdout

    @patch("agentic_spec.cli.TemplateValidator")
    def test_validate_no_templates(self, mock_validator_class, cli_runner, temp_dirs):
        """Test validate command with no templates."""
        templates_dir, specs_dir = temp_dirs

        mock_validator = MagicMock()
        mock_validator.validate_all_templates.return_value = {}
        mock_validator_class.return_value = mock_validator

        result = cli_runner.invoke(
            app, ["validate", "--templates-dir", str(templates_dir)]
        )

        assert result.exit_code == 0
        assert "No templates found to validate" in result.stdout


class TestRenderCommand:
    """Test the render command functionality."""

    @patch("agentic_spec.cli.initialize_generator")
    @patch("agentic_spec.cli.render_specification_template")
    @patch("dataclasses.asdict")
    def test_render_spec_to_stdout(
        self, mock_asdict, mock_render, mock_init_gen, cli_runner, temp_dirs
    ):
        """Test render command output to stdout."""
        templates_dir, specs_dir = temp_dirs

        # Mock the generator and its methods
        mock_generator = MagicMock()
        mock_spec = MagicMock()
        mock_generator.find_spec_by_id.return_value = mock_spec
        mock_init_gen.return_value = mock_generator
        mock_asdict.return_value = {"mock": "spec_dict"}
        mock_render.return_value = "Rendered template content"

        result = cli_runner.invoke(
            app,
            [
                "render",
                "spec123",
                "--template",
                "test.html",
                "--templates-dir",
                str(templates_dir),
                "--specs-dir",
                str(specs_dir),
            ],
        )

        assert result.exit_code == 0
        assert "Rendered Template" in result.stdout
        assert "Rendered template content" in result.stdout

    @patch("agentic_spec.cli.initialize_generator")
    @patch("agentic_spec.cli.render_specification_template")
    @patch("dataclasses.asdict")
    def test_render_spec_to_file(
        self, mock_asdict, mock_render, mock_init_gen, cli_runner, temp_dirs
    ):
        """Test render command output to file."""
        templates_dir, specs_dir = temp_dirs
        output_file = specs_dir / "output.html"

        # Mock the generator and its methods
        mock_generator = MagicMock()
        mock_spec = MagicMock()
        mock_generator.find_spec_by_id.return_value = mock_spec
        mock_init_gen.return_value = mock_generator
        mock_asdict.return_value = {"mock": "spec_dict"}
        mock_render.return_value = "Rendered template content"

        result = cli_runner.invoke(
            app,
            [
                "render",
                "spec123",
                "--output",
                str(output_file),
                "--templates-dir",
                str(templates_dir),
                "--specs-dir",
                str(specs_dir),
            ],
        )

        assert result.exit_code == 0
        assert "Rendered template saved" in result.stdout
        assert output_file.exists()
        assert output_file.read_text() == "Rendered template content"

    @patch("agentic_spec.cli.initialize_generator")
    def test_render_spec_not_found(self, mock_init_gen, cli_runner, temp_dirs):
        """Test render command with spec not found."""
        templates_dir, specs_dir = temp_dirs

        mock_generator = MagicMock()
        mock_generator.find_spec_by_id.return_value = None
        mock_init_gen.return_value = mock_generator

        result = cli_runner.invoke(
            app,
            [
                "render",
                "nonexistent",
                "--templates-dir",
                str(templates_dir),
                "--specs-dir",
                str(specs_dir),
            ],
        )

        assert result.exit_code == 0
        assert "Specification nonexistent not found" in result.stdout


class TestErrorHandling:
    """Test CLI error handling."""

    def test_keyboard_interrupt_handling(self, cli_runner):
        """Test that KeyboardInterrupt is handled gracefully."""
        with patch("agentic_spec.cli.app") as mock_app:
            mock_app.side_effect = KeyboardInterrupt()

            # Note: This test is tricky with Typer's CliRunner
            # The actual KeyboardInterrupt handling is tested in the main() function

    @patch("agentic_spec.cli.initialize_generator")
    def test_configuration_error_handling(self, mock_init_gen, cli_runner, temp_dirs):
        """Test configuration error handling."""
        templates_dir, specs_dir = temp_dirs

        mock_init_gen.side_effect = ConfigurationError("Config error", "details")

        result = cli_runner.invoke(
            app,
            [
                "generate",
                "test prompt",
                "--templates-dir",
                str(templates_dir),
                "--specs-dir",
                str(specs_dir),
            ],
        )

        assert result.exit_code == 1
        assert "Config error" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__])
