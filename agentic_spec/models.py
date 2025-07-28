"""Data models for programming specifications with database tracking support."""

from __future__ import annotations

# Removed dataclass imports - now using Pydantic BaseModel consistently
from datetime import datetime
from enum import Enum
from typing import Any

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
    version: str | None = Field(
        None, description="Version constraint for the dependency"
    )
    description: str | None = Field(
        None, description="Human-readable description of the dependency"
    )


class SpecMetadata(BaseModel):
    """Metadata for a programming specification."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="Unique identifier for the specification")
    title: str = Field(..., description="Human-readable title for the specification")
    inherits: list[str] = Field(
        default_factory=list, description="List of template IDs this spec inherits from"
    )
    created: str = Field(
        ..., description="ISO timestamp when specification was created"
    )
    version: str = Field(..., description="Semantic version of the specification")
    status: str = Field("draft", description="Current status of the specification")
    parent_spec_id: str | None = Field(
        None, description="ID of parent specification if this is a sub-spec"
    )
    child_spec_ids: list[str] | None = Field(
        None, description="List of child specification IDs"
    )
    author: str | None = Field(None, description="Author who created the specification")
    last_modified: str | None = Field(
        None, description="ISO timestamp when last modified"
    )


class SpecContext(BaseModel):
    """Context information for a programming specification."""

    model_config = ConfigDict(extra="allow")

    project: str = Field(
        ..., description="Name of the project this specification belongs to"
    )
    domain: str = Field(
        ..., description="Domain or area of focus for this specification"
    )
    dependencies: list[dict[str, Any] | DependencyModel] = Field(
        default_factory=list,
        description="List of project dependencies (libraries, frameworks, tools)",
    )
    files_involved: list[str] | None = Field(
        None, description="List of files that will be modified or created"
    )


class SpecRequirement(BaseModel):
    """Requirements section of a programming specification."""

    model_config = ConfigDict(extra="allow")

    functional: list[str] = Field(..., description="List of functional requirements")
    non_functional: list[str] = Field(
        ...,
        description="List of non-functional requirements (performance, security, etc.)",
    )
    constraints: list[str] | None = Field(
        None, description="List of constraints and limitations"
    )


class TaskProgress(BaseModel):
    """Progress tracking for an implementation task."""

    model_config = ConfigDict(extra="allow")

    status: TaskStatus = Field(
        TaskStatus.PENDING, description="Current status of the task"
    )
    started_at: datetime | None = Field(
        None, description="Timestamp when task was started"
    )
    completed_at: datetime | None = Field(
        None, description="Timestamp when task was completed"
    )
    time_spent_minutes: int | None = Field(
        None, ge=0, description="Time spent on task in minutes"
    )
    completion_notes: str | None = Field(
        None, description="Notes about task completion or issues"
    )
    blockers: list[str] | None = Field(
        None, description="List of items blocking task completion"
    )


class ApprovalRecord(BaseModel):
    """Approval record for task completion."""

    model_config = ConfigDict(extra="allow")

    level: ApprovalLevel = Field(
        ..., description="Level of approval (self, peer, admin, etc.)"
    )
    approved_by: str = Field(..., description="Identifier of who approved the task")
    approved_at: datetime = Field(..., description="Timestamp when approval was given")
    comments: str | None = Field(None, description="Comments from the approver")
    override_reason: str | None = Field(
        None, description="Reason if this approval overrides strict mode"
    )


class ImplementationStep(BaseModel):
    """Individual implementation step in a programming specification."""

    model_config = ConfigDict(extra="allow")

    task: str = Field(..., description="Brief description of the implementation task")
    details: str = Field(
        ..., description="Detailed description of what needs to be implemented"
    )
    files: list[str] = Field(
        default_factory=list,
        description="List of files that will be modified or created",
    )
    acceptance: str = Field(
        ..., description="Acceptance criteria for when this task is complete"
    )
    estimated_effort: str = Field(
        "medium", description="Estimated effort level (low, medium, high, composite)"
    )
    step_id: str | None = Field(None, description="Unique identifier for this step")
    sub_spec_id: str | None = Field(
        None, description="ID of sub-specification if this step was expanded"
    )
    decomposition_hint: str | None = Field(
        None,
        description="Hint about decomposition: 'atomic' for indivisible or 'composite:reason'",
    )

    # Database tracking fields
    progress: TaskProgress | None = Field(
        None, description="Progress tracking information"
    )
    approvals: list[ApprovalRecord] | None = Field(
        None, description="List of approvals for this task"
    )


class ContextParameters(BaseModel):
    """Additional context parameters for AI prompt generation."""

    model_config = ConfigDict(extra="allow")

    user_role: str | None = Field(
        None, description="Role of the user requesting this specification"
    )
    target_audience: str | None = Field(
        None, description="Target audience for the implementation"
    )
    desired_tone: str | None = Field(
        None,
        description="Desired tone for the specification (practical, detailed, etc.)",
    )
    complexity_level: str | None = Field(
        None, description="Expected complexity level (beginner, intermediate, advanced)"
    )
    time_constraints: str | None = Field(
        None, description="Time constraints for implementation"
    )
    existing_codebase_context: str | None = Field(
        None, description="Context about existing codebase"
    )
    custom_parameters: dict[str, Any] = Field(
        default_factory=dict, description="Additional custom parameters"
    )


class FeedbackData(BaseModel):
    """Feedback on AI-generated outputs."""

    model_config = ConfigDict(extra="allow")

    rating: int | None = Field(None, ge=1, le=5, description="Overall rating from 1-5")
    accuracy_score: int | None = Field(
        None, ge=1, le=5, description="Accuracy score from 1-5"
    )
    relevance_score: int | None = Field(
        None, ge=1, le=5, description="Relevance score from 1-5"
    )
    comments: str | None = Field(None, description="Detailed feedback comments")
    suggested_improvements: str | None = Field(
        None, description="Suggestions for improvement"
    )
    timestamp: str | None = Field(
        None, description="ISO timestamp when feedback was provided"
    )


class WorkLogEntry(BaseModel):
    """Work log entry for tracking task progress."""

    model_config = ConfigDict(extra="allow")

    spec_id: str = Field(
        ..., description="ID of the specification this log entry belongs to"
    )
    step_id: str = Field(..., description="ID of the step this log entry is for")
    action: str = Field(
        ...,
        description="Action performed (started, completed, blocked, approved, etc.)",
    )
    timestamp: datetime = Field(..., description="When this action occurred")
    duration_minutes: int | None = Field(
        None, ge=0, description="Duration of the action in minutes"
    )
    notes: str | None = Field(None, description="Additional notes about this action")
    metadata: dict[str, Any] | None = Field(
        None, description="Additional metadata for this log entry"
    )


class ProgrammingSpec(BaseModel):
    """Complete programming specification with database tracking support."""

    model_config = ConfigDict(extra="allow")

    metadata: SpecMetadata = Field(..., description="Metadata about this specification")
    context: SpecContext = Field(
        ..., description="Context information for this specification"
    )
    requirements: SpecRequirement = Field(..., description="Requirements section")
    implementation: list[ImplementationStep] = Field(
        default_factory=list, description="List of implementation steps"
    )
    review_notes: list[str] | None = Field(
        None, description="Review notes and feedback"
    )
    context_parameters: ContextParameters | None = Field(
        None, description="Additional context parameters for AI generation"
    )
    feedback_history: list[FeedbackData] = Field(
        default_factory=list, description="History of feedback on this specification"
    )

    # Database tracking fields
    work_logs: list[WorkLogEntry] | None = Field(
        None, description="Work log entries for this specification"
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProgrammingSpec:
        """Create ProgrammingSpec from dictionary (YAML data)."""
        # Preprocess dependencies to ensure they're in the right format
        if "context" in data and "dependencies" in data["context"]:
            deps = []
            for dep in data["context"]["dependencies"]:
                if isinstance(dep, dict):
                    if "name" in dep:
                        deps.append(DependencyModel(**dep))
                    else:
                        deps.append(dep)
                else:
                    deps.append({"name": str(dep)})
            data["context"]["dependencies"] = deps

        # Let Pydantic handle the rest of the conversion automatically
        return cls(**data)


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
