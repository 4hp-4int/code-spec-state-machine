"""Tests for enhanced codebase analysis features.

Tests the enhanced dependency detection, file categorization, and
architectural pattern detection in SpecGenerator.
"""

from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from agentic_spec.config import AgenticSpecConfig
from agentic_spec.core import SpecGenerator


class TestEnhancedDependencyDetection:
    """Test enhanced dependency detection from multiple sources."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory with test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create pyproject.toml
            pyproject_content = """
[project]
dependencies = [
    "fastapi>=0.100.0",
    "uvicorn[standard]>=0.20.0",
    "pydantic>=2.0.0"
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "black>=23.0.0"
]
"""
            (project_path / "pyproject.toml").write_text(pyproject_content)

            # Create requirements.txt
            requirements_content = """
aiosqlite>=0.19.0
typer>=0.9.0
# Development dependencies
pytest-asyncio>=0.21.0
"""
            (project_path / "requirements.txt").write_text(requirements_content)

            # Create setup.py
            setup_content = """
from setuptools import setup

setup(
    name="test-project",
    install_requires=[
        "click>=8.0.0",
        "jinja2>=3.0.0"
    ]
)
"""
            (project_path / "setup.py").write_text(setup_content)

            # Create Python files with various imports
            src_dir = project_path / "src"
            src_dir.mkdir()

            main_content = """
