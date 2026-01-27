"""Tests for CSRF path exclusions.

Sprint 39A: Verify Gemini and Drive APIs are excluded from CSRF protection.
"""
import pytest
from src.security.csrf import exclude_path


class TestCSRFExclusions:
    """Test CSRF path exclusion logic."""

    def test_gemini_chat_excluded(self):
        """Gemini chat endpoint should be excluded from CSRF."""
        assert exclude_path("/api/gemini/chat") is True

    def test_gemini_models_excluded(self):
        """Gemini models endpoint should be excluded from CSRF."""
        assert exclude_path("/api/gemini/models") is True

    def test_gemini_jarvis_excluded(self):
        """Gemini Jarvis endpoints should be excluded from CSRF."""
        assert exclude_path("/api/gemini/jarvis/chat") is True
        assert exclude_path("/api/gemini/jarvis/tools") is True

    def test_drive_files_excluded(self):
        """Drive file endpoints should be excluded from CSRF."""
        assert exclude_path("/api/drive/files") is True
        assert exclude_path("/api/drive/folders") is True

    def test_drive_content_excluded(self):
        """Drive content endpoint should be excluded from CSRF."""
        assert exclude_path("/api/drive/file/123/content") is True

    def test_drive_search_excluded(self):
        """Drive search endpoint should be excluded from CSRF."""
        assert exclude_path("/api/drive/search") is True

    def test_webhooks_still_excluded(self):
        """Webhook endpoints should still be excluded."""
        assert exclude_path("/api/webhooks/hubspot") is True
        assert exclude_path("/api/webhooks/gmail") is True

    def test_mcp_still_excluded(self):
        """MCP endpoints should still be excluded."""
        assert exclude_path("/mcp/tools") is True

    def test_health_checks_excluded(self):
        """Health check endpoints should be excluded."""
        assert exclude_path("/health") is True
        assert exclude_path("/healthz") is True
        assert exclude_path("/ready") is True

    def test_auth_excluded(self):
        """Auth endpoints should be excluded."""
        assert exclude_path("/auth/callback") is True
        assert exclude_path("/auth/login") is True

    def test_docs_excluded(self):
        """API docs should be excluded."""
        assert exclude_path("/docs") is True
        assert exclude_path("/redoc") is True
        assert exclude_path("/openapi.json") is True

    def test_command_queue_not_excluded(self):
        """Command queue API should NOT be excluded (needs CSRF)."""
        assert exclude_path("/api/command-queue/123") is False
        assert exclude_path("/api/command-queue/today") is False

    def test_regular_api_not_excluded(self):
        """Regular API endpoints should NOT be excluded."""
        assert exclude_path("/api/contacts") is False
        assert exclude_path("/api/users") is False
        assert exclude_path("/api/drafts") is False

    def test_caseyos_ui_not_excluded(self):
        """CaseyOS UI endpoints should NOT be excluded."""
        # Note: UI endpoints are GET requests, so CSRF doesn't apply
        # but they should not be in the exclusion list
        assert exclude_path("/caseyos/queue") is False
        assert exclude_path("/caseyos/gemini") is False
