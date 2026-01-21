"""Enrichment module for contact data."""
from src.enrichment.contact_enricher import (
    ContactEnricher,
    EnrichedContact,
    get_contact_enricher,
)

__all__ = [
    "ContactEnricher",
    "EnrichedContact",
    "get_contact_enricher",
]
