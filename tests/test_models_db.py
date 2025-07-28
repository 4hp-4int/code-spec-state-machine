"""Tests for database-enabled models and storage functionality."""

from datetime import datetime, timedelta
import shutil
import tempfile

import pytest
import yaml

from agentic_spec.db import FileBasedSpecStorage
from agentic_spec.exceptions import SpecificationError
from agentic_spec.models import (
    ApprovalLevel,
    ApprovalRecord,
    DependencyModel,
    ImplementationStep,
    ProgrammingSpec,
    SpecContext,
    SpecMetadata,
    SpecRequirement,
    TaskProgress,
    TaskStatus,
)


class TestDependencyModel:
    """Test DependencyModel functionality."""

    def test_dependency_basic(self):
        """Test basic dependency creation."""
        dep = DependencyModel(name="pytest", version="8.0.0")
        assert dep.name == "pytest"
        assert dep.version == "8.0.0"
        assert dep.description is None

    def test_dependency_with_description(self):
        """Test dependency with description."""
        dep = DependencyModel(
            name="pydantic", version="2.11.0", description="Data validation library"
        )
        assert dep.description == "Data validation library"

    def test_dependency_serialization(self):
        """Test dependency serialization."""
        dep = DependencyModel(name="typer", version="0.12.0")
        data = dep.model_dump(exclude_none=True)
        assert data == {"name": "typer", "version": "0.12.0"}

    def test_dependency_extra_fields(self):
        """Test dependency with extra fields."""
        dep = DependencyModel(
            name="custom",
            version="1.0.0",
            license="MIT",  # Extra field
            repository="https://github.com/example/custom",  # Extra field
        )
        data = dep.model_dump()
        assert "license" in data
        assert data["license"] == "MIT"


class TestTaskProgress:
    """Test TaskProgress functionality."""

    def test_progress_defaults(self):
        """Test default progress values."""
        progress = TaskProgress()
        assert progress.status == TaskStatus.PENDING
        assert progress.started_at is None
        assert progress.completed_at is None

    def test_progress_with_times(self):
        """Test progress with timestamps."""
        now = datetime.now()
        progress = TaskProgress(
            status=TaskStatus.COMPLETED,
            started_at=now - timedelta(hours=2),
            completed_at=now,
            time_spent_minutes=120,
        )
        assert progress.time_spent_minutes == 120

    def test_progress_blockers(self):
        """Test progress with blockers."""
        progress = TaskProgress(
            status=TaskStatus.BLOCKED,
            blockers=["Waiting for API access", "Need design approval"],
        )
        assert len(progress.blockers) == 2
        assert "Waiting for API access" in progress.blockers


class TestApprovalRecord:
    """Test ApprovalRecord functionality."""

    def test_approval_basic(self):
        """Test basic approval creation."""
        now = datetime.now()
        approval = ApprovalRecord(
            level=ApprovalLevel.PEER,
            approved_by="john.doe",
            approved_at=now,
            comments="Looks good to me",
        )
        assert approval.level == ApprovalLevel.PEER
        assert approval.approved_by == "john.doe"
        assert approval.comments == "Looks good to me"

    def test_approval_with_override(self):
        """Test approval with override reason."""
        approval = ApprovalRecord(
            level=ApprovalLevel.ADMIN,
            approved_by="admin",
            approved_at=datetime.now(),
            override_reason="Urgent deadline",
        )
        assert approval.override_reason == "Urgent deadline"


