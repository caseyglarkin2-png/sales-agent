"""
Playbook Service - Sales Playbook Management
=============================================
Handles sales playbooks, guided selling, and best practices.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid


class PlaybookStatus(str, Enum):
    """Playbook status."""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class StepType(str, Enum):
    """Playbook step type."""
    TASK = "task"
    EMAIL = "email"
    CALL = "call"
    MEETING = "meeting"
    CONTENT = "content"
    APPROVAL = "approval"
    WAIT = "wait"
    CONDITION = "condition"


class TriggerType(str, Enum):
    """Playbook trigger type."""
    MANUAL = "manual"
    DEAL_STAGE = "deal_stage"
    DEAL_CREATED = "deal_created"
    MEETING_COMPLETED = "meeting_completed"
    EMAIL_OPENED = "email_opened"
    SCORE_THRESHOLD = "score_threshold"


@dataclass
class ContentItem:
    """Content item for a playbook step."""
    id: str
    title: str
    content_type: str  # document, video, link, template
    url: Optional[str] = None
    description: str = ""


@dataclass
class PlaybookStep:
    """A step in a playbook."""
    id: str
    name: str
    description: str
    step_type: StepType
    order: int
    
    # Content
    instructions: str = ""
    content_items: list[ContentItem] = field(default_factory=list)
    
    # Templates
    email_template_id: Optional[str] = None
    task_template: Optional[dict[str, Any]] = None
    
    # Timing
    delay_days: int = 0
    due_in_days: int = 1
    
    # Conditions
    conditions: list[dict[str, Any]] = field(default_factory=list)
    skip_conditions: list[dict[str, Any]] = field(default_factory=list)
    
    # Outcomes
    outcomes: list[str] = field(default_factory=list)  # Possible step outcomes
    
    # Requirements
    required: bool = True
    approver_role: Optional[str] = None  # For approval steps
    
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Playbook:
    """A sales playbook."""
    id: str
    name: str
    description: str
    
    # Category
    category: str = "general"  # discovery, demo, negotiation, closing
    
    # Target
    deal_stages: list[str] = field(default_factory=list)
    segments: list[str] = field(default_factory=list)
    industries: list[str] = field(default_factory=list)
    
    # Steps
    steps: list[PlaybookStep] = field(default_factory=list)
    
    # Trigger
    trigger_type: TriggerType = TriggerType.MANUAL
    trigger_conditions: dict[str, Any] = field(default_factory=dict)
    
    # Settings
    estimated_duration_days: int = 7
    success_criteria: dict[str, Any] = field(default_factory=dict)
    
    # Status
    status: PlaybookStatus = PlaybookStatus.DRAFT
    
    # Ownership
    owner_id: Optional[str] = None
    team_ids: list[str] = field(default_factory=list)
    
    # Metrics
    usage_count: int = 0
    success_rate: float = 0.0
    avg_completion_days: float = 0.0
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None


@dataclass
class StepExecution:
    """Execution of a single playbook step."""
    id: str
    step_id: str
    status: str = "pending"  # pending, in_progress, completed, skipped
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    
    # Outcome
    outcome: Optional[str] = None
    notes: str = ""
    
    # Created task/activity IDs
    created_task_id: Optional[str] = None
    created_activity_id: Optional[str] = None


@dataclass
class PlaybookExecution:
    """Execution of a playbook for a deal."""
    id: str
    playbook_id: str
    deal_id: str
    user_id: str
    
    # Steps
    step_executions: list[StepExecution] = field(default_factory=list)
    current_step: int = 0
    
    # Status
    status: str = "active"  # active, completed, abandoned, paused
    
    # Progress
    steps_completed: int = 0
    total_steps: int = 0
    progress_percent: float = 0.0
    
    # Timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    
    # Outcome
    outcome: Optional[str] = None  # success, failure, abandoned
    outcome_notes: str = ""
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class PlaybookService:
    """Service for playbook management."""
    
    def __init__(self):
        self.playbooks: dict[str, Playbook] = {}
        self.executions: dict[str, PlaybookExecution] = {}
        self._init_sample_playbooks()
    
    def _init_sample_playbooks(self) -> None:
        """Initialize sample playbooks."""
        discovery = Playbook(
            id="pb-discovery",
            name="Enterprise Discovery",
            description="Discovery playbook for enterprise accounts",
            category="discovery",
            status=PlaybookStatus.PUBLISHED,
            deal_stages=["discovery"],
            steps=[
                PlaybookStep(
                    id="step-1",
                    name="Initial Research",
                    description="Research the prospect company",
                    step_type=StepType.TASK,
                    order=1,
                    instructions="Research the company website, news, and LinkedIn",
                    due_in_days=1,
                ),
                PlaybookStep(
                    id="step-2",
                    name="Send Introduction Email",
                    description="Send personalized introduction",
                    step_type=StepType.EMAIL,
                    order=2,
                    delay_days=1,
                    outcomes=["replied", "opened", "no_response"],
                ),
                PlaybookStep(
                    id="step-3",
                    name="Discovery Call",
                    description="Schedule and conduct discovery call",
                    step_type=StepType.CALL,
                    order=3,
                    delay_days=2,
                    instructions="Use BANT framework to qualify",
                    outcomes=["qualified", "not_qualified", "needs_follow_up"],
                ),
            ],
            estimated_duration_days=5,
        )
        
        demo = Playbook(
            id="pb-demo",
            name="Product Demo",
            description="Guided demo playbook",
            category="demo",
            status=PlaybookStatus.PUBLISHED,
            deal_stages=["demo"],
            steps=[
                PlaybookStep(
                    id="step-1",
                    name="Pre-Demo Prep",
                    description="Prepare customized demo",
                    step_type=StepType.TASK,
                    order=1,
                    instructions="Review discovery notes and customize demo environment",
                ),
                PlaybookStep(
                    id="step-2",
                    name="Send Demo Agenda",
                    description="Share demo agenda with stakeholders",
                    step_type=StepType.EMAIL,
                    order=2,
                    delay_days=1,
                ),
                PlaybookStep(
                    id="step-3",
                    name="Conduct Demo",
                    description="Deliver product demonstration",
                    step_type=StepType.MEETING,
                    order=3,
                    outcomes=["interested", "needs_poc", "not_interested"],
                ),
                PlaybookStep(
                    id="step-4",
                    name="Send Follow-up",
                    description="Send demo recording and next steps",
                    step_type=StepType.EMAIL,
                    order=4,
                    delay_days=1,
                ),
            ],
        )
        
        self.playbooks[discovery.id] = discovery
        self.playbooks[demo.id] = demo
    
    # Playbook CRUD
    async def create_playbook(
        self,
        name: str,
        description: str,
        category: str = "general",
        owner_id: Optional[str] = None,
        **kwargs
    ) -> Playbook:
        """Create a playbook."""
        playbook = Playbook(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            category=category,
            owner_id=owner_id,
            **kwargs
        )
        self.playbooks[playbook.id] = playbook
        return playbook
    
    async def get_playbook(self, playbook_id: str) -> Optional[Playbook]:
        """Get a playbook by ID."""
        return self.playbooks.get(playbook_id)
    
    async def update_playbook(
        self,
        playbook_id: str,
        updates: dict[str, Any]
    ) -> Optional[Playbook]:
        """Update a playbook."""
        playbook = self.playbooks.get(playbook_id)
        if not playbook:
            return None
        
        for key, value in updates.items():
            if hasattr(playbook, key):
                setattr(playbook, key, value)
        
        playbook.updated_at = datetime.utcnow()
        return playbook
    
    async def delete_playbook(self, playbook_id: str) -> bool:
        """Delete a playbook."""
        if playbook_id in self.playbooks:
            del self.playbooks[playbook_id]
            return True
        return False
    
    async def list_playbooks(
        self,
        category: Optional[str] = None,
        status: Optional[PlaybookStatus] = None,
        deal_stage: Optional[str] = None,
        limit: int = 100
    ) -> list[Playbook]:
        """List playbooks."""
        playbooks = list(self.playbooks.values())
        
        if category:
            playbooks = [p for p in playbooks if p.category == category]
        if status:
            playbooks = [p for p in playbooks if p.status == status]
        if deal_stage:
            playbooks = [p for p in playbooks if deal_stage in p.deal_stages]
        
        playbooks.sort(key=lambda p: p.name)
        return playbooks[:limit]
    
    async def publish_playbook(self, playbook_id: str) -> bool:
        """Publish a playbook."""
        playbook = self.playbooks.get(playbook_id)
        if not playbook or playbook.status != PlaybookStatus.DRAFT:
            return False
        
        playbook.status = PlaybookStatus.PUBLISHED
        playbook.published_at = datetime.utcnow()
        playbook.updated_at = datetime.utcnow()
        return True
    
    async def archive_playbook(self, playbook_id: str) -> bool:
        """Archive a playbook."""
        playbook = self.playbooks.get(playbook_id)
        if not playbook:
            return False
        
        playbook.status = PlaybookStatus.ARCHIVED
        playbook.updated_at = datetime.utcnow()
        return True
    
    # Steps
    async def add_step(
        self,
        playbook_id: str,
        name: str,
        description: str,
        step_type: StepType,
        order: Optional[int] = None,
        **kwargs
    ) -> Optional[PlaybookStep]:
        """Add a step to a playbook."""
        playbook = self.playbooks.get(playbook_id)
        if not playbook:
            return None
        
        if order is None:
            order = len(playbook.steps) + 1
        
        step = PlaybookStep(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            step_type=step_type,
            order=order,
            **kwargs
        )
        
        playbook.steps.append(step)
        playbook.steps.sort(key=lambda s: s.order)
        playbook.updated_at = datetime.utcnow()
        
        return step
    
    async def update_step(
        self,
        playbook_id: str,
        step_id: str,
        updates: dict[str, Any]
    ) -> Optional[PlaybookStep]:
        """Update a step."""
        playbook = self.playbooks.get(playbook_id)
        if not playbook:
            return None
        
        step = next((s for s in playbook.steps if s.id == step_id), None)
        if not step:
            return None
        
        for key, value in updates.items():
            if hasattr(step, key):
                setattr(step, key, value)
        
        playbook.updated_at = datetime.utcnow()
        return step
    
    async def remove_step(self, playbook_id: str, step_id: str) -> bool:
        """Remove a step from a playbook."""
        playbook = self.playbooks.get(playbook_id)
        if not playbook:
            return False
        
        original = len(playbook.steps)
        playbook.steps = [s for s in playbook.steps if s.id != step_id]
        
        if len(playbook.steps) < original:
            # Reorder remaining steps
            for i, step in enumerate(playbook.steps):
                step.order = i + 1
            playbook.updated_at = datetime.utcnow()
            return True
        
        return False
    
    async def reorder_steps(
        self,
        playbook_id: str,
        step_order: list[str]  # List of step IDs in new order
    ) -> bool:
        """Reorder playbook steps."""
        playbook = self.playbooks.get(playbook_id)
        if not playbook:
            return False
        
        step_map = {s.id: s for s in playbook.steps}
        
        for i, step_id in enumerate(step_order):
            if step_id in step_map:
                step_map[step_id].order = i + 1
        
        playbook.steps.sort(key=lambda s: s.order)
        playbook.updated_at = datetime.utcnow()
        
        return True
    
    # Execution
    async def start_execution(
        self,
        playbook_id: str,
        deal_id: str,
        user_id: str
    ) -> Optional[PlaybookExecution]:
        """Start a playbook execution for a deal."""
        playbook = self.playbooks.get(playbook_id)
        if not playbook or playbook.status != PlaybookStatus.PUBLISHED:
            return None
        
        # Create step executions
        step_executions = []
        for step in playbook.steps:
            from datetime import timedelta
            
            step_exec = StepExecution(
                id=str(uuid.uuid4()),
                step_id=step.id,
                due_date=datetime.utcnow() + timedelta(days=step.delay_days + step.due_in_days),
            )
            step_executions.append(step_exec)
        
        execution = PlaybookExecution(
            id=str(uuid.uuid4()),
            playbook_id=playbook_id,
            deal_id=deal_id,
            user_id=user_id,
            step_executions=step_executions,
            total_steps=len(step_executions),
        )
        
        # Start first step
        if step_executions:
            step_executions[0].status = "in_progress"
            step_executions[0].started_at = datetime.utcnow()
        
        self.executions[execution.id] = execution
        
        # Update playbook usage
        playbook.usage_count += 1
        
        return execution
    
    async def get_execution(self, execution_id: str) -> Optional[PlaybookExecution]:
        """Get an execution by ID."""
        return self.executions.get(execution_id)
    
    async def list_executions(
        self,
        playbook_id: Optional[str] = None,
        deal_id: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> list[PlaybookExecution]:
        """List executions."""
        executions = list(self.executions.values())
        
        if playbook_id:
            executions = [e for e in executions if e.playbook_id == playbook_id]
        if deal_id:
            executions = [e for e in executions if e.deal_id == deal_id]
        if user_id:
            executions = [e for e in executions if e.user_id == user_id]
        if status:
            executions = [e for e in executions if e.status == status]
        
        executions.sort(key=lambda e: e.started_at, reverse=True)
        return executions[:limit]
    
    async def complete_step(
        self,
        execution_id: str,
        step_id: str,
        outcome: Optional[str] = None,
        notes: str = ""
    ) -> bool:
        """Complete a step in an execution."""
        execution = self.executions.get(execution_id)
        if not execution or execution.status != "active":
            return False
        
        step_exec = next((s for s in execution.step_executions if s.step_id == step_id), None)
        if not step_exec or step_exec.status == "completed":
            return False
        
        step_exec.status = "completed"
        step_exec.completed_at = datetime.utcnow()
        step_exec.outcome = outcome
        step_exec.notes = notes
        
        execution.steps_completed += 1
        execution.progress_percent = (execution.steps_completed / execution.total_steps) * 100
        
        # Advance to next step
        execution.current_step += 1
        if execution.current_step < len(execution.step_executions):
            next_step = execution.step_executions[execution.current_step]
            next_step.status = "in_progress"
            next_step.started_at = datetime.utcnow()
        else:
            # All steps completed
            execution.status = "completed"
            execution.completed_at = datetime.utcnow()
            execution.outcome = "success"
        
        execution.updated_at = datetime.utcnow()
        return True
    
    async def skip_step(
        self,
        execution_id: str,
        step_id: str,
        reason: str = ""
    ) -> bool:
        """Skip a step in an execution."""
        execution = self.executions.get(execution_id)
        if not execution or execution.status != "active":
            return False
        
        step_exec = next((s for s in execution.step_executions if s.step_id == step_id), None)
        if not step_exec:
            return False
        
        step_exec.status = "skipped"
        step_exec.notes = reason
        
        # Advance to next step
        execution.current_step += 1
        if execution.current_step < len(execution.step_executions):
            next_step = execution.step_executions[execution.current_step]
            next_step.status = "in_progress"
            next_step.started_at = datetime.utcnow()
        
        execution.updated_at = datetime.utcnow()
        return True
    
    async def pause_execution(self, execution_id: str) -> bool:
        """Pause an execution."""
        execution = self.executions.get(execution_id)
        if not execution or execution.status != "active":
            return False
        
        execution.status = "paused"
        execution.paused_at = datetime.utcnow()
        execution.updated_at = datetime.utcnow()
        return True
    
    async def resume_execution(self, execution_id: str) -> bool:
        """Resume a paused execution."""
        execution = self.executions.get(execution_id)
        if not execution or execution.status != "paused":
            return False
        
        execution.status = "active"
        execution.paused_at = None
        execution.updated_at = datetime.utcnow()
        return True
    
    async def abandon_execution(
        self,
        execution_id: str,
        reason: str = ""
    ) -> bool:
        """Abandon an execution."""
        execution = self.executions.get(execution_id)
        if not execution or execution.status in ["completed", "abandoned"]:
            return False
        
        execution.status = "abandoned"
        execution.outcome = "abandoned"
        execution.outcome_notes = reason
        execution.completed_at = datetime.utcnow()
        execution.updated_at = datetime.utcnow()
        return True
    
    # Recommendations
    async def get_recommended_playbooks(
        self,
        deal_stage: Optional[str] = None,
        industry: Optional[str] = None,
        segment: Optional[str] = None,
        limit: int = 5
    ) -> list[Playbook]:
        """Get recommended playbooks."""
        playbooks = await self.list_playbooks(status=PlaybookStatus.PUBLISHED)
        
        # Score playbooks based on match
        scored = []
        for pb in playbooks:
            score = 0
            
            if deal_stage and deal_stage in pb.deal_stages:
                score += 3
            if industry and industry in pb.industries:
                score += 2
            if segment and segment in pb.segments:
                score += 2
            
            # Boost by success rate
            score += pb.success_rate / 20
            
            scored.append((pb, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return [pb for pb, _ in scored[:limit]]
    
    # Analytics
    async def get_playbook_analytics(
        self,
        playbook_id: str
    ) -> dict[str, Any]:
        """Get analytics for a playbook."""
        playbook = self.playbooks.get(playbook_id)
        if not playbook:
            return {}
        
        executions = [e for e in self.executions.values() if e.playbook_id == playbook_id]
        
        completed = [e for e in executions if e.status == "completed"]
        abandoned = [e for e in executions if e.status == "abandoned"]
        active = [e for e in executions if e.status == "active"]
        
        # Average completion time
        avg_days = 0
        if completed:
            total_days = sum(
                (e.completed_at - e.started_at).days
                for e in completed
                if e.completed_at
            )
            avg_days = total_days / len(completed)
        
        # Step completion rates
        step_stats = {}
        for step in playbook.steps:
            step_execs = [
                se for e in executions
                for se in e.step_executions
                if se.step_id == step.id
            ]
            completed_count = len([s for s in step_execs if s.status == "completed"])
            step_stats[step.id] = {
                "name": step.name,
                "total": len(step_execs),
                "completed": completed_count,
                "completion_rate": completed_count / len(step_execs) if step_execs else 0,
            }
        
        return {
            "playbook_id": playbook_id,
            "total_executions": len(executions),
            "completed": len(completed),
            "abandoned": len(abandoned),
            "active": len(active),
            "completion_rate": len(completed) / len(executions) if executions else 0,
            "avg_completion_days": avg_days,
            "step_stats": step_stats,
        }


# Singleton instance
_playbook_service: Optional[PlaybookService] = None


def get_playbook_service() -> PlaybookService:
    """Get playbook service singleton."""
    global _playbook_service
    if _playbook_service is None:
        _playbook_service = PlaybookService()
    return _playbook_service
