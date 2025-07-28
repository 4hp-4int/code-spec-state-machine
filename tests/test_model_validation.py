"""
Comprehensive validation tests for all Pydantic models.

Tests cover required fields, type validation, field constraints,
enum validation, and Pydantic v2 features after refactoring from dataclass.
"""

import pytest
from datetime import datetime, timedelta
from typing import Any

from pydantic import ValidationError

from agentic_spec.models import (
    # Enums
    TaskStatus,
    ApprovalLevel,
    SpecStatus,
    WorkflowStatus,
    # Models
    DependencyModel,
    SpecMetadata,
    SpecContext,
    SpecRequirement,
    TaskProgress,
    ApprovalRecord,
    ImplementationStep,
    ContextParameters,
    FeedbackData,
    WorkLogEntry,
    ProgrammingSpec,
    SpecificationDB,
    TaskDB,
    ApprovalDB,
    WorkLogDB,
)


class TestEnumValidation:
    """Test enum field validation."""

    def test_task_status_valid(self):
        """Test valid TaskStatus values."""
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.IN_PROGRESS == "in_progress"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.BLOCKED == "blocked"

    def test_approval_level_valid(self):
        """Test valid ApprovalLevel values."""
        assert ApprovalLevel.SELF == "self"
        assert ApprovalLevel.PEER == "peer"
        assert ApprovalLevel.AI == "ai"
        assert ApprovalLevel.ADMIN == "admin"

    def test_spec_status_valid(self):
        """Test valid SpecStatus values."""
        assert SpecStatus.DRAFT == "draft"
        assert SpecStatus.REVIEWED == "reviewed"
        assert SpecStatus.APPROVED == "approved"
        assert SpecStatus.IMPLEMENTED == "implemented"

    def test_workflow_status_valid(self):
        """Test valid WorkflowStatus values."""
        assert WorkflowStatus.CREATED == "created"
        assert WorkflowStatus.IN_PROGRESS == "in_progress"
        assert WorkflowStatus.READY_FOR_REVIEW == "ready_for_review"
        assert WorkflowStatus.COMPLETED == "completed"


class TestDependencyModel:
    """Test DependencyModel validation."""

    def test_valid_minimal(self):
        """Test creating with only required fields."""
        dep = DependencyModel(name="pytest")
        assert dep.name == "pytest"
        assert dep.version is None
        assert dep.description is None

    def test_valid_complete(self):
        """Test creating with all fields."""
        dep = DependencyModel(
            name="pytest",
            version=">=7.0.0",
            description="Testing framework"
        )
        assert dep.name == "pytest"
        assert dep.version == ">=7.0.0"
        assert dep.description == "Testing framework"

    def test_missing_required_name(self):
        """Test validation error for missing name."""
        with pytest.raises(ValidationError) as exc_info:
            DependencyModel()
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("name",)
        assert errors[0]["type"] == "missing"

    def test_invalid_type_name(self):
        """Test type validation for name field."""
        with pytest.raises(ValidationError) as exc_info:
            DependencyModel(name=123)
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("name",) for error in errors)

    def test_extra_fields_allowed(self):
        """Test that extra fields are allowed."""
        dep = DependencyModel(
            name="pytest",
            extra_field="extra_value",
            another_extra=123
        )
        assert dep.name == "pytest"
        # Extra fields should be accessible
        assert hasattr(dep, "extra_field")


