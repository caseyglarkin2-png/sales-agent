"""
PII (Personally Identifiable Information) detection and redaction.

Detects and optionally redacts sensitive information:
- Email addresses
- Phone numbers
- SSNs
- Credit card numbers
- API keys/tokens
- Physical addresses
"""
import re
import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class PIIType(str, Enum):
    """Types of PII that can be detected."""
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    API_KEY = "api_key"
    ADDRESS = "address"
    IP_ADDRESS = "ip_address"
    DOB = "date_of_birth"


class PIIDetector:
    """Detect PII in text content."""
    
    # Regex patterns for different PII types
    PATTERNS = {
        PIIType.EMAIL: r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        PIIType.PHONE: r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
        PIIType.SSN: r'\b\d{3}-\d{2}-\d{4}\b',
        PIIType.CREDIT_CARD: r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        PIIType.IP_ADDRESS: r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
        
        # API keys (generic patterns)
        PIIType.API_KEY: r'\b(?:api[_-]?key|token|secret|password|pwd)\s*[=:]\s*[\'"]?([A-Za-z0-9_\-]{20,})[\'"]?',
    }
    
    def __init__(self, confidence_threshold: float = 0.7):
        """
        Initialize PII detector.
        
        Args:
            confidence_threshold: Minimum confidence to flag as PII (0.0-1.0)
        """
        self.confidence_threshold = confidence_threshold
        self.compiled_patterns = {
            pii_type: re.compile(pattern, re.IGNORECASE)
            for pii_type, pattern in self.PATTERNS.items()
        }
    
    def detect(self, text: str, include_positions: bool = False) -> Dict[PIIType, List]:
        """
        Detect PII in text.
        
        Args:
            text: Text to scan
            include_positions: If True, include match positions
        
        Returns:
            {
                PIIType.EMAIL: ["user@example.com", ...],
                PIIType.PHONE: ["555-1234", ...],
                ...
            }
        """
        results = {}
        
        for pii_type, pattern in self.compiled_patterns.items():
            matches = pattern.finditer(text)
            
            if include_positions:
                results[pii_type] = [
                    {
                        "value": match.group(0),
                        "start": match.start(),
                        "end": match.end(),
                        "confidence": self._calculate_confidence(pii_type, match.group(0))
                    }
                    for match in matches
                ]
            else:
                results[pii_type] = list(set(match.group(0) for match in matches))
            
            # Filter by confidence
            if include_positions:
                results[pii_type] = [
                    item for item in results[pii_type]
                    if item["confidence"] >= self.confidence_threshold
                ]
        
        # Remove empty results
        results = {k: v for k, v in results.items() if v}
        
        return results
    
    def _calculate_confidence(self, pii_type: PIIType, value: str) -> float:
        """
        Calculate confidence score for detected PII.
        
        Args:
            pii_type: Type of PII
            value: Detected value
        
        Returns:
            Confidence score (0.0-1.0)
        """
        # Basic heuristics for confidence scoring
        if pii_type == PIIType.EMAIL:
            # Check for common TLDs
            if any(value.endswith(tld) for tld in ['.com', '.org', '.net', '.edu', '.gov']):
                return 0.95
            return 0.75
        
        elif pii_type == PIIType.PHONE:
            # Check for valid area codes (US)
            digits = ''.join(c for c in value if c.isdigit())
            if len(digits) == 10:
                area_code = int(digits[:3])
                if 200 <= area_code <= 999:
                    return 0.9
            return 0.7
        
        elif pii_type == PIIType.SSN:
            # SSN format check
            digits = ''.join(c for c in value if c.isdigit())
            if len(digits) == 9:
                # Check for invalid SSNs (000, 666, 900+)
                area = int(digits[:3])
                if area == 0 or area == 666 or area >= 900:
                    return 0.3
                return 0.95
            return 0.5
        
        elif pii_type == PIIType.CREDIT_CARD:
            # Luhn algorithm check
            digits = ''.join(c for c in value if c.isdigit())
            if self._luhn_check(digits):
                return 0.95
            return 0.5
        
        elif pii_type == PIIType.API_KEY:
            # Check length and entropy
            if len(value) >= 32:
                return 0.9
            return 0.7
        
        return 0.8  # Default confidence
    
    @staticmethod
    def _luhn_check(card_number: str) -> bool:
        """Validate credit card using Luhn algorithm."""
        def digits_of(n):
            return [int(d) for d in str(n)]
        
        digits = digits_of(card_number)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        
        for d in even_digits:
            checksum += sum(digits_of(d * 2))
        
        return checksum % 10 == 0
    
    def has_pii(self, text: str) -> bool:
        """
        Check if text contains any PII.
        
        Args:
            text: Text to check
        
        Returns:
            True if PII detected
        """
        detected = self.detect(text)
        return len(detected) > 0
    
    def redact(self, text: str, redaction_char: str = "X", partial: bool = True) -> Tuple[str, Dict]:
        """
        Redact PII from text.
        
        Args:
            text: Text to redact
            redaction_char: Character to use for redaction
            partial: If True, partially redact (e.g., email: u***@example.com)
        
        Returns:
            (redacted_text, redaction_map)
        """
        detected = self.detect(text, include_positions=True)
        redacted_text = text
        redaction_map = {}
        
        # Sort matches by position (reverse order to maintain positions)
        all_matches = []
        for pii_type, matches in detected.items():
            for match in matches:
                all_matches.append((pii_type, match))
        
        all_matches.sort(key=lambda x: x[1]["start"], reverse=True)
        
        # Redact each match
        for pii_type, match in all_matches:
            original = match["value"]
            start = match["start"]
            end = match["end"]
            
            if partial:
                redacted = self._partial_redact(original, pii_type, redaction_char)
            else:
                redacted = redaction_char * len(original)
            
            redacted_text = redacted_text[:start] + redacted + redacted_text[end:]
            
            # Track redaction
            if pii_type not in redaction_map:
                redaction_map[pii_type] = []
            redaction_map[pii_type].append({
                "original": original,
                "redacted": redacted,
                "position": start
            })
        
        return redacted_text, redaction_map
    
    def _partial_redact(self, value: str, pii_type: PIIType, char: str = "X") -> str:
        """Partially redact value based on type."""
        if pii_type == PIIType.EMAIL:
            # Redact username: u***@domain.com
            parts = value.split('@')
            if len(parts) == 2:
                username = parts[0][0] + char * (len(parts[0]) - 1)
                return f"{username}@{parts[1]}"
        
        elif pii_type == PIIType.PHONE:
            # Redact middle digits: (555) ***-1234
            digits = ''.join(c for c in value if c.isdigit())
            if len(digits) >= 10:
                return f"({digits[:3]}) {char*3}-{digits[-4:]}"
        
        elif pii_type == PIIType.SSN:
            # Redact first 5 digits: ***-**-1234
            digits = ''.join(c for c in value if c.isdigit())
            if len(digits) == 9:
                return f"{char*3}-{char*2}-{digits[-4:]}"
        
        elif pii_type == PIIType.CREDIT_CARD:
            # Redact middle digits: **** **** **** 1234
            digits = ''.join(c for c in value if c.isdigit())
            if len(digits) >= 12:
                return f"{char*4} {char*4} {char*4} {digits[-4:]}"
        
        # Default: redact all but last 4 chars
        if len(value) > 4:
            return char * (len(value) - 4) + value[-4:]
        return char * len(value)


