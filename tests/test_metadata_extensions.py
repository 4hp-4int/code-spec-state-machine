"""Tests for metadata extensions in models and core functionality."""

from datetime import datetime
from pathlib import Path
import tempfile
from unittest.mock import patch

from agentic_spec.core import SpecGenerator
from agentic_spec.models import (
    ImplementationStep,
    ProgrammingSpec,
    SpecContext,
    SpecMetadata,
    SpecRequirement,
)


class TestSpecMetadata:
    """Test metadata model extensions."""

    def test_spec_metadata_new_fields(self):
        """Test that new metadata fields are properly handled."""
        metadata = SpecMetadata(
            id="test123",
            title="Test Spec",
            inherits=[],
            created=datetime.now().isoformat(),
            version="1.0",
            status="draft",
            parent_spec_id=None,
            child_spec_ids=None,
            author="test_user",
            last_modified=datetime.now().isoformat(),
        )

        assert metadata.author == "test_user"
        assert metadata.last_modified is not None

    def test_spec_metadata_backward_compatibility(self):
        """Test that metadata works without new fields."""
        metadata = SpecMetadata(
            id="test123",
            title="Test Spec",
            inherits=[],
            created=datetime.now().isoformat(),
            version="1.0",
        )

        assert metadata.author is None
        assert metadata.last_modified is None

    def test_spec_metadata_to_dict_includes_new_fields(self):
        """Test that to_dict includes new fields."""
        metadata = SpecMetadata(
            id="test123",
            title="Test Spec",
            inherits=[],
            created=datetime.now().isoformat(),
            version="1.0",
            author="test_user",
            last_modified=datetime.now().isoformat(),
        )

        data = metadata.model_dump(exclude_none=True)
        assert "author" in data
        assert "last_modified" in data
        assert data["author"] == "test_user"


class TestSpecGeneration:
    """Test specification generation with new metadata."""

    def test_spec_generation_includes_author(self):
        """Test that generated specs include author from environment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            specs_dir = Path(tmpdir) / "specs"
            templates_dir = Path(tmpdir) / "templates"
            specs_dir.mkdir()
            templates_dir.mkdir()

            generator = SpecGenerator(templates_dir, specs_dir)

            with patch.dict("os.environ", {"USER": "test_author"}):
                # Use the async generate_spec method which creates actual ProgrammingSpec
                import asyncio

                spec = asyncio.run(
                    generator.generate_spec("Test prompt", project_name="test-project")
                )

            assert spec.metadata.author == "test_author"

    def test_spec_save_updates_last_modified(self):
        """Test that saving a spec updates last_modified timestamp."""
        with tempfile.TemporaryDirectory() as tmpdir:
            specs_dir = Path(tmpdir) / "specs"
            templates_dir = Path(tmpdir) / "templates"
            specs_dir.mkdir()
            templates_dir.mkdir()

            generator = SpecGenerator(templates_dir, specs_dir)

            # Create a spec
            spec = ProgrammingSpec(
                metadata=SpecMetadata(
                    id="test123",
                    title="Test Spec",
                    inherits=[],
                    created=datetime.now().isoformat(),
                    version="1.0",
                    author="test_user",
                    last_modified=None,  # Initially None
                ),
                context=SpecContext(
                    project="test",
                    domain="test",
                    dependencies=[],
                    files_involved=[],
                ),
                requirements=SpecRequirement(
                    functional=["Test"],
                    non_functional=["Test"],
                    constraints=[],
                ),
                implementation=[
                    ImplementationStep(
                        task="Test task",
                        details="Test details",
                        files=["test.py"],
                        acceptance="Test passes",
                    )
                ],
            )

            # Save should update last_modified
            generator.save_spec(spec)
            assert spec.metadata.last_modified is not None

    def test_spec_load_handles_missing_fields(self):
        """Test that loading specs handles missing new fields gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            specs_dir = Path(tmpdir) / "specs"
            templates_dir = Path(tmpdir) / "templates"
            specs_dir.mkdir()
            templates_dir.mkdir()

            # Create a YAML file without new fields
            spec_file = specs_dir / "test-spec.yaml"
            yaml_content = """
metadata:
  id: test123
  title: Test Spec
  inherits: []
  created: '2023-01-01T00:00:00'
  version: '1.0'
  status: draft
context:
  project: test
  domain: test
  dependencies: []
requirements:
  functional: ['Test']
  non_functional: ['Test']
implementation:
  - task: Test task
    details: Test details
    files: [test.py]
    acceptance: Test passes
"""
            spec_file.write_text(yaml_content)

            generator = SpecGenerator(templates_dir, specs_dir)
            spec = generator.load_spec(spec_file)

            # Should load without error and have None values for new fields
            assert spec.metadata.author is None
            assert spec.metadata.last_modified is None
