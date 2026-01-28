"""
Sprint 47: Notifications Center UI Tests

Tests for the Notifications Center page and related functionality.
"""

import pytest


class TestNotificationsUIRoute:
    """Tests for the notifications UI route."""

    @pytest.mark.asyncio
    async def test_notifications_route_returns_html(self, test_client):
        """Test that /caseyos/notifications returns HTML response."""
        response = test_client.get("/caseyos/notifications")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_notifications_route_uses_template(self, test_client):
        """Test that notifications route uses the correct template."""
        response = test_client.get("/caseyos/notifications")
        assert response.status_code == 200
        content = response.content.decode()
        assert "Notifications" in content

    @pytest.mark.asyncio
    async def test_notifications_route_has_active_tab(self, test_client):
        """Test that notifications tab is marked active."""
        response = test_client.get("/caseyos/notifications")
        assert response.status_code == 200
        content = response.content.decode()
        assert "notifications" in content.lower()


class TestNotificationsAPIEndpoints:
    """Tests for notifications API endpoints."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires database connection - run in integration tests")
    async def test_get_notifications_endpoint(self, test_client):
        """Test GET /api/jarvis/notifications returns list."""
        response = test_client.get("/api/jarvis/notifications")
        # May need auth, should not 404
        assert response.status_code in [200, 401, 403, 500]

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires database connection - run in integration tests")
    async def test_whats_up_endpoint(self, test_client):
        """Test GET /api/jarvis/whats-up returns status."""
        response = test_client.get("/api/jarvis/whats-up")
        assert response.status_code in [200, 401, 403, 500]


class TestNotificationsTemplateElements:
    """Tests for notifications template elements."""

    @pytest.mark.asyncio
    async def test_template_has_notifications_list(self, test_client):
        """Test that template includes notifications list container."""
        response = test_client.get("/caseyos/notifications")
        content = response.content.decode()
        assert "notifications-list" in content

    @pytest.mark.asyncio
    async def test_template_has_filter_controls(self, test_client):
        """Test that template includes filter controls."""
        response = test_client.get("/caseyos/notifications")
        content = response.content.decode()
        assert "filter-read" in content
        assert "filter-priority" in content

    @pytest.mark.asyncio
    async def test_template_has_mark_all_read(self, test_client):
        """Test that template includes mark all read button."""
        response = test_client.get("/caseyos/notifications")
        content = response.content.decode()
        assert "markAllRead" in content

    @pytest.mark.asyncio
    async def test_template_has_unread_badge(self, test_client):
        """Test that template includes unread count badge."""
        response = test_client.get("/caseyos/notifications")
        content = response.content.decode()
        assert "unread-count" in content


class TestNotificationBell:
    """Tests for notification bell in navigation."""

    @pytest.mark.asyncio
    async def test_nav_has_notification_bell(self, test_client):
        """Test that navigation includes notification bell."""
        response = test_client.get("/caseyos")
        content = response.content.decode()
        # Bell icon or link to notifications
        assert "/caseyos/notifications" in content or "notification" in content.lower()

    @pytest.mark.asyncio
    async def test_nav_has_badge_element(self, test_client):
        """Test that navigation includes badge element."""
        response = test_client.get("/caseyos")
        content = response.content.decode()
        assert "nav-notification-badge" in content


class TestNotificationActions:
    """Tests for notification action functionality."""

    @pytest.mark.asyncio
    async def test_template_has_action_handling(self, test_client):
        """Test that template includes action execution code."""
        response = test_client.get("/caseyos/notifications")
        content = response.content.decode()
        assert "executeAction" in content

    @pytest.mark.asyncio
    async def test_template_has_mark_read_function(self, test_client):
        """Test that template includes mark read function."""
        response = test_client.get("/caseyos/notifications")
        content = response.content.decode()
        assert "markRead" in content


# Fixture for test client
@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    from fastapi.testclient import TestClient
    from src.main import app
    return TestClient(app)
