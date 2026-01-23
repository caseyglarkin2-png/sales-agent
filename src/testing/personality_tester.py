"""
Agent Personality A/B Testing System
=====================================

Ship Ship Ship: Test different AI personalities in production!

Implements A/B testing for agent personalities:
- Professional vs Casual
- Brief vs Detailed  
- Formal vs Friendly
- Data-driven vs Storytelling
"""

from typing import Dict, List, Optional
from enum import Enum
from pydantic import BaseModel
from datetime import datetime
import random
import logging

logger = logging.getLogger(__name__)


class PersonalityStyle(str, Enum):
    """Agent personality styles for testing"""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    BRIEF = "brief"
    DETAILED = "detailed"
    FORMAL = "formal"
    FRIENDLY = "friendly"
    DATA_DRIVEN = "data_driven"
    STORYTELLING = "storytelling"


class PersonalityVariant(BaseModel):
    """Personality test variant"""
    id: str
    name: str
    style: PersonalityStyle
    prompt_suffix: str
    tone_keywords: List[str]
    enabled: bool = True
    weight: float = 0.5  # For weighted random selection


# Personality variants for A/B testing
PERSONALITY_VARIANTS = {
    "professional_brief": PersonalityVariant(
        id="professional_brief",
        name="Professional & Brief",
        style=PersonalityStyle.PROFESSIONAL,
        prompt_suffix="Keep responses professional and concise. Use business language. Get to the point quickly.",
        tone_keywords=["professional", "concise", "direct", "businesslike"]
    ),
    "casual_friendly": PersonalityVariant(
        id="casual_friendly",
        name="Casual & Friendly",
        style=PersonalityStyle.CASUAL,
        prompt_suffix="Be conversational and friendly. Use a warm, approachable tone. Make it feel personal.",
        tone_keywords=["casual", "friendly", "warm", "conversational"]
    ),
    "detailed_data": PersonalityVariant(
        id="detailed_data",
        name="Detailed & Data-Driven",
        style=PersonalityStyle.DETAILED,
        prompt_suffix="Provide detailed explanations with specific data points. Back claims with numbers and examples.",
        tone_keywords=["detailed", "analytical", "data-driven", "thorough"]
    ),
    "storytelling": PersonalityVariant(
        id="storytelling",
        name="Storytelling",
        style=PersonalityStyle.STORYTELLING,
        prompt_suffix="Tell a story. Use narrative structure. Paint a picture with words. Make it engaging and memorable.",
        tone_keywords=["narrative", "engaging", "story", "memorable"]
    ),
}


class PersonalityTest(BaseModel):
    """Personality A/B test configuration"""
    test_id: str
    variant_a: str  # Personality variant ID
    variant_b: str  # Personality variant ID
    traffic_split: float = 0.5  # % to variant A (rest to B)
    active: bool = True
    started_at: datetime
    results: Dict[str, Dict] = {}  # variant_id -> metrics