import asyncio
import sqlite3
from fastapi import FastAPI
from typing import Dict, List
import custom_module
"""
            (src_dir / "main.py").write_text(main_content)

            yield project_path

    @pytest.fixture
    def spec_generator(self, temp_project):
        """Create a SpecGenerator instance for testing."""
        spec_templates_dir = temp_project / "templates"
        specs_dir = temp_project / "specs"
        config = AgenticSpecConfig()

        return SpecGenerator(spec_templates_dir, specs_dir, config)

    def test_pyproject_dependency_extraction(self, spec_generator, temp_project):
        """Test extraction of dependencies from pyproject.toml."""
        dependencies = spec_generator._extract_from_pyproject(temp_project)

        # Check main dependencies
        main_deps = [
            dep["name"] for dep in dependencies if dep["source"] == "pyproject.toml"
        ]
        assert "fastapi" in main_deps
        assert "uvicorn" in main_deps
        assert "pydantic" in main_deps

        # Check optional dependencies
        optional_deps = [dep for dep in dependencies if "optional" in dep["source"]]
        assert len(optional_deps) >= 2
        assert any(dep["name"] == "pytest" for dep in optional_deps)

    def test_requirements_dependency_extraction(self, spec_generator, temp_project):
        """Test extraction of dependencies from requirements.txt."""
        dependencies = spec_generator._extract_from_requirements(temp_project)

        dep_names = [dep["name"] for dep in dependencies]
        assert "aiosqlite" in dep_names
        assert "typer" in dep_names
        assert "pytest-asyncio" in dep_names

    def test_setup_py_dependency_extraction(self, spec_generator, temp_project):
        """Test extraction of dependencies from setup.py."""
        dependencies = spec_generator._extract_from_setup_py(temp_project)

        dep_names = [dep["name"] for dep in dependencies]
        assert "click" in dep_names
        assert "jinja2" in dep_names

    def test_dependency_spec_parsing(self, spec_generator):
        """Test parsing of various dependency specification formats."""
        test_cases = [
            ("fastapi>=0.100.0", ("fastapi", ">=0.100.0")),
            ("uvicorn[standard]>=0.20.0", ("uvicorn", ">=0.20.0")),
            ("pytest==7.4.0", ("pytest", "==7.4.0")),
            ("requests", ("requests", "latest")),
            ("django>=4.0,<5.0", ("django", ">=4.0,<5.0")),
        ]

        for dep_spec, expected in test_cases:
            name, version = spec_generator._parse_dependency_spec(dep_spec)
            assert name == expected[0]
            assert version == expected[1]

    def test_third_party_package_detection(self, spec_generator):
        """Test detection of third-party vs stdlib packages."""
        # Standard library modules
        assert not spec_generator._is_third_party_package("os")
        assert not spec_generator._is_third_party_package("sys")
        assert not spec_generator._is_third_party_package("pathlib")
        assert not spec_generator._is_third_party_package("asyncio")

        # Third-party packages
        assert spec_generator._is_third_party_package("fastapi")
        assert spec_generator._is_third_party_package("django")
        assert spec_generator._is_third_party_package("requests")

    @patch("importlib.metadata.distribution")
    def test_transitive_dependency_detection(self, mock_distribution, spec_generator):
        """Test detection of transitive dependencies."""
        # Mock the distribution metadata
        mock_dist = MagicMock()
        mock_dist.requires = [
            "starlette>=0.27.0",
            "pydantic>=1.6.2",
            "typing-extensions>=4.5.0",
        ]
        mock_distribution.return_value = mock_dist

        transitive_deps = spec_generator._detect_transitive_dependencies("fastapi")

        assert "starlette" in transitive_deps
        assert "pydantic" in transitive_deps
        assert "typing-extensions" in transitive_deps


class TestEnhancedFileAnalysis:
    """Test enhanced file categorization and content analysis."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project with diverse file types."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create directory structure
            (project_path / "src").mkdir()
            (project_path / "tests").mkdir()
            (project_path / "web_ui").mkdir()
            (project_path / "migrations").mkdir()
            (project_path / "docs").mkdir()

            # CLI files
            cli_content = """
import typer
from typing import Optional

app = typer.Typer()

@app.command()
def main(name: str = typer.Argument(...)):
    print(f"Hello {name}")
"""
            (project_path / "src" / "cli.py").write_text(cli_content)

            # Web UI files
            web_content = """
from fastapi import FastAPI, HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def read_root():
    return HTMLResponse("<h1>Hello World</h1>")
"""
            (project_path / "web_ui" / "main.py").write_text(web_content)

            # Database files
            db_content = """
import aiosqlite
import sqlite3
from typing import List

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def create_tables(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL
                )
            ''')
"""
            (project_path / "src" / "database.py").write_text(db_content)

            # Migration files
            migration_content = """
# Migration: Add user preferences table
# Description: Adds table for storing user preferences

async def upgrade(connection):
    await connection.execute('''
        CREATE TABLE user_preferences (
            id INTEGER PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            key TEXT NOT NULL,
            value TEXT
        )
    ''')

async def downgrade(connection):
    await connection.execute('DROP TABLE user_preferences')
"""
            (project_path / "migrations" / "001_add_preferences.py").write_text(
                migration_content
            )

            # Test files
            test_content = """
import pytest
from src.cli import main

def test_main():
    assert True

class TestCLI:
    def test_command(self):
        pass
"""
            (project_path / "tests" / "test_cli.py").write_text(test_content)

            # Config files
            (project_path / "pyproject.toml").write_text("[project]\nname = 'test'")
            (project_path / "requirements.txt").write_text("fastapi>=0.100.0")

            # Templates
            (project_path / "web_ui" / "template.html").write_text(
                "<html><body>Test</body></html>"
            )
            (project_path / "web_ui" / "styles.css").write_text("body { margin: 0; }")
            (project_path / "web_ui" / "script.js").write_text("console.log('test');")

            # Documentation
            (project_path / "README.md").write_text("# Test Project")
            (project_path / "docs" / "guide.md").write_text("# Guide")

            # Build files
            (project_path / "Makefile").write_text("all:\n\techo 'build'")
            (project_path / "Dockerfile").write_text("FROM python:3.12")

            # Database files
            (project_path / "data.db").write_text("")
            (project_path / "backup.sqlite").write_text("")

            yield project_path

    @pytest.fixture
    def spec_generator(self, temp_project):
        """Create a SpecGenerator instance for testing."""
        spec_templates_dir = temp_project / "templates"
        specs_dir = temp_project / "specs"
        config = AgenticSpecConfig()

        return SpecGenerator(spec_templates_dir, specs_dir, config)

    def test_file_categorization(self, spec_generator, temp_project):
        """Test comprehensive file categorization."""
        categorization = spec_generator._categorize_files(temp_project)

        # Check that basic categorization works
        assert "cli_files" in categorization
        assert "web_ui_files" in categorization
        assert "database_files" in categorization
        assert "migration_files" in categorization
        assert "test_files" in categorization
        assert "config_files" in categorization
        assert "documentation_files" in categorization
        assert "build_files" in categorization
        assert "statistics" in categorization

        # Check that we have non-empty results for key categories
        stats = categorization["statistics"]
        assert isinstance(stats, dict)
        assert stats["python_files"] >= 4  # cli, web, db, migration files

        # Check some specific files exist in correct categories
        all_python_files = [str(f) for f in categorization["python_files"]]

        # Should find our test Python files
        assert any("cli.py" in f for f in all_python_files)
        assert any("main.py" in f for f in all_python_files)
        assert any("database.py" in f for f in all_python_files)
        assert any("001_add_preferences.py" in f for f in all_python_files)
        assert any("test_cli.py" in f for f in all_python_files)

        # Check non-Python files
        web_files = [str(Path(f)) for f in categorization["web_ui_files"]]
        assert any("template.html" in f for f in web_files)
        assert any("styles.css" in f for f in web_files)
        assert any("script.js" in f for f in web_files)

        config_files = [str(Path(f)) for f in categorization["config_files"]]
        assert any("pyproject.toml" in f for f in config_files)

        doc_files = [str(Path(f)) for f in categorization["documentation_files"]]
        assert any("README.md" in f for f in doc_files)

        build_files = [str(Path(f)) for f in categorization["build_files"]]
        assert any("Makefile" in f for f in build_files)

    def test_file_content_analysis(self, spec_generator, temp_project):
        """Test content-based file analysis."""
        # Test CLI file analysis
        cli_file = temp_project / "src" / "cli.py"
        indicators = spec_generator._analyze_file_content(cli_file)
        assert "typer" in indicators

        # Test web UI file analysis
        web_file = temp_project / "web_ui" / "main.py"
        indicators = spec_generator._analyze_file_content(web_file)
        assert "fastapi" in indicators

        # Test database file analysis
        db_file = temp_project / "src" / "database.py"
        indicators = spec_generator._analyze_file_content(db_file)
        assert "sqlite" in indicators
        assert "async def" in indicators

        # Test migration file analysis
        migration_file = temp_project / "migrations" / "001_add_preferences.py"
        indicators = spec_generator._analyze_file_content(migration_file)
        assert "migration" in indicators

        # Test test file analysis
        test_file = temp_project / "tests" / "test_cli.py"
        indicators = spec_generator._analyze_file_content(test_file)
        assert "pytest" in indicators

    def test_skip_patterns(self, spec_generator, temp_project):
        """Test that skip patterns correctly exclude unwanted directories."""
        # Create .venv directory with files
        venv_dir = temp_project / ".venv"
        venv_dir.mkdir()
        (venv_dir / "lib").mkdir()
        (venv_dir / "lib" / "python.py").write_text("# virtual env file")

        # Create __pycache__ directory
        cache_dir = temp_project / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "module.pyc").write_text("")

        categorization = spec_generator._categorize_files(temp_project)

        # Check that venv files are excluded
        all_python_files = [str(f) for f in categorization["python_files"]]
        assert not any(".venv" in f for f in all_python_files)
        assert not any("__pycache__" in f for f in all_python_files)

    def test_dependency_categorization(self, spec_generator):
        """Test dependency categorization logic."""
        test_cases = [
            ("fastapi", "web", "Web framework: fastapi"),
            ("aiosqlite", "database", "Database: aiosqlite"),
            ("jinja2", "templates", "Template engine: jinja2"),
            ("pytest", "testing", "Testing framework: pytest"),
            ("openai", "ai", "AI integration: openai"),
            ("typer", "cli", "CLI framework: typer"),
            ("networkx", "visualization", "Graph/visualization: networkx"),
            ("unknown-package", "core", "Core dependency: unknown-package"),
        ]

        for package_name, expected_category, expected_description in test_cases:
            result = spec_generator._categorize_dependency(package_name)
            assert result["category"] == expected_category
            assert result["description"] == expected_description


