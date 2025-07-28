"""Custom exception classes for agentic-spec domain-specific errors."""


class AgenticSpecError(Exception):
    """Base exception class for all agentic-spec related errors."""

    def __init__(self, message: str, details: str | None = None):
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


class DatabaseError(AgenticSpecError):
    """Exception raised for database operation errors."""


class ConnectionError(DatabaseError):
    """Exception raised for database connection errors."""


class TransactionError(DatabaseError):
    """Exception raised for database transaction errors."""


class SyncFoundationConfigError(ConfigurationError):
    """Exception raised for sync-foundation configuration errors."""

    def __init__(
        self, message: str, config_path: str | None = None, field: str | None = None
    ):
        self.config_path = config_path
        self.field = field
        details = []
        if config_path:
            details.append(f"Config file: {config_path}")
        if field:
            details.append(f"Field: {field}")
        super().__init__(message, "; ".join(details) if details else None)


class ConfigValidationError(SyncFoundationConfigError):
    """Exception raised when configuration validation fails."""


class ConfigParsingError(SyncFoundationConfigError):
    """Exception raised when configuration file parsing fails."""


class GitError(AgenticSpecError):
    """Exception raised for git operation errors."""

    def __init__(
        self,
        message: str,
        git_command: str | None = None,
        return_code: int | None = None,
    ):
        self.git_command = git_command
        self.return_code = return_code
        details = []
        if git_command:
            details.append(f"Git command: {git_command}")
        if return_code is not None:
            details.append(f"Return code: {return_code}")
        super().__init__(message, "; ".join(details) if details else None)
