# Async Database Layer

The async database layer provides database-backed storage for specifications with non-blocking operations using SQLite as the backend.

## Overview

The async database layer consists of:

- **AsyncDatabaseInterface**: Abstract interface defining CRUD operations
- **SQLiteBackend**: Async SQLite implementation using aiosqlite
- **AsyncSpecManager**: High-level manager for specification operations
- **Database Models**: Pydantic models optimized for database storage

## Quick Start

### Basic Usage

```python
import asyncio
from agentic_spec.async_db import DatabaseBackend, AsyncSpecManager

async def main():
    # Create backend
    backend = DatabaseBackend.create("sqlite", database_path="my_specs.db")

    # Use as context manager for automatic cleanup
    async with AsyncSpecManager(backend) as manager:
        # Save a ProgrammingSpec to database
        spec_id = await manager.save_spec_to_db(my_spec)

        # Retrieve specification
        db_spec = await backend.get_specification(spec_id)

        # List all specifications
        all_specs = await backend.list_specifications()

asyncio.run(main())
```

### Configuration

The database backend can be configured when creating the backend:

```python
# Default SQLite database
backend = DatabaseBackend.create()

# Custom database path
backend = DatabaseBackend.create("sqlite", database_path="/path/to/specs.db")

# Memory database (for testing)
backend = DatabaseBackend.create("sqlite", database_path=":memory:")
```

## Core Operations

### Specification Management

```python
async with AsyncSpecManager(backend) as manager:
    # Create specification from ProgrammingSpec
    spec_id = await manager.save_spec_to_db(programming_spec)

    # Get specification by ID
    spec = await backend.get_specification(spec_id)

    # Update specification
    spec.status = SpecStatus.REVIEWED
    await backend.update_specification(spec)

    # List specifications with filtering
    draft_specs = await backend.list_specifications(status=SpecStatus.DRAFT)

    # Delete specification
    await backend.delete_specification(spec_id)
```

### Task Management

```python
# Get all tasks for a specification
tasks = await backend.get_tasks_for_spec(spec_id)

# Update task status
task = await backend.get_task(task_id)
task.status = TaskStatus.IN_PROGRESS
task.started_at = datetime.now()
await backend.update_task(task)

# Create new task
new_task = TaskDB(
    id="task-456",
    spec_id=spec_id,
    step_index=1,
    task="Implement feature",
    details="Feature details",
    files=["feature.py"],
    acceptance="Feature works",
    estimated_effort="medium",
)
await backend.create_task(new_task)
```

### Work Log Tracking

```python
# Create work log entry
log = WorkLogDB(
    id=str(uuid.uuid4()),
    spec_id=spec_id,
    task_id=task_id,
    action="started",
    timestamp=datetime.now(),
    duration_minutes=30,
    notes="Started implementation",
    metadata={"priority": "high"},
)
await backend.create_work_log(log)

# Query work logs
recent_logs = await backend.get_work_logs(
    spec_id=spec_id,
    start_date=datetime.now() - timedelta(days=7),
    limit=50
)

# Query by action type
completed_logs = await backend.get_work_logs(
    task_id=task_id,
    action="completed"
)
```

### Approval Management

```python
# Create approval
approval = ApprovalDB(
    id=str(uuid.uuid4()),
    task_id=task_id,
    level=ApprovalLevel.PEER,
    approved_by="reviewer@company.com",
    approved_at=datetime.now(),
    comments="Implementation looks good",
)
await backend.create_approval(approval)

# Get all approvals for a task
approvals = await backend.get_approvals_for_task(task_id)
```

## Transaction Management

The database layer supports transactions for atomic operations:

```python
async with backend.transaction():
    # All operations within this block are atomic
    await backend.create_specification(spec)
    await backend.create_task(task1)
    await backend.create_task(task2)
    # If any operation fails, all changes are rolled back
```

## Data Models

### SpecificationDB

Database model for specifications with JSON fields for complex data:

```python
spec_db = SpecificationDB(
    id="spec-123",
    title="My Specification",
    inherits=[],
    created=datetime.now(),
    updated=datetime.now(),
    version="1.0",
    status=SpecStatus.DRAFT,
    parent_spec_id=None,
    child_spec_ids=[],
    context={"project": "my-project"},
    requirements={"functional": ["requirement 1"]},
    review_notes=["needs review"],
    context_parameters=None,
)
```

