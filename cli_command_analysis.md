# CLI Command Analysis and Categorization

## Overview

This document provides a comprehensive analysis and categorization of all existing CLI commands in `agentic_spec/cli.py` for the purpose of refactoring them into logical modules.

## Current CLI Structure

The current `cli.py` file contains **27 Typer commands** that can be logically grouped into 4 categories:

## Command Categorization

### 1. Core Commands (cli_core.py)
**Purpose**: Fundamental specification generation, validation, and management

| Command | Function | Description |
|---------|----------|-------------|
| `generate` | `generate_spec()` | Generate new programming specifications from prompts |
| `review` | `review_specs()` | List available specifications for review |
| `validate` | `validate_templates()` | Validate all templates for correctness and structure |
| `graph` | `show_graph()` | Display specification dependency graph and statistics |
| `expand` | `expand_step()` | Expand implementation step into detailed sub-specification |
| `publish` | `publish_spec()` | Mark specification as implemented and update status |
| `render` | `render_spec()` | Render a specification using a template |
| `init` | `init_project()` | Initialize new project with configuration and templates |

**Rationale**: These commands represent the core functionality of the agentic-spec tool - generating, managing, and publishing specifications.

### 2. Workflow Commands (cli_workflow.py)
**Purpose**: Task tracking, status management, and workflow operations

| Command | Function | Description |
|---------|----------|-------------|
| `task-start` | `start_task()` | Start working on a task |
| `task-complete` | `complete_task()` | Mark a task as completed |
| `task-approve` | `approve_task()` | Approve a completed task |
| `task-reject` | `reject_task()` | Reject a task, requiring rework |
| `task-block` | `block_task()` | Block a task due to external dependencies |
| `task-unblock` | `unblock_task()` | Unblock a task and return to pending status |
| `task-override` | `override_strict_mode()` | Override strict mode to start task out of sequence |
| `task-status` | `show_task_status()` | Show detailed status information for a task |
| `workflow-status` | `show_workflow_status()` | Show comprehensive workflow status for specification |
| `sync-foundation` | `sync_foundation_spec()` | Sync foundation specification with codebase analysis |
| `check-foundation` | `check_foundation_status()` | Check if foundation specification needs syncing |

**Rationale**: These commands handle the database-backed workflow system, task management, and foundation synchronization.

### 3. Template Commands (cli_template.py)
**Purpose**: Template management, browsing, and prompt handling

| Command | Function | Description |
|---------|----------|-------------|
| `templates` | `create_templates()` | Create base templates for common project patterns |
| `template` | `manage_templates()` | Manage and inspect templates (list, info actions) |
| `browse-templates` | `browse_templates()` | Browse available prompt templates |
| `preview-template` | `preview_template()` | Preview a specific prompt template |
| `prompt` | `prompt_command()` | Manage prompts (edit, list, new actions) |

**Rationale**: These commands are focused on template and prompt management, which is a distinct functional area.

### 4. Database Commands (cli_db.py)
**Purpose**: Database operations, migration management, and data persistence

| Command | Function | Description |
|---------|----------|-------------|
| `migrate-bulk` | `migrate_bulk()` | Migrate all specifications to database |
| `migrate-incremental` | `migrate_incremental()` | Migrate only new or changed specifications |
| `migration-status` | `migration_status()` | Show current migration status |
| `migration-report` | `migration_report()` | Generate detailed migration report |
| `config` | `manage_config()` | Manage application configuration (init, show, validate) |

**Rationale**: These commands handle database operations, migrations, and configuration management.

## Shared Utilities and Dependencies

### Common Imports Required Across Modules
- `typer` - CLI framework
- `asyncio` - Async operations
- `logging` - Logging functionality
- `Path` from `pathlib` - File system operations
- Models from `.models` - Data structures
- Database from `.async_db` - Database operations
- Configuration from `.config` - Configuration management
- Core exceptions from `.exceptions` - Error handling

### Shared Utility Functions
The following utility functions are used across multiple commands and should remain accessible:

1. **Logging Setup**: Logger configuration and error handling patterns
2. **Path Validation**: Directory existence checking and creation
3. **Error Handling**: Consistent exception handling and user-friendly error messages
4. **Async Pattern**: `asyncio.run()` wrapper pattern used by many commands
5. **Configuration Loading**: Config manager access patterns

## Implementation Considerations

### 1. Import Structure
- Each module should import necessary dependencies
- Shared utilities can be imported from a common module or kept in each module
- Avoid circular imports by keeping core functionality separate

### 2. Typer App Registration
Commands should be organized as sub-applications:
```python
# In cli_core.py
core_app = typer.Typer()

@core_app.command("generate")
def generate_spec(...):
    # Implementation

# In main cli.py
app.add_typer(core_app, name="core")
```

### 3. Backward Compatibility
All commands must remain available at the top level:
- `agentic-spec generate` (not `agentic-spec core generate`)
- Help output should group commands logically
- All existing command signatures and options must be preserved

### 4. Testing Considerations
- Each module needs independent test coverage
- Integration tests for command registration
- Backward compatibility tests for CLI interface

## Command Dependencies and Interactions

### Cross-Module Dependencies
1. **Workflow → Core**: Task operations reference specifications created by core commands
2. **Template → Core**: Template operations affect specification generation
3. **Database → All**: Migration operations affect all data managed by other modules
4. **Core → Template**: Specification generation uses templates

### State Management
- Database state is shared across all modules
- Configuration state affects all operations
- File system state (specs/, templates/) is shared

## Migration Strategy

1. **Create Module Files**: Start with empty module files with basic structure
2. **Move Commands**: Move commands by category, preserving function signatures
3. **Update Main CLI**: Register sub-apps in main cli.py
4. **Test Integration**: Ensure all commands remain accessible
5. **Update Tests**: Refactor test structure to match new organization
6. **Update Documentation**: Update help text and documentation

## Risk Assessment

**Low Risk**:
- Template and database commands have clear boundaries
- Most commands are independent

**Medium Risk**:
- Shared utility function dependencies
- Import path updates needed throughout codebase

**High Risk**:
- Typer command registration order affects help output
- Any dynamic command registration patterns
- Async command patterns must be preserved correctly

## Conclusion

The 27 CLI commands can be cleanly organized into 4 logical modules:
- **cli_core.py** (8 commands): Core specification operations
- **cli_workflow.py** (11 commands): Workflow and task management
- **cli_template.py** (5 commands): Template and prompt management
- **cli_db.py** (5 commands): Database and configuration operations

This organization improves maintainability while preserving all existing functionality and backward compatibility.
