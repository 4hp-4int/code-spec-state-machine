"""Tests for async database layer functionality."""

from datetime import datetime, timedelta
from pathlib import Path
import shutil
import tempfile

import pytest
import pytest_asyncio

# Configure pytest-asyncio
pytestmark = pytest.mark.asyncio

from agentic_spec.async_db import (
    AsyncSpecManager,
    DatabaseBackend,
    SQLiteBackend,
)
from agentic_spec.exceptions import ConfigurationError, DatabaseError
from agentic_spec.models import (
    ApprovalDB,
    ApprovalLevel,
    ImplementationStep,
    ProgrammingSpec,
    SpecContext,
    SpecificationDB,
    SpecMetadata,
    SpecRequirement,
    SpecStatus,
    TaskDB,
    TaskStatus,
    WorkLogDB,
)


class TestDatabaseBackend:
    """Test DatabaseBackend factory."""

    def test_create_sqlite_backend(self):
        """Test creating SQLite backend."""
        backend = DatabaseBackend.create("sqlite", database_path="test.db")
        assert isinstance(backend, SQLiteBackend)
        assert str(backend.database_path) == "test.db"

    def test_create_invalid_backend(self):
        """Test creating invalid backend raises error."""
        with pytest.raises(ConfigurationError):
            DatabaseBackend.create("invalid")

    def test_default_backend(self):
        """Test default backend is SQLite."""
        backend = DatabaseBackend.create()
        assert isinstance(backend, SQLiteBackend)