class TestSpecMetadata:
    """Test SpecMetadata validation."""

    def test_valid_minimal(self):
        """Test creating with only required fields."""
        metadata = SpecMetadata(
            id="test123",
            title="Test Spec",
            created=datetime.now().isoformat(),
            version="1.0"
        )
        assert metadata.id == "test123"
        assert metadata.title == "Test Spec"
        assert metadata.parent_spec_id is None
        assert metadata.author is None

    def test_valid_complete(self):
        """Test creating with all fields."""
        now = datetime.now().isoformat()
        metadata = SpecMetadata(
            id="test123",
            title="Test Spec",
            inherits=["base", "web-api"],
            created=now,
            version="1.0",
            status="approved",
            parent_spec_id="parent123",
            child_spec_ids=["child1", "child2"],
            author="test_user",
            last_modified=now
        )
        assert metadata.id == "test123"
        assert len(metadata.inherits) == 2
        assert metadata.author == "test_user"

    def test_missing_required_fields(self):
        """Test validation errors for missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            SpecMetadata(id="test123")  # Missing title, inherits, etc.
        
        errors = exc_info.value.errors()
        required_fields = {"title", "created", "version"}
        missing_fields = {error["loc"][0] for error in errors if error["type"] == "missing"}
        assert required_fields.issubset(missing_fields)

    def test_status_as_string(self):
        """Test status field accepts string values."""
        metadata = SpecMetadata(
            id="test123",
            title="Test",
            created=datetime.now().isoformat(),
            version="1.0",
            status="custom_status"
        )
        assert metadata.status == "custom_status"

    def test_datetime_serialization(self):
        """Test datetime field serialization."""
        now = datetime.now().isoformat()
        metadata = SpecMetadata(
            id="test123",
            title="Test",
            created=now,
            version="1.0"
        )
        
        # Test model_dump with json mode
        data = metadata.model_dump(mode='json')
        assert isinstance(data["created"], str)  # created field as string
        assert data["status"] == "draft"  # default status value


class TestTaskProgress:
    """Test TaskProgress validation."""

    def test_valid_minimal(self):
        """Test creating with defaults."""
        progress = TaskProgress()
        assert progress.status == TaskStatus.PENDING
        assert progress.started_at is None
        assert progress.completion_notes is None

    def test_valid_complete(self):
        """Test creating with all fields."""
        now = datetime.now()
        progress = TaskProgress(
            status=TaskStatus.COMPLETED,
            started_at=now - timedelta(hours=2),
            completed_at=now,
            time_spent_minutes=120,
            completion_notes="Task completed successfully",
            blockers=["Dependency issue resolved"]
        )
        assert progress.status == TaskStatus.COMPLETED
        assert progress.time_spent_minutes == 120
        assert progress.completion_notes == "Task completed successfully"

    def test_invalid_time_spent(self):
        """Test time_spent_minutes field constraints (>= 0)."""
        # Test negative time
        with pytest.raises(ValidationError) as exc_info:
            TaskProgress(time_spent_minutes=-10)
        
        errors = exc_info.value.errors()
        assert any("time_spent_minutes" in error["loc"] for error in errors)
        
        # Test valid time
        progress = TaskProgress(time_spent_minutes=0)
        assert progress.time_spent_minutes == 0

    def test_blockers_list(self):
        """Test blockers field validation."""
        # Test with valid blockers
        progress = TaskProgress(blockers=["API unavailable", "Need approval"])
        assert len(progress.blockers) == 2
        
        # Test with empty list
        progress = TaskProgress(blockers=[])
        assert progress.blockers == []
        
        # Test with None (default)
        progress = TaskProgress()
        assert progress.blockers is None

    def test_invalid_status_enum(self):
        """Test invalid enum value for status."""
        with pytest.raises(ValidationError) as exc_info:
            TaskProgress(status="invalid_status")
        
        errors = exc_info.value.errors()
        assert any("status" in error["loc"] for error in errors)


class TestFeedbackData:
    """Test FeedbackData validation including rating constraints."""

    def test_valid_minimal(self):
        """Test creating with defaults."""
        feedback = FeedbackData()
        assert feedback.rating is None
        assert feedback.accuracy_score is None
        assert feedback.relevance_score is None

    def test_valid_complete(self):
        """Test creating with all fields."""
        feedback = FeedbackData(
            rating=5,
            accuracy_score=4,
            relevance_score=5,
            comments="Excellent work",
            suggested_improvements="Consider edge cases",
            timestamp="2023-01-01T12:00:00"
        )
        assert feedback.rating == 5
        assert feedback.accuracy_score == 4
        assert feedback.relevance_score == 5

    def test_invalid_rating_range(self):
        """Test rating field constraints (1-5)."""
        # Test rating > 5
        with pytest.raises(ValidationError) as exc_info:
            FeedbackData(rating=6)
        
        errors = exc_info.value.errors()
        assert any("rating" in error["loc"] for error in errors)
        
        # Test rating < 1
        with pytest.raises(ValidationError) as exc_info:
            FeedbackData(rating=0)
        
        errors = exc_info.value.errors()
        assert any("rating" in error["loc"] for error in errors)

    def test_invalid_score_ranges(self):
        """Test accuracy_score and relevance_score constraints (1-5)."""
        # Test accuracy_score > 5
        with pytest.raises(ValidationError):
            FeedbackData(accuracy_score=6)
        
        # Test relevance_score < 1
        with pytest.raises(ValidationError):
            FeedbackData(relevance_score=0)

    @pytest.mark.parametrize("rating", [1, 2, 3, 4, 5])
    def test_rating_boundary_values(self, rating):
        """Test valid rating boundary values."""
        feedback = FeedbackData(rating=rating)
        assert feedback.rating == rating

    @pytest.mark.parametrize("rating", [0, 6, -1, 10])
    def test_rating_invalid_values(self, rating):
        """Test invalid rating values."""
        with pytest.raises(ValidationError):
            FeedbackData(rating=rating)


class TestWorkLogEntry:
    """Test WorkLogEntry validation."""

    def test_valid_minimal(self):
        """Test creating with only required fields."""
        log = WorkLogEntry(
            spec_id="spec123",
            step_id="step001",
            action="started",
            timestamp=datetime.now()
        )
        assert log.spec_id == "spec123"
        assert log.duration_minutes is None
        assert log.notes is None

    def test_valid_complete(self):
        """Test creating with all fields."""
        log = WorkLogEntry(
            spec_id="spec123",
            step_id="step001",
            action="completed",
            timestamp=datetime.now(),
            duration_minutes=60,
            notes="Task completed successfully",
            metadata={"priority": "high"}
        )
        assert log.duration_minutes == 60
        assert log.notes == "Task completed successfully"
        assert log.metadata["priority"] == "high"

    def test_missing_required_fields(self):
        """Test validation errors for missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            WorkLogEntry(spec_id="spec123")  # Missing step_id, action, timestamp
        
        errors = exc_info.value.errors()
        required_fields = {"step_id", "action", "timestamp"}
        missing_fields = {error["loc"][0] for error in errors if error["type"] == "missing"}
        assert required_fields.issubset(missing_fields)

    def test_negative_duration(self):
        """Test duration_minutes must be >= 0."""
        with pytest.raises(ValidationError) as exc_info:
            WorkLogEntry(
                spec_id="spec123",
                step_id="step001",
                action="completed",
                timestamp=datetime.now(),
                duration_minutes=-30
            )
        
        errors = exc_info.value.errors()
        assert any("duration_minutes" in error["loc"] for error in errors)


