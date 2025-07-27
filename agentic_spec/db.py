"""File-based storage operations for specifications with database-like functionality."""

from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import tempfile
from typing import Any

import yaml

from .exceptions import SpecificationError
from .models import (
    ApprovalLevel,
    ApprovalRecord,
    ProgrammingSpec,
    TaskProgress,
    TaskStatus,
    WorkLogEntry,
)


class FileBasedSpecStorage:
    """File-based storage for specifications with database-like operations."""

    def __init__(self, specs_dir: Path | str = "specs"):
        self.specs_dir = Path(specs_dir)
        self.specs_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.specs_dir / ".spec_index.json"
        self._ensure_index()

    def _ensure_index(self) -> None:
        """Ensure specification index exists."""
        if not self.index_file.exists():
            self._rebuild_index()

    def _rebuild_index(self) -> None:
        """Rebuild the specification index from YAML files."""
        index = {"specs": {}, "last_updated": datetime.now().isoformat()}

        for yaml_file in self.specs_dir.glob("*.yaml"):
            try:
                with open(yaml_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                if data and "metadata" in data:
                    spec_id = data["metadata"]["id"]
                    index["specs"][spec_id] = {
                        "file": yaml_file.name,
                        "title": data["metadata"]["title"],
                        "status": data["metadata"]["status"],
                        "created": data["metadata"]["created"],
                        "parent_spec_id": data["metadata"].get("parent_spec_id"),
                        "child_spec_ids": data["metadata"].get("child_spec_ids", []),
                    }
            except Exception:
                # Skip invalid files
                continue

        self._save_index(index)

    def _load_index(self) -> dict[str, Any]:
        """Load the specification index."""
        if self.index_file.exists():
            with open(self.index_file, encoding="utf-8") as f:
                return json.load(f)
        return {"specs": {}, "last_updated": None}

    def _save_index(self, index: dict[str, Any]) -> None:
        """Save the specification index."""
        index["last_updated"] = datetime.now().isoformat()
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2)

    def _atomic_write(self, filepath: Path, data: dict[str, Any]) -> None:
        """Atomically write YAML data to file."""
        # Create temporary file in same directory for atomic rename
        temp_fd, temp_path = tempfile.mkstemp(
            dir=filepath.parent, suffix=".tmp", text=True
        )

        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)

            # Atomic rename (works on Windows and Unix)
            os.replace(temp_path, filepath)
        except Exception:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise

    def save_spec(self, spec: ProgrammingSpec) -> Path:
        """Save a specification to YAML file."""
        filename = f"{datetime.now().strftime('%Y-%m-%d')}-{spec.metadata.id}.yaml"
        filepath = self.specs_dir / filename

        # Convert to dict and save atomically
        data = spec.to_dict()
        self._atomic_write(filepath, data)

        # Update index
        index = self._load_index()
        index["specs"][spec.metadata.id] = {
            "file": filename,
            "title": spec.metadata.title,
            "status": spec.metadata.status,
            "created": spec.metadata.created,
            "parent_spec_id": spec.metadata.parent_spec_id,
            "child_spec_ids": spec.metadata.child_spec_ids or [],
        }
        self._save_index(index)

        return filepath

    def load_spec(self, spec_id: str) -> ProgrammingSpec:
        """Load a specification by ID."""
        index = self._load_index()

        if spec_id not in index["specs"]:
            raise SpecificationError(f"Specification {spec_id} not found")

        spec_info = index["specs"][spec_id]
        filepath = self.specs_dir / spec_info["file"]

        if not filepath.exists():
            # Try to rebuild index if file is missing
            self._rebuild_index()
            raise SpecificationError(f"Specification file {filepath} not found")

        with open(filepath, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return ProgrammingSpec.from_dict(data)

    def update_task_progress(
        self,
        spec_id: str,
        step_id: str,
        status: TaskStatus,
        notes: str | None = None,
        blockers: list[str] | None = None,
    ) -> None:
        """Update task progress for a specific step."""
        spec = self.load_spec(spec_id)

        # Find the step
        step_index = None
        for i, step in enumerate(spec.implementation):
            if step.step_id == step_id:
                step_index = i
                break

        if step_index is None:
            raise SpecificationError(f"Step {step_id} not found in spec {spec_id}")

        step = spec.implementation[step_index]

        # Initialize progress if needed
        if not step.progress:
            step.progress = TaskProgress()

        # Update progress
        old_status = step.progress.status
        step.progress.status = status

        if status == TaskStatus.IN_PROGRESS and not step.progress.started_at:
            step.progress.started_at = datetime.now()
        elif status in (TaskStatus.COMPLETED, TaskStatus.APPROVED):
            if not step.progress.completed_at:
                step.progress.completed_at = datetime.now()
            if step.progress.started_at:
                duration = (
                    step.progress.completed_at - step.progress.started_at
                ).total_seconds() / 60
                step.progress.time_spent_minutes = int(duration)

        if notes:
            step.progress.completion_notes = notes
        if blockers:
            step.progress.blockers = blockers

        # Add work log entry
        if not spec.work_logs:
            spec.work_logs = []

        log_entry = WorkLogEntry(
            spec_id=spec_id,
            step_id=step_id,
            action=f"status_changed_{old_status}_to_{status.value}",
            timestamp=datetime.now(),
            duration_minutes=step.progress.time_spent_minutes,
            notes=notes,
        )
        spec.work_logs.append(log_entry)

        # Save updated spec
        self.save_spec(spec)

    def add_approval(
        self,
        spec_id: str,
        step_id: str,
        level: ApprovalLevel,
        approved_by: str,
        comments: str | None = None,
        override_reason: str | None = None,
    ) -> None:
        """Add approval record to a task."""
        spec = self.load_spec(spec_id)

        # Find the step
        step = None
        for s in spec.implementation:
            if s.step_id == step_id:
                step = s
                break

        if not step:
            raise SpecificationError(f"Step {step_id} not found in spec {spec_id}")

        # Initialize approvals if needed
        if not step.approvals:
            step.approvals = []

        # Add approval
        approval = ApprovalRecord(
            level=level,
            approved_by=approved_by,
            approved_at=datetime.now(),
            comments=comments,
            override_reason=override_reason,
        )
        step.approvals.append(approval)

        # Update task status to approved if appropriate
        if step.progress and step.progress.status == TaskStatus.COMPLETED:
            step.progress.status = TaskStatus.APPROVED

        # Add work log
        if not spec.work_logs:
            spec.work_logs = []

        log_entry = WorkLogEntry(
            spec_id=spec_id,
            step_id=step_id,
            action=f"approved_{level.value}",
            timestamp=datetime.now(),
            notes=f"Approved by {approved_by}" + (f": {comments}" if comments else ""),
            metadata={"approval_level": level.value, "override": bool(override_reason)},
        )
        spec.work_logs.append(log_entry)

        # Save updated spec
        self.save_spec(spec)

    def query_work_logs(
        self,
        spec_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        action_filter: str | None = None,
    ) -> list[WorkLogEntry]:
        """Query work logs across specifications."""
        logs = []

        if spec_id:
            # Query specific spec
            try:
                spec = self.load_spec(spec_id)
                if spec.work_logs:
                    logs.extend(spec.work_logs)
            except SpecificationError:
                return []
        else:
            # Query all specs
            index = self._load_index()
            for sid in index["specs"]:
                try:
                    spec = self.load_spec(sid)
                    if spec.work_logs:
                        logs.extend(spec.work_logs)
                except Exception:
                    continue

        # Apply filters
        if start_date:
            logs = [log for log in logs if log.timestamp >= start_date]
        if end_date:
            logs = [log for log in logs if log.timestamp <= end_date]
        if action_filter:
            logs = [log for log in logs if action_filter in log.action]

        # Sort by timestamp
        logs.sort(key=lambda l: l.timestamp, reverse=True)

        return logs

    def get_task_status_summary(self, spec_id: str) -> dict[str, Any]:
        """Get summary of task statuses for a specification."""
        spec = self.load_spec(spec_id)

        summary = {
            "total_tasks": len(spec.implementation),
            "by_status": {
                "pending": 0,
                "in_progress": 0,
                "completed": 0,
                "blocked": 0,
                "approved": 0,
                "rejected": 0,
            },
            "completion_percentage": 0,
            "blocked_tasks": [],
            "in_progress_tasks": [],
        }

        for step in spec.implementation:
            if step.progress:
                status = step.progress.status.value
                summary["by_status"][status] += 1

                if status == "blocked":
                    summary["blocked_tasks"].append(
                        {
                            "step_id": step.step_id,
                            "task": step.task,
                            "blockers": step.progress.blockers,
                        }
                    )
                elif status == "in_progress":
                    summary["in_progress_tasks"].append(
                        {
                            "step_id": step.step_id,
                            "task": step.task,
                            "started_at": step.progress.started_at,
                        }
                    )
            else:
                summary["by_status"]["pending"] += 1

        # Calculate completion percentage
        completed = summary["by_status"]["completed"] + summary["by_status"]["approved"]
        if summary["total_tasks"] > 0:
            summary["completion_percentage"] = (
                completed / summary["total_tasks"]
            ) * 100

        return summary

    def export_work_history(
        self,
        format: str = "markdown",
        spec_id: str | None = None,
        output_file: Path | None = None,
    ) -> str:
        """Export work history in various formats."""
        logs = self.query_work_logs(spec_id=spec_id)

        if format == "markdown":
            content = self._export_markdown(logs, spec_id)
        elif format == "csv":
            content = self._export_csv(logs)
        elif format == "json":
            content = self._export_json(logs)
        else:
            raise ValueError(f"Unsupported export format: {format}")

        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(content)

        return content

    def _export_markdown(self, logs: list[WorkLogEntry], spec_id: str | None) -> str:
        """Export logs as Markdown."""
        lines = ["# Work History Report", ""]

        if spec_id:
            lines.append(f"**Specification:** {spec_id}")

        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Total Entries:** {len(logs)}")
        lines.append("")

        if logs:
            lines.append("## Work Log Entries")
            lines.append("")

            current_date = None
            for log in logs:
                log_date = log.timestamp.date()
                if log_date != current_date:
                    current_date = log_date
                    lines.append(f"### {log_date.strftime('%Y-%m-%d')}")
                    lines.append("")

                time_str = log.timestamp.strftime("%H:%M:%S")
                duration_str = (
                    f" ({log.duration_minutes}m)" if log.duration_minutes else ""
                )

                lines.append(
                    f"- **{time_str}** [{log.spec_id}:{log.step_id}] {log.action}{duration_str}"
                )

                if log.notes:
                    lines.append(f"  - {log.notes}")

                lines.append("")

        return "\n".join(lines)

    def _export_csv(self, logs: list[WorkLogEntry]) -> str:
        """Export logs as CSV."""
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(
            [
                "Timestamp",
                "Spec ID",
                "Step ID",
                "Action",
                "Duration (min)",
                "Notes",
                "Metadata",
            ]
        )

        # Data
        for log in logs:
            writer.writerow(
                [
                    log.timestamp.isoformat(),
                    log.spec_id,
                    log.step_id,
                    log.action,
                    log.duration_minutes or "",
                    log.notes or "",
                    json.dumps(log.metadata) if log.metadata else "",
                ]
            )

        return output.getvalue()

    def _export_json(self, logs: list[WorkLogEntry]) -> str:
        """Export logs as JSON."""
        data = {
            "export_date": datetime.now().isoformat(),
            "total_entries": len(logs),
            "logs": [log.model_dump(mode="json") for log in logs],
        }
        return json.dumps(data, indent=2, default=str)
