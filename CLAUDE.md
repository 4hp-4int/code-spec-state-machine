# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Agentic Spec is an AI-powered tool for generating detailed programming specifications from high-level prompts. It features template inheritance, database-backed workflow tracking, automated review workflows, and supports both AI-assisted and basic generation modes with comprehensive task management capabilities.

## Development Commands

### Custom Slash Commands

This project includes custom slash commands for Claude Code:

- `/spec` - Generate programming specifications using agentic-spec
  - `/spec generate "task description"` - Generate a new specification
  - `/spec generate "task" --template feature-addition` - Generate with prompt template
  - `/spec generate "task" --inherits template1 template2` - Generate with template inheritance
  - `/spec browse-templates` - Browse available prompt templates
  - `/spec preview-template template-name` - Preview a prompt template
  - `/spec templates` - Create base templates
  - `/spec review` - List existing specifications
  - `/spec expand spec_id:step_index` - Expand an implementation step into a sub-specification
  - `/spec graph` - Display specification dependency graph
  - `/spec workflow-status spec_id` - Show workflow status for a specification
  - `/spec task-start spec_id:step_index` - Start working on a task
  - `/spec task-complete spec_id:step_index` - Mark a task as completed
  - `/spec migrate-bulk` - Migrate all specifications to database
  - `/spec migration-status` - Check migration status

## CLI Commands

### Complete Command Reference

The CLI has been refactored into a modular architecture with both **direct access** and **sub-application access** patterns:

#### CLI Architecture

**Modular Structure**: Commands are organized into logical modules:
- **Core Commands** (`cli_core.py`): Core specification operations
- **Workflow Commands** (`cli_workflow.py`): Task and workflow management
- **Template Commands** (`cli_template.py`): Template operations and browsing
- **Database Commands** (`cli_db.py`): Database migrations and management
- **Utility Commands** (`cli_utils.py`): Configuration and utility functions

**Access Patterns**: All commands support both access methods:
```bash
# Direct access (backward compatible)
agentic-spec generate "task description"
agentic-spec task-start spec_id:0
agentic-spec config show

# Sub-application access (new modular approach)
agentic-spec core generate "task description"
agentic-spec workflow task-start spec_id:0
agentic-spec utils config show
```

**Sub-Application Commands**:
```bash
agentic-spec core     # Core specification commands (4 commands)
agentic-spec workflow # Task workflow management (12 commands)
agentic-spec template # Template operations (4 commands)
agentic-spec database # Database and migrations (4 commands)
agentic-spec utils    # Configuration and utilities (5 commands)
```

#### Core Commands

**generate** - Generate a new programming specification from a prompt
```bash
# Basic generation
agentic-spec generate "Build a REST API for user management"

# With prompt template
agentic-spec generate "Add JWT authentication" --template feature-addition

# With template inheritance
agentic-spec generate "Add JWT authentication" --inherits web-api base-coding-standards

# With context customization
agentic-spec generate "Create data pipeline" \
  --user-role "data engineer" \
  --target-audience "team" \
  --tone "detailed" \
  --complexity "advanced"

# Interactive input mode
agentic-spec generate  # Then type prompt and press Ctrl+D/Ctrl+Z

# Pipe input from other sources
echo "Implement real-time chat feature" | agentic-spec generate

# Override configuration
agentic-spec generate "Task" --set prompt_settings.temperature=0.2
```

**review** - List available specifications for review
```bash
agentic-spec review
agentic-spec review --specs-dir ./custom-specs
```

**templates** - Create base templates for common project patterns
```bash
agentic-spec templates --project myproject
agentic-spec templates --templates-dir ./custom-templates
```

**graph** - Display specification dependency graph and statistics
```bash
agentic-spec graph
agentic-spec graph --specs-dir ./specs
```

**expand** - Expand an implementation step into a detailed sub-specification
```bash
agentic-spec expand spec_id:0  # Expand first step
agentic-spec expand abc123:2   # Expand third step of spec abc123
```

**publish** - Mark a specification as implemented and update its status
```bash
agentic-spec publish spec_id
agentic-spec publish abc123 --specs-dir ./specs
```

#### Database and Workflow Commands

