"""Integration tests for FastAPI web UI endpoints.

These tests hit the FastAPI app defined in agentic_spec.web_ui to ensure
routes are mounted, templates render, and error handlers work.

They rely on the pre-populated SQLite database at specs/specifications.db.
"""

from fastapi.testclient import TestClient
import pytest

# Ensure app uses correct DB path before import (if needed)
# Import web UI after potential environment tweaks
from agentic_spec import web_ui

app = web_ui.app
client = TestClient(app)


@pytest.mark.parametrize("url", ["/", "/projects", "/tasks"])  # basic pages
def test_basic_pages_load(url):
    resp = client.get(url)
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_task_filtering():
    """/tasks endpoint should accept status filter without crashing."""
    resp = client.get("/tasks", params={"status": "pending"})
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_nonexistent_task():
    """Requesting an unknown task_id should return custom 404 page."""
    resp = client.get("/tasks/does-not-exist")
    assert resp.status_code == 404
    assert "Error 404" in resp.text


def test_stats_api():
    """/api/stats should return JSON with expected keys."""
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_specifications" in data
    assert "status_breakdown" in data
    assert "workflow_breakdown" in data