class TestApprovalRecord:
    """Test ApprovalRecord validation."""

    def test_valid_minimal(self):
        """Test creating with only required fields."""
        approval = ApprovalRecord(
            level=ApprovalLevel.PEER,
            approved_by="reviewer",
            approved_at=datetime.now()
        )
        assert approval.level == ApprovalLevel.PEER
        assert approval.comments is None
        assert approval.override_reason is None

    def test_valid_complete(self):
        """Test creating with all fields."""
        approval = ApprovalRecord(
            level=ApprovalLevel.ADMIN,
            approved_by="admin_user",
            approved_at=datetime.now(),
            comments="Approved with minor suggestions",
            override_reason="Urgent deadline"
        )
        assert approval.override_reason == "Urgent deadline"

    def test_missing_required_fields(self):
        """Test validation errors for missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            ApprovalRecord(level=ApprovalLevel.PEER)
        
        errors = exc_info.value.errors()
        required_fields = {"approved_by", "approved_at"}
        missing_fields = {error["loc"][0] for error in errors if error["type"] == "missing"}
        assert required_fields.issubset(missing_fields)

    def test_invalid_approval_level(self):
        """Test invalid enum value for approval level."""
        with pytest.raises(ValidationError) as exc_info:
            ApprovalRecord(
                level="invalid_level",
                approved_by="user",
                approved_at=datetime.now()
            )
        
        errors = exc_info.value.errors()
        assert any("level" in error["loc"] for error in errors)


class TestImplementationStep:
    """Test ImplementationStep validation."""

    def test_valid_minimal(self):
        """Test creating with only required fields."""
        step = ImplementationStep(
            task="Implement feature",
            details="Detailed implementation steps",
            acceptance="Tests pass"
        )
        assert step.task == "Implement feature"
        assert step.details == "Detailed implementation steps"
        assert step.files == []
        assert step.progress is None

    def test_valid_complete(self):
        """Test creating with all fields including nested objects."""
        progress = TaskProgress(status=TaskStatus.IN_PROGRESS)
        approval = ApprovalRecord(
            level=ApprovalLevel.PEER,
            approved_by="reviewer",
            approved_at=datetime.now()
        )
        
        step = ImplementationStep(
            task="Implement feature",
            details="Detailed implementation plan",
            files=["src/feature.py", "tests/test_feature.py"],
            acceptance="All tests pass and code reviewed",
            estimated_effort="medium",
            step_id="step_001",
            sub_spec_id="sub_spec_123",
            decomposition_hint="atomic",
            progress=progress,
            approvals=[approval]
        )
        assert step.progress.status == TaskStatus.IN_PROGRESS
        assert len(step.approvals) == 1
        assert step.approvals[0].level == ApprovalLevel.PEER

    def test_missing_required_task(self):
        """Test validation error for missing task."""
        with pytest.raises(ValidationError) as exc_info:
            ImplementationStep(acceptance="Tests pass")
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("task",) for error in errors)

    def test_nested_validation(self):
        """Test validation of nested objects."""
        # Invalid TaskProgress
        with pytest.raises(ValidationError) as exc_info:
            ImplementationStep(
                task="Task",
                acceptance="Accept",
                progress={"status": "invalid_status"}
            )
        
        errors = exc_info.value.errors()
        assert any("progress" in error["loc"] and "status" in error["loc"] for error in errors)


class TestProgrammingSpec:
    """Test ProgrammingSpec validation (complex nested model)."""

    @pytest.fixture
    def valid_metadata(self):
        """Create valid metadata for tests."""
        return SpecMetadata(
            id="spec123",
            title="Test Specification",
            created=datetime.now().isoformat(),
            version="1.0"
        )

    @pytest.fixture
    def valid_context(self):
        """Create valid context for tests."""
        return SpecContext(
            project="test_project",
            domain="testing",
            dependencies=[
                DependencyModel(name="pytest", version=">=7.0")
            ],
            affected_files=["test.py"]
        )

    @pytest.fixture
    def valid_requirements(self):
        """Create valid requirements for tests."""
        return SpecRequirement(
            functional=["Feature must work"],
            non_functional=["Must be fast"],
            constraints=["Python 3.8+"]
        )

    def test_valid_minimal(self, valid_metadata, valid_context, valid_requirements):
        """Test creating with only required fields."""
        spec = ProgrammingSpec(
            metadata=valid_metadata,
            context=valid_context,
            requirements=valid_requirements,
            implementation=[]
        )
        assert spec.metadata.id == "spec123"
        assert spec.review_notes is None
        assert spec.work_logs is None

    def test_valid_complete(self, valid_metadata, valid_context, valid_requirements):
        """Test creating with all fields populated."""
        step = ImplementationStep(
            task="Implement",
            details="Implementation details",
            acceptance="Done",
            progress=TaskProgress(status=TaskStatus.COMPLETED)
        )
        
        spec = ProgrammingSpec(
            metadata=valid_metadata,
            context=valid_context,
            requirements=valid_requirements,
            implementation=[step],
            review_notes=["Consider performance"],
            context_parameters=ContextParameters(),
            feedback_history=[
                FeedbackData(
                    rating=5,
                    comments="Good approach"
                )
            ],
            work_logs=[
                WorkLogEntry(
                    spec_id="spec123",
                    step_id="step001",
                    action="Started implementation",
                    timestamp=datetime.now(),
                    notes="Beginning work on feature"
                )
            ]
        )
        assert len(spec.implementation) == 1
        assert len(spec.feedback_history) == 1
        assert len(spec.work_logs) == 1

    def test_model_dump_json_mode(self, valid_metadata, valid_context, valid_requirements):
        """Test model_dump with json mode for enum serialization."""
        spec = ProgrammingSpec(
            metadata=valid_metadata,
            context=valid_context,
            requirements=valid_requirements,
            implementation=[]
        )
        
        # Dump with json mode
        data = spec.model_dump(mode='json', exclude_none=True)
        
        # Check enums are serialized as strings
        assert data["metadata"]["status"] == "draft"
        assert isinstance(data["metadata"]["created"], str)
        
        # Check nested objects are properly serialized
        assert data["context"]["dependencies"][0]["name"] == "pytest"

    def test_nested_validation_errors(self, valid_context, valid_requirements):
        """Test validation errors in nested objects."""
        # Invalid metadata
        with pytest.raises(ValidationError) as exc_info:
            ProgrammingSpec(
                metadata={"id": "test"},  # Missing required fields
                context=valid_context,
                requirements=valid_requirements,
                implementation=[]
            )
        
        errors = exc_info.value.errors()
        assert any("metadata" in error["loc"] for error in errors)


class TestDatabaseModels:
    """Test database model validation."""

    def test_specification_db_valid(self):
        """Test valid SpecificationDB creation."""
        now = datetime.now()
        spec_db = SpecificationDB(
            id="spec123",
            title="Test Spec",
            created=now,
            updated=now,
            version="1.0",
            status=SpecStatus.DRAFT
        )
        assert spec_db.id == "spec123"
        assert spec_db.status == SpecStatus.DRAFT
        assert spec_db.workflow_status == WorkflowStatus.CREATED

    def test_task_db_valid(self):
        """Test valid TaskDB creation."""
        task_db = TaskDB(
            id="task001",
            spec_id="spec123",
            step_index=0,
            task="Implement feature",
            details="Detailed implementation plan",
            files=["src/feature.py"],
            acceptance="Feature works correctly",
            estimated_effort="medium"
        )
        assert task_db.id == "task001"
        assert task_db.status == TaskStatus.PENDING
        assert task_db.time_spent_minutes is None

    def test_task_db_time_constraint(self):
        """Test time_spent_minutes constraint."""
        with pytest.raises(ValidationError) as exc_info:
            TaskDB(
                id="task001",
                spec_id="spec123",
                step_index=0,
                task="Task",
                details="Details",
                files=["file.py"],
                acceptance="Done",
                estimated_effort="low",
                time_spent_minutes=-30
            )
        
        errors = exc_info.value.errors()
        assert any("time_spent_minutes" in error["loc"] for error in errors)


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_string_vs_none(self):
        """Test behavior with empty strings vs None."""
        # Required string field with empty string
        dep = DependencyModel(name="")
        assert dep.name == ""  # Empty string is valid
        
        # Optional string field with empty string
        dep = DependencyModel(name="test", version="")
        assert dep.version == ""  # Empty string is valid

    def test_mixed_dependency_types(self):
        """Test that dependencies accept both dict and DependencyModel objects."""
        # This is expected behavior - dependencies can be mixed types
        context = SpecContext(
            project="test",
            domain="test",
            dependencies=[
                {"name": "valid_dict"},
                DependencyModel(name="valid_model", version="1.0")
            ],
            affected_files=[]
        )
        assert len(context.dependencies) == 2
        assert context.dependencies[0] == {"name": "valid_dict"}
        assert isinstance(context.dependencies[1], DependencyModel)

    def test_datetime_string_parsing(self):
        """Test datetime parsing from strings."""
        data = {
            "level": "peer",
            "approved_by": "user",
            "approved_at": "2023-01-01T12:00:00"
        }
        approval = ApprovalRecord(**data)
        assert isinstance(approval.approved_at, datetime)

    def test_model_validate_round_trip(self):
        """Test model_validate for round-trip serialization."""
        progress = TaskProgress(
            status=TaskStatus.IN_PROGRESS,
            rating=4,
            time_spent_minutes=60
        )
        
        # Serialize and deserialize
        data = progress.model_dump()
        progress2 = TaskProgress.model_validate(data)
        
        assert progress2.status == progress.status
        assert progress2.rating == progress.rating
        assert progress2.time_spent_minutes == progress.time_spent_minutes

    @pytest.mark.parametrize("time_minutes", [0, 1, 60, 480, 1440])
    def test_time_spent_boundary_values(self, time_minutes):
        """Test valid time_spent_minutes boundary values."""
        progress = TaskProgress(time_spent_minutes=time_minutes)
        assert progress.time_spent_minutes == time_minutes

    @pytest.mark.parametrize("time_minutes", [-1, -10, -100])
    def test_time_spent_invalid_values(self, time_minutes):
        """Test invalid time_spent_minutes values."""
        with pytest.raises(ValidationError):
            TaskProgress(time_spent_minutes=time_minutes)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])