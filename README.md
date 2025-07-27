# Agentic Specification Generator

> 🤖 AI-powered tool for generating detailed programming specifications from high-level prompts

Agentic Spec transforms natural language descriptions into comprehensive, actionable programming specifications. Built for solo developers and small teams, it uses AI to create detailed implementation plans with template inheritance, automated reviews, and flexible workflows.

[![Tests](https://img.shields.io/badge/tests-90%20passing-brightgreen)](#testing)
[![Python](https://img.shields.io/badge/python-3.12+-blue)](#requirements)
[![License](https://img.shields.io/badge/license-MIT-green)](#license)

## 🚀 What It Does

Agentic Spec takes prompts like:
```
"Add JWT authentication to the user management API"
```

And generates complete specifications with:
- ✅ **Detailed requirements** (functional, non-functional, constraints)
- ✅ **Step-by-step implementation** with effort estimates
- ✅ **File-level guidance** on what to modify/create
- ✅ **Acceptance criteria** for each task
- ✅ **AI-powered review** with practical recommendations
- ✅ **Template inheritance** from base patterns

## 🎯 Key Features

### AI-Powered Generation
- Uses OpenAI's latest models with web search for current best practices
- Generates specifications that follow modern development patterns
- Graceful fallback when AI is unavailable

### Template Inheritance System
- Build specifications from reusable base templates
- Deep merge strategy for complex inheritance hierarchies
- Pre-built templates for common domains (web APIs, CLIs, data analysis, ML)

### Flexible Input Methods
- **Command-line arguments**: `agentic-spec generate "your prompt"`
- **Piped input**: `echo "task" | agentic-spec generate`
- **Interactive mode**: Multi-line input with `Ctrl+D/Ctrl+Z`
- **File input**: Read prompts from files

### Advanced Workflow Features
- **Sub-specification expansion**: Break down complex tasks into detailed sub-specs
- **Specification graphs**: Visualize dependency relationships
- **Review system**: AI-powered feedback for solo developer workflows
- **Status tracking**: Mark specifications as implemented/published

### Developer Experience
- **Modern CLI** with Typer framework and auto-generated help
- **Cross-platform**: Full Windows and Unix compatibility
- **Quality gates**: Pre-commit hooks with automatic formatting
- **Comprehensive testing**: 90+ tests covering all workflows

## 📦 Installation

### Prerequisites
- **Python 3.12+** (uses modern Python features)
- **OpenAI API key** (for AI features)

### Install from Source
```bash
# Clone the repository
git clone https://github.com/yourusername/agentic-spec.git
cd agentic-spec

# Install in development mode
make install-dev

# Set up pre-commit hooks
make dev-setup
```

### Quick Setup
```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your-api-key-here

# Initialize a new project
agentic-spec init --project myproject

# Generate your first specification
agentic-spec generate "Build a REST API for user management"
```

## 🎬 Quick Start

### 1. Initialize Project
```bash
agentic-spec init --project myproject
```
This creates:
- Configuration file (`agentic_spec_config.yaml`)
- Template directories (`spec-templates/`, `prompt-templates/`)
- Specs directory (`specs/`)
- Foundation specification

### 2. Generate Your First Specification
```bash
# Basic generation
agentic-spec generate "Add user authentication with JWT tokens"

# With template inheritance
agentic-spec generate "Add data export functionality" --inherits web-api base-coding-standards

# Interactive mode for complex prompts
agentic-spec generate
# Type your multi-line prompt, then Ctrl+D (Unix) or Ctrl+Z (Windows)
```

### 3. Review and Expand
```bash
# List all specifications
agentic-spec review

# Expand a specific implementation step
agentic-spec expand spec_id:2  # Expands step 2 of specification

# View specification dependencies
agentic-spec graph
```

### 4. Mark as Complete
```bash
# Mark specification as implemented
agentic-spec publish spec_id

# Complete workflow (commit + publish)
make spec-complete
```

## 🔧 Command Reference

### Core Commands

#### `generate` - Create Specifications
```bash
agentic-spec generate [PROMPT] [OPTIONS]
```

**Key Options:**
- `--inherits TEMPLATE...`: Inherit from base templates
- `--project NAME`: Set project context
- `--user-role ROLE`: Your role (e.g., "solo developer", "team lead")
- `--target-audience AUDIENCE`: Who will implement this
- `--tone TONE`: Generation style ("practical", "detailed", "beginner-friendly")
- `--complexity LEVEL`: Task complexity ("simple", "intermediate", "advanced")
- `--dry-run`: Preview without saving

**Examples:**
```bash
# Basic web API feature
agentic-spec generate "Add password reset functionality" --inherits web-api

# Data analysis task
agentic-spec generate "Create monthly sales dashboard" --inherits data-analysis --complexity advanced

# CLI enhancement
agentic-spec generate "Add progress bars to file operations" --inherits cli-application --tone beginner-friendly
```

#### `expand` - Detailed Sub-Specifications
```bash
agentic-spec expand SPEC_ID:STEP_INDEX
```

Breaks down implementation steps into detailed sub-specifications.

```bash
# Expand step 1 of specification abc123
agentic-spec expand abc123:1
```

#### `review` - List Specifications
```bash
agentic-spec review [OPTIONS]
```

Shows all available specifications with status and metadata.

#### `graph` - Dependency Visualization
```bash
agentic-spec graph [OPTIONS]
```

Displays specification relationships and dependency graphs.

### Template Management

#### `templates` - Create Base Templates
```bash
agentic-spec templates --project myproject
```

Creates standard templates:
- `agentic-spec-foundation.yaml`: Auto-synced project foundation
- `base-coding-standards.yaml`: General coding patterns
- `web-api.yaml`: REST API development
- `cli-application.yaml`: Command-line tools
- `data-analysis.yaml`: Data science workflows
- `machine-learning.yaml`: ML project patterns

#### `template` - Template Operations
```bash
# List available templates
agentic-spec template list

# Show template details
agentic-spec template info --template web-api
```

#### `validate` - Template Validation
```bash
agentic-spec validate [--templates-dir PATH]
```

### Configuration Commands

#### `config` - Configuration Management
```bash
# Create default configuration
agentic-spec config init

# Show current configuration
agentic-spec config show

# Validate configuration
agentic-spec config validate
```

#### Dynamic Configuration Override
```bash
# Override any configuration setting
agentic-spec generate "task" --set prompt_settings.temperature=0.2
agentic-spec generate "task" --set workflow.auto_review=false
```

## 🏗️ Architecture Overview

### Directory Structure
```
agentic-spec/
├── agentic_spec/           # Core package
│   ├── cli.py             # Typer-based CLI interface
│   ├── core.py            # SpecGenerator and AI integration
│   ├── models.py          # Data models (dataclasses)
│   ├── config.py          # Pydantic configuration system
│   ├── prompt_engineering.py  # AI prompt building
│   ├── template_loader.py     # YAML template system
│   ├── prompt_template_loader.py  # Jinja2 prompt templates
│   └── ai_providers/      # Pluggable AI provider system
│       ├── base.py
│       ├── openai_provider.py
│       └── factory.py
├── spec-templates/        # YAML inheritance templates
├── prompt-templates/      # Jinja2 text prompt templates
├── specs/                 # Generated specifications
└── tests/                 # Comprehensive test suite
```

### Key Design Patterns

**Template Inheritance**: Specifications inherit from multiple base templates using deep merge strategy.

**AI Integration**: Pluggable provider system with OpenAI as default, graceful degradation when unavailable.

**Input Flexibility**: Supports args, stdin, interactive input, and file-based prompts.

**Foundation Sync**: Automatically syncs foundation specification with codebase changes.

**Error Handling**: Custom exception hierarchy with informative user messages.

## 📝 Template System

### YAML Spec Templates
Templates define reusable specification patterns:

```yaml
# spec-templates/web-api.yaml
domain: "web API development"
dependencies:
  - name: "fastapi"
    version: "0.104.0"
    description: "Modern web framework"
  - name: "sqlalchemy"
    version: "2.0.0"
    description: "Database ORM"

patterns:
  architecture: "REST API with dependency injection"
  database: "SQLAlchemy ORM with Alembic migrations"
  testing: "pytest with async support"

files_involved:
  - "main.py"
  - "models/"
  - "routes/"
  - "tests/"
```

### Jinja2 Prompt Templates
Customize AI prompts for different scenarios:

```markdown
<!-- prompt-templates/feature-addition.md -->
You are adding a new feature to the {{project_name}} project.

Context:
- Project: {{project_name}}
- Domain: {{domain}}
- Feature: {{user_prompt}}

For this feature addition:
1. Consider integration with existing code
2. Maintain current coding standards
3. Include necessary tests
4. Plan for documentation updates

Focus on clean integration and maintaining code quality.
```

## ⚙️ Configuration

### Configuration File
Create `agentic_spec_config.yaml`:

```yaml
# AI Provider Settings
ai_settings:
  default_provider: "openai"
  providers:
    openai:
      provider_type: "openai"
      default_model: "gpt-4o-mini"
      timeout: 120.0

# Generation Settings
prompt_settings:
  temperature: 0.1
  max_tokens: 1300
  enable_web_search: true

# Default Context
default_context:
  user_role: "solo developer"
  target_audience: "solo developer"
  desired_tone: "practical"
  complexity_level: "intermediate"
  time_constraints: "production ready"

# Workflow Settings
workflow:
  auto_review: true
  collect_feedback: false
  save_intermediate_steps: true

# Directory Settings
directories:
  spec_templates_dir: "spec-templates"
  prompt_templates_dir: "prompt-templates"
  specs_dir: "specs"
```

### Environment Variables
```bash
# Required for AI features
export OPENAI_API_KEY=your-api-key-here

# Optional overrides
export AGENTIC_SPEC_CONFIG=path/to/config.yaml
```

## 🧪 Development

### Development Setup
```bash
# Install development dependencies
make install-dev

# Set up pre-commit hooks (includes ruff formatting)
make dev-setup

# Run quality checks
make quality-gate
```

### Testing
```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test types
make test-unit
make test-integration
```

### Code Quality
```bash
# Format code
make format

# Run linting
make lint

# Fix auto-fixable issues
make lint-fix

# Complete quality check
make quality
```

### Pre-commit Hooks
The project uses pre-commit hooks that automatically:
- Format code with `ruff format`
- Fix linting issues with `ruff --fix`
- Check YAML syntax
- Trim trailing whitespace
- Add missing newlines

When hooks modify files, review changes and re-commit.

## 📚 Example Workflows

### Web API Development
```bash
# Initialize with web API template
agentic-spec generate "User management API with CRUD operations" --inherits web-api base-coding-standards

# Add authentication
agentic-spec generate "JWT authentication middleware" --inherits web-api

# Add advanced features
agentic-spec generate "Rate limiting and request validation" --inherits web-api --complexity advanced
```

### Data Analysis Project
```bash
# Data pipeline
agentic-spec generate "ETL pipeline for sales data" --inherits data-analysis

# Visualization
agentic-spec generate "Interactive dashboard with filters" --inherits data-analysis --complexity intermediate

# Machine learning
agentic-spec generate "Predictive model for customer churn" --inherits machine-learning data-analysis
```

### CLI Tool Development
```bash
# Core functionality
agentic-spec generate "File processing CLI with progress bars" --inherits cli-application

# Configuration system
agentic-spec generate "YAML-based configuration with validation" --inherits cli-application

# Advanced features
agentic-spec generate "Plugin system with auto-discovery" --inherits cli-application --complexity advanced
```

## 🔍 Output Format

Generated specifications follow a structured YAML format:

```yaml
metadata:
  id: "abc12345"
  title: "Add JWT authentication to user API"
  inherits: ["web-api", "base-coding-standards"]
  created: "2025-07-27T10:30:00"
  version: "1.0"
  status: "draft"
  parent_spec_id: null
  child_spec_ids: ["def67890"]

context:
  project: "user-management-api"
  domain: "web API development"
  dependencies:
    - name: "pyjwt"
      version: "2.8.0"
      description: "JWT token handling"
  files_involved:
    - "auth/middleware.py"
    - "models/user.py"
    - "tests/test_auth.py"

requirements:
  functional:
    - "Generate JWT tokens on successful login"
    - "Validate JWT tokens on protected routes"
    - "Handle token expiration gracefully"
  non_functional:
    - "Token validation < 10ms"
    - "Secure token storage practices"
  constraints:
    - "Use existing user model"
    - "Maintain API compatibility"

implementation:
  - task: "Create JWT middleware"
    details: "FastAPI dependency for JWT validation"
    files: ["auth/middleware.py"]
    acceptance: "Middleware validates tokens and extracts user data"
    estimated_effort: "medium"
    step_id: "abc12345:0"
    sub_spec_id: null

review_notes:
  - "Consider refresh token strategy for long sessions"
  - "Add rate limiting to authentication endpoints"
  - "Ensure proper error handling for invalid tokens"

context_parameters:
  user_role: "solo developer"
  target_audience: "solo developer"
  desired_tone: "practical"
  complexity_level: "intermediate"
  time_constraints: "production ready"
```

## 📊 Foundation Specification

The foundation specification is automatically maintained and contains:
- **Current codebase structure** and file organization
- **Dependencies and versions** from pyproject.toml
- **Coding standards** and development practices
- **Testing patterns** and quality gates
- **Build and deployment** workflows

This ensures all generated specifications align with your project's current state.

## 🛠️ Troubleshooting

### Common Issues

**OpenAI API Key Issues**
```bash
# Check if key is set
echo $OPENAI_API_KEY

# Set for current session
export OPENAI_API_KEY=your-key-here

# Add to shell profile for persistence
echo 'export OPENAI_API_KEY=your-key-here' >> ~/.bashrc
```

**Template Not Found**
```bash
# List available templates
agentic-spec template list

# Recreate base templates
agentic-spec templates --project myproject

# Check template directory
ls spec-templates/
```

**Configuration Issues**
```bash
# Validate configuration
agentic-spec config validate

# Show current configuration
agentic-spec config show

# Reset to defaults
agentic-spec config init --force
```

**Windows Path Issues**
- Use forward slashes in paths: `--specs-dir specs/output`
- Quote paths with spaces: `--specs-dir "my specs"`
- Set Git line endings: `git config core.autocrlf true`

## 🎯 Requirements

- **Python 3.12+** (uses modern features like improved error messages and typing)
- **OpenAI API access** (for AI-powered generation)
- **Git** (for version control and line ending handling)

### Core Dependencies
- `openai >= 1.97.1` - AI integration with web search
- `pyyaml >= 6.0.2` - YAML processing and validation
- `typer >= 0.12.0` - Modern CLI framework
- `pydantic >= 2.0` - Configuration validation
- `jinja2 >= 3.1.0` - Template rendering
- `networkx >= 3.3` - Graph analysis and visualization

### Development Dependencies
- `pytest >= 8.4.1` - Testing framework with async support
- `ruff >= 0.8.0` - Fast Python linter and formatter
- `pre-commit >= 3.0` - Git hooks for quality control

## 🤝 Contributing

1. **Fork and clone** the repository
2. **Install development dependencies**: `make install-dev`
3. **Set up pre-commit hooks**: `make dev-setup`
4. **Create feature branch**: `git checkout -b feature-name`
5. **Make changes** following coding standards
6. **Run tests**: `make test`
7. **Run quality checks**: `make quality-gate`
8. **Submit pull request** with clear description

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [OpenAI's API](https://openai.com) for AI-powered generation
- CLI framework powered by [Typer](https://typer.tiangolo.com/)
- Code quality enforced by [Ruff](https://docs.astral.sh/ruff/)
- Template system inspired by modern Infrastructure as Code patterns

---

**Generated with ❤️ by Agentic Spec** - *The tool that documents itself*
