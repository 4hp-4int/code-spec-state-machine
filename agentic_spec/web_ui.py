"""Web UI for viewing specifications and tasks in the database.

This module provides a FastAPI-based web interface for browsing specifications,
tasks, and workflow status stored in the SQLite database.
"""

from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .async_db import AsyncSpecManager, SQLiteBackend
from .models import (
    SpecificationDB,
    TaskDB,
    TaskStatus,
    WorkflowStatus,
    WorkLogDB,
)

# Initialize FastAPI app
app = FastAPI(
    title="Agentic Spec Web UI",
    description="Web interface for viewing specifications and tasks",
    version="1.0.0",
)

# Templates and static files setup
templates = Jinja2Templates(directory="agentic_spec/web_templates")
# Provide `now()` to templates
templates.env.globals["now"] = datetime.now

# -----------------
# Helper utilities
# -----------------


async def build_nav_stats(manager: AsyncSpecManager) -> dict[str, int]:
    """Aggregate quick stats for primary navigation badges (spec and task counts)."""
    specs: list[SpecificationDB] = await manager.backend.list_specifications()
    total_specs = len(specs)
    pending_specs = sum(1 for s in specs if not s.is_completed)

    tasks: list[TaskDB] = []
    for spec in specs:
        tasks.extend(await manager.backend.get_tasks_for_spec(spec.id))

    pending_tasks = sum(
        1 for t in tasks if t.status not in {TaskStatus.COMPLETED, TaskStatus.APPROVED}
    )

    return {
        "total_specs": total_specs,
        "pending_specs": pending_specs,
        "pending_tasks": pending_tasks,
    }


def base_context(request: Request, title: str | None = None) -> dict[str, object]:
    """Return base template context shared across all pages."""
    return {
        "request": request,
        "title": title or "Agentic Spec",
    }


# ----------------------
# Error handling helpers
# ----------------------


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    """Render user-friendly error pages for HTTP errors."""
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "status_code": exc.status_code,
            "detail": exc.detail,
        },
        status_code=exc.status_code,
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    """Fallback handler for unhandled exceptions (returns 500)."""
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "status_code": 500,
            "detail": "Internal Server Error",
        },
        status_code=500,
    )


# Static assets directory (CSS, JS, images)
STATIC_DIR = Path("agentic_spec/web_templates/static")

# Ensure FastAPI can serve static assets from /static
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Global database path (can be configured)
DB_PATH = Path("specs/specifications.db")