**migrate-bulk** - Migrate all specifications to database
```bash
agentic-spec migrate-bulk
agentic-spec migrate-bulk --dry-run  # Validate without migrating
agentic-spec migrate-bulk --verbose  # Show detailed progress
```

**migrate-incremental** - Migrate only new or changed specifications
```bash
agentic-spec migrate-incremental
agentic-spec migrate-incremental --verbose
```

**migration-status** - Show current migration status
```bash
agentic-spec migration-status
```

**migration-report** - Generate detailed migration report
```bash
agentic-spec migration-report
```

#### Task Workflow Commands

**task-start** - Start working on a task
```bash
agentic-spec task-start spec_id:0  # Start first task
agentic-spec task-start abc123:2   # Start third task of spec abc123
```

**task-complete** - Mark a task as completed
```bash
agentic-spec task-complete spec_id:0
agentic-spec task-complete abc123:2 --notes "Implemented feature successfully"
```

**task-approve** - Approve a completed task
```bash
agentic-spec task-approve spec_id:0
agentic-spec task-approve abc123:2 --level peer --comments "Code review passed"
```

**task-reject** - Reject a task, requiring rework
```bash
agentic-spec task-reject spec_id:0 --reason "Needs additional testing"
```

**task-block** - Block a task due to external dependencies
```bash
agentic-spec task-block spec_id:0 --reason "Waiting for API documentation"
```

**task-unblock** - Unblock a task and return it to pending status
```bash
agentic-spec task-unblock spec_id:0
```

**task-override** - Override strict mode to start a task out of sequence
```bash
agentic-spec task-override spec_id:3 --reason "Critical bug fix needed"
```

**task-status** - Show detailed status information for a task
```bash
agentic-spec task-status spec_id:0
```

**workflow-status** - Show comprehensive workflow status for a specification
```bash
agentic-spec workflow-status spec_id
agentic-spec workflow-status abc123
```

#### Configuration Commands

**config** - Manage application configuration
```bash
# Create default configuration file
agentic-spec config init

# Show current configuration
agentic-spec config show

# Validate configuration file
agentic-spec config validate
```

#### Template Management Commands

**template** - Manage and inspect templates
```bash
# List available templates
agentic-spec template list

# Show template information
agentic-spec template info --template base-coding-standards
```

**validate** - Validate all templates for correctness and structure
```bash
agentic-spec validate
agentic-spec validate --templates-dir ./templates
```

#### Foundation Sync Commands

**sync-foundation** - Configurable codebase analysis and foundation specification sync
```bash
# Basic sync with auto-discovery
agentic-spec sync-foundation

# Force sync even if current
agentic-spec sync-foundation --force

# Use custom configuration file
agentic-spec sync-foundation --discovery-config my-project-config.yaml

# Specify custom templates directory
agentic-spec sync-foundation --templates-dir ./custom-templates
```

**🆕 NEW: Configurable for Any Project Type!**

The sync-foundation command is now fully configurable via YAML files, making it work seamlessly with any project structure:

**Enhanced Analysis Capabilities:**
- **🔍 Multi-source dependency detection**: pyproject.toml, requirements.txt, setup.py with proper TOML/Python parsing
- **📁 Configurable file categorization**: Custom patterns for CLI, web UI, database, API, test, config files
- **🏗️ Architectural pattern detection**: FastAPI, async operations, database migrations
- **⚙️ YAML-based configuration**: Fully customizable project analysis rules
- **🚀 Auto-discovery**: Automatically finds config files in project root
- **✅ Validation system**: Built-in error checking and warning system

**Configuration Files (Auto-Discovery Order):**
1. `sync_foundation_config.yaml` (recommended)
2. `sync-foundation-config.yaml`
3. `project_discovery.yaml`
4. `project-discovery.yaml`
5. `.sync-foundation.yaml`

**Configuration Validation:**
```bash
# Validate all configurations including sync-foundation config
agentic-spec config validate

# Test sync with specific config
agentic-spec sync-foundation --discovery-config test-config.yaml
```

**check-foundation** - Check if foundation specification needs to be synced
```bash
agentic-spec check-foundation
```

#### Template Browsing Commands

**browse-templates** - Browse available prompt templates
```bash
agentic-spec browse-templates
```

**preview-template** - Preview a specific prompt template
```bash
agentic-spec preview-template feature-addition
agentic-spec preview-template bug-fix
```

