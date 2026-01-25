"""Voice Service - Whisper transcription + OpenAI TTS synthesis.

Sprint 17: Voice Interface for CaseyOS/Jarvis

Provides:
- Audio transcription via OpenAI Whisper API
- Text-to-speech synthesis via OpenAI TTS API
- Wake word detection ("Hey Jarvis", "Jarvis")
- Voice conversation loop
"""
import os
import tempfile
import base64
from typing import Optional, Tuple, List
from enum import Enum

from openai import AsyncOpenAI
from pydantic import BaseModel

from src.config import get_settings
from src.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class TTSVoice(str, Enum):
    """Available OpenAI TTS voices."""
    ALLOY = "alloy"      # Neutral, balanced
    ECHO = "echo"        # Warm, conversational
    FABLE = "fable"      # Expressive, British
    ONYX = "onyx"        # Deep, authoritative
    NOVA = "nova"        # Friendly, upbeat (default for Jarvis)
    SHIMMER = "shimmer"  # Clear, optimistic


class TTSModel(str, Enum):
    """OpenAI TTS models."""
    TTS_1 = "tts-1"          # Faster, lower quality
    TTS_1_HD = "tts-1-hd"    # Slower, higher quality


class TranscriptionResult(BaseModel):
    """Result of audio transcription."""
    text: str
    language: Optional[str] = None
    duration_seconds: Optional[float] = None
    wake_word_detected: bool = False
    wake_word: Optional[str] = None


class SpeechResult(BaseModel):
    """Result of text-to-speech synthesis."""
    audio_base64: str
    format: str = "mp3"
    voice: str
    model: str
    text_length: int


class VoiceService:
    """Unified voice service for transcription and speech synthesis."""
    
    # Wake words to detect
    WAKE_WORDS = ["hey jarvis", "jarvis", "hey casey", "casey"]
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """Initialize voice service with OpenAI client."""
        api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key required for voice service")
        
        self.client = AsyncOpenAI(api_key=api_key)
        self.default_voice = TTSVoice.NOVA
        self.default_model = TTSModel.TTS_1
        
        logger.info("VoiceService initialized", extra={
            "default_voice": self.default_voice.value,
            "default_model": self.default_model.value
        })
    
    async def transcribe(
        self,
        audio_data: bytes,
        language: Optional[str] = None,
        detect_wake_word: bool = True
    ) -> TranscriptionResult:
        """Transcribe audio to text using OpenAI Whisper.
        
        Args:
            audio_data: Raw audio bytes (mp3, wav, webm, etc.)
            language: Optional language hint (ISO 639-1 code)
            detect_wake_word: Check for wake word in transcription
            
        Returns:
            TranscriptionResult with text and metadata
        """
        try:
            # Write audio to temp file (Whisper API requires file)
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
                f.write(audio_data)
                temp_file = f.name
            
            try:
                # Call Whisper API
                with open(temp_file, "rb") as audio_file:
                    kwargs = {
                        "model": "whisper-1",
                        "file": audio_file,
                        "response_format": "verbose_json"
                    }
                    if language:
                        kwargs["language"] = language
                    
                    response = await self.client.audio.transcriptions.create(**kwargs)
                
                text = response.text.strip()
                duration = getattr(response, "duration", None)
                detected_language = getattr(response, "language", None)
                
                # Check for wake word
                wake_word_detected = False
                wake_word = None
                if detect_wake_word:
                    wake_word_detected, wake_word = self._detect_wake_word(text)
                
                logger.info("Transcription complete", extra={
                    "text_length": len(text),
                    "duration": duration,
                    "wake_word_detected": wake_word_detected
                })
                
                return TranscriptionResult(
                    text=text,
                    language=detected_language,
                    duration_seconds=duration,
                    wake_word_detected=wake_word_detected,
                    wake_word=wake_word
                )
                
            finally:
                # Clean up temp file
                os.unlink(temp_file)
                
        except Exception as e:
            logger.error(f"Transcription failed: {e}", extra={"error": str(e)})
            raise
    
    async def speak(
        self,
        text: str,
        voice: Optional[TTSVoice] = None,
        model: Optional[TTSModel] = None,
        speed: float = 1.0
    ) -> SpeechResult:
        """Convert text to speech using OpenAI TTS.
        
        Args:
            text: Text to synthesize
            voice: TTS voice to use (default: nova)
            model: TTS model (tts-1 or tts-1-hd)
            speed: Speech speed (0.25 to 4.0, default 1.0)
            
        Returns:
            SpeechResult with base64-encoded audio
        """
        voice = voice or self.default_voice
        model = model or self.default_model
        
        # Clamp speed to valid range
        speed = max(0.25, min(4.0, speed))
        
        try:
            response = await self.client.audio.speech.create(
                model=model.value,
                voice=voice.value,
                input=text,
                speed=speed,
                response_format="mp3"
            )
            
            # Get audio bytes and encode to base64
            audio_bytes = response.content
            audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
            
            logger.info("Speech synthesis complete", extra={
                "text_length": len(text),
                "voice": voice.value,
                "model": model.value,
                "audio_bytes": len(audio_bytes)
            })
            
            return SpeechResult(
                audio_base64=audio_base64,
                format="mp3",
                voice=voice.value,
                model=model.value,
                text_length=len(text)
            )
            
        except Exception as e:
            logger.error(f"Speech synthesis failed: {e}", extra={"error": str(e)})
            raise
    
    async def speak_streaming(
        self,
        text: str,
        voice: Optional[TTSVoice] = None,
        model: Optional[TTSModel] = None
    ):
        """Stream TTS audio chunks (for real-time playback).
        
        Yields audio chunks as bytes for streaming response.
        """
        voice = voice or self.default_voice
        model = model or self.default_model
        
        try:
            response = await self.client.audio.speech.create(
                model=model.value,
                voice=voice.value,
                input=text,
                response_format="mp3"
            )
            
            # Yield content in chunks
            yield response.content
            
        except Exception as e:
            logger.error(f"Streaming TTS failed: {e}")
            raise
    
    def _detect_wake_word(self, text: str) -> Tuple[bool, Optional[str]]:
        """Check if transcription contains a wake word.
        
        Args:
            text: Transcribed text
            
        Returns:
            Tuple of (detected, wake_word)
        """
        text_lower = text.lower().strip()
        
        for wake_word in self.WAKE_WORDS:
            if text_lower.startswith(wake_word):
                return True, wake_word
            # Also check if wake word is at the beginning after common filler
            for filler in ["um ", "uh ", "so ", "okay "]:
                if text_lower.startswith(filler + wake_word):
                    return True, wake_word
        
        return False, None
    
    def strip_wake_word(self, text: str) -> str:
        """Remove wake word from beginning of text.
        
        Args:
            text: Text potentially starting with wake word
            
        Returns:
            Text with wake word removed
        """
        text_lower = text.lower().strip()
        
        for wake_word in self.WAKE_WORDS:
            if text_lower.startswith(wake_word):
                # Remove wake word and clean up
                result = text[len(wake_word):].strip()
                # Remove trailing comma if present
                if result.startswith(","):
                    result = result[1:].strip()
                return result
        
        return text


# Singleton instance
_voice_service: Optional[VoiceService] = None


def get_voice_service() -> VoiceService:
    """Get or create singleton VoiceService instance."""
    global _voice_service
    if _voice_service is None:
        _voice_service = VoiceService()
    return _voice_service
