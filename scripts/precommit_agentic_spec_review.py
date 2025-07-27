#!/usr/bin/env python3
"""
Pre-commit hook wrapper for agentic-spec review.

This script provides cross-platform compatibility for running agentic-spec review
as a pre-commit hook. It ensures proper error handling and exit code propagation.
"""

from pathlib import Path
import subprocess
import sys


def main():
    """Run agentic-spec review and propagate exit code."""
    try:
        # Run agentic-spec review
        result = subprocess.run(
            ["agentic-spec", "review"],
            capture_output=True,
            text=True,
            check=False,  # Don't raise exception on non-zero exit
        )

        # Print output
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="")

        # Check if there are any spec files to review
        specs_dir = Path("specs")
        if not specs_dir.exists() or not any(specs_dir.glob("*.yaml")):
            print("No specification files found to review. Continuing with commit.")
            return 0

        # Exit with the same code as agentic-spec review
        return result.returncode

    except FileNotFoundError:
        print(
            "Error: agentic-spec command not found. "
            "Please ensure the package is installed.",
            file=sys.stderr,
        )
        return 1
    except Exception as e:
        print(f"Error running agentic-spec review: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
