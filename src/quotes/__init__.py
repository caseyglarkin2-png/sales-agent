"""
Quotes Module - Quote and Proposal Management
==============================================
Generate and manage sales quotes and proposals.
"""

from .quote_service import (
    QuoteService,
    Quote,
    QuoteItem,
    QuoteStatus,
    QuoteTemplate,
    get_quote_service,
)

__all__ = [
    "QuoteService",
    "Quote",
    "QuoteItem",
    "QuoteStatus",
    "QuoteTemplate",
    "get_quote_service",
]
