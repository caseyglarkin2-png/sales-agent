"""
YouTube content extractor for voice training.

Extracts video transcripts using youtube-transcript-api.
"""
import logging
from typing import Optional, Dict
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


class YouTubeExtractor:
    """Extract transcripts from YouTube videos."""
    
    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """
        Extract YouTube video ID from URL.
        
        Supports formats:
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://www.youtube.com/embed/VIDEO_ID
        """
        try:
            parsed = urlparse(url)
            
            if parsed.hostname in ['www.youtube.com', 'youtube.com']:
                if parsed.path == '/watch':
                    query_params = parse_qs(parsed.query)
                    return query_params.get('v', [None])[0]
                elif parsed.path.startswith('/embed/'):
                    return parsed.path.split('/')[2]
            
            elif parsed.hostname == 'youtu.be':
                return parsed.path[1:]  # Remove leading /
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to parse YouTube URL {url}: {e}")
            return None
    
    @staticmethod
    async def extract_transcript(video_url: str) -> Dict[str, any]:
        """
        Extract transcript from YouTube video.
        
        Returns:
            {
                "video_id": str,
                "title": str,
                "transcript": str,
                "duration": int (seconds),
                "language": str
            }
        """
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
            
        except ImportError:
            logger.error("youtube-transcript-api not installed. Run: pip install youtube-transcript-api")
            raise RuntimeError("youtube-transcript-api package required")
        
        video_id = YouTubeExtractor.extract_video_id(video_url)
        if not video_id:
            raise ValueError(f"Invalid YouTube URL: {video_url}")
        
        try:
            # Fetch transcript (tries multiple languages)
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Try English first, fall back to any available language
            try:
                transcript = transcript_list.find_transcript(['en'])
                language = 'en'
            except NoTranscriptFound:
                transcript = transcript_list.find_generated_transcript(['en'])
                language = 'en (auto-generated)'
            
            # Fetch transcript entries
            entries = transcript.fetch()
            
            # Combine into single text
            full_text = " ".join(entry['text'] for entry in entries)
            duration = int(entries[-1]['start'] + entries[-1]['duration']) if entries else 0
            
            # Get video title (requires additional API call - optional)
            title = f"YouTube Video {video_id}"
            
            return {
                "video_id": video_id,
                "title": title,
                "transcript": full_text,
                "duration": duration,
                "language": language,
                "entry_count": len(entries)
            }
            
        except TranscriptsDisabled:
            raise ValueError(f"Transcripts are disabled for video {video_id}")
        
        except NoTranscriptFound:
            raise ValueError(f"No transcript available for video {video_id}")
        
        except Exception as e:
            logger.error(f"Failed to extract transcript from {video_url}: {e}")
            raise RuntimeError(f"Transcript extraction failed: {str(e)}")
    
    @staticmethod
    async def extract(url: str) -> Dict[str, any]:
        """
        Extract content from YouTube URL.
        
        Returns standardized format:
            {
                "title": str,
                "content": str,
                "source_id": str (video_id),
                "metadata": dict
            }
        """
        result = await YouTubeExtractor.extract_transcript(url)
        
        return {
            "title": result["title"],
            "content": result["transcript"],
            "source_id": result["video_id"],
            "metadata": {
                "duration": result["duration"],
                "language": result["language"],
                "entry_count": result["entry_count"],
                "video_url": url
            }
        }
