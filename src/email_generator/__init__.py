"""
Email Generator Module
======================
AI-powered email content generation.
"""

from src.email_generator.generator_service import (
    EmailGenerator,
    EmailType,
    EmailTone,
    GeneratedEmail,
    get_email_generator,
)

__all__ = [
    "EmailGenerator",
    "EmailType",
    "EmailTone",
    "GeneratedEmail",
    "get_email_generator",
]
