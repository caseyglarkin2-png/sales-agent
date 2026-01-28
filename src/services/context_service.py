"""Context Service - Enables context passing between agents in workflows.

Sprint 43.2: Manages workflow state and enables agents to pass context
to subsequent agents in multi-step workflows.
"""
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from src.logger import get_logger

logger = get_logger(__name__)


class WorkflowContext:
    """Container for workflow execution context."""
    
    def __init__(
        self,
        workflow_id: Optional[UUID] = None,
        initial_context: Optional[Dict[str, Any]] = None,
        ttl_minutes: int = 60,
    ):
        self.workflow_id = workflow_id or uuid4()
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(minutes=ttl_minutes)
        self.steps: List[Dict[str, Any]] = []
        self.shared_context: Dict[str, Any] = initial_context or {}
        self.current_step: int = 0
        self.status: str = "pending"  # pending, running, completed, failed
        
    def add_step_result(
        self,
        agent_name: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        success: bool = True,
        duration_ms: int = 0,
    ) -> None:
        """Record a step execution result."""
        self.steps.append({
            "step_number": len(self.steps) + 1,
            "agent_name": agent_name,
            "input": input_data,
            "output": output_data,
            "success": success,
            "duration_ms": duration_ms,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self.current_step = len(self.steps)
        
        # Merge output into shared context
        if success and output_data:
            self._merge_context(output_data)
    
    def _merge_context(self, data: Dict[str, Any]) -> None:
        """Merge step output into shared context."""
        # Extract key fields that should persist across steps
        extractable_keys = [
            "company_name", "company_info", "contact", "contacts",
            "deal", "deals", "research_data", "email_draft",
            "meeting_slots", "proposal", "stakeholders",
            "enriched_data", "insights", "recommendations",
        ]
        for key in extractable_keys:
            if key in data:
                self.shared_context[key] = data[key]
        
        # Also store last step output for reference
        self.shared_context["_last_output"] = data
    
    def get_context_for_next_step(self) -> Dict[str, Any]:
        """Get context to pass to the next agent."""
        return {
            "workflow_id": str(self.workflow_id),
            "step_number": self.current_step + 1,
            "previous_steps": [
                {"agent": s["agent_name"], "success": s["success"]}
                for s in self.steps
            ],
            **self.shared_context,
        }
    
    def is_expired(self) -> bool:
        """Check if context has expired."""
        return datetime.utcnow() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize context for storage."""
        return {
            "workflow_id": str(self.workflow_id),
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "steps": self.steps,
            "shared_context": self.shared_context,
            "current_step": self.current_step,
            "status": self.status,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowContext":
        """Deserialize context from storage."""
        ctx = cls(
            workflow_id=UUID(data["workflow_id"]),
            initial_context=data.get("shared_context", {}),
        )
        ctx.created_at = datetime.fromisoformat(data["created_at"])
        ctx.expires_at = datetime.fromisoformat(data["expires_at"])
        ctx.steps = data.get("steps", [])
        ctx.current_step = data.get("current_step", 0)
        ctx.status = data.get("status", "pending")
        return ctx


class ContextService:
    """Service for managing workflow contexts.
    
    Provides in-memory storage with optional Redis backend
    for persistence across restarts.
    """
    
    def __init__(self, redis_client=None):
        self._contexts: Dict[str, WorkflowContext] = {}
        self._redis = redis_client
        self._cache_prefix = "workflow_ctx:"
        
    async def create_context(
        self,
        initial_data: Optional[Dict[str, Any]] = None,
        ttl_minutes: int = 60,
    ) -> WorkflowContext:
        """Create a new workflow context."""
        ctx = WorkflowContext(initial_context=initial_data, ttl_minutes=ttl_minutes)
        ctx.status = "running"
        
        key = str(ctx.workflow_id)
        self._contexts[key] = ctx
        
        # Persist to Redis if available
        if self._redis:
            try:
                await self._redis.setex(
                    f"{self._cache_prefix}{key}",
                    ttl_minutes * 60,
                    json.dumps(ctx.to_dict()),
                )
            except Exception as e:
                logger.warning(f"Failed to persist context to Redis: {e}")
        
        logger.info(f"Created workflow context {ctx.workflow_id}")
        return ctx
    
    async def get_context(self, workflow_id: str) -> Optional[WorkflowContext]:
        """Retrieve a workflow context by ID."""
        # Check in-memory first
        if workflow_id in self._contexts:
            ctx = self._contexts[workflow_id]
            if not ctx.is_expired():
                return ctx
            else:
                # Clean up expired
                del self._contexts[workflow_id]
                return None
        
        # Try Redis
        if self._redis:
            try:
                data = await self._redis.get(f"{self._cache_prefix}{workflow_id}")
                if data:
                    ctx = WorkflowContext.from_dict(json.loads(data))
                    self._contexts[workflow_id] = ctx
                    return ctx
            except Exception as e:
                logger.warning(f"Failed to retrieve context from Redis: {e}")
        
        return None
    
    async def update_context(
        self,
        workflow_id: str,
        agent_name: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        success: bool = True,
        duration_ms: int = 0,
    ) -> Optional[WorkflowContext]:
        """Update context with a step result."""
        ctx = await self.get_context(workflow_id)
        if not ctx:
            logger.warning(f"Context not found: {workflow_id}")
            return None
        
        ctx.add_step_result(
            agent_name=agent_name,
            input_data=input_data,
            output_data=output_data,
            success=success,
            duration_ms=duration_ms,
        )
        
        # Persist update
        if self._redis:
            try:
                ttl = int((ctx.expires_at - datetime.utcnow()).total_seconds())
                if ttl > 0:
                    await self._redis.setex(
                        f"{self._cache_prefix}{workflow_id}",
                        ttl,
                        json.dumps(ctx.to_dict()),
                    )
            except Exception as e:
                logger.warning(f"Failed to update context in Redis: {e}")
        
        return ctx
    
    async def complete_context(
        self,
        workflow_id: str,
        status: str = "completed",
    ) -> Optional[WorkflowContext]:
        """Mark a workflow context as complete."""
        ctx = await self.get_context(workflow_id)
        if not ctx:
            return None
        
        ctx.status = status
        logger.info(f"Workflow {workflow_id} marked as {status}")
        return ctx
    
    async def cleanup_expired(self) -> int:
        """Remove expired contexts from memory."""
        expired_keys = [
            k for k, v in self._contexts.items()
            if v.is_expired()
        ]
        for key in expired_keys:
            del self._contexts[key]
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired contexts")
        
        return len(expired_keys)
    
    def get_active_count(self) -> int:
        """Get count of active (non-expired) contexts."""
        return sum(1 for ctx in self._contexts.values() if not ctx.is_expired())


# Singleton instance
_context_service: Optional[ContextService] = None


def get_context_service(redis_client=None) -> ContextService:
    """Get or create the context service singleton."""
    global _context_service
    if _context_service is None:
        _context_service = ContextService(redis_client)
    return _context_service
