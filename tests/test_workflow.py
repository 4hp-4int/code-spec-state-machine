"""Tests for task workflow management system."""

from datetime import datetime
import shutil
import tempfile

import pytest

from agentic_spec.db import FileBasedSpecStorage
from agentic_spec.models import (
    ApprovalLevel,
    ImplementationStep,
    ProgrammingSpec,
    SpecContext,
    SpecMetadata,
    SpecRequirement,
    TaskStatus,
)
from agentic_spec.workflow import TaskWorkflowManager, WorkflowViolationError


class TestTaskWorkflowManager:
    """Test TaskWorkflowManager functionality."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for tests."""
        temp_dir = tempfile.mkdtemp()
        storage = FileBasedSpecStorage(temp_dir)
        yield storage
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_spec(self):
        """Create a sample specification with multiple tasks."""
        metadata = SpecMetadata(
            id="workflow-test",
            title="Workflow Test Spec",
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
            functional=["Test workflow"],
            non_functional=["Reliability"],
            constraints=["Sequential execution"],
        )

        implementation = [
            ImplementationStep(
                task="First task",
                details="This is the first task",
                files=["task1.py"],
                acceptance="Task 1 complete",
                step_id="workflow-test:0",
            ),
            ImplementationStep(
                task="Second task",
                details="This is the second task",
                files=["task2.py"],
                acceptance="Task 2 complete",
                step_id="workflow-test:1",
            ),
            ImplementationStep(
                task="Third task",
                details="This is the third task",
                files=["task3.py"],
                acceptance="Task 3 complete",
                step_id="workflow-test:2",
            ),
        ]

        return ProgrammingSpec(
            metadata=metadata,
            context=context,
            requirements=requirements,
            implementation=implementation,
        )

    @pytest.fixture
    def workflow_manager(self, temp_storage):
        """Create a workflow manager with strict mode enabled."""
        return TaskWorkflowManager(temp_storage, strict_mode=True)

    def test_start_first_task(self, temp_storage, sample_spec, workflow_manager):
        """Test starting the first task in a specification."""
        # Save spec
        temp_storage.save_spec(sample_spec)

        # Start first task
        workflow_manager.start_task(
            "workflow-test", "workflow-test:0", "developer", "Starting first task"
        )

        # Verify task was started
        updated_spec = temp_storage.load_spec("workflow-test")
        first_task = updated_spec.implementation[0]

        assert first_task.progress is not None
        assert first_task.progress.status == TaskStatus.IN_PROGRESS
        assert first_task.progress.started_at is not None
        assert first_task.progress.completion_notes == "Starting first task"

        # Verify work log
        assert updated_spec.work_logs is not None
        assert len(updated_spec.work_logs) == 1
        assert updated_spec.work_logs[0].action == "task_started"

    def test_strict_mode_prevents_out_of_order(
        self, temp_storage, sample_spec, workflow_manager
    ):
        """Test that strict mode prevents starting tasks out of order."""
        # Save spec
        temp_storage.save_spec(sample_spec)

        # Try to start second task before first - should fail
        with pytest.raises(WorkflowViolationError) as exc_info:
            workflow_manager.start_task("workflow-test", "workflow-test:1", "developer")

        assert "previous step workflow-test:0 has not been started" in str(
            exc_info.value
        )
        assert exc_info.value.current_status == "pending"
        assert exc_info.value.attempted_action == "start"

    def test_complete_task_workflow(self, temp_storage, sample_spec, workflow_manager):
        """Test complete task workflow: start -> complete -> approve."""
        # Save spec
        temp_storage.save_spec(sample_spec)

        # Start task
        workflow_manager.start_task("workflow-test", "workflow-test:0", "developer")

        # Complete task
        workflow_manager.complete_task(
            "workflow-test",
            "workflow-test:0",
            "developer",
            "Task completed successfully",
        )

        # Verify completion
        updated_spec = temp_storage.load_spec("workflow-test")
        first_task = updated_spec.implementation[0]

        assert first_task.progress.status == TaskStatus.COMPLETED
        assert first_task.progress.completed_at is not None
        assert first_task.progress.time_spent_minutes is not None
        assert first_task.progress.completion_notes == "Task completed successfully"

        # Approve task
        workflow_manager.approve_task(
            "workflow-test",
            "workflow-test:0",
            ApprovalLevel.SELF,
            "developer",
            "Looks good",
        )

        # Verify approval
        updated_spec = temp_storage.load_spec("workflow-test")
        first_task = updated_spec.implementation[0]

        assert first_task.progress.status == TaskStatus.APPROVED
        assert first_task.approvals is not None
        assert len(first_task.approvals) == 1
        assert first_task.approvals[0].level == ApprovalLevel.SELF
        assert first_task.approvals[0].approved_by == "developer"
        assert first_task.approvals[0].comments == "Looks good"

    def test_sequential_task_execution(
        self, temp_storage, sample_spec, workflow_manager
    ):
        """Test that tasks can be executed sequentially after approval."""
        # Save spec
        temp_storage.save_spec(sample_spec)

        # Complete first task
        workflow_manager.start_task("workflow-test", "workflow-test:0", "dev1")
        workflow_manager.complete_task("workflow-test", "workflow-test:0", "dev1")
        workflow_manager.approve_task(
            "workflow-test", "workflow-test:0", ApprovalLevel.SELF, "dev1"
        )

        # Now second task should be startable
        workflow_manager.start_task("workflow-test", "workflow-test:1", "dev2")

        updated_spec = temp_storage.load_spec("workflow-test")
        second_task = updated_spec.implementation[1]
        assert second_task.progress.status == TaskStatus.IN_PROGRESS

    def test_reject_task_workflow(self, temp_storage, sample_spec, workflow_manager):
        """Test rejecting a task and requiring rework."""
        # Save spec
        temp_storage.save_spec(sample_spec)

        # Start and complete task
        workflow_manager.start_task("workflow-test", "workflow-test:0", "developer")
        workflow_manager.complete_task("workflow-test", "workflow-test:0", "developer")

        # Reject task
        workflow_manager.reject_task(
            "workflow-test", "workflow-test:0", "reviewer", "Code quality issues found"
        )

        # Verify rejection
        updated_spec = temp_storage.load_spec("workflow-test")
        first_task = updated_spec.implementation[0]

        assert first_task.progress.status == TaskStatus.REJECTED
        assert (
            "Rejected: Code quality issues found"
            in first_task.progress.completion_notes
        )
        assert not first_task.approvals  # Approvals should be cleared/empty

    def test_block_and_unblock_task(self, temp_storage, sample_spec, workflow_manager):
        """Test blocking and unblocking a task."""
        # Save spec
        temp_storage.save_spec(sample_spec)

        # Start task
        workflow_manager.start_task("workflow-test", "workflow-test:0", "developer")

        # Block task
        workflow_manager.block_task(
            "workflow-test",
            "workflow-test:0",
            "developer",
            ["Waiting for API access", "External dependency"],
            "Cannot proceed without access",
        )

        # Verify block
        updated_spec = temp_storage.load_spec("workflow-test")
        first_task = updated_spec.implementation[0]

        assert first_task.progress.status == TaskStatus.BLOCKED
        assert len(first_task.progress.blockers) == 2
        assert "Waiting for API access" in first_task.progress.blockers

        # Unblock task
        workflow_manager.unblock_task(
            "workflow-test",
            "workflow-test:0",
            "admin",
            "API access granted, dependency resolved",
        )

        # Verify unblock
        updated_spec = temp_storage.load_spec("workflow-test")
        first_task = updated_spec.implementation[0]

        assert first_task.progress.status == TaskStatus.PENDING
        assert first_task.progress.blockers == []
        assert "Unblocked: API access granted" in first_task.progress.completion_notes

    def test_strict_mode_override(self, temp_storage, sample_spec, workflow_manager):
        """Test overriding strict mode to start tasks out of order."""
        # Save spec
        temp_storage.save_spec(sample_spec)

        # Override strict mode to start second task
        workflow_manager.override_strict_mode(
            "workflow-test",
            "workflow-test:1",
            "admin",
            "Critical bug fix needed immediately",
        )

        # Verify task was started
        updated_spec = temp_storage.load_spec("workflow-test")
        second_task = updated_spec.implementation[1]

        assert second_task.progress.status == TaskStatus.IN_PROGRESS

        # Verify override was logged
        override_logs = [
            log
            for log in updated_spec.work_logs
            if log.action == "strict_mode_override"
        ]
        assert len(override_logs) == 1
        assert override_logs[0].metadata["override_by"] == "admin"
        assert "Critical bug fix" in override_logs[0].metadata["override_reason"]

    def test_multiple_approval_levels(self, temp_storage, sample_spec):
        """Test workflow with multiple approval levels required."""
        # Save spec
        temp_storage.save_spec(sample_spec)

        # Create workflow with multiple approval levels
        workflow = TaskWorkflowManager(
            temp_storage,
            strict_mode=True,
            required_approval_levels=[ApprovalLevel.SELF, ApprovalLevel.PEER],
        )

        # Complete task
        workflow.start_task("workflow-test", "workflow-test:0", "developer")
        workflow.complete_task("workflow-test", "workflow-test:0", "developer")

        # First approval (self)
        workflow.approve_task(
            "workflow-test",
            "workflow-test:0",
            ApprovalLevel.SELF,
            "developer",
            "I think it's good",
        )

        # Task should still be completed, not approved (needs peer approval)
        updated_spec = temp_storage.load_spec("workflow-test")
        first_task = updated_spec.implementation[0]
        assert first_task.progress.status == TaskStatus.COMPLETED

        # Second approval (peer)
        workflow.approve_task(
            "workflow-test",
            "workflow-test:0",
            ApprovalLevel.PEER,
            "reviewer",
            "Code looks good to me",
        )

        # Now task should be fully approved
        updated_spec = temp_storage.load_spec("workflow-test")
        first_task = updated_spec.implementation[0]
        assert first_task.progress.status == TaskStatus.APPROVED
        assert len(first_task.approvals) == 2

    def test_prevent_duplicate_approvals(
        self, temp_storage, sample_spec, workflow_manager
    ):
        """Test that duplicate approvals from the same level are prevented."""
        # Save spec and complete task
        temp_storage.save_spec(sample_spec)
        workflow_manager.start_task("workflow-test", "workflow-test:0", "developer")
        workflow_manager.complete_task("workflow-test", "workflow-test:0", "developer")

        # First approval
        workflow_manager.approve_task(
            "workflow-test", "workflow-test:0", ApprovalLevel.SELF, "developer"
        )

        # Second approval at same level should fail
        with pytest.raises(WorkflowViolationError) as exc_info:
            workflow_manager.approve_task(
                "workflow-test",
                "workflow-test:0",
                ApprovalLevel.SELF,
                "another_developer",
            )

        assert "already has self approval" in str(exc_info.value)

    def test_override_approval(self, temp_storage, sample_spec, workflow_manager):
        """Test approving a task with override reason."""
        # Save spec and start task (but don't complete)
        temp_storage.save_spec(sample_spec)
        workflow_manager.start_task("workflow-test", "workflow-test:0", "developer")

        # Approve with override
        workflow_manager.approve_task(
            "workflow-test",
            "workflow-test:0",
            ApprovalLevel.ADMIN,
            "admin",
            "Emergency deployment",
            override_reason="Critical production fix needed",
        )

        # Verify override approval
        updated_spec = temp_storage.load_spec("workflow-test")
        first_task = updated_spec.implementation[0]

        assert len(first_task.approvals) == 1
        approval = first_task.approvals[0]
        assert approval.level == ApprovalLevel.ADMIN
        assert approval.override_reason == "Critical production fix needed"

        # Verify override was logged
        override_logs = [
            log for log in updated_spec.work_logs if "override" in log.action
        ]
        assert len(override_logs) == 1

    def test_get_task_status(self, temp_storage, sample_spec, workflow_manager):
        """Test getting detailed task status information."""
        # Save spec
        temp_storage.save_spec(sample_spec)

        # Get status of pending task
        status = workflow_manager.get_task_status("workflow-test", "workflow-test:0")

        assert status["step_id"] == "workflow-test:0"
        assert status["task"] == "First task"
        assert status["status"] == "not_started"
        assert status["can_start"] is True
        assert status["can_complete"] is False
        assert status["can_approve"] is False

        # Start task and check status
        workflow_manager.start_task("workflow-test", "workflow-test:0", "developer")
        status = workflow_manager.get_task_status("workflow-test", "workflow-test:0")

        assert status["status"] == "in_progress"
        assert status["can_start"] is False
        assert status["can_complete"] is True
        assert status["started_at"] is not None

    def test_get_workflow_status(self, temp_storage, sample_spec, workflow_manager):
        """Test getting comprehensive workflow status."""
        # Save spec
        temp_storage.save_spec(sample_spec)

        # Get initial workflow status
        status = workflow_manager.get_workflow_status("workflow-test")

        assert status["spec_id"] == "workflow-test"
        assert status["total_tasks"] == 3
        assert status["completion_percentage"] == 0.0
        assert status["status_counts"]["pending"] == 3
        assert status["next_available_task"] == "workflow-test:0"
        assert status["strict_mode"] is True

        # Complete first task and check status
        workflow_manager.start_task("workflow-test", "workflow-test:0", "developer")
        workflow_manager.complete_task("workflow-test", "workflow-test:0", "developer")
        workflow_manager.approve_task(
            "workflow-test", "workflow-test:0", ApprovalLevel.SELF, "developer"
        )

        status = workflow_manager.get_workflow_status("workflow-test")
        assert status["completion_percentage"] == 33.3  # 1/3 * 100
        assert status["status_counts"]["approved"] == 1
        assert status["status_counts"]["pending"] == 2
        assert status["next_available_task"] == "workflow-test:1"

    def test_workflow_validation_errors(
        self, temp_storage, sample_spec, workflow_manager
    ):
        """Test various workflow validation scenarios."""
        # Save spec
        temp_storage.save_spec(sample_spec)

        # Try to complete task that hasn't been started
        with pytest.raises(WorkflowViolationError):
            workflow_manager.complete_task(
                "workflow-test", "workflow-test:0", "developer"
            )

        # Start task
        workflow_manager.start_task("workflow-test", "workflow-test:0", "developer")

        # Try to start already started task
        with pytest.raises(WorkflowViolationError):
            workflow_manager.start_task("workflow-test", "workflow-test:0", "developer")

        # Try to approve incomplete task
        with pytest.raises(WorkflowViolationError):
            workflow_manager.approve_task(
                "workflow-test", "workflow-test:0", ApprovalLevel.SELF, "developer"
            )

    def test_disabled_strict_mode(self, temp_storage, sample_spec):
        """Test that tasks can be started in any order when strict mode is disabled."""
        # Save spec
        temp_storage.save_spec(sample_spec)

        # Create workflow manager with strict mode disabled
        workflow = TaskWorkflowManager(temp_storage, strict_mode=False)

        # Should be able to start any task
        workflow.start_task(
            "workflow-test", "workflow-test:2", "developer"
        )  # Start third task

        updated_spec = temp_storage.load_spec("workflow-test")
        third_task = updated_spec.implementation[2]
        assert third_task.progress.status == TaskStatus.IN_PROGRESS

        # First task should still be startable
        workflow.start_task("workflow-test", "workflow-test:0", "developer")

        updated_spec = temp_storage.load_spec("workflow-test")
        first_task = updated_spec.implementation[0]
        assert first_task.progress.status == TaskStatus.IN_PROGRESS

    def test_work_log_creation(self, temp_storage, sample_spec, workflow_manager):
        """Test that work logs are properly created for all actions."""
        # Save spec
        temp_storage.save_spec(sample_spec)

        # Perform various actions
        workflow_manager.start_task(
            "workflow-test", "workflow-test:0", "developer", "Starting work"
        )
        workflow_manager.complete_task(
            "workflow-test", "workflow-test:0", "developer", "Work done"
        )
        workflow_manager.approve_task(
            "workflow-test",
            "workflow-test:0",
            ApprovalLevel.SELF,
            "developer",
            "Approved",
        )

        # Check work logs
        updated_spec = temp_storage.load_spec("workflow-test")
        assert len(updated_spec.work_logs) == 3

        actions = [log.action for log in updated_spec.work_logs]
        assert "task_started" in actions
        assert "task_completed" in actions
        assert "approved_self" in actions

        # Check metadata
        start_log = next(
            log for log in updated_spec.work_logs if log.action == "task_started"
        )
        assert start_log.metadata["started_by"] == "developer"
        assert "Starting work" in start_log.notes
