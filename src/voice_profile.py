"""Voice profile system for personalized email drafts.

This module manages voice profiles that capture the writing style,
tone, and preferences for outbound communications.

Sprint 69: Added Socratic approach fields.
"""
import json
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from src.logger import get_logger

logger = get_logger(__name__)


class OpenerStyle(str, Enum):
    """Email opener style preference."""
    QUESTION = "question"          # Lead with a thought-provoking question
    OBSERVATION = "observation"    # Lead with a contrarian observation
    CHALLENGE = "challenge"        # Directly challenge an assumption
    STORY = "story"               # Lead with a brief, relevant anecdote


class ChallengeIntensity(str, Enum):
    """How provocative to be in the email."""
    SOFT = "soft"          # Gentle questions, low friction
    BALANCED = "balanced"  # Mix of challenge and warmth
    BOLD = "bold"          # Direct challenges, high contrast


@dataclass
class VoiceProfile:
    """A voice profile capturing writing style preferences."""
    
    name: str
    tone: str = "professional"  # professional, casual, formal, friendly
    style_notes: List[str] = field(default_factory=list)
    
    # Socratic approach fields (Sprint 69)
    socratic_level: int = 3  # 1-5: How Socratic (1=declarative, 5=pure questions)
    opener_style: OpenerStyle = OpenerStyle.QUESTION
    challenge_intensity: ChallengeIntensity = ChallengeIntensity.BALANCED
    
    # Writing preferences
    use_contractions: bool = True
    max_paragraphs: int = 3
    include_ps: bool = True
    signature_style: str = "Best regards"
    calendar_link: Optional[str] = None  # HubSpot/Calendly link for booking
    
    # Prohibited patterns
    prohibited_words: List[str] = field(default_factory=lambda: [
        "synergy", "leverage", "circle back", "touch base",
        "low-hanging fruit", "move the needle", "bandwidth"
    ])
    prohibited_punctuation: List[str] = field(default_factory=lambda: [
        "—",  # em-dash
        "!!",
        "???",
    ])
    
    # CTA preferences
    single_cta: bool = True  # Only one call-to-action per email
    cta_style: str = "question"  # question, statement, soft
    
    # Meeting slot presentation
    slot_count: int = 3  # 2-3 options
    slot_urgency: str = "balanced"  # urgent, balanced, relaxed
    
    def to_prompt_context(self) -> str:
        """Generate prompt context for LLM."""
        calendar_context = f"\nCalendar Link: {self.calendar_link} (include in signature or CTA)" if self.calendar_link else ""
        
        # Socratic style guidance based on level (Sprint 69)
        socratic_guidance = {
            1: "Mostly declarative statements, occasional questions",
            2: "Balance of statements and questions",
            3: "Lead with questions, support with observations",
            4: "Primarily Socratic - guide through questions",
            5: "Pure Socratic - every point is a question",
        }
        
        opener_guidance = {
            OpenerStyle.QUESTION: "Open with a thought-provoking question",
            OpenerStyle.OBSERVATION: "Open with a contrarian observation about their industry",
            OpenerStyle.CHALLENGE: "Open by directly challenging an assumption they hold",
            OpenerStyle.STORY: "Open with a brief story or anecdote that illustrates a point",
        }
        
        intensity_guidance = {
            ChallengeIntensity.SOFT: "Be gentle and inviting, low friction",
            ChallengeIntensity.BALANCED: "Mix warmth with productive challenge",
            ChallengeIntensity.BOLD: "Be direct and provocative, high contrast",
        }
        
        return f"""
Voice Profile: {self.name}
Tone: {self.tone}
Style Notes: {', '.join(self.style_notes) if self.style_notes else 'None'}

Socratic Approach:
- Level {self.socratic_level}/5: {socratic_guidance.get(self.socratic_level, 'Balanced')}
- Opener: {opener_guidance.get(self.opener_style, 'Question')}
- Intensity: {intensity_guidance.get(self.challenge_intensity, 'Balanced')}

Writing Rules:
- Use contractions: {'Yes' if self.use_contractions else 'No'}
- Maximum paragraphs: {self.max_paragraphs}
- Include P.S.: {'Yes' if self.include_ps else 'No'}
- Sign off with: "{self.signature_style}"
- Single CTA only: {'Yes' if self.single_cta else 'No'}
- CTA style: {self.cta_style}{calendar_context}

PROHIBITED (never use):
- Words: {', '.join(self.prohibited_words)}
- Punctuation: {', '.join(self.prohibited_punctuation)}

Meeting Slots:
- Offer {self.slot_count} options
- Urgency level: {self.slot_urgency}
"""


