"""
Multi-Channel Sequence Engine.

Manages multi-step outreach sequences with timing and channel mix.
Supports: Email, LinkedIn, Call reminders
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum
import json
import uuid

logger = logging.getLogger(__name__)


class Channel(Enum):
    EMAIL = "email"
    LINKEDIN = "linkedin"
    CALL = "call"
    TASK = "task"


class StepStatus(Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class EnrollmentStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    REPLIED = "replied"  # Auto-completed when they reply
    UNSUBSCRIBED = "unsubscribed"
    BOUNCED = "bounced"


@dataclass
class SequenceStep:
    """A single step in a sequence."""
    step_number: int
    channel: Channel
    delay_days: int = 0
    delay_hours: int = 0
    subject_template: Optional[str] = None
    body_template: Optional[str] = None
    task_type: Optional[str] = None  # For call/task steps
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "channel": self.channel.value,
            "delay_days": self.delay_days,
            "delay_hours": self.delay_hours,
            "subject_template": self.subject_template,
            "body_template": self.body_template,
            "task_type": self.task_type,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SequenceStep":
        return cls(
            step_number=data["step_number"],
            channel=Channel(data["channel"]),
            delay_days=data.get("delay_days", 0),
            delay_hours=data.get("delay_hours", 0),
            subject_template=data.get("subject_template"),
            body_template=data.get("body_template"),
            task_type=data.get("task_type"),
        )


@dataclass
class Sequence:
    """A multi-step outreach sequence."""
    id: str
    name: str
    description: Optional[str] = None
    steps: List[SequenceStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True
    target_persona: Optional[str] = None  # events, demand_gen, sales, etc.
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active,
            "target_persona": self.target_persona,
            "step_count": len(self.steps),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Sequence":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            steps=[SequenceStep.from_dict(s) for s in data.get("steps", [])],
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.utcnow(),
            is_active=data.get("is_active", True),
            target_persona=data.get("target_persona"),
        )


@dataclass
class SequenceEnrollment:
    """A contact enrolled in a sequence."""
    id: str
    sequence_id: str
    contact_email: str
    contact_name: Optional[str] = None
    current_step: int = 0
    status: EnrollmentStatus = EnrollmentStatus.ACTIVE
    enrolled_at: datetime = field(default_factory=datetime.utcnow)
    next_step_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    step_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sequence_id": self.sequence_id,
            "contact_email": self.contact_email,
            "contact_name": self.contact_name,
            "current_step": self.current_step,
            "status": self.status.value,
            "enrolled_at": self.enrolled_at.isoformat(),
            "next_step_at": self.next_step_at.isoformat() if self.next_step_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "step_history": self.step_history,
        }


# Pre-built sequence templates
SEQUENCE_TEMPLATES = {
    "events_outreach": Sequence(
        id="template_events",
        name="Field Marketing Outreach",
        description="5-step sequence for event/field marketing contacts",
        target_persona="events",
        steps=[
            SequenceStep(
                step_number=1,
                channel=Channel.EMAIL,
                delay_days=0,
                subject_template="Quick question about {{company}}'s event strategy",
                body_template="""Hi {{first_name}},

I noticed you're leading field marketing at {{company}} and wanted to connect.

We help teams like yours run 3x more events with the same resources using AI-powered logistics and follow-up automation.

Would you be open to a 15-minute call to see if this could help {{company}}?

Best,
Casey""",
            ),
            SequenceStep(
                step_number=2,
                channel=Channel.LINKEDIN,
                delay_days=2,
                body_template="Connection request: Hi {{first_name}}, I'd love to connect and share some insights on scaling field marketing programs. - Casey",
            ),
            SequenceStep(
                step_number=3,
                channel=Channel.EMAIL,
                delay_days=4,
                subject_template="Re: Quick question about {{company}}'s event strategy",
                body_template="""Hi {{first_name}},

Following up on my note from last week.

