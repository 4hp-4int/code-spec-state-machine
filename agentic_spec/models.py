"""Data models for programming specifications with database tracking support."""

from __future__ import annotations

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from datetime import datetime

if TYPE_CHECKING:
    pass

from pydantic import BaseModel, ConfigDict, Field


class TaskStatus(str, Enum):
    """Status of an implementation task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalLevel(str, Enum):
    """Approval levels for task completion."""

    SELF = "self"
    PEER = "peer"
    AI = "ai"
    ADMIN = "admin"


class SpecStatus(str, Enum):
    """Status of a specification."""

    DRAFT = "draft"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    IMPLEMENTED = "implemented"
    ARCHIVED = "archived"


class WorkflowStatus(str, Enum):
    """Workflow status for tracking specification lifecycle."""

    CREATED = "created"
    IN_PROGRESS = "in_progress"
    READY_FOR_REVIEW = "ready_for_review"
    UNDER_REVIEW = "under_review"
    CHANGES_REQUESTED = "changes_requested"
    READY_FOR_IMPLEMENTATION = "ready_for_implementation"
    IMPLEMENTING = "implementing"
    TESTING = "testing"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"


class DependencyModel(BaseModel):
    """Dependency information with extended metadata."""

    model_config = ConfigDict(extra="allow")

    name: str
    version: str | None = None
    description: str | None = None


@dataclass
class SpecMetadata:
    """Metadata for a programming specification."""

    id: str
    title: str
    inherits: list[str]
    created: str
    version: str
    status: str = "draft"  # Will migrate to SpecStatus enum
    parent_spec_id: str | None = None
    child_spec_ids: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "inherits": self.inherits,
            "created": self.created,
            "version": self.version,
            "status": self.status,
            "parent_spec_id": self.parent_spec_id,
            "child_spec_ids": self.child_spec_ids,
        }


@dataclass
class SpecContext:
    """Context information for a programming specification."""

    project: str
    domain: str
    dependencies: list[dict[str, Any] | DependencyModel]
    files_involved: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        deps = []
        for dep in self.dependencies:
            if isinstance(dep, DependencyModel):
                deps.append(dep.model_dump(exclude_none=True))
            else:
                deps.append(dep)

        return {
            "project": self.project,
            "domain": self.domain,
            "dependencies": deps,
            "files_involved": self.files_involved,
        }


@dataclass
class SpecRequirement:
    """Requirements section of a programming specification."""

    functional: list[str]
    non_functional: list[str]
    constraints: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return {
            "functional": self.functional,
            "non_functional": self.non_functional,
            "constraints": self.constraints,
        }


class TaskProgress(BaseModel):
    """Progress tracking for an implementation task."""

    model_config = ConfigDict(extra="allow")

    status: TaskStatus = TaskStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    time_spent_minutes: int | None = None
    completion_notes: str | None = None
    blockers: list[str] | None = None


class ApprovalRecord(BaseModel):
    """Approval record for task completion."""

    model_config = ConfigDict(extra="allow")

    level: ApprovalLevel
    approved_by: str
    approved_at: datetime
    comments: str | None = None
    override_reason: str | None = None


@dataclass
class ImplementationStep:
    """Individual implementation step in a programming specification."""

    task: str
    details: str
    files: list[str]
    acceptance: str
    estimated_effort: str = "medium"
    step_id: str | None = None
    sub_spec_id: str | None = None
    decomposition_hint: str | None = None  # "atomic" or "composite:reason"

    # New fields for database tracking
    progress: TaskProgress | None = None
    approvals: list[ApprovalRecord] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        result = {
            "task": self.task,
            "details": self.details,
            "files": self.files,
            "acceptance": self.acceptance,
            "estimated_effort": self.estimated_effort,
            "step_id": self.step_id,
            "sub_spec_id": self.sub_spec_id,
            "decomposition_hint": self.decomposition_hint,
        }

        # Include progress and approvals if present
        if self.progress:
            result["progress"] = self.progress.model_dump(
                exclude_none=True, mode="json"
            )
        if self.approvals:
            result["approvals"] = [
                a.model_dump(exclude_none=True, mode="json") for a in self.approvals
            ]

        return result


@dataclass
class ContextParameters:
    """Additional context parameters for AI prompt generation."""

    user_role: str | None = None
    target_audience: str | None = None
    desired_tone: str | None = None
    complexity_level: str | None = None
    time_constraints: str | None = None
    existing_codebase_context: str | None = None
    custom_parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        if not any(
            [
                self.user_role,
                self.target_audience,
                self.desired_tone,
                self.complexity_level,
                self.time_constraints,
                self.existing_codebase_context,
                self.custom_parameters,
            ]
        ):
            return None

        return {
            "user_role": self.user_role,
            "target_audience": self.target_audience,
            "desired_tone": self.desired_tone,
            "complexity_level": self.complexity_level,
            "time_constraints": self.time_constraints,
            "existing_codebase_context": self.existing_codebase_context,
            "custom_parameters": self.custom_parameters,
        }


@dataclass
class FeedbackData:
    """Feedback on AI-generated outputs."""

    rating: int | None = None
    accuracy_score: int | None = None
    relevance_score: int | None = None
    comments: str | None = None
    suggested_improvements: str | None = None
    timestamp: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return {
            "rating": self.rating,
            "accuracy_score": self.accuracy_score,
            "relevance_score": self.relevance_score,
            "comments": self.comments,
            "suggested_improvements": self.suggested_improvements,
            "timestamp": self.timestamp,
        }


class WorkLogEntry(BaseModel):
    """Work log entry for tracking task progress."""

    model_config = ConfigDict(extra="allow")

    spec_id: str
    step_id: str
    action: str  # started, completed, blocked, approved, etc.
    timestamp: datetime
    duration_minutes: int | None = None
    notes: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class ProgrammingSpec:
    """Complete programming specification with database tracking support."""

    metadata: SpecMetadata
    context: SpecContext
    requirements: SpecRequirement
    implementation: list[ImplementationStep]
    review_notes: list[str] | None = None
    context_parameters: ContextParameters | None = None
    feedback_history: list[FeedbackData] = field(default_factory=list)

    # New fields for database tracking
    work_logs: list[WorkLogEntry] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        result = {
            "metadata": self.metadata.to_dict(),
            "context": self.context.to_dict(),
            "requirements": self.requirements.to_dict(),
            "implementation": [step.to_dict() for step in self.implementation],
            "review_notes": self.review_notes,
        }

        # Handle optional fields
        ctx_params = (
            self.context_parameters.to_dict() if self.context_parameters else None
        )
        if ctx_params:
            result["context_parameters"] = ctx_params

        if self.feedback_history:
            result["feedback_history"] = [f.to_dict() for f in self.feedback_history]

        if self.work_logs:
            result["work_logs"] = [
                log.model_dump(exclude_none=True, mode="json") for log in self.work_logs
            ]

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProgrammingSpec:
        """Create ProgrammingSpec from dictionary (YAML data)."""
        # Convert dependencies
        deps = []
        for dep in data["context"].get("dependencies", []):
            if isinstance(dep, dict):
                if "name" in dep:
                    deps.append(DependencyModel(**dep))
                else:
                    deps.append(dep)
            else:
                deps.append({"name": str(dep)})

        # Create context with converted dependencies
        context_data = data["context"].copy()
        context_data["dependencies"] = deps

        # Create implementation steps
        impl_steps = []
        for step_data in data.get("implementation", []):
            step = step_data.copy()

            # Convert progress if present and not null
            if "progress" in step and step["progress"] is not None:
                step["progress"] = TaskProgress(**step["progress"])

            # Convert approvals if present and not null
            if "approvals" in step and step["approvals"] is not None:
                step["approvals"] = [ApprovalRecord(**a) for a in step["approvals"]]

            impl_steps.append(ImplementationStep(**step))

        # Create context parameters if present
        ctx_params = None
        if data.get("context_parameters"):
            ctx_params = ContextParameters(**data["context_parameters"])

        # Create feedback history
        feedback = [FeedbackData(**fb) for fb in data.get("feedback_history", [])]

        # Create work logs if present
        work_logs = None
        if "work_logs" in data and data["work_logs"] is not None:
            work_logs = [WorkLogEntry(**log) for log in data["work_logs"]]

        return cls(
            metadata=SpecMetadata(**data["metadata"]),
            context=SpecContext(**context_data),
            requirements=SpecRequirement(**data["requirements"]),
            implementation=impl_steps,
            review_notes=data.get("review_notes"),
            context_parameters=ctx_params,
            feedback_history=feedback,
            work_logs=work_logs,
        )


# Database-specific models for future SQL implementation
class SpecificationDB(BaseModel):
    """Database model for specifications with enhanced tracking fields."""

    model_config = ConfigDict(extra="allow")

    id: str
    title: str
    inherits: list[str] = Field(default_factory=list)
    created: datetime
    updated: datetime
    version: str
    status: SpecStatus
    parent_spec_id: str | None = None
    child_spec_ids: list[str] = Field(default_factory=list)

    # Enhanced tracking fields
    workflow_status: WorkflowStatus = WorkflowStatus.CREATED
    is_completed: bool = False
    completed_at: datetime | None = None
    last_accessed: datetime | None = None
    completion_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    priority: int = Field(default=5, ge=1, le=10)  # 1=highest, 10=lowest

    # Lifecycle timestamps
    reviewed_at: datetime | None = None
    approved_at: datetime | None = None
    implemented_at: datetime | None = None

    # Metadata tracking
    created_by: str = "system"
    last_updated_by: str = "system"
    tags: list[str] = Field(default_factory=list)

    # JSON fields for complex data
    context: dict[str, Any]
    requirements: dict[str, Any]
    review_notes: list[str] = Field(default_factory=list)
    context_parameters: dict[str, Any] | None = None

    # Relationships (will be foreign keys in DB)
    tasks: list[TaskDB] = Field(default_factory=list)
    work_logs: list[WorkLogDB] = Field(default_factory=list)


class TaskDB(BaseModel):
    """Database model for implementation tasks with enhanced tracking."""

    model_config = ConfigDict(extra="allow")

    id: str
    spec_id: str
    step_index: int
    task: str
    details: str
    files: list[str]
    acceptance: str
    estimated_effort: str
    sub_spec_id: str | None = None
    decomposition_hint: str | None = None

    # Enhanced progress tracking
    status: TaskStatus = TaskStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    time_spent_minutes: int | None = None
    completion_notes: str | None = None
    blockers: list[str] = Field(default_factory=list)

    # Enhanced tracking fields
    is_completed: bool = False
    assigned_to: str = "unassigned"
    priority: int = Field(default=5, ge=1, le=10)  # 1=highest, 10=lowest
    last_accessed: datetime | None = None
    estimated_completion_date: datetime | None = None
    actual_effort_minutes: int | None = None
    dependencies: list[str] = Field(default_factory=list)  # Other task IDs

    # Lifecycle timestamps
    blocked_at: datetime | None = None
    unblocked_at: datetime | None = None
    approved_at: datetime | None = None
    rejected_at: datetime | None = None

    # Relationships
    approvals: list[ApprovalDB] = Field(default_factory=list)


class ApprovalDB(BaseModel):
    """Database model for task approvals."""

    model_config = ConfigDict(extra="allow")

    id: str
    task_id: str
    level: ApprovalLevel
    approved_by: str
    approved_at: datetime
    comments: str | None = None
    override_reason: str | None = None


class WorkLogDB(BaseModel):
    """Database model for work logs."""

    model_config = ConfigDict(extra="allow")

    id: str
    spec_id: str
    task_id: str | None = None
    action: str
    timestamp: datetime
    duration_minutes: int | None = None
    notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