class TestSQLiteBackend:
    """Test SQLiteBackend functionality."""

    @pytest_asyncio.fixture
    async def temp_backend(self):
        """Create temporary SQLite backend for testing."""
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test.db"
        backend = SQLiteBackend(database_path=db_path)
        await backend.initialize()
        yield backend
        await backend.close()
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_spec_db(self):
        """Create sample SpecificationDB for testing."""
        return SpecificationDB(
            id="test-spec-123",
            title="Test Specification",
            inherits=[],
            created=datetime.now(),
            updated=datetime.now(),
            version="1.0",
            status=SpecStatus.DRAFT,
            parent_spec_id=None,
            child_spec_ids=[],
            context={"project": "test", "domain": "testing"},
            requirements={"functional": ["test"], "non_functional": ["fast"]},
            review_notes=["looks good"],
            context_parameters=None,
        )

    @pytest.fixture
    def sample_task_db(self):
        """Create sample TaskDB for testing."""
        return TaskDB(
            id="task-123",
            spec_id="test-spec-123",
            step_index=0,
            task="Implement feature",
            details="Create the feature",
            files=["feature.py"],
            acceptance="Feature works",
            estimated_effort="medium",
            sub_spec_id=None,
            decomposition_hint=None,
            status=TaskStatus.PENDING,
            started_at=None,
            completed_at=None,
            time_spent_minutes=None,
            completion_notes=None,
            blockers=[],
        )

    async def test_initialize_creates_tables(self, temp_backend):
        """Test that initialize creates necessary tables."""
        # Verify tables exist by trying to query them
        async with temp_backend.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ) as cursor:
            tables = await cursor.fetchall()
            table_names = [row[0] for row in tables]

        expected_tables = ["specifications", "tasks", "approvals", "work_logs"]
        for table in expected_tables:
            assert table in table_names

    async def test_create_and_get_specification(self, temp_backend, sample_spec_db):
        """Test creating and retrieving a specification."""
        # Create specification
        spec_id = await temp_backend.create_specification(sample_spec_db)
        assert spec_id == sample_spec_db.id

        # Retrieve specification
        retrieved_spec = await temp_backend.get_specification(spec_id)
        assert retrieved_spec is not None
        assert retrieved_spec.id == sample_spec_db.id
        assert retrieved_spec.title == sample_spec_db.title
        assert retrieved_spec.status == sample_spec_db.status

    async def test_get_nonexistent_specification(self, temp_backend):
        """Test retrieving a non-existent specification."""
        result = await temp_backend.get_specification("nonexistent")
        assert result is None

    async def test_update_specification(self, temp_backend, sample_spec_db):
        """Test updating a specification."""
        # Create specification
        await temp_backend.create_specification(sample_spec_db)

        # Update specification
        sample_spec_db.title = "Updated Title"
        sample_spec_db.status = SpecStatus.REVIEWED
        await temp_backend.update_specification(sample_spec_db)

        # Verify update
        retrieved_spec = await temp_backend.get_specification(sample_spec_db.id)
        assert retrieved_spec.title == "Updated Title"
        assert retrieved_spec.status == SpecStatus.REVIEWED

    async def test_delete_specification(self, temp_backend, sample_spec_db):
        """Test deleting a specification."""
        # Create specification
        await temp_backend.create_specification(sample_spec_db)

        # Delete specification
        await temp_backend.delete_specification(sample_spec_db.id)

        # Verify deletion
        result = await temp_backend.get_specification(sample_spec_db.id)
        assert result is None

    async def test_list_specifications(self, temp_backend, sample_spec_db):
        """Test listing specifications."""
        # Create multiple specifications
        spec1 = sample_spec_db
        spec2 = sample_spec_db.model_copy()
        spec2.id = "test-spec-456"
        spec2.title = "Second Spec"
        spec2.status = SpecStatus.IMPLEMENTED

        await temp_backend.create_specification(spec1)
        await temp_backend.create_specification(spec2)

        # List all specifications
        all_specs = await temp_backend.list_specifications()
        assert len(all_specs) == 2

        # List by status
        draft_specs = await temp_backend.list_specifications(status=SpecStatus.DRAFT)
        assert len(draft_specs) == 1
        assert draft_specs[0].status == SpecStatus.DRAFT

        # List with limit
        limited_specs = await temp_backend.list_specifications(limit=1)
        assert len(limited_specs) == 1

    async def test_create_and_get_task(
        self, temp_backend, sample_spec_db, sample_task_db
    ):
        """Test creating and retrieving a task."""
        # Create specification first
        await temp_backend.create_specification(sample_spec_db)

        # Create task
        task_id = await temp_backend.create_task(sample_task_db)
        assert task_id == sample_task_db.id

        # Retrieve task
        retrieved_task = await temp_backend.get_task(task_id)
        assert retrieved_task is not None
        assert retrieved_task.id == sample_task_db.id
        assert retrieved_task.task == sample_task_db.task
        assert retrieved_task.status == sample_task_db.status

    async def test_update_task_status(
        self, temp_backend, sample_spec_db, sample_task_db
    ):
        """Test updating task status."""
        # Create specification and task
        await temp_backend.create_specification(sample_spec_db)
        await temp_backend.create_task(sample_task_db)

        # Update task
        sample_task_db.status = TaskStatus.IN_PROGRESS
        sample_task_db.started_at = datetime.now()
        sample_task_db.completion_notes = "Working on it"
        await temp_backend.update_task(sample_task_db)

        # Verify update
        retrieved_task = await temp_backend.get_task(sample_task_db.id)
        assert retrieved_task.status == TaskStatus.IN_PROGRESS
        assert retrieved_task.started_at is not None
        assert retrieved_task.completion_notes == "Working on it"

    async def test_get_tasks_for_spec(self, temp_backend, sample_spec_db):
        """Test getting all tasks for a specification."""
        # Create specification
        await temp_backend.create_specification(sample_spec_db)

        # Create multiple tasks
        task1 = TaskDB(
            id="task-1",
            spec_id=sample_spec_db.id,
            step_index=0,
            task="First task",
            details="Details",
            files=["file1.py"],
            acceptance="Works",
            estimated_effort="low",
            status=TaskStatus.COMPLETED,
        )
        task2 = TaskDB(
            id="task-2",
            spec_id=sample_spec_db.id,
            step_index=1,
            task="Second task",
            details="Details",
            files=["file2.py"],
            acceptance="Works",
            estimated_effort="medium",
            status=TaskStatus.IN_PROGRESS,
        )

        await temp_backend.create_task(task1)
        await temp_backend.create_task(task2)

        # Get tasks for spec
        tasks = await temp_backend.get_tasks_for_spec(sample_spec_db.id)
        assert len(tasks) == 2
        assert tasks[0].step_index == 0  # Should be ordered by step_index
        assert tasks[1].step_index == 1

    async def test_create_and_get_approval(
        self, temp_backend, sample_spec_db, sample_task_db
    ):
        """Test creating and retrieving approvals."""
        # Create specification and task
        await temp_backend.create_specification(sample_spec_db)
        await temp_backend.create_task(sample_task_db)

        # Create approval
        approval = ApprovalDB(
            id="approval-123",
            task_id=sample_task_db.id,
            level=ApprovalLevel.PEER,
            approved_by="reviewer",
            approved_at=datetime.now(),
            comments="Looks good",
            override_reason=None,
        )
        approval_id = await temp_backend.create_approval(approval)
        assert approval_id == approval.id

        # Get approvals for task
        approvals = await temp_backend.get_approvals_for_task(sample_task_db.id)
        assert len(approvals) == 1
        assert approvals[0].level == ApprovalLevel.PEER
        assert approvals[0].approved_by == "reviewer"

    async def test_create_and_query_work_logs(self, temp_backend, sample_spec_db):
        """Test creating and querying work logs."""
        # Create specification
        await temp_backend.create_specification(sample_spec_db)

        # Create work logs
        now = datetime.now()
        log1 = WorkLogDB(
            id="log-1",
            spec_id=sample_spec_db.id,
            task_id="task-1",
            action="started",
            timestamp=now - timedelta(hours=2),
            duration_minutes=60,
            notes="Started working",
            metadata={"urgency": "high"},
        )
        log2 = WorkLogDB(
            id="log-2",
            spec_id=sample_spec_db.id,
            task_id="task-1",
            action="completed",
            timestamp=now,
            duration_minutes=30,
            notes="Finished work",
            metadata={},
        )

        await temp_backend.create_work_log(log1)
        await temp_backend.create_work_log(log2)

        # Query all logs
        all_logs = await temp_backend.get_work_logs()
        assert len(all_logs) == 2

        # Query by spec
        spec_logs = await temp_backend.get_work_logs(spec_id=sample_spec_db.id)
        assert len(spec_logs) == 2

        # Query by task
        task_logs = await temp_backend.get_work_logs(task_id="task-1")
        assert len(task_logs) == 2

        # Query by date range
        recent_logs = await temp_backend.get_work_logs(
            start_date=now - timedelta(hours=1)
        )
        assert len(recent_logs) == 1
        assert recent_logs[0].action == "completed"

        # Query with limit
        limited_logs = await temp_backend.get_work_logs(limit=1)
        assert len(limited_logs) == 1

    async def test_transaction_context_manager(self, temp_backend, sample_spec_db):
        """Test transaction context manager."""
        # Successful transaction
        async with temp_backend.transaction():
            await temp_backend.create_specification(sample_spec_db)

        # Verify data was committed
        result = await temp_backend.get_specification(sample_spec_db.id)
        assert result is not None

        # Failed transaction (should rollback)
        spec2 = sample_spec_db.model_copy()
        spec2.id = "test-spec-456"

        with pytest.raises(Exception):
            async with temp_backend.transaction():
                await temp_backend.create_specification(spec2)
                # Simulate error
                raise RuntimeError("Transaction failed")

        # Verify rollback (spec2 should not exist)
        result = await temp_backend.get_specification("test-spec-456")
        assert result is None

    async def test_database_not_initialized_error(self):
        """Test operations fail when database not initialized."""
        backend = SQLiteBackend("test.db")

        with pytest.raises(DatabaseError, match="Database not initialized"):
            await backend.create_specification(
                SpecificationDB(
                    id="test",
                    title="test",
                    inherits=[],
                    created=datetime.now(),
                    updated=datetime.now(),
                    version="1.0",
                    status=SpecStatus.DRAFT,
                    context={},
                    requirements={},
                )
            )

    async def test_missing_aiosqlite_dependency(self):
        """Test error when aiosqlite is not available."""
        backend = SQLiteBackend("test.db")

        # Mock the import to fail
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "aiosqlite":
                raise ImportError("No module named 'aiosqlite'")
            return original_import(name, *args, **kwargs)

        builtins.__import__ = mock_import

        try:
            with pytest.raises(DatabaseError, match="aiosqlite is required"):
                await backend.initialize()
        finally:
            builtins.__import__ = original_import

    async def test_close_connection(self, temp_backend):
        """Test closing database connection."""
        # Verify connection exists
        assert temp_backend.connection is not None

        # Close connection
        await temp_backend.close()
        assert temp_backend.connection is None


