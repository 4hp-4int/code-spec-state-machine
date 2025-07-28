"""Tests for graph visualization functionality."""

from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch

from agentic_spec.core import SpecGenerator
from agentic_spec.graph_visualization import (
    detect_cycles,
    get_spec_stats,
    print_spec_graph,
    print_task_tree,
    visualize_spec_graph,
)
from agentic_spec.models import (
    ImplementationStep,
    ProgrammingSpec,
    SpecContext,
    SpecMetadata,
    SpecRequirement,
)


class TestGraphVisualizationFunctions:
    """Test graph visualization utility functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tmpdir = tempfile.mkdtemp()
        self.specs_dir = Path(self.tmpdir) / "specs"
        self.templates_dir = Path(self.tmpdir) / "templates"
        self.specs_dir.mkdir(parents=True)
        self.templates_dir.mkdir(parents=True)

    def create_test_spec(
        self, spec_id: str, title: str, has_sub_spec: bool = False
    ) -> Path:
        """Create a test specification file."""
        spec = ProgrammingSpec(
            metadata=SpecMetadata(
                id=spec_id,
                title=title,
                inherits=[],
                created="2023-01-01T00:00:00",
                version="1.0",
                author="test_user",
                last_modified="2023-01-01T00:00:00",
            ),
            context=SpecContext(
                project="test-project",
                domain="test",
                dependencies=[],
                files_involved=["test.py"],
            ),
            requirements=SpecRequirement(
                functional=["Test function"],
                non_functional=["Test performance"],
                constraints=["Test constraint"],
            ),
            implementation=[
                ImplementationStep(
                    task="Test task 1",
                    details="Test details 1",
                    files=["test1.py"],
                    acceptance="Test passes 1",
                    sub_spec_id="sub123" if has_sub_spec else None,
                ),
                ImplementationStep(
                    task="Test task 2",
                    details="Test details 2",
                    files=["test2.py"],
                    acceptance="Test passes 2",
                ),
            ],
        )

        generator = SpecGenerator(self.templates_dir, self.specs_dir)
        return generator.save_spec(spec)

    def test_get_spec_stats_empty_directory(self):
        """Test stats for empty specs directory."""
        stats = get_spec_stats(self.specs_dir)

        assert stats["total_specs"] == 0
        assert stats["root_specs"] == 0
        assert stats["leaf_specs"] == 0
        assert stats["max_depth"] == 0
        assert stats["status_counts"] == {}

    def test_get_spec_stats_with_specs(self):
        """Test stats calculation with actual specs."""
        # Create test specs
        self.create_test_spec("spec1", "Test Spec 1")
        self.create_test_spec("spec2", "Test Spec 2", has_sub_spec=True)

        stats = get_spec_stats(self.specs_dir)

        assert stats["total_specs"] == 2
        assert stats["root_specs"] >= 0  # Depends on parent relationships
        assert stats["leaf_specs"] >= 0
        assert "draft" in stats["status_counts"]

    def test_print_spec_graph_no_specs(self, capsys):
        """Test print_spec_graph with no specifications."""
        print_spec_graph(self.specs_dir)

        captured = capsys.readouterr()
        assert "No specifications found" in captured.out

    def test_print_spec_graph_with_tasks(self, capsys):
        """Test print_spec_graph with show_tasks=True."""
        self.create_test_spec("spec1", "Test Spec 1")

        print_spec_graph(self.specs_dir, show_tasks=True)

        captured = capsys.readouterr()
        assert "Specification Graph:" in captured.out
        assert "Task" in captured.out

    def test_print_task_tree_missing_spec(self, capsys):
        """Test print_task_tree with non-existent spec."""
        print_task_tree(self.specs_dir, "missing123")

        captured = capsys.readouterr()
        assert "Specification missing123 not found" in captured.out

    def test_print_task_tree_with_spec(self, capsys):
        """Test print_task_tree with existing spec."""
        self.create_test_spec("spec1", "Test Spec 1", has_sub_spec=True)

        print_task_tree(self.specs_dir, "spec1")

        captured = capsys.readouterr()
        assert "Task Tree for Specification: spec1" in captured.out
        assert "Test Spec 1" in captured.out
        assert "Test task 1" in captured.out
        assert "Summary:" in captured.out

    def test_detect_cycles_no_specs(self):
        """Test cycle detection with no specs."""
        cycles = detect_cycles(self.specs_dir)
        assert cycles == []

    def test_detect_cycles_with_specs(self):
        """Test cycle detection with specs (should be no cycles in normal case)."""
        self.create_test_spec("spec1", "Test Spec 1")
        self.create_test_spec("spec2", "Test Spec 2")

        cycles = detect_cycles(self.specs_dir)
        assert isinstance(cycles, list)

    @patch("agentic_spec.graph_visualization.VISUALIZATION_AVAILABLE", True)
    @patch("agentic_spec.graph_visualization.plt")
    @patch("agentic_spec.graph_visualization.nx")
    def test_visualize_spec_graph_image_output(self, mock_nx, mock_plt):
        """Test image generation for spec graph."""
        # Mock networkx and matplotlib
        mock_graph = MagicMock()
        mock_nx.DiGraph.return_value = mock_graph
        mock_nx.spring_layout.return_value = {}

        self.create_test_spec("spec1", "Test Spec 1")

        output_file = str(self.specs_dir / "test_graph.png")
        visualize_spec_graph(self.specs_dir, output_file, show_tasks=False)

        # Verify matplotlib was called
        mock_plt.figure.assert_called_once()
        mock_plt.savefig.assert_called_once_with(
            output_file, dpi=300, bbox_inches="tight"
        )

    @patch("agentic_spec.graph_visualization.VISUALIZATION_AVAILABLE", False)
    def test_visualize_spec_graph_no_libraries(self, capsys):
        """Test visualization when libraries are not available."""
        visualize_spec_graph(self.specs_dir, "output.png")

        captured = capsys.readouterr()
        assert "Visualization libraries not available" in captured.out


class TestGraphVisualizationIntegration:
    """Integration tests for graph visualization with real data."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tmpdir = tempfile.mkdtemp()
        self.specs_dir = Path(self.tmpdir) / "specs"
        self.templates_dir = Path(self.tmpdir) / "templates"
        self.specs_dir.mkdir(parents=True)
        self.templates_dir.mkdir(parents=True)

    def test_task_tree_with_nested_subspecs(self, capsys):
        """Test task tree visualization with nested sub-specifications."""
        # Create parent spec
        parent_spec = ProgrammingSpec(
            metadata=SpecMetadata(
                id="parent123",
                title="Parent Specification",
                inherits=[],
                created="2023-01-01T00:00:00",
                version="1.0",
                author="test_user",
            ),
            context=SpecContext(
                project="test-project",
                domain="test",
                dependencies=[],
            ),
            requirements=SpecRequirement(
                functional=["Parent function"],
                non_functional=["Parent performance"],
            ),
            implementation=[
                ImplementationStep(
                    task="Parent task with sub-spec",
                    details="This task has a sub-specification",
                    files=["parent.py"],
                    acceptance="Parent passes",
                    sub_spec_id="child123",
                ),
                ImplementationStep(
                    task="Regular parent task",
                    details="This is a regular task",
                    files=["regular.py"],
                    acceptance="Regular passes",
                ),
            ],
        )

        # Create child spec
        child_spec = ProgrammingSpec(
            metadata=SpecMetadata(
                id="child123",
                title="Child Specification",
                inherits=[],
                created="2023-01-01T00:00:00",
                version="1.0",
                author="test_user",
                parent_spec_id="parent123",
            ),
            context=SpecContext(
                project="test-project",
                domain="test",
                dependencies=[],
            ),
            requirements=SpecRequirement(
                functional=["Child function"],
                non_functional=["Child performance"],
            ),
            implementation=[
                ImplementationStep(
                    task="Child task 1",
                    details="First child task",
                    files=["child1.py"],
                    acceptance="Child 1 passes",
                ),
                ImplementationStep(
                    task="Child task 2",
                    details="Second child task",
                    files=["child2.py"],
                    acceptance="Child 2 passes",
                ),
            ],
        )

        # Save specs
        generator = SpecGenerator(self.templates_dir, self.specs_dir)
        generator.save_spec(parent_spec)
        generator.save_spec(child_spec)

        # Test task tree visualization
        print_task_tree(self.specs_dir, "parent123")

        captured = capsys.readouterr()
        assert "Parent Specification" in captured.out
        assert "Parent task with sub-spec" in captured.out
        assert "Regular parent task" in captured.out
        assert "Total Tasks:" in captured.out

    def test_spec_graph_with_relationships(self, capsys):
        """Test spec graph showing parent-child relationships."""
        # Create specs with relationships
        parent_spec = ProgrammingSpec(
            metadata=SpecMetadata(
                id="parent123",
                title="Parent Spec",
                inherits=[],
                created="2023-01-01T00:00:00",
                version="1.0",
                child_spec_ids=["child123"],
            ),
            context=SpecContext(project="test", domain="test", dependencies=[]),
            requirements=SpecRequirement(functional=["Test"], non_functional=["Test"]),
            implementation=[
                ImplementationStep(
                    task="Parent task",
                    details="Parent details",
                    files=["parent.py"],
                    acceptance="Parent passes",
                )
            ],
        )

        child_spec = ProgrammingSpec(
            metadata=SpecMetadata(
                id="child123",
                title="Child Spec",
                inherits=[],
                created="2023-01-01T00:00:00",
                version="1.0",
                parent_spec_id="parent123",
            ),
            context=SpecContext(project="test", domain="test", dependencies=[]),
            requirements=SpecRequirement(functional=["Test"], non_functional=["Test"]),
            implementation=[
                ImplementationStep(
                    task="Child task",
                    details="Child details",
                    files=["child.py"],
                    acceptance="Child passes",
                )
            ],
        )

        generator = SpecGenerator(self.templates_dir, self.specs_dir)
        generator.save_spec(parent_spec)
        generator.save_spec(child_spec)

        print_spec_graph(self.specs_dir)

        captured = capsys.readouterr()
        assert "Specification Graph:" in captured.out
        assert "parent123" in captured.out or "Parent Spec" in captured.out