async def get_db_manager() -> AsyncSpecManager:
    """Get database manager instance."""
    backend = SQLiteBackend(str(DB_PATH))
    return AsyncSpecManager(backend)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Home page showing overview of specifications."""
    async with await get_db_manager() as manager:
        specs = await manager.backend.list_specifications()

        # Calculate summary statistics
        total_specs = len(specs)
        completed_specs = sum(1 for s in specs if s.is_completed)
        in_progress_specs = sum(
            1 for s in specs if s.workflow_status == WorkflowStatus.IMPLEMENTING
        )

        # Exclude sub-specifications (those with a parent_spec_id)
        top_level_specs = [s for s in specs if not s.parent_spec_id]
        # Sort by updated descending for recency
        top_level_specs.sort(key=lambda s: s.updated, reverse=True)

        ctx = base_context(request, title="Overview")
        ctx.update(
            {
                "total_specs": total_specs,
                "completed_specs": completed_specs,
                "in_progress_specs": in_progress_specs,
                "recent_specs": top_level_specs[:10],
            }
        )
        return templates.TemplateResponse("index.html", ctx)


@app.get("/projects", response_class=HTMLResponse)
async def list_projects(request: Request):
    """List all projects with basic metadata."""
    async with await get_db_manager() as manager:
        specs = await manager.backend.list_specifications()

        # Transform specs into project data with metadata
        projects = []
        for spec in specs:
            projects.append(
                {
                    "id": spec.id,
                    "title": spec.title,
                    "status": spec.status.value,
                    "workflow_status": spec.workflow_status.value,
                    "created": spec.created,
                    "updated": spec.updated,
                    "completion_percentage": spec.completion_percentage,
                    "is_completed": spec.is_completed,
                    "priority": spec.priority,
                    "tags": spec.tags,
                }
            )

        ctx = base_context(request, title="Projects")
        ctx["projects"] = projects
        return templates.TemplateResponse("project_list.html", ctx)


@app.get("/specs", response_class=HTMLResponse)
async def list_specifications(request: Request, status: str | None = None):
    """List all specifications with optional status filtering."""
    async with await get_db_manager() as manager:
        if status:
            # Filter by status if provided
            specs = await manager.backend.list_specifications()
            specs = [s for s in specs if s.status.value == status]
        else:
            specs = await manager.backend.list_specifications()

        ctx = base_context(request, title="Specifications")
        ctx.update({"specs": specs, "current_status": status})
        return templates.TemplateResponse("specs_list.html", ctx)


@app.get("/specs/{spec_id}", response_class=HTMLResponse)
async def view_specification(request: Request, spec_id: str):
    """View detailed specification and its tasks."""
    async with await get_db_manager() as manager:
        spec = await manager.get_specification(spec_id)
        if not spec:
            raise HTTPException(status_code=404, detail="Specification not found")

        tasks = await manager.backend.get_tasks_for_spec(spec_id)

        # Calculate completion percentage
        total_tasks = len(tasks)
        completed_tasks = sum(
            1 for t in tasks if t.status in [TaskStatus.COMPLETED, TaskStatus.APPROVED]
        )
        completion_percentage = (
            (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        )

        ctx = base_context(request, title=f"Spec {spec.id}")
        ctx.update(
            {
                "spec": spec,
                "tasks": tasks,
                "completion_percentage": completion_percentage,
            }
        )
        return templates.TemplateResponse("spec_detail.html", ctx)


@app.get("/tasks", response_class=HTMLResponse)
async def list_tasks(
    request: Request,
    status: str | None = None,
    spec_id: str | None = None,
    project: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
):
    """List tasks with rich filtering.

    Query parameters
    -----------------
    status      : Filter tasks by TaskStatus value (pending, in_progress, etc.)
    spec_id     : Filter tasks belonging to a specific specification
    project     : Filter by specification project context (metadata.project)
    start_date  : ISO date (YYYY-MM-DD) – only include tasks *started* on/after this date
    end_date    : ISO date (YYYY-MM-DD) – only include tasks *started* before/at this date
    """

    # Helper to parse optional ISO dates
    def _parse_date(date_str: str | None) -> datetime | None:
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str)
        except ValueError:
            return None

    start_dt = _parse_date(start_date)
    end_dt = _parse_date(end_date)

    async with await get_db_manager() as manager:
        # Collect candidate tasks
        candidate_tasks: list[TaskDB] = []

        # Option 1 – filter by spec_id first (fast path)
        if spec_id:
            candidate_tasks = await manager.backend.get_tasks_for_spec(spec_id)
        else:
            # Load tasks from every specification (could be optimised later)
            specs: list[SpecificationDB] = await manager.backend.list_specifications()

            # If project filter supplied, narrow specs list by metadata.project
            if project:
                specs = [s for s in specs if s.context.get("project") == project]

            # Fetch tasks for each remaining spec
            for spec in specs:
                spec_tasks = await manager.backend.get_tasks_for_spec(spec.id)
                candidate_tasks.extend(spec_tasks)

        # Apply status filter
        if status:
            candidate_tasks = [t for t in candidate_tasks if t.status.value == status]

        # Apply date range filter (using started_at where available)
        if start_dt:
            candidate_tasks = [
                t for t in candidate_tasks if t.started_at and t.started_at >= start_dt
            ]
        if end_dt:
            candidate_tasks = [
                t for t in candidate_tasks if t.started_at and t.started_at <= end_dt
            ]

        # Sort tasks by started_at desc for convenience
        candidate_tasks.sort(key=lambda t: t.started_at or datetime.min, reverse=True)

        ctx = base_context(request, title="Tasks")
        ctx.update(
            {
                "tasks": candidate_tasks,
                "filters": {
                    "status": status,
                    "spec_id": spec_id,
                    "project": project,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            }
        )
        return templates.TemplateResponse("task_list.html", ctx)


@app.get("/tasks/{task_id}", response_class=HTMLResponse)
async def view_task(request: Request, task_id: str):
    """View detailed task information including approvals and timeline."""
    async with await get_db_manager() as manager:
        task = await manager.backend.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Get approvals for this task
        approvals = await manager.backend.get_approvals_for_task(task_id)

        # Fetch work-log entries (timeline) – newest first
        work_logs: list[WorkLogDB] = await manager.backend.get_work_logs(
            task_id=task_id,
            limit=100,  # safety cap
        )

        # Get the parent specification
        spec = await manager.get_specification(task.spec_id)

        ctx = base_context(request, title=f"Task {task.id}")
        ctx.update(
            {
                "task": task,
                "spec": spec,
                "approvals": approvals,
                "work_logs": work_logs,
            }
        )
        return templates.TemplateResponse("task_detail.html", ctx)


@app.get("/api/stats")
async def get_stats():
    """API endpoint for getting statistics (for dashboard widgets)."""
    async with await get_db_manager() as manager:
        specs = await manager.backend.list_specifications()

        # Count specifications by status
        status_counts = {}
        for spec in specs:
            status = spec.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        # Count specifications by workflow status
        workflow_counts = {}
        for spec in specs:
            workflow_status = spec.workflow_status.value
            workflow_counts[workflow_status] = (
                workflow_counts.get(workflow_status, 0) + 1
            )

        return {
            "total_specifications": len(specs),
            "status_breakdown": status_counts,
            "workflow_breakdown": workflow_counts,
            "updated_at": datetime.now().isoformat(),
        }


@app.get("/api/specs/{spec_id}/workflow")
async def get_workflow_visualization(spec_id: str):
    """API endpoint for workflow state machine visualization data."""
    async with await get_db_manager() as manager:
        spec = await manager.get_specification(spec_id)
        if not spec:
            raise HTTPException(status_code=404, detail="Specification not found")

        tasks = await manager.backend.get_tasks_for_spec(spec_id)

        # Define workflow states and transitions
        states = [
            {"id": "created", "label": "Created", "x": 100, "y": 100},
            {"id": "planning", "label": "Planning", "x": 300, "y": 100},
            {"id": "implementing", "label": "Implementing", "x": 500, "y": 100},
            {"id": "reviewing", "label": "Reviewing", "x": 700, "y": 100},
            {"id": "completed", "label": "Completed", "x": 900, "y": 100},
        ]

        # Define transitions between states
        transitions = [
            {"from": "created", "to": "planning"},
            {"from": "planning", "to": "implementing"},
            {"from": "implementing", "to": "reviewing"},
            {"from": "reviewing", "to": "completed"},
            {"from": "reviewing", "to": "implementing"},  # Feedback loop
        ]

        # Current state and task progress
        current_state = spec.workflow_status.value

        # Task breakdown by status
        task_stats = {
            "total": len(tasks),
            "completed": sum(
                1
                for t in tasks
                if t.status in [TaskStatus.COMPLETED, TaskStatus.APPROVED]
            ),
            "in_progress": sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS),
            "blocked": sum(1 for t in tasks if t.status == TaskStatus.BLOCKED),
            "pending": sum(1 for t in tasks if t.status == TaskStatus.PENDING),
        }

        return {
            "states": states,
            "transitions": transitions,
            "current_state": current_state,
            "task_stats": task_stats,
            "completion_percentage": spec.completion_percentage,
        }


if __name__ == "__main__":
    import uvicorn

    # Run the web UI server
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
