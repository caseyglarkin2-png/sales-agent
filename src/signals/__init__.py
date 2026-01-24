"""Signal Framework for CaseyOS.

Signals are raw events from external sources that get processed
into recommendations for the command queue.

Sources:
- HubSpot: Form submissions, deal stage changes, contact updates
- Gmail: Email replies, thread activity
- Twitter: Influencer mentions, market trends
- Calendar: Meeting events
- Manual: User-created signals
"""

from src.signals.base import Signal, SignalProvider, SignalProcessor
from src.signals.providers.social_signal import (
    SocialSignalProvider,
    get_social_signal_provider,
)
from src.signals.providers.twitter_home import (
    TwitterHomeProvider,
    get_twitter_home_provider,
)

__all__ = [
    "Signal",
    "SignalProvider",
    "SignalProcessor",
    "SocialSignalProvider",
    "get_social_signal_provider",
    "TwitterHomeProvider",
    "get_twitter_home_provider",
]
