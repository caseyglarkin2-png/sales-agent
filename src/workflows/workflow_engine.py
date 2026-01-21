"""
Workflow Automation Engine
==========================
Powerful workflow automation for complex multi-step sales processes.
Supports triggers, conditions, actions, branching, and parallel execution.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional
import structlog
import uuid

logger = structlog.get_logger(__name__)


class StepType(str, Enum):
    """Types of workflow steps."""
    SEND_EMAIL = "send_email"
    WAIT_DELAY = "wait_delay"
    WAIT_EVENT = "wait_event"
    CONDITION = "condition"
    HUBSPOT_UPDATE = "hubspot_update"
    SCORE_LEAD = "score_lead"
    ASSIGN_OWNER = "assign_owner"
    ADD_TO_SEQUENCE = "add_to_sequence"
    REMOVE_FROM_SEQUENCE = "remove_from_sequence"
    CREATE_TASK = "create_task"
    SEND_NOTIFICATION = "send_notification"
    WEBHOOK = "webhook"
    AI_GENERATE = "ai_generate"
    BRANCH = "branch"
    PARALLEL = "parallel"
    END = "end"


class TriggerType(str, Enum):
    """Types of workflow triggers."""
    CONTACT_CREATED = "contact_created"
    CONTACT_UPDATED = "contact_updated"
    FORM_SUBMISSION = "form_submission"
    EMAIL_OPENED = "email_opened"
    EMAIL_CLICKED = "email_clicked"
    EMAIL_REPLIED = "email_replied"
    MEETING_BOOKED = "meeting_booked"
    DEAL_STAGE_CHANGED = "deal_stage_changed"
    SCORE_THRESHOLD = "score_threshold"
    TAG_ADDED = "tag_added"
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    API_CALL = "api_call"


class ExecutionStatus(str, Enum):
    """Status of workflow execution."""
    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    id: str
    name: str
    step_type: StepType
    config: dict = field(default_factory=dict)
    next_step_id: Optional[str] = None
    on_success_step_id: Optional[str] = None
    on_failure_step_id: Optional[str] = None
    conditions: list[dict] = field(default_factory=list)
    timeout_seconds: int = 3600
    retry_count: int = 3
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "step_type": self.step_type.value,
            "config": self.config,
            "next_step_id": self.next_step_id,
            "on_success_step_id": self.on_success_step_id,
            "on_failure_step_id": self.on_failure_step_id,
            "conditions": self.conditions,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
        }


@dataclass
class WorkflowTrigger:
    """Trigger that starts a workflow."""
    id: str
    trigger_type: TriggerType
    conditions: list[dict] = field(default_factory=list)
    filters: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "trigger_type": self.trigger_type.value,
            "conditions": self.conditions,
            "filters": self.filters,
        }
    
    def matches(self, event: dict) -> bool:
        """Check if this trigger matches the given event."""
        if event.get("type") != self.trigger_type.value:
            return False
        
        for key, expected in self.filters.items():
            if event.get("data", {}).get(key) != expected:
                return False
        
        return True


@dataclass
class Workflow:
    """A complete workflow definition."""
    id: str
    name: str
    description: str = ""
    triggers: list[WorkflowTrigger] = field(default_factory=list)
    steps: dict[str, WorkflowStep] = field(default_factory=dict)
    entry_step_id: Optional[str] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)
    
    def add_step(self, step: WorkflowStep) -> None:
        """Add a step to the workflow."""
        self.steps[step.id] = step
        if self.entry_step_id is None:
            self.entry_step_id = step.id
    
    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """Get a step by ID."""
        return self.steps.get(step_id)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "triggers": [t.to_dict() for t in self.triggers],
            "steps": {k: v.to_dict() for k, v in self.steps.items()},
            "entry_step_id": self.entry_step_id,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class WorkflowExecution:
    """An instance of a workflow being executed."""
    id: str
    workflow_id: str
    contact_id: Optional[str] = None
    company_id: Optional[str] = None
    current_step_id: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.PENDING
    context: dict = field(default_factory=dict)
    step_results: dict = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    next_execution_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "contact_id": self.contact_id,
            "company_id": self.company_id,
            "current_step_id": self.current_step_id,
            "status": self.status.value,
            "context": self.context,
            "step_results": self.step_results,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "next_execution_at": self.next_execution_at.isoformat() if self.next_execution_at else None,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
        }


class WorkflowEngine:
    """
    Engine that executes workflows.
    Handles step execution, branching, waiting, and error recovery.
    """
    
    def __init__(self):
        self.workflows: dict[str, Workflow] = {}
        self.executions: dict[str, WorkflowExecution] = {}
        self.step_handlers: dict[StepType, Callable] = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self) -> None:
        """Register default step handlers."""
        self.step_handlers = {
            StepType.SEND_EMAIL: self._handle_send_email,
            StepType.WAIT_DELAY: self._handle_wait_delay,
            StepType.WAIT_EVENT: self._handle_wait_event,
            StepType.CONDITION: self._handle_condition,
            StepType.HUBSPOT_UPDATE: self._handle_hubspot_update,
            StepType.SCORE_LEAD: self._handle_score_lead,
            StepType.CREATE_TASK: self._handle_create_task,
            StepType.SEND_NOTIFICATION: self._handle_send_notification,
            StepType.WEBHOOK: self._handle_webhook,
            StepType.AI_GENERATE: self._handle_ai_generate,
            StepType.BRANCH: self._handle_branch,
            StepType.END: self._handle_end,
        }
    
    def register_workflow(self, workflow: Workflow) -> None:
        """Register a workflow."""
        self.workflows[workflow.id] = workflow
        logger.info("workflow_registered", workflow_id=workflow.id, name=workflow.name)
    
    def create_workflow(
        self,
        name: str,
        description: str = "",
        triggers: list[dict] = None,
    ) -> Workflow:
        """Create a new workflow."""
        workflow = Workflow(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
        )
        
        if triggers:
            for t in triggers:
                trigger = WorkflowTrigger(
                    id=str(uuid.uuid4()),
                    trigger_type=TriggerType(t["type"]),
                    conditions=t.get("conditions", []),
                    filters=t.get("filters", {}),
                )
                workflow.triggers.append(trigger)
        
        self.register_workflow(workflow)
        return workflow
    
    def add_step_to_workflow(
        self,
        workflow_id: str,
        name: str,
        step_type: StepType,
        config: dict = None,
        after_step_id: str = None,
    ) -> WorkflowStep:
        """Add a step to an existing workflow."""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        step = WorkflowStep(
            id=str(uuid.uuid4()),
            name=name,
            step_type=step_type,
            config=config or {},
        )
        
        if after_step_id and after_step_id in workflow.steps:
            workflow.steps[after_step_id].next_step_id = step.id
        
        workflow.add_step(step)
        return step
    
    async def trigger_workflow(
        self,
        workflow_id: str,
        contact_id: str = None,
        company_id: str = None,
        context: dict = None,
    ) -> WorkflowExecution:
        """Start a new workflow execution."""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        if not workflow.is_active:
            raise ValueError(f"Workflow {workflow_id} is not active")
        
        execution = WorkflowExecution(
            id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            contact_id=contact_id,
            company_id=company_id,
            current_step_id=workflow.entry_step_id,
            status=ExecutionStatus.RUNNING,
            context=context or {},
            started_at=datetime.utcnow(),
        )
        
        self.executions[execution.id] = execution
        
        logger.info(
            "workflow_execution_started",
            execution_id=execution.id,
            workflow_id=workflow_id,
            contact_id=contact_id,
        )
        
        # Start executing
        await self._execute_next_step(execution)
        
        return execution
    
    async def process_event(self, event: dict) -> list[WorkflowExecution]:
        """Process an event and trigger matching workflows."""
        triggered_executions = []
        
        for workflow in self.workflows.values():
            if not workflow.is_active:
                continue
            
            for trigger in workflow.triggers:
                if trigger.matches(event):
                    execution = await self.trigger_workflow(
                        workflow_id=workflow.id,
                        contact_id=event.get("data", {}).get("contact_id"),
                        company_id=event.get("data", {}).get("company_id"),
                        context={"trigger_event": event},
                    )
                    triggered_executions.append(execution)
        
        return triggered_executions
    
    async def _execute_next_step(self, execution: WorkflowExecution) -> None:
        """Execute the next step in the workflow."""
        workflow = self.workflows.get(execution.workflow_id)
        if not workflow or not execution.current_step_id:
            execution.status = ExecutionStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            return
        
        step = workflow.get_step(execution.current_step_id)
        if not step:
            execution.status = ExecutionStatus.FAILED
            execution.error_message = f"Step {execution.current_step_id} not found"
            return
        
        handler = self.step_handlers.get(step.step_type)
        if not handler:
            execution.status = ExecutionStatus.FAILED
            execution.error_message = f"No handler for step type {step.step_type}"
            return
        
        try:
            result = await handler(execution, step)
            execution.step_results[step.id] = {
                "status": "success",
                "result": result,
                "executed_at": datetime.utcnow().isoformat(),
            }
            
            # Determine next step
            if step.step_type == StepType.END:
                execution.status = ExecutionStatus.COMPLETED
                execution.completed_at = datetime.utcnow()
            elif step.step_type == StepType.WAIT_DELAY:
                execution.status = ExecutionStatus.WAITING
                execution.next_execution_at = datetime.utcnow() + timedelta(seconds=step.config.get("delay_seconds", 86400))
            elif step.step_type == StepType.WAIT_EVENT:
                execution.status = ExecutionStatus.WAITING
            elif step.step_type == StepType.CONDITION:
                # Condition handler sets next_step_id
                if execution.current_step_id:
                    await self._execute_next_step(execution)
            elif step.next_step_id:
                execution.current_step_id = step.next_step_id
                await self._execute_next_step(execution)
            else:
                execution.status = ExecutionStatus.COMPLETED
                execution.completed_at = datetime.utcnow()
                
        except Exception as e:
            logger.error("step_execution_failed", step_id=step.id, error=str(e))
            execution.retry_count += 1
            
            if execution.retry_count <= step.retry_count:
                # Schedule retry
                execution.status = ExecutionStatus.WAITING
                execution.next_execution_at = datetime.utcnow() + timedelta(minutes=5 * execution.retry_count)
            else:
                execution.status = ExecutionStatus.FAILED
                execution.error_message = str(e)
                
                if step.on_failure_step_id:
                    execution.current_step_id = step.on_failure_step_id
                    await self._execute_next_step(execution)
    
    async def resume_waiting_executions(self) -> list[WorkflowExecution]:
        """Resume executions that are past their wait time."""
        resumed = []
        now = datetime.utcnow()
        
        for execution in self.executions.values():
            if execution.status == ExecutionStatus.WAITING:
                if execution.next_execution_at and execution.next_execution_at <= now:
                    execution.status = ExecutionStatus.RUNNING
                    
                    # Move to next step
                    workflow = self.workflows.get(execution.workflow_id)
                    if workflow:
                        current_step = workflow.get_step(execution.current_step_id)
                        if current_step and current_step.next_step_id:
                            execution.current_step_id = current_step.next_step_id
                    
                    await self._execute_next_step(execution)
                    resumed.append(execution)
        
        return resumed
    
    # Step Handlers
    
    async def _handle_send_email(self, execution: WorkflowExecution, step: WorkflowStep) -> dict:
        """Handle send email step."""
        template_id = step.config.get("template_id")
        subject_override = step.config.get("subject")
        
        logger.info(
            "workflow_send_email",
            execution_id=execution.id,
            contact_id=execution.contact_id,
            template_id=template_id,
        )
        
        return {
            "action": "email_queued",
            "template_id": template_id,
            "contact_id": execution.contact_id,
        }
    
    async def _handle_wait_delay(self, execution: WorkflowExecution, step: WorkflowStep) -> dict:
        """Handle wait delay step."""
        delay_seconds = step.config.get("delay_seconds", 86400)
        delay_type = step.config.get("delay_type", "fixed")  # fixed, business_hours, specific_time
        
        return {
            "action": "waiting",
            "delay_seconds": delay_seconds,
            "delay_type": delay_type,
            "resume_at": (datetime.utcnow() + timedelta(seconds=delay_seconds)).isoformat(),
        }
    
    async def _handle_wait_event(self, execution: WorkflowExecution, step: WorkflowStep) -> dict:
        """Handle wait for event step."""
        event_type = step.config.get("event_type")
        timeout_seconds = step.config.get("timeout_seconds", 604800)  # 7 days default
        
        return {
            "action": "waiting_for_event",
            "event_type": event_type,
            "timeout_at": (datetime.utcnow() + timedelta(seconds=timeout_seconds)).isoformat(),
        }
    
    async def _handle_condition(self, execution: WorkflowExecution, step: WorkflowStep) -> dict:
        """Handle condition/branching step."""
        conditions = step.config.get("conditions", [])
        
        for condition in conditions:
            field = condition.get("field")
            operator = condition.get("operator")
            value = condition.get("value")
            next_step = condition.get("next_step_id")
            
            # Get field value from context
            actual_value = execution.context.get(field)
            
            matches = self._evaluate_condition(actual_value, operator, value)
            
            if matches:
                execution.current_step_id = next_step
                return {"action": "branched", "matched_condition": condition}
        
        # Default branch
        if step.next_step_id:
            execution.current_step_id = step.next_step_id
        
        return {"action": "default_branch"}
    
    async def _handle_hubspot_update(self, execution: WorkflowExecution, step: WorkflowStep) -> dict:
        """Handle HubSpot update step."""
        object_type = step.config.get("object_type", "contact")
        properties = step.config.get("properties", {})
        
        logger.info(
            "workflow_hubspot_update",
            execution_id=execution.id,
            object_type=object_type,
            properties=properties,
        )
        
        return {
            "action": "hubspot_updated",
            "object_type": object_type,
            "properties": properties,
        }
    
    async def _handle_score_lead(self, execution: WorkflowExecution, step: WorkflowStep) -> dict:
        """Handle lead scoring step."""
        score_adjustment = step.config.get("score_adjustment", 0)
        reason = step.config.get("reason", "workflow_action")
        
        return {
            "action": "lead_scored",
            "score_adjustment": score_adjustment,
            "reason": reason,
        }
    
    async def _handle_create_task(self, execution: WorkflowExecution, step: WorkflowStep) -> dict:
        """Handle task creation step."""
        task_title = step.config.get("title", "Follow up")
        task_type = step.config.get("type", "follow_up")
        due_days = step.config.get("due_days", 1)
        assignee = step.config.get("assignee")
        
        return {
            "action": "task_created",
            "title": task_title,
            "type": task_type,
            "due_date": (datetime.utcnow() + timedelta(days=due_days)).isoformat(),
            "assignee": assignee,
        }
    
    async def _handle_send_notification(self, execution: WorkflowExecution, step: WorkflowStep) -> dict:
        """Handle notification step."""
        channel = step.config.get("channel", "email")
        recipients = step.config.get("recipients", [])
        message = step.config.get("message", "Workflow notification")
        
        return {
            "action": "notification_sent",
            "channel": channel,
            "recipients": recipients,
        }
    
    async def _handle_webhook(self, execution: WorkflowExecution, step: WorkflowStep) -> dict:
        """Handle webhook step."""
        url = step.config.get("url")
        method = step.config.get("method", "POST")
        headers = step.config.get("headers", {})
        
        return {
            "action": "webhook_called",
            "url": url,
            "method": method,
        }
    
    async def _handle_ai_generate(self, execution: WorkflowExecution, step: WorkflowStep) -> dict:
        """Handle AI generation step."""
        prompt_template = step.config.get("prompt_template")
        output_field = step.config.get("output_field", "ai_output")
        
        # Would call OpenAI here
        execution.context[output_field] = f"AI-generated content for {execution.contact_id}"
        
        return {
            "action": "ai_generated",
            "output_field": output_field,
        }
    
    async def _handle_branch(self, execution: WorkflowExecution, step: WorkflowStep) -> dict:
        """Handle explicit branching step."""
        branches = step.config.get("branches", [])
        
        for branch in branches:
            if self._evaluate_branch_condition(execution, branch):
                execution.current_step_id = branch.get("next_step_id")
                return {"action": "branched", "branch": branch.get("name")}
        
        return {"action": "no_branch_matched"}
    
    async def _handle_end(self, execution: WorkflowExecution, step: WorkflowStep) -> dict:
        """Handle workflow end step."""
        final_status = step.config.get("final_status", "completed")
        
        return {
            "action": "workflow_ended",
            "final_status": final_status,
        }
    
    def _evaluate_condition(self, actual: Any, operator: str, expected: Any) -> bool:
        """Evaluate a single condition."""
        if operator == "equals":
            return actual == expected
        elif operator == "not_equals":
            return actual != expected
        elif operator == "contains":
            return expected in str(actual) if actual else False
        elif operator == "greater_than":
            return actual > expected if actual is not None else False
        elif operator == "less_than":
            return actual < expected if actual is not None else False
        elif operator == "is_empty":
            return not actual
        elif operator == "is_not_empty":
            return bool(actual)
        elif operator == "in_list":
            return actual in expected if isinstance(expected, list) else False
        return False
    
    def _evaluate_branch_condition(self, execution: WorkflowExecution, branch: dict) -> bool:
        """Evaluate branch conditions."""
        conditions = branch.get("conditions", [])
        match_type = branch.get("match_type", "all")  # all or any
        
        results = []
        for cond in conditions:
            field = cond.get("field")
            actual = execution.context.get(field)
            result = self._evaluate_condition(actual, cond.get("operator"), cond.get("value"))
            results.append(result)
        
        if match_type == "all":
            return all(results)
        return any(results)
    
    # Query methods
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow by ID."""
        return self.workflows.get(workflow_id)
    
    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get an execution by ID."""
        return self.executions.get(execution_id)
    
    def list_workflows(self, active_only: bool = True) -> list[Workflow]:
        """List all workflows."""
        workflows = list(self.workflows.values())
        if active_only:
            workflows = [w for w in workflows if w.is_active]
        return workflows
    
    def list_executions(
        self,
        workflow_id: str = None,
        status: ExecutionStatus = None,
        contact_id: str = None,
    ) -> list[WorkflowExecution]:
        """List executions with optional filters."""
        executions = list(self.executions.values())
        
        if workflow_id:
            executions = [e for e in executions if e.workflow_id == workflow_id]
        if status:
            executions = [e for e in executions if e.status == status]
        if contact_id:
            executions = [e for e in executions if e.contact_id == contact_id]
        
        return sorted(executions, key=lambda e: e.started_at or datetime.min, reverse=True)
    
    def pause_execution(self, execution_id: str) -> WorkflowExecution:
        """Pause an execution."""
        execution = self.executions.get(execution_id)
        if execution:
            execution.status = ExecutionStatus.PAUSED
        return execution
    
    def cancel_execution(self, execution_id: str) -> WorkflowExecution:
        """Cancel an execution."""
        execution = self.executions.get(execution_id)
        if execution:
            execution.status = ExecutionStatus.CANCELLED
            execution.completed_at = datetime.utcnow()
        return execution


# Singleton instance
_workflow_engine: Optional[WorkflowEngine] = None


def get_workflow_engine() -> WorkflowEngine:
    """Get the workflow engine singleton."""
    global _workflow_engine
    if _workflow_engine is None:
        _workflow_engine = WorkflowEngine()
        _setup_default_workflows(_workflow_engine)
    return _workflow_engine


def _setup_default_workflows(engine: WorkflowEngine) -> None:
    """Set up default workflow templates."""
    
    # New Lead Nurturing Workflow
    nurture_workflow = engine.create_workflow(
        name="New Lead Nurturing",
        description="Automatically nurture new leads through a multi-step sequence",
        triggers=[{
            "type": "form_submission",
            "conditions": [],
            "filters": {},
        }],
    )
    
    step1 = engine.add_step_to_workflow(
        nurture_workflow.id,
        "Send Welcome Email",
        StepType.SEND_EMAIL,
        {"template_id": "welcome_email"},
    )
    
    step2 = engine.add_step_to_workflow(
        nurture_workflow.id,
        "Wait 2 Days",
        StepType.WAIT_DELAY,
        {"delay_seconds": 172800},
        step1.id,
    )
    
    step3 = engine.add_step_to_workflow(
        nurture_workflow.id,
        "Check Engagement",
        StepType.CONDITION,
        {
            "conditions": [
                {"field": "email_opened", "operator": "equals", "value": True, "next_step_id": "high_engagement"},
                {"field": "email_opened", "operator": "equals", "value": False, "next_step_id": "low_engagement"},
            ]
        },
        step2.id,
    )
    
    # Meeting Booked Workflow
    meeting_workflow = engine.create_workflow(
        name="Meeting Booked Follow-up",
        description="Send confirmation and reminders for booked meetings",
        triggers=[{
            "type": "meeting_booked",
            "conditions": [],
            "filters": {},
        }],
    )
    
    m_step1 = engine.add_step_to_workflow(
        meeting_workflow.id,
        "Send Confirmation",
        StepType.SEND_EMAIL,
        {"template_id": "meeting_confirmation"},
    )
    
    m_step2 = engine.add_step_to_workflow(
        meeting_workflow.id,
        "Update HubSpot",
        StepType.HUBSPOT_UPDATE,
        {"object_type": "contact", "properties": {"meeting_booked": True}},
        m_step1.id,
    )
    
    m_step3 = engine.add_step_to_workflow(
        meeting_workflow.id,
        "Create Prep Task",
        StepType.CREATE_TASK,
        {"title": "Prepare for meeting", "due_days": 1},
        m_step2.id,
    )
    
    logger.info("default_workflows_setup", count=2)