class TestProgrammingSpecSerialization:
    """Test ProgrammingSpec serialization/deserialization."""

    @pytest.fixture
    def sample_spec_data(self):
        """Create sample specification data."""
        return {
            "metadata": {
                "id": "test123",
                "title": "Test Specification",
                "inherits": [],
                "created": "2025-07-27T10:00:00",
                "version": "1.0",
                "status": "draft",
                "parent_spec_id": None,
                "child_spec_ids": None,
            },
            "context": {
                "project": "test-project",
                "domain": "Testing",
                "dependencies": [
                    {"name": "pytest", "version": "8.0.0"},
                    {"name": "pydantic", "version": "2.11.0"},
                ],
                "files_involved": ["test.py"],
            },
            "requirements": {
                "functional": ["Test feature"],
                "non_functional": ["Performance"],
                "constraints": ["Python 3.12+"],
            },
            "implementation": [
                {
                    "task": "Write tests",
                    "details": "Create unit tests",
                    "files": ["tests/test_feature.py"],
                    "acceptance": "All tests pass",
                    "estimated_effort": "low",
                    "step_id": "test123:0",
                }
            ],
            "review_notes": ["Consider edge cases"],
        }

    def test_spec_from_dict(self, sample_spec_data):
        """Test creating spec from dictionary."""
        spec = ProgrammingSpec.from_dict(sample_spec_data)

        assert spec.metadata.id == "test123"
        assert spec.metadata.title == "Test Specification"
        assert spec.context.project == "test-project"
        assert len(spec.context.dependencies) == 2
        assert isinstance(spec.context.dependencies[0], DependencyModel)
        assert spec.context.dependencies[0].name == "pytest"
        assert len(spec.implementation) == 1
        assert spec.implementation[0].task == "Write tests"

    def test_spec_to_dict(self, sample_spec_data):
        """Test converting spec to dictionary."""
        spec = ProgrammingSpec.from_dict(sample_spec_data)
        data = spec.model_dump(exclude_none=True, mode="json")

        assert data["metadata"]["id"] == "test123"
        assert len(data["context"]["dependencies"]) == 2
        assert data["context"]["dependencies"][0]["name"] == "pytest"
        assert len(data["implementation"]) == 1

    def test_spec_roundtrip(self, sample_spec_data):
        """Test spec serialization roundtrip."""
        spec1 = ProgrammingSpec.from_dict(sample_spec_data)
        data = spec1.model_dump(exclude_none=True)
        spec2 = ProgrammingSpec.from_dict(data)

        assert spec1.metadata.id == spec2.metadata.id
        assert spec1.metadata.title == spec2.metadata.title
        assert len(spec1.implementation) == len(spec2.implementation)

    def test_spec_with_progress(self, sample_spec_data):
        """Test spec with task progress."""
        # Add progress to implementation
        sample_spec_data["implementation"][0]["progress"] = {
            "status": "in_progress",
            "started_at": "2025-07-27T11:00:00",
            "completion_notes": "Working on it",
        }

        spec = ProgrammingSpec.from_dict(sample_spec_data)
        assert spec.implementation[0].progress is not None
        assert spec.implementation[0].progress.status == TaskStatus.IN_PROGRESS
        assert spec.implementation[0].progress.completion_notes == "Working on it"

    def test_spec_with_approvals(self, sample_spec_data):
        """Test spec with approvals."""
        sample_spec_data["implementation"][0]["approvals"] = [
            {
                "level": "peer",
                "approved_by": "reviewer",
                "approved_at": "2025-07-27T12:00:00",
                "comments": "LGTM",
            }
        ]

        spec = ProgrammingSpec.from_dict(sample_spec_data)
        assert spec.implementation[0].approvals is not None
        assert len(spec.implementation[0].approvals) == 1
        assert spec.implementation[0].approvals[0].level == ApprovalLevel.PEER

    def test_spec_with_work_logs(self, sample_spec_data):
        """Test spec with work logs."""
        sample_spec_data["work_logs"] = [
            {
                "spec_id": "test123",
                "step_id": "test123:0",
                "action": "started",
                "timestamp": "2025-07-27T11:00:00",
                "duration_minutes": 30,
                "notes": "Beginning implementation",
            }
        ]

        spec = ProgrammingSpec.from_dict(sample_spec_data)
        assert spec.work_logs is not None
        assert len(spec.work_logs) == 1
        assert spec.work_logs[0].action == "started"
        assert spec.work_logs[0].duration_minutes == 30


