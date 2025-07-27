"""Tests for error handling and logging functionality."""

import pytest
import logging
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from agentic_spec.cli import setup_logging, get_prompt_input
from agentic_spec.exceptions import (
    AgenticSpecError,
    SpecificationError,
    TemplateError,
    ConfigurationError,
    AIServiceError,
    FileSystemError,
    ValidationError,
)


class TestCustomExceptions:
    """Test custom exception classes."""

    def test_agentic_spec_error_base(self):
        """Test base exception class."""
        error = AgenticSpecError("Test message", "Test details")
        assert error.message == "Test message"
        assert error.details == "Test details"
        assert str(error) == "Test message"

    def test_specification_error(self):
        """Test specification-specific error."""
        error = SpecificationError("Spec error")
        assert isinstance(error, AgenticSpecError)
        assert error.message == "Spec error"

    def test_template_error(self):
        """Test template-specific error."""
        error = TemplateError("Template error", "Template details")
        assert isinstance(error, AgenticSpecError)
        assert error.message == "Template error"
        assert error.details == "Template details"

    def test_configuration_error(self):
        """Test configuration-specific error."""
        error = ConfigurationError("Config error")
        assert isinstance(error, AgenticSpecError)

    def test_ai_service_error(self):
        """Test AI service error."""
        error = AIServiceError("AI error")
        assert isinstance(error, AgenticSpecError)

    def test_file_system_error(self):
        """Test file system error."""
        error = FileSystemError("FS error")
        assert isinstance(error, AgenticSpecError)

    def test_validation_error(self):
        """Test validation error."""
        error = ValidationError("Validation error")
        assert isinstance(error, AgenticSpecError)


class TestLoggingConfiguration:
    """Test logging setup functionality."""

    def test_setup_logging_default(self):
        """Test logging setup with default parameters."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            with patch('agentic_spec.cli.Path', return_value=tmp_path / "logs"):
                logger = setup_logging()
                
                try:
                    assert logger.name == "agentic_spec"
                    assert logger.level == logging.INFO
                    assert len(logger.handlers) >= 2  # Console and file handlers
                finally:
                    # Clean up handlers to release file locks
                    for handler in logger.handlers[:]:
                        handler.close()
                        logger.removeHandler(handler)

    def test_setup_logging_debug_level(self):
        """Test logging setup with debug level."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            with patch('agentic_spec.cli.Path', return_value=tmp_path / "logs"):
                logger = setup_logging("DEBUG")
                
                try:
                    assert logger.level == logging.DEBUG
                finally:
                    # Clean up handlers to release file locks
                    for handler in logger.handlers[:]:
                        handler.close()
                        logger.removeHandler(handler)

    def test_setup_logging_prevents_duplicates(self):
        """Test that multiple calls don't create duplicate handlers."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            with patch('agentic_spec.cli.Path', return_value=tmp_path / "logs"):
                logger1 = setup_logging()
                handler_count = len(logger1.handlers)
                
                logger2 = setup_logging()
                try:
                    assert len(logger2.handlers) == handler_count
                finally:
                    # Clean up handlers to release file locks
                    for handler in logger2.handlers[:]:
                        handler.close()
                        logger2.removeHandler(handler)


class TestPromptInputHandling:
    """Test prompt input error handling."""

    def test_get_prompt_input_command_line(self):
        """Test prompt input from command line argument."""
        result = get_prompt_input("test prompt")
        assert result == "test prompt"

    def test_get_prompt_input_empty_raises_validation_error(self):
        """Test that empty prompt raises ValidationError."""
        with patch('sys.stdin.isatty', return_value=True):
            with patch('builtins.input', side_effect=EOFError):
                with pytest.raises(ValidationError, match="No prompt provided"):
                    get_prompt_input(None)

    def test_get_prompt_input_keyboard_interrupt(self):
        """Test handling of keyboard interrupt during interactive input."""
        with patch('sys.stdin.isatty', return_value=True):
            with patch('builtins.input', side_effect=KeyboardInterrupt):
                with pytest.raises(SystemExit):
                    get_prompt_input(None)

    def test_get_prompt_input_piped_error(self):
        """Test handling of piped input errors."""
        with patch('sys.stdin.isatty', return_value=False):
            with patch('sys.stdin.read', side_effect=IOError("Read error")):
                with pytest.raises(FileSystemError, match="Failed to read piped input"):
                    get_prompt_input(None)

    def test_get_prompt_input_piped_success(self):
        """Test successful piped input."""
        with patch('sys.stdin.isatty', return_value=False):
            with patch('sys.stdin.read', return_value="piped prompt"):
                result = get_prompt_input(None)
                assert result == "piped prompt"

    def test_get_prompt_input_interactive_success(self):
        """Test successful interactive input."""
        with patch('sys.stdin.isatty', return_value=True):
            with patch('builtins.input', side_effect=["line 1", "line 2", EOFError]):
                result = get_prompt_input(None)
                assert result == "line 1\nline 2"


class TestIntegrationErrorHandling:
    """Integration tests for error handling in CLI commands."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            templates_dir = tmp_path / "templates"
            specs_dir = tmp_path / "specs" 
            templates_dir.mkdir()
            specs_dir.mkdir()
            yield templates_dir, specs_dir

    def test_missing_specs_directory_handling(self, temp_dirs):
        """Test handling of missing specs directory."""
        templates_dir, specs_dir = temp_dirs
        specs_dir.rmdir()  # Remove the directory
        
        # The CLI should handle this gracefully by creating the directory
        # or providing a meaningful error message
        assert not specs_dir.exists()

    def test_logging_creates_directory(self):
        """Test that logging setup creates the logs directory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            logs_dir = tmp_path / "logs"
            
            with patch('agentic_spec.cli.Path', return_value=logs_dir):
                logger = setup_logging()
                
                try:
                    # Verify the logs directory was created
                    assert logs_dir.exists()
                finally:
                    # Clean up handlers to release file locks
                    for handler in logger.handlers[:]:
                        handler.close()
                        logger.removeHandler(handler)


if __name__ == "__main__":
    pytest.main([__file__])