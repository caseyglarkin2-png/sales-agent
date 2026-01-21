"""
Daily Agenda Generator.

Creates prioritized daily task lists for the operator.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class TaskType(Enum):
    APPROVE_DRAFT = "approve_draft"
    FOLLOW_UP = "follow_up"
    SEQUENCE_STEP = "sequence_step"
    CALL_TASK = "call_task"
    MEETING_PREP = "meeting_prep"
    PROPOSAL_REVIEW = "proposal_review"
    HIGH_PRIORITY_LEAD = "high_priority_lead"


class TaskPriority(Enum):
    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class AgendaTask:
    """A single task on the daily agenda."""
    id: str
    task_type: TaskType
    priority: TaskPriority
    title: str
    description: str
    contact_email: Optional[str] = None
    company: Optional[str] = None
    due_time: Optional[str] = None
    action_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_type": self.task_type.value,
            "priority": self.priority.value,
            "title": self.title,
            "description": self.description,
            "contact_email": self.contact_email,
            "company": self.company,
            "due_time": self.due_time,
            "action_url": self.action_url,
            "metadata": self.metadata,
        }


@dataclass
class DailyAgenda:
    """Complete daily agenda."""
    date: str
    tasks: List[AgendaTask]
    summary: Dict[str, int]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "tasks": [t.to_dict() for t in self.tasks],
            "summary": self.summary,
            "total_tasks": len(self.tasks),
        }


class AgendaGenerator:
    """Generates daily agendas from various data sources."""
    
    def __init__(
        self,
        draft_service=None,
        sequence_engine=None,
        bulk_processor=None,
        calendar_connector=None,
    ):
        self.drafts = draft_service
        self.sequences = sequence_engine
        self.bulk = bulk_processor
        self.calendar = calendar_connector
    
    async def generate_agenda(
        self,
        date: Optional[datetime] = None,
    ) -> DailyAgenda:
        """Generate the daily agenda.
        
        Args:
            date: Date for agenda (defaults to today)
            
        Returns:
            Complete daily agenda
        """
        if date is None:
            date = datetime.utcnow()
        
        tasks: List[AgendaTask] = []
        task_id = 1
        
        # 1. Get pending drafts to approve
        draft_tasks = await self._get_draft_tasks(task_id)
        tasks.extend(draft_tasks)
        task_id += len(draft_tasks)
        
        # 2. Get due sequence steps
        sequence_tasks = await self._get_sequence_tasks(task_id)
        tasks.extend(sequence_tasks)
        task_id += len(sequence_tasks)
        
        # 3. Get high-priority leads in queue
        lead_tasks = await self._get_priority_lead_tasks(task_id)
        tasks.extend(lead_tasks)
        task_id += len(lead_tasks)
        
        # 4. Get upcoming meetings
        meeting_tasks = await self._get_meeting_tasks(task_id, date)
        tasks.extend(meeting_tasks)
        task_id += len(meeting_tasks)
        
        # Sort by priority
        priority_order = {
            TaskPriority.URGENT: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.MEDIUM: 2,
            TaskPriority.LOW: 3,
        }
        tasks.sort(key=lambda t: priority_order.get(t.priority, 99))
        
        # Generate summary
        summary = {
            "urgent": sum(1 for t in tasks if t.priority == TaskPriority.URGENT),
            "high": sum(1 for t in tasks if t.priority == TaskPriority.HIGH),
            "medium": sum(1 for t in tasks if t.priority == TaskPriority.MEDIUM),
            "low": sum(1 for t in tasks if t.priority == TaskPriority.LOW),
            "drafts": sum(1 for t in tasks if t.task_type == TaskType.APPROVE_DRAFT),
            "sequences": sum(1 for t in tasks if t.task_type == TaskType.SEQUENCE_STEP),
            "leads": sum(1 for t in tasks if t.task_type == TaskType.HIGH_PRIORITY_LEAD),
            "meetings": sum(1 for t in tasks if t.task_type == TaskType.MEETING_PREP),
        }
        
        return DailyAgenda(
            date=date.strftime("%Y-%m-%d"),
            tasks=tasks,
            summary=summary,
        )
    
    async def _get_draft_tasks(self, start_id: int) -> List[AgendaTask]:
        """Get pending draft approval tasks."""
        tasks = []
        
        if not self.drafts:
            return tasks
        
        try:
            pending = await self.drafts.get_pending_drafts()
            
            for i, draft in enumerate(pending[:10]):  # Max 10
                tasks.append(AgendaTask(
                    id=f"task_{start_id + i}",
                    task_type=TaskType.APPROVE_DRAFT,
                    priority=TaskPriority.HIGH,
                    title=f"Review draft: {draft.get('subject', 'No subject')[:40]}",
                    description=f"Email to {draft.get('recipient', 'Unknown')}",
                    contact_email=draft.get("recipient"),
                    company=draft.get("company_name"),
                    action_url=f"/api/operator/drafts/{draft.get('id')}",
                    metadata={"draft_id": draft.get("id")},
                ))
                
        except Exception as e:
            logger.warning(f"Could not get draft tasks: {e}")
        
        return tasks
    
    async def _get_sequence_tasks(self, start_id: int) -> List[AgendaTask]:
        """Get due sequence step tasks."""
        tasks = []
        
        if not self.sequences:
            return tasks
        
        try:
            due_steps = await self.sequences.get_due_steps()
            
            for i, step_info in enumerate(due_steps[:10]):
                enrollment = step_info.get("enrollment", {})
                step = step_info.get("step", {})
                
                tasks.append(AgendaTask(
                    id=f"task_{start_id + i}",
                    task_type=TaskType.SEQUENCE_STEP,
                    priority=TaskPriority.MEDIUM,
                    title=f"Sequence step: {step.get('channel', 'email')}",
                    description=f"{step_info.get('sequence_name', 'Sequence')} - Step {enrollment.get('current_step', 1)}",
                    contact_email=enrollment.get("contact_email"),
                    metadata={
                        "enrollment_id": enrollment.get("id"),
                        "channel": step.get("channel"),
                    },
                ))
                
        except Exception as e:
            logger.warning(f"Could not get sequence tasks: {e}")
        
        return tasks
    
    async def _get_priority_lead_tasks(self, start_id: int) -> List[AgendaTask]:
        """Get high-priority leads that need attention."""
        tasks = []
        
        if not self.bulk:
            return tasks
        
        try:
            # Get top leads from queue
            top_leads = self.bulk.get_queue_preview(limit=5)
            
            for i, lead in enumerate(top_leads):
                if lead.get("priority_score", 0) >= 80:  # High priority threshold
                    tasks.append(AgendaTask(
                        id=f"task_{start_id + i}",
                        task_type=TaskType.HIGH_PRIORITY_LEAD,
                        priority=TaskPriority.HIGH,
                        title=f"High-priority lead: {lead.get('email', '')[:30]}",
                        description=f"{lead.get('job_title', '')} at {lead.get('company', '')}",
                        contact_email=lead.get("email"),
                        company=lead.get("company"),
                        metadata={"score": lead.get("priority_score")},
                    ))
                    
        except Exception as e:
            logger.warning(f"Could not get lead tasks: {e}")
        
        return tasks
    
    async def _get_meeting_tasks(self, start_id: int, date: datetime) -> List[AgendaTask]:
        """Get upcoming meeting prep tasks."""
        tasks = []
        
        if not self.calendar:
            return tasks
        
        try:
            # Get today's meetings
            meetings = await self.calendar.get_events(
                start_time=date.replace(hour=0, minute=0),
                end_time=date.replace(hour=23, minute=59),
            )
            
            for i, meeting in enumerate(meetings[:5]):
                attendees = meeting.get("attendees", [])
                external = [a for a in attendees if not a.get("email", "").endswith("@pesti.io")]
                
                if external:
                    tasks.append(AgendaTask(
                        id=f"task_{start_id + i}",
                        task_type=TaskType.MEETING_PREP,
                        priority=TaskPriority.MEDIUM,
                        title=f"Prep for: {meeting.get('summary', 'Meeting')[:40]}",
                        description=f"With {external[0].get('email', 'External')}",
                        contact_email=external[0].get("email") if external else None,
                        due_time=meeting.get("start", {}).get("dateTime"),
                        metadata={"meeting_id": meeting.get("id")},
                    ))
                    
        except Exception as e:
            logger.warning(f"Could not get meeting tasks: {e}")
        
        return tasks


# Singleton
_generator: Optional[AgendaGenerator] = None


def get_agenda_generator(**kwargs) -> AgendaGenerator:
    """Get singleton agenda generator."""
    global _generator
    if _generator is None:
        _generator = AgendaGenerator(**kwargs)
    return _generator