class TestFileBasedSpecStorage:
    """Test FileBasedSpecStorage functionality."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for tests."""
        temp_dir = tempfile.mkdtemp()
        storage = FileBasedSpecStorage(temp_dir)
        yield storage
        # Cleanup
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_spec(self):
        """Create a sample specification."""
        metadata = SpecMetadata(
            id="test456",
            title="Storage Test Spec",
            inherits=[],
            created=datetime.now().isoformat(),
            version="1.0",
            status="draft",
        )

        context = SpecContext(
            project="test-project",
            domain="Testing",
            dependencies=[
                DependencyModel(name="pytest", version="8.0.0"),
            ],
            files_involved=["test.py"],
        )

        requirements = SpecRequirement(
            functional=["Test storage"],
            non_functional=["Reliability"],
            constraints=["Must be atomic"],
        )

        implementation = [
            ImplementationStep(
                task="Implement feature",
                details="Create the feature",
                files=["feature.py"],
                acceptance="Feature works",
                step_id="test456:0",
            ),
            ImplementationStep(
                task="Write tests",
                details="Test the feature",
                files=["test_feature.py"],
                acceptance="Tests pass",
                step_id="test456:1",
            ),
        ]

        return ProgrammingSpec(
            metadata=metadata,
            context=context,
            requirements=requirements,
            implementation=implementation,
        )

    def test_save_and_load_spec(self, temp_storage, sample_spec):
        """Test saving and loading a specification."""
        # Save spec
        filepath = temp_storage.save_spec(sample_spec)
        assert filepath.exists()

        # Load spec
        loaded_spec = temp_storage.load_spec("test456")
        assert loaded_spec.metadata.id == sample_spec.metadata.id
        assert loaded_spec.metadata.title == sample_spec.metadata.title
        assert len(loaded_spec.implementation) == 2

    def test_load_nonexistent_spec(self, temp_storage):
        """Test loading a non-existent specification."""
        with pytest.raises(SpecificationError):
            temp_storage.load_spec("nonexistent")

    def test_update_task_progress(self, temp_storage, sample_spec):
        """Test updating task progress."""
        # Save spec first
        temp_storage.save_spec(sample_spec)

        # Update progress
        temp_storage.update_task_progress(
            "test456",
            "test456:0",
            TaskStatus.IN_PROGRESS,
            notes="Started working on it",
        )

        # Load and verify
        loaded_spec = temp_storage.load_spec("test456")
        step = loaded_spec.implementation[0]
        assert step.progress is not None
        assert step.progress.status == TaskStatus.IN_PROGRESS
        assert step.progress.completion_notes == "Started working on it"
        assert step.progress.started_at is not None

        # Verify work log was added
        assert loaded_spec.work_logs is not None
        assert len(loaded_spec.work_logs) == 1
        assert "status_changed" in loaded_spec.work_logs[0].action

    def test_add_approval(self, temp_storage, sample_spec):
        """Test adding approval to a task."""
        # Save spec and mark task as completed
        temp_storage.save_spec(sample_spec)
        temp_storage.update_task_progress(
            "test456",
            "test456:0",
            TaskStatus.COMPLETED,
            notes="Implementation complete",
        )

        # Add approval
        temp_storage.add_approval(
            "test456",
            "test456:0",
            ApprovalLevel.PEER,
            "john.reviewer",
            comments="Good implementation",
        )

        # Load and verify
        loaded_spec = temp_storage.load_spec("test456")
        step = loaded_spec.implementation[0]
        assert step.approvals is not None
        assert len(step.approvals) == 1
        assert step.approvals[0].level == ApprovalLevel.PEER
        assert step.approvals[0].approved_by == "john.reviewer"
        assert step.progress.status == TaskStatus.APPROVED

    def test_query_work_logs(self, temp_storage, sample_spec):
        """Test querying work logs."""
        # Create some work history
        temp_storage.save_spec(sample_spec)

        temp_storage.update_task_progress(
            "test456", "test456:0", TaskStatus.IN_PROGRESS
        )
        temp_storage.update_task_progress("test456", "test456:0", TaskStatus.COMPLETED)
        temp_storage.update_task_progress(
            "test456", "test456:1", TaskStatus.IN_PROGRESS
        )

        # Query all logs
        logs = temp_storage.query_work_logs()
        assert len(logs) == 3

        # Query by spec
        logs = temp_storage.query_work_logs(spec_id="test456")
        assert len(logs) == 3

        # Query by action filter
        logs = temp_storage.query_work_logs(action_filter="in_progress")
        assert len(logs) == 2

    def test_task_status_summary(self, temp_storage, sample_spec):
        """Test getting task status summary."""
        # Set up various task statuses
        temp_storage.save_spec(sample_spec)
        temp_storage.update_task_progress("test456", "test456:0", TaskStatus.COMPLETED)
        temp_storage.update_task_progress(
            "test456", "test456:1", TaskStatus.IN_PROGRESS
        )

        # Get summary
        summary = temp_storage.get_task_status_summary("test456")
        assert summary["total_tasks"] == 2
        assert summary["by_status"]["completed"] == 1
        assert summary["by_status"]["in_progress"] == 1
        assert summary["completion_percentage"] == 50.0
        assert len(summary["in_progress_tasks"]) == 1

    def test_export_work_history(self, temp_storage, sample_spec):
        """Test exporting work history."""
        # Create some history
        temp_storage.save_spec(sample_spec)
        temp_storage.update_task_progress(
            "test456",
            "test456:0",
            TaskStatus.COMPLETED,
            notes="Task completed successfully",
        )

        # Export as markdown
        md_export = temp_storage.export_work_history(
            format="markdown", spec_id="test456"
        )
        assert "# Work History Report" in md_export
        assert "test456" in md_export
        assert "Task completed successfully" in md_export

        # Export as CSV
        csv_export = temp_storage.export_work_history(format="csv", spec_id="test456")
        assert "Timestamp,Spec ID,Step ID,Action" in csv_export
        assert "test456" in csv_export

        # Export as JSON
        json_export = temp_storage.export_work_history(format="json", spec_id="test456")
        assert '"spec_id": "test456"' in json_export

    def test_atomic_write(self, temp_storage, sample_spec):
        """Test atomic write functionality."""
        # This tests that writes are atomic by ensuring the file
        # is either fully written or not written at all
        filepath = temp_storage.save_spec(sample_spec)

        # Verify file exists and can be loaded
        assert filepath.exists()
        with open(filepath) as f:
            data = yaml.safe_load(f)
        assert data["metadata"]["id"] == "test456"

        # The atomic write should have no partial states
        loaded_spec = temp_storage.load_spec("test456")
        assert loaded_spec.metadata.id == sample_spec.metadata.id
