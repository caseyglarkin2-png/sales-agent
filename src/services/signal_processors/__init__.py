"""Signal processors package for CaseyOS signal ingestion."""
from src.services.signal_processors.base import SignalProcessor

# Lazy imports to avoid circular dependencies
def get_form_processor():
    from src.services.signal_processors.form import FormSubmissionSignalProcessor
    return FormSubmissionSignalProcessor

def get_hubspot_processor():
    from src.services.signal_processors.hubspot import HubSpotDealSignalProcessor
    return HubSpotDealSignalProcessor

def get_gmail_processor():
    from src.services.signal_processors.gmail import GmailReplySignalProcessor
    return GmailReplySignalProcessor

def get_social_processor():
    from src.services.signal_processors.social import SocialSignalProcessor
    return SocialSignalProcessor

__all__ = [
    "SignalProcessor",
    "get_form_processor",
    "get_hubspot_processor",
    "get_gmail_processor",
    "get_social_processor",
]