#### Rendering Commands

**render** - Render a specification using a template
```bash
# Render to stdout
agentic-spec render spec_id --template template.html

# Render to file
agentic-spec render spec_id --template template.html --output output.html
```

### Modular CLI API Reference

#### Core Module (`agentic-spec core` or direct access)
```bash
agentic-spec core generate       # Generate new specification
agentic-spec core review         # List existing specifications
agentic-spec core graph          # Show dependency graph
agentic-spec core expand         # Expand implementation step
```

#### Workflow Module (`agentic-spec workflow`)
```bash
agentic-spec workflow task-start spec_id:step      # Start working on task
agentic-spec workflow task-complete spec_id:step   # Mark task completed
agentic-spec workflow task-approve spec_id:step    # Approve completed task
agentic-spec workflow task-reject spec_id:step     # Reject task for rework
agentic-spec workflow task-block spec_id:step      # Block task (dependencies)
agentic-spec workflow task-unblock spec_id:step    # Unblock task
agentic-spec workflow task-override spec_id:step   # Override strict mode
agentic-spec workflow task-status spec_id:step     # Show task status
agentic-spec workflow workflow-status spec_id      # Show full workflow status
agentic-spec workflow publish spec_id              # Publish as implemented
agentic-spec workflow sync-foundation              # Sync foundation spec
agentic-spec workflow check-foundation             # Check foundation status
```

#### Template Module (`agentic-spec template`)
```bash
agentic-spec template templates          # Create base templates
agentic-spec template manage list        # List available templates
agentic-spec template manage info --template name  # Show template info
agentic-spec template browse             # Browse prompt templates
agentic-spec template preview name       # Preview template content
```

#### Database Module (`agentic-spec database`)
```bash
agentic-spec database migrate-bulk          # Migrate all specs to database
agentic-spec database migrate-incremental   # Migrate only changed specs
agentic-spec database migration-status      # Show migration status
agentic-spec database migration-report      # Generate migration report
```

#### Utils Module (`agentic-spec utils`)
```bash
agentic-spec utils init                  # Initialize new project
agentic-spec utils config init          # Create default configuration
agentic-spec utils config show          # Show current configuration
agentic-spec utils config validate      # Validate configuration
agentic-spec utils validate             # Validate templates
agentic-spec utils render spec_id       # Render specification
agentic-spec utils prompt edit name     # Edit prompt in system editor
agentic-spec utils prompt list          # List available prompts
```

### Makefile Commands

All development tasks should be run through the Makefile:

```bash
# Installation
make install          # Install package in development mode
make install-dev      # Install with development dependencies

# Code Quality
make format           # Format code using ruff
make lint             # Run linting checks
make check            # Run both formatting and linting checks
make lint-fix         # Auto-fix linting issues where possible
make quality          # Run comprehensive quality checks

# Testing
make test             # Run all tests
make test-cov         # Run tests with coverage reporting
make test-fast        # Run tests excluding slow tests
make test-unit        # Run only unit tests
make test-integration # Run only integration tests

# CI/CD
make ci               # Run full CI pipeline (format, lint, test)
make pre-commit       # Run pre-commit checks
make quality-gate     # All-in-one quality gate

# Utilities
make clean            # Clean build artifacts and cache files
make build            # Build distribution packages
make help             # Show available commands
make version-check    # Check version information
make analyze          # Run code analysis with statistics

# Specification Workflow (IMPORTANT)
make spec-commit      # Commit specifications and implementation changes
make spec-publish     # Publish all completed specifications as implemented
make spec-complete    # Complete specification workflow (commit + publish)
```

### Development Workflow

```bash
# Initial setup
make install-dev
make dev-setup

# Before committing
make pre-commit

# Full quality check
make quality-gate

# Run specific test suite
make test-unit
make test-integration

# Get detailed output
make format-verbose
make lint-verbose
make test-verbose
```

## Architecture

### Core Components

