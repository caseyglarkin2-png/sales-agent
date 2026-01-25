"""
Tests for Email Safety Checks Module
"""

import pytest
from src.email_utils.email_safety import (
    check_email_safety,
    SafetyViolationType,
    SafetyCheckResult,
)


class TestPIIDetection:
    """Tests for PII detection"""
    
    def test_detects_ssn_with_dashes(self):
        """Should detect SSN in format XXX-XX-XXXX"""
        result = check_email_safety(
            to_email="test@example.com",
            subject="Application",
            body_text="My SSN is 123-45-6789",
            require_unsubscribe=False,
        )
        
        assert not result.is_safe
        assert len(result.violations) == 1
        assert result.violations[0]["type"] == SafetyViolationType.PII_DETECTED.value
        assert "Social Security Number" in result.violations[0]["detail"]
    
    def test_detects_credit_card_number(self):
        """Should detect credit card numbers"""
        result = check_email_safety(
            to_email="test@example.com",
            subject="Payment",
            body_text="Card: 4532-1234-5678-9010",
            require_unsubscribe=False,
        )
        
        assert not result.is_safe
        assert any(
            v["type"] == SafetyViolationType.PII_DETECTED.value
            for v in result.violations
        )
    
    def test_warns_on_9_digit_numbers(self):
        """Should warn on 9-digit numbers (potential SSN without dashes)"""
        result = check_email_safety(
            to_email="test@example.com",
            subject="Order",
            body_text="Order number: 123456789",
            require_unsubscribe=False,
        )
        
        # Should warn but not block (could be legitimate order number)
        assert result.is_safe or len(result.warnings) > 0
    
    def test_allows_clean_content(self):
        """Should pass clean content with no PII"""
        result = check_email_safety(
            to_email="test@example.com",
            subject="Hello",
            body_text="Hi there, how are you?",
            require_unsubscribe=False,
        )
        
        # Should pass (no PII violations)
        pii_violations = [
            v for v in result.violations
            if v["type"] == SafetyViolationType.PII_DETECTED.value
        ]
        assert len(pii_violations) == 0


class TestProhibitedContent:
    """Tests for prohibited content detection"""
    
    def test_detects_guarantee(self):
        """Should detect 'guarantee' spam trigger"""
        result = check_email_safety(
            to_email="test@example.com",
            subject="Special offer",
            body_text="We guarantee 100% satisfaction!",
            require_unsubscribe=False,
        )
        
        assert not result.is_safe
        prohibited_violations = [
            v for v in result.violations
            if v["type"] == SafetyViolationType.PROHIBITED_CONTENT.value
        ]
        assert len(prohibited_violations) > 0
        assert "guarantee" in prohibited_violations[0]["detail"].lower()
    
    def test_detects_multiple_prohibited_terms(self):
        """Should detect multiple prohibited terms"""
        result = check_email_safety(
            to_email="test@example.com",
            subject="Amazing deal",
            body_text="Act now for this limited time offer! 100% free with no risk!",
            require_unsubscribe=False,
        )
        
        assert not result.is_safe
        prohibited_violations = [
            v for v in result.violations
            if v["type"] == SafetyViolationType.PROHIBITED_CONTENT.value
        ]
        assert len(prohibited_violations) > 0
        # Should list multiple terms
        violation_detail = prohibited_violations[0]["detail"]
        assert "act now" in violation_detail.lower()
        assert "limited time" in violation_detail.lower()
    
    def test_allows_professional_language(self):
        """Should allow professional business language"""
        result = check_email_safety(
            to_email="test@example.com",
            subject="Q1 Meeting",
            body_text="Looking forward to our quarterly review meeting.",
            require_unsubscribe=False,
        )
        
        prohibited_violations = [
            v for v in result.violations
            if v["type"] == SafetyViolationType.PROHIBITED_CONTENT.value
        ]
        assert len(prohibited_violations) == 0


class TestUnsubscribeLink:
    """Tests for unsubscribe link validation"""
    
    def test_requires_unsubscribe_link(self):
        """Should require unsubscribe link when require_unsubscribe=True"""
        result = check_email_safety(
            to_email="test@example.com",
            subject="Newsletter",
            body_text="Here's our latest news.",
            require_unsubscribe=True,
        )
        
        assert not result.is_safe
        unsub_violations = [
            v for v in result.violations
            if v["type"] == SafetyViolationType.MISSING_UNSUBSCRIBE.value
        ]
        assert len(unsub_violations) == 1
    
    def test_detects_unsubscribe_in_text(self):
        """Should detect unsubscribe link in plain text"""
        result = check_email_safety(
            to_email="test@example.com",
            subject="Newsletter",
            body_text="News here.\n\nTo unsubscribe, click here: http://example.com/unsub",
            require_unsubscribe=True,
        )
        
        unsub_violations = [
            v for v in result.violations
            if v["type"] == SafetyViolationType.MISSING_UNSUBSCRIBE.value
        ]
        assert len(unsub_violations) == 0
    
    def test_detects_opt_out_variant(self):
        """Should detect 'opt-out' as valid unsubscribe"""
        result = check_email_safety(
            to_email="test@example.com",
            subject="Update",
            body_text="Update here. Opt-out anytime.",
            require_unsubscribe=True,
        )
        
        unsub_violations = [
            v for v in result.violations
            if v["type"] == SafetyViolationType.MISSING_UNSUBSCRIBE.value
        ]
        assert len(unsub_violations) == 0
    
    def test_skips_check_when_not_required(self):
        """Should skip unsubscribe check when require_unsubscribe=False"""
        result = check_email_safety(
            to_email="test@example.com",
            subject="Personal email",
            body_text="Hi, how are you?",
            require_unsubscribe=False,
        )
        
        # Should not have unsubscribe violation
        unsub_violations = [
            v for v in result.violations
            if v["type"] == SafetyViolationType.MISSING_UNSUBSCRIBE.value
        ]
        assert len(unsub_violations) == 0