# Default voice profiles
DEFAULT_PROFILES: Dict[str, VoiceProfile] = {
    "casey_larkin": VoiceProfile(
        name="Casey Larkin",
        tone="provocative-professional",
        # Socratic approach settings (Sprint 69)
        socratic_level=4,  # High Socratic - guide through questions
        opener_style=OpenerStyle.QUESTION,
        challenge_intensity=ChallengeIntensity.BALANCED,
        style_notes=[
            # Socratic approach - guide through questions
            "Lead with a thought-provoking question that challenges their current approach",
            "Ask 'what if' questions that make them reconsider assumptions",
            "Use Socratic method: don't tell them the answer, help them discover it",
            # Provocative edge - create productive tension
            "Name uncomfortable truths about their industry that others avoid",
            "Challenge the status quo respectfully but directly",
            "Create cognitive dissonance about their current state vs. potential",
            # Core personality
            "Direct, warm, and intellectually curious",
            "Focus on outcomes they haven't considered, not obvious value props",
            "Reference specific pain points they may not have articulated yet",
            # Domain expertise
            "Go-to-market and demand generation expert with contrarian insights",
            "Pesti helps companies with field marketing, lead generation, nurturing, and ABM",
            "Connect marketing and sales to enable real GTM functions",
            # Tactical
            "Keep it concise - every word earns its place",
            "End with ONE question that's hard to ignore",
            "Never sound like every other sales email they delete",
        ],
        use_contractions=True,
        max_paragraphs=3,
        include_ps=True,
        signature_style="Best,\n\nCasey Larkin\nCEO, Pesti\n\nBook time: https://meetings.hubspot.com/casey-larkin",
        calendar_link="https://meetings.hubspot.com/casey-larkin",
        single_cta=True,
        cta_style="question",
        slot_count=3,
        slot_urgency="balanced",
    ),
    "formal": VoiceProfile(
        name="Formal",
        tone="formal",
        style_notes=[
            "Professional and polished",
            "No casual language",
        ],
        use_contractions=False,
        max_paragraphs=4,
        include_ps=False,
        signature_style="Best regards",
        single_cta=True,
        cta_style="statement",
        slot_count=3,
        slot_urgency="relaxed",
    ),
}


class VoiceProfileManager:
    """Manages voice profiles for email generation."""
    
    def __init__(self, profiles_dir: Optional[str] = None):
        """Initialize voice profile manager."""
        self.profiles: Dict[str, VoiceProfile] = DEFAULT_PROFILES.copy()
        self.profiles_dir = profiles_dir or os.environ.get(
            "VOICE_PROFILES_DIR", 
            os.path.join(os.path.dirname(__file__), "voice_profiles")
        )
        self._load_custom_profiles()
    
    def _load_custom_profiles(self) -> None:
        """Load custom profiles from JSON files."""
        if not os.path.exists(self.profiles_dir):
            return
        
        for filename in os.listdir(self.profiles_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.profiles_dir, filename)
                try:
                    with open(filepath) as f:
                        data = json.load(f)
                    profile = VoiceProfile(**data)
                    self.profiles[profile.name.lower().replace(" ", "_")] = profile
                    logger.info(f"Loaded voice profile: {profile.name}")
                except Exception as e:
                    logger.error(f"Error loading profile {filename}: {e}")
    
    def get_profile(self, name: str) -> VoiceProfile:
        """Get a voice profile by name."""
        profile = self.profiles.get(name.lower().replace(" ", "_"))
        if not profile:
            logger.warning(f"Profile '{name}' not found, using default")
            profile = self.profiles.get("casey_larkin", VoiceProfile(name="default"))
        return profile
    
    def list_profiles(self) -> List[str]:
        """List available profile names."""
        return list(self.profiles.keys())
    
    def add_profile(self, profile: VoiceProfile) -> None:
        """Add a new voice profile."""
        key = profile.name.lower().replace(" ", "_")
        self.profiles[key] = profile
        logger.info(f"Added voice profile: {profile.name}")


# Global instance
_voice_profile_manager: Optional[VoiceProfileManager] = None


def get_voice_profile_manager() -> VoiceProfileManager:
    """Get or create the voice profile manager singleton."""
    global _voice_profile_manager
    if _voice_profile_manager is None:
        _voice_profile_manager = VoiceProfileManager()
    return _voice_profile_manager


def get_voice_profile(name: str = "casey_larkin") -> VoiceProfile:
    """Get a voice profile by name."""
    return get_voice_profile_manager().get_profile(name)


# ============================================================================
# Voice Quality Scoring (Sprint 69)
# ============================================================================

# Patterns that indicate Socratic style
SOCRATIC_PATTERNS = [
    r"\bwhat if\b",
    r"\bhave you (ever |)?(noticed|considered|thought|wondered)\b",
    r"\bwhy do (most|many|so many)\b",
    r"\bwhat would (happen|change|it mean)\b",
    r"\bwhat's (stopping|keeping|preventing)\b",
    r"\bhow (often|much|many|would)\b",
    r"\bisn't it (strange|curious|interesting)\b",
    r"\?\s*$",  # Ends with a question
]

