"""
AI-Powered Reply Classifier
============================
Classifies email replies to determine intent, sentiment, and recommended actions.
Uses OpenAI for intelligent classification with fallback pattern matching.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)


class ReplyIntent(str, Enum):
    """Classified intent of a reply."""
    INTERESTED = "interested"              # Expressing interest, wants more info
    MEETING_REQUEST = "meeting_request"    # Wants to schedule a meeting
    MEETING_CONFIRMED = "meeting_confirmed" # Confirmed a meeting time
    QUESTION = "question"                   # Has questions
    OBJECTION = "objection"                 # Price, timing, competitor objection
    NOT_NOW = "not_now"                     # Not right time, maybe later
    NOT_INTERESTED = "not_interested"       # Clear no
    UNSUBSCRIBE = "unsubscribe"             # Wants to opt out
    OUT_OF_OFFICE = "out_of_office"         # Auto-reply, OOO
    BOUNCE = "bounce"                       # Email bounced
    REFERRAL = "referral"                   # Referring to someone else
    POSITIVE_FEEDBACK = "positive_feedback" # Thanks, appreciation
    UNCLEAR = "unclear"                     # Can't determine intent


class SentimentLevel(str, Enum):
    """Sentiment analysis of reply."""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


@dataclass
class ReplyClassification:
    """Result of reply classification."""
    intent: ReplyIntent
    confidence: float  # 0.0 to 1.0
    sentiment: SentimentLevel
    urgency: int  # 1-5, where 5 is most urgent
    key_phrases: list[str] = field(default_factory=list)
    objection_type: Optional[str] = None  # If intent is OBJECTION
    referral_contact: Optional[str] = None  # If intent is REFERRAL
    meeting_preference: Optional[str] = None  # If meeting-related
    recommended_action: str = ""
    follow_up_priority: int = 3  # 1-5, where 5 is highest priority
    classification_method: str = "pattern"  # pattern or ai
    classified_at: datetime = field(default_factory=datetime.utcnow)
    raw_analysis: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "intent": self.intent.value,
            "confidence": self.confidence,
            "sentiment": self.sentiment.value,
            "urgency": self.urgency,
            "key_phrases": self.key_phrases,
            "objection_type": self.objection_type,
            "referral_contact": self.referral_contact,
            "meeting_preference": self.meeting_preference,
            "recommended_action": self.recommended_action,
            "follow_up_priority": self.follow_up_priority,
            "classification_method": self.classification_method,
            "classified_at": self.classified_at.isoformat(),
        }


# Pattern matching rules
INTENT_PATTERNS = {
    ReplyIntent.OUT_OF_OFFICE: [
        r"out of (?:the )?office",
        r"away from (?:my )?(?:desk|email)",
        r"on (?:vacation|holiday|leave|pto)",
        r"automatic reply",
        r"auto[- ]?reply",
        r"will (?:be|return) (?:back )?(?:on|after)",
        r"limited access to email",
        r"currently (?:out|away|traveling)",
    ],
    ReplyIntent.BOUNCE: [
        r"delivery (?:has )?failed",
        r"undeliverable",
        r"mail(?:box)? (?:is )?(?:full|unavailable)",
        r"user (?:unknown|not found)",
        r"address rejected",
        r"permanent failure",
        r"550 (?:\d\.)+",
        r"does not exist",
    ],
    ReplyIntent.UNSUBSCRIBE: [
        r"unsubscribe",
        r"remove (?:me|us) from",
        r"stop (?:sending|emailing|contacting)",
        r"opt[- ]?out",
        r"do not contact",
        r"take me off",
        r"no longer interested",
    ],
    ReplyIntent.NOT_INTERESTED: [
        r"not interested",
        r"no(?:t)? thank(?:s| you)",
        r"we(?:'re| are) (?:all )?set",
        r"we(?:'re| are) (?:not )?looking",
        r"please don'?t (?:contact|email)",
        r"not a (?:fit|match|priority)",
        r"already (?:have|use|using)",
        r"happy with (?:current|our|what we have)",
    ],
    ReplyIntent.NOT_NOW: [
        r"not (?:right )?now",
        r"maybe (?:later|next)",
        r"reach out (?:in|next)",
        r"circle back",
        r"not a good time",
        r"(?:busy|swamped) (?:right )?now",
        r"check back (?:in|later|next)",
        r"(?:q[1-4]|next (?:month|quarter|year))",
    ],
    ReplyIntent.MEETING_REQUEST: [
        r"(?:can we|let'?s) (?:schedule|set up|book|arrange|find)",
        r"(?:free|available|open) (?:for a|to) (?:call|chat|meeting)",
        r"(?:hop on|jump on) a (?:call|zoom|meeting)",
        r"(?:when|what time) (?:works|is good)",
        r"send (?:me )?(?:a )?(?:calendar|meeting) (?:invite|link)",
        r"calendly",
        r"(?:15|30|45|60) minutes?",
    ],
    ReplyIntent.MEETING_CONFIRMED: [
        r"(?:see you|talk to you) (?:on|at|then)",
        r"(?:confirmed|booked|scheduled)",
        r"(?:looking|look) forward to (?:it|meeting|talking)",
        r"(?:sounds|works) (?:good|great|perfect)",
        r"(?:i'?ll|we'?ll) be there",
        r"calendar invite (?:sent|received|accepted)",
    ],
    ReplyIntent.INTERESTED: [
        r"(?:i'?m|we'?re) interested",
        r"(?:tell|send) (?:me|us) more",
        r"(?:sounds|looks) (?:interesting|good|great)",
        r"(?:i|we) (?:want|would like) to (?:learn|know|hear) more",
        r"how does (?:it|this) work",
        r"(?:what are|tell me about) (?:your|the) (?:pricing|features)",
        r"(?:sign|signed) (?:me|us) up",
    ],
    ReplyIntent.QUESTION: [
        r"^(?:what|how|when|where|who|why|can|could|do|does|is|are|will)\b.*\?",
        r"(?:curious|wondering) (?:about|if)",
        r"(?:can you|could you) (?:explain|clarify|tell me)",
        r"(?:i|we) (?:have|had) (?:a )?questions?",
        r"(?:what|how) (?:about|is)",
    ],
    ReplyIntent.OBJECTION: [
        r"(?:too )?expensive",
        r"(?:over )?budget",
        r"(?:cost|price|pricing) (?:is|seems)",
        r"(?:already|currently) (?:using|have|with)",
        r"(?:happy|satisfied) with (?:current|our)",
        r"(?:don'?t|we) (?:need|see the need)",
        r"(?:competitor|alternative)",
        r"(?:not|isn'?t) (?:a )?(?:priority|fit)",
    ],
    ReplyIntent.REFERRAL: [
        r"(?:talk|speak|connect) (?:to|with) (?:my|our)",
        r"(?:reach out to|contact|email|cc)",
        r"(?:forward|forwarding|sent) (?:this )?to",
        r"(?:right|better) person (?:to|would be)",
        r"(?:copied|cc'?d|looping in)",
        r"handles? (?:this|these)",
    ],
    ReplyIntent.POSITIVE_FEEDBACK: [
        r"^thanks?(?:\s+(?:you|so much))?[!.]?$",
        r"(?:appreciate|appreciated)",
        r"(?:helpful|useful|great) (?:info|information|email)",
        r"(?:thank(?:s| you) for (?:reaching out|the info))",
    ],
}

# Sentiment indicators
POSITIVE_INDICATORS = [
    "great", "excellent", "perfect", "wonderful", "fantastic", "amazing",
    "love", "excited", "interested", "looking forward", "appreciate",
    "thanks", "thank you", "helpful", "sounds good", "works for me",
]

NEGATIVE_INDICATORS = [
    "unfortunately", "sorry", "can't", "cannot", "won't", "don't",
    "not interested", "no thanks", "stop", "unsubscribe", "annoying",
    "spam", "never", "terrible", "worst", "horrible", "waste",
]


class ReplyClassifier:
    """
    Classifies email replies using pattern matching and AI.
    """
    
    def __init__(self, use_ai: bool = True):
        self.use_ai = use_ai
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """Compile regex patterns for efficiency."""
        self.compiled_patterns = {}
        for intent, patterns in INTENT_PATTERNS.items():
            self.compiled_patterns[intent] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
    
    def classify(
        self,
        reply_body: str,
        subject: str = "",
        sender: str = "",
        context: dict = None,
    ) -> ReplyClassification:
        """
        Classify an email reply.
        
        Args:
            reply_body: The body text of the reply
            subject: The email subject
            sender: The sender's email address
            context: Additional context (prior thread, contact info, etc.)
        
        Returns:
            ReplyClassification with intent, sentiment, and recommendations
        """
        # Clean the reply body
        clean_body = self._clean_text(reply_body)
        
        # Try pattern matching first (fast and reliable for common cases)
        pattern_result = self._classify_by_pattern(clean_body, subject)
        
        if pattern_result and pattern_result.confidence >= 0.8:
            # High-confidence pattern match, use it
            classification = pattern_result
        elif self.use_ai:
            # Use AI for more nuanced classification
            classification = self._classify_by_ai(clean_body, subject, context)
            if classification.confidence < pattern_result.confidence:
                classification = pattern_result
        else:
            classification = pattern_result
        
        # Add recommended action
        classification.recommended_action = self._get_recommended_action(classification)
        classification.follow_up_priority = self._calculate_priority(classification)
        
        logger.info(
            "reply_classified",
            intent=classification.intent.value,
            confidence=classification.confidence,
            sentiment=classification.sentiment.value,
            method=classification.classification_method,
        )
        
        return classification
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for classification."""
        # Remove quoted text (previous messages)
        lines = text.split("\n")
        clean_lines = []
        for line in lines:
            if line.strip().startswith(">"):
                continue
            if line.strip().startswith("On ") and "wrote:" in line:
                break
            if line.strip().startswith("From:"):
                break
            if "Original Message" in line:
                break
            clean_lines.append(line)
        
        text = "\n".join(clean_lines)
        
        # Remove signatures
        signature_markers = [
            "Best regards,", "Thanks,", "Regards,", "Cheers,", "Best,",
            "Sincerely,", "Kind regards,", "--", "___", "Sent from my",
        ]
        for marker in signature_markers:
            if marker in text:
                text = text.split(marker)[0]
        
        return text.strip()
    
    def _classify_by_pattern(self, text: str, subject: str) -> ReplyClassification:
        """Classify using pattern matching."""
        combined_text = f"{subject} {text}".lower()
        
        best_intent = ReplyIntent.UNCLEAR
        best_confidence = 0.0
        matched_phrases = []
        
        for intent, patterns in self.compiled_patterns.items():
            match_count = 0
            for pattern in patterns:
                matches = pattern.findall(combined_text)
                if matches:
                    match_count += len(matches)
                    matched_phrases.extend(matches[:3])
            
            if match_count > 0:
                # Calculate confidence based on match count and text length
                confidence = min(0.95, 0.6 + (match_count * 0.1))
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_intent = intent
        
        # Analyze sentiment
        sentiment = self._analyze_sentiment(text)
        
        # Calculate urgency
        urgency = self._calculate_urgency(best_intent, text)
        
        # Extract objection type if applicable
        objection_type = None
        if best_intent == ReplyIntent.OBJECTION:
            objection_type = self._extract_objection_type(text)
        
        # Extract referral contact if applicable
        referral_contact = None
        if best_intent == ReplyIntent.REFERRAL:
            referral_contact = self._extract_referral_contact(text)
        
        return ReplyClassification(
            intent=best_intent,
            confidence=best_confidence,
            sentiment=sentiment,
            urgency=urgency,
            key_phrases=matched_phrases[:5],
            objection_type=objection_type,
            referral_contact=referral_contact,
            classification_method="pattern",
        )
    
    def _classify_by_ai(
        self,
        text: str,
        subject: str,
        context: dict = None,
    ) -> ReplyClassification:
        """Classify using AI (OpenAI)."""
        # This would call OpenAI API in production
        # For now, fall back to pattern matching with AI label
        result = self._classify_by_pattern(text, subject)
        result.classification_method = "ai_fallback"
        return result
    
    def _analyze_sentiment(self, text: str) -> SentimentLevel:
        """Analyze sentiment of the text."""
        text_lower = text.lower()
        
        positive_count = sum(1 for word in POSITIVE_INDICATORS if word in text_lower)
        negative_count = sum(1 for word in NEGATIVE_INDICATORS if word in text_lower)
        
        score = positive_count - negative_count
        
        if score >= 3:
            return SentimentLevel.VERY_POSITIVE
        elif score >= 1:
            return SentimentLevel.POSITIVE
        elif score <= -3:
            return SentimentLevel.VERY_NEGATIVE
        elif score <= -1:
            return SentimentLevel.NEGATIVE
        return SentimentLevel.NEUTRAL
    
    def _calculate_urgency(self, intent: ReplyIntent, text: str) -> int:
        """Calculate urgency level (1-5)."""
        urgency_map = {
            ReplyIntent.MEETING_CONFIRMED: 5,
            ReplyIntent.MEETING_REQUEST: 5,
            ReplyIntent.INTERESTED: 4,
            ReplyIntent.QUESTION: 4,
            ReplyIntent.REFERRAL: 4,
            ReplyIntent.OBJECTION: 3,
            ReplyIntent.NOT_NOW: 2,
            ReplyIntent.POSITIVE_FEEDBACK: 2,
            ReplyIntent.UNCLEAR: 2,
            ReplyIntent.NOT_INTERESTED: 1,
            ReplyIntent.UNSUBSCRIBE: 1,
            ReplyIntent.OUT_OF_OFFICE: 1,
            ReplyIntent.BOUNCE: 1,
        }
        
        base_urgency = urgency_map.get(intent, 2)
        
        # Check for urgency indicators in text
        urgent_indicators = [
            "urgent", "asap", "immediately", "right away", "today",
            "time sensitive", "deadline", "need this now",
        ]
        
        if any(ind in text.lower() for ind in urgent_indicators):
            base_urgency = min(5, base_urgency + 1)
        
        return base_urgency
    
    def _extract_objection_type(self, text: str) -> Optional[str]:
        """Extract specific objection type."""
        text_lower = text.lower()
        
        objection_types = {
            "price": ["price", "cost", "expensive", "budget", "afford"],
            "timing": ["not now", "later", "busy", "next quarter", "next year"],
            "competitor": ["already using", "happy with", "competitor", "alternative"],
            "need": ["don't need", "not necessary", "no use for"],
            "authority": ["not my decision", "talk to my", "need approval"],
            "trust": ["not sure", "concerns", "worried about"],
        }
        
        for obj_type, keywords in objection_types.items():
            if any(kw in text_lower for kw in keywords):
                return obj_type
        
        return "unspecified"
    
    def _extract_referral_contact(self, text: str) -> Optional[str]:
        """Extract referral contact from text."""
        # Look for email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        
        if emails:
            return emails[0]
        
        # Look for names after referral indicators
        name_patterns = [
            r"(?:talk|speak|connect) (?:to|with) (\w+ \w+)",
            r"(?:reach out to|contact) (\w+ \w+)",
            r"(?:my|our) (\w+) handles",
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _get_recommended_action(self, classification: ReplyClassification) -> str:
        """Get recommended action based on classification."""
        action_map = {
            ReplyIntent.INTERESTED: "Send follow-up with more details and propose meeting time",
            ReplyIntent.MEETING_REQUEST: "Send calendar link or propose specific times immediately",
            ReplyIntent.MEETING_CONFIRMED: "Send calendar invite and meeting prep materials",
            ReplyIntent.QUESTION: "Answer questions promptly and offer to schedule a call",
            ReplyIntent.OBJECTION: f"Address {classification.objection_type or 'objection'} with tailored response",
            ReplyIntent.NOT_NOW: "Add to nurture sequence with check-in in 30-60 days",
            ReplyIntent.NOT_INTERESTED: "Thank them, mark as closed-lost, suppress from outreach",
            ReplyIntent.UNSUBSCRIBE: "Remove from all sequences immediately, mark as suppressed",
            ReplyIntent.OUT_OF_OFFICE: "Reschedule follow-up for after their return date",
            ReplyIntent.BOUNCE: "Verify email address or find alternate contact",
            ReplyIntent.REFERRAL: f"Reach out to {classification.referral_contact or 'referred contact'}",
            ReplyIntent.POSITIVE_FEEDBACK: "No immediate action needed, continue sequence",
            ReplyIntent.UNCLEAR: "Review manually and determine appropriate response",
        }
        
        return action_map.get(classification.intent, "Review and respond appropriately")
    
    def _calculate_priority(self, classification: ReplyClassification) -> int:
        """Calculate follow-up priority (1-5)."""
        priority_map = {
            ReplyIntent.MEETING_CONFIRMED: 5,
            ReplyIntent.MEETING_REQUEST: 5,
            ReplyIntent.INTERESTED: 5,
            ReplyIntent.REFERRAL: 4,
            ReplyIntent.QUESTION: 4,
            ReplyIntent.OBJECTION: 3,
            ReplyIntent.NOT_NOW: 2,
            ReplyIntent.POSITIVE_FEEDBACK: 2,
            ReplyIntent.UNCLEAR: 2,
            ReplyIntent.NOT_INTERESTED: 1,
            ReplyIntent.UNSUBSCRIBE: 1,
            ReplyIntent.OUT_OF_OFFICE: 1,
            ReplyIntent.BOUNCE: 1,
        }
        
        return priority_map.get(classification.intent, 2)
    
    def batch_classify(
        self,
        replies: list[dict],
    ) -> list[ReplyClassification]:
        """
        Classify multiple replies at once.
        
        Args:
            replies: List of dicts with 'body', 'subject', 'sender' keys
        
        Returns:
            List of classifications
        """
        results = []
        for reply in replies:
            classification = self.classify(
                reply_body=reply.get("body", ""),
                subject=reply.get("subject", ""),
                sender=reply.get("sender", ""),
                context=reply.get("context"),
            )
            results.append(classification)
        
        return results


# Singleton instance
_classifier: Optional[ReplyClassifier] = None


def get_reply_classifier() -> ReplyClassifier:
    """Get the reply classifier singleton."""
    global _classifier
    if _classifier is None:
        _classifier = ReplyClassifier()
    return _classifier