class TestRecipientChecks:
    """Tests for recipient allowlist/denylist"""
    
    def test_blocks_denylisted_email(self):
        """Should block emails to denylisted recipients"""
        result = check_email_safety(
            to_email="spam@example.com",
            subject="Test",
            body_text="Test",
            require_unsubscribe=False,
            recipient_denylist=["spam@example.com"],
        )
        
        assert not result.is_safe
        blocked_violations = [
            v for v in result.violations
            if v["type"] == SafetyViolationType.BLOCKED_RECIPIENT.value
        ]
        assert len(blocked_violations) == 1
        assert "denylist" in blocked_violations[0]["detail"]
    
    def test_blocks_denylisted_domain(self):
        """Should block emails to denylisted domains"""
        result = check_email_safety(
            to_email="anyone@blocked.com",
            subject="Test",
            body_text="Test",
            require_unsubscribe=False,
            recipient_denylist=["blocked.com"],
        )
        
        assert not result.is_safe
        blocked_violations = [
            v for v in result.violations
            if v["type"] == SafetyViolationType.BLOCKED_RECIPIENT.value
        ]
        assert len(blocked_violations) == 1
    
    def test_allows_allowlisted_email(self):
        """Should allow emails to allowlisted recipients"""
        result = check_email_safety(
            to_email="safe@example.com",
            subject="Test",
            body_text="Test",
            require_unsubscribe=False,
            recipient_allowlist=["safe@example.com"],
        )
        
        blocked_violations = [
            v for v in result.violations
            if v["type"] == SafetyViolationType.BLOCKED_RECIPIENT.value
        ]
        assert len(blocked_violations) == 0
    
    def test_blocks_non_allowlisted_when_allowlist_provided(self):
        """Should block emails NOT on allowlist when allowlist provided"""
        result = check_email_safety(
            to_email="notlisted@example.com",
            subject="Test",
            body_text="Test",
            require_unsubscribe=False,
            recipient_allowlist=["safe@example.com"],
        )
        
        assert not result.is_safe
        blocked_violations = [
            v for v in result.violations
            if v["type"] == SafetyViolationType.BLOCKED_RECIPIENT.value
        ]
        assert len(blocked_violations) == 1
        assert "not on allowlist" in blocked_violations[0]["detail"]


class TestSuspiciousPatterns:
    """Tests for suspicious pattern detection"""
    
    def test_warns_on_excessive_caps(self):
        """Should warn on excessive capitalization"""
        result = check_email_safety(
            to_email="test@example.com",
            subject="URGENT",
            body_text="THIS IS VERY IMPORTANT PLEASE READ NOW!!!",
            require_unsubscribe=False,
        )
        
        # Should have warning about capitalization
        assert len(result.warnings) > 0
        assert any("capitalization" in w["detail"].lower() for w in result.warnings)
    
    def test_warns_on_excessive_exclamations(self):
        """Should warn on too many exclamation marks"""
        result = check_email_safety(
            to_email="test@example.com",
            subject="Great news!!!!",
            body_text="This is amazing!!!! You won't believe it!!!!",
            require_unsubscribe=False,
        )
        
        # Should have warning about exclamation marks
        assert len(result.warnings) > 0
        assert any("exclamation" in w["detail"].lower() for w in result.warnings)
    
    def test_allows_normal_formatting(self):
        """Should allow normal professional formatting"""
        result = check_email_safety(
            to_email="test@example.com",
            subject="Quarterly Review",
            body_text="Looking forward to our meeting. Let me know if you have questions.",
            require_unsubscribe=False,
        )
        
        # Should have no warnings about formatting
        formatting_warnings = [
            w for w in result.warnings
            if "capitalization" in w["detail"].lower() or "exclamation" in w["detail"].lower()
        ]
        assert len(formatting_warnings) == 0


class TestIntegration:
    """Integration tests for complete safety checks"""
    
    def test_safe_email_passes_all_checks(self):
        """Should pass a completely safe, professional email"""
        result = check_email_safety(
            to_email="john@techcorp.com",
            subject="Q1 Supply Chain Discussion",
            body_text="Hi John,\n\nLooking forward to our meeting.\n\nBest,\nSales Team\n\nUnsubscribe: http://example.com/unsub",
            require_unsubscribe=True,
        )
        
        assert result.is_safe
        assert len(result.violations) == 0
    
    def test_dangerous_email_fails_multiple_checks(self):
        """Should fail an email with multiple violations"""
        result = check_email_safety(
            to_email="spam@noreply.com",
            subject="You won!!!",
            body_text="ACT NOW!!! Your SSN 123-45-6789 won FREE MONEY! 100% GUARANTEED!!!",
            require_unsubscribe=True,
        )
        
        assert not result.is_safe
        assert len(result.violations) >= 3  # PII + prohibited + missing unsubscribe
        
        # Check all violation types present
        violation_types = {v["type"] for v in result.violations}
        assert SafetyViolationType.PII_DETECTED.value in violation_types
        assert SafetyViolationType.PROHIBITED_CONTENT.value in violation_types
        assert SafetyViolationType.MISSING_UNSUBSCRIBE.value in violation_types
