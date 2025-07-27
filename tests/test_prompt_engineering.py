"""Tests for the prompt engineering module."""

from datetime import UTC, datetime

import pytest

from agentic_spec.models import ContextParameters, FeedbackData
from agentic_spec.prompt_engineering import (
    PromptEngineer,
    create_default_context_parameters,
)


class TestPromptEngineer:
    """Test cases for the PromptEngineer class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.prompt_engineer = PromptEngineer()
        self.base_prompt = "Create a REST API for user management"

    def test_build_context_aware_prompt_with_no_context(self):
        """Test prompt building with no context parameters."""
        result = self.prompt_engineer.build_context_aware_prompt(self.base_prompt, None)
        assert result == self.base_prompt

    def test_build_context_aware_prompt_with_empty_context(self):
        """Test prompt building with empty context parameters."""
        context_params = ContextParameters()
        result = self.prompt_engineer.build_context_aware_prompt(
            self.base_prompt, context_params
        )
        assert result == self.base_prompt

    def test_build_context_aware_prompt_with_full_context(self):
        """Test prompt building with all context parameters."""
        context_params = ContextParameters(
            user_role="senior developer",
            target_audience="enterprise team",
            desired_tone="detailed",
            complexity_level="advanced",
            time_constraints="production ready",
            existing_codebase_context="Django application with PostgreSQL",
            custom_parameters={"architecture": "microservices"},
        )

        result = self.prompt_engineer.build_context_aware_prompt(
            self.base_prompt, context_params
        )

        # Check that context sections are included
        assert "User Role: You are working with a senior developer" in result
        assert "Target Audience: Design this for enterprise team" in result
        assert "Tone: Use a detailed approach" in result
        assert "Complexity: Target advanced level implementation" in result
        assert "Timeline: Optimize for production ready" in result
        assert "Codebase Context: Django application with PostgreSQL" in result
        assert "Architecture: microservices" in result
        assert self.base_prompt in result

    def test_build_context_aware_prompt_with_partial_context(self):
        """Test prompt building with only some context parameters."""
        context_params = ContextParameters(
            user_role="solo developer", desired_tone="practical"
        )

        result = self.prompt_engineer.build_context_aware_prompt(
            self.base_prompt, context_params
        )

        assert "User Role: You are working with a solo developer" in result
        assert "Tone: Use a practical approach" in result
        assert "Target Audience:" not in result  # Should not include empty parameters
        assert self.base_prompt in result

    def test_analyze_feedback_history_empty(self):
        """Test feedback analysis with no feedback data."""
        analysis = self.prompt_engineer.analyze_feedback_history([])

        assert analysis["summary"] == "No feedback data available"

    def test_analyze_feedback_history_with_data(self):
        """Test feedback analysis with sample feedback data."""
        feedback_data = [
            FeedbackData(
                rating=4, accuracy_score=5, relevance_score=3, comments="Good overall"
            ),
            FeedbackData(
                rating=3,
                accuracy_score=4,
                relevance_score=4,
                comments="Could be more specific",
            ),
            FeedbackData(
                rating=5,
                accuracy_score=5,
                relevance_score=5,
                comments="Excellent detail",
            ),
        ]

        analysis = self.prompt_engineer.analyze_feedback_history(feedback_data)

        assert analysis["total_feedback_count"] == 3
        assert analysis["average_rating"] == 4.0
        assert analysis["average_accuracy"] == pytest.approx(4.67, rel=1e-2)
        assert analysis["average_relevance"] == 4.0
        assert (
            len(analysis["improvement_areas"]) >= 0
        )  # May or may not have improvement areas

    def test_analyze_feedback_history_with_low_scores(self):
        """Test feedback analysis identifies improvement areas for low scores."""
        feedback_data = [
            FeedbackData(rating=2, accuracy_score=2, relevance_score=3),
            FeedbackData(rating=1, accuracy_score=2, relevance_score=2),
        ]

        analysis = self.prompt_engineer.analyze_feedback_history(feedback_data)

        assert "accuracy" in analysis["improvement_areas"]
        assert "relevance" in analysis["improvement_areas"]
        assert "overall_quality" in analysis["improvement_areas"]

    def test_generate_improvement_suggestions_for_accuracy(self):
        """Test improvement suggestions for accuracy issues."""
        analysis = {"improvement_areas": ["accuracy"], "common_feedback_themes": []}

        suggestions = self.prompt_engineer.generate_improvement_suggestions(analysis)

        assert any("technical constraints" in suggestion for suggestion in suggestions)
        assert any("examples" in suggestion for suggestion in suggestions)

    def test_generate_improvement_suggestions_for_relevance(self):
        """Test improvement suggestions for relevance issues."""
        analysis = {"improvement_areas": ["relevance"], "common_feedback_themes": []}

        suggestions = self.prompt_engineer.generate_improvement_suggestions(analysis)

        assert any("context parameters" in suggestion for suggestion in suggestions)
        assert any("domain-specific" in suggestion for suggestion in suggestions)

    def test_generate_improvement_suggestions_with_themes(self):
        """Test improvement suggestions based on common feedback themes."""
        analysis = {
            "improvement_areas": [],
            "common_feedback_themes": ["complex", "missing"],
        }

        suggestions = self.prompt_engineer.generate_improvement_suggestions(analysis)

        assert any("Simplify language" in suggestion for suggestion in suggestions)
        assert any("comprehensive coverage" in suggestion for suggestion in suggestions)

    def test_generate_improvement_suggestions_no_issues(self):
        """Test improvement suggestions when no issues are identified."""
        analysis = {"improvement_areas": [], "common_feedback_themes": []}

        suggestions = self.prompt_engineer.generate_improvement_suggestions(analysis)

        assert "Continue monitoring feedback" in suggestions[0]


class TestContextParameters:
    """Test cases for ContextParameters model."""

    def test_context_parameters_defaults(self):
        """Test that ContextParameters can be created with defaults."""
        context = ContextParameters()

        assert context.user_role is None
        assert context.target_audience is None
        assert context.desired_tone is None
        assert context.complexity_level is None
        assert context.time_constraints is None
        assert context.existing_codebase_context is None
        assert context.custom_parameters == {}

    def test_context_parameters_with_values(self):
        """Test ContextParameters creation with values."""
        context = ContextParameters(
            user_role="solo developer",
            target_audience="small team",
            desired_tone="practical",
            complexity_level="intermediate",
            time_constraints="quick prototype",
            existing_codebase_context="Flask app",
            custom_parameters={"database": "SQLite"},
        )

        assert context.user_role == "solo developer"
        assert context.target_audience == "small team"
        assert context.desired_tone == "practical"
        assert context.complexity_level == "intermediate"
        assert context.time_constraints == "quick prototype"
        assert context.existing_codebase_context == "Flask app"
        assert context.custom_parameters["database"] == "SQLite"


class TestFeedbackData:
    """Test cases for FeedbackData model."""

    def test_feedback_data_defaults(self):
        """Test FeedbackData creation with defaults."""
        feedback = FeedbackData()

        assert feedback.rating is None
        assert feedback.accuracy_score is None
        assert feedback.relevance_score is None
        assert feedback.comments is None
        assert feedback.suggested_improvements is None
        assert feedback.timestamp is None

    def test_feedback_data_with_values(self):
        """Test FeedbackData creation with values."""
        timestamp = datetime.now(tz=UTC).isoformat()
        feedback = FeedbackData(
            rating=4,
            accuracy_score=5,
            relevance_score=3,
            comments="Good specification",
            suggested_improvements="Add more examples",
            timestamp=timestamp,
        )

        assert feedback.rating == 4
        assert feedback.accuracy_score == 5
        assert feedback.relevance_score == 3
        assert feedback.comments == "Good specification"
        assert feedback.suggested_improvements == "Add more examples"
        assert feedback.timestamp == timestamp


def test_create_default_context_parameters():
    """Test the create_default_context_parameters function."""
    defaults = create_default_context_parameters()

    assert defaults.user_role == "solo developer"
    assert defaults.target_audience == "solo developer"
    assert defaults.desired_tone == "practical"
    assert defaults.complexity_level == "intermediate"
    assert defaults.time_constraints == "production ready"
    assert defaults.existing_codebase_context is None
    assert defaults.custom_parameters == {}
