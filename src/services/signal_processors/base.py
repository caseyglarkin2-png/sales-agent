"""Base signal processor abstract class."""
from abc import ABC, abstractmethod
from typing import Optional

from src.models.signal import Signal
from src.models.command_queue import CommandQueueItem


class SignalProcessor(ABC):
    """
    Abstract base class for signal processors.
    
    Each processor handles signals from a specific source and converts
    them into command queue recommendations when appropriate.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the name of the signal source this processor handles."""
        pass

    @abstractmethod
    async def process(self, signal: Signal) -> Optional[CommandQueueItem]:
        """
        Process a signal and optionally create a command queue item.
        
        Args:
            signal: The signal to process
            
        Returns:
            CommandQueueItem if a recommendation should be created, None otherwise
        """
        pass

    @abstractmethod
    def can_handle(self, signal: Signal) -> bool:
        """
        Check if this processor can handle the given signal.
        
        Args:
            signal: The signal to check
            
        Returns:
            True if this processor should handle the signal
        """
        pass

    async def validate(self, signal: Signal) -> bool:
        """
        Validate that a signal has all required data for processing.
        
        Override in subclasses for source-specific validation.
        
        Args:
            signal: The signal to validate
            
        Returns:
            True if signal is valid
        """
        return signal.payload is not None and len(signal.payload) > 0
