"""Tests for configurable sync-foundation functionality.

Tests the new YAML-based configuration system for sync-foundation command,
including file categorization, dependency detection, validation, and error handling.
"""

from pathlib import Path
import tempfile
from unittest.mock import patch

from pydantic import ValidationError
import pytest
import yaml

from agentic_spec.config import (
    AgenticSpecConfig,
    DependencyDetection,
    FileCategorization,
    ProjectAnalysis,
    SyncFoundationConfig,
)
from agentic_spec.core import SpecGenerator
from agentic_spec.exceptions import (
    ConfigParsingError,
    ConfigValidationError,
    SyncFoundationConfigError,
)


class TestSyncFoundationConfig:
    """Test the SyncFoundationConfig Pydantic model."""

    def test_default_config_creation(self):
        """Test creating config with all defaults."""
        config = SyncFoundationConfig()

        assert config.foundation_template_name == "project-foundation"
        assert config.generate_statistics is True
        assert config.include_transitive_dependencies is True
        assert config.max_transitive_dependencies == 10
        assert config.enable_caching is True
        assert config.cache_duration_hours == 24

        # Check nested defaults
        assert len(config.file_categorization.cli_patterns) > 0
        assert len(config.dependency_detection.requirements_files) > 0
        assert config.project_analysis.default_language == "Python"

    def test_config_validation_valid_data(self):
        """Test config validation with valid data."""
        valid_data = {
            "foundation_template_name": "my-foundation",
            "max_transitive_dependencies": 5,
            "cache_duration_hours": 12,
            "file_categorization": {
                "cli_patterns": ["cli", "command"],
                "web_ui_patterns": ["web", "ui"],
            },
            "dependency_detection": {
                "requirements_files": ["requirements.txt"],
                "config_files": ["pyproject.toml"],
            },
        }

        config = SyncFoundationConfig(**valid_data)
        assert config.foundation_template_name == "my-foundation"
        assert config.max_transitive_dependencies == 5

    def test_config_validation_invalid_data(self):
        """Test config validation with invalid data."""
        # Test invalid foundation template name
        with pytest.raises(ValidationError) as exc_info:
            SyncFoundationConfig(foundation_template_name="")
        assert "String should have at least 1 character" in str(exc_info.value)

        # Test invalid numeric ranges
        with pytest.raises(ValidationError) as exc_info:
            SyncFoundationConfig(max_transitive_dependencies=-1)
        assert "Input should be greater than or equal to 0" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            SyncFoundationConfig(cache_duration_hours=200)
        assert "Input should be less than or equal to 168" in str(exc_info.value)

    def test_foundation_template_name_validation(self):
        """Test foundation template name field validation."""
        # Valid names
        valid_names = ["project-foundation", "my_foundation", "foundation123"]
        for name in valid_names:
            config = SyncFoundationConfig(foundation_template_name=name)
            assert config.foundation_template_name == name

        # Invalid characters
        invalid_names = [
            "foundation/name",
            "foundation\\name",
            "foundation:name",
            "foundation*name",
        ]
        for name in invalid_names:
            with pytest.raises(ValidationError) as exc_info:
                SyncFoundationConfig(foundation_template_name=name)
            assert "invalid characters" in str(exc_info.value)

        # Whitespace handling
        config = SyncFoundationConfig(foundation_template_name="  spaced-name  ")
        assert config.foundation_template_name == "spaced-name"

    def test_pattern_validation_method(self):
        """Test the validate_patterns method."""
        # Config with overlapping patterns
        config = SyncFoundationConfig()
        config.file_categorization.cli_patterns = ["main", "cli"]
        config.file_categorization.web_ui_patterns = [
            "main",
            "web",
        ]  # 'main' is duplicate
        config.dependency_detection.requirements_files = [
            "requirements.txt",
            "pyproject.toml",
        ]
        config.dependency_detection.config_files = [
            "pyproject.toml",
            "setup.py",
        ]  # 'pyproject.toml' overlap

        warnings = config.validate_patterns()

        assert len(warnings) >= 2
        assert any("Duplicate patterns found" in warning for warning in warnings)
        assert any(
            "Files listed in both requirements_files and config_files" in warning
            for warning in warnings
        )

    def test_skip_patterns_validation_method(self):
        """Test the validate_skip_patterns method."""
        config = SyncFoundationConfig()
        config.project_analysis.skip_patterns = ["*", "src/core", ".venv/"]

        warnings = config.validate_skip_patterns()

        assert len(warnings) >= 2
        assert any(
            "Very broad skip pattern detected" in warning for warning in warnings
        )
        assert any("may exclude essential directory" in warning for warning in warnings)


