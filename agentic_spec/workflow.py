"""Task workflow management with strict mode enforcement and approval tracking."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .db import FileBasedSpecStorage
from .exceptions import SpecificationError, ValidationError
from .models import (
    ApprovalLevel,
    ApprovalRecord,
    ImplementationStep,
    ProgrammingSpec,
    TaskProgress,
    TaskStatus,
    WorkLogEntry,
)


class WorkflowViolationError(ValidationError):
    """Exception raised when workflow rules are violated."""

    def __init__(self, message: str, current_status: str, attempted_action: str):
        self.current_status = current_status
        self.attempted_action = attempted_action
        super().__init__(message)


class TaskWorkflowManager:
    """Manages task workflow with strict mode enforcement and approval tracking."""

    def __init__(
        self,
        storage: FileBasedSpecStorage,
        strict_mode: bool = True,
        required_approval_levels: list[ApprovalLevel] | None = None,
    ):
        self.storage = storage
        self.strict_mode = strict_mode
        self.required_approval_levels = required_approval_levels or [ApprovalLevel.SELF]

    def start_task(
        self,
        spec_id: str,
        step_id: str,
        started_by: str,
        notes: str | None = None,
    ) -> None:
        """Start a task, enforcing strict mode if enabled."""
        spec = self.storage.load_spec(spec_id)
        step = self._find_step(spec, step_id)

        # Check if we can start this task in strict mode
        if self.strict_mode:
            self._enforce_sequential_execution(spec, step)

        # Initialize or update progress
        if not step.progress:
            step.progress = TaskProgress()

        if step.progress.status not in (TaskStatus.PENDING, TaskStatus.BLOCKED):
            raise WorkflowViolationError(
                f"Cannot start task with status {step.progress.status.value}",
                step.progress.status.value,
                "start",
            )

        # Update task status
        step.progress.status = TaskStatus.IN_PROGRESS
        step.progress.started_at = datetime.now()
        if notes:
            step.progress.completion_notes = notes

        # Add work log entry
        self._add_work_log(
            spec,
            step_id,
            "task_started",
            notes=f"Task started by {started_by}" + (f": {notes}" if notes else ""),
            metadata={"started_by": started_by},
        )

        # Save updated spec
        self.storage.save_spec(spec)

    def complete_task(
        self,
        spec_id: str,
        step_id: str,
        completed_by: str,
        completion_notes: str | None = None,
    ) -> None:
        """Mark a task as completed."""
        spec = self.storage.load_spec(spec_id)
        step = self._find_step(spec, step_id)

        if not step.progress:
            raise WorkflowViolationError(
                "Cannot complete task that has not been started",
                "not_started",
                "complete",
            )

        if step.progress.status != TaskStatus.IN_PROGRESS:
            raise WorkflowViolationError(
                f"Cannot complete task with status {step.progress.status.value}",
                step.progress.status.value,
                "complete",
            )

        # Update task status
        step.progress.status = TaskStatus.COMPLETED
        step.progress.completed_at = datetime.now()
        if completion_notes:
            step.progress.completion_notes = completion_notes

        # Calculate time spent
        if step.progress.started_at:
            duration = (
                step.progress.completed_at - step.progress.started_at
            ).total_seconds() / 60
            step.progress.time_spent_minutes = int(duration)

        # Add work log entry
        self._add_work_log(
            spec,
            step_id,
            "task_completed",
            duration_minutes=step.progress.time_spent_minutes,
            notes=f"Task completed by {completed_by}"
            + (f": {completion_notes}" if completion_notes else ""),
            metadata={"completed_by": completed_by},
        )

        # Save updated spec
        self.storage.save_spec(spec)

    def approve_task(
        self,
        spec_id: str,
        step_id: str,
        approval_level: ApprovalLevel,
        approved_by: str,
        comments: str | None = None,
        override_reason: str | None = None,
    ) -> None:
        """Approve a completed task."""
        spec = self.storage.load_spec(spec_id)
        step = self._find_step(spec, step_id)

        if not step.progress:
            raise WorkflowViolationError(
                "Cannot approve task that has not been started",
                "not_started",
                "approve",
            )

        # Allow approval of completed tasks, or override with reason
        if step.progress.status not in (TaskStatus.COMPLETED, TaskStatus.APPROVED):
            if not override_reason:
                raise WorkflowViolationError(
                    f"Cannot approve task with status {step.progress.status.value} without override reason",
                    step.progress.status.value,
                    "approve",
                )

        # Initialize approvals list if needed
        if not step.approvals:
            step.approvals = []

        # Check if this approval level already exists (prevent duplicate approvals)
        existing_approval = next(
            (a for a in step.approvals if a.level == approval_level),
            None,
        )
        if existing_approval:
            raise WorkflowViolationError(
                f"Task already has {approval_level.value} approval from {existing_approval.approved_by}",
                step.progress.status.value,
                "approve",
            )

        # Create approval record
        approval = ApprovalRecord(
            level=approval_level,
            approved_by=approved_by,
            approved_at=datetime.now(),
            comments=comments,
            override_reason=override_reason,
        )
        step.approvals.append(approval)

        # Check if all required approvals are present
        if self._has_all_required_approvals(step):
            step.progress.status = TaskStatus.APPROVED

        # Add work log entry
        action = f"approved_{approval_level.value}"
        if override_reason:
            action += "_override"

        self._add_work_log(
            spec,
            step_id,
            action,
            notes=f"Approved by {approved_by} ({approval_level.value})"
            + (f": {comments}" if comments else "")
            + (f" [Override: {override_reason}]" if override_reason else ""),
            metadata={
                "approved_by": approved_by,
                "approval_level": approval_level.value,
                "override": bool(override_reason),
                "override_reason": override_reason,
            },
        )

        # Save updated spec
        self.storage.save_spec(spec)

    def reject_task(
        self,
        spec_id: str,
        step_id: str,
        rejected_by: str,
        rejection_reason: str,
    ) -> None:
        """Reject a task, requiring it to be reworked."""
        spec = self.storage.load_spec(spec_id)
        step = self._find_step(spec, step_id)

        if not step.progress:
            raise WorkflowViolationError(
                "Cannot reject task that has not been started",
                "not_started",
                "reject",
            )

        if step.progress.status not in (TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS):
            raise WorkflowViolationError(
                f"Cannot reject task with status {step.progress.status.value}",
                step.progress.status.value,
                "reject",
            )

        # Update task status
        step.progress.status = TaskStatus.REJECTED
        step.progress.completion_notes = f"Rejected: {rejection_reason}"

        # Clear any existing approvals
        if step.approvals:
            step.approvals = []

        # Add work log entry
        self._add_work_log(
            spec,
            step_id,
            "task_rejected",
            notes=f"Task rejected by {rejected_by}: {rejection_reason}",
            metadata={"rejected_by": rejected_by, "rejection_reason": rejection_reason},
        )

        # Save updated spec
        self.storage.save_spec(spec)

    def block_task(
        self,
        spec_id: str,
        step_id: str,
        blocked_by: str,
        blockers: list[str],
        notes: str | None = None,
    ) -> None:
        """Block a task due to external dependencies or issues."""
        spec = self.storage.load_spec(spec_id)
        step = self._find_step(spec, step_id)

        if not step.progress:
            step.progress = TaskProgress()

        # Update task status
        step.progress.status = TaskStatus.BLOCKED
        step.progress.blockers = blockers
        if notes:
            step.progress.completion_notes = notes

        # Add work log entry
        self._add_work_log(
            spec,
            step_id,
            "task_blocked",
            notes=f"Task blocked by {blocked_by}: {', '.join(blockers)}"
            + (f" - {notes}" if notes else ""),
            metadata={"blocked_by": blocked_by, "blockers": blockers},
        )

        # Save updated spec
        self.storage.save_spec(spec)

    def unblock_task(
        self,
        spec_id: str,
        step_id: str,
        unblocked_by: str,
        resolution_notes: str,
    ) -> None:
        """Unblock a task and return it to pending status."""
        spec = self.storage.load_spec(spec_id)
        step = self._find_step(spec, step_id)

        if not step.progress or step.progress.status != TaskStatus.BLOCKED:
            raise WorkflowViolationError(
                f"Cannot unblock task with status {step.progress.status.value if step.progress else 'not_started'}",
                step.progress.status.value if step.progress else "not_started",
                "unblock",
            )

        # Update task status
        step.progress.status = TaskStatus.PENDING
        step.progress.blockers = []
        step.progress.completion_notes = f"Unblocked: {resolution_notes}"

        # Add work log entry
        self._add_work_log(
            spec,
            step_id,
            "task_unblocked",
            notes=f"Task unblocked by {unblocked_by}: {resolution_notes}",
            metadata={"unblocked_by": unblocked_by, "resolution": resolution_notes},
        )

        # Save updated spec
        self.storage.save_spec(spec)

    def override_strict_mode(
        self,
        spec_id: str,
        step_id: str,
        override_by: str,
        override_reason: str,
    ) -> None:
        """Override strict mode to allow starting a task out of sequence."""
        if not self.strict_mode:
            raise WorkflowViolationError(
                "Cannot override strict mode when it is not enabled",
                "strict_mode_disabled",
                "override",
            )

        spec = self.storage.load_spec(spec_id)
        step = self._find_step(spec, step_id)

        # Add work log entry for the override
        self._add_work_log(
            spec,
            step_id,
            "strict_mode_override",
            notes=f"Strict mode overridden by {override_by}: {override_reason}",
            metadata={
                "override_by": override_by,
                "override_reason": override_reason,
                "override_timestamp": datetime.now().isoformat(),
            },
        )

        # Save the override log
        self.storage.save_spec(spec)

        # Temporarily disable strict mode for this operation
        original_strict_mode = self.strict_mode
        try:
            self.strict_mode = False
            # Allow starting the task
            self.start_task(
                spec_id, step_id, override_by, f"Override: {override_reason}"
            )
        finally:
            self.strict_mode = original_strict_mode

    def get_task_status(self, spec_id: str, step_id: str) -> dict[str, Any]:
        """Get comprehensive status information for a task."""
        spec = self.storage.load_spec(spec_id)
        step = self._find_step(spec, step_id)

        result = {
            "step_id": step_id,
            "task": step.task,
            "status": step.progress.status.value if step.progress else "not_started",
            "can_start": self._can_start_task(spec, step),
            "can_complete": self._can_complete_task(step),
            "can_approve": self._can_approve_task(step),
            "estimated_effort": step.estimated_effort,
            "files": step.files,
        }

        if step.progress:
            result.update(
                {
                    "started_at": step.progress.started_at.isoformat()
                    if step.progress.started_at
                    else None,
                    "completed_at": step.progress.completed_at.isoformat()
                    if step.progress.completed_at
                    else None,
                    "time_spent_minutes": step.progress.time_spent_minutes,
                    "completion_notes": step.progress.completion_notes,
                    "blockers": step.progress.blockers,
                }
            )

        if step.approvals:
            result["approvals"] = [
                {
                    "level": approval.level.value,
                    "approved_by": approval.approved_by,
                    "approved_at": approval.approved_at.isoformat(),
                    "comments": approval.comments,
                    "override_reason": approval.override_reason,
                }
                for approval in step.approvals
            ]

        return result

    def get_workflow_status(self, spec_id: str) -> dict[str, Any]:
        """Get comprehensive workflow status for an entire specification."""
        spec = self.storage.load_spec(spec_id)

        total_tasks = len(spec.implementation)
        status_counts = {
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "approved": 0,
            "rejected": 0,
            "blocked": 0,
        }

        task_details = []
        next_available_task = None

        for i, step in enumerate(spec.implementation):
            status = step.progress.status.value if step.progress else "pending"
            status_counts[status] += 1

            task_info = {
                "step_index": i,
                "step_id": step.step_id,
                "task": step.task,
                "status": status,
                "can_start": self._can_start_task(spec, step),
            }

            if step.progress:
                task_info["time_spent_minutes"] = step.progress.time_spent_minutes
                task_info["blockers"] = step.progress.blockers

            task_details.append(task_info)

            # Find next available task
            if next_available_task is None and self._can_start_task(spec, step):
                next_available_task = step.step_id

        # Calculate completion percentage
        completed_tasks = status_counts["completed"] + status_counts["approved"]
        completion_percentage = (
            (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        )

        return {
            "spec_id": spec_id,
            "spec_title": spec.metadata.title,
            "total_tasks": total_tasks,
            "status_counts": status_counts,
            "completion_percentage": round(completion_percentage, 1),
            "next_available_task": next_available_task,
            "strict_mode": self.strict_mode,
            "required_approval_levels": [
                level.value for level in self.required_approval_levels
            ],
            "tasks": task_details,
        }

    def _find_step(self, spec: ProgrammingSpec, step_id: str) -> ImplementationStep:
        """Find a step by its ID."""
        for step in spec.implementation:
            if step.step_id == step_id:
                return step
        raise SpecificationError(
            f"Step {step_id} not found in specification {spec.metadata.id}"
        )

    def _enforce_sequential_execution(
        self, spec: ProgrammingSpec, current_step: ImplementationStep
    ) -> None:
        """Enforce that tasks are executed in sequence."""
        current_index = None
        for i, step in enumerate(spec.implementation):
            if step.step_id == current_step.step_id:
                current_index = i
                break

        if current_index is None:
            return  # Step not found, let other validation handle this

        # Check if previous tasks are completed/approved
        for i in range(current_index):
            prev_step = spec.implementation[i]
            if not prev_step.progress:
                raise WorkflowViolationError(
                    f"Cannot start step {current_step.step_id}: previous step {prev_step.step_id} has not been started",
                    "pending",
                    "start",
                )

            if prev_step.progress.status not in (
                TaskStatus.COMPLETED,
                TaskStatus.APPROVED,
            ):
                raise WorkflowViolationError(
                    f"Cannot start step {current_step.step_id}: previous step {prev_step.step_id} "
                    f"has status {prev_step.progress.status.value}",
                    prev_step.progress.status.value,
                    "start",
                )

    def _can_start_task(self, spec: ProgrammingSpec, step: ImplementationStep) -> bool:
        """Check if a task can be started."""
        # If task is already in progress or completed, it can't be started again
        if step.progress and step.progress.status not in (
            TaskStatus.PENDING,
            TaskStatus.BLOCKED,
            TaskStatus.REJECTED,
        ):
            return False

        # If strict mode is disabled, any pending task can be started
        if not self.strict_mode:
            return True

        # In strict mode, check sequential execution
        try:
            self._enforce_sequential_execution(spec, step)
            return True
        except WorkflowViolationError:
            return False

    def _can_complete_task(self, step: ImplementationStep) -> bool:
        """Check if a task can be completed."""
        return (
            step.progress is not None and step.progress.status == TaskStatus.IN_PROGRESS
        )

    def _can_approve_task(self, step: ImplementationStep) -> bool:
        """Check if a task can be approved."""
        return step.progress is not None and step.progress.status in (
            TaskStatus.COMPLETED,
            TaskStatus.APPROVED,
        )

    def _has_all_required_approvals(self, step: ImplementationStep) -> bool:
        """Check if a task has all required approval levels."""
        if not step.approvals:
            return False

        approved_levels = {approval.level for approval in step.approvals}
        required_levels = set(self.required_approval_levels)
        return required_levels.issubset(approved_levels)

    def _add_work_log(
        self,
        spec: ProgrammingSpec,
        step_id: str,
        action: str,
        duration_minutes: int | None = None,
        notes: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a work log entry to the specification."""
        if not spec.work_logs:
            spec.work_logs = []

        log_entry = WorkLogEntry(
            spec_id=spec.metadata.id,
            step_id=step_id,
            action=action,
            timestamp=datetime.now(),
            duration_minutes=duration_minutes,
            notes=notes,
            metadata=metadata,
        )

        spec.work_logs.append(log_entry)
