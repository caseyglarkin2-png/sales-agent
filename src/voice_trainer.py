"""Voice Profile Training - Learn writing patterns from email samples.

This module analyzes emails (from HubSpot, Gmail, or uploads) to extract
voice patterns, phrases, and style characteristics for training voice profiles.
"""
import os
import re
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field

from openai import AsyncOpenAI

from src.logger import get_logger
from src.voice_profile import VoiceProfile, get_voice_profile_manager

logger = get_logger(__name__)


@dataclass
class TrainingSample:
    """A training sample from an email."""
    source: str  # hubspot, gmail, upload
    source_id: str
    subject: str
    body: str
    from_address: str
    date: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VoiceAnalysis:
    """Analysis results from email samples."""
    tone: str
    formality_level: float  # 0-1, 0=casual, 1=formal
    avg_sentence_length: float
    avg_paragraph_length: float
    common_greetings: List[str]
    common_sign_offs: List[str]
    common_phrases: List[str]
    style_notes: List[str]
    uses_contractions: bool
    uses_questions: bool
    uses_ps: bool
    prohibited_patterns: List[str]


class VoiceProfileTrainer:
    """Trains voice profiles from email samples using AI analysis."""
    
    def __init__(self, hubspot_connector=None, gmail_connector=None):
        self.hubspot_connector = hubspot_connector
        self.gmail_connector = gmail_connector
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None
        self.training_samples: List[TrainingSample] = []
    
    async def fetch_hubspot_marketing_emails(
        self,
        search_query: str = "Freight Marketer Newsletter",
        limit: int = 20,
    ) -> List[TrainingSample]:
        """Fetch marketing emails from HubSpot for training.
        
        Args:
            search_query: Search term for finding emails
            limit: Maximum emails to fetch
        
        Returns:
            List of TrainingSample objects
        """
        samples = []
        
        if not self.hubspot_connector:
            logger.warning("HubSpot connector not available for email fetch")
            return samples
        
        try:
            # HubSpot Marketing Email API
            # GET /marketing/v3/emails
            emails = await self.hubspot_connector.get_marketing_emails(
                search=search_query,
                limit=limit
            )
            
            for email in emails:
                sample = TrainingSample(
                    source="hubspot",
                    source_id=email.get("id", ""),
                    subject=email.get("subject", ""),
                    body=email.get("content", {}).get("body", ""),
                    from_address=email.get("from", {}).get("email", ""),
                    date=email.get("publishDate"),
                    metadata={
                        "campaign_name": email.get("name"),
                        "type": email.get("type"),
                        "status": email.get("status"),
                    }
                )
                samples.append(sample)
            
            logger.info(f"Fetched {len(samples)} HubSpot marketing emails")
        except Exception as e:
            logger.error(f"Error fetching HubSpot emails: {e}")
        
        return samples
    
    async def fetch_gmail_sent_emails(
        self,
        from_address: str,
        limit: int = 20,
    ) -> List[TrainingSample]:
        """Fetch sent emails from Gmail for training.
        
        Args:
            from_address: Email address of sender to analyze
            limit: Maximum emails to fetch
        
        Returns:
            List of TrainingSample objects
        """
        samples = []
        
        if not self.gmail_connector:
            logger.warning("Gmail connector not available for email fetch")
            return samples
        
        try:
            # Search for sent emails from specific address
            threads = await self.gmail_connector.search_threads(
                f"from:{from_address} in:sent",
                max_results=limit
            )
            
            for thread in threads:
                thread_data = await self.gmail_connector.get_thread(thread["id"])
                if not thread_data:
                    continue
                
                for message in thread_data.get("messages", []):
                    # Extract body from message
                    payload = message.get("payload", {})
                    body = self._extract_body(payload)
                    subject = ""
                    
                    for header in payload.get("headers", []):
                        if header.get("name", "").lower() == "subject":
                            subject = header.get("value", "")
                    
                    if body:
                        sample = TrainingSample(
                            source="gmail",
                            source_id=message.get("id", ""),
                            subject=subject,
                            body=body,
                            from_address=from_address,
                            date=message.get("internalDate"),
                        )
                        samples.append(sample)
            
            logger.info(f"Fetched {len(samples)} Gmail sent emails")
        except Exception as e:
            logger.error(f"Error fetching Gmail emails: {e}")
        
        return samples
    
    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """Extract email body from Gmail message payload."""
        import base64
        
        # Try direct body first
        if payload.get("body", {}).get("data"):
            try:
                return base64.urlsafe_b64decode(
                    payload["body"]["data"]
                ).decode("utf-8")
            except:
                pass
        
        # Try parts
        for part in payload.get("parts", []):
            mime_type = part.get("mimeType", "")
            if mime_type == "text/plain":
                if part.get("body", {}).get("data"):
                    try:
                        return base64.urlsafe_b64decode(
                            part["body"]["data"]
                        ).decode("utf-8")
                    except:
                        pass
        
        return ""
    
    def add_sample(self, sample: TrainingSample) -> None:
        """Add a training sample."""
        self.training_samples.append(sample)
        logger.info(f"Added training sample from {sample.source}: {sample.subject[:50]}")
    
    def add_text_sample(
        self,
        text: str,
        source: str = "upload",
        subject: str = "Training Sample",
    ) -> None:
        """Add a raw text sample for training."""
        sample = TrainingSample(
            source=source,
            source_id=f"{source}-{datetime.utcnow().timestamp()}",
            subject=subject,
            body=text,
            from_address="training",
        )
        self.training_samples.append(sample)
    
    async def analyze_samples(self) -> VoiceAnalysis:
        """Analyze all training samples to extract voice patterns."""
        if not self.training_samples:
            raise ValueError("No training samples provided")
        
        # Use AI for deep analysis if available
        if self.client:
            return await self._ai_analyze_samples()
        
        # Fall back to rule-based analysis
        return self._rule_based_analysis()
    
    async def _ai_analyze_samples(self) -> VoiceAnalysis:
        """Use OpenAI to analyze writing patterns."""
        # Combine samples for analysis
        sample_texts = []
        for i, sample in enumerate(self.training_samples[:10]):  # Limit to 10
            sample_texts.append(f"--- Sample {i+1} ---\nSubject: {sample.subject}\n\n{sample.body[:2000]}")
        
        combined = "\n\n".join(sample_texts)
        
        prompt = """Analyze these email samples and extract the writer's voice profile.

Return a JSON object with:
{
  "tone": "professional/casual/formal/friendly",
  "formality_level": 0.0-1.0,
  "avg_sentence_length": number,
  "avg_paragraph_length": number,
  "common_greetings": ["list", "of", "greetings"],
  "common_sign_offs": ["list", "of", "sign-offs"],
  "common_phrases": ["frequently", "used", "phrases"],
  "style_notes": ["key", "style", "observations"],
  "uses_contractions": true/false,
  "uses_questions": true/false,
  "uses_ps": true/false,
  "prohibited_patterns": ["patterns", "to", "avoid"]
}

EMAIL SAMPLES:
""" + combined
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3,
            )
            
            import json
            data = json.loads(response.choices[0].message.content)
            
            return VoiceAnalysis(
                tone=data.get("tone", "professional"),
                formality_level=data.get("formality_level", 0.5),
                avg_sentence_length=data.get("avg_sentence_length", 15),
                avg_paragraph_length=data.get("avg_paragraph_length", 3),
                common_greetings=data.get("common_greetings", ["Hi"]),
                common_sign_offs=data.get("common_sign_offs", ["Best"]),
                common_phrases=data.get("common_phrases", []),
                style_notes=data.get("style_notes", []),
                uses_contractions=data.get("uses_contractions", True),
                uses_questions=data.get("uses_questions", True),
                uses_ps=data.get("uses_ps", False),
                prohibited_patterns=data.get("prohibited_patterns", []),
            )
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return self._rule_based_analysis()
    
    def _rule_based_analysis(self) -> VoiceAnalysis:
        """Simple rule-based analysis as fallback."""
        all_text = " ".join([s.body for s in self.training_samples])
        
        # Count patterns
        sentences = re.split(r'[.!?]+', all_text)
        avg_sentence_len = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
        
        uses_contractions = any(c in all_text.lower() for c in ["don't", "can't", "won't", "I'm", "we're"])
        uses_questions = "?" in all_text
        uses_ps = "p.s." in all_text.lower() or "ps:" in all_text.lower()
        
        # Extract common patterns
        greetings = []
        for pattern in ["Hi ", "Hello ", "Hey ", "Dear "]:
            if pattern.lower() in all_text.lower():
                greetings.append(pattern.strip())
        
        return VoiceAnalysis(
            tone="professional",
            formality_level=0.5,
            avg_sentence_length=avg_sentence_len,
            avg_paragraph_length=3,
            common_greetings=greetings or ["Hi"],
            common_sign_offs=["Best"],
            common_phrases=[],
            style_notes=["Analyzed using rule-based approach"],
            uses_contractions=uses_contractions,
            uses_questions=uses_questions,
            uses_ps=uses_ps,
            prohibited_patterns=[],
        )
    
    async def create_profile_from_analysis(
        self,
        profile_name: str,
        analysis: VoiceAnalysis,
    ) -> VoiceProfile:
        """Create a VoiceProfile from analysis results."""
        profile = VoiceProfile(
            name=profile_name,
            tone=analysis.tone,
            style_notes=analysis.style_notes,
            use_contractions=analysis.uses_contractions,
            max_paragraphs=int(analysis.avg_paragraph_length) + 1,
            include_ps=analysis.uses_ps,
            signature_style=analysis.common_sign_offs[0] if analysis.common_sign_offs else "Best",
            single_cta=True,
            cta_style="question" if analysis.uses_questions else "statement",
            slot_count=3,
            slot_urgency="balanced",
        )
        
        # Add to manager
        manager = get_voice_profile_manager()
        manager.add_profile(profile)
        
        logger.info(f"Created voice profile: {profile_name}")
        return profile
    
    async def train_from_hubspot(
        self,
        profile_name: str,
        search_query: str = "Freight Marketer Newsletter",
        limit: int = 20,
    ) -> VoiceProfile:
        """Complete training pipeline from HubSpot emails.
        
        Args:
            profile_name: Name for the new profile
            search_query: HubSpot search query
            limit: Max emails to analyze
        
        Returns:
            Trained VoiceProfile
        """
        # Fetch samples
        samples = await self.fetch_hubspot_marketing_emails(search_query, limit)
        
        if not samples:
            raise ValueError(f"No emails found for query: {search_query}")
        
        for sample in samples:
            self.add_sample(sample)
        
        # Analyze
        analysis = await self.analyze_samples()
        
        # Create profile
        profile = await self.create_profile_from_analysis(profile_name, analysis)
        
        return profile
    
    def get_training_status(self) -> Dict[str, Any]:
        """Get current training status."""
        return {
            "samples_count": len(self.training_samples),
            "sources": list(set(s.source for s in self.training_samples)),
            "samples": [
                {
                    "source": s.source,
                    "subject": s.subject[:50],
                    "date": s.date,
                }
                for s in self.training_samples[:20]
            ],
        }


# Factory function
def create_trainer(hubspot_connector=None, gmail_connector=None) -> VoiceProfileTrainer:
    """Create a voice profile trainer."""
    return VoiceProfileTrainer(
        hubspot_connector=hubspot_connector,
        gmail_connector=gmail_connector,
    )
