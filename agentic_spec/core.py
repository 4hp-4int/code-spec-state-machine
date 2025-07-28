"""Core specification generation functionality."""

# Removed dataclass asdict import - now using Pydantic model_dump
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any
import uuid

import yaml

from .ai_providers import AIProviderFactory
from .config import AgenticSpecConfig
from .exceptions import ConfigurationError, GitError
from .models import (
    ContextParameters,
    ImplementationStep,
    ProgrammingSpec,
    SpecContext,
    SpecMetadata,
    SpecRequirement,
)
from .prompt_engineering import PromptEngineer
from .prompt_template_loader import PromptTemplateLoader
from .utils.deep_merge import merge_configs


class GitUtility:
    """Git utility functions for workflow integration."""

    @staticmethod
    def is_git_repo(directory: Path = None) -> bool:
        """Check if current or specified directory is a git repository."""
        if directory is None:
            directory = Path.cwd()
        return (directory / ".git").exists()

    @staticmethod
    def run_git_command(
        command: list[str], directory: Path = None, check: bool = True
    ) -> subprocess.CompletedProcess:
        """Run a git command and return the result."""
        if directory is None:
            directory = Path.cwd()

        full_command = ["git"] + command
        try:
            result = subprocess.run(
                full_command, cwd=directory, capture_output=True, text=True, check=check
            )
            return result
        except subprocess.CalledProcessError as e:
            raise GitError(
                f"Git command failed: {e.stderr.strip() if e.stderr else 'Unknown error'}",
                git_command=" ".join(full_command),
                return_code=e.returncode,
            )
        except FileNotFoundError:
            raise GitError(
                "Git command not found. Please ensure git is installed and in your PATH."
            )

    @staticmethod
    def get_current_branch(directory: Path = None) -> str:
        """Get the current git branch name."""
        result = GitUtility.run_git_command(["branch", "--show-current"], directory)
        return result.stdout.strip()

    @staticmethod
    def has_uncommitted_changes(directory: Path = None) -> bool:
        """Check if there are uncommitted changes in the repository."""
        result = GitUtility.run_git_command(["status", "--porcelain"], directory)
        return bool(result.stdout.strip())

    @staticmethod
    def create_and_checkout_branch(branch_name: str, directory: Path = None) -> None:
        """Create and checkout a new git branch."""
        if not GitUtility.is_git_repo(directory):
            raise GitError("Not in a git repository")

        # Check if branch already exists
        try:
            GitUtility.run_git_command(
                ["show-ref", "--verify", f"refs/heads/{branch_name}"], directory
            )
            raise GitError(f"Branch '{branch_name}' already exists")
        except GitError:
            # Branch doesn't exist, which is what we want
            pass

        # Create and checkout the branch
        GitUtility.run_git_command(["checkout", "-b", branch_name], directory)

    @staticmethod
    def generate_branch_name(task_id: str, task_title: str) -> str:
        """Generate a standardized branch name from task ID and title."""
        # Clean the task title for use in branch name
        task_slug = re.sub(r"[^a-zA-Z0-9\s\-_]", "", task_title)
        task_slug = re.sub(r"\s+", "-", task_slug.strip())
        task_slug = task_slug.lower()[:50]  # Limit length
        task_slug = task_slug.rstrip("-")

        return f"feature/{task_id}_{task_slug}"


