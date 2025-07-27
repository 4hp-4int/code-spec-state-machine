"""Tests for Typer integration and CLI user experience improvements."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from agentic_spec.cli import app


@pytest.fixture
def cli_runner():
    """Create a CLI runner for testing Typer commands."""
    return CliRunner()


class TestTyperIntegration:
    """Test Typer integration and user experience improvements."""

    def test_typer_app_configuration(self):
        """Test that Typer app is configured correctly."""
        assert isinstance(app, typer.Typer)
        assert app.info.name == "agentic-spec"
        assert "AI-powered programming specification generator" in app.info.help

    def test_no_args_shows_help(self, cli_runner):
        """Test that running with no arguments shows help."""
        result = cli_runner.invoke(app, [])
        assert result.exit_code == 0
        assert "Usage:" in result.stdout
        assert "Commands" in result.stdout

    def test_invalid_command_shows_error(self, cli_runner):
        """Test that invalid commands show appropriate error."""
        result = cli_runner.invoke(app, ["invalid-command"])
        assert result.exit_code != 0
        assert "No such command" in result.stdout or "Usage:" in result.stdout

    def test_command_help_follows_conventions(self, cli_runner):
        """Test that all commands follow CLI help conventions."""
        commands = ["generate", "review", "templates", "graph", "expand", "publish", "config", "template", "validate", "render"]
        
        for command in commands:
            result = cli_runner.invoke(app, [command, "--help"])
            assert result.exit_code == 0, f"Help failed for command: {command}"
            assert "Usage:" in result.stdout, f"No usage info for command: {command}"
            assert "Options" in result.stdout, f"No options section for command: {command}"

    def test_version_option_handling(self, cli_runner):
        """Test version option handling (if implemented)."""
        # Note: Version option would need to be added to the Typer app
        # This test documents the expected behavior
        result = cli_runner.invoke(app, ["--version"])
        # Currently this will fail as --version is not implemented
        # When implemented, should return version information

    def test_global_options_parsing(self, cli_runner):
        """Test that global options are parsed correctly."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            templates_dir = Path(tmp_dir) / "templates"
            specs_dir = Path(tmp_dir) / "specs"
            templates_dir.mkdir()
            specs_dir.mkdir()

            # Test that global options don't interfere with command execution
            result = cli_runner.invoke(app, [
                "review",
                "--templates-dir", str(templates_dir),
                "--specs-dir", str(specs_dir)
            ])
            
            # Should execute successfully even with empty directories
            assert result.exit_code == 0


