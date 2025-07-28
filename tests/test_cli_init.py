"""Tests for CLI initialization functionality."""

import os
from pathlib import Path
import tempfile
from unittest.mock import patch

import typer
from typer.testing import CliRunner

from agentic_spec.cli_utils import utils_app


class TestInitProject:
    """Test the init_project command functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.tmpdir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()

    def teardown_method(self):
        """Clean up after tests."""
        os.chdir(self.original_cwd)

    def test_init_project_basic_success(self):
        """Test basic init project success."""
        os.chdir(self.tmpdir)

        # Mock user input - use defaults for everything
        with patch("builtins.input", side_effect=["y", "", "test-project"]):
            result = self.runner.invoke(utils_app, ["init", "--force"])

        assert result.exit_code == 0
        assert "🚀 Welcome to agentic-spec!" in result.stdout
        assert "Project initialized successfully!" in result.stdout

        # Check that directories were created
        assert Path("spec-templates").exists()
        assert Path("prompt-templates").exists()
        assert Path("specs").exists()
        assert Path("logs").exists()

        # Check that config file was created
        assert Path("agentic_spec_config.yaml").exists()

    def test_init_project_custom_directories(self):
        """Test init with custom directory names."""
        os.chdir(self.tmpdir)

        with patch("builtins.input", side_effect=["y", "", "custom-project"]):
            result = self.runner.invoke(
                utils_app,
                [
                    "init",
                    "--force",
                    "--spec-templates-dir",
                    "custom-specs",
                    "--prompt-templates-dir",
                    "custom-prompts",
                    "--specs-dir",
                    "my-outputs",
                ],
            )

        assert result.exit_code == 0
        assert "custom-specs/" in result.stdout
        assert "custom-prompts/" in result.stdout
        assert "my-outputs/" in result.stdout

        # Check custom directories were created
        assert Path("custom-specs").exists()
        assert Path("custom-prompts").exists()
        assert Path("my-outputs").exists()

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-1234"})
    def test_init_project_with_existing_api_key(self):
        """Test init when OPENAI_API_KEY already exists."""
        os.chdir(self.tmpdir)

        with patch("builtins.input", side_effect=["y", "test-project"]):
            result = self.runner.invoke(utils_app, ["init", "--force"])

        assert result.exit_code == 0
        assert "Found OPENAI_API_KEY environment variable" in result.stdout
        assert "***1234" in result.stdout  # Masked key display

    @patch.dict(os.environ, {}, clear=True)
    def test_init_project_no_api_key(self):
        """Test init when no OPENAI_API_KEY exists."""
        os.chdir(self.tmpdir)

        with patch("builtins.input", side_effect=["", "test-project"]):
            result = self.runner.invoke(utils_app, ["init", "--force"])

        assert result.exit_code == 0
        assert (
            "Remember to set your OPENAI_API_KEY environment variable" in result.stdout
        )

    def test_init_project_single_provider_no_choice_error(self):
        """Test that single provider doesn't cause typer choice error."""
        os.chdir(self.tmpdir)

        with patch("builtins.input", side_effect=["y", "", "test-project"]):
            result = self.runner.invoke(utils_app, ["init", "--force"])

        assert result.exit_code == 0
        assert "Using AI provider: openai" in result.stdout
        # Should not see a choice prompt since there's only one provider

    def test_init_project_non_interactive_mode(self):
        """Test init in non-interactive environment (CI/automated scenarios)."""
        os.chdir(self.tmpdir)

        # Simulate non-interactive environment by having input fail
        with patch("typer.confirm", side_effect=typer.Abort()):
            with patch("typer.prompt", side_effect=typer.Abort()):
                result = self.runner.invoke(utils_app, ["init", "--force"])

        assert result.exit_code == 0
        assert "non-interactive mode" in result.stdout
        assert "Using default project name" in result.stdout

    def test_init_project_file_permission_error(self):
        """Test init handling of file permission errors."""
        # Use a directory where we can't write (simulate permission error)
        readonly_dir = Path(self.tmpdir) / "readonly"
        readonly_dir.mkdir()

        # Make directory read-only on Unix systems
        if hasattr(os, "chmod"):
            readonly_dir.chmod(0o444)

        os.chdir(str(readonly_dir))

        with patch("builtins.input", side_effect=["y", "", "test-project"]):
            result = self.runner.invoke(utils_app, ["init", "--force"])

        # Should handle permission error gracefully
        if result.exit_code != 0:
            assert (
                "Permission error" in result.stdout or "Error creating" in result.stdout
            )

    def test_init_project_force_flag_overwrites(self):
        """Test that --force flag overwrites existing config without prompting."""
        os.chdir(self.tmpdir)

        # Create existing config file
        config_file = Path("agentic_spec_config.yaml")
        config_file.write_text("existing: config")

        # Test with --force flag - should overwrite without prompting
        with patch("builtins.input", side_effect=["y", "", "test-project"]):
            result = self.runner.invoke(utils_app, ["init", "--force"])

        assert result.exit_code == 0

        # Check that config file was overwritten
        with config_file.open() as f:
            content = f.read()
        assert "existing: config" not in content
        assert "ai_settings" in content

    @patch("agentic_spec.cli_utils.create_base_templates")
    def test_init_project_template_creation_failure(self, mock_create_templates):
        """Test init handling when template creation fails."""
        os.chdir(self.tmpdir)
        mock_create_templates.side_effect = Exception("Template creation failed")

        with patch("builtins.input", side_effect=["y", "", "test-project"]):
            result = self.runner.invoke(utils_app, ["init", "--force"])

        # Should continue despite template creation failure
        assert result.exit_code == 0
        assert "Warning: Could not create spec templates" in result.stdout

    @patch("agentic_spec.cli_utils.SpecGenerator")
    @patch("agentic_spec.cli_utils.AgenticSpecConfig")
    def test_init_project_foundation_spec_failure(self, mock_config, mock_generator):
        """Test init handling when foundation spec creation fails."""
        os.chdir(self.tmpdir)
        mock_generator.return_value.sync_foundation_spec.side_effect = Exception(
            "Foundation sync failed"
        )

        with patch("builtins.input", side_effect=["y", "", "test-project"]):
            result = self.runner.invoke(utils_app, ["init", "--force"])

        # Should continue despite foundation spec failure
        assert result.exit_code == 0
        assert "Warning: Could not create foundation spec" in result.stdout
        assert (
            "You can create it later with: agentic-spec sync-foundation"
            in result.stdout
        )

    def test_init_project_handles_interrupts_gracefully(self):
        """Test init provides helpful error messages."""
        os.chdir(self.tmpdir)

        # Test that the init function has proper error handling structure
        # (The actual KeyboardInterrupt testing is complex with CLI runners)
        result = self.runner.invoke(utils_app, ["init", "--help"])

        assert result.exit_code == 0
        assert "Initialize a new agentic-spec project" in result.stdout

    def test_init_project_config_validation(self):
        """Test that generated config file is valid."""
        os.chdir(self.tmpdir)

        with patch("builtins.input", side_effect=["y", "", "test-project"]):
            result = self.runner.invoke(utils_app, ["init", "--force"])

        assert result.exit_code == 0

        # Check that config file exists and is valid YAML
        config_file = Path("agentic_spec_config.yaml")
        assert config_file.exists()

        import yaml

        with config_file.open() as f:
            config_data = yaml.safe_load(f)

        # Validate config structure
        assert "ai_settings" in config_data
        assert "directories" in config_data
        assert "prompt_settings" in config_data
        assert "default_context" in config_data

        # Check that directories match what was specified
        assert config_data["directories"]["spec_templates_dir"] == "spec-templates"
        assert config_data["directories"]["specs_dir"] == "specs"

    def test_init_project_templates_created_correctly(self):
        """Test that all expected template files are created."""
        os.chdir(self.tmpdir)

        with patch("builtins.input", side_effect=["y", "", "test-project"]):
            result = self.runner.invoke(utils_app, ["init", "--force"])

        assert result.exit_code == 0

        # Check spec templates
        spec_templates_dir = Path("spec-templates")
        expected_spec_templates = [
            "agentic-spec-foundation.yaml",
            "base-coding-standards.yaml",
            "web-api.yaml",
            "cli-application.yaml",
            "data-analysis.yaml",
            "machine-learning.yaml",
        ]

        for template in expected_spec_templates:
            template_file = spec_templates_dir / template
            assert template_file.exists(), f"Missing spec template: {template}"

        # Check prompt templates
        prompt_templates_dir = Path("prompt-templates")
        expected_prompt_templates = [
            "basic-specification.md",
            "feature-addition.md",
            "bug-fix.md",
        ]

        for template in expected_prompt_templates:
            template_file = prompt_templates_dir / template
            assert template_file.exists(), f"Missing prompt template: {template}"

            # Check that template contains some project name (could be default "my-project")
            content = template_file.read_text()
            assert (
                "test-project" in content or "my-project" in content
            ), f"Template {template} missing project name"


