"""YouTube video transcription service.

This module provides functionality to fetch and transcribe YouTube videos
for voice training and content analysis.
"""
import os
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import httpx
from openai import AsyncOpenAI

from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class VideoTranscript:
    """Transcript from a video."""
    video_id: str
    title: str
    transcript_text: str
    duration_seconds: Optional[int] = None
    language: str = "en"
    source: str = "youtube"
    metadata: Dict[str, Any] = None


class YouTubeTranscriber:
    """Transcriber for YouTube videos."""
    
    def __init__(self):
        """Initialize YouTube transcriber."""
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL.
        
        Supports formats:
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://www.youtube.com/embed/VIDEO_ID
        """
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # If it's already just the ID
        if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
            return url
        
        return None
    
    async def get_video_info(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get video metadata from YouTube.
        
        Note: This uses youtube-transcript-api which doesn't require API key
        for public videos with captions.
        """
        try:
            # For now, return basic info
            # In production, you might use youtube-transcript-api or YouTube Data API
            return {
                "id": video_id,
                "title": f"YouTube Video {video_id}",
                "url": f"https://www.youtube.com/watch?v={video_id}",
            }
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return None
    
    async def transcribe_from_url(self, url: str) -> Optional[VideoTranscript]:
        """Transcribe a YouTube video from URL.
        
        First tries to get existing captions, falls back to Whisper if needed.
        """
        video_id = self.extract_video_id(url)
        if not video_id:
            logger.error(f"Could not extract video ID from URL: {url}")
            return None
        
        # Try to get YouTube's built-in captions first
        transcript = await self._get_youtube_captions(video_id)
        
        if transcript:
            logger.info(f"Got captions for video {video_id}")
            return transcript
        
        # If no captions, would need to download audio and use Whisper
        logger.warning(f"No captions available for {video_id}, would need Whisper")
        return None
    
    async def _get_youtube_captions(self, video_id: str) -> Optional[VideoTranscript]:
        """Get YouTube's automatic or manual captions.
        
        Uses youtube-transcript-api library.
        """
        try:
            # Try to import youtube-transcript-api
            from youtube_transcript_api import YouTubeTranscriptApi
            
            # Get transcript (tries auto-generated if manual not available)
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            
            # Combine all text
            full_text = " ".join([item['text'] for item in transcript_list])
            
            # Get video info
            video_info = await self.get_video_info(video_id)
            
            return VideoTranscript(
                video_id=video_id,
                title=video_info.get("title", f"Video {video_id}") if video_info else f"Video {video_id}",
                transcript_text=full_text,
                source="youtube_captions",
            )
            
        except ImportError:
            logger.warning("youtube-transcript-api not installed. Install with: pip install youtube-transcript-api")
            return None
        except Exception as e:
            logger.error(f"Error getting YouTube captions: {e}")
            return None
    
    async def transcribe_multiple(self, urls: List[str]) -> List[VideoTranscript]:
        """Transcribe multiple videos."""
        transcripts = []
        
        for url in urls:
            transcript = await self.transcribe_from_url(url)
            if transcript:
                transcripts.append(transcript)
        
        logger.info(f"Transcribed {len(transcripts)} of {len(urls)} videos")
        return transcripts


def create_youtube_transcriber() -> YouTubeTranscriber:
    """Create a YouTubeTranscriber instance."""
    return YouTubeTranscriber()
