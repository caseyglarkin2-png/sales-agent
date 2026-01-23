"""
Tests for feature flag system.
"""
import pytest
from unittest.mock import patch
from src.feature_flags import (
    FeatureFlagManager,
    FeatureFlagError,
    OperationMode,
    get_flag_manager
)


def test_feature_flag_initialization():
    """Test feature flag manager initialization (legacy)."""
    flags = {"feature_a": True, "feature_b": False}
    manager = FeatureFlagManager(flags)
    
    assert manager.is_enabled("feature_a") is True
    assert manager.is_enabled("feature_b") is False


def test_feature_flag_set():
    """Test setting a feature flag (legacy)."""
    manager = FeatureFlagManager({})
    
    manager.set_flag("new_feature", True)
    assert manager.is_enabled("new_feature") is True
    
    manager.set_flag("new_feature", False)
    assert manager.is_enabled("new_feature") is False


def test_feature_flag_get_all():
    """Test getting all feature flags (legacy)."""
    flags = {"feature_a": True, "feature_b": False}
    manager = FeatureFlagManager(flags)
    
    all_flags = manager.get_all_flags()
    assert all_flags == flags


def test_default_draft_only_mode():
    """Test system defaults to DRAFT_ONLY mode."""
    with patch('src.config.get_settings') as mock_settings:
        mock_settings.return_value.MODE_DRAFT_ONLY = True
        mock_settings.return_value.ALLOW_AUTO_SEND = False
        mock_settings.return_value.API_ENV = "development"
        
        manager = FeatureFlagManager()
        assert manager.is_send_mode_enabled() is False
        assert manager.get_operation_mode() == OperationMode.DRAFT_ONLY


def test_send_mode_blocked_in_dev():
    """Test SEND mode blocked in non-production environments."""
    with patch('src.config.get_settings') as mock_settings:
        mock_settings.return_value.MODE_DRAFT_ONLY = False
        mock_settings.return_value.ALLOW_AUTO_SEND = True
        mock_settings.return_value.API_ENV = "development"
        
        manager = FeatureFlagManager()
        
        with pytest.raises(FeatureFlagError, match="not allowed in development"):
            manager.is_send_mode_enabled()


def test_send_mode_allowed_in_production():
    """Test SEND mode allowed in production with correct flags."""
    with patch('src.config.get_settings') as mock_settings:
        mock_settings.return_value.MODE_DRAFT_ONLY = False
        mock_settings.return_value.ALLOW_AUTO_SEND = True
        mock_settings.return_value.API_ENV = "production"
        
        manager = FeatureFlagManager()
        assert manager.is_send_mode_enabled() is True
        assert manager.get_operation_mode() == OperationMode.SEND


def test_kill_switch_disables_send_mode():
    """Test kill switch immediately disables SEND mode."""
    with patch('src.config.get_settings') as mock_settings:
        mock_settings.return_value.MODE_DRAFT_ONLY = False
        mock_settings.return_value.ALLOW_AUTO_SEND = True
        mock_settings.return_value.API_ENV = "production"
        
        manager = FeatureFlagManager()
        assert manager.is_send_mode_enabled() is True
        
        # Activate kill switch
        change_record = manager.disable_send_mode(
            operator="test@example.com",
            reason="Emergency test"
        )
        
        assert manager.is_send_mode_enabled() is False
        assert change_record["action"] == "kill_switch_activated"
        assert change_record["operator"] == "test@example.com"
        assert change_record["new_state"] == "DRAFT_ONLY"


def test_enable_send_mode_requires_production():
    """Test enabling SEND mode requires production environment."""
    with patch('src.config.get_settings') as mock_settings:
        mock_settings.return_value.API_ENV = "development"
        
        manager = FeatureFlagManager()
        
        with pytest.raises(FeatureFlagError, match="Cannot enable SEND mode in development"):
            manager.enable_send_mode(
                operator="test@example.com",
                reason="Test enable"
            )


def test_circuit_breaker_blocks_send_mode():
    """Test circuit breaker disables SEND mode on high error rate."""
    with patch('src.config.get_settings') as mock_settings:
        mock_settings.return_value.MODE_DRAFT_ONLY = False
        mock_settings.return_value.ALLOW_AUTO_SEND = True
        mock_settings.return_value.API_ENV = "production"
        
        manager = FeatureFlagManager()
        
        # Record 15 sends with >10% error rate
        for i in range(15):
            success = i < 13  # 2/15 = 13.3% error rate
            manager.record_send_attempt(success=success, email=f"test{i}@example.com")
        
        # Circuit breaker should open
        assert manager.is_send_mode_enabled() is False
        
        status = manager.get_circuit_breaker_status()
        assert status["status"] == "open"
        assert status["error_count"] == 2
        assert status["error_rate"] > 0.10


def test_mode_history_audit_trail():
    """Test mode changes are logged to audit trail."""
    with patch('src.config.get_settings') as mock_settings:
        mock_settings.return_value.API_ENV = "production"
        
        manager = FeatureFlagManager()
        
        # Enable SEND mode
        manager.enable_send_mode(operator="admin@example.com", reason="Test activation")
        
        # Disable SEND mode
        manager.disable_send_mode(operator="ops@example.com", reason="Emergency shutoff")
        
        history = manager.get_mode_history()
        assert len(history) == 2
        assert history[0]["operator"] == "admin@example.com"
        assert history[0]["action"] == "send_mode_enabled"
        assert history[1]["operator"] == "ops@example.com"
        assert history[1]["action"] == "kill_switch_activated"


def test_validate_send_mode_on_startup():
    """Test validate_send_mode raises on invalid configuration."""
    with patch('src.config.get_settings') as mock_settings:
        mock_settings.return_value.MODE_DRAFT_ONLY = True
        mock_settings.return_value.ALLOW_AUTO_SEND = False
        mock_settings.return_value.API_ENV = "production"
        
        manager = FeatureFlagManager()
        
        # Should succeed (DRAFT_ONLY is safe)
        manager.validate_send_mode()


def test_circuit_breaker_requires_minimum_sample():
    """Test circuit breaker requires at least 10 sends before opening."""
    with patch('src.config.get_settings') as mock_settings:
        mock_settings.return_value.MODE_DRAFT_ONLY = False
        mock_settings.return_value.ALLOW_AUTO_SEND = True
        mock_settings.return_value.API_ENV = "production"
        
        manager = FeatureFlagManager()
        
        # Record only 5 failed sends
        for i in range(5):
            manager.record_send_attempt(success=False, email=f"test{i}@example.com")
        
        status = manager.get_circuit_breaker_status()
        # Should not open with <10 samples
        assert status["status"] == "closed"


def test_circuit_breaker_metrics():
    """Test circuit breaker status returns correct metrics."""
    with patch('src.config.get_settings') as mock_settings:
        mock_settings.return_value.MODE_DRAFT_ONLY = False
        mock_settings.return_value.ALLOW_AUTO_SEND = True
        mock_settings.return_value.API_ENV = "production"
        
        manager = FeatureFlagManager()
        
        # Record 20 sends: 18 success, 2 failures (10% error rate exactly)
        for i in range(20):
            success = i < 18
            manager.record_send_attempt(success=success, email=f"test{i}@example.com")
        
        status = manager.get_circuit_breaker_status()
        assert status["total_sends"] == 20
        assert status["error_count"] == 2
        assert status["error_rate"] == 0.10
        assert status["threshold"] == 0.10
        assert status["sample_window"] == "1 hour"