class PIISafetyValidator:
    """Validate content safety before sending."""
    
    def __init__(self, strict_mode: bool = True):
        """
        Initialize safety validator.
        
        Args:
            strict_mode: If True, block on any PII detection
        """
        self.strict_mode = strict_mode
        self.detector = PIIDetector()
    
    def validate(self, content: str, context: str = "email") -> Dict:
        """
        Validate content safety.
        
        Args:
            content: Content to validate
            context: Context (email, draft, message)
        
        Returns:
            {
                "safe": bool,
                "warnings": List[str],
                "pii_detected": Dict,
                "risk_score": float (0.0-1.0),
                "recommendation": str
            }
        """
        pii_detected = self.detector.detect(content, include_positions=True)
        warnings = []
        risk_score = 0.0
        
        # Calculate risk based on PII types
        if PIIType.SSN in pii_detected or PIIType.CREDIT_CARD in pii_detected:
            risk_score = 1.0
            warnings.append("HIGH RISK: Financial/identity information detected")
        
        if PIIType.API_KEY in pii_detected:
            risk_score = max(risk_score, 0.9)
            warnings.append("CRITICAL: API keys or tokens detected")
        
        if PIIType.EMAIL in pii_detected:
            risk_score = max(risk_score, 0.3)
            if len(pii_detected[PIIType.EMAIL]) > 3:
                warnings.append("Multiple email addresses detected")
        
        if PIIType.PHONE in pii_detected:
            risk_score = max(risk_score, 0.2)
        
        # Determine if safe
        safe = True
        if self.strict_mode and pii_detected:
            safe = False
        elif risk_score >= 0.8:
            safe = False
        
        # Recommendation
        if risk_score >= 0.8:
            recommendation = "BLOCK: Do not send. Remove sensitive information."
        elif risk_score >= 0.5:
            recommendation = "REVIEW: Manual review required before sending."
        elif pii_detected:
            recommendation = "CAUTION: PII detected. Verify necessity."
        else:
            recommendation = "SAFE: No PII detected."
        
        return {
            "safe": safe,
            "warnings": warnings,
            "pii_detected": {k.value: v for k, v in pii_detected.items()},
            "risk_score": risk_score,
            "recommendation": recommendation
        }
