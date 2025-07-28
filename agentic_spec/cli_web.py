"""Web UI management commands for the agentic-spec CLI.

This module provides CLI commands to manage the web UI server,
including starting/stopping the server, opening the browser,
checking status, and managing configuration.
"""

import socket
import threading
import time
from typing import Annotated
import webbrowser

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import typer
import uvicorn

from .config import AgenticSpecConfig, get_config_manager, load_config
from .web_ui import DB_PATH
from .web_ui import app as web_app

# Create Typer app
app = typer.Typer(
    name="web",
    help="Web UI management commands",
    rich_markup_mode="rich",
)

console = Console()

# Global server thread reference
_server_thread = None
_server = None


def is_port_in_use(host: str, port: int) -> bool:
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def get_web_config(config: AgenticSpecConfig) -> dict:
    """Extract web UI configuration from main config."""
    # Convert Pydantic model to dict
    return config.web_ui.model_dump()


@app.command()
def start(
    host: Annotated[
        str | None, typer.Option("--host", "-h", help="Host to bind to")
    ] = None,
    port: Annotated[
        int | None, typer.Option("--port", "-p", help="Port to bind to")
    ] = None,
    no_browser: Annotated[
        bool, typer.Option("--no-browser", help="Don't open browser automatically")
    ] = False,
    log_level: Annotated[
        str | None, typer.Option("--log-level", "-l", help="Logging level")
    ] = None,
):
    """Start the web UI server.

    The server runs in the background and can be stopped with 'agentic-spec web stop'.
    """
    global _server_thread, _server

    # Check if server is already running
    if _server_thread and _server_thread.is_alive():
        console.print("[yellow]⚠️  Web UI server is already running[/yellow]")
        return

    # Load configuration
    try:
        config = load_config()
        web_config = get_web_config(config)
    except Exception as e:
        console.print(f"[red]❌ Failed to load configuration: {e}[/red]")
        return

    # Override with command line options
    host = host or web_config["host"]
    port = port or web_config["port"]
    log_level = log_level or web_config["log_level"]
    auto_open = web_config["auto_open_browser"] and not no_browser

    # Check if port is available
    if is_port_in_use(host, port):
        console.print(f"[red]❌ Port {port} is already in use[/red]")
        console.print("[yellow]💡 Try a different port with --port option[/yellow]")
        return

    # Check database exists
    if not DB_PATH.exists():
        console.print("[yellow]⚠️  Database not found at {DB_PATH}[/yellow]")
        console.print(
            "[yellow]💡 Run 'agentic-spec migrate-bulk' to create database[/yellow]"
        )
        return

    # Start server in background thread
    def run_server():
        global _server
        config = uvicorn.Config(
            web_app,
            host=host,
            port=port,
            log_level=log_level,
            access_log=False,
        )
        _server = uvicorn.Server(config)
        _server.run()

    _server_thread = threading.Thread(target=run_server, daemon=True)
    _server_thread.start()

    # Wait a moment for server to start
    time.sleep(1)

    url = f"http://{host}:{port}"

    console.print(
        Panel(
            f"[green]✅ Web UI server started[/green]\n\n"
            f"[bold]URL:[/bold] {url}\n"
            f"[bold]Host:[/bold] {host}\n"
            f"[bold]Port:[/bold] {port}\n\n"
            f"[dim]Press Ctrl+C to stop the server[/dim]",
            title="Web UI Server",
            border_style="green",
        )
    )

    # Open browser if configured
    if auto_open:
        console.print(f"[blue]🌐 Opening browser to {url}...[/blue]")
        webbrowser.open(url)

    # Keep the main thread alive
    try:
        while _server_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]⏹️  Stopping server...[/yellow]")
        if _server:
            _server.should_exit = True
        _server_thread.join(timeout=5)
        console.print("[green]✅ Server stopped[/green]")


@app.command()
def stop():
    """Stop the web UI server."""
    global _server_thread, _server

    if not _server_thread or not _server_thread.is_alive():
        console.print("[yellow]⚠️  Web UI server is not running[/yellow]")
        return

    console.print("[yellow]⏹️  Stopping server...[/yellow]")
    if _server:
        _server.should_exit = True

    _server_thread.join(timeout=5)

    if _server_thread.is_alive():
        console.print("[red]❌ Failed to stop server gracefully[/red]")
    else:
        console.print("[green]✅ Server stopped[/green]")
        _server_thread = None
        _server = None


