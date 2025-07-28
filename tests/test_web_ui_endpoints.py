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


# --- New tests for enhanced UI metadata and accessibility ---


def test_skip_link_present():
    """Home page should include a skip navigation link for accessibility."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Skip to main content" in resp.text


SPEC_ID = "ed67766b"
TASK_ID = "ed67766b:0"  # Current spec in fresh database


def test_spec_detail_metadata_rendered():
    """Spec detail page includes new contextual metadata fields."""
    resp = client.get(f"/specs/{SPEC_ID}")
    assert resp.status_code == 200
    html = resp.text
    # Check for injected title text
    assert f"Spec {SPEC_ID}" in html
    # Check for metadata labels
    assert "Created:" in html
    assert "Last Updated:" in html
    assert "Completion:" in html


def test_task_detail_metadata_rendered():
    """Task detail page includes progress timestamps and last updated info."""
    # Encode colon for URL path safety
    from urllib.parse import quote

    encoded_task_id = quote(TASK_ID, safe="")
    resp = client.get(f"/tasks/{encoded_task_id}")
    assert resp.status_code == 200
    html = resp.text
    assert "Started at:" in html
    assert "Last Updated:" in html


# --- Tests for new UX enhancements ---


def test_workflow_visualization_api():
    """Test the new workflow visualization API endpoint."""
    # Use the known spec ID from the test database
    resp = client.get(f"/api/specs/{SPEC_ID}/workflow")
    assert resp.status_code == 200
    data = resp.json()

    # Check required fields
    assert "states" in data
    assert "transitions" in data
    assert "current_state" in data
    assert "task_stats" in data
    assert "completion_percentage" in data

    # Validate states structure
    assert isinstance(data["states"], list)
    if data["states"]:
        state = data["states"][0]
        assert "id" in state
        assert "label" in state
        assert "x" in state
        assert "y" in state

    # Validate task stats structure
    task_stats = data["task_stats"]
    assert "total" in task_stats
    assert "completed" in task_stats
    assert "in_progress" in task_stats
    assert "blocked" in task_stats
    assert "pending" in task_stats


def test_workflow_visualization_nonexistent_spec():
    """Workflow API should return 404 for nonexistent spec."""
    resp = client.get("/api/specs/nonexistent/workflow")
    assert resp.status_code == 404


def test_enhanced_stats_api():
    """Enhanced stats API should include workflow breakdown."""
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()

    # Original fields
    assert "total_specifications" in data
    assert "status_breakdown" in data
    assert "workflow_breakdown" in data
    assert "updated_at" in data

    # Validate structure
    assert isinstance(data["total_specifications"], int)
    assert isinstance(data["status_breakdown"], dict)
    assert isinstance(data["workflow_breakdown"], dict)


def test_specs_list_with_filtering_controls():
    """Specs list page should include new filtering controls."""
    resp = client.get("/specs")
    assert resp.status_code == 200
    html = resp.text

    # Check for filter controls
    assert "workflow-filter" in html
    assert "priority-filter" in html
    assert "sort-by" in html
    assert "Clear Filters" in html

    # Check for status filter badges
    assert "All" in html
    assert "Draft" in html
    assert "Approved" in html
    assert "Implemented" in html


def test_tasks_list_with_sorting():
    """Tasks list page should include new sorting controls."""
    resp = client.get("/tasks")
    assert resp.status_code == 200
    html = resp.text

    # Check for sort controls
    assert "task-sort-by" in html
    assert "Sort By:" in html

    # Check for status filter badges
    assert "Pending" in html
    assert "In Progress" in html
    assert "Completed" in html
    assert "Blocked" in html


def test_dashboard_recent_activity():
    """Dashboard should include recent activity timeline."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    # Check for activity timeline
    assert "Recent Activity" in html
    assert "activity-container" in html

    # Check for stats grid
    assert "stats-grid" in html
    assert "Total Specifications" in html


def test_spec_detail_state_machine():
    """Spec detail page should include state machine visualization."""
    resp = client.get(f"/specs/{SPEC_ID}")
    assert resp.status_code == 200
    html = resp.text

    # Check for state machine components
    assert "Workflow State Machine" in html
    assert "state-machine" in html
    assert "renderWorkflow" in html

    # Check for enhanced layout
    assert "card-header" in html
    assert "progress-bar" in html


def test_visual_hierarchy_elements():
    """Test that visual hierarchy elements are present."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    # Check for CSS classes that provide visual hierarchy
    assert "stat-card" in html
    assert "card" in html

    # Check for status and workflow badges in HTML structure
    # (The actual badges are rendered by JavaScript, but containers should be present)
    resp_specs = client.get("/specs")
    assert resp_specs.status_code == 200
    specs_html = resp_specs.text
    assert "status-badge" in specs_html
    assert "workflow-badge" in specs_html


def test_accessibility_features():
    """Test accessibility enhancements."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    # Check for skip link (already tested but including for completeness)
    assert "Skip to main content" in html

    # Check for ARIA labels and screen reader support
    resp_specs = client.get("/specs")
    specs_html = resp_specs.text
    assert "sr-only" in specs_html or "aria-label" in specs_html


def test_error_handling_preserved():
    """Ensure error handling still works with new UI components."""
    # Test 404 for nonexistent spec
    resp = client.get("/specs/nonexistent-spec-id")
    assert resp.status_code == 404

    # Test 404 for nonexistent task
    resp = client.get("/tasks/nonexistent-task-id")
    assert resp.status_code == 404
