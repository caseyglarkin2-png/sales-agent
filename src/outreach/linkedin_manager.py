"""
LinkedIn Outreach Manager.

Manages LinkedIn connection requests and messages.
Since LinkedIn API is restricted, this creates a queue for manual execution.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class LinkedInActionType(Enum):
    CONNECTION_REQUEST = "connection_request"
    DIRECT_MESSAGE = "direct_message"
    INMAIL = "inmail"
    PROFILE_VIEW = "profile_view"
    COMMENT = "comment"
    LIKE = "like"


class ActionStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class LinkedInAction:
    """A LinkedIn action to be performed manually."""
    id: str
    action_type: LinkedInActionType
    contact_email: str
    contact_name: str
    linkedin_url: Optional[str]
    message: str
    company: Optional[str] = None
    job_title: Optional[str] = None
    status: ActionStatus = ActionStatus.PENDING
    created_at: datetime = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    sequence_id: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action_type": self.action_type.value,
            "contact_email": self.contact_email,
            "contact_name": self.contact_name,
            "linkedin_url": self.linkedin_url,
            "message": self.message,
            "company": self.company,
            "job_title": self.job_title,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "notes": self.notes,
            "sequence_id": self.sequence_id,
        }


# Message templates for LinkedIn
CONNECTION_TEMPLATES = {
    "events": """Hi {first_name}, I noticed you're leading field marketing at {company}. I'd love to connect and share some insights on scaling event programs with AI. - Casey""",
    
    "demand_gen": """Hi {first_name}, saw your work in demand gen at {company}. Would love to connect and swap notes on pipeline acceleration. - Casey""",
    
    "sales": """Hi {first_name}, always great to connect with fellow revenue leaders. I'm helping B2B teams align sales and marketing - let's connect! - Casey""",
    
    "executive": """Hi {first_name}, I'm working on AI-powered GTM solutions and thought you might find our approach interesting. Would love to connect. - Casey""",
    
    "default": """Hi {first_name}, I came across your profile and would love to connect. I'm helping B2B companies modernize their go-to-market. - Casey""",
}


