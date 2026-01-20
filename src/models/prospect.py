"""Prospect and Task models for the prospecting workflow."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class Prospect(BaseModel):
    """Represents a sales prospect extracted from form submissions."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    first_name: str = ""
    last_name: str = ""
    company: str = ""
    phone: Optional[str] = None
    job_title: Optional[str] = None
    source: str = "form_submission"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def full_name(self) -> str:
        """Get the prospect's full name."""
        return f"{self.first_name} {self.last_name}".strip()
    
    def dict(self, *args, **kwargs) -> dict:
        """Override dict to include full_name."""
        d = super().model_dump(*args, **kwargs)
        d["full_name"] = self.full_name
        return d


class Task(BaseModel):
    """Represents a follow-up task for the sales team."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str = ""
    prospect_id: Optional[str] = None
    prospect_email: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: str = "medium"  # low, medium, high
    status: str = "pending"  # pending, in_progress, completed
    assigned_to: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    hubspot_task_id: Optional[str] = None
