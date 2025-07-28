"""Tests for web UI CLI commands."""

import socket
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from agentic_spec.cli_web import (
    app,
    get_web_config,
    is_port_in_use,
)
from agentic_spec.config import AgenticSpecConfig, WebUISettings


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_config():
    """Create a mock configuration with web UI settings."""
    config = AgenticSpecConfig()
    config.web_ui = WebUISettings(
        host="127.0.0.1", port=8000, auto_open_browser=True, log_level="info"
    )
    return config


class TestWebUICommands:
    """Test web UI CLI commands."""

    def test_is_port_in_use(self):
        """Test port availability checking."""
        # Test with a port that should be free
        assert not is_port_in_use("127.0.0.1", 0)

        # Test with a port that we bind
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            s.listen(1)
            port = s.getsockname()[1]
            assert is_port_in_use("127.0.0.1", port)

    def test_get_web_config(self, mock_config):
        """Test web configuration extraction."""
        web_config = get_web_config(mock_config)
        assert web_config["host"] == "127.0.0.1"
        assert web_config["port"] == 8000
        assert web_config["auto_open_browser"] is True
        assert web_config["log_level"] == "info"

    @patch("agentic_spec.cli_web.load_config")
    def test_status_command(self, mock_load_config, runner, mock_config):
        """Test the status command."""
        mock_load_config.return_value = mock_config

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "Web UI Server Status" in result.stdout
        assert "Stopped" in result.stdout
        assert "127.0.0.1" in result.stdout
        assert "8000" in result.stdout

    @patch("agentic_spec.cli_web.load_config")
    @patch("agentic_spec.cli_web.webbrowser")
    def test_open_command_server_not_running(
        self, mock_browser, mock_load_config, runner, mock_config
    ):
        """Test opening browser when server is not running."""
        mock_load_config.return_value = mock_config

        # Mock port as in use (server not running)
        with patch("agentic_spec.cli_web.is_port_in_use", return_value=True):
            result = runner.invoke(app, ["open"])

        assert result.exit_code == 0
        assert "Web UI server is not running" in result.stdout
        mock_browser.open.assert_not_called()

    @patch("agentic_spec.cli_web.load_config")
    @patch("agentic_spec.cli_web.webbrowser")
    def test_open_command_server_running(
        self, mock_browser, mock_load_config, runner, mock_config
    ):
        """Test opening browser when server is running."""
        mock_load_config.return_value = mock_config

        # Mock port as not in use (server running)
        with patch("agentic_spec.cli_web.is_port_in_use", return_value=False):
            result = runner.invoke(app, ["open"])

        assert result.exit_code == 0
        assert "Opening browser" in result.stdout
        mock_browser.open.assert_called_once_with("http://127.0.0.1:8000")

    @patch("agentic_spec.cli_web.load_config")
    def test_config_show(self, mock_load_config, runner, mock_config):
        """Test showing configuration."""
        mock_load_config.return_value = mock_config

        result = runner.invoke(app, ["config"])
        assert result.exit_code == 0
        assert "Web UI Configuration" in result.stdout
        assert "127.0.0.1" in result.stdout
        assert "8000" in result.stdout

    @patch("agentic_spec.cli_web.load_config")
    @patch("agentic_spec.cli_web.get_config_manager")
    def test_config_update(
        self, mock_get_manager, mock_load_config, runner, mock_config
    ):
        """Test updating configuration."""
        mock_load_config.return_value = mock_config
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(app, ["config", "--port", "9000", "--no-auto-browser"])
        assert result.exit_code == 0
        assert "Configuration updated" in result.stdout

        # Verify save was called
        mock_manager.save_config.assert_called_once()
        saved_config = mock_manager.save_config.call_args[0][0]
        assert saved_config.web_ui.port == 9000
        assert saved_config.web_ui.auto_open_browser is False

    @patch("agentic_spec.cli_web.load_config")
    def test_config_invalid_log_level(self, mock_load_config, runner, mock_config):
        """Test configuration with invalid log level."""
        mock_load_config.return_value = mock_config

        result = runner.invoke(app, ["config", "--log-level", "invalid"])
        assert result.exit_code == 0
        assert "Invalid log level" in result.stdout

    @patch("agentic_spec.cli_web.load_config")
    @patch("agentic_spec.cli_web.DB_PATH")
    @patch("agentic_spec.cli_web.threading.Thread")
    def test_start_command_port_in_use(
        self, mock_thread, mock_db_path, mock_load_config, runner, mock_config
    ):
        """Test starting server when port is in use."""
        mock_load_config.return_value = mock_config
        mock_db_path.exists.return_value = True

        # Mock port as in use
        with patch("agentic_spec.cli_web.is_port_in_use", return_value=True):
            result = runner.invoke(app, ["start"])

        assert result.exit_code == 0
        assert "Port 8000 is already in use" in result.stdout
        mock_thread.assert_not_called()

    @patch("agentic_spec.cli_web.load_config")
    @patch("agentic_spec.cli_web.DB_PATH")
    def test_start_command_no_database(
        self, mock_db_path, mock_load_config, runner, mock_config
    ):
        """Test starting server when database doesn't exist."""
        mock_load_config.return_value = mock_config
        mock_db_path.exists.return_value = False

        result = runner.invoke(app, ["start"])
        assert result.exit_code == 0
        assert "Database not found" in result.stdout
        assert "migrate-bulk" in result.stdout

    def test_stop_command_no_server(self, runner):
        """Test stopping server when not running."""
        result = runner.invoke(app, ["stop"])
        assert result.exit_code == 0
        assert "Web UI server is not running" in result.stdout


class TestWebUISettings:
    """Test WebUISettings model validation."""

    def test_valid_settings(self):
        """Test creating valid settings."""
        settings = WebUISettings(
            host="0.0.0.0", port=3000, auto_open_browser=False, log_level="debug"
        )
        assert settings.host == "0.0.0.0"
        assert settings.port == 3000
        assert settings.auto_open_browser is False
        assert settings.log_level == "debug"

    def test_invalid_port(self):
        """Test invalid port validation."""
        with pytest.raises(ValueError, match="Port must be between"):
            WebUISettings(port=70000)

        with pytest.raises(ValueError, match="Port must be between"):
            WebUISettings(port=0)

    def test_invalid_log_level(self):
        """Test invalid log level validation."""
        with pytest.raises(ValueError, match="Invalid log level"):
            WebUISettings(log_level="invalid")

    def test_log_level_case_insensitive(self):
        """Test log level is case insensitive."""
        settings = WebUISettings(log_level="DEBUG")
        assert settings.log_level == "debug"

        settings = WebUISettings(log_level="Warning")
        assert settings.log_level == "warning"