@app.command()
def status():
    """Check the status of the web UI server."""
    global _server_thread

    # Load configuration to show current settings
    try:
        config = load_config()
        web_config = get_web_config(config)
    except Exception:
        web_config = {
            "host": "127.0.0.1",
            "port": 8000,
            "auto_open_browser": True,
            "log_level": "info",
        }

    # Check if server is running
    is_running = _server_thread and _server_thread.is_alive()

    # Create status table
    table = Table(title="Web UI Server Status", title_style="bold")
    table.add_column("Property", style="cyan")
    table.add_column("Value")

    # Server status
    status_style = "green" if is_running else "red"
    status_text = "Running" if is_running else "Stopped"
    table.add_row("Status", f"[{status_style}]{status_text}[/{status_style}]")

    # Configuration
    table.add_row("Host", web_config["host"])
    table.add_row("Port", str(web_config["port"]))
    table.add_row(
        "Auto-open Browser", "Yes" if web_config["auto_open_browser"] else "No"
    )
    table.add_row("Log Level", web_config["log_level"])

    # Database
    db_exists = DB_PATH.exists()
    db_style = "green" if db_exists else "yellow"
    db_text = "Found" if db_exists else "Not found"
    table.add_row("Database", f"[{db_style}]{db_text}[/{db_style}]")

    if is_running:
        url = f"http://{web_config['host']}:{web_config['port']}"
        table.add_row("URL", f"[link]{url}[/link]")

    console.print(table)

    # Additional hints
    if not is_running:
        console.print("\n[dim]💡 Start the server with 'agentic-spec web start'[/dim]")
    elif not db_exists:
        console.print(
            "\n[yellow]⚠️  Database not found. Run 'agentic-spec migrate-bulk' to create it.[/yellow]"
        )


@app.command()
def open():
    """Open the web UI in the default browser."""
    # Load configuration
    try:
        config = load_config()
        web_config = get_web_config(config)
    except Exception:
        web_config = {"host": "127.0.0.1", "port": 8000}

    url = f"http://{web_config['host']}:{web_config['port']}"

    # Check if server is running by trying to connect
    is_running = not is_port_in_use(web_config["host"], web_config["port"])

    if not is_running:
        console.print("[yellow]⚠️  Web UI server is not running[/yellow]")
        console.print("[yellow]💡 Start it with 'agentic-spec web start'[/yellow]")
        return

    console.print(f"[blue]🌐 Opening browser to {url}...[/blue]")
    webbrowser.open(url)


@app.command()
def config(
    show: Annotated[
        bool, typer.Option("--show", "-s", help="Show current configuration")
    ] = False,
    host: Annotated[str | None, typer.Option("--host", help="Set host address")] = None,
    port: Annotated[int | None, typer.Option("--port", help="Set port number")] = None,
    auto_browser: Annotated[
        bool | None,
        typer.Option("--auto-browser/--no-auto-browser", help="Set auto-open browser"),
    ] = None,
    log_level: Annotated[
        str | None, typer.Option("--log-level", help="Set log level")
    ] = None,
):
    """Configure web UI settings.

    Without options, shows current configuration.
    Use options to update specific settings.
    """
    # Load current configuration
    try:
        config = load_config()
    except Exception as e:
        console.print(f"[red]❌ Failed to load configuration: {e}[/red]")
        return

    # Get current web config
    web_config = get_web_config(config)

    # Update configuration if options provided
    updated = False
    if host is not None:
        web_config["host"] = host
        updated = True
    if port is not None:
        web_config["port"] = port
        updated = True
    if auto_browser is not None:
        web_config["auto_open_browser"] = auto_browser
        updated = True
    if log_level is not None:
        if log_level not in ["debug", "info", "warning", "error", "critical"]:
            console.print(f"[red]❌ Invalid log level: {log_level}[/red]")
            console.print(
                "[yellow]💡 Valid levels: debug, info, warning, error, critical[/yellow]"
            )
            return
        web_config["log_level"] = log_level
        updated = True

    # Save updated configuration
    if updated:
        # Update the web_ui settings
        config.web_ui.host = web_config["host"]
        config.web_ui.port = web_config["port"]
        config.web_ui.auto_open_browser = web_config["auto_open_browser"]
        config.web_ui.log_level = web_config["log_level"]

        try:
            config_manager = get_config_manager()
            config_manager.save_config(config)
            console.print("[green]✅ Configuration updated[/green]")
        except Exception as e:
            console.print(f"[red]❌ Failed to save configuration: {e}[/red]")
            return

    # Display configuration
    table = Table(title="Web UI Configuration", title_style="bold")
    table.add_column("Setting", style="cyan")
    table.add_column("Value")
    table.add_column("Description", style="dim")

    table.add_row("host", web_config["host"], "Host address to bind server")
    table.add_row("port", str(web_config["port"]), "Port number for server")
    table.add_row(
        "auto_open_browser",
        "Yes" if web_config["auto_open_browser"] else "No",
        "Open browser on server start",
    )
    table.add_row("log_level", web_config["log_level"], "Server logging level")

    console.print(table)

    if not updated:
        console.print(
            "\n[dim]💡 Use options to update settings, e.g., --port 8080[/dim]"
        )


if __name__ == "__main__":
    app()
