"""
Unit tests for Sprint 52: Legacy Cleanup & Polish

Tests that legacy files have been removed and version updated.
"""
import pytest
import os


class TestLegacyCleanup:
    """Test legacy static HTML files have been removed/archived."""
    
    def test_legacy_html_removed_from_static(self):
        """Legacy HTML files should not be in src/static."""
        legacy_files = [
            "admin.html",
            "agent-hub.html",
            "agents.html",
            "index.html",
            "integrations.html",
            "operator-dashboard.html",
            "queue-item-detail.html",
            "voice-profiles.html",
            "voice-training.html",
        ]
        for f in legacy_files:
            path = f"src/static/{f}"
            assert not os.path.exists(path), f"Legacy file {f} should be removed from src/static"
    
    def test_legacy_files_archived(self):
        """Legacy files should be moved to archive."""
        archive_path = "archive/legacy_spa"
        assert os.path.isdir(archive_path), "Archive directory should exist"
        archived_files = os.listdir(archive_path)
        # At least some legacy files should be archived
        assert len(archived_files) > 0, "Archive should contain legacy files"
    
    def test_deprecated_routes_removed(self):
        """Deprecated route files should not be in src/routes."""
        deprecated = [
            "src/routes/ui_command_queue.py",
            "src/routes/caseyos_ui.py",
        ]
        for f in deprecated:
            assert not os.path.exists(f), f"Deprecated route {f} should be removed"
    
    def test_static_still_has_required_files(self):
        """Required static files should still exist."""
        required = [
            "src/static/manifest.json",
            "src/static/sw.js",
        ]
        for f in required:
            assert os.path.exists(f), f"Required file {f} should still exist"


class TestVersionUpdate:
    """Test version numbers have been updated."""
    
    def test_base_html_version_updated(self):
        """Base template footer should show v4.0."""
        with open("src/templates/base.html", "r") as f:
            content = f.read()
        assert "v4.0" in content, "Base template should show version 4.0"
        assert "Sprint 52" in content or "v4.0" in content, "Version should reference Sprint 52"
    
    def test_pyproject_version_updated(self):
        """pyproject.toml should have updated version."""
        with open("pyproject.toml", "r") as f:
            content = f.read()
        assert 'version = "4.0.0"' in content, "pyproject.toml should have version 4.0.0"


class TestNavigationComplete:
    """Test all navigation tabs are present."""
    
    def test_all_tabs_present(self):
        """All main navigation tabs should be present in base.html."""
        with open("src/templates/base.html", "r") as f:
            content = f.read()
        
        # Core tabs
        assert 'href="/caseyos"' in content or 'Dashboard' in content
        assert 'href="/caseyos/queue"' in content
        assert 'href="/caseyos/gemini"' in content
        assert 'href="/caseyos/drive"' in content
        assert 'href="/caseyos/agents"' in content
        assert 'href="/caseyos/executions"' in content
        assert 'href="/caseyos/signals"' in content
        assert 'href="/caseyos/overview"' in content
        
        # Sprint 45-51 tabs
        assert 'href="/caseyos/memory"' in content
        assert 'href="/caseyos/integrations"' in content
        assert 'href="/caseyos/analytics"' in content
        assert 'href="/caseyos/workflows"' in content
        assert 'href="/caseyos/settings"' in content
        assert 'href="/caseyos/admin"' in content
    
    def test_notification_bell_present(self):
        """Notification bell should be in header."""
        with open("src/templates/base.html", "r") as f:
            content = f.read()
        assert 'href="/caseyos/notifications"' in content
        assert 'nav-notification-badge' in content


class TestTemplatesComplete:
    """Test all Sprint 45-51 templates exist."""
    
    def test_all_new_templates_exist(self):
        """All new templates from Sprints 45-51 should exist."""
        templates = [
            "src/templates/memory.html",
            "src/templates/integrations.html",
            "src/templates/notifications.html",
            "src/templates/analytics.html",
            "src/templates/workflows.html",
            "src/templates/settings.html",
            "src/templates/admin.html",
        ]
        for t in templates:
            assert os.path.exists(t), f"Template {t} should exist"
    
    def test_templates_extend_base(self):
        """All new templates should extend base.html."""
        templates = [
            "src/templates/memory.html",
            "src/templates/integrations.html",
            "src/templates/notifications.html",
            "src/templates/analytics.html",
            "src/templates/workflows.html",
            "src/templates/settings.html",
            "src/templates/admin.html",
        ]
        for t in templates:
            with open(t, "r") as f:
                content = f.read()
            assert '{% extends "base.html" %}' in content, f"{t} should extend base.html"
