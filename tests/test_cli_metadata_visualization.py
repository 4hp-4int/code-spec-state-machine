"""Integration tests for CLI metadata and visualization commands."""

from pathlib import Path
import tempfile
from unittest.mock import patch

from typer.testing import CliRunner

from agentic_spec.cli_core import core_app
from agentic_spec.core import SpecGenerator
from agentic_spec.models import (
    ImplementationStep,
    ProgrammingSpec,
    SpecContext,
    SpecMetadata,
    SpecRequirement,
)


class TestCLIMetadataCommands:
    """Test CLI commands for metadata display."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.tmpdir = tempfile.mkdtemp()
        self.specs_dir = Path(self.tmpdir) / "specs"
        self.templates_dir = Path(self.tmpdir) / "templates"
        self.specs_dir.mkdir(parents=True)
        self.templates_dir.mkdir(parents=True)

    def create_test_spec(self, spec_id: str = "test123") -> Path:
        """Create a test specification with enhanced metadata."""
        spec = ProgrammingSpec(
            metadata=SpecMetadata(
                id=spec_id,
                title="Test Specification for CLI",
                inherits=["base-template"],
                created="2023-01-01T12:00:00",
                version="1.0",
                status="draft",
                author="test_author",
                last_modified="2023-01-02T12:00:00",
                parent_spec_id=None,
                child_spec_ids=["child1", "child2"],
            ),
            context=SpecContext(
                project="test-project",
                domain="CLI testing",
                dependencies=[
                    {"name": "pytest", "version": "7.0.0"},
                    {"name": "typer", "version": "0.12.0"},
                ],
                files_involved=["test.py", "cli.py"],
            ),
            requirements=SpecRequirement(
                functional=[
                    "Display enhanced metadata",
                    "Show task hierarchies",
                ],
                non_functional=[
                    "Fast response time",
                    "Clear output formatting",
                ],
                constraints=["Must be backward compatible"],
            ),
            implementation=[
                ImplementationStep(
                    task="Implement metadata display",
                    details="Add enhanced metadata to CLI output",
                    files=["cli.py"],
                    acceptance="Metadata shown correctly",
                    sub_spec_id="sub123",
                ),
                ImplementationStep(
                    task="Add task tree visualization",
                    details="Implement hierarchical task display",
                    files=["visualization.py"],
                    acceptance="Task tree displays properly",
                ),
            ],
        )

        generator = SpecGenerator(self.templates_dir, self.specs_dir)
        return generator.save_spec(spec)

    def test_spec_detail_command(self):
        """Test the spec-detail command shows enhanced metadata."""
        self.create_test_spec("test123")

        result = self.runner.invoke(
            core_app,
            [
                "spec-detail",
                "test123",
                "--specs-dir",
                str(self.specs_dir),
                "--templates-dir",
                str(self.templates_dir),
            ],
        )

        assert result.exit_code == 0
        output = result.stdout

        # Check that enhanced metadata is displayed
        assert "📋 Specification Details: test123" in output
        assert "👤 Author: test_author" in output
        assert "📅 Created: 2023-01-01T12:00:00" in output
        assert (
            "🔄 Last Modified:" in output and "2025-07-28" in output
        )  # Gets updated on save
        assert "📊 Status: draft" in output
        assert "🔖 Version: 1.0" in output
        assert "🧬 Inherits from: base-template" in output
        assert "⬇️  Child Specs:" in output
        assert "child1" in output
        assert "child2" in output

        # Check context information
        assert "📁 Context:" in output
        assert "Project: test-project" in output
        assert "Domain: CLI testing" in output
        assert "Dependencies: 2" in output

        # Check implementation with sub-spec indicators
        assert "⚙️  Implementation:" in output
        assert "📦 Implement metadata display" in output  # Has sub-spec
        assert "Sub-spec: sub123" in output
        assert "📄 Add task tree visualization" in output  # No sub-spec

    def test_spec_detail_command_missing_spec(self):
        """Test spec-detail command with non-existent spec."""
        result = self.runner.invoke(
            core_app,
            [
                "spec-detail",
                "missing123",
                "--specs-dir",
                str(self.specs_dir),
                "--templates-dir",
                str(self.templates_dir),
            ],
        )

        assert result.exit_code == 1
        assert "Specification missing123 not found" in result.stdout

    def test_graph_command_basic(self):
        """Test the basic graph command."""
        self.create_test_spec("test123")

        result = self.runner.invoke(
            core_app,
            ["graph", "--specs-dir", str(self.specs_dir)],
        )

        assert result.exit_code == 0
        output = result.stdout

        assert "📊 Specification Graph:" in output
        assert "📈 Statistics:" in output
        assert "Total specs:" in output
        assert "Status breakdown:" in output

    def test_graph_command_with_tasks(self):
        """Test the graph command with --show-tasks flag."""
        self.create_test_spec("test123")

        result = self.runner.invoke(
            core_app,
            ["graph", "--specs-dir", str(self.specs_dir), "--show-tasks"],
        )

        assert result.exit_code == 0
        output = result.stdout

        assert "📊 Specification Graph:" in output
        assert "Task" in output  # Should show tasks

    @patch("agentic_spec.graph_visualization.VISUALIZATION_AVAILABLE", True)
    @patch("agentic_spec.graph_visualization.plt")
    @patch("agentic_spec.graph_visualization.nx")
    def test_graph_command_image_output(self, mock_nx, mock_plt):
        """Test graph command with image output."""
        # Mock the visualization libraries
        mock_graph = mock_nx.DiGraph.return_value
        mock_nx.spring_layout.return_value = {}

        self.create_test_spec("test123")
        output_file = str(self.specs_dir / "test_output.png")

        result = self.runner.invoke(
            core_app,
            [
                "graph",
                "--specs-dir",
                str(self.specs_dir),
                "--output",
                output_file,
            ],
        )

        assert result.exit_code == 0
        # Should call matplotlib for image generation
        mock_plt.figure.assert_called_once()
        mock_plt.savefig.assert_called_once()

    def test_task_tree_command(self):
        """Test the task-tree command."""
        self.create_test_spec("test123")

        result = self.runner.invoke(
            core_app,
            ["task-tree", "test123", "--specs-dir", str(self.specs_dir)],
        )

        assert result.exit_code == 0
        output = result.stdout

        assert "📋 Task Tree for Specification: test123" in output
        assert "🎯 Root: Test Specification for CLI" in output
        assert "👤 Author: test_author" in output
        assert "📊 Status: draft" in output
        assert "Implement metadata display" in output
        assert "Add task tree visualization" in output
        assert "📊 Summary:" in output
        assert "Total Tasks:" in output

    def test_task_tree_command_missing_spec(self):
        """Test task-tree command with non-existent spec."""
        result = self.runner.invoke(
            core_app,
            ["task-tree", "missing123", "--specs-dir", str(self.specs_dir)],
        )

        assert result.exit_code == 0  # Command succeeds but shows error message
        assert "Specification missing123 not found" in result.stdout

    @patch("agentic_spec.graph_visualization.VISUALIZATION_AVAILABLE", True)
    @patch("agentic_spec.graph_visualization.plt")
    @patch("agentic_spec.graph_visualization.nx")
    def test_task_tree_image_output(self, mock_nx, mock_plt):
        """Test task-tree command with image output."""
        mock_graph = mock_nx.DiGraph.return_value
        mock_nx.spring_layout.return_value = {}

        self.create_test_spec("test123")
        output_file = str(self.specs_dir / "task_tree.png")

        result = self.runner.invoke(
            core_app,
            [
                "task-tree",
                "test123",
                "--specs-dir",
                str(self.specs_dir),
                "--output",
                output_file,
            ],
        )

        assert result.exit_code == 0
        assert "Task tree visualization saved to" in result.stdout
        mock_plt.figure.assert_called_once()
        mock_plt.savefig.assert_called_once()


class TestCLIBackwardCompatibility:
    """Test backward compatibility of CLI commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.tmpdir = tempfile.mkdtemp()
        self.specs_dir = Path(self.tmpdir) / "specs"
        self.templates_dir = Path(self.tmpdir) / "templates"
        self.specs_dir.mkdir(parents=True)
        self.templates_dir.mkdir(parents=True)

    def create_legacy_spec_file(self) -> Path:
        """Create a legacy spec file without new metadata fields."""
        spec_file = self.specs_dir / "2023-01-01-legacy123.yaml"
        yaml_content = """
metadata:
  id: legacy123
  title: Legacy Specification
  inherits: []
  created: '2023-01-01T00:00:00'
  version: '1.0'
  status: draft
context:
  project: legacy-project
  domain: legacy testing
  dependencies: []
requirements:
  functional: ['Legacy function']
  non_functional: ['Legacy performance']
implementation:
  - task: Legacy task
    details: Legacy task details
    files: [legacy.py]
    acceptance: Legacy test passes
"""
        spec_file.write_text(yaml_content)
        return spec_file

    def test_spec_detail_legacy_spec(self):
        """Test spec-detail command with legacy spec (no new metadata fields)."""
        self.create_legacy_spec_file()

        result = self.runner.invoke(
            core_app,
            [
                "spec-detail",
                "legacy123",
                "--specs-dir",
                str(self.specs_dir),
                "--templates-dir",
                str(self.templates_dir),
            ],
        )

        assert result.exit_code == 0
        output = result.stdout

        # Should handle missing fields gracefully
        assert "📋 Specification Details: legacy123" in output
        assert "👤 Author: N/A" in output  # Should show N/A for missing author
        assert (
            "🔄 Last Modified: N/A" in output
        )  # Should show N/A for missing last_modified
        assert "📊 Status: draft" in output
        assert "Legacy Specification" in output

    def test_graph_commands_with_legacy_specs(self):
        """Test graph commands work with legacy specifications."""
        self.create_legacy_spec_file()

        # Test basic graph command
        result = self.runner.invoke(
            core_app,
            ["graph", "--specs-dir", str(self.specs_dir)],
        )

        assert result.exit_code == 0
        assert "📊 Specification Graph:" in result.stdout

        # Test task-tree command
        result = self.runner.invoke(
            core_app,
            ["task-tree", "legacy123", "--specs-dir", str(self.specs_dir)],
        )

        assert result.exit_code == 0
        assert "📋 Task Tree for Specification: legacy123" in result.stdout
        assert "👤 Author: N/A" in result.stdout  # Should handle missing author


class TestCLIOutputFormats:
    """Test different output formats and edge cases."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.tmpdir = tempfile.mkdtemp()
        self.specs_dir = Path(self.tmpdir) / "specs"
        self.templates_dir = Path(self.tmpdir) / "templates"
        self.specs_dir.mkdir(parents=True)
        self.templates_dir.mkdir(parents=True)

    def test_empty_specs_directory(self):
        """Test CLI commands with empty specs directory."""
        result = self.runner.invoke(
            core_app,
            ["graph", "--specs-dir", str(self.specs_dir)],
        )

        assert result.exit_code == 0
        assert "No specifications found" in result.stdout

    @patch("agentic_spec.graph_visualization.VISUALIZATION_AVAILABLE", False)
    def test_image_output_without_libraries(self):
        """Test image output when visualization libraries are not available."""
        result = self.runner.invoke(
            core_app,
            [
                "graph",
                "--specs-dir",
                str(self.specs_dir),
                "--output",
                "test.png",
            ],
        )

        assert result.exit_code == 0
        assert "Visualization libraries not available" in result.stdout
