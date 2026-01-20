"""Unit tests for config module."""
import pytest
from pydantic import ValidationError

from src.config import Settings, get_settings


def test_base_settings_validates_required_fields() -> None:
    """Test that required fields raise error in production."""
    # Development should not require fields
    settings = Settings(api_env="development")
    assert settings.api_env == "development"
    # Calling validate should not raise in development
    settings.validate_required_fields()

    # Production should validate - missing required fields raises ValueError
    prod_settings = Settings(api_env="production")
    with pytest.raises(ValueError, match="Missing required fields"):
        prod_settings.validate_required_fields()


def test_settings_loads_from_env(monkeypatch) -> None:
    """Test that settings load from environment variables."""
    monkeypatch.setenv("API_HOST", "127.0.0.1")
    monkeypatch.setenv("API_PORT", "9000")
    monkeypatch.setenv("API_ENV", "staging")

    settings = Settings()
    assert settings.api_host == "127.0.0.1"
    assert settings.api_port == 9000
    assert settings.api_env == "staging"


def test_settings_defaults() -> None:
    """Test that default values are set correctly."""
    settings = Settings()
    assert settings.api_host == "0.0.0.0"
    assert settings.api_port == 8000
    assert settings.api_env == "development"
    assert settings.operator_mode_enabled is True
    assert settings.max_emails_per_day == 20


def test_get_settings() -> None:
    """Test get_settings factory function."""
    settings = get_settings()
    assert isinstance(settings, Settings)
    assert settings.api_env in ("development", "staging", "production")
