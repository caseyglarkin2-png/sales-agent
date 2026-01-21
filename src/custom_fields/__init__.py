"""
Custom Fields Module
====================
Dynamic custom field definitions and values for entities.
"""

from .custom_fields_service import (
    CustomFieldsService,
    CustomField,
    CustomFieldValue,
    FieldType,
    EntityType,
    get_custom_fields_service,
)

__all__ = [
    "CustomFieldsService",
    "CustomField",
    "CustomFieldValue",
    "FieldType",
    "EntityType",
    "get_custom_fields_service",
]