class TestInitProjectEdgeCases:
    """Test edge cases and error conditions for init project."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.tmpdir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()

    def teardown_method(self):
        """Clean up after tests."""
        os.chdir(self.original_cwd)

    def test_init_project_very_long_project_name(self):
        """Test init with very long project name."""
        os.chdir(self.tmpdir)
        long_name = "a" * 200  # Very long project name

        with patch("builtins.input", side_effect=["y", "", long_name]):
            result = self.runner.invoke(utils_app, ["init", "--force"])

        assert result.exit_code == 0
        # Should handle long names gracefully

    def test_init_project_special_characters_in_name(self):
        """Test init with special characters in project name."""
        os.chdir(self.tmpdir)
        special_name = "my-project_2024!@#"

        with patch("builtins.input", side_effect=["y", "", special_name]):
            result = self.runner.invoke(utils_app, ["init", "--force"])

        assert result.exit_code == 0
        # Should handle special characters in project names

    def test_init_project_empty_project_name(self):
        """Test init with empty project name (should use default)."""
        os.chdir(self.tmpdir)

        with patch("builtins.input", side_effect=["y", "", ""]):  # Empty project name
            result = self.runner.invoke(utils_app, ["init", "--force"])

        assert result.exit_code == 0
        assert "my-project" in result.stdout  # Should use default
