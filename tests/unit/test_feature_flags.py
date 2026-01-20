"""Tests for feature flags."""
import pytest

from src.feature_flags import FeatureFlagManager


def test_feature_flag_initialization():
    """Test feature flag manager initialization."""
    flags = {"feature_a": True, "feature_b": False}
    manager = FeatureFlagManager(flags)
    
    assert manager.is_enabled("feature_a") is True
    assert manager.is_enabled("feature_b") is False


def test_feature_flag_set():
    """Test setting a feature flag."""
    manager = FeatureFlagManager({})
    
    manager.set_flag("new_feature", True)
    assert manager.is_enabled("new_feature") is True
    
    manager.set_flag("new_feature", False)
    assert manager.is_enabled("new_feature") is False


def test_feature_flag_get_all():
    """Test getting all feature flags."""
    flags = {"feature_a": True, "feature_b": False}
    manager = FeatureFlagManager(flags)
    
    all_flags = manager.get_all_flags()
    assert all_flags == flags
