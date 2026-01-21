"""
A/B Testing Framework.

Supports testing different email templates, subject lines, and messaging variations.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import random

logger = logging.getLogger(__name__)


class VariantType(Enum):
    SUBJECT_LINE = "subject_line"
    EMAIL_BODY = "email_body"
    CTA = "cta"
    TONE = "tone"
    SEND_TIME = "send_time"


class TestStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


@dataclass
class Variant:
    """Test variant."""
    id: str
    name: str
    content: str
    description: Optional[str] = None
    
    # Metrics
    impressions: int = 0  # Emails sent
    opens: int = 0
    clicks: int = 0
    replies: int = 0
    meetings: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @property
    def open_rate(self) -> float:
        return (self.opens / self.impressions * 100) if self.impressions > 0 else 0
    
    @property
    def reply_rate(self) -> float:
        return (self.replies / self.impressions * 100) if self.impressions > 0 else 0
    
    @property
    def meeting_rate(self) -> float:
        return (self.meetings / self.impressions * 100) if self.impressions > 0 else 0


@dataclass
class ABTest:
    """A/B test configuration."""
    id: str
    name: str
    variant_type: VariantType
    variants: List[Variant]
    status: TestStatus
    created_at: datetime
    
    # Test configuration
    target_impressions: int = 100
    confidence_threshold: float = 0.95
    persona_filter: Optional[str] = None
    industry_filter: Optional[str] = None
    
    # Winner tracking
    winning_variant_id: Optional[str] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "variant_type": self.variant_type.value,
            "variants": [v.to_dict() for v in self.variants],
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "target_impressions": self.target_impressions,
            "confidence_threshold": self.confidence_threshold,
            "persona_filter": self.persona_filter,
            "industry_filter": self.industry_filter,
            "winning_variant_id": self.winning_variant_id,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_impressions": sum(v.impressions for v in self.variants),
        }


class ABTestingEngine:
    """Manages A/B testing for email campaigns."""
    
    def __init__(self):
        self.tests: Dict[str, ABTest] = {}
        self.assignments: Dict[str, str] = {}  # contact_email -> variant_id
    
    def create_test(
        self,
        name: str,
        variant_type: VariantType,
        variants: List[Dict[str, str]],
        target_impressions: int = 100,
        persona_filter: Optional[str] = None,
        industry_filter: Optional[str] = None,
    ) -> ABTest:
        """Create a new A/B test.
        
        Args:
            name: Test name
            variant_type: What's being tested
            variants: List of variant configs with name and content
            target_impressions: Total impressions before completing
            persona_filter: Optional persona filter
            industry_filter: Optional industry filter
            
        Returns:
            Created test
        """
        test_id = f"test_{uuid.uuid4().hex[:8]}"
        
        variant_objects = [
            Variant(
                id=f"var_{uuid.uuid4().hex[:6]}",
                name=v.get("name", f"Variant {i+1}"),
                content=v.get("content", ""),
                description=v.get("description"),
            )
            for i, v in enumerate(variants)
        ]
        
        test = ABTest(
            id=test_id,
            name=name,
            variant_type=variant_type,
            variants=variant_objects,
            status=TestStatus.DRAFT,
            created_at=datetime.utcnow(),
            target_impressions=target_impressions,
            persona_filter=persona_filter,
            industry_filter=industry_filter,
        )
        
        self.tests[test_id] = test
        logger.info(f"Created A/B test: {name} with {len(variants)} variants")
        
        return test
    
    def start_test(self, test_id: str) -> bool:
        """Start an A/B test."""
        if test_id not in self.tests:
            return False
        
        self.tests[test_id].status = TestStatus.ACTIVE
        logger.info(f"Started A/B test: {test_id}")
        return True
    
    def pause_test(self, test_id: str) -> bool:
        """Pause an A/B test."""
        if test_id not in self.tests:
            return False
        
        self.tests[test_id].status = TestStatus.PAUSED
        return True
    
    def get_variant_for_contact(
        self,
        test_id: str,
        contact_email: str,
    ) -> Optional[Variant]:
        """Get assigned variant for a contact.
        
        Implements sticky assignment - same contact always gets same variant.
        
        Args:
            test_id: Test ID
            contact_email: Contact email
            
        Returns:
            Assigned variant or None
        """
        if test_id not in self.tests:
            return None
        
        test = self.tests[test_id]
        
        if test.status != TestStatus.ACTIVE:
            return None
        
        # Check existing assignment
        assignment_key = f"{test_id}:{contact_email}"
        if assignment_key in self.assignments:
            variant_id = self.assignments[assignment_key]
            return next((v for v in test.variants if v.id == variant_id), None)
        
        # Random assignment
        variant = random.choice(test.variants)
        self.assignments[assignment_key] = variant.id
        
        return variant
    
    def record_impression(
        self,
        test_id: str,
        variant_id: str,
    ):
        """Record that a variant was shown (email sent)."""
        if test_id not in self.tests:
            return
        
        test = self.tests[test_id]
        for variant in test.variants:
            if variant.id == variant_id:
                variant.impressions += 1
                break
        
        # Check if test should complete
        self._check_completion(test_id)
    
    def record_open(
        self,
        test_id: str,
        variant_id: str,
    ):
        """Record email open."""
        if test_id not in self.tests:
            return
        
        test = self.tests[test_id]
        for variant in test.variants:
            if variant.id == variant_id:
                variant.opens += 1
                break
    
    def record_click(
        self,
        test_id: str,
        variant_id: str,
    ):
        """Record link click."""
        if test_id not in self.tests:
            return
        
        test = self.tests[test_id]
        for variant in test.variants:
            if variant.id == variant_id:
                variant.clicks += 1
                break
    
    def record_reply(
        self,
        test_id: str,
        variant_id: str,
    ):
        """Record email reply."""
        if test_id not in self.tests:
            return
        
        test = self.tests[test_id]
        for variant in test.variants:
            if variant.id == variant_id:
                variant.replies += 1
                break
    
    def record_meeting(
        self,
        test_id: str,
        variant_id: str,
    ):
        """Record meeting booked."""
        if test_id not in self.tests:
            return
        
        test = self.tests[test_id]
        for variant in test.variants:
            if variant.id == variant_id:
                variant.meetings += 1
                break
    
    def _check_completion(self, test_id: str):
        """Check if test should complete and determine winner."""
        test = self.tests[test_id]
        
        total_impressions = sum(v.impressions for v in test.variants)
        
        if total_impressions >= test.target_impressions:
            # Find winner based on reply rate
            winner = max(test.variants, key=lambda v: v.reply_rate)
            
            test.status = TestStatus.COMPLETED
            test.winning_variant_id = winner.id
            test.completed_at = datetime.utcnow()
            
            logger.info(f"A/B test {test_id} completed. Winner: {winner.name} ({winner.reply_rate:.1f}% reply rate)")
    
    def get_test_results(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed test results."""
        if test_id not in self.tests:
            return None
        
        test = self.tests[test_id]
        
        return {
            "test": test.to_dict(),
            "results": [
                {
                    "variant_id": v.id,
                    "variant_name": v.name,
                    "impressions": v.impressions,
                    "opens": v.opens,
                    "open_rate": round(v.open_rate, 1),
                    "clicks": v.clicks,
                    "replies": v.replies,
                    "reply_rate": round(v.reply_rate, 1),
                    "meetings": v.meetings,
                    "meeting_rate": round(v.meeting_rate, 1),
                    "is_winner": v.id == test.winning_variant_id,
                }
                for v in test.variants
            ],
        }
    
    def get_active_tests(self) -> List[Dict[str, Any]]:
        """Get all active tests."""
        return [
            t.to_dict() for t in self.tests.values()
            if t.status == TestStatus.ACTIVE
        ]
    
    def list_tests(
        self,
        status: Optional[TestStatus] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """List all tests."""
        tests = list(self.tests.values())
        
        if status:
            tests = [t for t in tests if t.status == status]
        
        return [t.to_dict() for t in sorted(tests, key=lambda x: x.created_at, reverse=True)[:limit]]


# Singleton
_engine: Optional[ABTestingEngine] = None


def get_ab_testing_engine() -> ABTestingEngine:
    """Get singleton A/B testing engine."""
    global _engine
    if _engine is None:
        _engine = ABTestingEngine()
    return _engine


# Preset tests for common scenarios
PRESET_TESTS = {
    "subject_line_personalization": {
        "name": "Subject Line Personalization Test",
        "variant_type": VariantType.SUBJECT_LINE,
        "variants": [
            {"name": "Company Name", "content": "Quick question for {company}"},
            {"name": "First Name", "content": "{first_name}, quick question"},
            {"name": "Role-Based", "content": "For {job_title}s like you"},
        ],
    },
    "cta_urgency": {
        "name": "CTA Urgency Test",
        "variant_type": VariantType.CTA,
        "variants": [
            {"name": "Soft Ask", "content": "Happy to share more if helpful"},
            {"name": "Direct Ask", "content": "Can we find 15 minutes this week?"},
            {"name": "Value First", "content": "Would a demo help evaluate this?"},
        ],
    },
    "tone_variation": {
        "name": "Email Tone Test",
        "variant_type": VariantType.TONE,
        "variants": [
            {"name": "Professional", "content": "professional"},
            {"name": "Conversational", "content": "conversational"},
            {"name": "Direct", "content": "direct"},
        ],
    },
}