class TestConfigFileLoading:
    """Test loading configuration from YAML files."""

    @pytest.fixture
    def temp_project(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def spec_generator_factory(self, temp_project):
        """Factory to create SpecGenerator instances."""

        def _create_generator(discovery_config_file=None):
            spec_templates_dir = temp_project / "templates"
            specs_dir = temp_project / "specs"
            spec_templates_dir.mkdir(exist_ok=True)
            specs_dir.mkdir(exist_ok=True)
            config = AgenticSpecConfig()

            return SpecGenerator(
                spec_templates_dir,
                specs_dir,
                config,
                discovery_config_file=discovery_config_file,
            )

        return _create_generator

    def test_auto_discovery_config_loading(self, temp_project, spec_generator_factory):
        """Test automatic discovery of config files."""
        # Create sync_foundation_config.yaml
        config_content = {
            "foundation_template_name": "auto-discovered",
            "file_categorization": {"cli_patterns": ["custom-cli"]},
        }

        config_file = temp_project / "sync_foundation_config.yaml"
        with config_file.open("w") as f:
            yaml.dump(config_content, f)

        generator = spec_generator_factory()

        assert generator.sync_foundation_config is not None
        assert (
            generator.sync_foundation_config.foundation_template_name
            == "auto-discovered"
        )
        assert (
            "custom-cli"
            in generator.sync_foundation_config.file_categorization.cli_patterns
        )

    def test_explicit_config_file_loading(self, temp_project, spec_generator_factory):
        """Test loading config from explicitly specified file."""
        config_content = {
            "foundation_template_name": "explicit-config",
            "max_transitive_dependencies": 20,
        }

        custom_config_file = temp_project / "custom-config.yaml"
        with custom_config_file.open("w") as f:
            yaml.dump(config_content, f)

        generator = spec_generator_factory(discovery_config_file=custom_config_file)

        assert generator.sync_foundation_config is not None
        assert (
            generator.sync_foundation_config.foundation_template_name
            == "explicit-config"
        )
        assert generator.sync_foundation_config.max_transitive_dependencies == 20

    def test_config_file_not_found(self, temp_project, spec_generator_factory):
        """Test handling when explicit config file doesn't exist."""
        non_existent_file = temp_project / "does-not-exist.yaml"

        with pytest.raises(SyncFoundationConfigError) as exc_info:
            spec_generator_factory(discovery_config_file=non_existent_file)

        assert "Specified discovery config file not found" in str(exc_info.value)
        assert str(non_existent_file) in str(exc_info.value)

    def test_invalid_yaml_syntax(self, temp_project, spec_generator_factory):
        """Test handling of invalid YAML syntax."""
        config_file = temp_project / "invalid.yaml"
        config_file.write_text("invalid: yaml: content: [\n")  # Invalid YAML

        with pytest.raises(ConfigParsingError) as exc_info:
            spec_generator_factory(discovery_config_file=config_file)

        assert "Failed to parse YAML" in str(exc_info.value)

    def test_empty_config_file(self, temp_project, spec_generator_factory):
        """Test handling of empty config file."""
        config_file = temp_project / "empty.yaml"
        config_file.write_text("")  # Empty file

        with pytest.raises(ConfigParsingError) as exc_info:
            spec_generator_factory(discovery_config_file=config_file)

        assert "Config file is empty or contains only comments" in str(exc_info.value)

    def test_non_dict_yaml_content(self, temp_project, spec_generator_factory):
        """Test handling of YAML that isn't a dictionary."""
        config_file = temp_project / "list.yaml"
        config_file.write_text("- item1\n- item2")  # YAML list instead of dict

        with pytest.raises(ConfigParsingError) as exc_info:
            spec_generator_factory(discovery_config_file=config_file)

        assert "Config file must contain a YAML object, got list" in str(exc_info.value)

    def test_auto_discovery_priority_order(self, temp_project, spec_generator_factory):
        """Test that auto-discovery follows correct priority order."""
        # Create multiple config files
        configs = [
            ("sync_foundation_config.yaml", "first-priority"),
            ("sync-foundation-config.yaml", "second-priority"),
            ("project_discovery.yaml", "third-priority"),
        ]

        for filename, template_name in configs:
            config_content = {"foundation_template_name": template_name}
            config_file = temp_project / filename
            with config_file.open("w") as f:
                yaml.dump(config_content, f)

        generator = spec_generator_factory()

        # Should load the first one in priority order
        assert (
            generator.sync_foundation_config.foundation_template_name
            == "first-priority"
        )

    def test_no_config_file_fallback(self, temp_project, spec_generator_factory):
        """Test fallback to None when no config files are found."""
        generator = spec_generator_factory()

        # Should fall back to None (use defaults)
        assert generator.sync_foundation_config is None


class TestConfigDrivenAnalysis:
    """Test file categorization and dependency detection with custom configs."""

    @pytest.fixture
    def temp_project_with_files(self):
        """Create temp project with diverse file structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create custom directory structure
            (project_path / "commands").mkdir()
            (project_path / "frontend").mkdir()
            (project_path / "backend").mkdir()
            (project_path / "services").mkdir()

            # Create files that match custom patterns
            (project_path / "commands" / "main.py").write_text(
                "import typer\napp = typer.Typer()"
            )
            (project_path / "frontend" / "app.py").write_text(
                "from fastapi import FastAPI, HTMLResponse\nreturn HTMLResponse()"
            )
            (project_path / "backend" / "database.py").write_text(
                "import aiosqlite\nasync def connect():"
            )
            (project_path / "services" / "api.py").write_text(
                "from fastapi import APIRouter\nrouter = APIRouter()"
            )

            # Create requirements files
            (project_path / "requirements.txt").write_text(
                "fastapi>=0.100.0\ntyper>=0.9.0"
            )
            (project_path / "pyproject.toml").write_text("""
[project]
dependencies = ["aiosqlite>=0.19.0"]
""")

            yield project_path

    def test_custom_file_categorization_patterns(self, temp_project_with_files):
        """Test file categorization with custom patterns."""
        # Create custom config with content indicators as well
        # Note: Order matters in categorization - more specific patterns should avoid conflicts
        custom_config = SyncFoundationConfig(
            file_categorization=FileCategorization(
                cli_patterns=["commands"],
                web_ui_patterns=["frontend"],  # Only match frontend directory
                database_patterns=["backend"],
                api_patterns=["services"],
                # Add content indicators that don't conflict
                cli_content_indicators=["typer"],
                web_ui_content_indicators=[
                    "HTMLResponse"
                ],  # Use non-conflicting indicator
                database_content_indicators=["aiosqlite"],
                api_content_indicators=["APIRouter"],
            )
        )

        spec_templates_dir = temp_project_with_files / "templates"
        specs_dir = temp_project_with_files / "specs"
        spec_templates_dir.mkdir(exist_ok=True)
        specs_dir.mkdir(exist_ok=True)

        generator = SpecGenerator(spec_templates_dir, specs_dir, AgenticSpecConfig())
        generator.sync_foundation_config = custom_config

        categorization = generator._categorize_files(temp_project_with_files)

        # Check that custom patterns work
        cli_files = [str(f) for f in categorization["cli_files"]]
        web_files = [str(f) for f in categorization["web_ui_files"]]
        db_files = [str(f) for f in categorization["database_files"]]
        api_files = [str(f) for f in categorization["api_files"]]

        assert any("commands" in f for f in cli_files)
        assert any("frontend" in f for f in web_files)
        assert any("backend" in f for f in db_files)
        assert any("services" in f for f in api_files)

    def test_custom_dependency_detection_patterns(self, temp_project_with_files):
        """Test dependency detection with custom patterns."""
        # Test that config properly separates requirements files from config files
        custom_config = SyncFoundationConfig(
            dependency_detection=DependencyDetection(
                requirements_files=["requirements.txt"],  # Only text files
                config_files=["pyproject.toml"],  # Only structured files
            )
        )

        spec_templates_dir = temp_project_with_files / "templates"
        specs_dir = temp_project_with_files / "specs"
        spec_templates_dir.mkdir(exist_ok=True)
        specs_dir.mkdir(exist_ok=True)

        generator = SpecGenerator(spec_templates_dir, specs_dir, AgenticSpecConfig())
        generator.sync_foundation_config = custom_config

        # Test requirements file extraction
        req_deps = generator._extract_from_requirements(temp_project_with_files)
        req_names = [dep["name"] for dep in req_deps]
        assert "fastapi" in req_names
        assert "typer" in req_names

        # Test pyproject.toml extraction
        pyproject_deps = generator._extract_from_pyproject(temp_project_with_files)
        pyproject_names = [dep["name"] for dep in pyproject_deps]
        assert "aiosqlite" in pyproject_names

        # Ensure no cross-contamination (pyproject not parsed as requirements)
        assert not any("project" in name for name in req_names)  # No TOML sections
        assert not any("[" in name for name in req_names)  # No TOML syntax

    def test_custom_skip_patterns(self, temp_project_with_files):
        """Test custom skip patterns."""
        # Create directories that should be skipped
        (temp_project_with_files / "node_modules").mkdir()
        (temp_project_with_files / "node_modules" / "package.py").write_text(
            "# should be skipped"
        )

        (temp_project_with_files / "custom_skip").mkdir()
        (temp_project_with_files / "custom_skip" / "file.py").write_text(
            "# should be skipped"
        )

        custom_config = SyncFoundationConfig(
            project_analysis=ProjectAnalysis(
                skip_patterns=[
                    "node_modules",
                    "custom_skip",
                ]  # Pattern matching works with substring
            )
        )

        spec_templates_dir = temp_project_with_files / "templates"
        specs_dir = temp_project_with_files / "specs"
        spec_templates_dir.mkdir(exist_ok=True)
        specs_dir.mkdir(exist_ok=True)

        generator = SpecGenerator(spec_templates_dir, specs_dir, AgenticSpecConfig())
        generator.sync_foundation_config = custom_config

        categorization = generator._categorize_files(temp_project_with_files)

        # Check relative paths to see if they contain skipped directories
        all_python_file_paths = []
        for py_file in categorization["python_files"]:
            relative_path = str(
                py_file.relative_to(temp_project_with_files)
                if hasattr(py_file, "relative_to")
                else py_file
            )
            all_python_file_paths.append(relative_path)

        assert not any("node_modules" in f for f in all_python_file_paths)
        assert not any("custom_skip" in f for f in all_python_file_paths)

    def test_config_driven_stdlib_detection(self, temp_project_with_files):
        """Test custom stdlib module configuration."""
        custom_config = SyncFoundationConfig(
            dependency_detection=DependencyDetection(
                stdlib_modules=[
                    "os",
                    "sys",
                    "custom_builtin",
                ]  # Add custom module as stdlib
            )
        )

        spec_templates_dir = temp_project_with_files / "templates"
        specs_dir = temp_project_with_files / "specs"
        spec_templates_dir.mkdir(exist_ok=True)
        specs_dir.mkdir(exist_ok=True)

        generator = SpecGenerator(spec_templates_dir, specs_dir, AgenticSpecConfig())
        generator.sync_foundation_config = custom_config

        # Test stdlib detection
        assert not generator._is_third_party_package("os")  # Standard stdlib
        assert not generator._is_third_party_package("custom_builtin")  # Custom stdlib
        assert generator._is_third_party_package("fastapi")  # Still third-party

    def test_domain_inference_with_custom_patterns(self, temp_project_with_files):
        """Test domain inference with custom domain patterns."""
        custom_config = SyncFoundationConfig(
            project_analysis=ProjectAnalysis(
                domain_patterns={
                    "simple_cli": "Custom {language} CLI tool for {domain}",
                    "full_stack": "Full-stack {language} application with CLI, web UI, and database components for {domain}",
                },
                default_domain="custom business logic",
            )
        )

        spec_templates_dir = temp_project_with_files / "templates"
        specs_dir = temp_project_with_files / "specs"
        spec_templates_dir.mkdir(exist_ok=True)
        specs_dir.mkdir(exist_ok=True)

        generator = SpecGenerator(spec_templates_dir, specs_dir, AgenticSpecConfig())
        generator.sync_foundation_config = custom_config

        # Test full-stack pattern with domain substitution
        full_stack_analysis = {
            "cli_files": ["commands/main.py"],
            "web_ui_files": ["frontend/app.py"],
            "database_files": ["backend/database.py"],
            "api_files": ["services/api.py"],
        }

        domain = generator._infer_domain(full_stack_analysis)
        assert "custom business logic" in domain
        assert "Full-stack Python application" in domain

        # Test simple CLI pattern
        simple_cli_analysis = {
            "cli_files": ["commands/main.py"],
            "web_ui_files": [],
            "database_files": [],
            "api_files": [],
        }

        simple_domain = generator._infer_domain(simple_cli_analysis)
        assert "Custom Python CLI tool" in simple_domain
        assert "custom business logic" in simple_domain


class TestConfigValidationIntegration:
    """Test integration of config validation with CLI commands."""

    @pytest.fixture
    def temp_project(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_validation_warnings_display(self, temp_project):
        """Test that validation warnings are properly displayed during config loading."""
        # Create config with warnings
        config_content = {
            "file_categorization": {
                "cli_patterns": ["main", "cli"],
                "web_ui_patterns": ["main"],  # Duplicate pattern
            },
            "dependency_detection": {
                "requirements_files": ["requirements.txt", "pyproject.toml"],
                "config_files": ["pyproject.toml"],  # Overlap
            },
            "project_analysis": {
                "skip_patterns": ["*"]  # Overly broad
            },
        }

        config_file = temp_project / "test-config.yaml"
        with config_file.open("w") as f:
            yaml.dump(config_content, f)

        spec_templates_dir = temp_project / "templates"
        specs_dir = temp_project / "specs"
        spec_templates_dir.mkdir(exist_ok=True)
        specs_dir.mkdir(exist_ok=True)

        # Capture output during config loading
        with patch("builtins.print") as mock_print:
            generator = SpecGenerator(
                spec_templates_dir,
                specs_dir,
                AgenticSpecConfig(),
                discovery_config_file=config_file,
            )

            # Check that warnings were printed
            print_calls = [call.args[0] for call in mock_print.call_args_list]
            warning_messages = [
                msg for msg in print_calls if "Configuration warnings" in msg
            ]
            assert len(warning_messages) > 0

    def test_config_error_propagation(self, temp_project):
        """Test that config errors are properly propagated to CLI level."""
        # Create config with validation errors
        config_content = {
            "foundation_template_name": "",  # Invalid
            "max_transitive_dependencies": -1,  # Invalid
            "cache_duration_hours": 200,  # Invalid
        }

        config_file = temp_project / "invalid-config.yaml"
        with config_file.open("w") as f:
            yaml.dump(config_content, f)

        spec_templates_dir = temp_project / "templates"
        specs_dir = temp_project / "specs"
        spec_templates_dir.mkdir(exist_ok=True)
        specs_dir.mkdir(exist_ok=True)

        with pytest.raises(ConfigValidationError) as exc_info:
            SpecGenerator(
                spec_templates_dir,
                specs_dir,
                AgenticSpecConfig(),
                discovery_config_file=config_file,
            )

        error_message = str(exc_info.value)
        assert "String should have at least 1 character" in error_message
        assert "Input should be greater than or equal to 0" in error_message
        assert "Input should be less than or equal to 168" in error_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
