"""Tests for the model audit tool."""

from pathlib import Path
import tempfile
from unittest.mock import patch

import pytest

from tools.audit_models import analyze_models_file, generate_report, main


class TestModelAudit:
    """Test the model audit functionality."""

    def test_analyze_models_file_with_mixed_models(self):
        """Test parsing a file with mixed model types."""
        test_content = """
from dataclasses import dataclass
from pydantic import BaseModel
from enum import Enum

@dataclass
class TestDataclass:
    name: str

class TestPydantic(BaseModel):
    name: str

class TestEnum(str, Enum):
    VALUE1 = "value1"

class TestPlain:
    pass
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(test_content)
            f.flush()

            result = analyze_models_file(Path(f.name))

        # Clean up
        Path(f.name).unlink()

        assert len(result["dataclass_models"]) == 1
        assert result["dataclass_models"][0]["name"] == "TestDataclass"

        assert len(result["pydantic_models"]) == 1
        assert result["pydantic_models"][0]["name"] == "TestPydantic"

        assert len(result["enum_models"]) == 1
        assert result["enum_models"][0]["name"] == "TestEnum"

        assert len(result["other_models"]) == 1
        assert result["other_models"][0]["name"] == "TestPlain"

    def test_generate_report_with_inconsistencies(self):
        """Test report generation when inconsistencies exist."""
        classes = {
            "dataclass_models": [{"name": "TestDataclass", "line": 5}],
            "pydantic_models": [{"name": "TestPydantic", "line": 10}],
            "enum_models": [{"name": "TestEnum", "line": 15}],
            "other_models": [],
        }

        report = generate_report(classes)

        assert "INCONSISTENT" in report
        assert "1 dataclass models need conversion" in report
        assert "TestDataclass" in report
        assert "TestPydantic" in report

    def test_generate_report_when_consistent(self):
        """Test report generation when all models are consistent."""
        classes = {
            "dataclass_models": [],
            "pydantic_models": [
                {"name": "TestPydantic1", "line": 5},
                {"name": "TestPydantic2", "line": 10},
            ],
            "enum_models": [{"name": "TestEnum", "line": 15}],
            "other_models": [],
        }

        report = generate_report(classes)

        assert "CONSISTENT" in report
        assert "All models use Pydantic BaseModel" in report

    @patch("tools.audit_models.Path")
    def test_main_missing_file(self, mock_path):
        """Test main function with missing models file."""
        mock_path.return_value.parent.parent.__truediv__.return_value.exists.return_value = False

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    def test_audit_current_models_file(self):
        """Test auditing the actual models.py file."""
        models_file = Path(__file__).parent.parent / "agentic_spec" / "models.py"

        if not models_file.exists():
            pytest.skip("models.py not found")

        classes = analyze_models_file(models_file)

        # Should find our known inconsistencies
        assert len(classes["dataclass_models"]) > 0, "Should find dataclass models"
        assert len(classes["pydantic_models"]) > 0, "Should find Pydantic models"

        # Check for specific models we know exist
        dataclass_names = [m["name"] for m in classes["dataclass_models"]]
        pydantic_names = [m["name"] for m in classes["pydantic_models"]]

        assert "ProgrammingSpec" in dataclass_names
        assert "SpecMetadata" in dataclass_names
        assert "TaskProgress" in pydantic_names
        assert "DependencyModel" in pydantic_names

    def test_report_format(self):
        """Test that generated reports have expected format."""
        classes = {
            "dataclass_models": [{"name": "Test", "line": 1}],
            "pydantic_models": [{"name": "Test2", "line": 2}],
            "enum_models": [{"name": "TestEnum", "line": 3}],
            "other_models": [],
        }

        report = generate_report(classes)

        # Check required sections
        assert "# Model Audit Report" in report
        assert "## Summary" in report
        assert "Total Classes:" in report
        assert "## Consistency Status" in report

        # Check specific counts
        assert "Total Classes:** 3" in report
        assert "Dataclass Models:** 1" in report
        assert "Pydantic Models:** 1" in report

    def test_json_output_structure(self):
        """Test that JSON output has expected structure."""
        test_content = """
from dataclasses import dataclass
from pydantic import BaseModel

@dataclass
class TestDataclass:
    name: str

class TestPydantic(BaseModel):
    name: str
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(test_content)
            f.flush()

            result = analyze_models_file(Path(f.name))

        # Clean up
        Path(f.name).unlink()

        # Verify JSON structure
        expected_keys = [
            "dataclass_models",
            "pydantic_models",
            "enum_models",
            "other_models",
        ]
        assert all(key in result for key in expected_keys)

        # Verify model entries have required fields
        for model in result["dataclass_models"] + result["pydantic_models"]:
            assert "name" in model
            assert "line" in model
            assert "decorators" in model
            assert "bases" in model
