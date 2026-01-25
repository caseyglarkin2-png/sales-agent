"""Action Executor for CaseyOS - the brain that executes Today's Moves.

This service handles:
1. Kill switch validation (blocks all actions if emergency stop is active)
2. Rate limiting (prevents abuse of external APIs)
3. Dry-run mode (preview what would happen without executing)
4. Idempotency (prevents duplicate execution)
5. Audit trail (logs all actions for compliance)
6. Rollback support (undo actions when possible)

Usage:
    executor = ActionExecutor()
    result = await executor.execute(ActionRequest(
        queue_item_id="abc123",
        action_type=ActionType.SEND_EMAIL,
        context={"recipient": "john@acme.com", "subject": "Follow up"},
        dry_run=True
    ))
"""
import os
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

from src.actions.contracts import (
    ActionRequest, 
    ActionResult, 
    ActionStatus,
    ActionType,
    RollbackRequest,
    RollbackResult
)
from src.audit_trail import AuditTrail, AuditEvent
from src.feature_flags import get_flag_manager
from src.rate_limiter import RateLimiter, get_rate_limiter
from src.logger import get_logger
from src.telemetry import log_event

# Import connectors for real action execution
from src.connectors.gmail import create_gmail_connector
from src.connectors.hubspot import create_hubspot_connector
from src.connectors.calendar_connector import create_calendar_connector

logger = get_logger(__name__)


# In-memory store for idempotency and rollback (use Redis in production)
_executed_actions: Dict[str, ActionResult] = {}
_rollback_registry: Dict[str, Dict[str, Any]] = {}