class LinkedInManager:
    """Manages LinkedIn outreach queue."""
    
    def __init__(self):
        self.action_queue: List[LinkedInAction] = []
        self.completed_actions: List[LinkedInAction] = []
    
    def create_connection_request(
        self,
        contact_email: str,
        contact_name: str,
        company: str,
        job_title: str,
        linkedin_url: Optional[str] = None,
        persona: Optional[str] = None,
        custom_message: Optional[str] = None,
        sequence_id: Optional[str] = None,
    ) -> LinkedInAction:
        """Create a connection request action.
        
        Args:
            contact_email: Contact email
            contact_name: Full name
            company: Company name
            job_title: Job title
            linkedin_url: LinkedIn profile URL if known
            persona: Persona for template selection
            custom_message: Custom message (overrides template)
            sequence_id: Optional sequence ID
            
        Returns:
            Created action
        """
        # Generate message
        if custom_message:
            message = custom_message
        else:
            template = CONNECTION_TEMPLATES.get(persona, CONNECTION_TEMPLATES["default"])
            first_name = contact_name.split()[0] if contact_name else "there"
            message = template.format(
                first_name=first_name,
                company=company or "your company",
            )
        
        action = LinkedInAction(
            id=f"li_{uuid.uuid4().hex[:8]}",
            action_type=LinkedInActionType.CONNECTION_REQUEST,
            contact_email=contact_email,
            contact_name=contact_name,
            linkedin_url=linkedin_url,
            message=message,
            company=company,
            job_title=job_title,
            sequence_id=sequence_id,
        )
        
        self.action_queue.append(action)
        logger.info(f"Created LinkedIn connection request for {contact_name}")
        
        return action
    
    def create_message(
        self,
        contact_email: str,
        contact_name: str,
        message: str,
        linkedin_url: Optional[str] = None,
        action_type: LinkedInActionType = LinkedInActionType.DIRECT_MESSAGE,
        sequence_id: Optional[str] = None,
    ) -> LinkedInAction:
        """Create a direct message action.
        
        Args:
            contact_email: Contact email
            contact_name: Full name
            message: Message content
            linkedin_url: LinkedIn profile URL
            action_type: Type of message action
            sequence_id: Optional sequence ID
            
        Returns:
            Created action
        """
        action = LinkedInAction(
            id=f"li_{uuid.uuid4().hex[:8]}",
            action_type=action_type,
            contact_email=contact_email,
            contact_name=contact_name,
            linkedin_url=linkedin_url,
            message=message,
            sequence_id=sequence_id,
        )
        
        self.action_queue.append(action)
        logger.info(f"Created LinkedIn message for {contact_name}")
        
        return action
    
    def get_pending_actions(
        self,
        limit: int = 20,
        action_type: Optional[LinkedInActionType] = None,
    ) -> List[Dict[str, Any]]:
        """Get pending actions.
        
        Args:
            limit: Max actions to return
            action_type: Filter by type
            
        Returns:
            List of pending actions
        """
        pending = [a for a in self.action_queue if a.status == ActionStatus.PENDING]
        
        if action_type:
            pending = [a for a in pending if a.action_type == action_type]
        
        return [a.to_dict() for a in pending[:limit]]
    
    def mark_completed(
        self,
        action_id: str,
        notes: Optional[str] = None,
    ) -> bool:
        """Mark an action as completed.
        
        Args:
            action_id: Action ID
            notes: Optional completion notes
            
        Returns:
            True if found and updated
        """
        for action in self.action_queue:
            if action.id == action_id:
                action.status = ActionStatus.COMPLETED
                action.completed_at = datetime.utcnow()
                action.notes = notes
                
                self.completed_actions.append(action)
                self.action_queue.remove(action)
                
                logger.info(f"Marked LinkedIn action {action_id} as completed")
                return True
        
        return False
    
    def mark_skipped(
        self,
        action_id: str,
        reason: Optional[str] = None,
    ) -> bool:
        """Mark an action as skipped.
        
        Args:
            action_id: Action ID
            reason: Skip reason
            
        Returns:
            True if found and updated
        """
        for action in self.action_queue:
            if action.id == action_id:
                action.status = ActionStatus.SKIPPED
                action.completed_at = datetime.utcnow()
                action.notes = reason
                
                self.action_queue.remove(action)
                
                logger.info(f"Marked LinkedIn action {action_id} as skipped")
                return True
        
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get LinkedIn outreach statistics."""
        pending = [a for a in self.action_queue if a.status == ActionStatus.PENDING]
        
        return {
            "pending_count": len(pending),
            "completed_count": len(self.completed_actions),
            "connection_requests_pending": sum(
                1 for a in pending if a.action_type == LinkedInActionType.CONNECTION_REQUEST
            ),
            "messages_pending": sum(
                1 for a in pending if a.action_type == LinkedInActionType.DIRECT_MESSAGE
            ),
        }
    
    def generate_daily_batch(
        self,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Generate a batch of actions for daily execution.
        
        LinkedIn has limits on daily connection requests (~100/week).
        This generates a safe daily batch.
        
        Args:
            limit: Max actions per day
            
        Returns:
            Daily batch of actions
        """
        pending = [a for a in self.action_queue if a.status == ActionStatus.PENDING]
        
        # Prioritize connection requests first
        connections = [a for a in pending if a.action_type == LinkedInActionType.CONNECTION_REQUEST]
        messages = [a for a in pending if a.action_type == LinkedInActionType.DIRECT_MESSAGE]
        
        batch = connections[:limit] + messages[:max(0, limit - len(connections[:limit]))]
        
        return [a.to_dict() for a in batch[:limit]]


# Singleton
_manager: Optional[LinkedInManager] = None


def get_linkedin_manager() -> LinkedInManager:
    """Get singleton LinkedIn manager."""
    global _manager
    if _manager is None:
        _manager = LinkedInManager()
    return _manager
