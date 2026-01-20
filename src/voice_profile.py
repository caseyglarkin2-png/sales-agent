"""Voice profile system for personalized email drafts.

This module manages voice profiles that capture the writing style,
tone, and preferences for outbound communications.
"""
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class VoiceProfile:
    """A voice profile capturing writing style preferences."""
    
    name: str
    tone: str = "professional"  # professional, casual, formal, friendly
    style_notes: List[str] = field(default_factory=list)
    
    # Writing preferences
    use_contractions: bool = True
    max_paragraphs: int = 3
    include_ps: bool = True
    signature_style: str = "Best regards"
    
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
        return f"""
Voice Profile: {self.name}
Tone: {self.tone}
Style Notes: {', '.join(self.style_notes) if self.style_notes else 'None'}

Writing Rules:
- Use contractions: {'Yes' if self.use_contractions else 'No'}
- Maximum paragraphs: {self.max_paragraphs}
- Include P.S.: {'Yes' if self.include_ps else 'No'}
- Sign off with: "{self.signature_style}"
- Single CTA only: {'Yes' if self.single_cta else 'No'}
- CTA style: {self.cta_style}

PROHIBITED (never use):
- Words: {', '.join(self.prohibited_words)}
- Punctuation: {', '.join(self.prohibited_punctuation)}

Meeting Slots:
- Offer {self.slot_count} options
- Urgency level: {self.slot_urgency}
"""


# Default voice profiles
DEFAULT_PROFILES: Dict[str, VoiceProfile] = {
    "charlie_pesti": VoiceProfile(
        name="Charlie Pesti",
        tone="professional",
        style_notes=[
            "Direct but warm",
            "Focus on value, not features",
            "Reference specific pain points",
            "Never pushy or salesy",
        ],
        use_contractions=True,
        max_paragraphs=3,
        include_ps=True,
        signature_style="Best",
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
            profile = self.profiles.get("charlie_pesti", VoiceProfile(name="default"))
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


def get_voice_profile(name: str = "charlie_pesti") -> VoiceProfile:
    """Get a voice profile by name."""
    return get_voice_profile_manager().get_profile(name)
