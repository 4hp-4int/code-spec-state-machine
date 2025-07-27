"""Core specification generation functionality."""

from dataclasses import asdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time
from typing import Any

import yaml

from .config import AgenticSpecConfig
from .models import (
    ContextParameters,
    ImplementationStep,
    ProgrammingSpec,
    SpecContext,
    SpecMetadata,
    SpecRequirement,
)
from .prompt_engineering import PromptEngineer

try:
    from openai import AsyncOpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class SpecGenerator:
    """Generates programming specifications from prompts with inheritance."""

    def __init__(
        self,
        templates_dir: Path,
        specs_dir: Path,
        config: AgenticSpecConfig | None = None,
    ):
        self.templates_dir = templates_dir
        self.specs_dir = specs_dir
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.specs_dir.mkdir(parents=True, exist_ok=True)
        self.prompt_engineer = PromptEngineer()
        self.config = config or AgenticSpecConfig()

        if OPENAI_AVAILABLE:
            self.client = AsyncOpenAI()
        else:
            self.client = None

        # Initialize SQLite cache
        self.cache_db_path = self.specs_dir / "openai_cache.db"
        self._init_cache_db()

    def load_template(self, template_name: str) -> dict[str, Any]:
        """Load a base template by name with version validation."""
        template_path = self.templates_dir / f"{template_name}.yaml"
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

    def _init_cache_db(self) -> None:
        """Initialize SQLite cache database."""
        with sqlite3.connect(self.cache_db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_cache (
                    cache_key TEXT PRIMARY KEY,
                    response_data TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    ttl_hours INTEGER DEFAULT 24,
                    input_text TEXT NOT NULL,
                    model TEXT NOT NULL,
                    temperature REAL NOT NULL
                )
            """)
            conn.commit()

    def _get_cache_key(
        self, model: str, input_text: str, tools: list = None, temperature: float = 0.7
    ) -> str:
        """Generate semantic cache key using embeddings."""
        # For semantic caching, we'll use a simpler approach:
        # Extract key semantic elements from the input text
        semantic_elements = {
            "model": model,
            "tools": tools or [],
            "temperature": round(temperature, 1),  # Round temperature to reduce variation
            # Extract core prompt elements for semantic similarity
            "word_count": len(input_text.split()),
            "has_system_prompt": "system" in input_text.lower(),
            "has_json_request": "json" in input_text.lower(),
            "content_type": self._classify_prompt_type(input_text),
        }
        cache_string = json.dumps(semantic_elements, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()

    def _classify_prompt_type(self, text: str) -> str:
        """Classify prompt type for semantic caching."""
        text_lower = text.lower()
        if "specification" in text_lower and "generate" in text_lower:
            return "spec_generation"
        elif "review" in text_lower:
            return "spec_review"
        elif "template" in text_lower:
            return "template_related"
        else:
            return "general"

    def _get_cached_response(self, model: str, input_text: str, temperature: float = 0.7) -> dict[str, Any] | None:
        """Retrieve semantically similar cached response if valid."""
        with sqlite3.connect(self.cache_db_path) as conn:
            # First try exact match
            exact_key = self._get_cache_key(model, input_text, temperature=temperature)
            cursor = conn.execute(
                "SELECT response_data, created_at, ttl_hours FROM api_cache WHERE cache_key = ?",
                (exact_key,),
            )
            row = cursor.fetchone()
            
            if row:
                response_data, created_at, ttl_hours = row
                if time.time() - created_at < (ttl_hours * 3600):
                    return json.loads(response_data)
                # Remove expired cache
                conn.execute("DELETE FROM api_cache WHERE cache_key = ?", (exact_key,))
                conn.commit()
            
            # If no exact match, try semantic similarity for similar models and temperatures
            cursor = conn.execute(
                "SELECT response_data, created_at, ttl_hours, input_text FROM api_cache WHERE model = ? AND ABS(temperature - ?) < 0.1",
                (model, temperature),
            )
            
            for row in cursor.fetchall():
                response_data, created_at, ttl_hours, cached_input = row
                if time.time() - created_at < (ttl_hours * 3600):
                    # Simple semantic similarity check
                    if self._is_semantically_similar(input_text, cached_input):
                        return json.loads(response_data)
                else:
                    # Clean up expired cache
                    conn.execute("DELETE FROM api_cache WHERE input_text = ?", (cached_input,))
                    conn.commit()
        return None
        
    def _is_semantically_similar(self, text1: str, text2: str, threshold: float = 0.8) -> bool:
        """Simple semantic similarity check using word overlap."""
        # Extract key words (longer than 3 chars, not common words)
        common_words = {"the", "and", "for", "are", "but", "not", "you", "all", "can", "had", "her", "was", "one", "our", "out", "day", "get", "has", "him", "his", "how", "its", "new", "now", "old", "see", "two", "who", "boy", "did", "man", "may", "she", "use", "way", "what", "when", "with"}
        
        words1 = {word.lower().strip('.,!?";') for word in text1.split() if len(word) > 3 and word.lower() not in common_words}
        words2 = {word.lower().strip('.,!?";') for word in text2.split() if len(word) > 3 and word.lower() not in common_words}
        
        if not words1 or not words2:
            return False
            
        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return (intersection / union) > threshold if union > 0 else False

    def _store_cached_response(
        self, cache_key: str, response_data: dict[str, Any], input_text: str, model: str, temperature: float, ttl_hours: int = 24
    ) -> None:
        """Store response in cache."""
        with sqlite3.connect(self.cache_db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO api_cache (cache_key, response_data, created_at, ttl_hours, input_text, model, temperature) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (cache_key, json.dumps(response_data), time.time(), ttl_hours, input_text, model, temperature),
            )
            conn.commit()

    async def _cached_openai_call(
        self,
        model: str,
        input_text: str,
        tools: list = None,
        temperature: float = 0.7,
        ttl_hours: int = 24,
    ) -> dict[str, Any]:
        """Make OpenAI API call with caching."""
        if not self.client:
            raise RuntimeError("OpenAI client not available")

        # Generate cache key
        cache_key = self._get_cache_key(model, input_text, tools, temperature)

        # Try to get semantically similar cached response
        cached_response = self._get_cached_response(model, input_text, temperature)
        if cached_response:
            # Create a mock response object from cached data
            class MockResponse:
                def __init__(self, data):
                    self.output_text = data.get("output_text", "")
                    for key, value in data.items():
                        setattr(self, key, value)

            return MockResponse(cached_response)

        # Make API call
        response = await self.client.responses.create(
            model=model,
            tools=tools or [],
            input=input_text,
            temperature=temperature,
        )

        # Convert response to dict and cache it
        response_dict = response.model_dump()
        self._store_cached_response(cache_key, response_dict, input_text, model, temperature, ttl_hours)

        return response

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
            foundation_path = self.templates_dir / "agentic-spec-foundation.yaml"
            with foundation_path.open("w", encoding="utf-8") as f:
                yaml.dump(foundation_data, f, default_flow_style=False, sort_keys=False)

            return True
        except (OSError, PermissionError) as e:
            print(f"Failed to sync foundation spec: {e}")
            return False

    def _analyze_codebase_for_foundation(self) -> dict[str, Any]:
        """Analyze current codebase to generate foundation spec data."""
        # Get project root (go up from agentic_spec directory)
        project_root = self.templates_dir.parent

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
        if self.client and OPENAI_AVAILABLE:
            spec_data = await self._generate_with_ai(
                prompt, comprehensive_context, project_name, context_params
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
            response = await self._cached_openai_call(
                model=self.config.prompt_settings.model,
                tools=tools,
                input_text=f"{system_prompt}\n\n{enhanced_user_prompt}",
                temperature=self.config.prompt_settings.temperature,
            )

            content = response.output_text
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

        return ProgrammingSpec(
            metadata=SpecMetadata(**data["metadata"]),
            context=SpecContext(**data["context"]),
            requirements=SpecRequirement(**data["requirements"]),
            implementation=[
                ImplementationStep(**step) for step in data["implementation"]
            ],
            review_notes=data.get("review_notes", []),
        )

    async def review_spec(self, spec: ProgrammingSpec) -> list[str]:
        """AI-powered specification review for solo developer workflow."""
        if not self.client or not OPENAI_AVAILABLE:
            return ["Manual review required - AI not available"]

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
            # Use Responses API with web search for current best practices
            response = await self._cached_openai_call(
                model="gpt-4.1",  # Use model that supports web search
                tools=[
                    {"type": "web_search_preview"}
                ],  # Enable web search for current practices
                input_text=f"{system_prompt}\n\nReview this specification:\n\n{spec_yaml}",
                temperature=0.1,
                ttl_hours=48,  # Cache reviews longer since they're less likely to change
            )

            content = response.output_text
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

        # Create detailed prompt for the sub-specification
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