### TaskDB

Database model for implementation tasks:

```python
task_db = TaskDB(
    id="task-123",
    spec_id="spec-123",
    step_index=0,
    task="Implement feature",
    details="Detailed description",
    files=["file1.py", "file2.py"],
    acceptance="Feature works correctly",
    estimated_effort="medium",
    status=TaskStatus.PENDING,
    started_at=None,
    completed_at=None,
    time_spent_minutes=None,
    completion_notes=None,
    blockers=[],
)
```

### WorkLogDB

Database model for work history tracking:

```python
log_db = WorkLogDB(
    id=str(uuid.uuid4()),
    spec_id="spec-123",
    task_id="task-123",
    action="status_changed",
    timestamp=datetime.now(),
    duration_minutes=45,
    notes="Completed implementation",
    metadata={"tools_used": ["vscode", "pytest"]},
)
```

## Error Handling

The database layer includes robust error handling:

```python
from agentic_spec.exceptions import DatabaseError, ConnectionError

try:
    await backend.create_specification(spec)
except DatabaseError as e:
    print(f"Database operation failed: {e}")
except ConnectionError as e:
    print(f"Database connection failed: {e}")
```

## Performance Considerations

- **Connection Management**: Use the AsyncSpecManager context manager for proper connection lifecycle
- **Batch Operations**: Use transactions for multiple related operations
- **Indexing**: The database creates indexes on commonly queried fields (spec_id, status, timestamps)
- **Memory Usage**: SQLite is memory-efficient for typical specification workloads

## Schema

The database creates four main tables:

### specifications
- `id` (TEXT PRIMARY KEY): Unique specification identifier
- `title` (TEXT): Specification title
- `inherits` (JSON): List of inherited template IDs
- `created`, `updated` (TIMESTAMP): Creation and modification times
- `version` (TEXT): Specification version
- `status` (TEXT): Current status (draft, reviewed, approved, implemented, archived)
- `parent_spec_id` (TEXT): Parent specification for sub-specs
- `child_spec_ids` (JSON): List of child specification IDs
- `context` (JSON): Project context information
- `requirements` (JSON): Functional and non-functional requirements
- `review_notes` (JSON): Review feedback
- `context_parameters` (JSON): AI generation parameters

### tasks
- `id` (TEXT PRIMARY KEY): Unique task identifier
- `spec_id` (TEXT): Reference to parent specification
- `step_index` (INTEGER): Order index within specification
- `task` (TEXT): Task description
- `details` (TEXT): Detailed task information
- `files` (JSON): List of files involved
- `acceptance` (TEXT): Acceptance criteria
- `estimated_effort` (TEXT): Effort estimate
- `sub_spec_id` (TEXT): Reference to sub-specification if expanded
- `decomposition_hint` (TEXT): Guidance for task breakdown
- `status` (TEXT): Current task status
- `started_at`, `completed_at` (TIMESTAMP): Task timing
- `time_spent_minutes` (INTEGER): Actual time spent
- `completion_notes` (TEXT): Notes on task completion
- `blockers` (JSON): List of blocking issues

### approvals
- `id` (TEXT PRIMARY KEY): Unique approval identifier
- `task_id` (TEXT): Reference to approved task
- `level` (TEXT): Approval level (self, peer, ai, admin)
- `approved_by` (TEXT): Approver identifier
- `approved_at` (TIMESTAMP): Approval timestamp
- `comments` (TEXT): Approval comments
- `override_reason` (TEXT): Reason for any approval override

### work_logs
- `id` (TEXT PRIMARY KEY): Unique log entry identifier
- `spec_id` (TEXT): Reference to specification
- `task_id` (TEXT): Reference to task (optional)
- `action` (TEXT): Action performed
- `timestamp` (TIMESTAMP): When action occurred
- `duration_minutes` (INTEGER): Duration of work session
- `notes` (TEXT): Additional notes
- `metadata` (JSON): Additional structured data

## Testing

The database layer includes comprehensive async tests:

```bash
# Run async database tests
python -m pytest tests/test_simple_async_db.py -v

# Run with coverage
python -m pytest tests/test_simple_async_db.py --cov=agentic_spec.async_db
```

## Dependencies

The async database layer requires:

- `aiosqlite>=0.21.0`: Async SQLite driver
- `pydantic>=2.11.0`: Data validation and serialization

These are automatically installed with the agentic-spec package.