# Patterns that indicate provocative style
PROVOCATIVE_PATTERNS = [
    r"\bmost\s+(companies|teams|people|leaders|marketers|sales|demand|marketing)\b",
    r"\bmost\s+\w+\s*(I talk to|teams|people|leaders|marketers|companies)\b",
    r"\buncomfortable truth\b",
    r"\bno one (talks|mentions|addresses)\b",
    r"\bthe (real|hard|uncomfortable) (truth|problem|issue)\b",
    r"\bstop (doing|believing|thinking)\b",
    r"\bwrong (about|way|approach)\b",
    r"\bcontrary to\b",
    r"\bdespite what\b",
    r"\bhere's (the thing|what I've seen|what works)\b",
    r"\bI've (been noticing|seen|audited|watched|helped)\b",
    r"\bpattern\b.{0,30}\bsame\b",
    r"\bdrowning in\b",
    r"\blooks great on paper\b",
    r"\bisn't\s+\w+\.\s+It's\b",  # "It's not X. It's Y." pattern
    r"\bthe fix isn't\b",
    r"\bnot\s+because\b",
]

# Anti-patterns (salesy jargon to avoid)
JARGON_PATTERNS = [
    r"\bsynergy\b",
    r"\bleverage\b",
    r"\bcircle back\b",
    r"\btouch base\b",
    r"\blow-hanging fruit\b",
    r"\bmove the needle\b",
    r"\bbandwidth\b",
    r"\bloop (you|me|us) in\b",
    r"\bpivot\b",
    r"\bdisrupt(ive|ion)?\b",
    r"\bgame(-| )changer\b",
    r"\bvalue(-| )add\b",
    r"\bactionable\b",
]


def score_socratic(text: str) -> float:
    """Score how Socratic the text is (0.0 to 1.0).
    
    Args:
        text: The email text to score
        
    Returns:
        Score from 0.0 (not Socratic) to 1.0 (highly Socratic)
    """
    import re
    
    if not text:
        return 0.0
    
    text_lower = text.lower()
    matches = 0
    
    for pattern in SOCRATIC_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            matches += 1
    
    # Normalize: 3+ matches = 1.0, scale linearly below
    max_expected = 3
    return min(1.0, matches / max_expected)


def score_provocative(text: str) -> float:
    """Score how provocative the text is (0.0 to 1.0).
    
    Args:
        text: The email text to score
        
    Returns:
        Score from 0.0 (not provocative) to 1.0 (highly provocative)
    """
    import re
    
    if not text:
        return 0.0
    
    text_lower = text.lower()
    matches = 0
    
    for pattern in PROVOCATIVE_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            matches += 1
    
    # Normalize: 2+ matches = 1.0, scale linearly below
    max_expected = 2
    return min(1.0, matches / max_expected)


def score_jargon_free(text: str) -> float:
    """Score how jargon-free the text is (0.0 to 1.0).
    
    Args:
        text: The email text to score
        
    Returns:
        Score from 0.0 (lots of jargon) to 1.0 (no jargon)
    """
    import re
    
    if not text:
        return 1.0  # Empty text has no jargon
    
    text_lower = text.lower()
    matches = 0
    
    for pattern in JARGON_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            matches += 1
    
    # Invert: 0 matches = 1.0, 3+ matches = 0.0
    penalty_per_match = 0.33
    return max(0.0, 1.0 - (matches * penalty_per_match))


def score_voice_quality(text: str, weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """Score overall voice quality with detailed breakdown.
    
    Args:
        text: The email text to score
        weights: Optional weights for each dimension (default: balanced)
        
    Returns:
        Dict with overall score, dimension scores, and details
    """
    weights = weights or {
        "socratic": 0.4,
        "provocative": 0.3,
        "jargon_free": 0.3,
    }
    
    socratic = score_socratic(text)
    provocative = score_provocative(text)
    jargon_free = score_jargon_free(text)
    
    overall = (
        socratic * weights.get("socratic", 0.4) +
        provocative * weights.get("provocative", 0.3) +
        jargon_free * weights.get("jargon_free", 0.3)
    )
    
    return {
        "overall": round(overall, 2),
        "socratic": round(socratic, 2),
        "provocative": round(provocative, 2),
        "jargon_free": round(jargon_free, 2),
        "passes_threshold": overall >= 0.6,
        "feedback": _generate_voice_feedback(socratic, provocative, jargon_free),
    }


def _generate_voice_feedback(socratic: float, provocative: float, jargon_free: float) -> List[str]:
    """Generate actionable feedback for improving voice quality."""
    feedback = []
    
    if socratic < 0.5:
        feedback.append("Add more questions - lead with 'What if' or 'Have you noticed'")
    
    if provocative < 0.5:
        feedback.append("Be more provocative - challenge common assumptions")
    
    if jargon_free < 0.8:
        feedback.append("Remove sales jargon - use plain language")
    
    if not feedback:
        feedback.append("Great voice consistency! Casey would approve.")
    
    return feedback
