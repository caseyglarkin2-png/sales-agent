"""
Unit tests for Sprint 50: Settings & Configuration UI

Tests the settings template rendering and route functionality.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


class TestSettingsTemplate:
    """Test settings.html template structure and content."""
    
    def test_template_extends_base(self):
        """Template should extend base.html."""
        with open("src/templates/settings.html", "r") as f:
            content = f.read()
        assert '{% extends "base.html" %}' in content
    
    def test_template_has_title_block(self):
        """Template should set proper page title."""
        with open("src/templates/settings.html", "r") as f:
            content = f.read()
        assert "{% block title %}" in content
        assert "Settings" in content
    
    def test_template_has_tabs(self):
        """Template should have settings tabs."""
        with open("src/templates/settings.html", "r") as f:
            content = f.read()
        assert 'data-tab="general"' in content
        assert 'data-tab="operations"' in content
        assert 'data-tab="rules"' in content
        assert 'data-tab="notifications"' in content
        assert 'data-tab="danger"' in content
    
    def test_template_has_general_tab(self):
        """Template should have general settings tab content."""
        with open("src/templates/settings.html", "r") as f:
            content = f.read()
        assert 'id="tab-general"' in content
        assert "System Status" in content
        assert "Connectors" in content
    
    def test_template_has_operations_tab(self):
        """Template should have operations mode tab content."""
        with open("src/templates/settings.html", "r") as f:
            content = f.read()
        assert 'id="tab-operations"' in content
        assert "Operation Mode" in content
        assert "Draft Only" in content
        assert "Send Mode" in content
    
    def test_template_has_rate_limits(self):
        """Template should have rate limit configuration."""
        with open("src/templates/settings.html", "r") as f:
            content = f.read()
        assert "Rate Limits" in content
        assert 'id="rate-hourly"' in content
        assert 'id="rate-daily"' in content
    
    def test_template_has_rules_tab(self):
        """Template should have auto-approval rules tab."""
        with open("src/templates/settings.html", "r") as f:
            content = f.read()
        assert 'id="tab-rules"' in content
        assert "Auto-Approval Rules" in content
        assert 'id="rules-list"' in content
    
    def test_template_has_notifications_tab(self):
        """Template should have notification preferences tab."""
        with open("src/templates/settings.html", "r") as f:
            content = f.read()
        assert 'id="tab-notifications"' in content
        assert "Notification Preferences" in content
        assert 'id="notify-signals"' in content
        assert 'id="notify-approvals"' in content
    
    def test_template_has_danger_zone(self):
        """Template should have danger zone tab."""
        with open("src/templates/settings.html", "r") as f:
            content = f.read()
        assert 'id="tab-danger"' in content
        assert "Danger Zone" in content
        assert "Emergency Stop" in content
    
    def test_template_has_emergency_controls(self):
        """Template should have emergency stop and resume controls."""
        with open("src/templates/settings.html", "r") as f:
            content = f.read()
        assert "emergencyStop" in content
        assert "resumeOperations" in content
        assert 'id="emergency-btn"' in content
    
    def test_template_has_toggle_switches(self):
        """Template should have styled toggle switches."""
        with open("src/templates/settings.html", "r") as f:
            content = f.read()
        assert "toggle-switch" in content
        assert "toggle-slider" in content
    
    def test_template_api_endpoints(self):
        """Template should call correct API endpoints."""
        with open("src/templates/settings.html", "r") as f:
            content = f.read()
        assert "/health/status" in content
        assert "/api/admin/emergency-status" in content
        assert "/api/admin/rules" in content
        assert "/api/admin/emergency-stop" in content


class TestSettingsRoute:
    """Test settings route configuration."""
    
    def test_route_exists_in_ui_router(self):
        """Settings route should be defined in ui.py."""
        with open("src/routes/ui.py", "r") as f:
            content = f.read()
        assert '/caseyos/settings' in content
        assert 'settings_page' in content
    
    def test_route_uses_correct_template(self):
        """Route should render settings.html template."""
        with open("src/routes/ui.py", "r") as f:
            content = f.read()
        assert 'settings.html' in content
    
    def test_route_sets_active_tab(self):
        """Route should set active_tab to settings."""
        with open("src/routes/ui.py", "r") as f:
            content = f.read()
        assert '"active_tab": "settings"' in content


class TestNavigationLink:
    """Test settings link in navigation."""
    
    def test_settings_link_in_nav(self):
        """Base template should have Settings link in nav."""
        with open("src/templates/base.html", "r") as f:
            content = f.read()
        assert 'href="/caseyos/settings"' in content
        assert "⚙️ Settings" in content
    
    def test_settings_active_state(self):
        """Settings tab should have proper active state styling."""
        with open("src/templates/base.html", "r") as f:
            content = f.read()
        assert "active_tab == 'settings'" in content


class TestSettingsFunctions:
    """Test settings JavaScript functions."""
    
    def test_template_has_tab_switching(self):
        """Template should have tab switching function."""
        with open("src/templates/settings.html", "r") as f:
            content = f.read()
        assert "showTab" in content
        assert "tab-content" in content
    
    def test_template_has_load_functions(self):
        """Template should have data loading functions."""
        with open("src/templates/settings.html", "r") as f:
            content = f.read()
        assert "loadAllSettings" in content
        assert "loadSystemStatus" in content
        assert "loadEmergencyStatus" in content
        assert "loadRules" in content
    
    def test_template_has_save_functions(self):
        """Template should have save functions."""
        with open("src/templates/settings.html", "r") as f:
            content = f.read()
        assert "saveNotificationPrefs" in content
        assert "saveRateLimits" in content
    
    def test_template_has_csrf_handling(self):
        """Template should include CSRF token in requests."""
        with open("src/templates/settings.html", "r") as f:
            content = f.read()
        assert "X-CSRF-Token" in content
        assert "getCookie" in content


@pytest.mark.skip(reason="Requires database connection")
class TestSettingsRouteIntegration:
    """Integration tests requiring app context."""
    
    def test_settings_route_returns_200(self, client):
        """Settings page should return 200 status."""
        response = client.get("/caseyos/settings")
        assert response.status_code == 200
    
    def test_settings_page_renders_content(self, client):
        """Settings page should render settings content."""
        response = client.get("/caseyos/settings")
        assert b"Settings" in response.content