class PersonalityTester:
    """
    Manages personality A/B tests.
    
    Ship Ship Ship: Test in production, learn fast!
    """
    
    def __init__(self):
        self.active_tests: Dict[str, PersonalityTest] = {}
        
    def create_test(
        self,
        test_id: str,
        variant_a: str,
        variant_b: str,
        traffic_split: float = 0.5
    ) -> PersonalityTest:
        """
        Create new personality A/B test.
        
        Args:
            test_id: Unique test identifier
            variant_a: First personality variant ID
            variant_b: Second personality variant ID
            traffic_split: % of traffic to send to variant A
            
        Returns:
            PersonalityTest object
        """
        if variant_a not in PERSONALITY_VARIANTS:
            raise ValueError(f"Unknown variant: {variant_a}")
        if variant_b not in PERSONALITY_VARIANTS:
            raise ValueError(f"Unknown variant: {variant_b}")
            
        test = PersonalityTest(
            test_id=test_id,
            variant_a=variant_a,
            variant_b=variant_b,
            traffic_split=traffic_split,
            active=True,
            started_at=datetime.utcnow(),
            results={
                variant_a: {"impressions": 0, "responses": 0, "positive_outcomes": 0},
                variant_b: {"impressions": 0, "responses": 0, "positive_outcomes": 0}
            }
        )
        
        self.active_tests[test_id] = test
        logger.info(f"Created personality test: {test_id} ({variant_a} vs {variant_b})")
        
        return test
    
    def select_variant(self, test_id: str, user_id: Optional[str] = None) -> PersonalityVariant:
        """
        Select personality variant for request.
        
        Uses consistent hashing on user_id for stable assignment.
        
        Args:
            test_id: Test identifier
            user_id: Optional user ID for consistent assignment
            
        Returns:
            PersonalityVariant to use
        """
        if test_id not in self.active_tests:
            # No test running, use default
            return PERSONALITY_VARIANTS["professional_brief"]
            
        test = self.active_tests[test_id]
        
        if not test.active:
            return PERSONALITY_VARIANTS[test.variant_a]
        
        # Consistent assignment based on user_id
        if user_id:
            # Hash user_id to get consistent variant
            hash_val = hash(user_id) % 100
            if hash_val < (test.traffic_split * 100):
                variant_id = test.variant_a
            else:
                variant_id = test.variant_b
        else:
            # Random selection
            if random.random() < test.traffic_split:
                variant_id = test.variant_a
            else:
                variant_id = test.variant_b
        
        # Track impression
        test.results[variant_id]["impressions"] += 1
        
        return PERSONALITY_VARIANTS[variant_id]
    
    def record_response(self, test_id: str, variant_id: str):
        """Record that user responded to email"""
        if test_id in self.active_tests:
            test = self.active_tests[test_id]
            if variant_id in test.results:
                test.results[variant_id]["responses"] += 1
    
    def record_positive_outcome(self, test_id: str, variant_id: str):
        """Record positive outcome (meeting booked, deal closed, etc)"""
        if test_id in self.active_tests:
            test = self.active_tests[test_id]
            if variant_id in test.results:
                test.results[variant_id]["positive_outcomes"] += 1
    
    def get_test_results(self, test_id: str) -> Dict:
        """
        Get A/B test results with statistics.
        
        Args:
            test_id: Test identifier
            
        Returns:
            Test results with response rates and conversion rates
        """
        if test_id not in self.active_tests:
            return {"error": "Test not found"}
        
        test = self.active_tests[test_id]
        
        results = {}
        for variant_id, metrics in test.results.items():
            impressions = metrics["impressions"]
            responses = metrics["responses"]
            positives = metrics["positive_outcomes"]
            
            response_rate = (responses / impressions * 100) if impressions > 0 else 0
            conversion_rate = (positives / impressions * 100) if impressions > 0 else 0
            
            variant = PERSONALITY_VARIANTS[variant_id]
            
            results[variant_id] = {
                "variant_name": variant.name,
                "style": variant.style,
                "impressions": impressions,
                "responses": responses,
                "positive_outcomes": positives,
                "response_rate": round(response_rate, 2),
                "conversion_rate": round(conversion_rate, 2)
            }
        
        # Calculate winner
        variant_a_conversion = results[test.variant_a]["conversion_rate"]
        variant_b_conversion = results[test.variant_b]["conversion_rate"]
        
        if variant_a_conversion > variant_b_conversion:
            winner = test.variant_a
            lift = ((variant_a_conversion - variant_b_conversion) / variant_b_conversion * 100) if variant_b_conversion > 0 else 0
        elif variant_b_conversion > variant_a_conversion:
            winner = test.variant_b
            lift = ((variant_b_conversion - variant_a_conversion) / variant_a_conversion * 100) if variant_a_conversion > 0 else 0
        else:
            winner = None
            lift = 0
        
        return {
            "test_id": test_id,
            "started_at": test.started_at,
            "active": test.active,
            "variants": results,
            "winner": winner,
            "lift_percentage": round(lift, 2) if winner else 0
        }
    
    def stop_test(self, test_id: str):
        """Stop running test"""
        if test_id in self.active_tests:
            self.active_tests[test_id].active = False
            logger.info(f"Stopped personality test: {test_id}")


# Global tester instance
personality_tester = PersonalityTester()


# Ship Ship Ship: Create default test
DEFAULT_TEST = personality_tester.create_test(
    test_id="default_personality_test",
    variant_a="professional_brief",
    variant_b="casual_friendly",
    traffic_split=0.5
)
