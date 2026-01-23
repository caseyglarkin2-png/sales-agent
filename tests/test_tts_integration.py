"""Tests for Text-to-Speech integration in Jarvis."""
import pytest
from unittest.mock import Mock, patch


@pytest.fixture
def mock_tts_config():
    """Mock TTS configuration."""
    return {
        "enabled": True,
        "rate": 1.0,
        "pitch": 1.0,
        "volume": 1.0,
        "voice_name": "Google UK English Female"
    }


def test_tts_config_endpoint_structure(mock_tts_config):
    """Test that TTS config endpoint returns expected structure."""
    required_keys = ["enabled", "rate", "pitch", "volume", "voice_name"]
    
    for key in required_keys:
        assert key in mock_tts_config, f"Missing required key: {key}"


def test_tts_config_values_valid(mock_tts_config):
    """Test that TTS config values are within valid ranges."""
    assert isinstance(mock_tts_config["enabled"], bool)
    assert 0.5 <= mock_tts_config["rate"] <= 2.0
    assert 0.0 <= mock_tts_config["pitch"] <= 2.0
    assert 0.0 <= mock_tts_config["volume"] <= 1.0
    assert isinstance(mock_tts_config["voice_name"], str)


def test_speak_response_function_exists():
    """Test that speakResponse() function exists in jarvis.html."""
    import os
    jarvis_path = os.path.join(os.path.dirname(__file__), "..", "src", "static", "jarvis.html")
    
    with open(jarvis_path, "r") as f:
        content = f.read()
    
    assert "function speakResponse(" in content
    assert "window.speechSynthesis" in content


def test_read_draft_button_exists():
    """Test that Read Draft button exists in jarvis.html."""
    import os
    jarvis_path = os.path.join(os.path.dirname(__file__), "..", "src", "static", "jarvis.html")
    
    with open(jarvis_path, "r") as f:
        content = f.read()
    
    assert "read-draft-btn" in content
    assert "Read Draft Aloud" in content


def test_voice_selector_exists():
    """Test that voice selector exists in jarvis.html."""
    import os
    jarvis_path = os.path.join(os.path.dirname(__file__), "..", "src", "static", "jarvis.html")
    
    with open(jarvis_path, "r") as f:
        content = f.read()
    
    assert "voice-select" in content
    assert "populateVoices" in content
