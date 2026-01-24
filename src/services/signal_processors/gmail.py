"""Gmail reply signal processor."""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from src.models.signal import Signal, SignalSource
from src.models.command_queue import CommandQueueItem
from src.services.signal_processors.base import SignalProcessor
from src.services.aps_calculator import calculate_aps
from src.logger import get_logger

logger = get_logger(__name__)


class GmailReplySignalProcessor(SignalProcessor):
    """
    Processes Gmail reply signals and creates follow-up recommendations.
    
    Handles:
    - reply_received: When a prospect/lead replies to our email
    - thread_updated: When there's activity on a tracked thread
    """

    @property
    def source_name(self) -> str:
        return "gmail"

    def can_handle(self, signal: Signal) -> bool:
        """Handle signals from Gmail source with reply event types."""
        if signal.source != SignalSource.GMAIL:
            return False
        
        reply_event_types = [
            "reply_received",
            "thread_updated",
        ]
        return signal.event_type in reply_event_types

    async def validate(self, signal: Signal) -> bool:
        """Validate Gmail reply signal has required fields."""
        if not await super().validate(signal):
            return False
        
        payload = signal.payload
        
        # Must have thread_id
        if not payload.get("thread_id"):
            logger.warning(f"Signal {signal.id} missing thread_id in payload")
            return False
        
        # Must have from_email
        if not payload.get("from_email"):
            logger.warning(f"Signal {signal.id} missing from_email in payload")
            return False
        
        return True

    async def process(self, signal: Signal) -> Optional[CommandQueueItem]:
        """
        Process Gmail reply signal and create follow-up recommendation.
        
        Args:
            signal: Gmail reply signal
            
        Returns:
            CommandQueueItem for follow-up action, or None if invalid
        """
        if not self.can_handle(signal):
            return None
        
        if not await self.validate(signal):
            logger.warning(f"Invalid Gmail reply signal {signal.id}, skipping")
            return None

        payload = signal.payload
        thread_id = payload.get("thread_id")
        from_email = payload.get("from_email", "")
        from_name = payload.get("from_name", "Unknown")
        subject = payload.get("subject", "Re: [Thread]")
        snippet = payload.get("snippet", "")
        is_positive = payload.get("is_positive", True)  # Sentiment hint
        company = payload.get("company", "")
        
        # Determine action type based on reply content
        action_type = self._determine_action_type(payload)
        
        # Calculate urgency - replies are high priority
        urgency = self._calculate_urgency(payload)
        
        # Build context for the action
        action_context = {
            "thread_id": thread_id,
            "from_email": from_email,
            "from_name": from_name,
            "subject": subject,
            "snippet": snippet[:200] if snippet else "",  # Truncate snippet
            "company": company,
            "is_positive": is_positive,
            "signal_id": signal.id,
            "source": "gmail_reply",
        }
        
        # Calculate APS - replies are typically high priority
        aps_result = calculate_aps(
            action_type=action_type,
            context={
                "revenue_impact": payload.get("revenue_potential", 0.7),
                "urgency": urgency,
                "strategic_value": 0.7 if is_positive else 0.4,
                "effort": 0.3,  # Medium effort to respond
            }
        )
        
        # Replies need fast response
        due_by = self._calculate_due_by(payload)
        
        # Create the command queue item
        item = CommandQueueItem(
            id=str(uuid4()),
            priority_score=aps_result.score / 100.0,
            action_type=action_type,
            action_context=action_context,
            status="pending",
            owner="casey",
            due_by=due_by,
            recommendation_id=None,
            created_at=datetime.utcnow(),
        )
        
        logger.info(
            f"Created recommendation for reply from '{from_name}' <{from_email}> "
            f"(action: {action_type}, APS: {aps_result.score})"
        )
        
        return item

    def _determine_action_type(self, payload: Dict[str, Any]) -> str:
        """Determine action type based on reply content."""
        snippet = (payload.get("snippet") or "").lower()
        
        # Check for meeting-related keywords
        meeting_keywords = ["meet", "call", "schedule", "calendar", "time", "available"]
        if any(kw in snippet for kw in meeting_keywords):
            return "schedule_meeting"
        
        # Check for interest keywords
        interest_keywords = ["interested", "tell me more", "pricing", "demo", "trial"]
        if any(kw in snippet for kw in interest_keywords):
            return "email_follow_up"
        
        # Check for negative keywords
        negative_keywords = ["unsubscribe", "not interested", "remove", "stop"]
        if any(kw in snippet for kw in negative_keywords):
            return "unsubscribe_process"
        
        # Default - reply to thread
        return "thread_reply"

    def _calculate_urgency(self, payload: Dict[str, Any]) -> float:
        """Calculate urgency based on reply context."""
        is_positive = payload.get("is_positive", True)
        snippet = (payload.get("snippet") or "").lower()
        
        # High urgency for positive/engaged responses
        if is_positive:
            base_urgency = 0.85
        else:
            base_urgency = 0.5
        
        # Boost for meeting-related replies
        if any(kw in snippet for kw in ["meet", "call", "schedule"]):
            base_urgency = min(0.95, base_urgency + 0.1)
        
        # Boost for pricing/demo requests
        if any(kw in snippet for kw in ["pricing", "demo", "trial"]):
            base_urgency = min(0.95, base_urgency + 0.1)
        
        return base_urgency

    def _calculate_due_by(self, payload: Dict[str, Any]) -> datetime:
        """Calculate due_by based on reply urgency."""
        now = datetime.utcnow()
        is_positive = payload.get("is_positive", True)
        
        if is_positive:
            # Positive replies - respond within 2 hours
            return now + timedelta(hours=2)
        else:
            # Negative/neutral - can wait longer
            return now + timedelta(hours=8)


