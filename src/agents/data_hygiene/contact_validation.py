"""Contact Validation Agent - Validates and standardizes contact data.

Responsibilities:
- Email format validation (RFC 5322)
- Phone number normalization
- Job title standardization
- Required field checks
- Flagging invalid contacts for review
"""

import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from src.agents.base import BaseAgent
from src.logger import get_logger

logger = get_logger(__name__)


class ValidationSeverity(str, Enum):
    """Severity of validation issue."""
    ERROR = "error"      # Must fix before use
    WARNING = "warning"  # Should fix, but usable
    INFO = "info"        # Nice to fix


@dataclass
class ValidationIssue:
    """A single validation issue found on a contact."""
    field: str
    severity: ValidationSeverity
    message: str
    current_value: Optional[str] = None
    suggested_value: Optional[str] = None


class ContactValidationAgent(BaseAgent):
    """Validates contact data for quality issues.
    
    Checks:
    - Email: valid format, not disposable, not generic (info@, sales@)
    - Phone: valid format, normalized to E.164
    - Job Title: standardized to common formats
    - Required Fields: firstname, lastname, company for ICP contacts
    """
    
    # Common disposable email domains
    DISPOSABLE_DOMAINS = {
        "mailinator.com", "guerrillamail.com", "tempmail.com", "10minutemail.com",
        "throwaway.email", "maildrop.cc", "yopmail.com", "getnada.com"
    }
    
    # Generic email prefixes that indicate role-based emails
    GENERIC_PREFIXES = {
        "info", "sales", "support", "hello", "contact", "admin", "help",
        "team", "noreply", "no-reply", "marketing", "press", "media"
    }
    
    # Job title standardization map
    JOB_TITLE_MAP = {
        "ceo": "Chief Executive Officer",
        "cfo": "Chief Financial Officer",
        "cto": "Chief Technology Officer",
        "cmo": "Chief Marketing Officer",
        "coo": "Chief Operating Officer",
        "cro": "Chief Revenue Officer",
        "vp": "Vice President",
        "svp": "Senior Vice President",
        "evp": "Executive Vice President",
        "dir": "Director",
        "mgr": "Manager",
        "sr": "Senior",
        "jr": "Junior",
    }
    
    def __init__(self):
        super().__init__(
            name="ContactValidationAgent",
            description="Validates and standardizes contact data quality"
        )
        # RFC 5322 simplified email regex
        self.email_pattern = re.compile(
            r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        )
        # E.164 phone pattern (international)
        self.phone_pattern = re.compile(r"^\+?[1-9]\d{1,14}$")
    
    async def validate_input(self, context: Dict[str, Any]) -> bool:
        """Validate we have contact data to check."""
        action = context.get("action", "validate")
        if action == "validate_contact":
            return "contact" in context
        elif action == "validate_batch":
            return "contacts" in context and isinstance(context["contacts"], list)
        return True
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute validation based on action."""
        action = context.get("action", "validate_contact")
        
        if action == "validate_contact":
            contact = context.get("contact", {})
            issues = self._validate_contact(contact)
            return {
                "status": "success",
                "contact_id": contact.get("id"),
                "issues": [self._issue_to_dict(i) for i in issues],
                "is_valid": not any(i.severity == ValidationSeverity.ERROR for i in issues),
                "error_count": sum(1 for i in issues if i.severity == ValidationSeverity.ERROR),
                "warning_count": sum(1 for i in issues if i.severity == ValidationSeverity.WARNING),
            }
        
        elif action == "validate_batch":
            contacts = context.get("contacts", [])
            results = []
            total_errors = 0
            total_warnings = 0
            
            for contact in contacts:
                issues = self._validate_contact(contact)
                errors = sum(1 for i in issues if i.severity == ValidationSeverity.ERROR)
                warnings = sum(1 for i in issues if i.severity == ValidationSeverity.WARNING)
                total_errors += errors
                total_warnings += warnings
                
                results.append({
                    "contact_id": contact.get("id"),
                    "email": contact.get("email"),
                    "issues": [self._issue_to_dict(i) for i in issues],
                    "is_valid": errors == 0,
                })
            
            return {
                "status": "success",
                "total_contacts": len(contacts),
                "valid_contacts": sum(1 for r in results if r["is_valid"]),
                "invalid_contacts": sum(1 for r in results if not r["is_valid"]),
                "total_errors": total_errors,
                "total_warnings": total_warnings,
                "results": results,
            }
        
        return {"status": "error", "error": f"Unknown action: {action}"}
    
    def _validate_contact(self, contact: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate a single contact and return issues."""
        issues = []
        
        # Email validation
        email = contact.get("email", "")
        issues.extend(self._validate_email(email))
        
        # Phone validation
        phone = contact.get("phone") or contact.get("mobilephone") or ""
        if phone:
            issues.extend(self._validate_phone(phone))
        
        # Job title standardization
        job_title = contact.get("jobtitle", "")
        if job_title:
            issues.extend(self._validate_job_title(job_title))
        
        # Required fields for ICP contacts
        if contact.get("hs_lead_status") == "QUALIFIED" or contact.get("lifecyclestage") == "opportunity":
            issues.extend(self._validate_required_fields(contact))
        
        return issues
    
    def _validate_email(self, email: str) -> List[ValidationIssue]:
        """Validate email format and quality."""
        issues = []
        
        if not email:
            issues.append(ValidationIssue(
                field="email",
                severity=ValidationSeverity.ERROR,
                message="Email is required",
            ))
            return issues
        
        email_lower = email.lower().strip()
        
        # Format check
        if not self.email_pattern.match(email_lower):
            issues.append(ValidationIssue(
                field="email",
                severity=ValidationSeverity.ERROR,
                message="Invalid email format",
                current_value=email,
            ))
            return issues
        
        # Extract domain and prefix
        prefix, domain = email_lower.split("@")
        
        # Disposable email check
        if domain in self.DISPOSABLE_DOMAINS:
            issues.append(ValidationIssue(
                field="email",
                severity=ValidationSeverity.WARNING,
                message="Disposable email domain detected",
                current_value=email,
            ))
        
        # Generic prefix check
        if prefix in self.GENERIC_PREFIXES:
            issues.append(ValidationIssue(
                field="email",
                severity=ValidationSeverity.INFO,
                message="Generic/role-based email - may not reach decision maker",
                current_value=email,
            ))
        
        return issues
    
    def _validate_phone(self, phone: str) -> List[ValidationIssue]:
        """Validate and suggest normalized phone format."""
        issues = []
        
        # Strip common formatting
        normalized = re.sub(r"[\s\-\(\)\.]", "", phone)
        
        # Add + prefix if missing for 10+ digit numbers
        if len(normalized) >= 10 and not normalized.startswith("+"):
            if normalized.startswith("1") and len(normalized) == 11:
                normalized = "+" + normalized
            elif len(normalized) == 10:
                normalized = "+1" + normalized  # Assume US
        
        if not self.phone_pattern.match(normalized):
            issues.append(ValidationIssue(
                field="phone",
                severity=ValidationSeverity.WARNING,
                message="Phone number format may be invalid",
                current_value=phone,
                suggested_value=normalized if normalized != phone else None,
            ))
        elif normalized != phone:
            issues.append(ValidationIssue(
                field="phone",
                severity=ValidationSeverity.INFO,
                message="Phone number can be normalized to E.164",
                current_value=phone,
                suggested_value=normalized,
            ))
        
        return issues
    
    def _validate_job_title(self, title: str) -> List[ValidationIssue]:
        """Check if job title can be standardized."""
        issues = []
        title_lower = title.lower().strip()
        
        # Check for common abbreviations
        words = title_lower.split()
        suggestions = []
        
        for word in words:
            if word in self.JOB_TITLE_MAP:
                suggestions.append(self.JOB_TITLE_MAP[word])
        
        if suggestions:
            # Build suggested title
            suggested = title
            for abbr, full in self.JOB_TITLE_MAP.items():
                if abbr in title_lower.split():
                    suggested = re.sub(rf"\b{abbr}\b", full, suggested, flags=re.IGNORECASE)
            
            if suggested != title:
                issues.append(ValidationIssue(
                    field="jobtitle",
                    severity=ValidationSeverity.INFO,
                    message="Job title can be standardized",
                    current_value=title,
                    suggested_value=suggested,
                ))
        
        return issues
    
    def _validate_required_fields(self, contact: Dict[str, Any]) -> List[ValidationIssue]:
        """Check required fields for qualified contacts."""
        issues = []
        
        required = ["firstname", "lastname", "company"]
        for field in required:
            if not contact.get(field):
                issues.append(ValidationIssue(
                    field=field,
                    severity=ValidationSeverity.WARNING,
                    message=f"{field} is recommended for qualified contacts",
                ))
        
        return issues
    
    def _issue_to_dict(self, issue: ValidationIssue) -> Dict[str, Any]:
        """Convert ValidationIssue to dict."""
        return {
            "field": issue.field,
            "severity": issue.severity.value,
            "message": issue.message,
            "current_value": issue.current_value,
            "suggested_value": issue.suggested_value,
        }
