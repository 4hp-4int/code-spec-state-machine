"""Prompt engineering utilities for enhanced AI context awareness."""

from datetime import datetime
from typing import Any

from .models import ContextParameters, FeedbackData


class PromptEngineer:
    """Manages AI prompt generation with context awareness and feedback integration."""

    def __init__(self):
        self.feedback_weights = {
            "accuracy_score": 0.4,
            "relevance_score": 0.4,
            "rating": 0.2,
        }

    def build_context_aware_prompt(
        self,
        base_prompt: str,
        context_params: ContextParameters | None = None,
        _existing_context: dict[str, Any] | None = None,
    ) -> str:
        """Build an enhanced prompt with context parameters."""

        if not context_params:
            return base_prompt

        context_sections = []

        # User role context
        if context_params.user_role:
            context_sections.append(
                f"User Role: You are working with a {context_params.user_role}"
            )

        # Target audience
        if context_params.target_audience:
            context_sections.append(
                f"Target Audience: Design this for {context_params.target_audience}"
            )

        # Desired tone
        if context_params.desired_tone:
            context_sections.append(
                f"Tone: Use a {context_params.desired_tone} approach"
            )

        # Complexity level
        if context_params.complexity_level:
            context_sections.append(
                f"Complexity: Target {context_params.complexity_level} level implementation"
            )

        # Time constraints
        if context_params.time_constraints:
            context_sections.append(
                f"Timeline: Optimize for {context_params.time_constraints}"
            )

        # Existing codebase context
        if context_params.existing_codebase_context:
            context_sections.append(
                f"Codebase Context: {context_params.existing_codebase_context}"
            )

        # Custom parameters
        for key, value in context_params.custom_parameters.items():
            context_sections.append(f"{key.replace('_', ' ').title()}: {value}")

        if not context_sections:
            return base_prompt

        # Build enhanced prompt
        return f"""CONTEXT PARAMETERS:
{chr(10).join(f"- {section}" for section in context_sections)}

TASK:
{base_prompt}

Please consider the above context parameters when generating your response to ensure maximum relevance and accuracy for the specified user and situation."""

    def collect_feedback(
        self, output_content: str, interactive: bool = True
    ) -> FeedbackData | None:
        """Collect user feedback on AI output."""

        if not interactive:
            return None

        # Check if we're in an interactive terminal
        import sys

        if not sys.stdin.isatty():
            print("📝 Feedback collection skipped (non-interactive terminal)")
            return None

        print("\n" + "=" * 50)
        print("📝 FEEDBACK REQUEST")
        print("=" * 50)
        print("Please rate the AI-generated specification:")

        feedback = FeedbackData(timestamp=datetime.now().isoformat())

        try:
            # Overall rating
            while True:
                try:
                    rating = input(
                        "Overall rating (1-5, or press Enter to skip): "
                    ).strip()
                    if not rating:
                        break
                    rating = int(rating)
                    if 1 <= rating <= 5:
                        feedback.rating = rating
                        break
                    print("Please enter a number between 1 and 5")
                except ValueError:
                    print("Please enter a valid number")

            # Accuracy score
            while True:
                try:
                    accuracy = input(
                        "Accuracy score (1-5, or press Enter to skip): "
                    ).strip()
                    if not accuracy:
                        break
                    accuracy = int(accuracy)
                    if 1 <= accuracy <= 5:
                        feedback.accuracy_score = accuracy
                        break
                    print("Please enter a number between 1 and 5")
                except ValueError:
                    print("Please enter a valid number")

            # Relevance score
            while True:
                try:
                    relevance = input(
                        "Relevance score (1-5, or press Enter to skip): "
                    ).strip()
                    if not relevance:
                        break
                    relevance = int(relevance)
                    if 1 <= relevance <= 5:
                        feedback.relevance_score = relevance
                        break
                    print("Please enter a number between 1 and 5")
                except ValueError:
                    print("Please enter a valid number")

            # Comments
            comments = input("Comments (optional): ").strip()
            if comments:
                feedback.comments = comments

            # Suggested improvements
            improvements = input("Suggested improvements (optional): ").strip()
            if improvements:
                feedback.suggested_improvements = improvements

            print("✅ Thank you for your feedback!")
            return feedback

        except KeyboardInterrupt:
            print("\n❌ Feedback collection cancelled")
            return None

    def analyze_feedback_history(
        self, feedback_history: list[FeedbackData]
    ) -> dict[str, Any]:
        """Analyze feedback history to identify improvement opportunities."""

        if not feedback_history:
            return {"summary": "No feedback data available"}

        # Calculate averages
        ratings = [f.rating for f in feedback_history if f.rating is not None]
        accuracy_scores = [
            f.accuracy_score for f in feedback_history if f.accuracy_score is not None
        ]
        relevance_scores = [
            f.relevance_score for f in feedback_history if f.relevance_score is not None
        ]

        analysis = {
            "total_feedback_count": len(feedback_history),
            "average_rating": sum(ratings) / len(ratings) if ratings else None,
            "average_accuracy": sum(accuracy_scores) / len(accuracy_scores)
            if accuracy_scores
            else None,
            "average_relevance": sum(relevance_scores) / len(relevance_scores)
            if relevance_scores
            else None,
            "improvement_areas": [],
        }

        # Identify improvement areas
        if analysis["average_accuracy"] and analysis["average_accuracy"] < 3.5:
            analysis["improvement_areas"].append("accuracy")

        if analysis["average_relevance"] and analysis["average_relevance"] < 3.5:
            analysis["improvement_areas"].append("relevance")

        if analysis["average_rating"] and analysis["average_rating"] < 3.5:
            analysis["improvement_areas"].append("overall_quality")

        # Collect common themes from comments
        common_themes = []
        all_comments = [f.comments for f in feedback_history if f.comments]
        if all_comments:
            # Simple keyword analysis
            keywords = {}
            for comment in all_comments:
                words = comment.lower().split()
                for word in words:
                    if len(word) > 3:  # Filter out short words
                        keywords[word] = keywords.get(word, 0) + 1

            # Get most common keywords
            sorted_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)
            common_themes = [word for word, count in sorted_keywords[:5] if count > 1]

        analysis["common_feedback_themes"] = common_themes

        return analysis

    def generate_improvement_suggestions(
        self, feedback_analysis: dict[str, Any]
    ) -> list[str]:
        """Generate suggestions for prompt improvements based on feedback analysis."""

        suggestions = []

        if "accuracy" in feedback_analysis.get("improvement_areas", []):
            suggestions.append(
                "Consider adding more specific technical constraints and requirements to prompts"
            )
            suggestions.append("Include examples of desired output format in prompts")

        if "relevance" in feedback_analysis.get("improvement_areas", []):
            suggestions.append(
                "Enhance context parameters to better capture user intent"
            )
            suggestions.append("Add more domain-specific context to prompts")

        if "overall_quality" in feedback_analysis.get("improvement_areas", []):
            suggestions.append(
                "Break down complex requests into smaller, more focused prompts"
            )
            suggestions.append(
                "Add quality checkpoints in multi-step generation processes"
            )

        # Add suggestions based on common themes
        themes = feedback_analysis.get("common_feedback_themes", [])
        if "complex" in themes or "complicated" in themes:
            suggestions.append(
                "Simplify language and explanations in generated content"
            )

        if "missing" in themes or "incomplete" in themes:
            suggestions.append(
                "Ensure prompts explicitly request comprehensive coverage"
            )

        return (
            suggestions
            if suggestions
            else ["Continue monitoring feedback for patterns"]
        )


def create_default_context_parameters() -> ContextParameters:
    """Create default context parameters for solo developer workflows."""
    return ContextParameters(
        user_role="solo developer",
        target_audience="solo developer",
        desired_tone="practical",
        complexity_level="intermediate",
        time_constraints="production ready",
    )
