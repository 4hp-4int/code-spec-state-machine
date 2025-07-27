"""Custom exception classes for agentic-spec domain-specific errors."""


class AgenticSpecError(Exception):
    """Base exception class for all agentic-spec related errors."""

    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(message)


class SpecificationError(AgenticSpecError):
    """Exception raised for specification-related errors."""


class TemplateError(AgenticSpecError):
    """Exception raised for template-related errors."""


class ConfigurationError(AgenticSpecError):
    """Exception raised for configuration-related errors."""


class AIServiceError(AgenticSpecError):
    """Exception raised when AI service operations fail."""


class FileSystemError(AgenticSpecError):
    """Exception raised for file system operation errors."""


class ValidationError(AgenticSpecError):
    """Exception raised for data validation errors."""
