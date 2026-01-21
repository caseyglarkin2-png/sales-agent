"""
Documents Module - Document Management
======================================
Handles document storage, sharing, and tracking.
"""

from .document_service import (
    DocumentService,
    Document,
    DocumentFolder,
    DocumentVersion,
    DocumentShare,
    DocumentType,
    DocumentStatus,
    SharePermission,
    get_document_service,
)

__all__ = [
    "DocumentService",
    "Document",
    "DocumentFolder",
    "DocumentVersion",
    "DocumentShare",
    "DocumentType",
    "DocumentStatus",
    "SharePermission",
    "get_document_service",
]
