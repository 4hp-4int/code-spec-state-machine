"""Async database layer for specifications with SQLite and PostgreSQL backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from datetime import datetime
import json
from pathlib import Path
from typing import TYPE_CHECKING
import uuid

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

from .exceptions import ConfigurationError, DatabaseError
from .models import (
    ApprovalDB,
    ApprovalLevel,
    ProgrammingSpec,
    SpecificationDB,
    SpecStatus,
    TaskDB,
    TaskStatus,
    WorkLogDB,
)


class AsyncDatabaseInterface(ABC):
    """Abstract interface for async database operations."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize database and create tables if needed."""

    @abstractmethod
    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[None, None]:
        """Async context manager for database transactions."""

    @abstractmethod
    async def close(self) -> None:
        """Close database connection."""

    # Specification CRUD operations
    @abstractmethod
    async def create_specification(self, spec: SpecificationDB) -> str:
        """Create a new specification and return its ID."""

    @abstractmethod
    async def get_specification(self, spec_id: str) -> SpecificationDB | None:
        """Get specification by ID."""

    @abstractmethod
    async def update_specification(self, spec: SpecificationDB) -> None:
        """Update an existing specification."""

    @abstractmethod
    async def delete_specification(self, spec_id: str) -> None:
        """Delete a specification by ID."""

    @abstractmethod
    async def list_specifications(
        self,
        status: SpecStatus | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[SpecificationDB]:
        """List specifications with optional filtering."""

    # Task CRUD operations
    @abstractmethod
    async def create_task(self, task: TaskDB) -> str:
        """Create a new task and return its ID."""

    @abstractmethod
    async def get_task(self, task_id: str) -> TaskDB | None:
        """Get task by ID."""

    @abstractmethod
    async def update_task(self, task: TaskDB) -> None:
        """Update an existing task."""

    @abstractmethod
    async def delete_task(self, task_id: str) -> None:
        """Delete a task by ID."""

    @abstractmethod
    async def get_tasks_for_spec(self, spec_id: str) -> list[TaskDB]:
        """Get all tasks for a specification."""

    # Approval operations
    @abstractmethod
    async def create_approval(self, approval: ApprovalDB) -> str:
        """Create a new approval and return its ID."""

    @abstractmethod
    async def get_approvals_for_task(self, task_id: str) -> list[ApprovalDB]:
        """Get all approvals for a task."""

    # Work log operations
    @abstractmethod
    async def create_work_log(self, log: WorkLogDB) -> str:
        """Create a new work log entry and return its ID."""

    @abstractmethod
    async def get_work_logs(
        self,
        spec_id: str | None = None,
        task_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int | None = None,
    ) -> list[WorkLogDB]:
        """Query work logs with optional filtering."""


class DatabaseBackend:
    """Factory for creating database backend instances."""

    @staticmethod
    def create(backend_type: str = "sqlite", **config) -> AsyncDatabaseInterface:
        """Create a database backend instance based on type."""
        if backend_type.lower() == "sqlite":
            return SQLiteBackend(**config)
        msg = f"Unsupported database backend: {backend_type}. Only SQLite is supported."
        raise ConfigurationError(msg)


class SQLiteBackend(AsyncDatabaseInterface):
    """SQLite async database backend using aiosqlite."""

    def __init__(self, database_path: str | Path = "agentic_spec.db"):
        self.database_path = Path(database_path)
        self.connection = None

    async def initialize(self) -> None:
        """Initialize SQLite database and create tables."""
        try:
            import aiosqlite
        except ImportError as err:
            msg = "aiosqlite is required for SQLite backend. Install with: pip install aiosqlite"
            raise DatabaseError(msg) from err

        self.connection = await aiosqlite.connect(str(self.database_path))
        await self._create_tables()

    async def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        tables = [
            """
            CREATE TABLE IF NOT EXISTS specifications (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                inherits TEXT DEFAULT '[]',
                created TIMESTAMP NOT NULL,
                updated TIMESTAMP NOT NULL,
                version TEXT NOT NULL,
                status TEXT NOT NULL,
                parent_spec_id TEXT,
                child_spec_ids TEXT DEFAULT '[]',
                context TEXT NOT NULL,
                requirements TEXT NOT NULL,
                review_notes TEXT DEFAULT '[]',
                context_parameters TEXT,
                -- Enhanced tracking fields
                workflow_status TEXT DEFAULT 'created',
                is_completed BOOLEAN DEFAULT FALSE,
                completed_at TIMESTAMP,
                last_accessed TIMESTAMP,
                completion_percentage REAL DEFAULT 0.0,
                priority INTEGER DEFAULT 5,
                -- Lifecycle timestamps
                reviewed_at TIMESTAMP,
                approved_at TIMESTAMP,
                implemented_at TIMESTAMP,
                -- Metadata tracking
                created_by TEXT DEFAULT 'system',
                last_updated_by TEXT DEFAULT 'system',
                tags TEXT DEFAULT '[]'
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                spec_id TEXT NOT NULL,
                step_index INTEGER NOT NULL,
                task TEXT NOT NULL,
                details TEXT NOT NULL,
                files TEXT NOT NULL,
                acceptance TEXT NOT NULL,
                estimated_effort TEXT NOT NULL,
                sub_spec_id TEXT,
                decomposition_hint TEXT,
                status TEXT DEFAULT 'pending',
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                time_spent_minutes INTEGER,
                completion_notes TEXT,
                blockers TEXT DEFAULT '[]',
                -- Enhanced tracking fields
                is_completed BOOLEAN DEFAULT FALSE,
                assigned_to TEXT DEFAULT 'unassigned',
                priority INTEGER DEFAULT 5,
                last_accessed TIMESTAMP,
                estimated_completion_date TIMESTAMP,
                actual_effort_minutes INTEGER,
                dependencies TEXT DEFAULT '[]',
                -- Lifecycle timestamps
                blocked_at TIMESTAMP,
                unblocked_at TIMESTAMP,
                approved_at TIMESTAMP,
                rejected_at TIMESTAMP,
                FOREIGN KEY (spec_id) REFERENCES specifications (id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS approvals (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                level TEXT NOT NULL,
                approved_by TEXT NOT NULL,
                approved_at TIMESTAMP NOT NULL,
                comments TEXT,
                override_reason TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS work_logs (
                id TEXT PRIMARY KEY,
                spec_id TEXT NOT NULL,
                task_id TEXT,
                action TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                duration_minutes INTEGER,
                notes TEXT,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (spec_id) REFERENCES specifications (id) ON DELETE CASCADE,
                FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE SET NULL
            )
            """,
        ]

        for table_sql in tables:
            await self.connection.execute(table_sql)

        # Create indexes for performance optimization
        indexes = [
            # Specifications indexes
            "CREATE INDEX IF NOT EXISTS idx_specs_status ON specifications (status)",
            "CREATE INDEX IF NOT EXISTS idx_specs_workflow_status ON specifications (workflow_status)",
            "CREATE INDEX IF NOT EXISTS idx_specs_is_completed ON specifications (is_completed)",
            "CREATE INDEX IF NOT EXISTS idx_specs_priority ON specifications (priority)",
            "CREATE INDEX IF NOT EXISTS idx_specs_created ON specifications (created)",
            "CREATE INDEX IF NOT EXISTS idx_specs_updated ON specifications (updated)",
            "CREATE INDEX IF NOT EXISTS idx_specs_completed_at ON specifications (completed_at)",
            "CREATE INDEX IF NOT EXISTS idx_specs_parent_id ON specifications (parent_spec_id)",
            "CREATE INDEX IF NOT EXISTS idx_specs_tags ON specifications (tags)",
            # Tasks indexes
            "CREATE INDEX IF NOT EXISTS idx_tasks_spec_id ON tasks (spec_id)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_is_completed ON tasks (is_completed)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks (priority)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_assigned_to ON tasks (assigned_to)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_started_at ON tasks (started_at)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_completed_at ON tasks (completed_at)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_step_index ON tasks (step_index)",
            # Work logs indexes
            "CREATE INDEX IF NOT EXISTS idx_work_logs_spec_id ON work_logs (spec_id)",
            "CREATE INDEX IF NOT EXISTS idx_work_logs_task_id ON work_logs (task_id)",
            "CREATE INDEX IF NOT EXISTS idx_work_logs_timestamp ON work_logs (timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_work_logs_action ON work_logs (action)",
            # Approvals indexes
            "CREATE INDEX IF NOT EXISTS idx_approvals_task_id ON approvals (task_id)",
            "CREATE INDEX IF NOT EXISTS idx_approvals_level ON approvals (level)",
            "CREATE INDEX IF NOT EXISTS idx_approvals_approved_at ON approvals (approved_at)",
        ]

        for index_sql in indexes:
            await self.connection.execute(index_sql)

        await self.connection.commit()

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[None, None]:
        """Async context manager for database transactions."""
        if not self.connection:
            msg = "Database not initialized"
            raise DatabaseError(msg)

        try:
            await self.connection.execute("BEGIN")
            yield
            await self.connection.commit()
        except Exception:
            await self.connection.rollback()
            raise

    async def close(self) -> None:
        """Close database connection."""
        if self.connection:
            await self.connection.close()
            self.connection = None

    async def create_specification(self, spec: SpecificationDB) -> str:
        """Create a new specification."""
        if not self.connection:
            msg = "Database not initialized"
            raise DatabaseError(msg)

        sql = """
        INSERT INTO specifications (
            id, title, inherits, created, updated, version, status,
            parent_spec_id, child_spec_ids, context, requirements,
            review_notes, context_parameters, workflow_status, is_completed,
            completed_at, last_accessed, completion_percentage, priority,
            reviewed_at, approved_at, implemented_at, created_by, last_updated_by, tags
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        values = (
            spec.id,
            spec.title,
            json.dumps(spec.inherits),
            spec.created,
            spec.updated,
            spec.version,
            spec.status.value,
            spec.parent_spec_id,
            json.dumps(spec.child_spec_ids),
            json.dumps(spec.context),
            json.dumps(spec.requirements),
            json.dumps(spec.review_notes),
            json.dumps(spec.context_parameters) if spec.context_parameters else None,
            spec.workflow_status.value,
            spec.is_completed,
            spec.completed_at,
            spec.last_accessed,
            spec.completion_percentage,
            spec.priority,
            spec.reviewed_at,
            spec.approved_at,
            spec.implemented_at,
            spec.created_by,
            spec.last_updated_by,
            json.dumps(spec.tags),
        )

        await self.connection.execute(sql, values)
        await self.connection.commit()
        return spec.id

    async def get_specification(self, spec_id: str) -> SpecificationDB | None:
        """Get specification by ID."""
        if not self.connection:
            msg = "Database not initialized"
            raise DatabaseError(msg)

        sql = "SELECT * FROM specifications WHERE id = ?"
        async with self.connection.execute(sql, (spec_id,)) as cursor:
            row = await cursor.fetchone()

        if not row:
            return None

        return self._row_to_specification(row)

    async def update_specification(self, spec: SpecificationDB) -> None:
        """Update an existing specification."""
        if not self.connection:
            msg = "Database not initialized"
            raise DatabaseError(msg)

        sql = """
        UPDATE specifications SET
            title = ?, inherits = ?, updated = ?, version = ?, status = ?,
            parent_spec_id = ?, child_spec_ids = ?, context = ?,
            requirements = ?, review_notes = ?, context_parameters = ?
        WHERE id = ?
        """

        values = (
            spec.title,
            json.dumps(spec.inherits),
            datetime.now(datetime.timezone.utc),
            spec.version,
            spec.status.value,
            spec.parent_spec_id,
            json.dumps(spec.child_spec_ids),
            json.dumps(spec.context),
            json.dumps(spec.requirements),
            json.dumps(spec.review_notes),
            json.dumps(spec.context_parameters) if spec.context_parameters else None,
            spec.id,
        )

        await self.connection.execute(sql, values)
        await self.connection.commit()

    async def delete_specification(self, spec_id: str) -> None:
        """Delete a specification by ID."""
        if not self.connection:
            msg = "Database not initialized"
            raise DatabaseError(msg)

        await self.connection.execute(
            "DELETE FROM specifications WHERE id = ?", (spec_id,)
        )
        await self.connection.commit()

    async def list_specifications(
        self,
        status: SpecStatus | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[SpecificationDB]:
        """List specifications with optional filtering."""
        if not self.connection:
            msg = "Database not initialized"
            raise DatabaseError(msg)

        sql = "SELECT * FROM specifications"
        params = []

        if status:
            sql += " WHERE status = ?"
            params.append(status.value)

        sql += " ORDER BY created DESC"

        if limit:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        async with self.connection.execute(sql, params) as cursor:
            rows = await cursor.fetchall()

        return [self._row_to_specification(row) for row in rows]

    def _row_to_specification(self, row) -> SpecificationDB:
        """Convert database row to SpecificationDB model."""
        from .models import WorkflowStatus

        # Handle both old and new database schemas
        base_spec = SpecificationDB(
            id=row[0],
            title=row[1],
            inherits=json.loads(row[2]),
            created=datetime.fromisoformat(row[3]),
            updated=datetime.fromisoformat(row[4]),
            version=row[5],
            status=SpecStatus(row[6]),
            parent_spec_id=row[7],
            child_spec_ids=json.loads(row[8]),
            context=json.loads(row[9]),
            requirements=json.loads(row[10]),
            review_notes=json.loads(row[11]),
            context_parameters=json.loads(row[12]) if row[12] else None,
        )

        # Check if we have the enhanced tracking fields (new schema)
        if len(row) >= 25:
            # Enhanced tracking fields
            base_spec.workflow_status = (
                WorkflowStatus(row[13]) if row[13] else WorkflowStatus.CREATED
            )
            base_spec.is_completed = bool(row[14]) if row[14] is not None else False
            base_spec.completed_at = (
                datetime.fromisoformat(row[15]) if row[15] else None
            )
            base_spec.last_accessed = (
                datetime.fromisoformat(row[16]) if row[16] else None
            )
            base_spec.completion_percentage = (
                float(row[17]) if row[17] is not None else 0.0
            )
            base_spec.priority = int(row[18]) if row[18] is not None else 5
            # Lifecycle timestamps
            base_spec.reviewed_at = datetime.fromisoformat(row[19]) if row[19] else None
            base_spec.approved_at = datetime.fromisoformat(row[20]) if row[20] else None
            base_spec.implemented_at = (
                datetime.fromisoformat(row[21]) if row[21] else None
            )
            # Metadata tracking
            base_spec.created_by = row[22] if row[22] else "system"
            base_spec.last_updated_by = row[23] if row[23] else "system"
            base_spec.tags = json.loads(row[24]) if row[24] else []

        return base_spec

    async def create_task(self, task: TaskDB) -> str:
        """Create a new task."""
        if not self.connection:
            msg = "Database not initialized"
            raise DatabaseError(msg)

        sql = """
        INSERT INTO tasks (
            id, spec_id, step_index, task, details, files, acceptance,
            estimated_effort, sub_spec_id, decomposition_hint, status,
            started_at, completed_at, time_spent_minutes, completion_notes, blockers
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        values = (
            task.id,
            task.spec_id,
            task.step_index,
            task.task,
            task.details,
            json.dumps(task.files),
            task.acceptance,
            task.estimated_effort,
            task.sub_spec_id,
            task.decomposition_hint,
            task.status.value,
            task.started_at,
            task.completed_at,
            task.time_spent_minutes,
            task.completion_notes,
            json.dumps(task.blockers),
        )

        await self.connection.execute(sql, values)
        await self.connection.commit()
        return task.id

    async def get_task(self, task_id: str) -> TaskDB | None:
        """Get task by ID."""
        if not self.connection:
            msg = "Database not initialized"
            raise DatabaseError(msg)

        sql = "SELECT * FROM tasks WHERE id = ?"
        async with self.connection.execute(sql, (task_id,)) as cursor:
            row = await cursor.fetchone()

        if not row:
            return None

        return self._row_to_task(row)

    async def update_task(self, task: TaskDB) -> None:
        """Update an existing task."""
        if not self.connection:
            msg = "Database not initialized"
            raise DatabaseError(msg)

        sql = """
        UPDATE tasks SET
            task = ?, details = ?, files = ?, acceptance = ?, estimated_effort = ?,
            sub_spec_id = ?, decomposition_hint = ?, status = ?, started_at = ?,
            completed_at = ?, time_spent_minutes = ?, completion_notes = ?, blockers = ?
        WHERE id = ?
        """

        values = (
            task.task,
            task.details,
            json.dumps(task.files),
            task.acceptance,
            task.estimated_effort,
            task.sub_spec_id,
            task.decomposition_hint,
            task.status.value,
            task.started_at,
            task.completed_at,
            task.time_spent_minutes,
            task.completion_notes,
            json.dumps(task.blockers),
            task.id,
        )

        await self.connection.execute(sql, values)
        await self.connection.commit()

    async def delete_task(self, task_id: str) -> None:
        """Delete a task by ID."""
        if not self.connection:
            msg = "Database not initialized"
            raise DatabaseError(msg)

        await self.connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        await self.connection.commit()

    async def get_tasks_for_spec(self, spec_id: str) -> list[TaskDB]:
        """Get all tasks for a specification."""
        if not self.connection:
            msg = "Database not initialized"
            raise DatabaseError(msg)

        sql = "SELECT * FROM tasks WHERE spec_id = ? ORDER BY step_index"
        async with self.connection.execute(sql, (spec_id,)) as cursor:
            rows = await cursor.fetchall()

        return [self._row_to_task(row) for row in rows]

    def _row_to_task(self, row) -> TaskDB:
        """Convert database row to TaskDB model."""
        return TaskDB(
            id=row[0],
            spec_id=row[1],
            step_index=row[2],
            task=row[3],
            details=row[4],
            files=json.loads(row[5]),
            acceptance=row[6],
            estimated_effort=row[7],
            sub_spec_id=row[8],
            decomposition_hint=row[9],
            status=TaskStatus(row[10]),
            started_at=datetime.fromisoformat(row[11]) if row[11] else None,
            completed_at=datetime.fromisoformat(row[12]) if row[12] else None,
            time_spent_minutes=row[13],
            completion_notes=row[14],
            blockers=json.loads(row[15]),
        )

    async def create_approval(self, approval: ApprovalDB) -> str:
        """Create a new approval."""
        if not self.connection:
            msg = "Database not initialized"
            raise DatabaseError(msg)

        sql = """
        INSERT INTO approvals (id, task_id, level, approved_by, approved_at, comments, override_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """

        values = (
            approval.id,
            approval.task_id,
            approval.level.value,
            approval.approved_by,
            approval.approved_at,
            approval.comments,
            approval.override_reason,
        )

        await self.connection.execute(sql, values)
        await self.connection.commit()
        return approval.id

    async def get_approvals_for_task(self, task_id: str) -> list[ApprovalDB]:
        """Get all approvals for a task."""
        if not self.connection:
            msg = "Database not initialized"
            raise DatabaseError(msg)

        sql = "SELECT * FROM approvals WHERE task_id = ? ORDER BY approved_at"
        async with self.connection.execute(sql, (task_id,)) as cursor:
            rows = await cursor.fetchall()

        return [self._row_to_approval(row) for row in rows]

    def _row_to_approval(self, row) -> ApprovalDB:
        """Convert database row to ApprovalDB model."""
        return ApprovalDB(
            id=row[0],
            task_id=row[1],
            level=ApprovalLevel(row[2]),
            approved_by=row[3],
            approved_at=datetime.fromisoformat(row[4]),
            comments=row[5],
            override_reason=row[6],
        )

    async def create_work_log(self, log: WorkLogDB) -> str:
        """Create a new work log entry."""
        if not self.connection:
            msg = "Database not initialized"
            raise DatabaseError(msg)

        sql = """
        INSERT INTO work_logs (id, spec_id, task_id, action, timestamp, duration_minutes, notes, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """

        values = (
            log.id,
            log.spec_id,
            log.task_id,
            log.action,
            log.timestamp,
            log.duration_minutes,
            log.notes,
            json.dumps(log.metadata),
        )

        await self.connection.execute(sql, values)
        await self.connection.commit()
        return log.id

    async def get_work_logs(
        self,
        spec_id: str | None = None,
        task_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int | None = None,
    ) -> list[WorkLogDB]:
        """Query work logs with optional filtering."""
        if not self.connection:
            msg = "Database not initialized"
            raise DatabaseError(msg)

        sql = "SELECT * FROM work_logs WHERE 1=1"
        params = []

        if spec_id:
            sql += " AND spec_id = ?"
            params.append(spec_id)

        if task_id:
            sql += " AND task_id = ?"
            params.append(task_id)

        if start_date:
            sql += " AND timestamp >= ?"
            params.append(start_date)

        if end_date:
            sql += " AND timestamp <= ?"
            params.append(end_date)

        sql += " ORDER BY timestamp DESC"

        if limit:
            sql += " LIMIT ?"
            params.append(limit)

        async with self.connection.execute(sql, params) as cursor:
            rows = await cursor.fetchall()

        return [self._row_to_work_log(row) for row in rows]

    # Enhanced query methods leveraging new indexes
    async def get_specifications_by_workflow_status(
        self, workflow_status: "WorkflowStatus", limit: int | None = None
    ) -> list[SpecificationDB]:
        """Get specifications by workflow status (uses index)."""
        if not self.connection:
            msg = "Database not initialized"
            raise DatabaseError(msg)

        sql = "SELECT * FROM specifications WHERE workflow_status = ? ORDER BY priority, updated DESC"
        params = [workflow_status.value]

        if limit:
            sql += " LIMIT ?"
            params.append(limit)

        async with self.connection.execute(sql, params) as cursor:
            rows = await cursor.fetchall()

        return [self._row_to_specification(row) for row in rows]

    async def get_completed_specifications(
        self, limit: int | None = None
    ) -> list[SpecificationDB]:
        """Get completed specifications (uses index)."""
        if not self.connection:
            msg = "Database not initialized"
            raise DatabaseError(msg)

        sql = "SELECT * FROM specifications WHERE is_completed = TRUE ORDER BY completed_at DESC"
        params = []

        if limit:
            sql += " LIMIT ?"
            params.append(limit)

        async with self.connection.execute(sql, params) as cursor:
            rows = await cursor.fetchall()

        return [self._row_to_specification(row) for row in rows]

    async def get_high_priority_tasks(
        self, priority_threshold: int = 3, limit: int | None = None
    ) -> list[TaskDB]:
        """Get high priority tasks (uses index)."""
        if not self.connection:
            msg = "Database not initialized"
            raise DatabaseError(msg)

        sql = "SELECT * FROM tasks WHERE priority <= ? ORDER BY priority, started_at"
        params = [priority_threshold]

        if limit:
            sql += " LIMIT ?"
            params.append(limit)

        async with self.connection.execute(sql, params) as cursor:
            rows = await cursor.fetchall()

        return [self._row_to_task(row) for row in rows]

    async def get_tasks_by_assignee(
        self, assigned_to: str, limit: int | None = None
    ) -> list[TaskDB]:
        """Get tasks by assignee (uses index)."""
        if not self.connection:
            msg = "Database not initialized"
            raise DatabaseError(msg)

        sql = "SELECT * FROM tasks WHERE assigned_to = ? ORDER BY priority, started_at"
        params = [assigned_to]

        if limit:
            sql += " LIMIT ?"
            params.append(limit)

        async with self.connection.execute(sql, params) as cursor:
            rows = await cursor.fetchall()

        return [self._row_to_task(row) for row in rows]

    def _row_to_work_log(self, row) -> WorkLogDB:
        """Convert database row to WorkLogDB model."""
        return WorkLogDB(
            id=row[0],
            spec_id=row[1],
            task_id=row[2],
            action=row[3],
            timestamp=datetime.fromisoformat(row[4]),
            duration_minutes=row[5],
            notes=row[6],
            metadata=json.loads(row[7]),
        )


class AsyncSpecManager:
    """High-level async manager for specification operations."""

    def __init__(self, backend: AsyncDatabaseInterface):
        self.backend = backend

    async def __aenter__(self):
        """Async context manager entry."""
        await self.backend.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.backend.close()

    async def save_spec_to_db(self, spec: ProgrammingSpec) -> str:
        """Convert ProgrammingSpec to database format and save."""
        # Convert to database model with enhanced tracking
        spec_db = SpecificationDB(
            id=spec.metadata.id,
            title=spec.metadata.title,
            inherits=spec.metadata.inherits,
            created=datetime.fromisoformat(spec.metadata.created),
            updated=datetime.now(datetime.timezone.utc),
            version=spec.metadata.version,
            status=SpecStatus(spec.metadata.status),
            parent_spec_id=spec.metadata.parent_spec_id,
            child_spec_ids=spec.metadata.child_spec_ids or [],
            context=spec.context.to_dict(),
            requirements=spec.requirements.to_dict(),
            review_notes=spec.review_notes or [],
            context_parameters=spec.context_parameters.to_dict()
            if spec.context_parameters
            else None,
            # Enhanced tracking fields with intelligent defaults
            workflow_status=self._determine_workflow_status(spec.metadata.status),
            is_completed=spec.metadata.status in ["implemented", "archived"],
            completion_percentage=self._calculate_completion_percentage(spec),
            priority=5,  # Default priority
            created_by="migration",
            last_updated_by="migration",
            tags=[],
        )

        # Save specification
        await self.backend.create_specification(spec_db)

        # Save tasks
        for i, step in enumerate(spec.implementation):
            task_db = TaskDB(
                id=step.step_id or f"{spec.metadata.id}:{i}",
                spec_id=spec.metadata.id,
                step_index=i,
                task=step.task,
                details=step.details,
                files=step.files,
                acceptance=step.acceptance,
                estimated_effort=step.estimated_effort,
                sub_spec_id=step.sub_spec_id,
                decomposition_hint=step.decomposition_hint,
                status=step.progress.status if step.progress else TaskStatus.PENDING,
                started_at=step.progress.started_at if step.progress else None,
                completed_at=step.progress.completed_at if step.progress else None,
                time_spent_minutes=step.progress.time_spent_minutes
                if step.progress
                else None,
                completion_notes=step.progress.completion_notes
                if step.progress
                else None,
                blockers=step.progress.blockers or [] if step.progress else [],
            )
            await self.backend.create_task(task_db)

            # Save approvals if any
            if step.approvals:
                for approval in step.approvals:
                    approval_db = ApprovalDB(
                        id=str(uuid.uuid4()),
                        task_id=task_db.id,
                        level=approval.level,
                        approved_by=approval.approved_by,
                        approved_at=approval.approved_at,
                        comments=approval.comments,
                        override_reason=approval.override_reason,
                    )
                    await self.backend.create_approval(approval_db)

        # Save work logs if any
        if spec.work_logs:
            for log in spec.work_logs:
                log_db = WorkLogDB(
                    id=str(uuid.uuid4()),
                    spec_id=log.spec_id,
                    task_id=log.step_id,  # Map step_id to task_id
                    action=log.action,
                    timestamp=log.timestamp,
                    duration_minutes=log.duration_minutes,
                    notes=log.notes,
                    metadata=log.metadata or {},
                )
                await self.backend.create_work_log(log_db)

        return spec.metadata.id

    def _determine_workflow_status(self, status: str) -> "WorkflowStatus":
        """Map specification status to workflow status."""
        from .models import WorkflowStatus

        mapping = {
            "draft": WorkflowStatus.CREATED,
            "reviewed": WorkflowStatus.READY_FOR_REVIEW,
            "approved": WorkflowStatus.READY_FOR_IMPLEMENTATION,
            "implemented": WorkflowStatus.COMPLETED,
            "archived": WorkflowStatus.COMPLETED,
        }
        return mapping.get(status, WorkflowStatus.CREATED)

    def _calculate_completion_percentage(self, spec: ProgrammingSpec) -> float:
        """Calculate completion percentage based on implementation steps."""
        if not spec.implementation:
            return 0.0

        completed_steps = 0
        total_steps = len(spec.implementation)

        for step in spec.implementation:
            if step.progress and step.progress.status.value in [
                "completed",
                "approved",
            ]:
                completed_steps += 1

        return (completed_steps / total_steps) * 100.0 if total_steps > 0 else 0.0

    async def get_specification(self, spec_id: str) -> SpecificationDB | None:
        """Get specification by ID."""
        return await self.backend.get_specification(spec_id)

    async def update_specification(self, spec: SpecificationDB) -> None:
        """Update an existing specification."""
        await self.backend.update_specification(spec)

    async def create_specification(self, spec: SpecificationDB) -> str:
        """Create a new specification."""
        return await self.backend.create_specification(spec)