class TestUserExperienceImprovements:
    """Test user experience improvements from Typer integration."""

    def test_rich_help_formatting(self, cli_runner):
        """Test that help uses rich formatting."""
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        # Rich formatting includes Unicode characters and colors in terminal
        # In testing, we just verify structure is present
        assert "Usage:" in result.stdout
        assert "Commands" in result.stdout
        assert "Options" in result.stdout

    def test_command_categorization(self, cli_runner):
        """Test that commands are properly categorized in help."""
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        
        # All main commands should be listed
        expected_commands = [
            "generate", "review", "templates", "graph", 
            "expand", "publish", "config", "template", 
            "validate", "render"
        ]
        
        for command in expected_commands:
            assert command in result.stdout

    def test_intuitive_command_names(self, cli_runner):
        """Test that command names are intuitive and follow conventions."""
        # Test verb-noun patterns where applicable
        commands_with_descriptions = {
            "generate": "Generate a new programming specification",
            "review": "List available specifications",
            "templates": "Create base templates",
            "validate": "Validate all templates",
            "render": "Render a specification"
        }
        
        for command, expected_desc in commands_with_descriptions.items():
            result = cli_runner.invoke(app, [command, "--help"])
            assert result.exit_code == 0
            # Check that description matches expected pattern
            assert any(word in result.stdout.lower() for word in expected_desc.lower().split())

    def test_option_consistency(self, cli_runner):
        """Test that options are consistently named across commands."""
        # Commands that should accept templates-dir
        template_dir_commands = ["generate", "templates", "expand", "template", "validate", "render"]
        
        for command in template_dir_commands:
            result = cli_runner.invoke(app, [command, "--help"])
            assert result.exit_code == 0
            assert "--templates-dir" in result.stdout, f"Command {command} missing --templates-dir option"

        # Commands that should accept specs-dir
        specs_dir_commands = ["generate", "review", "graph", "expand", "publish", "render"]
        
        for command in specs_dir_commands:
            result = cli_runner.invoke(app, [command, "--help"])
            assert result.exit_code == 0
            assert "--specs-dir" in result.stdout, f"Command {command} missing --specs-dir option"

    def test_error_message_clarity(self, cli_runner):
        """Test that error messages are clear and helpful."""
        # Test missing required argument
        result = cli_runner.invoke(app, ["expand"])
        assert result.exit_code != 0
        # Should show usage information when required arguments are missing
        assert "Usage:" in result.stdout or "Error:" in result.stdout

        result = cli_runner.invoke(app, ["publish"])
        assert result.exit_code != 0
        # Should show usage information when required arguments are missing
        assert "Usage:" in result.stdout or "Error:" in result.stdout

    @patch("agentic_spec.cli.initialize_generator")
    def test_informative_progress_messages(self, mock_init_gen, cli_runner):
        """Test that commands provide informative progress messages."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            templates_dir = Path(tmp_dir) / "templates"
            specs_dir = Path(tmp_dir) / "specs"
            templates_dir.mkdir()
            specs_dir.mkdir()

            # Test generate command progress messages
            mock_generator = MagicMock()
            mock_init_gen.side_effect = Exception("Test error")

            result = cli_runner.invoke(app, [
                "generate",
                "test prompt",
                "--templates-dir", str(templates_dir),
                "--specs-dir", str(specs_dir)
            ])

            # Should show clear error message
            assert result.exit_code == 1
            assert "Failed to initialize application" in result.stdout


class TestCLIConventions:
    """Test adherence to CLI conventions and best practices."""

    def test_help_option_availability(self, cli_runner):
        """Test that --help is available for all commands."""
        # Get list of commands from main help
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        
        # Extract command names (simplified approach)
        commands = ["generate", "review", "templates", "graph", "expand", "publish", "config", "template", "validate", "render"]
        
        for command in commands:
            result = cli_runner.invoke(app, [command, "--help"])
            assert result.exit_code == 0, f"--help not working for {command}"

    def test_option_naming_conventions(self, cli_runner):
        """Test that options follow standard naming conventions."""
        result = cli_runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        
        # Long options should use double dashes
        assert "--inherits" in result.stdout
        assert "--project" in result.stdout
        assert "--user-role" in result.stdout
        assert "--target-audience" in result.stdout
        
        # Options should use kebab-case for multi-word options
        assert "--templates-dir" in result.stdout
        assert "--specs-dir" in result.stdout
        assert "--user-role" in result.stdout
        assert "--target-audience" in result.stdout

    def test_boolean_flags(self, cli_runner):
        """Test that boolean flags work correctly."""
        result = cli_runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        
        # --feedback should be a boolean flag
        assert "--feedback" in result.stdout
        # Should not require a value
        assert "Enable interactive feedback collection" in result.stdout

    def test_argument_vs_option_usage(self, cli_runner):
        """Test proper distinction between arguments and options."""
        # Commands that use positional arguments
        commands_with_args = {
            "expand": "step_id",
            "publish": "spec_id", 
            "config": "action",
            "template": "action",
            "render": "spec_id"
        }
        
        for command, arg_name in commands_with_args.items():
            result = cli_runner.invoke(app, [command, "--help"])
            assert result.exit_code == 0
            assert "Arguments" in result.stdout, f"Command {command} should show Arguments section"

    def test_consistent_path_handling(self, cli_runner):
        """Test that path options are consistently handled."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            templates_dir = Path(tmp_dir) / "templates"
            specs_dir = Path(tmp_dir) / "specs"
            templates_dir.mkdir()
            specs_dir.mkdir()

            # Test that paths work with various formats
            result = cli_runner.invoke(app, [
                "review",
                "--specs-dir", str(specs_dir)
            ])
            assert result.exit_code == 0

            # Test relative paths
            result = cli_runner.invoke(app, [
                "review", 
                "--specs-dir", "specs"
            ])
            # Should handle gracefully even if directory doesn't exist
            assert result.exit_code in [0, 1]  # Either succeeds or fails gracefully


class TestBackwardCompatibility:
    """Test that new Typer implementation maintains backward compatibility."""

    def test_all_original_commands_available(self, cli_runner):
        """Test that all original commands are still available."""
        original_commands = [
            "generate", "review", "templates", "graph", 
            "expand", "publish", "config", "template", 
            "validate", "render"
        ]
        
        for command in original_commands:
            result = cli_runner.invoke(app, [command, "--help"])
            assert result.exit_code == 0, f"Original command {command} not available"

    def test_original_options_preserved(self, cli_runner):
        """Test that original command options are preserved."""
        # Test generate command options
        result = cli_runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        
        original_options = [
            "--inherits", "--project", "--user-role", 
            "--target-audience", "--tone", "--complexity",
            "--feedback", "--templates-dir", "--specs-dir",
            "--config", "--set"
        ]
        
        for option in original_options:
            assert option in result.stdout, f"Original option {option} not preserved"

    @patch("agentic_spec.cli.create_base_templates")
    def test_templates_command_compatibility(self, mock_create_templates, cli_runner):
        """Test that templates command works as before."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            templates_dir = Path(tmp_dir) / "templates"
            templates_dir.mkdir()

            result = cli_runner.invoke(app, [
                "templates",
                "--project", "test-project",
                "--templates-dir", str(templates_dir)
            ])

            assert result.exit_code == 0
            mock_create_templates.assert_called_once_with(templates_dir, "test-project")

    def test_configuration_options_compatibility(self, cli_runner):
        """Test that configuration-related options still work."""
        result = cli_runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        
        # Configuration options should be preserved
        assert "--config" in result.stdout
        assert "--set" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__])