- **Main CLI Module** (`cli.py`): Main CLI entrypoint that aggregates sub-applications and provides backward compatibility
- **Core CLI Commands** (`cli_core.py`): Core specification operations (generate, review, graph, expand, validate, render)
- **Workflow CLI Commands** (`cli_workflow.py`): Task tracking and workflow management commands
- **Template CLI Commands** (`cli_template.py`): Template management and browsing commands
- **Database CLI Commands** (`cli_db.py`): Database migration and management commands
- **Utility CLI Commands** (`cli_utils.py`): Configuration and utility commands
- **Core Engine** (`core.py`): Specification generation logic with AI integration, template inheritance, and database migration
- **Data Models** (`models.py`): Enhanced dataclass and Pydantic definitions with workflow tracking, task management, and database support
- **Database Layer** (`async_db.py`): Async SQLite backend with comprehensive task and specification tracking
- **Template System** (`templates/base.py`): Pre-built templates for common project patterns
- **Workflow Manager**: Database-backed task tracking with strict mode enforcement and approval workflows

### Key Design Patterns

- **Template Inheritance**: Specifications can inherit from multiple base templates using deep merge strategy
- **Database-Backed Workflow**: SQLite database with async operations, comprehensive indexing, and task tracking
- **Workflow Status Management**: 10-state workflow lifecycle (created → in_progress → ready_for_review → completed, etc.)
- **Task Management**: Individual task tracking with progress, approval workflows, and dependency management
- **Strict Mode Enforcement**: Sequential task execution with approval gates and override capabilities
- **Async AI Integration**: Uses OpenAI's Responses API with web search for current best practices
- **Graceful Degradation**: Falls back to basic generation when AI is unavailable
- **Input Flexibility**: Supports command-line args, piped input, and interactive multiline input
- **Foundation Sync**: Automated foundation specification syncing with codebase analysis
- **Comprehensive Context**: Parent spec traversal and foundation context for complete awareness
- **Migration System**: Automated YAML-to-database migration with change detection and validation
- **Error Handling**: Custom exception hierarchy with informative user messages
- **Typer CLI**: Modern CLI framework with automatic help generation and type validation
- **Modular CLI Architecture**: Commands organized into logical modules with both direct access (`agentic-spec generate`) and sub-app access (`agentic-spec core generate`)

### File Structure
```
agentic_spec/
├── cli.py                      # Main CLI entrypoint that aggregates sub-applications
├── cli_core.py                 # Core specification commands (generate, review, graph, expand)
├── cli_workflow.py             # Workflow and task management commands
├── cli_template.py             # Template management and browsing commands
├── cli_db.py                   # Database and migration commands
├── cli_utils.py                # Configuration and utility commands
├── core.py                     # SpecGenerator class, AI integration, and database migration
├── models.py                   # Enhanced data models with workflow tracking and database support
├── async_db.py                 # Async SQLite database backend with comprehensive indexing
├── config.py                   # Configuration management with Pydantic
├── exceptions.py               # Custom exception hierarchy
├── prompt_engineering.py       # AI prompt building and optimization
├── graph_visualization.py      # Specification dependency graph tools
├── template_loader.py          # Template loading and management
├── template_validator.py       # Template validation system
├── migrations/                 # Database migration scripts
│   ├── migration_manager.py    # Migration framework
│   └── 002_add_enhanced_tracking_fields.py  # Schema enhancement migration
└── templates/
    ├── base.py                 # Template generation functions
    └── __init__.py

templates/                      # Generated base templates
├── agentic-spec-foundation.yaml    # Auto-synced foundation specification
├── base-coding-standards.yaml      # Coding standards template
├── web-api.yaml                    # Web API project template
├── cli-application.yaml            # CLI application template
├── data-analysis.yaml              # Data analysis template
└── machine-learning.yaml           # ML project template

specs/                          # Generated specifications and database
├── specifications.db           # SQLite database with workflow tracking
├── *.yaml                      # YAML specification files
└── migration-*.yaml            # Migration planning files

logs/                           # Application logs with rotation

Makefile                        # Development automation commands
```

### AI Integration Details

- Uses OpenAI's Responses API with web search capabilities for current best practices
- System prompts emphasize up-to-date libraries and implementation patterns
- Review system focuses on practical solo developer concerns
- Graceful fallback to basic generation when AI unavailable

### Template System

Templates use YAML format and support deep merging. The inheritance system allows building complex specifications from reusable components. Base templates cover common domains (web APIs, CLIs, data analysis, ML).

### Specification Format

