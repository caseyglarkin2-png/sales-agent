"""
Unit tests for Sprint 51: Admin & Ops Dashboard UI

Tests the admin dashboard template rendering and route functionality.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


class TestAdminTemplate:
    """Test admin.html template structure and content."""
    
    def test_template_extends_base(self):
        """Template should extend base.html."""
        with open("src/templates/admin.html", "r") as f:
            content = f.read()
        assert '{% extends "base.html" %}' in content
    
    def test_template_has_title_block(self):
        """Template should set proper page title."""
        with open("src/templates/admin.html", "r") as f:
            content = f.read()
        assert "{% block title %}" in content
        assert "Admin" in content
    
    def test_template_has_health_overview(self):
        """Template should have system health overview cards."""
        with open("src/templates/admin.html", "r") as f:
            content = f.read()
        assert 'id="system-health"' in content
        assert 'id="system-status-text"' in content
        assert "System Status" in content
    
    def test_template_has_queue_stats(self):
        """Template should display queue statistics."""
        with open("src/templates/admin.html", "r") as f:
            content = f.read()
        assert 'id="queue-count"' in content
        assert "Queue Items" in content
    
    def test_template_has_ops_mode(self):
        """Template should show operations mode."""
        with open("src/templates/admin.html", "r") as f:
            content = f.read()
        assert 'id="ops-mode"' in content
        assert "Operations Mode" in content
    
    def test_template_has_celery_tasks(self):
        """Template should have Celery tasks panel."""
        with open("src/templates/admin.html", "r") as f:
            content = f.read()
        assert 'id="celery-tasks"' in content
        assert "Celery Tasks" in content
    
    def test_template_has_database_stats(self):
        """Template should have database stats panel."""
        with open("src/templates/admin.html", "r") as f:
            content = f.read()
        assert 'id="database-stats"' in content
        assert "Database Stats" in content
    
    def test_template_has_approved_recipients(self):
        """Template should have approved recipients list."""
        with open("src/templates/admin.html", "r") as f:
            content = f.read()
        assert 'id="recipients-list"' in content
        assert "Approved Recipients" in content
    
    def test_template_has_activity_log(self):
        """Template should have recent activity log."""
        with open("src/templates/admin.html", "r") as f:
            content = f.read()
        assert 'id="activity-log"' in content
        assert "Recent Activity" in content
    
    def test_template_has_quick_actions(self):
        """Template should have quick action buttons."""
        with open("src/templates/admin.html", "r") as f:
            content = f.read()
        assert "Quick Actions" in content
        assert "Poll Signals" in content
        assert "Refresh Tokens" in content
        assert "Health Check" in content
    
    def test_template_has_auto_refresh(self):
        """Template should have auto-refresh functionality."""
        with open("src/templates/admin.html", "r") as f:
            content = f.read()
        assert "setInterval" in content
        assert "refreshAll" in content
        assert 'id="last-refresh"' in content
    
    def test_template_api_endpoints(self):
        """Template should call correct API endpoints."""
        with open("src/templates/admin.html", "r") as f:
            content = f.read()
        assert "/health/status" in content
        assert "/api/admin/emergency-status" in content
        assert "/api/admin/approved-recipients" in content
        assert "/api/command-queue" in content


class TestAdminRoute:
    """Test admin route configuration."""
    
    def test_route_exists_in_ui_router(self):
        """Admin route should be defined in ui.py."""
        with open("src/routes/ui.py", "r") as f:
            content = f.read()
        assert '/caseyos/admin' in content
        assert 'admin_dashboard' in content
    
    def test_route_uses_correct_template(self):
        """Route should render admin.html template."""
        with open("src/routes/ui.py", "r") as f:
            content = f.read()
        assert 'admin.html' in content
    
    def test_route_sets_active_tab(self):
        """Route should set active_tab to admin."""
        with open("src/routes/ui.py", "r") as f:
            content = f.read()
        assert '"active_tab": "admin"' in content


class TestNavigationLink:
    """Test admin link in navigation."""
    
    def test_admin_link_in_nav(self):
        """Base template should have Admin link in nav."""
        with open("src/templates/base.html", "r") as f:
            content = f.read()
        assert 'href="/caseyos/admin"' in content
        assert "👑 Admin" in content
    
    def test_admin_active_state(self):
        """Admin tab should have proper active state styling."""
        with open("src/templates/base.html", "r") as f:
            content = f.read()
        assert "active_tab == 'admin'" in content


class TestAdminFunctions:
    """Test admin JavaScript functions."""
    
    def test_template_has_load_functions(self):
        """Template should have data loading functions."""
        with open("src/templates/admin.html", "r") as f:
            content = f.read()
        assert "loadSystemHealth" in content
        assert "loadQueueStats" in content
        assert "loadCeleryTasks" in content
        assert "loadDatabaseStats" in content
        assert "loadApprovedRecipients" in content
        assert "loadRecentActivity" in content
    
    def test_template_has_action_functions(self):
        """Template should have quick action functions."""
        with open("src/templates/admin.html", "r") as f:
            content = f.read()
        assert "triggerSignalPoll" in content
        assert "refreshTokens" in content
        assert "seedRules" in content
        assert "runHealthCheck" in content
    
    def test_template_has_recipient_management(self):
        """Template should have recipient management functions."""
        with open("src/templates/admin.html", "r") as f:
            content = f.read()
        assert "removeRecipient" in content
    
    def test_template_has_api_docs_link(self):
        """Template should link to API docs."""
        with open("src/templates/admin.html", "r") as f:
            content = f.read()
        assert "viewApiDocs" in content
        assert "/docs" in content


@pytest.mark.skip(reason="Requires database connection")
class TestAdminRouteIntegration:
    """Integration tests requiring app context."""
    
    def test_admin_route_returns_200(self, client):
        """Admin page should return 200 status."""
        response = client.get("/caseyos/admin")
        assert response.status_code == 200
    
    def test_admin_page_renders_content(self, client):
        """Admin page should render dashboard content."""
        response = client.get("/caseyos/admin")
        assert b"Admin" in response.content
