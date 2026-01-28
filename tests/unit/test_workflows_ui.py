"""
Unit tests for Sprint 49: Workflows Hub UI

Tests the workflows template rendering and route functionality.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


class TestWorkflowsTemplate:
    """Test workflows.html template structure and content."""
    
    def test_template_extends_base(self):
        """Template should extend base.html."""
        with open("src/templates/workflows.html", "r") as f:
            content = f.read()
        assert '{% extends "base.html" %}' in content
    
    def test_template_has_title_block(self):
        """Template should set proper page title."""
        with open("src/templates/workflows.html", "r") as f:
            content = f.read()
        assert "{% block title %}" in content
        assert "Workflows" in content
    
    def test_template_has_category_filter(self):
        """Template should have category filter dropdown."""
        with open("src/templates/workflows.html", "r") as f:
            content = f.read()
        assert 'id="category-filter"' in content
        assert "All Categories" in content
    
    def test_template_has_workflow_list(self):
        """Template should have workflow list container."""
        with open("src/templates/workflows.html", "r") as f:
            content = f.read()
        assert 'id="workflow-list"' in content
        assert "Available Workflows" in content
    
    def test_template_has_workflow_detail(self):
        """Template should have workflow detail panel."""
        with open("src/templates/workflows.html", "r") as f:
            content = f.read()
        assert 'id="workflow-detail"' in content
        assert "Select a workflow" in content
    
    def test_template_has_execution_panel(self):
        """Template should have execution panel for progress display."""
        with open("src/templates/workflows.html", "r") as f:
            content = f.read()
        assert 'id="execution-panel"' in content
        assert "Execution Progress" in content
    
    def test_template_has_input_modal(self):
        """Template should have input modal for workflow execution."""
        with open("src/templates/workflows.html", "r") as f:
            content = f.read()
        assert 'id="input-modal"' in content
        assert 'id="input-form"' in content
        assert "Execute" in content
    
    def test_template_has_step_visualization(self):
        """Template should have step progress visualization."""
        with open("src/templates/workflows.html", "r") as f:
            content = f.read()
        assert 'id="execution-steps"' in content
        assert "step-complete" in content or "step-running" in content
    
    def test_template_has_result_display(self):
        """Template should have execution result display."""
        with open("src/templates/workflows.html", "r") as f:
            content = f.read()
        assert 'id="execution-result"' in content
        assert 'id="execution-output"' in content
        assert "Final Output" in content
    
    def test_template_has_load_functions(self):
        """Template should have JavaScript data loading functions."""
        with open("src/templates/workflows.html", "r") as f:
            content = f.read()
        assert "loadWorkflows" in content
        assert "selectWorkflow" in content
        assert "executeWorkflow" in content
    
    def test_template_api_endpoints(self):
        """Template should call correct API endpoints."""
        with open("src/templates/workflows.html", "r") as f:
            content = f.read()
        assert "/api/gemini/workflows" in content
        assert "/execute" in content
    
    def test_template_has_status_indicator(self):
        """Template should show execution status."""
        with open("src/templates/workflows.html", "r") as f:
            content = f.read()
        assert 'id="execution-status"' in content
        assert "Not Started" in content


class TestWorkflowsRoute:
    """Test workflows route configuration."""
    
    def test_route_exists_in_ui_router(self):
        """Workflows route should be defined in ui.py."""
        with open("src/routes/ui.py", "r") as f:
            content = f.read()
        assert '/caseyos/workflows' in content
        assert 'workflows_hub' in content
    
    def test_route_uses_correct_template(self):
        """Route should render workflows.html template."""
        with open("src/routes/ui.py", "r") as f:
            content = f.read()
        assert 'workflows.html' in content
    
    def test_route_sets_active_tab(self):
        """Route should set active_tab to workflows."""
        with open("src/routes/ui.py", "r") as f:
            content = f.read()
        assert '"active_tab": "workflows"' in content


class TestNavigationLink:
    """Test workflows link in navigation."""
    
    def test_workflows_link_in_nav(self):
        """Base template should have Workflows link in nav."""
        with open("src/templates/base.html", "r") as f:
            content = f.read()
        assert 'href="/caseyos/workflows"' in content
        assert "🔄 Workflows" in content
    
    def test_workflows_active_state(self):
        """Workflows tab should have proper active state styling."""
        with open("src/templates/base.html", "r") as f:
            content = f.read()
        assert "active_tab == 'workflows'" in content


class TestWorkflowExecution:
    """Test workflow execution UI elements."""
    
    def test_template_has_csrf_handling(self):
        """Template should include CSRF token in requests."""
        with open("src/templates/workflows.html", "r") as f:
            content = f.read()
        assert "csrf_token" in content.lower() or "X-CSRF-Token" in content
    
    def test_template_has_error_handling(self):
        """Template should handle execution errors."""
        with open("src/templates/workflows.html", "r") as f:
            content = f.read()
        assert "catch" in content
        assert "error" in content.lower()
    
    def test_template_has_step_states(self):
        """Template should show different step states."""
        with open("src/templates/workflows.html", "r") as f:
            content = f.read()
        assert "pending" in content or "complete" in content
        assert "running" in content or "error" in content


@pytest.mark.skip(reason="Requires database connection")
class TestWorkflowsRouteIntegration:
    """Integration tests requiring app context."""
    
    def test_workflows_route_returns_200(self, client):
        """Workflows page should return 200 status."""
        response = client.get("/caseyos/workflows")
        assert response.status_code == 200
    
    def test_workflows_page_renders_content(self, client):
        """Workflows page should render dashboard content."""
        response = client.get("/caseyos/workflows")
        assert b"Workflows" in response.content
