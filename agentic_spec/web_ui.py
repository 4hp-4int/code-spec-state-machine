"""Web UI for viewing specifications and tasks in the database.

This module provides a FastAPI-based web interface for browsing specifications,
tasks, and workflow status stored in the SQLite database.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .async_db import AsyncSpecManager, SQLiteBackend
from .models import SpecificationDB, TaskDB, TaskStatus, WorkflowStatus


# Initialize FastAPI app
app = FastAPI(
    title="Agentic Spec Web UI",
    description="Web interface for viewing specifications and tasks",
    version="1.0.0",
)

# Templates and static files setup
templates = Jinja2Templates(directory="agentic_spec/web_templates")

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
        specs = await manager.backend.list_specifications(limit=20)
        
        # Calculate summary statistics
        total_specs = len(specs)
        completed_specs = sum(1 for s in specs if s.is_completed)
        in_progress_specs = sum(1 for s in specs if s.workflow_status == WorkflowStatus.IMPLEMENTING)
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "total_specs": total_specs,
            "completed_specs": completed_specs,
            "in_progress_specs": in_progress_specs,
            "recent_specs": specs[:10],
        })


@app.get("/projects", response_class=HTMLResponse)
async def list_projects(request: Request):
    """List all projects with basic metadata."""
    async with await get_db_manager() as manager:
        specs = await manager.backend.list_specifications()
        
        # Transform specs into project data with metadata
        projects = []
        for spec in specs:
            projects.append({
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
            })
        
        return templates.TemplateResponse("project_list.html", {
            "request": request,
            "projects": projects,
        })


@app.get("/specs", response_class=HTMLResponse)
async def list_specifications(request: Request, status: Optional[str] = None):
    """List all specifications with optional status filtering."""
    async with await get_db_manager() as manager:
        if status:
            # Filter by status if provided
            specs = await manager.backend.list_specifications()
            specs = [s for s in specs if s.status.value == status]
        else:
            specs = await manager.backend.list_specifications()
        
        return templates.TemplateResponse("specs_list.html", {
            "request": request,
            "specs": specs,
            "current_status": status,
        })


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
        completed_tasks = sum(1 for t in tasks if t.status in [TaskStatus.COMPLETED, TaskStatus.APPROVED])
        completion_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        return templates.TemplateResponse("spec_detail.html", {
            "request": request,
            "spec": spec,
            "tasks": tasks,
            "completion_percentage": completion_percentage,
        })


@app.get("/tasks", response_class=HTMLResponse)
async def list_tasks(request: Request, status: Optional[str] = None, spec_id: Optional[str] = None):
    """List tasks with optional filtering by status or specification."""
    async with await get_db_manager() as manager:
        if spec_id:
            tasks = await manager.backend.get_tasks_for_spec(spec_id)
        else:
            # Get all tasks (we'll need to implement a method for this)
            specs = await manager.backend.list_specifications()
            tasks = []
            for spec in specs:
                spec_tasks = await manager.backend.get_tasks_for_spec(spec.id)
                tasks.extend(spec_tasks)
        
        # Filter by status if provided
        if status:
            tasks = [t for t in tasks if t.status.value == status]
        
        return templates.TemplateResponse("tasks_list.html", {
            "request": request,
            "tasks": tasks,
            "current_status": status,
            "current_spec": spec_id,
        })


@app.get("/tasks/{task_id}", response_class=HTMLResponse)
async def view_task(request: Request, task_id: str):
    """View detailed task information including approvals and timeline."""
    async with await get_db_manager() as manager:
        task = await manager.backend.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Get approvals for this task
        approvals = await manager.backend.get_approvals_for_task(task_id)
        
        # Get the parent specification
        spec = await manager.get_specification(task.spec_id)
        
        return templates.TemplateResponse("task_detail.html", {
            "request": request,
            "task": task,
            "spec": spec,
            "approvals": approvals,
        })


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
            workflow_counts[workflow_status] = workflow_counts.get(workflow_status, 0) + 1
        
        return {
            "total_specifications": len(specs),
            "status_breakdown": status_counts,
            "workflow_breakdown": workflow_counts,
            "updated_at": datetime.now().isoformat(),
        }


if __name__ == "__main__":
    import uvicorn
    
    # Run the web UI server
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")