def create_reply_signals_from_threads(
    threads: List[Dict[str, Any]],
    our_sent_message_ids: List[str],
    last_checked: Optional[datetime] = None
) -> List[Signal]:
    """
    Create Signal objects from Gmail threads by detecting replies.
    
    A reply is detected when:
    1. Thread contains a message we sent (message_id in our_sent_message_ids)
    2. Thread has a newer message from someone else
    
    Args:
        threads: List of thread dicts from Gmail API
        our_sent_message_ids: List of message IDs that we sent
        last_checked: Only create signals for newer messages
        
    Returns:
        List of Signal objects for detected replies
    """
    signals = []
    our_ids_set = set(our_sent_message_ids)
    
    for thread in threads:
        thread_id = thread.get("id")
        messages = thread.get("messages", [])
        
        if not messages:
            continue
        
        # Check if we have a sent message in this thread
        our_message_in_thread = False
        for msg in messages:
            if msg.get("id") in our_ids_set:
                our_message_in_thread = True
                break
        
        if not our_message_in_thread:
            continue  # Thread doesn't contain our messages
        
        # Find the latest message that isn't ours
        latest_reply = None
        for msg in reversed(messages):
            if msg.get("id") not in our_ids_set:
                latest_reply = msg
                break
        
        if not latest_reply:
            continue  # No reply from others
        
        # Check if reply is newer than last_checked
        internal_date = latest_reply.get("internalDate")
        if internal_date and last_checked:
            reply_time = datetime.fromtimestamp(int(internal_date) / 1000)
            if reply_time <= last_checked:
                continue  # Already processed
        
        # Extract sender info from headers
        headers = {h["name"].lower(): h["value"] for h in latest_reply.get("payload", {}).get("headers", [])}
        from_header = headers.get("from", "")
        subject = headers.get("subject", "")
        
        # Parse from header (e.g., "John Doe <john@example.com>")
        from_name, from_email = _parse_from_header(from_header)
        
        signal = Signal(
            id=str(uuid4()),
            source=SignalSource.GMAIL,
            event_type="reply_received",
            source_id=f"reply-{latest_reply.get('id')}",
            payload={
                "thread_id": thread_id,
                "message_id": latest_reply.get("id"),
                "from_email": from_email,
                "from_name": from_name,
                "subject": subject,
                "snippet": latest_reply.get("snippet", ""),
                "is_positive": True,  # Default to positive - could enhance with sentiment
            },
            created_at=datetime.utcnow(),
        )
        signals.append(signal)
    
    logger.info(f"Created {len(signals)} reply signals from {len(threads)} threads")
    return signals


def _parse_from_header(from_header: str) -> tuple:
    """Parse From header into (name, email)."""
    import re
    
    # Match "Name <email@example.com>" format
    match = re.match(r'^(.+?)\s*<(.+?)>$', from_header)
    if match:
        name = match.group(1).strip().strip('"')
        email = match.group(2).strip()
        return (name, email)
    
    # Just email address
    if "@" in from_header:
        return ("", from_header.strip())
    
    return ("Unknown", "")
