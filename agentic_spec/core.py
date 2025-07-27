"""Core specification generation functionality."""

from dataclasses import asdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any
import uuid

import yaml

from .ai_providers import AIProviderFactory
from .config import AgenticSpecConfig
from .exceptions import ConfigurationError
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


class SpecGenerator:
    """Generates programming specifications from prompts with inheritance."""

    def __init__(
        self,
        spec_templates_dir: Path,
        specs_dir: Path,
        config: AgenticSpecConfig | None = None,
    ):
        self.spec_templates_dir = spec_templates_dir
        self.specs_dir = specs_dir
        self.spec_templates_dir.mkdir(parents=True, exist_ok=True)
        self.specs_dir.mkdir(parents=True, exist_ok=True)
        self.config = config or AgenticSpecConfig()

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
            # Simple deep merge - could be enhanced
            self._deep_merge(merged, template)

        return merged

    def _deep_merge(self, target: dict, source: dict):
        """Deep merge dictionaries."""
        for key, value in source.items():
            if (
                key in target
                and isinstance(target[key], dict)
                and isinstance(value, dict)
            ):
                self._deep_merge(target[key], value)
            else:
                target[key] = value

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
            self._deep_merge(context, {"foundation": foundation_context})
        except (FileNotFoundError, KeyError, ValueError):
            # Foundation spec not found - this indicates it needs to be synced
            context["foundation_sync_needed"] = True

        # 2. Load inherited template context
        inherited_context = self.resolve_inheritance(inherits or [])
        if inherited_context:
            self._deep_merge(context, {"inherited": inherited_context})

        # 3. Load parent spec context if provided
        if parent_spec_id:
            parent_spec = self.find_spec_by_id(parent_spec_id)
            if parent_spec:
                parent_context = self.load_parent_spec_context(parent_spec)
                if parent_context:
                    self._deep_merge(context, {"parent": parent_context})

        return context

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

        # Analyze Python files
        python_files = list(project_root.rglob("*.py"))

        # Analyze dependencies from pyproject.toml
        dependencies = self._extract_dependencies(project_root)

        # Analyze architecture from file structure
        architecture = self._analyze_architecture(project_root)

        # Generate foundation data
        return {
            "context": {
                "project": "agentic-spec",
                "domain": "Python CLI tool for AI-powered specification generation",
                "dependencies": dependencies,
                "architecture_overview": architecture["overview"],
                "current_codebase_structure": architecture["structure"],
            },
            "requirements": {
                "functional": architecture["functional_requirements"],
                "non_functional": architecture["non_functional_requirements"],
                "constraints": architecture["constraints"],
            },
            "coding_standards": self._extract_coding_standards(python_files),
            "key_design_patterns": self._extract_design_patterns(python_files),
            "_last_synced": datetime.now().isoformat(),
            "_sync_version": "1.0",
        }

    def _extract_dependencies(self, project_root: Path) -> list[dict[str, str]]:
        """Extract dependencies from pyproject.toml."""
        try:
            import tomllib

            pyproject_path = project_root / "pyproject.toml"
            if pyproject_path.exists():
                with pyproject_path.open("rb") as f:
                    data = tomllib.load(f)

                dependencies = []
                # Main dependencies
                for dep in data.get("project", {}).get("dependencies", []):
                    name = dep.split(">=")[0].split(">")[0].split("==")[0]
                    version = dep.split(">=")[1] if ">=" in dep else "latest"
                    dependencies.append(
                        {
                            "name": name,
                            "version": version,
                            "description": f"Core dependency: {name}",
                        }
                    )

                return dependencies
        except (OSError, ImportError, KeyError, ValueError, TypeError):
            pass

        # Fallback basic dependencies
        return [
            {
                "name": "Python",
                "version": "3.12+",
                "description": "Core programming language",
            },
            {
                "name": "PyYAML",
                "version": "6.0+",
                "description": "YAML parsing and generation",
            },
            {"name": "OpenAI", "version": "1.97+", "description": "AI integration"},
        ]

    def _analyze_architecture(self, project_root: Path) -> dict[str, Any]:
        """Analyze project architecture from file structure."""
        src_dir = project_root / "agentic_spec"

        structure_lines = ["agentic_spec/"]
        if src_dir.exists():
            for py_file in sorted(src_dir.glob("*.py")):
                if py_file.name != "__init__.py":
                    structure_lines.append(f"├── {py_file.name}")

        structure_lines.extend(
            [
                "templates/              # YAML template files",
                "specs/                  # Generated specification files",
                "tests/                  # Test files",
            ]
        )

        return {
            "overview": (
                "agentic-spec is a Python CLI tool that generates detailed programming "
                "specifications using AI with template inheritance and review workflows."
            ),
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

    def _extract_design_patterns(self, _python_files: list[Path]) -> list[str]:
        """Extract key design patterns from codebase."""
        return [
            "Template inheritance with deep merging strategy",
            "Context-aware AI prompting with parameter injection",
            "Configuration-driven workflow behavior",
            "Graph-based specification relationships",
            "Graceful AI fallback mechanisms",
            "Step-based implementation tracking with unique IDs",
        ]

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

        with spec_path.open("w") as f:
            yaml.dump(asdict(spec), f, default_flow_style=False, sort_keys=False)

        return spec_path

    def load_spec(self, spec_path: Path) -> ProgrammingSpec:
        """Load specification from file."""
        with spec_path.open() as f:
            data = yaml.safe_load(f)

        # Handle backward compatibility for specs without title
        metadata = data["metadata"]
        if "title" not in metadata:
            metadata["title"] = f"Specification {metadata['id']}"

        return ProgrammingSpec(
            metadata=SpecMetadata(**metadata),
            context=SpecContext(**data["context"]),
            requirements=SpecRequirement(**data["requirements"]),
            implementation=[
                ImplementationStep(**step) for step in data["implementation"]
            ],
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

        spec_yaml = yaml.dump(asdict(spec), default_flow_style=False)

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
            context=spec.context.to_dict(),
            requirements=spec.requirements.to_dict(),
            review_notes=spec.review_notes or [],
            context_parameters=spec.context_parameters.to_dict()
            if spec.context_parameters
            else None,
            tasks=tasks,
            work_logs=work_logs,
        )

        return spec_db