Generated specs include:
- **Metadata**: ID, inheritance chain, timestamps, version, parent/child relationships
- **Context**: Project info, domain, dependencies, affected files
- **Requirements**: Functional, non-functional, constraints
- **Implementation**: Detailed steps with acceptance criteria, effort estimates, and progress tracking
- **Review Notes**: AI-generated feedback and recommendations
- **Workflow Tracking**: Status, completion percentage, approval workflows, work logs
- **Database Fields**: Enhanced tracking with 25 fields including priority, assignee, lifecycle timestamps

### Database Schema

The SQLite database includes:
- **Specifications Table**: 25 fields with workflow status, completion tracking, and metadata
- **Tasks Table**: 25 fields with enhanced progress tracking and dependency management
- **Approvals Table**: Multi-level approval workflow tracking
- **Work Logs Table**: Detailed activity and time tracking
- **23 Performance Indexes**: Optimized queries for status, completion, dates, and assignments

## Environment Requirements

- Python 3.12+ (configured in pyproject.toml)
- OpenAI API key for AI features (optional)
- Core Dependencies:
  - PyYAML >= 6.0.2 (YAML parsing and generation)
  - OpenAI >= 1.97.1 (AI integration)
  - Typer >= 0.12.0 (CLI framework)
  - NetworkX >= 3.3 (Graph visualization)
  - Matplotlib >= 3.9.2 (Graph rendering)
  - Jinja2 >= 3.1.0 (Template rendering)
  - pytest-cov >= 6.2.1 (Test coverage)
- Development Dependencies:
  - Ruff >= 0.8.0 (Linting and formatting, replaces Black/flake8)
  - pytest >= 8.4.1 (Testing framework)
  - pytest-asyncio >= 0.23.2,<0.24.0 (Async test support)
  - aiosqlite (Async SQLite support for database operations)

## Claude Code Memories

- Always use the agentic-spec tool to generate new specs to follow when working on the project.
- Run project commands through make and the Makefile
- **DATABASE-BACKED WORKFLOW**: All specifications are now tracked in SQLite database at `specs/specifications.db`
- **WORKFLOW COMMANDS**: Use task workflow commands to track progress:
  - `agentic-spec task-start spec_id:step` - Start working on a task
  - `agentic-spec task-complete spec_id:step` - Mark task as completed
  - `agentic-spec workflow-status spec_id` - Check specification progress
  - `agentic-spec migration-status` - Check database migration status
- **AUTOMATIC WORKFLOW**: When completing a specification or declaring it done, ALWAYS run `make spec-complete` to commit changes and publish completed specifications.
- **MIGRATION**: Use `agentic-spec migrate-bulk` to sync YAML files with database
- Memorize the doc/location structure, keep docs up to date
- Relay the current spec graph after completing sub-specifications or the parent specification
- **DECOMPOSITION RULE**: Whenever you encounter a composite task, decompose using the expand command, go 3 levels of nesting deep, if you need to go further, ask for approval.
- All 39 existing specifications have been marked as completed in the database
- **TEMPLATE INHERITANCE**: Ensure generated specs inherit from the correct templates
- **🆕 CONFIGURABLE SYNC-FOUNDATION**: The sync-foundation command is now configurable for any project type via YAML files. Use `sync_foundation_config.yaml` for custom file categorization, dependency detection, and project analysis patterns. Auto-discovery enabled.

## Interactive Workflow Usage

### Basic Workflow
1. **Generate Specification**: `/spec generate "task description"`
2. **Check Status**: `/spec workflow-status spec_id`
3. **Start Task**: `/spec task-start spec_id:0`
4. **Complete Task**: `/spec task-complete spec_id:0`
5. **Check Progress**: `/spec workflow-status spec_id`

### Database Operations
1. **Migrate to Database**: `/spec migrate-bulk`
2. **Check Migration**: `/spec migration-status`
3. **View All Specs**: `/spec review`
4. **Expand Steps**: `/spec expand spec_id:step_index`

### Advanced Features
- **Template Inheritance**: `/spec generate "task" --inherits template1 template2`
- **Task Approval**: `/spec task-approve spec_id:step --level peer`
- **Block/Unblock**: `/spec task-block spec_id:step --reason "dependency"`
- **Override Strict Mode**: `/spec task-override spec_id:step --reason "urgent"`