class SpecGenerator:
    """Generates programming specifications from prompts with inheritance."""

    def __init__(
        self,
        spec_templates_dir: Path,
        specs_dir: Path,
        config: AgenticSpecConfig | None = None,
        discovery_config_file: Path | None = None,
    ):
        self.spec_templates_dir = spec_templates_dir
        self.specs_dir = specs_dir
        self.spec_templates_dir.mkdir(parents=True, exist_ok=True)
        self.specs_dir.mkdir(parents=True, exist_ok=True)
        self.config = config or AgenticSpecConfig()
        self.discovery_config_file = discovery_config_file
        self.sync_foundation_config = self._load_sync_foundation_config()

        # Initialize prompt template loader
        prompt_templates_dir = (
            self.spec_templates_dir.parent
            / self.config.directories.get_prompt_templates_dir()
        )
        self.prompt_template_loader = PromptTemplateLoader(prompt_templates_dir)
        self.prompt_engineer = PromptEngineer(prompt_templates_dir)

        # Initialize AI provider
        self.ai_provider = self._initialize_ai_provider()

    def _initialize_ai_provider(self):
        """Initialize the AI provider based on configuration."""
        try:
            provider_name = self.config.ai_settings.default_provider
            provider_config = self.config.ai_settings.providers.get(provider_name)

            if not provider_config:
                raise ConfigurationError(f"Provider '{provider_name}' not configured")

            return AIProviderFactory.create_provider(provider_config)
        except Exception as e:
            print(f"Warning: Failed to initialize AI provider: {e}")
            return None

    def load_template(self, template_name: str) -> dict[str, Any]:
        """Load a base template by name with version validation."""
        template_path = self.spec_templates_dir / f"{template_name}.yaml"
        if template_path.exists():
            with template_path.open() as f:
                template_data = yaml.safe_load(f)

            # Check for version field and validate
            if "version" in template_data:
                if not self._is_valid_semver(template_data["version"]):
                    print(
                        f"Warning: Template '{template_name}' has invalid semver version: {template_data['version']}"
                    )
                else:
                    # Check if migration is needed (simplified version)
                    self._check_version_compatibility(
                        template_name, template_data["version"]
                    )

            return template_data
        return {}

    def _is_valid_semver(self, version: str) -> bool:
        """Validate semantic version format (MAJOR.MINOR.PATCH)."""
        semver_pattern = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*(?:\.[0-9a-zA-Z-]*)*)))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
        return bool(re.match(semver_pattern, version))

    def _check_version_compatibility(self, template_name: str, version: str) -> None:
        """Check version compatibility and prompt for migration if needed."""
        # For this simplified implementation, we'll just log the version
        # In a full implementation, we could store last used versions and compare
        print(f"Template '{template_name}' version: {version}")

    def _generate_title_from_prompt(self, prompt: str) -> str:
        """Generate a human-readable title from the user prompt."""
        # Clean up the prompt and create a concise title
        title = prompt.strip()

        # Remove common prefixes
        prefixes = ["implement", "create", "add", "build", "develop", "write"]
        for prefix in prefixes:
            if title.lower().startswith(prefix.lower()):
                title = title[len(prefix) :].strip()

        # Capitalize first letter and limit length
        if title:
            title = title[0].upper() + title[1:] if len(title) > 1 else title.upper()

        # Truncate if too long and add ellipsis
        if len(title) > 80:
            title = title[:77] + "..."

        return title if title else "Programming Specification"

    def _compare_versions(self, version1: str, version2: str) -> int:
        """Compare two semantic version strings.

        Returns:
            -1 if version1 < version2
             0 if version1 == version2
             1 if version1 > version2
        """

        def _parse_version(version: str) -> tuple[int, int, int]:
            # Simple semver parsing (MAJOR.MINOR.PATCH)
            parts = version.split(".")
            return (int(parts[0]), int(parts[1]), int(parts[2]))

        v1 = _parse_version(version1)
        v2 = _parse_version(version2)

        if v1 < v2:
            return -1
        if v1 > v2:
            return 1
        return 0

    def resolve_inheritance(self, inherits: list[str]) -> dict[str, Any]:
        """Resolve inheritance chain and merge templates."""
        merged = {}

        for template_name in inherits:
            template = self.load_template(template_name)
            # Use robust deep merge utility with template inheritance semantics
            merged = merge_configs(merged, template)

        return merged

    def load_parent_spec_context(self, spec: ProgrammingSpec) -> dict[str, Any]:
        """Load context from parent specification if it exists."""
        if not spec.metadata.parent_spec_id:
            return {}

        parent_spec = self.find_spec_by_id(spec.metadata.parent_spec_id)
        if not parent_spec:
            return {}

        # Convert parent spec to context dict
        parent_context = {
            "parent_project": parent_spec.context.project,
            "parent_domain": parent_spec.context.domain,
            "parent_requirements": parent_spec.requirements,
            "parent_context": parent_spec.context,
            "parent_metadata": parent_spec.metadata,
        }

        # Recursively load grandparent context
        grandparent_context = self.load_parent_spec_context(parent_spec)
        if grandparent_context:
            parent_context["ancestor_context"] = grandparent_context

        return parent_context

    def resolve_comprehensive_context(
        self, inherits: list[str] | None = None, parent_spec_id: str | None = None
    ) -> dict[str, Any]:
        """Resolve complete context including inheritance, parent specs, and foundation."""
        context = {}

        # 1. Load foundation spec context (always include)
        try:
            foundation_context = self.load_template("agentic-spec-foundation")
            context = merge_configs(context, {"foundation": foundation_context})
        except (FileNotFoundError, KeyError, ValueError):
            # Foundation spec not found - this indicates it needs to be synced
            context["foundation_sync_needed"] = True

        # 2. Load inherited template context
        inherited_context = self.resolve_inheritance(inherits or [])
        if inherited_context:
            context = merge_configs(context, {"inherited": inherited_context})

        # 3. Load parent spec context if provided
        if parent_spec_id:
            parent_spec = self.find_spec_by_id(parent_spec_id)
            if parent_spec:
                parent_context = self.load_parent_spec_context(parent_spec)
                if parent_context:
                    context = merge_configs(context, {"parent": parent_context})

        return context

    def _load_sync_foundation_config(self) -> "SyncFoundationConfig | None":
        """Load sync-foundation configuration from file with comprehensive error handling."""

        from .exceptions import (
            ConfigParsingError,
            ConfigValidationError,
            SyncFoundationConfigError,
        )

        config_path = None
        try:
            # If explicit path provided, use it
            if self.discovery_config_file:
                config_path = Path(self.discovery_config_file)
                if not config_path.exists():
                    raise SyncFoundationConfigError(
                        f"Specified discovery config file not found: {config_path}",
                        config_path=str(config_path),
                    )

                return self._load_config_from_path(config_path)

            # Auto-discovery: check for common config file names
            project_root = self.spec_templates_dir.parent
            config_names = [
                "sync_foundation_config.yaml",
                "sync-foundation-config.yaml",
                "project_discovery.yaml",
                "project-discovery.yaml",
                ".sync-foundation.yaml",
            ]

            for config_name in config_names:
                config_path = project_root / config_name
                if config_path.exists():
                    print(f"📄 Using discovery config: {config_path.name}")
                    return self._load_config_from_path(config_path)

            # No config found, return None to use defaults
            return None

        except (ConfigParsingError, ConfigValidationError, SyncFoundationConfigError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise SyncFoundationConfigError(
                f"Unexpected error loading sync-foundation config: {e}",
                config_path=str(config_path) if config_path else None,
            ) from e

    def _load_config_from_path(self, config_path: Path) -> "SyncFoundationConfig":
        """Load and validate config from a specific path."""
        from pydantic import ValidationError
        import yaml

        from .config import SyncFoundationConfig
        from .exceptions import ConfigParsingError, ConfigValidationError

        try:
            # Read and parse YAML
            with config_path.open(encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            if config_data is None:
                raise ConfigParsingError(
                    "Config file is empty or contains only comments",
                    config_path=str(config_path),
                )

            if not isinstance(config_data, dict):
                raise ConfigParsingError(
                    f"Config file must contain a YAML object, got {type(config_data).__name__}",
                    config_path=str(config_path),
                )

        except yaml.YAMLError as e:
            raise ConfigParsingError(
                f"Failed to parse YAML: {e}", config_path=str(config_path)
            ) from e
        except (OSError, UnicodeDecodeError) as e:
            raise ConfigParsingError(
                f"Failed to read config file: {e}", config_path=str(config_path)
            ) from e

        try:
            # Create and validate config object
            config = SyncFoundationConfig(**config_data)

            # Run additional validation checks
            pattern_warnings = config.validate_patterns()
            skip_warnings = config.validate_skip_patterns()

            # Log warnings but don't fail
            all_warnings = pattern_warnings + skip_warnings
            if all_warnings:
                print(f"⚠️  Configuration warnings for {config_path.name}:")
                for warning in all_warnings:
                    print(f"   • {warning}")

            return config

        except ValidationError as e:
            # Convert Pydantic validation errors to our custom exception
            error_details = []
            for error in e.errors():
                field = ".".join(str(x) for x in error["loc"])
                message = error["msg"]
                error_details.append(f"{field}: {message}")

            raise ConfigValidationError(
                f"Configuration validation failed: {'; '.join(error_details)}",
                config_path=str(config_path),
            ) from e

    def sync_foundation_spec(self) -> bool:
        """Sync foundation spec with current codebase state."""
        try:
            # Analyze current codebase
            foundation_data = self._analyze_codebase_for_foundation()

            # Write updated foundation spec
            foundation_path = self.spec_templates_dir / "agentic-spec-foundation.yaml"
            with foundation_path.open("w", encoding="utf-8") as f:
                yaml.dump(foundation_data, f, default_flow_style=False, sort_keys=False)

            return True
        except (OSError, PermissionError) as e:
            print(f"Failed to sync foundation spec: {e}")
            return False

    def _analyze_codebase_for_foundation(self) -> dict[str, Any]:
        """Analyze current codebase to generate foundation spec data."""
        # Get project root (go up from agentic_spec directory)
        project_root = self.spec_templates_dir.parent

        # Categorize and analyze files
        file_analysis = self._categorize_files(project_root)
        python_files = file_analysis["python_files"]

        # Analyze dependencies from pyproject.toml and imports
        dependencies = self._extract_dependencies(project_root, python_files)

        # Analyze architecture from file structure and content
        architecture = self._analyze_architecture(project_root, file_analysis)

        # Generate foundation data
        return {
            "context": {
                "project": "agentic-spec",
                "domain": self._infer_domain(file_analysis),
                "dependencies": dependencies,
                "architecture_overview": architecture["overview"],
                "current_codebase_structure": architecture["structure"],
                "file_categorization": {
                    "cli_files": file_analysis["cli_files"],
                    "web_ui_files": file_analysis["web_ui_files"],
                    "api_files": file_analysis["api_files"],
                    "database_files": file_analysis["database_files"],
                    "migration_files": file_analysis["migration_files"],
                    "test_files": file_analysis["test_files"],
                    "config_files": file_analysis["config_files"],
                    "template_files": file_analysis["template_files"],
                    "documentation_files": file_analysis["documentation_files"],
                    "build_files": file_analysis["build_files"],
                    "data_files": file_analysis["data_files"],
                    "statistics": file_analysis["statistics"],
                },
                "web_ui_components": file_analysis["web_ui_files"],
                "database_components": file_analysis["database_files"],
                "test_coverage": file_analysis["test_files"],
            },
            "requirements": {
                "functional": architecture["functional_requirements"],
                "non_functional": architecture["non_functional_requirements"],
                "constraints": architecture["constraints"],
            },
            "coding_standards": self._extract_coding_standards(python_files),
            "key_design_patterns": self._extract_design_patterns(
                python_files, file_analysis
            ),
            "architectural_patterns": self._detect_architectural_patterns(
                file_analysis
            ),
            "_last_synced": datetime.now().isoformat(),
            "_sync_version": "2.0",
        }

    def _categorize_files(self, project_root: Path) -> dict[str, Any]:
        """Categorize files by type and purpose using config-driven patterns."""
        categorization = {
            "python_files": [],
            "web_ui_files": [],
            "database_files": [],
            "test_files": [],
            "config_files": [],
            "template_files": [],
            "migration_files": [],
            "cli_files": [],
            "api_files": [],
            "data_files": [],
            "documentation_files": [],
            "build_files": [],
        }

        # Get skip patterns from config or use defaults
        if self.sync_foundation_config:
            skip_patterns = self.sync_foundation_config.project_analysis.skip_patterns
        else:
            # Default skip patterns for better organization (use both forward and backslashes for Windows)
            skip_patterns = [
                ".venv\\",
                ".venv/",
                "venv\\",
                "venv/",
                "build\\",
                "build/",
                "dist\\",
                "dist/",
                "__pycache__\\",
                "__pycache__/",
                ".git\\",
                ".git/",
                ".pytest_cache\\",
                ".pytest_cache/",
                ".mypy_cache\\",
                ".mypy_cache/",
                "node_modules\\",
                "node_modules/",
            ]

        # Categorize Python files with enhanced detection
        for py_file in project_root.rglob("*.py"):
            file_path = str(py_file.relative_to(project_root))

            # Skip virtual environment and build directories
            if any(skip_dir in file_path for skip_dir in skip_patterns):
                continue

            categorization["python_files"].append(py_file)

            # Read file content for better categorization
            content_indicators = self._analyze_file_content(py_file)

            # Use config-driven categorization
            file_category = self._categorize_single_file(file_path, content_indicators)
            if file_category:
                categorization[file_category].append(file_path)

        # Enhanced non-Python file categorization
        file_mappings = {
            "*.toml": ("config_files", ["pyproject.toml", "*.toml"]),
            "*.yaml": ("template_files", ["templates/", "specs/"]),
            "*.yml": ("config_files", [".github/"]),
            "*.html": ("web_ui_files", []),
            "*.css": ("web_ui_files", []),
            "*.js": ("web_ui_files", []),
            "*.json": ("config_files", ["package.json", "tsconfig.json"]),
            "*.md": ("documentation_files", ["README", "CHANGELOG", "docs/"]),
            "*.rst": ("documentation_files", ["docs/"]),
            "*.txt": ("data_files", ["requirements", "LICENSE"]),
            "*.sql": ("database_files", []),
            "*.db": ("database_files", []),
            "*.sqlite": ("database_files", []),
            "Makefile": ("build_files", []),
            "Dockerfile": ("build_files", []),
            "*.dockerfile": ("build_files", []),
        }

        for pattern, (category, context_indicators) in file_mappings.items():
            for file_obj in project_root.rglob(pattern):
                file_path = str(file_obj.relative_to(project_root))

                # Skip virtual environment and build directories
                if any(skip_dir in file_path for skip_dir in skip_patterns):
                    continue

                # Apply context-based filtering
                if context_indicators:
                    if any(
                        indicator in file_path.lower()
                        for indicator in context_indicators
                    ):
                        categorization[category].append(file_path)
                else:
                    categorization[category].append(file_path)

        # Add file count statistics
        categorization["statistics"] = {
            category: len(files)
            for category, files in categorization.items()
            if category != "statistics"
        }

        return categorization

    def _categorize_single_file(
        self, file_path: str, content_indicators: list[str]
    ) -> str | None:
        """Categorize a single file using config-driven patterns."""
        if self.sync_foundation_config:
            config = self.sync_foundation_config.file_categorization

            # Check migration files first (to avoid being categorized as database files)
            if any(
                pattern in file_path.lower() for pattern in config.migration_patterns
            ) or any(
                indicator in content_indicators
                for indicator in config.migration_content_indicators
            ):
                return "migration_files"

            # Check each category with both path and content patterns
            categorization_rules = [
                ("cli_files", config.cli_patterns, config.cli_content_indicators),
                (
                    "web_ui_files",
                    config.web_ui_patterns,
                    config.web_ui_content_indicators,
                ),
                ("api_files", config.api_patterns, config.api_content_indicators),
                (
                    "database_files",
                    config.database_patterns,
                    config.database_content_indicators,
                ),
                ("test_files", config.test_patterns, config.test_content_indicators),
            ]

            for category, path_patterns, content_patterns in categorization_rules:
                if any(
                    pattern in file_path.lower() for pattern in path_patterns
                ) or any(
                    indicator in content_indicators for indicator in content_patterns
                ):
                    return category
        # Fallback to hardcoded logic if no config
        # Migration files (check first to avoid being categorized as database files)
        elif (
            any(
                indicator in file_path.lower() for indicator in ["migration", "migrate"]
            )
            or "migration" in content_indicators
        ):
            return "migration_files"

        # Web UI files (enhanced detection)
        elif any(
            indicator in file_path.lower()
            for indicator in ["web_ui", "webui", "fastapi", "templates"]
        ) or any(
            indicator in content_indicators
            for indicator in ["fastapi", "starlette", "@app.route", "HTMLResponse"]
        ):
            return "web_ui_files"

        # API files
        elif any(
            indicator in file_path.lower()
            for indicator in ["api", "routes", "endpoints"]
        ) or any(
            indicator in content_indicators
            for indicator in ["@app.", "APIRouter", "FastAPI"]
        ):
            return "api_files"

        # Database files (enhanced detection)
        elif any(
            indicator in file_path.lower()
            for indicator in ["db", "database", "sqlite", "async_db"]
        ) or any(
            indicator in content_indicators
            for indicator in ["sqlite", "aiosqlite", "CREATE TABLE", "async def"]
        ):
            return "database_files"

        # CLI files
        elif any(
            indicator in file_path.lower() for indicator in ["cli", "command", "main"]
        ) or any(
            indicator in content_indicators
            for indicator in ["typer", "click", "argparse", "@app.command"]
        ):
            return "cli_files"

        # Test files (enhanced detection)
        elif any(
            indicator in file_path.lower()
            for indicator in ["test_", "_test", "tests/", "conftest"]
        ) or any(
            indicator in content_indicators
            for indicator in ["pytest", "def test_", "class Test"]
        ):
            return "test_files"

        return None

    def _analyze_file_content(self, file_path: Path) -> list[str]:
        """Analyze file content to extract key indicators for categorization."""
        indicators = []

        try:
            with file_path.open("r", encoding="utf-8") as f:
                # Read first few lines for performance
                content = f.read(2000)  # First 2KB

            content_lower = content.lower()

            # Web framework indicators
            if any(
                term in content_lower for term in ["fastapi", "starlette", "uvicorn"]
            ):
                indicators.append("fastapi")
            if any(term in content for term in ["@app.route", "@app.get", "@app.post"]):
                indicators.append("@app.route")
            if "HTMLResponse" in content:
                indicators.append("HTMLResponse")

            # Database indicators
            if any(term in content_lower for term in ["sqlite", "aiosqlite"]):
                indicators.append("sqlite")
            if "CREATE TABLE" in content.upper():
                indicators.append("CREATE TABLE")
            if "async def" in content:
                indicators.append("async def")

            # CLI indicators
            if any(term in content_lower for term in ["typer", "click"]):
                indicators.append("typer" if "typer" in content_lower else "click")
            if "@app.command" in content:
                indicators.append("@app.command")
            if "argparse" in content_lower:
                indicators.append("argparse")

            # Testing indicators
            if any(term in content_lower for term in ["pytest", "unittest"]):
                indicators.append("pytest" if "pytest" in content_lower else "unittest")
            if any(term in content for term in ["def test_", "class Test"]):
                indicators.append(
                    "def test_" if "def test_" in content else "class Test"
                )

            # Migration indicators
            if any(
                term in content_lower for term in ["migration", "migrate", "schema"]
            ):
                indicators.append("migration")

        except (OSError, UnicodeDecodeError, PermissionError):
            pass

        return indicators

    def _infer_domain(self, file_analysis: dict[str, Any]) -> str:
        """Infer project domain from file analysis using config-driven patterns."""
        if self.sync_foundation_config:
            config = self.sync_foundation_config.project_analysis
            language = config.default_language
            base_domain = config.default_domain

            # Use config patterns to generate domain description
            if file_analysis["web_ui_files"]:
                if file_analysis["database_files"]:
                    pattern = config.domain_patterns.get(
                        "full_stack",
                        "Full-stack {language} application with CLI, web UI, and database components",
                    )
                    return pattern.format(language=language, domain=base_domain)
                pattern = config.domain_patterns.get(
                    "web_cli", "{language} CLI tool with web UI for {domain}"
                )
                return pattern.format(language=language, domain=base_domain)
            if file_analysis["database_files"]:
                pattern = config.domain_patterns.get(
                    "database_cli",
                    "{language} CLI tool with database backend for {domain}",
                )
                return pattern.format(language=language, domain=base_domain)
            pattern = config.domain_patterns.get(
                "simple_cli", "{language} CLI tool for {domain}"
            )
            return pattern.format(language=language, domain=base_domain)
        # Fallback to hardcoded logic
        if file_analysis["web_ui_files"]:
            if file_analysis["database_files"]:
                return "Full-stack Python application with CLI, web UI, and database components"
            return "Python CLI tool with web UI for AI-powered specification generation"
        if file_analysis["database_files"]:
            return "Python CLI tool with database backend for AI-powered specification generation"
        return "Python CLI tool for AI-powered specification generation"

    def _detect_architectural_patterns(
        self, file_analysis: dict[str, Any]
    ) -> list[str]:
        """Detect architectural patterns from file analysis."""
        patterns = []

        if file_analysis["web_ui_files"]:
            patterns.append("Web UI with FastAPI/Jinja2 templates")
        if file_analysis["database_files"]:
            patterns.append("Database-backed workflow with async operations")
        if any("async" in f for f in file_analysis["database_files"]):
            patterns.append("Asynchronous database operations")
        if file_analysis["template_files"]:
            patterns.append("Template inheritance system")
        if len(file_analysis["test_files"]) > 5:
            patterns.append("Comprehensive test coverage")
        if any("migration" in f for f in file_analysis["database_files"]):
            patterns.append("Database migrations")

        return patterns

    def _extract_dependencies(
        self, project_root: Path, python_files: list[Path]
    ) -> list[dict[str, str]]:
        """Extract dependencies from multiple sources including transitive dependencies."""
        dependencies = []

        # Extract from pyproject.toml (main dependencies)
        dependencies.extend(self._extract_from_pyproject(project_root))

        # Extract from requirements.txt files if present
        dependencies.extend(self._extract_from_requirements(project_root))

        # Extract from setup.py if present
        dependencies.extend(self._extract_from_setup_py(project_root))

        # Analyze import statements for additional context and transitive deps
        import_analysis = self._analyze_imports(python_files)

        # Add dependencies found in imports but not in config files
        for module_name, usage_data in import_analysis.items():
            if not any(
                dep["name"].lower() == module_name.lower() for dep in dependencies
            ):
                # Check if this is a known package (not stdlib)
                if self._is_third_party_package(module_name):
                    dep_info = self._categorize_dependency(module_name)
                    dependencies.append(
                        {
                            "name": module_name,
                            "version": "unknown",
                            "description": dep_info["description"],
                            "category": dep_info["category"],
                            "source": "import_analysis",
                            "usage_context": usage_data["context"],
                            "import_frequency": usage_data["frequency"],
                        }
                    )

        # Enhance dependency descriptions with usage context
        for dep in dependencies:
            if dep["name"] in import_analysis:
                usage = import_analysis[dep["name"]]
                dep["usage_context"] = usage["context"]
                dep["import_frequency"] = usage["frequency"]

            # Add transitive dependency information where possible
            transitive_deps = self._detect_transitive_dependencies(dep["name"])
            if transitive_deps:
                dep["transitive_dependencies"] = transitive_deps

        # Fallback if no dependencies found
        if not dependencies:
            dependencies = [
                {
                    "name": "Python",
                    "version": "3.12+",
                    "description": "Core programming language",
                    "category": "runtime",
                },
                {
                    "name": "PyYAML",
                    "version": "6.0+",
                    "description": "YAML parsing and generation",
                    "category": "core",
                },
                {
                    "name": "OpenAI",
                    "version": "1.97+",
                    "description": "AI integration",
                    "category": "ai",
                },
            ]

        return dependencies

    def _extract_from_pyproject(self, project_root: Path) -> list[dict[str, Any]]:
        """Extract dependencies from pyproject.toml."""
        dependencies = []

        try:
            import tomllib

            pyproject_path = project_root / "pyproject.toml"
            if pyproject_path.exists():
                with pyproject_path.open("rb") as f:
                    data = tomllib.load(f)

                # Main dependencies
                for dep in data.get("project", {}).get("dependencies", []):
                    name, version = self._parse_dependency_spec(dep)
                    dep_info = self._categorize_dependency(name)
                    dependencies.append(
                        {
                            "name": name,
                            "version": version,
                            "description": dep_info["description"],
                            "category": dep_info["category"],
                            "source": "pyproject.toml",
                        }
                    )

                # Optional dependencies
                optional_deps = data.get("project", {}).get("optional-dependencies", {})
                for group_name, deps in optional_deps.items():
                    for dep in deps:
                        name, version = self._parse_dependency_spec(dep)
                        dep_info = self._categorize_dependency(name)
                        dependencies.append(
                            {
                                "name": name,
                                "version": version,
                                "description": dep_info["description"],
                                "category": dep_info["category"],
                                "source": f"pyproject.toml (optional-{group_name})",
                            }
                        )

        except (OSError, ImportError, KeyError, ValueError, TypeError):
            pass

        return dependencies

    def _extract_from_requirements(self, project_root: Path) -> list[dict[str, Any]]:
        """Extract dependencies from requirements files using config-driven patterns."""
        dependencies = []

        # Get requirements file patterns from config or use defaults
        if self.sync_foundation_config:
            req_patterns = (
                self.sync_foundation_config.dependency_detection.requirements_files
            )
        else:
            # Default requirements file patterns
            req_patterns = [
                "requirements.txt",
                "requirements/*.txt",
                "requirements-*.txt",
            ]

        for pattern in req_patterns:
            for req_file in project_root.glob(pattern):
                try:
                    with req_file.open("r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if (
                                line
                                and not line.startswith("#")
                                and not line.startswith("-")
                            ):
                                name, version = self._parse_dependency_spec(line)
                                if name:
                                    dep_info = self._categorize_dependency(name)
                                    dependencies.append(
                                        {
                                            "name": name,
                                            "version": version,
                                            "description": dep_info["description"],
                                            "category": dep_info["category"],
                                            "source": str(req_file.name),
                                        }
                                    )
                except (OSError, UnicodeDecodeError):
                    continue

        return dependencies

    def _extract_from_setup_py(self, project_root: Path) -> list[dict[str, Any]]:
        """Extract dependencies from setup.py."""
        dependencies = []

        setup_py = project_root / "setup.py"
        if setup_py.exists():
            try:
                with setup_py.open("r", encoding="utf-8") as f:
                    content = f.read()

                # Simple regex to find install_requires
                import re

                install_requires_match = re.search(
                    r"install_requires\s*=\s*\[(.*?)\]", content, re.DOTALL
                )
                if install_requires_match:
                    deps_str = install_requires_match.group(1)
                    # Extract quoted dependencies
                    for match in re.finditer(r'["\']([^"\']+)["\']', deps_str):
                        dep_spec = match.group(1)
                        name, version = self._parse_dependency_spec(dep_spec)
                        if name:
                            dep_info = self._categorize_dependency(name)
                            dependencies.append(
                                {
                                    "name": name,
                                    "version": version,
                                    "description": dep_info["description"],
                                    "category": dep_info["category"],
                                    "source": "setup.py",
                                }
                            )

            except (OSError, UnicodeDecodeError):
                pass

        return dependencies

    def _parse_dependency_spec(self, dep_spec: str) -> tuple[str, str]:
        """Parse dependency specification to extract name and version."""
        import re

        # Remove comments and whitespace
        dep_spec = dep_spec.split("#")[0].strip()

        # Handle package name with optional extras like package[extra1,extra2]
        # Pattern matches: package_name[extras]version_spec or package_nameversion_spec
        pattern = r"^([a-zA-Z0-9_\-\.]+)(?:\[[^\]]+\])?([>=<~!,\s]+.+)?$"
        match = re.match(pattern, dep_spec)

        if match:
            name = match.group(1)
            version_spec = match.group(2)
            if version_spec:
                return name, version_spec.strip()
            return name, "latest"
        # Fallback: try to extract just alphanumeric name
        name_match = re.match(r"^([a-zA-Z0-9_\-\.]+)", dep_spec)
        if name_match:
            return name_match.group(1), "latest"
        return dep_spec, "latest"

    def _is_third_party_package(self, module_name: str) -> bool:
        """Check if a module is likely a third-party package using config-driven stdlib detection."""
        # Get stdlib modules from config or use defaults
        if self.sync_foundation_config:
            stdlib_modules = set(
                self.sync_foundation_config.dependency_detection.stdlib_modules
            )
        else:
            # Default stdlib modules to exclude
            stdlib_modules = {
                "os",
                "sys",
                "re",
                "json",
                "urllib",
                "http",
                "pathlib",
                "typing",
                "asyncio",
                "logging",
                "datetime",
                "collections",
                "itertools",
                "functools",
                "inspect",
                "importlib",
                "unittest",
                "sqlite3",
                "csv",
                "xml",
                "email",
                "html",
                "math",
                "random",
                "string",
                "threading",
                "multiprocessing",
                "subprocess",
                "shutil",
                "tempfile",
                "glob",
                "fnmatch",
                "warnings",
                "traceback",
                "io",
                "contextlib",
                "copy",
                "pickle",
                "struct",
                "zlib",
                "hashlib",
                "hmac",
                "secrets",
                "base64",
                "binascii",
                "uuid",
                "time",
                "calendar",
                "argparse",
                "configparser",
                "tomllib",
            }

        return module_name.lower() not in stdlib_modules

    def _detect_transitive_dependencies(self, package_name: str) -> list[str]:
        """Detect transitive dependencies using importlib.metadata if available."""
        try:
            from importlib import metadata

            # Get distribution for the package
            dist = metadata.distribution(package_name)
            requires = dist.requires or []

            transitive = []
            for req in requires:
                # Parse requirement string to get package name
                req_name = (
                    req.split()[0]
                    .split(">=")[0]
                    .split(">")[0]
                    .split("==")[0]
                    .split("!=")[0]
                )
                if req_name != package_name:
                    transitive.append(req_name)

            return transitive[:10]  # Limit to prevent excessive output

        except (ImportError, metadata.PackageNotFoundError, Exception):
            return []

    def _categorize_dependency(self, name: str) -> dict[str, str]:
        """Categorize dependency by type using config-driven patterns."""
        name_lower = name.lower()

        if self.sync_foundation_config:
            config = self.sync_foundation_config.dependency_detection

            # Check each category using config patterns
            if name_lower in [lib.lower() for lib in config.web_frameworks]:
                return {"category": "web", "description": f"Web framework: {name}"}
            if name_lower in [lib.lower() for lib in config.database_libs]:
                return {"category": "database", "description": f"Database: {name}"}
            if name_lower in [lib.lower() for lib in config.template_engines]:
                return {
                    "category": "templates",
                    "description": f"Template engine: {name}",
                }
            if name_lower in [lib.lower() for lib in config.testing_frameworks]:
                return {
                    "category": "testing",
                    "description": f"Testing framework: {name}",
                }
            if name_lower in [lib.lower() for lib in config.ai_libraries]:
                return {"category": "ai", "description": f"AI integration: {name}"}
            if name_lower in [lib.lower() for lib in config.config_parsers]:
                return {
                    "category": "config",
                    "description": f"Configuration parsing: {name}",
                }
            if name_lower in [lib.lower() for lib in config.cli_frameworks]:
                return {"category": "cli", "description": f"CLI framework: {name}"}
            if name_lower in [lib.lower() for lib in config.visualization_libs]:
                return {
                    "category": "visualization",
                    "description": f"Graph/visualization: {name}",
                }

            # Check if it's a standard library module
            if name_lower in [mod.lower() for mod in config.stdlib_modules]:
                return {
                    "category": "stdlib",
                    "description": f"Standard library: {name}",
                }
        else:
            # Fallback to hardcoded logic if no config
            if name_lower in ["fastapi", "uvicorn", "starlette"]:
                return {"category": "web", "description": f"Web framework: {name}"}
            if name_lower in ["aiosqlite", "sqlite3", "sqlalchemy"]:
                return {"category": "database", "description": f"Database: {name}"}
            if name_lower in ["jinja2", "mako"]:
                return {
                    "category": "templates",
                    "description": f"Template engine: {name}",
                }
            if name_lower in ["pytest", "pytest-cov", "pytest-asyncio"]:
                return {
                    "category": "testing",
                    "description": f"Testing framework: {name}",
                }
            if name_lower in ["openai", "anthropic"]:
                return {"category": "ai", "description": f"AI integration: {name}"}
            if name_lower in ["pyyaml", "toml", "tomllib"]:
                return {
                    "category": "config",
                    "description": f"Configuration parsing: {name}",
                }
            if name_lower in ["typer", "click", "argparse"]:
                return {"category": "cli", "description": f"CLI framework: {name}"}
            if name_lower in ["networkx", "matplotlib"]:
                return {
                    "category": "visualization",
                    "description": f"Graph/visualization: {name}",
                }

        return {"category": "core", "description": f"Core dependency: {name}"}

    def _analyze_imports(self, python_files: list[Path]) -> dict[str, dict[str, Any]]:
        """Analyze import statements to understand dependency usage."""
        import_analysis = {}

        for py_file in python_files:
            # Only analyze actual Python files
            if not py_file.name.endswith(".py"):
                continue

            try:
                with py_file.open("r", encoding="utf-8") as f:
                    content = f.read()

                # Simple import detection
                import_lines = [
                    line.strip()
                    for line in content.split("\n")
                    if line.strip().startswith(("import ", "from "))
                ]

                for line in import_lines:
                    # Extract module name
                    if line.startswith("from "):
                        module = line.split()[1].split(".")[0]
                    else:
                        module = line.split()[1].split(".")[0]

                    # Skip invalid module names
                    if (
                        not module
                        or not module.replace("_", "").replace("-", "").isalnum()
                    ):
                        continue

                    if module not in import_analysis:
                        import_analysis[module] = {"frequency": 0, "context": []}

                    import_analysis[module]["frequency"] += 1

                    # Add context based on file type
                    file_context = self._get_file_context(py_file)
                    if file_context not in import_analysis[module]["context"]:
                        import_analysis[module]["context"].append(file_context)

            except (OSError, UnicodeDecodeError):
                continue

        return import_analysis

    def _get_file_context(self, py_file: Path) -> str:
        """Get context description for a Python file."""
        file_name = py_file.name.lower()
        file_path = str(py_file).lower()

        if "web_ui" in file_path or "fastapi" in file_path:
            return "web_ui"
        if "test" in file_path:
            return "testing"
        if "db" in file_name or "database" in file_name:
            return "database"
        if "cli" in file_name:
            return "cli"
        if "core" in file_name:
            return "core_logic"
        return "general"

    def _analyze_architecture(
        self, project_root: Path, file_analysis: dict[str, Any]
    ) -> dict[str, Any]:
        """Analyze project architecture from file structure and categorization."""
        src_dir = project_root / "agentic_spec"

        # Enhanced structure based on categorization
        structure_lines = ["agentic_spec/"]
        if src_dir.exists():
            for py_file in sorted(src_dir.glob("*.py")):
                if py_file.name != "__init__.py":
                    # Add context indicators
                    file_path = str(py_file.relative_to(project_root))
                    if file_path in file_analysis["web_ui_files"]:
                        structure_lines.append(f"├── {py_file.name}  # Web UI")
                    elif file_path in file_analysis["database_files"]:
                        structure_lines.append(f"├── {py_file.name}  # Database")
                    else:
                        structure_lines.append(f"├── {py_file.name}")

        # Add other directories with enhanced descriptions
        structure_lines.extend(
            [
                "├── web_templates/      # Jinja2 HTML templates and static assets",
                "├── migrations/         # Database migration scripts",
                "templates/              # YAML specification templates",
                "specs/                  # Generated specifications and SQLite database",
                "tests/                  # Unit and integration tests",
                "tools/                  # Utility scripts and automation",
            ]
        )

        # Enhanced overview based on detected components
        overview_parts = [
            "agentic-spec is a Python CLI tool that generates detailed programming specifications using AI"
        ]

        if file_analysis["web_ui_files"]:
            overview_parts.append(
                "with a FastAPI web interface for workflow visualization"
            )
        if file_analysis["database_files"]:
            overview_parts.append("and SQLite database backend for task tracking")

        overview_parts.append(
            "featuring template inheritance and automated review workflows"
        )

        return {
            "overview": " ".join(overview_parts) + ".",
            "structure": "\n".join(structure_lines),
            "functional_requirements": [
                "Generate detailed specifications from high-level prompts",
                "Support hierarchical sub-specifications with parent-child relationships",
                "Enable template inheritance for reusable specification patterns",
                "Provide context-aware AI prompting with user role parameters",
                "Track specification relationships and implementation status",
            ],
            "non_functional_requirements": [
                "Maintain file-based storage for simplicity and transparency",
                "Ensure graceful degradation when AI services are unavailable",
                "Provide comprehensive error handling and informative messages",
                "Support solo developer workflows with minimal setup",
            ],
            "constraints": [
                "Use Python 3.12+ for modern language features",
                "Maintain CLI interface for automation and scripting",
                "Store all data in human-readable YAML format",
                "Avoid external databases to keep deployment simple",
            ],
        }

    def _extract_coding_standards(self, _python_files: list[Path]) -> list[str]:
        """Extract coding standards from Python files."""
        return [
            "Use dataclasses and Pydantic models for data structures",
            "Implement async/await for AI API calls",
            "Follow Python type hints throughout codebase",
            "Use pathlib.Path for all file operations",
            "Implement comprehensive error handling with informative messages",
            "Write unit tests for all new functionality",
            "Use configuration-driven behavior over hard-coded values",
        ]

    def _extract_design_patterns(
        self, python_files: list[Path], file_analysis: dict[str, Any]
    ) -> list[str]:
        """Extract key design patterns from codebase analysis."""
        patterns = [
            "Template inheritance with deep merging strategy",
            "Context-aware AI prompting with parameter injection",
            "Configuration-driven workflow behavior",
            "Graph-based specification relationships",
            "Graceful AI fallback mechanisms",
            "Step-based implementation tracking with unique IDs",
        ]

        # Add patterns based on detected components
        if file_analysis["database_files"]:
            patterns.extend(
                [
                    "Database-backed workflow state management",
                    "Async/await pattern for database operations",
                    "YAML-to-database migration pipeline",
                ]
            )

        if file_analysis["web_ui_files"]:
            patterns.extend(
                [
                    "FastAPI REST API with async endpoints",
                    "Jinja2 template rendering with context injection",
                    "Client-side JavaScript for interactive components",
                    "CSS-based visual hierarchy and status indicators",
                ]
            )

        # Detect async patterns
        async_pattern_found = False
        for py_file in python_files:
            try:
                with py_file.open("r", encoding="utf-8") as f:
                    content = f.read()
                    if "async def" in content and not async_pattern_found:
                        patterns.append("Comprehensive async/await architecture")
                        async_pattern_found = True
                        break
            except (OSError, UnicodeDecodeError):
                continue

        # Detect dataclass/pydantic patterns
        dataclass_pattern_found = False
        for py_file in python_files:
            try:
                with py_file.open("r", encoding="utf-8") as f:
                    content = f.read()
                    if (
                        "@dataclass" in content or "BaseModel" in content
                    ) and not dataclass_pattern_found:
                        patterns.append(
                            "Dataclass and Pydantic model-driven data structures"
                        )
                        dataclass_pattern_found = True
                        break
            except (OSError, UnicodeDecodeError):
                continue

        return patterns

    def check_foundation_sync_needed(self) -> bool:
        """Check if foundation spec needs to be synced with current codebase."""
        try:
            foundation = self.load_template("agentic-spec-foundation")
            last_synced = foundation.get("_last_synced")
            if not last_synced:
                return True

            # Check if significant time has passed since last sync
            from datetime import datetime, timedelta

            last_sync_time = datetime.fromisoformat(last_synced)
            if datetime.now() - last_sync_time > timedelta(days=7):
                return True

            # Check if codebase has changed significantly
            # (Could be enhanced to check git commits, file mtimes, etc.)
            return False

        except (OSError, UnicodeDecodeError, KeyError, ValueError, TypeError):
            # Foundation spec not found or corrupted
            return True

    async def generate_spec(
        self,
        prompt: str,
        inherits: list[str] | None = None,
        project_name: str = "project",
        context_params: ContextParameters | None = None,
        parent_spec_id: str | None = None,
        custom_template: str | None = None,
    ) -> ProgrammingSpec:
        """Generate a detailed programming specification from a prompt."""

        # Create unique ID
        spec_id = hashlib.md5(
            f"{prompt}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:8]

        # Check and sync foundation spec if needed
        if self.check_foundation_sync_needed():
            print("🔄 Foundation spec out of sync, updating...")
            self.sync_foundation_spec()
            print("✅ Foundation spec synced")

        # Resolve comprehensive context (foundation + inheritance + parent)
        comprehensive_context = self.resolve_comprehensive_context(
            inherits, parent_spec_id
        )

        # Legacy support: also keep inherited_context for backward compatibility
        inherited_context = comprehensive_context.get("inherited", {})

        # Use default context parameters if none provided, with config defaults
        if context_params is None:
            context_params = ContextParameters(
                user_role=self.config.default_context.user_role,
                target_audience=self.config.default_context.target_audience,
                desired_tone=self.config.default_context.desired_tone,
                complexity_level=self.config.default_context.complexity_level,
                time_constraints=self.config.default_context.time_constraints,
            )

        # Generate spec using AI if available
        if self.ai_provider and self.ai_provider.is_available:
            spec_data = await self._generate_with_ai(
                prompt,
                comprehensive_context,
                project_name,
                context_params,
                custom_template,
            )
        else:
            spec_data = self._generate_basic(prompt, inherited_context, project_name)

        # Create spec object
        implementation_steps = []
        for i, step_data in enumerate(spec_data.get("implementation", [])):
            # Ensure decomposition_hint is never null - add fallback logic
            if not step_data.get("decomposition_hint"):
                effort = step_data.get("estimated_effort", "medium")
                if effort == "high":
                    step_data["decomposition_hint"] = (
                        "composite: high-effort task requiring breakdown"
                    )
                else:
                    step_data["decomposition_hint"] = "atomic"

            step = ImplementationStep(**step_data)
            step.step_id = f"{spec_id}:{i}"
            implementation_steps.append(step)

        return ProgrammingSpec(
            metadata=SpecMetadata(
                id=spec_id,
                title=self._generate_title_from_prompt(prompt),
                inherits=inherits or [],
                created=datetime.now().isoformat(),
                version="1.0",
                author=os.environ.get("USER")
                or os.environ.get("USERNAME")
                or "unknown",
            ),
            context=SpecContext(**spec_data.get("context", {})),
            requirements=SpecRequirement(**spec_data.get("requirements", {})),
            implementation=implementation_steps,
            context_parameters=context_params,
        )

    async def _generate_with_ai(
        self,
        prompt: str,
        comprehensive_context: dict,
        project_name: str,
        context_params: ContextParameters,
        custom_template: str | None = None,
    ) -> dict:
        """Use AI to generate detailed specification."""

        # Build comprehensive context description
        context_info = ""

        # Foundation context
        if "foundation" in comprehensive_context:
            context_info += f"""
FOUNDATION CONTEXT (Current Codebase):
{yaml.dump(comprehensive_context["foundation"], default_flow_style=False)}

"""

        # Parent spec context
        if "parent" in comprehensive_context:
            context_info += f"""
PARENT SPECIFICATION CONTEXT:
{yaml.dump(comprehensive_context["parent"], default_flow_style=False)}

"""

        # Inherited template context
        if "inherited" in comprehensive_context:
            context_info += f"""
INHERITED TEMPLATE CONTEXT:
{yaml.dump(comprehensive_context["inherited"], default_flow_style=False)}

"""

        if context_info:
            context_info += """
CRITICAL CONTEXT REQUIREMENTS:
1. FOUNDATION CONTEXT contains the current state of the codebase - use this as the source of truth
2. PARENT CONTEXT (if present) shows the broader specification this is part of - maintain consistency
3. INHERITED CONTEXT contains templates and patterns that must be followed
4. Pay special attention to:
   - Existing codebase structure and file organization
   - Current dependencies and versions - do NOT introduce conflicts
   - Established coding standards and design patterns
   - Architectural constraints and project requirements
   - Parent specification requirements and context

You MUST thoroughly analyze and incorporate ALL provided context into your specification."""

        # Load system prompt from template
        try:
            # Use custom template if provided, otherwise use default
            template_name = custom_template or "specification-generation"
            system_prompt = self.prompt_template_loader.render_template(
                template_name,
                context_info=context_info,
                project_name=project_name,
            )
        except (FileNotFoundError, ValueError):
            # Fallback to embedded prompt if template not found
            system_prompt = f"""You are a programming specification generator. Create detailed, implementable specifications from high-level prompts.

CRITICAL INSTRUCTIONS:
1. THOROUGHLY INSPECT AND ANALYZE all provided context (foundation, parent, inherited) below
2. ENSURE your specification aligns with existing project architecture and standards
3. DO NOT contradict or ignore constraints, dependencies, or patterns from ANY context
4. USE web search for current best practices while respecting all contextual constraints
5. REFERENCE specific files, classes, or functions from the existing codebase when relevant
6. MAINTAIN consistency with parent specifications when provided

{context_info}

Project name: {project_name}

SPECIFICATION REQUIREMENTS:
Generate a detailed specification with:
1. Context (project, domain, dependencies, files_involved) - MUST align with inherited context
2. Requirements (functional, non_functional, constraints) - MUST respect inherited constraints
3. Implementation steps (task, details, files, acceptance, estimated_effort) - MUST follow inherited patterns

DEPENDENCY GUIDELINES:
- Use versions compatible with inherited dependencies
- Prefer existing dependencies over introducing new ones
- When new dependencies are needed, justify why existing ones are insufficient

FILE PLACEMENT GUIDELINES:
- Follow the existing codebase structure shown in inherited context
- Place new files in appropriate directories as established by current architecture
- Reference specific existing files when modifications are needed

Return ONLY valid JSON matching this structure:
{{
  "context": {{"project": "...", "domain": "...", "dependencies": [], "files_involved": []}},
  "requirements": {{"functional": [], "non_functional": [], "constraints": []}},
  "implementation": [
    {{"task": "...", "details": "...", "files": [], "acceptance": "...", "estimated_effort": "low|medium|high"}}
  ]
}}"""

        # Build context-aware prompt using the prompt engineer
        # Use inherited context from comprehensive context for backward compatibility
        legacy_inherited_context = comprehensive_context.get("inherited", {})
        enhanced_user_prompt = self.prompt_engineer.build_context_aware_prompt(
            f"Create a detailed programming specification for: {prompt}",
            context_params,
            legacy_inherited_context,
        )

        try:
            # Use Responses API with web search for up-to-date information
            tools = (
                [{"type": "web_search_preview"}]
                if self.config.prompt_settings.enable_web_search
                else []
            )

            content = await self.ai_provider.generate_response(
                prompt=enhanced_user_prompt,
                system_prompt=system_prompt,
                temperature=self.config.prompt_settings.temperature,
                model=self.config.prompt_settings.model,
                tools=tools,
            )
            # Extract JSON from the response if it's wrapped in markdown
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif content.strip().startswith("{") and content.strip().endswith("}"):
                content = content.strip()

            return json.loads(content)

        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
        ) as e:
            print(f"AI generation failed: {e}")
            return self._generate_basic(prompt, legacy_inherited_context, project_name)

    def _generate_basic(
        self, prompt: str, inherited_context: dict, project_name: str
    ) -> dict:
        """Generate basic specification without AI."""
        return {
            "context": {
                "project": inherited_context.get("project", project_name),
                "domain": "general",
                "dependencies": [],
                "files_involved": [],
            },
            "requirements": {
                "functional": [f"Implement: {prompt}"],
                "non_functional": ["Follow coding standards", "Include tests"],
                "constraints": [],
            },
            "implementation": [
                {
                    "task": f"Implement {prompt}",
                    "details": "Implementation details to be refined",
                    "files": [],
                    "acceptance": "Implementation complete and tested",
                    "estimated_effort": "medium",
                }
            ],
        }

    def save_spec(self, spec: ProgrammingSpec) -> Path:
        """Save specification to file."""
        filename = f"{spec.metadata.created[:10]}-{spec.metadata.id}.yaml"
        spec_path = self.specs_dir / filename

        # Update last_modified timestamp
        spec.metadata.last_modified = datetime.now().isoformat()

        with spec_path.open("w") as f:
            yaml.dump(
                spec.model_dump(exclude_none=True),
                f,
                default_flow_style=False,
                sort_keys=False,
            )

        return spec_path

    def load_spec(self, spec_path: Path) -> ProgrammingSpec:
        """Load specification from file."""
        with spec_path.open() as f:
            data = yaml.safe_load(f)

        # Handle backward compatibility for specs without title
        metadata = data["metadata"]
        if "title" not in metadata:
            metadata["title"] = f"Specification {metadata['id']}"
        # Handle backward compatibility for new fields
        if "author" not in metadata:
            metadata["author"] = None
        if "last_modified" not in metadata:
            metadata["last_modified"] = None

        # Fix null decomposition_hints in loaded specs
        implementation_steps = []
        for step_data in data["implementation"]:
            # Ensure decomposition_hint is never null - add fallback logic
            if not step_data.get("decomposition_hint"):
                effort = step_data.get("estimated_effort", "medium")
                if effort == "high":
                    step_data["decomposition_hint"] = (
                        "composite: high-effort task requiring breakdown"
                    )
                else:
                    step_data["decomposition_hint"] = "atomic"
            implementation_steps.append(ImplementationStep(**step_data))

        return ProgrammingSpec(
            metadata=SpecMetadata(**metadata),
            context=SpecContext(**data["context"]),
            requirements=SpecRequirement(**data["requirements"]),
            implementation=implementation_steps,
            review_notes=data.get("review_notes", []),
        )

    async def review_spec(self, spec: ProgrammingSpec) -> list[str]:
        """AI-powered specification review for solo developer workflow."""
        if not self.ai_provider or not self.ai_provider.is_available:
            return ["Manual review required - AI not available"]

        # Load system prompt from template
        try:
            system_prompt = self.prompt_template_loader.render_template(
                "specification-review"
            )
        except (FileNotFoundError, ValueError):
            # Fallback to embedded prompt if template not found
            system_prompt = """You are a pragmatic senior developer reviewing a specification for a solo developer.

IMPORTANT: When reviewing, consider current best practices, library versions, and implementation patterns. If needed, use web search to verify that the proposed approach uses up-to-date libraries and follows current standards.

Focus ONLY on practical implementation concerns:

1. **Missing Implementation Details** - Are there gaps that would block coding?
2. **Technical Gotchas** - What specific technical challenges should be anticipated?
3. **Integration Points** - How does this connect with existing code? Any conflicts?
4. **Scope Creep** - Is this too ambitious for a single feature? Should it be broken down?
5. **Quick Wins** - Are there simpler approaches that accomplish the same goal?
6. **Current Best Practices** - Are the suggested libraries and approaches current and well-maintained?

Provide 2-4 concise, actionable insights. Skip generic advice about user stories, dependency compatibility, or enterprise testing practices. Focus on what a solo developer actually needs to know to implement this successfully.

Return a simple JSON array of strings - no markdown formatting."""

        spec_yaml = yaml.dump(
            spec.model_dump(exclude_none=True), default_flow_style=False
        )

        try:
            # Use AI provider with web search for current best practices
            content = await self.ai_provider.generate_response(
                prompt=f"Review this specification:\n\n{spec_yaml}",
                system_prompt=system_prompt,
                temperature=0.1,
                model="gpt-4.1",  # Use model that supports web search
                tools=[
                    {"type": "web_search_preview"}
                ],  # Enable web search for current practices
            )
            # Try to parse as JSON, fallback to text
            try:
                return json.loads(content)
            except (json.JSONDecodeError, ValueError, TypeError):
                return [content]

        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            AttributeError,
        ) as e:
            return [f"Review failed: {e}"]

    async def generate_sub_spec(
        self,
        parent_spec: ProgrammingSpec,
        step_id: str,
        max_depth: int = 3,
        visited_specs: set[str] | None = None,
    ) -> ProgrammingSpec | None:
        """Generate a detailed sub-specification for a specific implementation step."""

        if visited_specs is None:
            visited_specs = set()

        # Cycle detection
        if parent_spec.metadata.id in visited_specs or len(visited_specs) >= max_depth:
            return None

        visited_specs.add(parent_spec.metadata.id)

        # Find the implementation step
        target_step = None
        step_index = None

        # Handle both legacy specs (no step_id) and new specs (with step_id)
        if ":" in step_id:
            spec_part, index_part = step_id.rsplit(":", 1)
            try:
                step_index = int(index_part)
                if 0 <= step_index < len(parent_spec.implementation):
                    target_step = parent_spec.implementation[step_index]
                    # Assign step_id if it doesn't exist (for legacy specs)
                    if not target_step.step_id:
                        target_step.step_id = step_id
            except ValueError:
                # Try to find by exact step_id match
                for step in parent_spec.implementation:
                    if step.step_id == step_id:
                        target_step = step
                        break

        if not target_step:
            return None

        # Generate sub-spec ID
        sub_spec_id = hashlib.md5(
            f"{parent_spec.metadata.id}:{step_id}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:8]

        # Create detailed prompt for the sub-specification using template
        try:
            sub_prompt = self.prompt_template_loader.render_template(
                "step-expansion",
                parent_spec_id=parent_spec.metadata.id,
                step_task=target_step.task,
                step_details=target_step.details,
                step_files=", ".join(target_step.files),
                step_acceptance=target_step.acceptance,
                step_effort=target_step.estimated_effort,
                parent_project=parent_spec.context.project,
                parent_domain=parent_spec.context.domain,
            )
        except (FileNotFoundError, ValueError):
            # Fallback to embedded prompt if template not found
            sub_prompt = f"""
        Expand this implementation step into a detailed sub-specification:

        Parent Spec: {parent_spec.metadata.id}
        Step: {target_step.task}
        Details: {target_step.details}
        Files: {", ".join(target_step.files)}

        Context from parent spec:
        - Project: {parent_spec.context.project}
        - Domain: {parent_spec.context.domain}

        Create a focused sub-specification that breaks down this step into concrete, actionable tasks.
        """

        # Generate the sub-specification
        sub_spec = await self.generate_spec(
            sub_prompt, inherits=[], project_name=parent_spec.context.project
        )

        # Update relationships
        sub_spec.metadata.id = sub_spec_id
        sub_spec.metadata.parent_spec_id = parent_spec.metadata.id

        # Assign step IDs to implementation steps
        for i, step in enumerate(sub_spec.implementation):
            step.step_id = f"{sub_spec_id}:{i}"

        # Update parent step to reference sub-spec
        target_step.sub_spec_id = sub_spec_id

        # Update parent's child list
        if parent_spec.metadata.child_spec_ids is None:
            parent_spec.metadata.child_spec_ids = []
        if sub_spec_id not in parent_spec.metadata.child_spec_ids:
            parent_spec.metadata.child_spec_ids.append(sub_spec_id)

        return sub_spec

    def get_spec_graph(self) -> dict[str, dict[str, Any]]:
        """Build a graph of all specifications and their relationships."""
        specs = {}

        # Load all specs from directory
        for spec_file in self.specs_dir.glob("*.yaml"):
            try:
                spec = self.load_spec(spec_file)
                specs[spec.metadata.id] = {
                    "spec": spec,
                    "file_path": spec_file,
                    "parent": spec.metadata.parent_spec_id,
                    "children": spec.metadata.child_spec_ids or [],
                }
            except (OSError, UnicodeDecodeError, ValueError, KeyError) as e:
                print(f"Error loading {spec_file}: {e}")

        return specs

    def find_spec_by_id(self, spec_id: str) -> ProgrammingSpec | None:
        """Find a specification by its ID."""
        for spec_file in self.specs_dir.glob("*.yaml"):
            try:
                spec = self.load_spec(spec_file)
                if spec.metadata.id == spec_id:
                    return spec
            except (OSError, UnicodeDecodeError, ValueError, KeyError):
                continue
        return None

    # Migration functionality for database backfill

    def discover_yaml_files(self, full_migration: bool = True) -> list[Path]:
        """Discover YAML specification files for migration.

        Args:
            full_migration: If True, return all files. If False, return only new/changed files.

        Returns:
            List of Path objects for YAML files to process.
        """
        # Get all YAML files in specs directory
        all_files = list(self.specs_dir.glob("*.yaml"))

        # Filter out non-specification files
        spec_files = []
        for file_path in all_files:
            # Skip documentation files
            if file_path.name in ["yaml-to-db-mapping.yaml", "migration-plan.yaml"]:
                continue

            # Skip files that don't parse as valid specifications
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                # Check if it looks like a specification (has required fields)
                if (
                    isinstance(data, dict)
                    and "metadata" in data
                    and "context" in data
                    and "requirements" in data
                    and "implementation" in data
                ):
                    spec_files.append(file_path)

            except (yaml.YAMLError, UnicodeDecodeError, KeyError, TypeError):
                # Skip invalid YAML files
                continue

        if full_migration:
            return spec_files

        # For incremental migration, check change detection
        return self._detect_changed_files(spec_files)

    def _detect_changed_files(self, spec_files: list[Path]) -> list[Path]:
        """Detect which files have changed since last migration.

        Args:
            spec_files: List of all specification files

        Returns:
            List of files that are new or have changed
        """
        migration_state_file = self.specs_dir / ".migration_state.json"

        # Load previous migration state
        previous_state = {}
        if migration_state_file.exists():
            try:
                with open(migration_state_file, encoding="utf-8") as f:
                    previous_state = json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError):
                # If state file is corrupted, treat as full migration
                previous_state = {}

        changed_files = []
        current_state = {}

        for file_path in spec_files:
            try:
                # Calculate file hash for change detection
                file_hash = self._calculate_file_hash(file_path)
                current_state[str(file_path)] = {
                    "hash": file_hash,
                    "modified": file_path.stat().st_mtime,
                    "size": file_path.stat().st_size,
                }

                # Check if file is new or changed
                file_key = str(file_path)
                if (
                    file_key not in previous_state
                    or previous_state[file_key].get("hash") != file_hash
                ):
                    changed_files.append(file_path)

            except (OSError, PermissionError):
                # If we can't read the file, include it for migration attempt
                changed_files.append(file_path)

        # Update migration state
        try:
            with open(migration_state_file, "w", encoding="utf-8") as f:
                json.dump(current_state, f, indent=2)
        except (OSError, PermissionError):
            # Log warning but continue - state tracking is optional
            pass

        return changed_files

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of file contents for change detection.

        Args:
            file_path: Path to file

        Returns:
            MD5 hash as hex string
        """
        hasher = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                # Read file in chunks to handle large files
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
        except (OSError, PermissionError):
            # If we can't read file, use file stats as fallback
            stat = file_path.stat()
            fallback_data = f"{file_path.name}{stat.st_size}{stat.st_mtime}".encode()
            hasher.update(fallback_data)

        return hasher.hexdigest()

    def validate_yaml_file(
        self, file_path: Path
    ) -> tuple[bool, dict[str, Any] | None, str | None]:
        """Validate a YAML file against our specification schema.

        Args:
            file_path: Path to YAML file to validate

        Returns:
            Tuple of (is_valid, parsed_data, error_message)
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            # Basic structure validation
            if not isinstance(data, dict):
                return False, None, "Root element must be a dictionary"

            # Check required top-level fields
            required_fields = ["metadata", "context", "requirements", "implementation"]
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return (
                    False,
                    None,
                    f"Missing required fields: {', '.join(missing_fields)}",
                )

            # Try to parse with our ProgrammingSpec model for full validation
            try:
                spec = ProgrammingSpec.from_dict(data)
                # If we get here, the spec is fully valid
                return True, data, None

            except (ValueError, TypeError, KeyError):
                # ProgrammingSpec validation failed, do basic validation
                return self._basic_validation(data)

        except yaml.YAMLError as e:
            return False, None, f"YAML parsing error: {e!s}"
        except (UnicodeDecodeError, OSError) as e:
            return False, None, f"File reading error: {e!s}"
        except Exception as e:
            return False, None, f"Unexpected error: {e!s}"

    def _basic_validation(
        self, data: dict[str, Any]
    ) -> tuple[bool, dict[str, Any] | None, str | None]:
        """Perform basic validation when Pydantic validation fails.

        Args:
            data: Parsed YAML data

        Returns:
            Tuple of (is_valid, data, error_message)
        """
        # Validate metadata structure
        metadata = data.get("metadata", {})
        required_metadata = ["id", "title", "created", "version"]
        missing_metadata = [
            field for field in required_metadata if field not in metadata
        ]
        if missing_metadata:
            return (
                False,
                None,
                f"Missing metadata fields: {', '.join(missing_metadata)}",
            )

        # Validate context structure
        context = data.get("context", {})
        required_context = ["project", "domain"]
        missing_context = [field for field in required_context if field not in context]
        if missing_context:
            return False, None, f"Missing context fields: {', '.join(missing_context)}"

        # Validate requirements structure
        requirements = data.get("requirements", {})
        required_requirements = ["functional", "non_functional"]
        missing_requirements = [
            field for field in required_requirements if field not in requirements
        ]
        if missing_requirements:
            return (
                False,
                None,
                f"Missing requirements fields: {', '.join(missing_requirements)}",
            )

        # Validate implementation structure
        implementation = data.get("implementation", [])
        if not isinstance(implementation, list):
            return False, None, "Implementation must be a list"

        # Validate each implementation step
        for i, step in enumerate(implementation):
            if not isinstance(step, dict):
                return False, None, f"Implementation step {i} must be a dictionary"

            required_step_fields = ["task", "details", "files", "acceptance"]
            missing_step_fields = [
                field for field in required_step_fields if field not in step
            ]
            if missing_step_fields:
                return (
                    False,
                    None,
                    f"Step {i} missing fields: {', '.join(missing_step_fields)}",
                )

        # Basic validation passed, but note that Pydantic validation failed
        return True, data, "Basic validation passed, but some data may be malformed"

    async def migrate_specifications(
        self,
        full_migration: bool = True,
        dry_run: bool = False,
        progress_callback: callable = None,
    ) -> dict[str, Any]:
        """Migrate YAML specifications to database using AsyncSpecManager.

        Args:
            full_migration: If True, migrate all files. If False, only new/changed files.
            dry_run: If True, validate but don't actually migrate
            progress_callback: Optional callback for progress updates

        Returns:
            Migration results dictionary with statistics and errors
        """
        from .async_db import AsyncSpecManager, SQLiteBackend
        from .db import FileBasedSpecStorage

        # Initialize results tracking
        results = {
            "total_files": 0,
            "valid_files": 0,
            "migrated_files": 0,
            "errors": [],
            "warnings": [],
            "skipped_files": [],
            "migration_start": datetime.now().isoformat(),
            "migration_end": None,
            "dry_run": dry_run,
        }

        try:
            # Discover files to migrate
            files_to_migrate = self.discover_yaml_files(full_migration=full_migration)
            results["total_files"] = len(files_to_migrate)

            if progress_callback:
                progress_callback(
                    f"Discovered {len(files_to_migrate)} files for migration"
                )

            # Initialize database backend
            db_path = self.specs_dir / "specifications.db"
            backend = SQLiteBackend(str(db_path))

            # Initialize file storage for comparison
            file_storage = FileBasedSpecStorage(self.specs_dir)

            # Process files in batches
            batch_size = 10
            migrated_count = 0

            async with AsyncSpecManager(backend) as spec_manager:
                for i in range(0, len(files_to_migrate), batch_size):
                    batch = files_to_migrate[i : i + batch_size]

                    for file_path in batch:
                        try:
                            # Progress update
                            if progress_callback:
                                progress_callback(f"Processing {file_path.name}...")

                            # Validate file
                            is_valid, data, error = self.validate_yaml_file(file_path)
                            if not is_valid:
                                results["errors"].append(
                                    {
                                        "file": str(file_path),
                                        "error": f"Validation failed: {error}",
                                    }
                                )
                                continue

                            results["valid_files"] += 1

                            if error:  # Warning from basic validation
                                results["warnings"].append(
                                    {"file": str(file_path), "warning": error}
                                )

                            # Convert YAML data to database format
                            try:
                                migration_result = await self._migrate_single_spec(
                                    spec_manager, data, file_path, dry_run
                                )

                                if migration_result["success"]:
                                    migrated_count += 1
                                    results["migrated_files"] += 1
                                else:
                                    results["errors"].append(
                                        {
                                            "file": str(file_path),
                                            "error": migration_result["error"],
                                        }
                                    )

                            except Exception as e:
                                results["errors"].append(
                                    {
                                        "file": str(file_path),
                                        "error": f"Migration error: {e!s}",
                                    }
                                )

                        except Exception as e:
                            results["errors"].append(
                                {
                                    "file": str(file_path),
                                    "error": f"Processing error: {e!s}",
                                }
                            )

                    # Progress update after batch
                    if progress_callback:
                        progress_callback(
                            f"Processed {min(i + batch_size, len(files_to_migrate))}/{len(files_to_migrate)} files"
                        )

        except Exception as e:
            results["errors"].append(
                {"file": "SYSTEM", "error": f"Migration system error: {e!s}"}
            )

        results["migration_end"] = datetime.now().isoformat()

        if progress_callback:
            progress_callback(
                f"Migration completed: {results['migrated_files']}/{results['total_files']} files migrated"
            )

        return results

    async def _migrate_single_spec(
        self,
        spec_manager: "AsyncSpecManager",
        data: dict[str, Any],
        file_path: Path,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Migrate a single specification to the database.

        Args:
            spec_manager: AsyncSpecManager instance
            data: Parsed YAML data
            file_path: Path to source file
            dry_run: If True, validate but don't insert

        Returns:
            Migration result dictionary
        """
        try:
            # Create ProgrammingSpec object for conversion
            spec = ProgrammingSpec.from_dict(data)

            # Convert to database format
            spec_db = await self._convert_spec_to_db(spec, file_path)

            if dry_run:
                return {"success": True, "action": "validated", "spec_id": spec_db.id}

            # Check if spec already exists to determine action
            existing_spec = await spec_manager.get_specification(spec.metadata.id)
            action = "updated" if existing_spec else "created"

            # Use save_spec_to_db which handles both specification and tasks
            await spec_manager.save_spec_to_db(spec)

            return {"success": True, "action": action, "spec_id": spec.metadata.id}

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "spec_id": data.get("metadata", {}).get("id", "unknown"),
            }

    async def _convert_spec_to_db(
        self, spec: ProgrammingSpec, file_path: Path
    ) -> "SpecificationDB":
        """Convert ProgrammingSpec to SpecificationDB format.

        Args:
            spec: ProgrammingSpec object
            file_path: Source file path for metadata

        Returns:
            SpecificationDB object
        """
        from datetime import datetime

        from .models import (
            ApprovalDB,
            SpecificationDB,
            SpecStatus,
            TaskDB,
            TaskStatus,
            WorkLogDB,
        )

        # Convert datetime string to datetime object
        created_dt = datetime.fromisoformat(
            spec.metadata.created.replace("Z", "+00:00")
        )
        updated_dt = datetime.fromtimestamp(file_path.stat().st_mtime)

        # Convert status to enum
        try:
            status = SpecStatus(spec.metadata.status.lower())
        except ValueError:
            status = SpecStatus.DRAFT

        # Create task records
        tasks = []
        work_logs = []

        for i, step in enumerate(spec.implementation):
            # Generate task ID if missing
            task_id = step.step_id or f"{spec.metadata.id}:{i}"

            # Convert task status
            task_status = TaskStatus.PENDING
            started_at = None
            completed_at = None
            time_spent = None
            completion_notes = None
            blockers = []

            if step.progress:
                try:
                    task_status = TaskStatus(step.progress.status.value)
                    started_at = step.progress.started_at
                    completed_at = step.progress.completed_at
                    time_spent = step.progress.time_spent_minutes
                    completion_notes = step.progress.completion_notes
                    blockers = step.progress.blockers if step.progress.blockers else []
                except (ValueError, AttributeError):
                    pass

            task_db = TaskDB(
                id=task_id,
                spec_id=spec.metadata.id,
                step_index=i,
                task=step.task,
                details=step.details,
                files=step.files,
                acceptance=step.acceptance,
                estimated_effort=step.estimated_effort,
                sub_spec_id=step.sub_spec_id,
                decomposition_hint=step.decomposition_hint,
                status=task_status,
                started_at=started_at,
                completed_at=completed_at,
                time_spent_minutes=time_spent,
                completion_notes=completion_notes,
                blockers=blockers,
            )

            # Convert approvals if present
            if step.approvals:
                for approval in step.approvals:
                    approval_db = ApprovalDB(
                        id=str(uuid.uuid4()),
                        task_id=task_id,
                        level=approval.level,
                        approved_by=approval.approved_by,
                        approved_at=approval.approved_at,
                        comments=approval.comments,
                        override_reason=approval.override_reason,
                    )
                    task_db.approvals.append(approval_db)

            tasks.append(task_db)

        # Convert work logs if present
        if spec.work_logs:
            for log in spec.work_logs:
                work_log_db = WorkLogDB(
                    id=str(uuid.uuid4()),
                    spec_id=spec.metadata.id,
                    task_id=log.step_id if hasattr(log, "step_id") else None,
                    action=log.action,
                    timestamp=log.timestamp,
                    duration_minutes=log.duration_minutes,
                    notes=log.notes,
                    metadata=log.metadata or {},
                )
                work_logs.append(work_log_db)

        # Create specification DB record
        spec_db = SpecificationDB(
            id=spec.metadata.id,
            title=spec.metadata.title,
            inherits=spec.metadata.inherits,
            created=created_dt,
            updated=updated_dt,
            version=spec.metadata.version,
            status=status,
            parent_spec_id=spec.metadata.parent_spec_id,
            child_spec_ids=spec.metadata.child_spec_ids
            if spec.metadata.child_spec_ids
            else [],
            context=spec.context.model_dump(exclude_none=True),
            requirements=spec.requirements.model_dump(exclude_none=True),
            review_notes=spec.review_notes or [],
            context_parameters=spec.context_parameters.model_dump(exclude_none=True)
            if spec.context_parameters
            else None,
            tasks=tasks,
            work_logs=work_logs,
        )

        return spec_db

    async def expand_step(self, spec_id: str, step_index: int) -> ProgrammingSpec:
        """Expand a specific implementation step into a detailed sub-specification.

        Args:
            spec_id: ID of the parent specification
            step_index: Index of the step to expand (0-based)

        Returns:
            ProgrammingSpec: New sub-specification for the expanded step

        Raises:
            FileNotFoundError: If the parent specification doesn't exist
            IndexError: If the step index is out of range
            AIServiceError: If AI generation fails
        """
        # Load the parent specification
        parent_spec = self.find_spec_by_id(spec_id)
        if not parent_spec:
            raise FileNotFoundError(f"Specification {spec_id} not found")

        # Validate step index
        if step_index < 0 or step_index >= len(parent_spec.implementation):
            raise IndexError(f"Step index {step_index} out of range for spec {spec_id}")

        target_step = parent_spec.implementation[step_index]

        # Create a detailed prompt for expanding this specific step
        expansion_prompt = f"""
Expand the following implementation step into a comprehensive sub-specification:

**Parent Specification**: {parent_spec.metadata.title}
**Step to Expand**: {target_step.task}
**Step Details**: {target_step.details}
**Files Involved**: {", ".join(target_step.files)}
**Acceptance Criteria**: {target_step.acceptance}

**Context from Parent Project**:
- Project: {parent_spec.context.project}
- Domain: {parent_spec.context.domain}
- Dependencies: {[f"{dep.get('name', 'unknown') if isinstance(dep, dict) else str(dep)}@{dep.get('version', 'latest') if isinstance(dep, dict) else 'latest'}" for dep in parent_spec.context.dependencies]}

Create a detailed specification that breaks down this step into:
1. Clear sub-tasks with specific implementation details
2. Proper file organization and structure
3. Testing requirements and acceptance criteria
4. Error handling and edge cases
5. Integration points with the parent system

The sub-specification should be comprehensive enough that a developer can implement it independently while maintaining compatibility with the parent specification.
"""

        # Generate the expanded specification using AI
        if self.ai_provider:
            # Build context parameters
            context_params = ContextParameters(
                user_role=self.config.default_context.user_role,
                target_audience=self.config.default_context.target_audience,
                desired_tone=self.config.default_context.desired_tone,
                complexity_level=self.config.default_context.complexity_level,
                time_constraints=self.config.default_context.time_constraints,
            )

            # Build comprehensive context
            comprehensive_context = {
                "project": parent_spec.context.project,
                "domain": parent_spec.context.domain,
                "dependencies": parent_spec.context.dependencies,
                "parent_spec": parent_spec.metadata.title,
                "step_context": {
                    "task": target_step.task,
                    "details": target_step.details,
                    "files": target_step.files,
                    "acceptance": target_step.acceptance,
                },
            }

            # Generate using AI
            spec_data = await self._generate_with_ai(
                expansion_prompt,
                comprehensive_context,
                parent_spec.context.project,
                context_params,
            )

            # Convert AI response to ProgrammingSpec
            expanded_id = hashlib.md5(
                f"{target_step.task}{datetime.now().isoformat()}".encode()
            ).hexdigest()[:8]

            # Create implementation steps
            implementation_steps = []
            for i, step_data in enumerate(spec_data.get("implementation", [])):
                # Ensure decomposition_hint is never null
                if not step_data.get("decomposition_hint"):
                    effort = step_data.get("estimated_effort", "medium")
                    if effort == "high":
                        step_data["decomposition_hint"] = (
                            "composite: high-effort task requiring breakdown"
                        )
                    else:
                        step_data["decomposition_hint"] = "atomic"

                step = ImplementationStep(**step_data)
                step.step_id = f"{expanded_id}:{i}"
                implementation_steps.append(step)

            # Prepare context data with dependency format normalization
            default_context = {
                "project": parent_spec.context.project,
                "domain": f"{parent_spec.context.domain} - {target_step.task}",
                "dependencies": parent_spec.context.dependencies,
                "files_involved": target_step.files,
            }

            # Merge with AI-generated context, but normalize dependencies
            context_data = {**default_context, **spec_data.get("context", {})}

            # Normalize dependencies to proper format if they're strings
            if "dependencies" in context_data:
                normalized_deps = []
                for dep in context_data["dependencies"]:
                    if isinstance(dep, str):
                        # Convert string format 'name@version' to dict format
                        if "@" in dep:
                            name, version = dep.split("@", 1)
                            # Convert 'None' string to actual None
                            if version == "None":
                                version = None
                            normalized_deps.append({"name": name, "version": version})
                        else:
                            normalized_deps.append({"name": dep})
                    elif isinstance(dep, dict):
                        # Already in correct format
                        normalized_deps.append(dep)
                    else:
                        # DependencyModel or other type, keep as-is
                        normalized_deps.append(dep)
                context_data["dependencies"] = normalized_deps

            expanded_spec = ProgrammingSpec(
                metadata=SpecMetadata(
                    id=expanded_id,
                    title=spec_data.get("title", f"Expanded: {target_step.task}"),
                    inherits=parent_spec.metadata.inherits,
                    created=datetime.now().isoformat(),
                    version="1.0",
                    status="draft",
                    parent_spec_id=spec_id,
                    child_spec_ids=None,
                    author=os.environ.get("USER")
                    or os.environ.get("USERNAME")
                    or "unknown",
                    last_modified=None,
                ),
                context=SpecContext(**context_data),
                requirements=SpecRequirement(
                    **spec_data.get(
                        "requirements",
                        {
                            "functional": [
                                f"Complete implementation of: {target_step.task}"
                            ],
                            "non_functional": ["Code should follow project standards"],
                            "constraints": [
                                "Must be compatible with parent specification"
                            ],
                        },
                    )
                ),
                implementation=implementation_steps,
                review_notes=spec_data.get("review_notes", []),
                context_parameters=context_params,
            )
        else:
            # Fallback to basic generation if AI is not available
            expanded_spec = self._create_basic_expanded_spec(
                parent_spec, target_step, step_index
            )

        # Set up parent-child relationship
        expanded_spec.metadata.parent_spec_id = spec_id
        target_step.sub_spec_id = expanded_spec.metadata.id

        # Update parent spec's child list
        if not parent_spec.metadata.child_spec_ids:
            parent_spec.metadata.child_spec_ids = []
        if expanded_spec.metadata.id not in parent_spec.metadata.child_spec_ids:
            parent_spec.metadata.child_spec_ids.append(expanded_spec.metadata.id)

        # Save both specifications
        self.save_spec(expanded_spec)
        self.save_spec(parent_spec)

        return expanded_spec

    def _create_basic_expanded_spec(
        self,
        parent_spec: ProgrammingSpec,
        target_step: ImplementationStep,
        step_index: int,
    ) -> ProgrammingSpec:
        """Create a basic expanded specification when AI is not available."""
        expanded_id = hashlib.md5(
            f"{target_step.task}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:8]

        # Create basic implementation steps by splitting the task
        basic_steps = [
            ImplementationStep(
                task=f"Plan and design {target_step.task.lower()}",
                details=f"Create detailed design and planning for: {target_step.details}",
                files=["design.md", "planning.md"],
                acceptance="Design is complete and approved",
                estimated_effort="low",
            ),
            ImplementationStep(
                task=f"Implement core functionality for {target_step.task.lower()}",
                details=f"Build the main implementation: {target_step.details}",
                files=target_step.files,
                acceptance=target_step.acceptance,
                estimated_effort="high",
            ),
            ImplementationStep(
                task=f"Test {target_step.task.lower()}",
                details=f"Create and run tests for: {target_step.task}",
                files=[f"test_{f}" for f in target_step.files if f.endswith(".py")]
                + ["tests/"],
                acceptance="All tests pass with good coverage",
                estimated_effort="medium",
            ),
            ImplementationStep(
                task=f"Document {target_step.task.lower()}",
                details=f"Create documentation for: {target_step.task}",
                files=["README.md", "docs/"],
                acceptance="Documentation is complete and clear",
                estimated_effort="low",
            ),
        ]

        # Add step IDs
        for i, step in enumerate(basic_steps):
            step.step_id = f"{expanded_id}:{i}"

        expanded_spec = ProgrammingSpec(
            metadata=SpecMetadata(
                id=expanded_id,
                title=f"Expanded: {target_step.task}",
                inherits=parent_spec.metadata.inherits,
                created=datetime.now().isoformat(),
                version="1.0",
                status="draft",
                parent_spec_id=parent_spec.metadata.id,
                child_spec_ids=None,
                author=os.environ.get("USER")
                or os.environ.get("USERNAME")
                or "unknown",
                last_modified=None,
            ),
            context=SpecContext(
                project=parent_spec.context.project,
                domain=f"{parent_spec.context.domain} - {target_step.task}",
                dependencies=parent_spec.context.dependencies,
                files_involved=target_step.files,
            ),
            requirements=SpecRequirement(
                functional=[
                    f"Complete implementation of: {target_step.task}",
                    f"Meet acceptance criteria: {target_step.acceptance}",
                    "Integrate properly with parent specification",
                ],
                non_functional=[
                    "Code should follow project standards",
                    "Implementation should be well-tested",
                    "Documentation should be comprehensive",
                ],
                constraints=[
                    "Must be compatible with parent specification",
                    "Should follow existing project patterns",
                ],
            ),
            implementation=basic_steps,
            review_notes=[
                "This is a basic expansion - consider using AI generation for more detailed specifications",
                f"Expanded from parent spec {parent_spec.metadata.id}, step {step_index}",
            ],
        )

        return expanded_spec