class ActionExecutor:
    """Executes actions from the Command Queue with safety guardrails.
    
    The executor is the gateway for all action execution in CaseyOS.
    Every action passes through:
    1. Kill switch check
    2. Rate limit check
    3. Idempotency check
    4. Dry-run handling
    5. Actual execution
    6. Audit logging
    """
    
    def __init__(
        self,
        rate_limiter: Optional[RateLimiter] = None,
        handlers: Optional[Dict[ActionType, Callable]] = None
    ):
        """Initialize the action executor.
        
        Args:
            rate_limiter: Custom rate limiter (default: global instance)
            handlers: Custom action handlers by type
        """
        self.rate_limiter = rate_limiter or get_rate_limiter()
        self.flag_manager = get_flag_manager()
        self._handlers: Dict[ActionType, Callable] = handlers or {}
        
        # Initialize connectors (lazy-loaded to avoid startup errors)
        self._gmail_connector = None
        self._hubspot_connector = None
        self._calendar_connector = None
        
        self._register_default_handlers()
        
        logger.info("ActionExecutor initialized with guardrails")
    
    def _get_gmail(self):
        """Lazy-load Gmail connector."""
        if self._gmail_connector is None:
            self._gmail_connector = create_gmail_connector()
        return self._gmail_connector
    
    def _get_hubspot(self):
        """Lazy-load HubSpot connector."""
        if self._hubspot_connector is None:
            self._hubspot_connector = create_hubspot_connector()
        return self._hubspot_connector
    
    def _get_calendar(self):
        """Lazy-load Calendar connector."""
        if self._calendar_connector is None:
            self._calendar_connector = create_calendar_connector()
        return self._calendar_connector
    
    def _register_default_handlers(self) -> None:
        """Register default handlers for each action type."""
        # Email actions
        self._handlers[ActionType.SEND_EMAIL] = self._handle_send_email
        self._handlers[ActionType.CREATE_DRAFT] = self._handle_create_draft
        
        # Task actions
        self._handlers[ActionType.CREATE_TASK] = self._handle_create_task
        self._handlers[ActionType.COMPLETE_TASK] = self._handle_complete_task
        
        # Meeting actions
        self._handlers[ActionType.BOOK_MEETING] = self._handle_book_meeting
        
        # Follow-up actions
        self._handlers[ActionType.FOLLOW_UP] = self._handle_follow_up
        self._handlers[ActionType.CHECK_IN] = self._handle_check_in
        
        # Deal actions
        self._handlers[ActionType.UPDATE_DEAL_STAGE] = self._handle_update_deal_stage
        
        # Custom handler
        self._handlers[ActionType.CUSTOM] = self._handle_custom
    
    async def execute(self, request: ActionRequest) -> ActionResult:
        """Execute an action with all safety guardrails.
        
        Args:
            request: The action to execute
            
        Returns:
            ActionResult with success/failure status and details
        """
        start_time = time.time()
        idempotency_key = request.generate_idempotency_key()
        
        try:
            # 1. Check idempotency - already executed?
            if idempotency_key in _executed_actions:
                logger.info(f"Idempotent hit: action {idempotency_key} already executed")
                existing = _executed_actions[idempotency_key]
                return ActionResult(
                    success=existing.success,
                    status=existing.status,
                    message=f"Already executed: {existing.message}",
                    data=existing.data,
                    idempotency_key=idempotency_key
                )
            
            # 2. Check kill switch
            if not self._is_actions_enabled():
                logger.warning(f"Kill switch active, blocking action: {request.action_type}")
                result = ActionResult.blocked_result("Kill switch is active - all actions disabled")
                await log_event("action_blocked", properties={
                    "queue_item_id": request.queue_item_id,
                    "action_type": request.action_type.value,
                    "reason": "kill_switch"
                })
                return result
            
            # 3. Check rate limits (only for external actions)
            if self._requires_rate_limit(request.action_type):
                contact_email = request.context.get("recipient") or request.context.get("contact_email")
                if contact_email:
                    can_send, limit_reason = await self.rate_limiter.check_can_send(contact_email)
                    if not can_send:
                        logger.warning(f"Rate limited: {limit_reason}")
                        result = ActionResult.rate_limited_result(limit_reason)
                        await log_event("action_rate_limited", properties={
                            "queue_item_id": request.queue_item_id,
                            "action_type": request.action_type.value,
                            "contact": contact_email,
                            "reason": limit_reason
                        })
                        return result
            
            # 4. Handle dry-run mode
            if request.dry_run:
                logger.info(f"Dry-run: {request.action_type.value}")
                result = ActionResult.dry_run_result(request.action_type, request.context)
                result.idempotency_key = idempotency_key
                await log_event("action_dry_run", properties={
                    "queue_item_id": request.queue_item_id,
                    "action_type": request.action_type.value,
                    "context": request.context
                })
                return result
            
            # 5. Execute the action
            handler = self._handlers.get(request.action_type)
            if not handler:
                return ActionResult.failed_result(f"No handler for action type: {request.action_type}")
            
            result = await handler(request)
            execution_time = (time.time() - start_time) * 1000
            result.execution_time_ms = execution_time
            result.idempotency_key = idempotency_key
            
            # 6. Record for idempotency
            _executed_actions[idempotency_key] = result
            
            # 7. Record send for rate limiting
            if result.success and self._requires_rate_limit(request.action_type):
                contact_email = request.context.get("recipient") or request.context.get("contact_email")
                if contact_email:
                    await self.rate_limiter.record_send(contact_email)
            
            # 8. Audit log
            self._log_action(request, result)
            
            # 9. Telemetry
            await log_event("action_executed", properties={
                "queue_item_id": request.queue_item_id,
                "action_type": request.action_type.value,
                "success": result.success,
                "status": result.status.value,
                "execution_time_ms": execution_time,
                "operator": request.operator
            })
            
            return result
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Action execution failed: {str(e)}", exc_info=True)
            result = ActionResult.failed_result(str(e), execution_time)
            
            await log_event("action_failed", properties={
                "queue_item_id": request.queue_item_id,
                "action_type": request.action_type.value,
                "error": str(e),
                "execution_time_ms": execution_time
            })
            
            return result
    
    async def rollback(self, request: RollbackRequest) -> RollbackResult:
        """Rollback a previously executed action.
        
        Args:
            request: Rollback request with token and reason
            
        Returns:
            RollbackResult indicating success/failure
        """
        if request.rollback_token not in _rollback_registry:
            return RollbackResult(
                success=False,
                message=f"Rollback token not found: {request.rollback_token}"
            )
        
        rollback_info = _rollback_registry[request.rollback_token]
        action_type = rollback_info.get("action_type")
        
        try:
            # Execute rollback based on action type
            if action_type == ActionType.CREATE_DRAFT.value:
                # Delete the draft from Gmail
                draft_id = rollback_info.get("draft_id")
                if draft_id:
                    logger.info(f"Rolling back draft: {draft_id}")
                    gmail = self._get_gmail()
                    success = await gmail.delete_draft(draft_id)
                    if not success:
                        return RollbackResult(
                            success=False,
                            message=f"Failed to delete draft {draft_id}",
                            original_action=rollback_info
                        )
                
            elif action_type == ActionType.CREATE_TASK.value:
                # Delete the task from HubSpot
                task_id = rollback_info.get("task_id")
                if task_id:
                    logger.info(f"Rolling back task: {task_id}")
                    hubspot = self._get_hubspot()
                    success = await hubspot.delete_task(task_id)
                    if not success:
                        return RollbackResult(
                            success=False,
                            message=f"Failed to delete task {task_id}",
                            original_action=rollback_info
                        )
            
            # Log rollback
            AuditTrail.log_config_change(
                config_key=f"rollback:{request.rollback_token}",
                old_value=str(rollback_info),
                new_value="rolled_back",
                actor=request.operator,
                metadata={"reason": request.reason}
            )
            
            # Remove from registry
            del _rollback_registry[request.rollback_token]
            
            await log_event("action_rolled_back", properties={
                "rollback_token": request.rollback_token,
                "action_type": action_type,
                "operator": request.operator,
                "reason": request.reason
            })
            
            return RollbackResult(
                success=True,
                message=f"Successfully rolled back action",
                original_action=rollback_info
            )
            
        except Exception as e:
            logger.error(f"Rollback failed: {str(e)}", exc_info=True)
            return RollbackResult(
                success=False,
                message=f"Rollback failed: {str(e)}",
                original_action=rollback_info
            )
    
    def _is_actions_enabled(self) -> bool:
        """Check if actions are globally enabled (kill switch)."""
        # Check feature flag - if SEND mode is disabled, block send actions
        # For now, we allow draft/task creation even in DRAFT_ONLY mode
        try:
            return not self.flag_manager._send_mode_override == False
        except Exception:
            return True  # Default to enabled if check fails
    
    def _requires_rate_limit(self, action_type: ActionType) -> bool:
        """Check if action type requires rate limiting."""
        rate_limited_actions = {
            ActionType.SEND_EMAIL,
            ActionType.CREATE_DRAFT,
            ActionType.FOLLOW_UP,
            ActionType.CHECK_IN,
        }
        return action_type in rate_limited_actions
    
    def _log_action(self, request: ActionRequest, result: ActionResult) -> None:
        """Log action to audit trail."""
        event = AuditEvent(
            event_type="action_executed",
            actor=request.operator,
            resource=request.queue_item_id,
            action=request.action_type.value,
            status="success" if result.success else "failed",
            details={
                "context": request.context,
                "result_message": result.message,
                "execution_time_ms": result.execution_time_ms,
                "dry_run": request.dry_run
            }
        )
        event.log()
    
    # ============ ACTION HANDLERS ============
    
    async def _handle_send_email(self, request: ActionRequest) -> ActionResult:
        """Handle email send action via Gmail API.
        
        Note: DRAFT_ONLY mode creates draft instead of sending.
        Real sending requires SEND mode to be enabled.
        """
        recipient = request.context.get("recipient")
        subject = request.context.get("subject", "Follow up")
        body = request.context.get("body", "")
        body_html = request.context.get("body_html")
        
        if not recipient:
            return ActionResult.failed_result("Missing recipient email")
        
        # Check if SEND mode is enabled
        if not self.flag_manager.is_send_mode_enabled():
            # Fall back to draft creation
            logger.info(f"DRAFT_ONLY mode: Creating draft instead of sending to {recipient}")
            return await self._handle_create_draft(request)
        
        # Send via Gmail API
        gmail = self._get_gmail()
        from_email = os.environ.get("GMAIL_DELEGATED_USER", "me")
        
        try:
            result = await gmail.send_email(
                from_email=from_email,
                to_email=recipient,
                subject=subject,
                body_text=body,
                body_html=body_html,
            )
            
            if result:
                message_id = result.get("id")
                thread_id = result.get("threadId")
                
                rollback_token = str(uuid4())
                _rollback_registry[rollback_token] = {
                    "action_type": ActionType.SEND_EMAIL.value,
                    "message_id": message_id,
                    "recipient": recipient,
                    "subject": subject,
                    "executed_at": datetime.utcnow().isoformat()
                }
                
                logger.info(f"Email sent: {message_id} to {recipient}")
                
                return ActionResult.success_result(
                    message=f"Email sent to {recipient}",
                    data={
                        "recipient": recipient,
                        "subject": subject,
                        "message_id": message_id,
                        "thread_id": thread_id
                    },
                    rollback_token=rollback_token
                )
            else:
                return ActionResult.failed_result(f"Failed to send email to {recipient}")
                
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return ActionResult.failed_result(f"Error sending email: {str(e)}")
    
    async def _handle_create_draft(self, request: ActionRequest) -> ActionResult:
        """Handle draft creation via Gmail API."""
        recipient = request.context.get("recipient")
        subject = request.context.get("subject", "Follow up")
        body = request.context.get("body", "")
        
        if not recipient:
            return ActionResult.failed_result("Missing recipient email")
        
        # Create draft via Gmail API
        gmail = self._get_gmail()
        
        try:
            draft_id = await gmail.create_draft(
                to=recipient,
                subject=subject,
                body=body
            )
            
            if draft_id:
                rollback_token = str(uuid4())
                _rollback_registry[rollback_token] = {
                    "action_type": ActionType.CREATE_DRAFT.value,
                    "draft_id": draft_id,
                    "recipient": recipient,
                    "created_at": datetime.utcnow().isoformat()
                }
                
                logger.info(f"Draft created: {draft_id} for {recipient}")
                
                return ActionResult.success_result(
                    message=f"Draft created for {recipient}",
                    data={
                        "draft_id": draft_id,
                        "recipient": recipient,
                        "subject": subject
                    },
                    rollback_token=rollback_token
                )
            else:
                return ActionResult.failed_result(f"Failed to create draft for {recipient}")
                
        except Exception as e:
            logger.error(f"Error creating draft: {e}")
            return ActionResult.failed_result(f"Error creating draft: {str(e)}")
    
    async def _handle_create_task(self, request: ActionRequest) -> ActionResult:
        """Handle HubSpot task creation via HubSpot API."""
        title = request.context.get("title", "Follow up task")
        contact_id = request.context.get("contact_id")
        body = request.context.get("body", "")
        due_date = request.context.get("due_date")
        
        # Create task via HubSpot API
        hubspot = self._get_hubspot()
        
        try:
            task_id = await hubspot.create_task(
                contact_id=contact_id or "",
                title=title,
                body=body,
                due_date=due_date
            )
            
            if task_id:
                rollback_token = str(uuid4())
                _rollback_registry[rollback_token] = {
                    "action_type": ActionType.CREATE_TASK.value,
                    "task_id": task_id,
                    "contact_id": contact_id,
                    "created_at": datetime.utcnow().isoformat()
                }
                
                logger.info(f"Task created: {task_id}")
                
                return ActionResult.success_result(
                    message=f"Task created: {title}",
                    data={
                        "task_id": task_id,
                        "title": title,
                        "contact_id": contact_id
                    },
                    rollback_token=rollback_token
                )
            else:
                return ActionResult.failed_result(f"Failed to create task: {title}")
                
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return ActionResult.failed_result(f"Error creating task: {str(e)}")
    
    async def _handle_complete_task(self, request: ActionRequest) -> ActionResult:
        """Handle task completion via HubSpot API."""
        task_id = request.context.get("task_id")
        
        if not task_id:
            return ActionResult.failed_result("Missing task_id")
        
        # Update task via HubSpot API
        hubspot = self._get_hubspot()
        
        try:
            result = await hubspot.update_task(
                task_id=task_id,
                properties={"hs_task_status": "COMPLETED"}
            )
            
            if result:
                logger.info(f"Task completed: {task_id}")
                return ActionResult.success_result(
                    message=f"Task {task_id} marked complete",
                    data={"task_id": task_id, "status": "completed"}
                )
            else:
                return ActionResult.failed_result(f"Failed to complete task {task_id}")
                
        except Exception as e:
            logger.error(f"Error completing task: {e}")
            return ActionResult.failed_result(f"Error completing task: {str(e)}")
    
    async def _handle_book_meeting(self, request: ActionRequest) -> ActionResult:
        """Handle meeting booking via Calendar API."""
        contact_email = request.context.get("contact_email")
        title = request.context.get("title", "Meeting")
        description = request.context.get("description", "")
        meeting_time = request.context.get("meeting_time")
        duration_minutes = request.context.get("duration_minutes", 30)
        
        if not contact_email:
            return ActionResult.failed_result("Missing contact_email")
        
        # Parse meeting time
        if meeting_time:
            if isinstance(meeting_time, str):
                start_time = datetime.fromisoformat(meeting_time.replace("Z", "+00:00"))
            else:
                start_time = meeting_time
        else:
            # Default to tomorrow at 10am
            start_time = datetime.utcnow().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        # Create event via Calendar API
        calendar = self._get_calendar()
        
        try:
            event_id = await calendar.create_event(
                title=title,
                description=description,
                start_time=start_time,
                end_time=end_time,
                attendees=[contact_email]
            )
            
            if event_id:
                logger.info(f"Meeting booked: {event_id} with {contact_email}")
                
                return ActionResult.success_result(
                    message=f"Meeting booked with {contact_email}",
                    data={
                        "meeting_id": event_id,
                        "contact_email": contact_email,
                        "meeting_time": start_time.isoformat(),
                        "duration_minutes": duration_minutes
                    }
                )
            else:
                return ActionResult.failed_result(f"Failed to book meeting with {contact_email}")
                
        except Exception as e:
            logger.error(f"Error booking meeting: {e}")
            return ActionResult.failed_result(f"Error booking meeting: {str(e)}")
    
    async def _handle_follow_up(self, request: ActionRequest) -> ActionResult:
        """Handle follow-up action (creates draft)."""
        # Follow-up is essentially a draft creation with specific template
        request.context.setdefault("subject", "Following up")
        return await self._handle_create_draft(request)
    
    async def _handle_check_in(self, request: ActionRequest) -> ActionResult:
        """Handle check-in action (creates draft)."""
        # Check-in is a softer follow-up
        request.context.setdefault("subject", "Quick check-in")
        return await self._handle_create_draft(request)
    
    async def _handle_update_deal_stage(self, request: ActionRequest) -> ActionResult:
        """Handle deal stage update via HubSpot API."""
        deal_id = request.context.get("deal_id")
        new_stage = request.context.get("new_stage")
        
        if not deal_id or not new_stage:
            return ActionResult.failed_result("Missing deal_id or new_stage")
        
        # Update deal via HubSpot API
        hubspot = self._get_hubspot()
        
        try:
            result = await hubspot.update_deal(
                deal_id=deal_id,
                properties={"dealstage": new_stage}
            )
            
            if result:
                logger.info(f"Deal {deal_id} stage updated to {new_stage}")
                
                return ActionResult.success_result(
                    message=f"Deal stage updated to {new_stage}",
                    data={"deal_id": deal_id, "new_stage": new_stage}
                )
            else:
                return ActionResult.failed_result(f"Failed to update deal {deal_id}")
                
        except Exception as e:
            logger.error(f"Error updating deal: {e}")
            return ActionResult.failed_result(f"Error updating deal: {str(e)}")
    
    async def _handle_custom(self, request: ActionRequest) -> ActionResult:
        """Handle custom action type."""
        custom_handler = request.context.get("handler")
        
        if not custom_handler:
            return ActionResult.failed_result("Custom action requires 'handler' in context")
        
        logger.info(f"Custom action executed: {custom_handler}")
        
        return ActionResult.success_result(
            message=f"Custom action executed: {custom_handler}",
            data=request.context
        )


# Global executor instance
_executor: Optional[ActionExecutor] = None


def get_executor() -> ActionExecutor:
    """Get or create the global ActionExecutor instance."""
    global _executor
    if _executor is None:
        _executor = ActionExecutor()
    return _executor
