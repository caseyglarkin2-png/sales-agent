"""
YouTube Connector for Content Engine.

Handles extracting transcripts and metadata from YouTube videos.
"""
import re
import asyncio
from typing import Dict, Optional, Any
from urllib.parse import urlparse, parse_qs

import httpx
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled

from src.logger import get_logger

logger = get_logger(__name__)

class YoutubeConnector:
    """Connector for fetching YouTube content."""
    
    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """Extract video ID from various YouTube URL formats."""
        try:
            if not url:
                return None
                
            parsed = urlparse(url)
            if parsed.hostname in ['www.youtube.com', 'youtube.com']:
                if parsed.path == '/watch':
                    return parse_qs(parsed.query).get('v', [None])[0]
                elif parsed.path.startswith('/embed/'):
                    return parsed.path.split('/')[2]
                elif parsed.path.startswith('/v/'):
                    return parsed.path.split('/')[2]
            elif parsed.hostname == 'youtu.be':
                return parsed.path[1:]
            
            return None
        except Exception as e:
            logger.error(f"Failed to parse YouTube URL {url}: {e}")
            return None

    async def get_video_content(self, url: str) -> Dict[str, Any]:
        """
        Fetch transcript and metadata for a video.
        
        Returns dict with:
        - video_id
        - title
        - content (transcript text)
        - metadata (duration, language, etc.)
        """
        video_id = self.extract_video_id(url)
        if not video_id:
            raise ValueError(f"Invalid YouTube URL: {url}")
            
        # 1. Fetch Metadata (Title)
        # We use httpx to get the page and regex for title to avoid heavy dependencies
        title = f"YouTube Video {video_id}"
        author = "Unknown"
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(f"https://www.youtube.com/watch?v={video_id}")
                if response.status_code == 200:
                    html = response.text
                    # Try to extract title from <title> tag
                    title_match = re.search(r'<title>(.*?)</title>', html)
                    if title_match:
                        # Remove " - YouTube" suffix
                        title = title_match.group(1).replace(" - YouTube", "")
                    
                    # Try to find author
                    author_match = re.search(r'"author":"(.*?)"', html)
                    if author_match:
                        author = author_match.group(1)
        except Exception as e:
            logger.warning(f"Failed to fetch video metadata for {video_id}: {e}")

        # 2. Fetch Transcript
        # Run sync youtube_transcript_api in thread
        loop = asyncio.get_event_loop()
        try:
            transcript_data = await loop.run_in_executor(
                None, 
                self._fetch_transcript_sync, 
                video_id
            )
        except Exception as e:
            logger.error(f"Failed to fetch transcript: {e}")
            raise ValueError(f"Could not retrieve transcript for {url}: {str(e)}")

        return {
            "source_id": video_id,
            "source_url": url,
            "title": title,
            "content": transcript_data["text"],
            "metadata": {
                "author": author,
                "duration_seconds": transcript_data["duration"],
                "language": transcript_data["language"],
                "platform": "youtube"
            }
        }

    def _fetch_transcript_sync(self, video_id: str) -> Dict[str, Any]:
        """Synchronous wrapper for transcript api."""
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Try English first, then auto-generated English, then any
        try:
            t = transcript_list.find_transcript(['en'])
            language = 'en'
        except NoTranscriptFound:
            try:
                t = transcript_list.find_generated_transcript(['en'])
                language = 'en-auto'
            except NoTranscriptFound:
                # Fallback to whatever is available
                t = transcript_list[0] # type: ignore
                language = t.language_code # type: ignore
        
        entries = t.fetch()
        full_text = " ".join([e['text'] for e in entries])
        duration = sum([e['duration'] for e in entries]) if entries else 0
        
        return {
            "text": full_text,
            "duration": int(duration),
            "language": language
        }
