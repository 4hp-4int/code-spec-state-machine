"""Data models for programming specifications."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SpecMetadata:
    """Metadata for a programming specification."""

    id: str
    inherits: list[str]
    created: str
    version: str
    status: str = "draft"  # draft, reviewed, approved, implemented
    parent_spec_id: str | None = None
    child_spec_ids: list[str] = None


@dataclass
class SpecContext:
    """Context information for a programming specification."""

    project: str
    domain: str
    dependencies: list[str]
    files_involved: list[str] = None


@dataclass
class SpecRequirement:
    """Requirements section of a programming specification."""

    functional: list[str]
    non_functional: list[str]
    constraints: list[str] = None


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


@dataclass
class ContextParameters:
    """Additional context parameters for AI prompt generation."""

    user_role: str | None = (
        None  # e.g., "senior developer", "solo developer", "team lead"
    )
    target_audience: str | None = None  # e.g., "solo developer", "enterprise team"
    desired_tone: str | None = (
        None  # e.g., "practical", "detailed", "beginner-friendly"
    )
    complexity_level: str | None = None  # e.g., "simple", "intermediate", "advanced"
    time_constraints: str | None = None  # e.g., "quick prototype", "production ready"
    existing_codebase_context: str | None = (
        None  # Brief description of current codebase
    )
    custom_parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class FeedbackData:
    """Feedback on AI-generated outputs."""

    rating: int | None = None  # 1-5 rating
    accuracy_score: int | None = None  # 1-5 accuracy rating
    relevance_score: int | None = None  # 1-5 relevance rating
    comments: str | None = None
    suggested_improvements: str | None = None
    timestamp: str | None = None


@dataclass
class ProgrammingSpec:
    """Complete programming specification."""

    metadata: SpecMetadata
    context: SpecContext
    requirements: SpecRequirement
    implementation: list[ImplementationStep]
    review_notes: list[str] = None
    context_parameters: ContextParameters | None = None
    feedback_history: list[FeedbackData] = field(default_factory=list)