I recently helped a similar company increase their event-to-pipeline conversion by 40% - happy to share how.

Worth a quick call?

Casey""",
            ),
            SequenceStep(
                step_number=4,
                channel=Channel.CALL,
                delay_days=7,
                task_type="call_reminder",
                body_template="Call {{first_name}} at {{company}} - follow up on event marketing outreach",
            ),
            SequenceStep(
                step_number=5,
                channel=Channel.EMAIL,
                delay_days=10,
                subject_template="Last try - event marketing for {{company}}",
                body_template="""Hi {{first_name}},

I'll keep this short - I've reached out a few times about how Pesti helps event marketing teams scale.

If the timing isn't right, no worries at all. But if you'd like to explore this, just reply and we'll set something up.

Best,
Casey""",
            ),
        ],
    ),
    "demand_gen_outreach": Sequence(
        id="template_demand_gen",
        name="Demand Gen Outreach",
        description="5-step sequence for demand gen contacts",
        target_persona="demand_gen",
        steps=[
            SequenceStep(
                step_number=1,
                channel=Channel.EMAIL,
                delay_days=0,
                subject_template="Accelerating {{company}}'s pipeline",
                body_template="""Hi {{first_name}},

Quick question: How much pipeline could {{company}} generate if you could personalize every touchpoint at scale?

We're helping demand gen teams like yours accelerate pipeline velocity using AI - typically seeing 2-3x improvement in lead-to-opp conversion.

Worth 15 minutes to explore?

Casey""",
            ),
            SequenceStep(
                step_number=2,
                channel=Channel.LINKEDIN,
                delay_days=3,
                body_template="Hi {{first_name}} - would love to connect and share some demand gen insights. - Casey",
            ),
            SequenceStep(
                step_number=3,
                channel=Channel.EMAIL,
                delay_days=5,
                subject_template="Re: Accelerating {{company}}'s pipeline",
                body_template="""{{first_name}},

Circling back - I know demand gen leaders are always looking for ways to do more with less.

Just published a case study showing how we helped a similar company hit their pipeline targets 6 weeks early. Happy to share.

Casey""",
            ),
            SequenceStep(
                step_number=4,
                channel=Channel.CALL,
                delay_days=8,
                task_type="call_reminder",
            ),
            SequenceStep(
                step_number=5,
                channel=Channel.EMAIL,
                delay_days=12,
                subject_template="Closing the loop on pipeline acceleration",
                body_template="""Hi {{first_name}},

Last note from me on this - if accelerating {{company}}'s pipeline is a priority, I'd love to show you how Pesti can help.

If not the right time, totally understand. Just reply and let me know either way.

Casey""",
            ),
        ],
    ),
    "executive_outreach": Sequence(
        id="template_executive",
        name="Executive Outreach",
        description="3-step sequence for CMOs/CROs",
        target_persona="executive",
        steps=[
            SequenceStep(
                step_number=1,
                channel=Channel.EMAIL,
                delay_days=0,
                subject_template="GTM efficiency at {{company}}",
                body_template="""{{first_name}},

I'll be brief - we help B2B companies like {{company}} 10x their GTM efficiency using AI agents.

No more manual outreach, proposal writing, or follow-up tracking. Your team focuses on strategy while AI handles execution.

Worth 20 minutes to see if this fits {{company}}'s 2026 plans?

Casey Larkin
Pesti""",
            ),
            SequenceStep(
                step_number=2,
                channel=Channel.EMAIL,
                delay_days=5,
                subject_template="Re: GTM efficiency at {{company}}",
                body_template="""{{first_name}},

Following up - I know your time is valuable.

One data point: Companies using Pesti are seeing 3x pipeline growth with the same team size.

Happy to share specifics if helpful.