class TestAsyncSpecManager:
    """Test AsyncSpecManager functionality."""

    @pytest.fixture
    def sample_programming_spec(self):
        """Create a sample ProgrammingSpec for testing."""
        metadata = SpecMetadata(
            id="manager-test-123",
            title="Manager Test Spec",
            inherits=[],
            created=datetime.now().isoformat(),
            version="1.0",
            status="draft",
        )

        context = SpecContext(
            project="test-project",
            domain="Testing",
            dependencies=[{"name": "pytest", "version": "8.0.0"}],
            files_involved=["test.py"],
        )

        requirements = SpecRequirement(
            functional=["Test functionality"],
            non_functional=["Performance"],
            constraints=["Python 3.12+"],
        )

        implementation = [
            ImplementationStep(
                task="Implement feature",
                details="Create the feature",
                files=["feature.py"],
                acceptance="Feature works",
                step_id="manager-test-123:0",
            )
        ]

        return ProgrammingSpec(
            metadata=metadata,
            context=context,
            requirements=requirements,
            implementation=implementation,
        )

    async def test_async_context_manager(self):
        """Test AsyncSpecManager as async context manager."""
        temp_dir = tempfile.mkdtemp()
        try:
            backend = SQLiteBackend(Path(temp_dir) / "test.db")

            async with AsyncSpecManager(backend) as manager:
                assert manager.backend.connection is not None

            # Connection should be closed after exiting context
            assert manager.backend.connection is None
        finally:
            shutil.rmtree(temp_dir)

    async def test_save_spec_to_db(self, sample_programming_spec):
        """Test saving ProgrammingSpec to database."""
        temp_dir = tempfile.mkdtemp()
        try:
            backend = SQLiteBackend(Path(temp_dir) / "test.db")

            async with AsyncSpecManager(backend) as manager:
                spec_id = await manager.save_spec_to_db(sample_programming_spec)
                assert spec_id == sample_programming_spec.metadata.id

                # Verify spec was saved
                saved_spec = await backend.get_specification(spec_id)
                assert saved_spec is not None
                assert saved_spec.title == sample_programming_spec.metadata.title

                # Verify tasks were saved
                tasks = await backend.get_tasks_for_spec(spec_id)
                assert len(tasks) == 1
                assert tasks[0].task == "Implement feature"

        finally:
            shutil.rmtree(temp_dir)

    async def test_save_spec_with_work_logs(self, sample_programming_spec):
        """Test saving spec with work logs."""
        # Add work logs to spec
        from agentic_spec.models import WorkLogEntry

        sample_programming_spec.work_logs = [
            WorkLogEntry(
                spec_id=sample_programming_spec.metadata.id,
                step_id="manager-test-123:0",
                action="started",
                timestamp=datetime.now(),
                notes="Beginning work",
            )
        ]

        temp_dir = tempfile.mkdtemp()
        try:
            backend = SQLiteBackend(Path(temp_dir) / "test.db")

            async with AsyncSpecManager(backend) as manager:
                await manager.save_spec_to_db(sample_programming_spec)

                # Verify work logs were saved
                logs = await backend.get_work_logs(
                    spec_id=sample_programming_spec.metadata.id
                )
                assert len(logs) == 1
                assert logs[0].action == "started"

        finally:
            shutil.rmtree(temp_dir)
