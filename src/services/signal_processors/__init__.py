"""Signal processors package for CaseyOS signal ingestion."""
from src.services.signal_processors.base import SignalProcessor

# Lazy imports to avoid circular dependencies
def get_form_processor():
    from src.services.signal_processors.form import FormSubmissionSignalProcessor
    return FormSubmissionSignalProcessor

__all__ = [
    "SignalProcessor",
    "get_form_processor",
]