class TestArchitecturalPatternDetection:
    """Test detection of architectural patterns and project structure."""

    @pytest.fixture
    def spec_generator(self):
        """Create a minimal SpecGenerator instance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            spec_templates_dir = Path(temp_dir) / "templates"
            specs_dir = Path(temp_dir) / "specs"
            config = AgenticSpecConfig()
            yield SpecGenerator(spec_templates_dir, specs_dir, config)

    def test_domain_inference(self, spec_generator):
        """Test project domain inference from file analysis."""
        # Full-stack application
        full_stack_analysis = {
            "web_ui_files": ["web_ui/main.py", "templates/index.html"],
            "database_files": ["db/models.py", "migrations/001_init.py"],
            "cli_files": ["cli/main.py"],
            "test_files": ["tests/test_web.py"],
        }
        domain = spec_generator._infer_domain(full_stack_analysis)
        assert "Full-stack Python application" in domain
        assert "CLI, web UI, and database" in domain

        # CLI with web UI only
        web_cli_analysis = {
            "web_ui_files": ["web_ui/main.py"],
            "database_files": [],
            "cli_files": ["cli/main.py"],
            "test_files": [],
        }
        domain = spec_generator._infer_domain(web_cli_analysis)
        assert "Python CLI tool with web UI" in domain

        # CLI with database only
        db_cli_analysis = {
            "web_ui_files": [],
            "database_files": ["db/models.py"],
            "cli_files": ["cli/main.py"],
            "test_files": [],
        }
        domain = spec_generator._infer_domain(db_cli_analysis)
        assert "Python CLI tool with database backend" in domain

        # Simple CLI tool
        simple_cli_analysis = {
            "web_ui_files": [],
            "database_files": [],
            "cli_files": ["cli/main.py"],
            "test_files": [],
        }
        domain = spec_generator._infer_domain(simple_cli_analysis)
        assert "Python CLI tool for AI-powered" in domain

    def test_architectural_pattern_detection(self, spec_generator):
        """Test detection of specific architectural patterns."""
        file_analysis = {
            "web_ui_files": ["web_ui/main.py", "templates/index.html"],
            "database_files": ["db/async_db.py", "migrations/001_init.py"],
            "migration_files": ["migrations/001_init.py", "migrations/002_update.py"],
            "test_files": ["tests/test_async.py"],
            "template_files": ["templates/spec.yaml"],
            "cli_files": ["cli/main.py"],
        }

        patterns = spec_generator._detect_architectural_patterns(file_analysis)

        expected_patterns = [
            "Web UI with FastAPI/Jinja2 templates",
            "Database-backed workflow with async operations",
            "Asynchronous database operations",
            "Database migrations",
        ]

        for pattern in expected_patterns:
            assert pattern in patterns


if __name__ == "__main__":
    pytest.main([__file__])
