"""Migration: Add task tracking fields
Created: 2025-07-27

Adds progress tracking and approval fields to implementation steps.
"""

from typing import Any


def upgrade(data: dict[str, Any]) -> dict[str, Any]:
    """Add tracking fields to implementation steps."""
    # Add progress and approvals to each implementation step
    if "implementation" in data:
        for step in data["implementation"]:
            if "progress" not in step:
                step["progress"] = None
            if "approvals" not in step:
                step["approvals"] = None

    # Add work_logs to root if not present
    if "work_logs" not in data:
        data["work_logs"] = None

    # Update metadata version
    if "metadata" in data:
        data["metadata"]["schema_version"] = "2.0"

    return data


def downgrade(data: dict[str, Any]) -> dict[str, Any]:
    """Remove tracking fields from implementation steps."""
    # Remove progress and approvals from implementation steps
    if "implementation" in data:
        for step in data["implementation"]:
            step.pop("progress", None)
            step.pop("approvals", None)

    # Remove work_logs from root
    data.pop("work_logs", None)

    # Revert metadata version
    if "metadata" in data:
        data["metadata"]["schema_version"] = "1.0"

    return data
