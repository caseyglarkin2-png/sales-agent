"""Base classes for Signal framework.

The signal framework provides:
1. Signal - A raw event from an external source
2. SignalProvider - Polls/receives signals from a source
3. SignalProcessor - Converts signals to recommendations
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum
import hashlib
import json


class SignalSource(str, Enum):
    """Known signal sources."""
    HUBSPOT = "hubspot"
    GMAIL = "gmail"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    CALENDAR = "calendar"
    MANUAL = "manual"
    INTERNAL = "internal"


@dataclass
class Signal:
    """A raw signal from an external source.
    
    Signals are immutable events that capture something that happened.
    They get processed into recommendations for the command queue.
    
    Attributes:
        source: Where the signal came from (hubspot, gmail, twitter, etc.)
        signal_type: Type of signal (form_submitted, email_replied, tweet_mention)
        data: Raw signal data as dict
        processed: Whether signal has been processed into a recommendation
        created_at: When the signal was created
        processed_at: When the signal was processed
        recommendation_id: ID of generated recommendation (if any)
    """
    source: str
    signal_type: str
    data: Dict[str, Any]
    processed: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    recommendation_id: Optional[str] = None
    id: Optional[str] = None
    
    def __post_init__(self):
        """Generate ID from payload hash if not provided."""
        if self.id is None:
            self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Generate deterministic ID from signal content."""
        payload = {
            "source": self.source,
            "signal_type": self.signal_type,
            "data": self.data,
        }
        payload_str = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(payload_str.encode()).hexdigest()[:16]
    
    @property
    def payload_hash(self) -> str:
        """Get hash of payload for deduplication."""
        return self._generate_id()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for storage."""
        return {
            "id": self.id,
            "source": self.source,
            "signal_type": self.signal_type,
            "data": self.data,
            "processed": self.processed,
            "created_at": self.created_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "recommendation_id": self.recommendation_id,
            "payload_hash": self.payload_hash,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Signal":
        """Create Signal from dict."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        processed_at = data.get("processed_at")
        if isinstance(processed_at, str):
            processed_at = datetime.fromisoformat(processed_at)
        
        return cls(
            id=data.get("id"),
            source=data.get("source", "unknown"),
            signal_type=data.get("signal_type", "unknown"),
            data=data.get("data", {}),
            processed=data.get("processed", False),
            created_at=created_at or datetime.utcnow(),
            processed_at=processed_at,
            recommendation_id=data.get("recommendation_id"),
        )


class SignalProvider(ABC):
    """Base class for signal providers.
    
    A signal provider polls or receives signals from an external source
    and converts them to Signal objects for processing.
    """
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Name of the signal source."""
        pass
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is configured and available."""
        pass
    
    @abstractmethod
    async def poll_signals(self, since: Optional[datetime] = None) -> List[Signal]:
        """Poll for new signals.
        
        Args:
            since: Only get signals after this timestamp
            
        Returns:
            List of Signal objects
        """
        pass


class SignalProcessor(ABC):
    """Base class for signal processors.
    
    A signal processor takes a Signal and optionally generates
    an ActionRecommendation for the command queue.
    """
    
    @property
    @abstractmethod
    def supported_signal_types(self) -> List[str]:
        """List of signal types this processor handles."""
        pass
    
    @abstractmethod
    async def process(self, signal: Signal) -> Optional[Dict[str, Any]]:
        """Process a signal and optionally generate a recommendation.
        
        Args:
            signal: The signal to process
            
        Returns:
            Recommendation dict if one should be created, None otherwise
        """
        pass
    
    def can_process(self, signal: Signal) -> bool:
        """Check if this processor can handle the signal."""
        return signal.signal_type in self.supported_signal_types
