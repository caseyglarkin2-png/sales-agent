"""Tests for SignalProcessor interface."""
import pytest
from abc import ABC

from src.services.signal_processors.base import SignalProcessor
from src.models.signal import Signal, SignalSource


class TestSignalProcessorInterface:
    """Test SignalProcessor ABC interface."""

    def test_is_abstract_class(self):
        """SignalProcessor should be an abstract class."""
        assert issubclass(SignalProcessor, ABC)

    def test_cannot_instantiate_directly(self):
        """Cannot instantiate SignalProcessor directly."""
        with pytest.raises(TypeError):
            SignalProcessor()

    def test_has_required_abstract_methods(self):
        """SignalProcessor defines required abstract methods."""
        abstract_methods = SignalProcessor.__abstractmethods__
        assert "process" in abstract_methods
        assert "can_handle" in abstract_methods
        assert "source_name" in abstract_methods

    def test_concrete_implementation_works(self):
        """A concrete implementation should work."""
        
        class TestProcessor(SignalProcessor):
            @property
            def source_name(self) -> str:
                return "test"
            
            async def process(self, signal):
                return None
            
            def can_handle(self, signal) -> bool:
                return True
        
        processor = TestProcessor()
        assert processor.source_name == "test"
        assert processor.can_handle(None) is True

    @pytest.mark.asyncio
    async def test_validate_default_implementation(self):
        """Default validate checks for non-empty payload."""
        
        class TestProcessor(SignalProcessor):
            @property
            def source_name(self) -> str:
                return "test"
            
            async def process(self, signal):
                return None
            
            def can_handle(self, signal) -> bool:
                return True
        
        processor = TestProcessor()
        
        # Empty payload should fail
        signal_empty = Signal(
            source=SignalSource.MANUAL,
            event_type="test",
            payload={}
        )
        assert await processor.validate(signal_empty) is False
        
        # Non-empty payload should pass
        signal_valid = Signal(
            source=SignalSource.MANUAL,
            event_type="test",
            payload={"key": "value"}
        )
        assert await processor.validate(signal_valid) is True