Casey""",
            ),
            SequenceStep(
                step_number=3,
                channel=Channel.CALL,
                delay_days=10,
                task_type="executive_call",
                body_template="Call {{first_name}} ({{title}}) at {{company}} - executive GTM conversation",
            ),
        ],
    ),
}


class SequenceEngine:
    """Manages sequence execution."""
    
    def __init__(self, db=None):
        self.db = db
        self.sequences: Dict[str, Sequence] = {}
        self.enrollments: Dict[str, SequenceEnrollment] = {}
        
        # Load templates
        for key, seq in SEQUENCE_TEMPLATES.items():
            self.sequences[seq.id] = seq
    
    async def create_sequence(
        self,
        name: str,
        steps: List[Dict[str, Any]],
        description: Optional[str] = None,
        target_persona: Optional[str] = None,
    ) -> Sequence:
        """Create a new sequence.
        
        Args:
            name: Sequence name
            steps: List of step definitions
            description: Optional description
            target_persona: Target persona (events, demand_gen, etc.)
            
        Returns:
            Created Sequence
        """
        sequence = Sequence(
            id=f"seq_{uuid.uuid4().hex[:8]}",
            name=name,
            description=description,
            target_persona=target_persona,
            steps=[SequenceStep.from_dict(s) for s in steps],
        )
        
        self.sequences[sequence.id] = sequence
        
        # Persist to database
        if self.db:
            await self._save_sequence(sequence)
        
        logger.info(f"Created sequence: {name} ({sequence.id}) with {len(steps)} steps")
        
        return sequence
    
    async def _save_sequence(self, sequence: Sequence):
        """Save sequence to database."""
        try:
            await self.db.execute("""
                INSERT INTO sequences (id, name, description, steps, target_persona, is_active, created_at)
                VALUES (:id, :name, :description, :steps, :target_persona, :is_active, :created_at)
                ON CONFLICT (id) DO UPDATE SET
                    name = :name,
                    description = :description,
                    steps = :steps,
                    target_persona = :target_persona,
                    is_active = :is_active
            """, {
                "id": sequence.id,
                "name": sequence.name,
                "description": sequence.description,
                "steps": json.dumps([s.to_dict() for s in sequence.steps]),
                "target_persona": sequence.target_persona,
                "is_active": sequence.is_active,
                "created_at": sequence.created_at,
            })
        except Exception as e:
            logger.warning(f"Could not save sequence: {e}")
    
    def list_sequences(self) -> List[Dict[str, Any]]:
        """List all available sequences."""
        return [s.to_dict() for s in self.sequences.values()]
    
    def get_sequence(self, sequence_id: str) -> Optional[Sequence]:
        """Get a sequence by ID."""
        return self.sequences.get(sequence_id)
    
    def get_sequence_for_persona(self, persona: str) -> Optional[Sequence]:
        """Get the best sequence for a persona."""
        for seq in self.sequences.values():
            if seq.target_persona == persona and seq.is_active:
                return seq
        
        # Fallback to demand_gen
        return self.sequences.get("template_demand_gen")
    
    async def enroll_contact(
        self,
        sequence_id: str,
        contact_email: str,
        contact_name: Optional[str] = None,
        start_immediately: bool = True,
    ) -> SequenceEnrollment:
        """Enroll a contact in a sequence.
        
        Args:
            sequence_id: Sequence to enroll in
            contact_email: Contact email
            contact_name: Optional contact name
            start_immediately: Whether to schedule first step now
            
        Returns:
            SequenceEnrollment
        """
        sequence = self.sequences.get(sequence_id)
        if not sequence:
            raise ValueError(f"Sequence not found: {sequence_id}")
        
        enrollment = SequenceEnrollment(
            id=f"enr_{uuid.uuid4().hex[:8]}",
            sequence_id=sequence_id,
            contact_email=contact_email,
            contact_name=contact_name,
            current_step=1,
            status=EnrollmentStatus.ACTIVE,
        )
        
        if start_immediately and sequence.steps:
            first_step = sequence.steps[0]
            delay = timedelta(days=first_step.delay_days, hours=first_step.delay_hours)
            enrollment.next_step_at = datetime.utcnow() + delay
        
        self.enrollments[enrollment.id] = enrollment
        
        # Persist
        if self.db:
            await self._save_enrollment(enrollment)
        
        logger.info(f"Enrolled {contact_email} in sequence {sequence.name}")
        
        return enrollment
    
    async def _save_enrollment(self, enrollment: SequenceEnrollment):
        """Save enrollment to database."""
        try:
            await self.db.execute("""
                INSERT INTO sequence_enrollments (id, sequence_id, contact_email, contact_name,
                    current_step, status, enrolled_at, next_step_at, step_history)
                VALUES (:id, :sequence_id, :contact_email, :contact_name,
                    :current_step, :status, :enrolled_at, :next_step_at, :step_history)
                ON CONFLICT (id) DO UPDATE SET
                    current_step = :current_step,
                    status = :status,
                    next_step_at = :next_step_at,
                    step_history = :step_history
            """, {
                "id": enrollment.id,
                "sequence_id": enrollment.sequence_id,
                "contact_email": enrollment.contact_email,
                "contact_name": enrollment.contact_name,
                "current_step": enrollment.current_step,
                "status": enrollment.status.value,
                "enrolled_at": enrollment.enrolled_at,
                "next_step_at": enrollment.next_step_at,
                "step_history": json.dumps(enrollment.step_history),
            })
        except Exception as e:
            logger.warning(f"Could not save enrollment: {e}")
    
    async def get_due_steps(self) -> List[Dict[str, Any]]:
        """Get all steps that are due to execute.
        
        Returns:
            List of enrollments with their due steps
        """
        due_steps = []
        now = datetime.utcnow()
        
        for enrollment in self.enrollments.values():
            if enrollment.status != EnrollmentStatus.ACTIVE:
                continue
            
            if enrollment.next_step_at and enrollment.next_step_at <= now:
                sequence = self.sequences.get(enrollment.sequence_id)
                if not sequence:
                    continue
                
                # Find current step
                current_step = None
                for step in sequence.steps:
                    if step.step_number == enrollment.current_step:
                        current_step = step
                        break
                
                if current_step:
                    due_steps.append({
                        "enrollment": enrollment.to_dict(),
                        "step": current_step.to_dict(),
                        "sequence_name": sequence.name,
                    })
        
        return due_steps
    
    async def execute_step(
        self,
        enrollment_id: str,
        contact_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute the current step for an enrollment.
        
        Args:
            enrollment_id: Enrollment ID
            contact_data: Contact data for template rendering
            
        Returns:
            Execution result
        """
        enrollment = self.enrollments.get(enrollment_id)
        if not enrollment:
            raise ValueError(f"Enrollment not found: {enrollment_id}")
        
        sequence = self.sequences.get(enrollment.sequence_id)
        if not sequence:
            raise ValueError(f"Sequence not found: {enrollment.sequence_id}")
        
        # Find current step
        current_step = None
        for step in sequence.steps:
            if step.step_number == enrollment.current_step:
                current_step = step
                break
        
        if not current_step:
            # No more steps - complete
            enrollment.status = EnrollmentStatus.COMPLETED
            enrollment.completed_at = datetime.utcnow()
            return {"status": "completed", "message": "Sequence completed"}
        
        # Render templates
        rendered_content = self._render_templates(current_step, contact_data)
        
        # Execute based on channel
        result = await self._execute_channel_step(
            current_step.channel,
            enrollment,
            rendered_content,
            contact_data,
        )
        
        # Record in history
        enrollment.step_history.append({
            "step_number": current_step.step_number,
            "channel": current_step.channel.value,
            "executed_at": datetime.utcnow().isoformat(),
            "result": result,
        })
        
        # Advance to next step
        next_step = None
        for step in sequence.steps:
            if step.step_number == enrollment.current_step + 1:
                next_step = step
                break
        
        if next_step:
            enrollment.current_step = next_step.step_number
            delay = timedelta(days=next_step.delay_days, hours=next_step.delay_hours)
            enrollment.next_step_at = datetime.utcnow() + delay
        else:
            enrollment.status = EnrollmentStatus.COMPLETED
            enrollment.completed_at = datetime.utcnow()
            enrollment.next_step_at = None
        
        # Persist
        if self.db:
            await self._save_enrollment(enrollment)
        
        return result
    
    def _render_templates(
        self,
        step: SequenceStep,
        contact_data: Dict[str, Any],
    ) -> Dict[str, str]:
        """Render step templates with contact data."""
        result = {}
        
        replacements = {
            "{{first_name}}": contact_data.get("first_name", "there"),
            "{{last_name}}": contact_data.get("last_name", ""),
            "{{company}}": contact_data.get("company", "your company"),
            "{{title}}": contact_data.get("job_title", ""),
            "{{email}}": contact_data.get("email", ""),
        }
        
        if step.subject_template:
            subject = step.subject_template
            for placeholder, value in replacements.items():
                subject = subject.replace(placeholder, value)
            result["subject"] = subject
        
        if step.body_template:
            body = step.body_template
            for placeholder, value in replacements.items():
                body = body.replace(placeholder, value)
            result["body"] = body
        
        return result
    
    async def _execute_channel_step(
        self,
        channel: Channel,
        enrollment: SequenceEnrollment,
        content: Dict[str, str],
        contact_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute step for a specific channel."""
        
        if channel == Channel.EMAIL:
            # Would create draft or send email
            return {
                "status": "draft_created",
                "channel": "email",
                "subject": content.get("subject"),
                "recipient": enrollment.contact_email,
            }
        
        elif channel == Channel.LINKEDIN:
            # Store for manual action
            return {
                "status": "task_created",
                "channel": "linkedin",
                "action": "Send LinkedIn connection request",
                "message": content.get("body"),
            }
        
        elif channel == Channel.CALL:
            # Create call reminder task
            return {
                "status": "task_created",
                "channel": "call",
                "action": "Make phone call",
                "notes": content.get("body"),
            }
        
        elif channel == Channel.TASK:
            return {
                "status": "task_created",
                "channel": "task",
                "description": content.get("body"),
            }
        
        return {"status": "unknown_channel"}
    
    async def mark_replied(self, contact_email: str):
        """Mark all enrollments for a contact as replied.
        
        Args:
            contact_email: Contact who replied
        """
        for enrollment in self.enrollments.values():
            if enrollment.contact_email.lower() == contact_email.lower():
                if enrollment.status == EnrollmentStatus.ACTIVE:
                    enrollment.status = EnrollmentStatus.REPLIED
                    enrollment.completed_at = datetime.utcnow()
                    logger.info(f"Marked {contact_email} as replied, stopping sequence")
    
    def get_enrollment_status(
        self,
        contact_email: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get enrollment status, optionally filtered by contact.
        
        Args:
            contact_email: Optional email filter
            
        Returns:
            List of enrollment statuses
        """
        results = []
        
        for enrollment in self.enrollments.values():
            if contact_email and enrollment.contact_email.lower() != contact_email.lower():
                continue
            
            sequence = self.sequences.get(enrollment.sequence_id)
            
            results.append({
                **enrollment.to_dict(),
                "sequence_name": sequence.name if sequence else "Unknown",
                "total_steps": len(sequence.steps) if sequence else 0,
            })
        
        return results


# Singleton
_engine: Optional[SequenceEngine] = None


def get_sequence_engine(db=None) -> SequenceEngine:
    """Get singleton sequence engine."""
    global _engine
    if _engine is None:
        _engine = SequenceEngine(db=db)
    return _engine
