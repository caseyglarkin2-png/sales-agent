"""
HubSpot content extractor for voice training.

Supports:
- Email threads from contacts/deals
- Call recordings and transcripts
- Notes from contacts/deals
- Meeting transcripts
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class HubSpotExtractor:
    """Extract content from HubSpot for voice training."""
    
    def __init__(self, api_key: str):
        """
        Initialize HubSpot extractor.
        
        Args:
            api_key: HubSpot API key
        """
        self.api_key = api_key
        self.base_url = "https://api.hubapi.com"
    
    async def extract_email_thread(self, engagement_id: str) -> Dict:
        """
        Extract email thread from HubSpot.
        
        Args:
            engagement_id: HubSpot engagement ID for email
        
        Returns:
            {
                "title": str,
                "content": str (formatted email thread),
                "source_id": str,
                "source_metadata": dict
            }
        """
        import httpx
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                # Get engagement details
                response = await client.get(
                    f"{self.base_url}/engagements/v1/engagements/{engagement_id}",
                    headers=headers
                )
                response.raise_for_status()
                engagement = response.json()
                
                # Extract email content
                metadata = engagement.get("engagement", {}).get("metadata", {})
                subject = metadata.get("subject", "No Subject")
                from_email = metadata.get("from", {}).get("email", "Unknown")
                to_emails = [t.get("email") for t in metadata.get("to", [])]
                body = metadata.get("html", "") or metadata.get("text", "")
                
                # Format as readable thread
                content = f"Subject: {subject}\n"
                content += f"From: {from_email}\n"
                content += f"To: {', '.join(to_emails)}\n"
                content += f"\n{body}\n"
                
                return {
                    "title": f"Email: {subject}",
                    "content": content,
                    "source_id": engagement_id,
                    "source_metadata": {
                        "type": "email",
                        "subject": subject,
                        "from": from_email,
                        "to": to_emails,
                        "timestamp": engagement.get("engagement", {}).get("timestamp"),
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to extract email thread {engagement_id}: {e}")
            raise RuntimeError(f"Could not extract email thread: {str(e)}")
    
    async def extract_call_transcript(self, engagement_id: str) -> Dict:
        """
        Extract call recording/transcript from HubSpot.
        
        Args:
            engagement_id: HubSpot engagement ID for call
        
        Returns:
            Content dict with transcript
        """
        import httpx
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/engagements/v1/engagements/{engagement_id}",
                    headers=headers
                )
                response.raise_for_status()
                engagement = response.json()
                
                metadata = engagement.get("engagement", {}).get("metadata", {})
                title = metadata.get("title", "Untitled Call")
                body = metadata.get("body", "")
                duration = metadata.get("durationMilliseconds", 0)
                
                # Format call notes
                content = f"Call: {title}\n"
                content += f"Duration: {duration/1000:.0f} seconds\n"
                content += f"\nNotes:\n{body}\n"
                
                # Check for recording URL (if available)
                recording_url = metadata.get("recordingUrl")
                if recording_url:
                    content += f"\n[Recording: {recording_url}]\n"
                
                return {
                    "title": f"Call: {title}",
                    "content": content,
                    "source_id": engagement_id,
                    "source_metadata": {
                        "type": "call",
                        "title": title,
                        "duration_ms": duration,
                        "recording_url": recording_url,
                        "timestamp": engagement.get("engagement", {}).get("timestamp"),
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to extract call {engagement_id}: {e}")
            raise RuntimeError(f"Could not extract call transcript: {str(e)}")
    
    async def extract_notes(self, engagement_id: str) -> Dict:
        """
        Extract notes from HubSpot contact/deal.
        
        Args:
            engagement_id: HubSpot engagement ID for note
        
        Returns:
            Content dict with notes
        """
        import httpx
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/engagements/v1/engagements/{engagement_id}",
                    headers=headers
                )
                response.raise_for_status()
                engagement = response.json()
                
                metadata = engagement.get("engagement", {}).get("metadata", {})
                body = metadata.get("body", "")
                
                return {
                    "title": f"Note from {datetime.now().strftime('%Y-%m-%d')}",
                    "content": body,
                    "source_id": engagement_id,
                    "source_metadata": {
                        "type": "note",
                        "timestamp": engagement.get("engagement", {}).get("timestamp"),
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to extract note {engagement_id}: {e}")
            raise RuntimeError(f"Could not extract note: {str(e)}")
    
    async def extract(self, engagement_id: str, engagement_type: str = None) -> Dict:
        """
        Extract content from HubSpot engagement.
        
        Args:
            engagement_id: HubSpot engagement ID
            engagement_type: Type of engagement (email, call, note) - auto-detected if not provided
        
        Returns:
            {
                "title": str,
                "content": str,
                "source_id": str,
                "source_metadata": dict
            }
        """
        import httpx
        
        # Auto-detect type if not provided
        if not engagement_type:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.base_url}/engagements/v1/engagements/{engagement_id}",
                        headers=headers
                    )
                    response.raise_for_status()
                    engagement = response.json()
                    engagement_type = engagement.get("engagement", {}).get("type", "").lower()
            except Exception as e:
                logger.error(f"Failed to detect engagement type: {e}")
                raise ValueError(f"Could not determine engagement type: {str(e)}")
        
        # Route to appropriate extractor
        if engagement_type == "email":
            return await self.extract_email_thread(engagement_id)
        elif engagement_type == "call":
            return await self.extract_call_transcript(engagement_id)
        elif engagement_type == "note":
            return await self.extract_notes(engagement_id)
        else:
            raise ValueError(f"Unsupported engagement type: {engagement_type}")
    
    @staticmethod
    def extract_engagement_id_from_url(url: str) -> Optional[str]:
        """
        Extract engagement ID from HubSpot URL.
        
        Supports:
        - https://app.hubspot.com/contacts/PORTAL/record/OBJECT/ENGAGEMENT_ID
        """
        import re
        
        patterns = [
            r'/record/[^/]+/(\d+)',
            r'engagementId=(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # If no match, assume it's a raw ID
        if url.isdigit():
            return url
        
        return None
