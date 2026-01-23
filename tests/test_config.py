"""Tests for application configuration settings."""

import pytest
import os
from src.config import get_settings, Settings


def test_tts_config_defaults():
    """Test that TTS configuration has correct default values."""
    settings = get_settings()
    
    assert settings.tts_enabled is True
    assert settings.tts_voice_name == "Google UK English Female"
    assert settings.tts_rate == 1.0
    assert settings.tts_pitch == 1.0
    assert settings.tts_volume == 1.0


def test_tts_config_from_environment(monkeypatch):
    """Test that TTS configuration can be overridden via environment variables."""
    # Set environment variables
    monkeypatch.setenv("TTS_ENABLED", "false")
    monkeypatch.setenv("TTS_VOICE_NAME", "Custom Voice")
    monkeypatch.setenv("TTS_RATE", "1.5")
    monkeypatch.setenv("TTS_PITCH", "0.8")
    monkeypatch.setenv("TTS_VOLUME", "0.9")
    
    # Create new settings instance (bypassing singleton)
    settings = Settings()
    
    assert settings.tts_enabled is False
    assert settings.tts_voice_name == "Custom Voice"
    assert settings.tts_rate == 1.5
    assert settings.tts_pitch == 0.8
    assert settings.tts_volume == 0.9


def test_tts_rate_boundaries():
    """Test TTS rate accepts valid boundary values."""
    # Min boundary
    settings = Settings(tts_rate=0.5)
    assert settings.tts_rate == 0.5
    
    # Max boundary
    settings = Settings(tts_rate=2.0)
    assert settings.tts_rate == 2.0


def test_tts_pitch_boundaries():
    """Test TTS pitch accepts valid boundary values."""
    # Min boundary
    settings = Settings(tts_pitch=0.0)
    assert settings.tts_pitch == 0.0
    
    # Max boundary
    settings = Settings(tts_pitch=2.0)
    assert settings.tts_pitch == 2.0


def test_tts_volume_boundaries():
    """Test TTS volume accepts valid boundary values."""
    # Min boundary
    settings = Settings(tts_volume=0.0)
    assert settings.tts_volume == 0.0
    
    # Max boundary
    settings = Settings(tts_volume=1.0)
    assert settings.tts_volume == 1.0


def test_settings_singleton():
    """Test that get_settings() returns consistent instance."""
    settings1 = get_settings()
    settings2 = get_settings()
    
    # Should be same configuration
    assert settings1.tts_enabled == settings2.tts_enabled
    assert settings1.tts_voice_name == settings2.tts_voice_name


def test_tts_rate_validation_rejects_invalid():
    """Test that TTS rate validates bounds and rejects invalid values."""
    from pydantic import ValidationError
    
    # Too low
    with pytest.raises(ValidationError) as exc_info:
        Settings(tts_rate=0.4)
    assert "greater than or equal to 0.5" in str(exc_info.value)
    
    # Too high
    with pytest.raises(ValidationError) as exc_info:
        Settings(tts_rate=2.1)
    assert "less than or equal to 2" in str(exc_info.value)


def test_tts_pitch_validation_rejects_invalid():
    """Test that TTS pitch validates bounds and rejects invalid values."""
    from pydantic import ValidationError
    
    # Too low
    with pytest.raises(ValidationError) as exc_info:
        Settings(tts_pitch=-0.1)
    assert "greater than or equal to 0" in str(exc_info.value)
    
    # Too high
    with pytest.raises(ValidationError) as exc_info:
        Settings(tts_pitch=2.1)
    assert "less than or equal to 2" in str(exc_info.value)


def test_tts_volume_validation_rejects_invalid():
    """Test that TTS volume validates bounds and rejects invalid values."""
    from pydantic import ValidationError
    
    # Too low
    with pytest.raises(ValidationError) as exc_info:
        Settings(tts_volume=-0.1)
    assert "greater than or equal to 0" in str(exc_info.value)
    
    # Too high
    with pytest.raises(ValidationError) as exc_info:
        Settings(tts_volume=1.1)
    assert "less than or equal to 1" in str(exc_info.value)

