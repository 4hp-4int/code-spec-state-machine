"""Prompt editing functionality with cross-platform editor support."""

import os
from pathlib import Path
import platform
import subprocess
import tempfile

from agentic_spec.exceptions import ConfigurationError


class PromptEditor:
    """Handle prompt editing using system editors."""

    def __init__(self, config_dir: Path | None = None):
        """Initialize the prompt editor.

        Args:
            config_dir: Directory containing configuration files and templates
        """
        self.config_dir = config_dir or Path.cwd()
        self.prompt_templates_dir = self.config_dir / "prompt-templates"
        self.spec_templates_dir = self.config_dir / "spec-templates"
        # Legacy fallback
        self.legacy_templates_dir = self.config_dir / "templates"

    def edit_prompt(self, name: str) -> str:
        """Edit a prompt file using the system editor.

        Args:
            name: Name of the prompt to edit (without extension)

        Returns:
            Updated prompt content

        Raises:
            ConfigurationError: If editor cannot be found or launched
            FileNotFoundError: If prompt file doesn't exist
        """
        prompt_file = self._find_prompt_file(name)
        if not prompt_file:
            # Create new prompt file
            prompt_file = self._create_new_prompt_file(name)

        # Read current content
        original_content = (
            prompt_file.read_text(encoding="utf-8") if prompt_file.exists() else ""
        )

        # Create temporary file for editing
        with tempfile.NamedTemporaryFile(
            mode="w+",
            suffix=".md",
            prefix=f"agentic_spec_prompt_{name}_",
            delete=False,
            encoding="utf-8",
        ) as temp_file:
            temp_file.write(original_content)
            temp_path = Path(temp_file.name)

        try:
            # Launch editor
            self._launch_editor(temp_path)

            # Read edited content
            edited_content = temp_path.read_text(encoding="utf-8")

            # Only save if content changed
            if edited_content != original_content:
                prompt_file.parent.mkdir(parents=True, exist_ok=True)
                prompt_file.write_text(edited_content, encoding="utf-8")

            return edited_content

        finally:
            # Clean up temporary file
            try:
                temp_path.unlink()
            except (OSError, FileNotFoundError):
                pass  # Ignore cleanup failures

    def _find_prompt_file(self, name: str) -> Path | None:
        """Find existing prompt file by name.

        Args:
            name: Name of prompt to find

        Returns:
            Path to prompt file or None if not found
        """
        # Check common locations and extensions
        search_paths = [
            self.prompt_templates_dir / f"{name}.md",
            self.prompt_templates_dir / f"{name}.txt",
            self.spec_templates_dir / f"{name}.md",
            self.spec_templates_dir / f"{name}.txt",
            self.legacy_templates_dir / f"{name}.md",
            self.legacy_templates_dir / f"{name}.txt",
            self.config_dir / f"{name}.md",
            self.config_dir / f"{name}.txt",
        ]

        for path in search_paths:
            if path.exists() and path.is_file():
                return path

        return None

    def _create_new_prompt_file(self, name: str) -> Path:
        """Create path for new prompt file.

        Args:
            name: Name of new prompt

        Returns:
            Path where new prompt will be created
        """
        return self.prompt_templates_dir / f"{name}.md"

    def _launch_editor(self, file_path: Path) -> None:
        """Launch system editor for the given file.

        Args:
            file_path: Path to file to edit

        Raises:
            ConfigurationError: If editor cannot be launched
        """
        system = platform.system().lower()

        try:
            if system == "windows":
                self._launch_editor_windows(file_path)
            elif system == "darwin":  # macOS
                self._launch_editor_macos(file_path)
            else:  # Linux and other Unix-like systems
                self._launch_editor_unix(file_path)
        except (subprocess.SubprocessError, OSError, FileNotFoundError) as e:
            raise ConfigurationError(
                f"Failed to launch editor for {file_path}: {e}"
            ) from e

    def _launch_editor_windows(self, file_path: Path) -> None:
        """Launch editor on Windows.

        Args:
            file_path: Path to file to edit
        """
        editor = os.environ.get("EDITOR")

        if editor:
            # Use specified editor
            subprocess.run([editor, str(file_path)], check=True)
        else:
            # Fall back to default system editor
            os.startfile(str(file_path))  # type: ignore[attr-defined]

    def _launch_editor_macos(self, file_path: Path) -> None:
        """Launch editor on macOS.

        Args:
            file_path: Path to file to edit
        """
        editor = os.environ.get("EDITOR")

        if editor:
            # Use specified editor
            subprocess.run([editor, str(file_path)], check=True)
        else:
            # Use default application
            subprocess.run(["open", "-t", str(file_path)], check=True)

    def _launch_editor_unix(self, file_path: Path) -> None:
        """Launch editor on Unix-like systems.

        Args:
            file_path: Path to file to edit
        """
        editor = os.environ.get("EDITOR")

        if editor:
            # Use specified editor
            subprocess.run([editor, str(file_path)], check=True)
        else:
            # Try common editors or fall back to xdg-open
            common_editors = ["nano", "vim", "vi", "emacs"]

            for editor_cmd in common_editors:
                try:
                    subprocess.run([editor_cmd, str(file_path)], check=True)
                    return
                except (subprocess.SubprocessError, FileNotFoundError):
                    continue

            # Fall back to system default
            subprocess.run(["xdg-open", str(file_path)], check=True)

    def list_prompts(self) -> list[str]:
        """List all available prompts.

        Returns:
            List of prompt names (without extensions)
        """
        prompts = set()

        # Search in prompt templates directory
        if self.prompt_templates_dir.exists():
            for file_path in self.prompt_templates_dir.glob("*.md"):
                prompts.add(file_path.stem)
            for file_path in self.prompt_templates_dir.glob("*.txt"):
                prompts.add(file_path.stem)

        # Search in legacy templates directory for prompt-like files
        if self.legacy_templates_dir.exists():
            for file_path in self.legacy_templates_dir.glob("*.md"):
                if "prompt" in file_path.name.lower():
                    prompts.add(file_path.stem)

        return sorted(prompts)
