"""
Email Reply Detector.

Monitors Gmail for replies to stop sequences and track engagement.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)


class ReplyDetector:
    """Detects and tracks email replies from prospects."""
    
    def __init__(self, gmail_connector=None, sequences_engine=None):
        self.gmail = gmail_connector
        self.sequences = sequences_engine
        self.tracked_threads: Dict[str, Dict[str, Any]] = {}
    
    async def check_for_replies(
        self,
        since_hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """Check Gmail for new replies from tracked contacts.
        
        Args:
            since_hours: Look back this many hours
            
        Returns:
            List of detected replies
        """
        replies = []
        
        if not self.gmail:
            logger.warning("Gmail connector not available")
            return replies
        
        try:
            # Search for recent inbound emails
            since_date = datetime.utcnow() - timedelta(hours=since_hours)
            query = f"in:inbox after:{since_date.strftime('%Y/%m/%d')}"
            
            messages = await self.gmail.search_messages(query, max_results=50)
            
            for msg in messages:
                # Check if sender is someone we've emailed
                sender = self._extract_email(msg.get("from", ""))
                if not sender:
                    continue
                
                # Check if this is a reply (has Re: in subject or is part of a thread)
                subject = msg.get("subject", "")
                is_reply = subject.lower().startswith("re:") or msg.get("threadId") in self.tracked_threads
                
                if is_reply or await self._is_tracked_contact(sender):
                    reply_info = {
                        "from": sender,
                        "subject": subject,
                        "date": msg.get("date"),
                        "snippet": msg.get("snippet", "")[:200],
                        "thread_id": msg.get("threadId"),
                        "message_id": msg.get("id"),
                    }
                    replies.append(reply_info)
                    
                    # Mark as replied in sequences
                    if self.sequences:
                        await self.sequences.mark_replied(sender)
                    
                    logger.info(f"Detected reply from {sender}")
            
            return replies
            
        except Exception as e:
            logger.error(f"Error checking for replies: {e}")
            return replies
    
    def _extract_email(self, from_header: str) -> Optional[str]:
        """Extract email address from From header."""
        match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', from_header)
        return match.group(0).lower() if match else None
    
    async def _is_tracked_contact(self, email: str) -> bool:
        """Check if this email is from a contact we're tracking."""
        # Check sequences
        if self.sequences:
            enrollments = self.sequences.get_enrollment_status(contact_email=email)
            if enrollments:
                return True
        return False
    
    def track_outbound(
        self,
        thread_id: str,
        recipient_email: str,
        subject: str,
    ):
        """Track an outbound email for reply detection.
        
        Args:
            thread_id: Gmail thread ID
            recipient_email: Who we emailed
            subject: Email subject
        """
        self.tracked_threads[thread_id] = {
            "recipient": recipient_email.lower(),
            "subject": subject,
            "sent_at": datetime.utcnow().isoformat(),
        }
    
    async def get_engagement_stats(
        self,
        contact_email: str,
    ) -> Dict[str, Any]:
        """Get engagement statistics for a contact.
        
        Args:
            contact_email: Contact email
            
        Returns:
            Engagement stats
        """
        stats = {
            "email": contact_email,
            "emails_sent": 0,
            "emails_opened": 0,
            "replies_received": 0,
            "last_engagement": None,
            "engagement_score": 0,
        }
        
        # This would integrate with email tracking pixels or HubSpot engagement data
        # For now, return basic structure
        
        return stats


# Singleton
_detector: Optional[ReplyDetector] = None


def get_reply_detector(gmail=None, sequences=None) -> ReplyDetector:
    """Get singleton reply detector."""
    global _detector
    if _detector is None:
        _detector = ReplyDetector(gmail_connector=gmail, sequences_engine=sequences)
    return _detector
