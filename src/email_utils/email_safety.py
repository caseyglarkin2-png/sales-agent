"""
Email Safety Checks Module

Validates emails before sending to prevent:
- PII leakage (SSN, credit card numbers)
- Prohibited content (spam triggers, guarantees)
- Compliance violations (missing unsubscribe links)
- Recipient blocklist violations
"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class SafetyViolationType(str, Enum):
    """Types of safety violations"""
    PII_DETECTED = "pii_detected"
    PROHIBITED_CONTENT = "prohibited_content"
    MISSING_UNSUBSCRIBE = "missing_unsubscribe"
    BLOCKED_RECIPIENT = "blocked_recipient"
    SUSPICIOUS_PATTERN = "suspicious_pattern"


@dataclass
class SafetyCheckResult:
    """Result of email safety check"""
    is_safe: bool
    violations: List[Dict[str, str]]
    warnings: List[Dict[str, str]]
    
    def add_violation(self, violation_type: SafetyViolationType, detail: str):
        """Add a safety violation"""
        self.is_safe = False
        self.violations.append({
            "type": violation_type.value,
            "detail": detail
        })
    
    def add_warning(self, warning_type: str, detail: str):
        """Add a warning (doesn't block send)"""
        self.warnings.append({
            "type": warning_type,
            "detail": detail
        })


# PII Patterns
SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
SSN_NO_DASH_PATTERN = re.compile(r'\b\d{9}\b')
CREDIT_CARD_PATTERN = re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b')

# Prohibited Terms (spam triggers, legal landmines)
PROHIBITED_TERMS = [
    "guarantee",
    "guaranteed",
    "100% free",
    "risk-free",
    "no risk",
    "promise",
    "promised",
    "free money",
    "act now",
    "limited time",
    "click here",
    "cash bonus",
    "you have been selected",
    "winner",
    "congratulations you",
    "claim your",
]

# Unsubscribe link patterns
UNSUBSCRIBE_PATTERNS = [
    re.compile(r'unsubscribe', re.IGNORECASE),
    re.compile(r'opt[- ]?out', re.IGNORECASE),
    re.compile(r'preferences', re.IGNORECASE),
]

# Recipient denylist (example - would be loaded from database)
BLOCKED_DOMAINS = [
    "donotreply.com",
    "noreply.com",
    "blackhole.com",
]


def check_email_safety(
    to_email: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    require_unsubscribe: bool = True,
    recipient_allowlist: Optional[List[str]] = None,
    recipient_denylist: Optional[List[str]] = None,
) -> SafetyCheckResult:
    """
    Comprehensive email safety check
    
    Args:
        to_email: Recipient email address
        subject: Email subject line
        body_text: Plain text email body
        body_html: HTML email body (optional)
        require_unsubscribe: Whether to require unsubscribe link (default: True)
        recipient_allowlist: List of allowed recipient emails/domains
        recipient_denylist: List of blocked recipient emails/domains
    
    Returns:
        SafetyCheckResult with is_safe flag and violation/warning details
    """
    result = SafetyCheckResult(is_safe=True, violations=[], warnings=[])
    
    # Combine all content for checking
    full_content = f"{subject} {body_text}"
    if body_html:
        full_content += f" {body_html}"
    
    # Check 1: PII Detection
    _check_pii(full_content, result)
    
    # Check 2: Prohibited Content
    _check_prohibited_content(full_content, result)
    
    # Check 3: Unsubscribe Link (if required)
    if require_unsubscribe:
        _check_unsubscribe_link(body_text, body_html, result)
    
    # Check 4: Recipient Blocklist
    _check_recipient(to_email, recipient_allowlist, recipient_denylist, result)
    
    # Check 5: Suspicious Patterns
    _check_suspicious_patterns(full_content, result)
    
    return result


def _check_pii(content: str, result: SafetyCheckResult):
    """Check for PII patterns (SSN, credit cards)"""
    
    # SSN with dashes (123-45-6789)
    if SSN_PATTERN.search(content):
        result.add_violation(
            SafetyViolationType.PII_DETECTED,
            "Social Security Number detected (format: XXX-XX-XXXX)"
        )
    
    # 9-digit number (could be SSN without dashes)
    ssn_no_dash_matches = SSN_NO_DASH_PATTERN.findall(content)
    if ssn_no_dash_matches:
        result.add_warning(
            "possible_pii",
            f"Found {len(ssn_no_dash_matches)} 9-digit number(s) - may be SSN without dashes"
        )
    
    # Credit card numbers
    if CREDIT_CARD_PATTERN.search(content):
        result.add_violation(
            SafetyViolationType.PII_DETECTED,
            "Credit card number detected"
        )


def _check_prohibited_content(content: str, result: SafetyCheckResult):
    """Check for prohibited terms (spam triggers, legal issues)"""
    content_lower = content.lower()
    
    found_terms = []
    for term in PROHIBITED_TERMS:
        if term in content_lower:
            found_terms.append(term)
    
    if found_terms:
        result.add_violation(
            SafetyViolationType.PROHIBITED_CONTENT,
            f"Prohibited terms detected: {', '.join(found_terms)}"
        )


def _check_unsubscribe_link(
    body_text: str,
    body_html: Optional[str],
    result: SafetyCheckResult
):
    """Check for unsubscribe link (compliance requirement)"""
    
    # Check text body
    has_unsubscribe = any(
        pattern.search(body_text)
        for pattern in UNSUBSCRIBE_PATTERNS
    )
    
    # Also check HTML if provided
    if not has_unsubscribe and body_html:
        has_unsubscribe = any(
            pattern.search(body_html)
            for pattern in UNSUBSCRIBE_PATTERNS
        )
    
    if not has_unsubscribe:
        result.add_violation(
            SafetyViolationType.MISSING_UNSUBSCRIBE,
            "Email missing unsubscribe link or opt-out mechanism (required for compliance)"
        )


def _check_recipient(
    to_email: str,
    allowlist: Optional[List[str]],
    denylist: Optional[List[str]],
    result: SafetyCheckResult
):
    """Check recipient against allowlist/denylist"""
    
    # Extract domain from email
    domain = to_email.split('@')[-1] if '@' in to_email else None
    
    # Check denylist first (takes precedence)
    if denylist:
        for blocked in denylist:
            if blocked in to_email or (domain and blocked == domain):
                result.add_violation(
                    SafetyViolationType.BLOCKED_RECIPIENT,
                    f"Recipient {to_email} is on denylist"
                )
                return
    
    # Check global blocked domains
    if domain and domain in BLOCKED_DOMAINS:
        result.add_violation(
            SafetyViolationType.BLOCKED_RECIPIENT,
            f"Domain {domain} is globally blocked"
        )
        return
    
    # Check allowlist (if provided, email MUST be on it)
    if allowlist:
        is_allowed = any(
            allowed in to_email or (domain and allowed == domain)
            for allowed in allowlist
        )
        if not is_allowed:
            result.add_violation(
                SafetyViolationType.BLOCKED_RECIPIENT,
                f"Recipient {to_email} not on allowlist"
            )


def _check_suspicious_patterns(content: str, result: SafetyCheckResult):
    """Check for suspicious patterns that may indicate spam/phishing"""
    
    # Excessive caps (more than 30% of content)
    caps_count = sum(1 for c in content if c.isupper())
    total_alpha = sum(1 for c in content if c.isalpha())
    
    if total_alpha > 0:
        caps_ratio = caps_count / total_alpha
        if caps_ratio > 0.3:
            result.add_warning(
                "suspicious_formatting",
                f"Excessive capitalization ({caps_ratio:.0%}) may trigger spam filters"
            )
    
    # Excessive exclamation marks (more than 3)
    exclamation_count = content.count('!')
    if exclamation_count > 3:
        result.add_warning(
            "suspicious_formatting",
            f"Excessive exclamation marks ({exclamation_count}) may trigger spam filters"
        )
    
    # Multiple dollar signs (potential scam indicator)
    dollar_count = content.count('$')
    if dollar_count > 2:
        result.add_warning(
            "suspicious_content",
            f"Multiple dollar signs ({dollar_count}) may appear promotional"
        )
