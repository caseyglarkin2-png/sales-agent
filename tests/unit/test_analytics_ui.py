"""
Unit tests for Sprint 48: Analytics Dashboard UI

Tests the analytics template rendering and route functionality.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


class TestAnalyticsTemplate:
    """Test analytics.html template structure and content."""
    
    def test_template_extends_base(self):
        """Template should extend base.html."""
        with open("src/templates/analytics.html", "r") as f:
            content = f.read()
        assert '{% extends "base.html" %}' in content
    
    def test_template_has_title_block(self):
        """Template should set proper page title."""
        with open("src/templates/analytics.html", "r") as f:
            content = f.read()
        assert "{% block title %}" in content
        assert "Analytics" in content
    
    def test_template_has_chart_js(self):
        """Template should include Chart.js for visualizations."""
        with open("src/templates/analytics.html", "r") as f:
            content = f.read()
        assert "chart.js" in content.lower() or "Chart" in content
    
    def test_template_has_time_window_selector(self):
        """Template should have time window filter dropdown."""
        with open("src/templates/analytics.html", "r") as f:
            content = f.read()
        assert 'id="time-window"' in content
        assert "hour" in content.lower()
        assert "day" in content.lower()
        assert "week" in content.lower()
        assert "month" in content.lower()
    
    def test_template_has_key_metrics(self):
        """Template should display key performance metrics."""
        with open("src/templates/analytics.html", "r") as f:
            content = f.read()
        # Check for metric display elements
        assert "metric-completion" in content
        assert "metric-throughput" in content
        assert "metric-errors" in content
        assert "metric-duration" in content
    
    def test_template_has_trend_chart(self):
        """Template should have performance trend chart container."""
        with open("src/templates/analytics.html", "r") as f:
            content = f.read()
        assert 'id="trend-chart"' in content
        assert "Performance Trend" in content
    
    def test_template_has_mode_distribution_chart(self):
        """Template should have mode distribution pie chart."""
        with open("src/templates/analytics.html", "r") as f:
            content = f.read()
        assert 'id="mode-chart"' in content
        assert "Mode Distribution" in content
    
    def test_template_has_error_analysis(self):
        """Template should have error analysis panel."""
        with open("src/templates/analytics.html", "r") as f:
            content = f.read()
        assert "Error Analysis" in content
        assert 'id="error-list"' in content
        assert "error-count" in content
    
    def test_template_has_recovery_stats(self):
        """Template should have recovery status panel."""
        with open("src/templates/analytics.html", "r") as f:
            content = f.read()
        assert "Recovery Status" in content
        assert 'id="recovery-stats"' in content
        assert "Auto-Recover" in content
    
    def test_template_has_load_functions(self):
        """Template should have JavaScript data loading functions."""
        with open("src/templates/analytics.html", "r") as f:
            content = f.read()
        assert "loadAllData" in content
        assert "loadMetrics" in content
        assert "loadTrends" in content
        assert "loadModeDistribution" in content
        assert "loadErrors" in content
        assert "loadRecoveryStats" in content
    
    def test_template_api_endpoints(self):
        """Template should call correct API endpoints."""
        with open("src/templates/analytics.html", "r") as f:
            content = f.read()
        assert "/api/analytics/metrics" in content
        assert "/api/analytics/trends/" in content
        assert "/api/analytics/mode-distribution" in content
        assert "/api/analytics/errors" in content
        assert "/api/analytics/recovery/stats" in content


class TestAnalyticsRoute:
    """Test analytics route configuration."""
    
    def test_route_exists_in_ui_router(self):
        """Analytics route should be defined in ui.py."""
        with open("src/routes/ui.py", "r") as f:
            content = f.read()
        assert '/caseyos/analytics' in content
        assert 'analytics_dashboard' in content
    
    def test_route_uses_correct_template(self):
        """Route should render analytics.html template."""
        with open("src/routes/ui.py", "r") as f:
            content = f.read()
        assert 'analytics.html' in content
    
    def test_route_sets_active_tab(self):
        """Route should set active_tab to analytics."""
        with open("src/routes/ui.py", "r") as f:
            content = f.read()
        assert '"active_tab": "analytics"' in content


class TestNavigationLink:
    """Test analytics link in navigation."""
    
    def test_analytics_link_in_nav(self):
        """Base template should have Analytics link in nav."""
        with open("src/templates/base.html", "r") as f:
            content = f.read()
        assert 'href="/caseyos/analytics"' in content
        assert "📈 Analytics" in content
    
    def test_analytics_active_state(self):
        """Analytics tab should have proper active state styling."""
        with open("src/templates/base.html", "r") as f:
            content = f.read()
        assert "active_tab == 'analytics'" in content


@pytest.mark.skip(reason="Requires database connection")
class TestAnalyticsRouteIntegration:
    """Integration tests requiring app context."""
    
    def test_analytics_route_returns_200(self, client):
        """Analytics page should return 200 status."""
        response = client.get("/caseyos/analytics")
        assert response.status_code == 200
    
    def test_analytics_page_renders_content(self, client):
        """Analytics page should render dashboard content."""
        response = client.get("/caseyos/analytics")
        assert b"Analytics" in response.content
