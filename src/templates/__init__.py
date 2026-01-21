"""Templates package."""

from .template_library import (
    TemplateLibrary,
    EmailTemplate,
    TemplateCategory,
    get_template_library,
)

__all__ = [
    "TemplateLibrary",
    "EmailTemplate",
    "TemplateCategory",
    "get_template_library",
]
