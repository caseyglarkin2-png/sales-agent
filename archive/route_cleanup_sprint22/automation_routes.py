"""
Automation Routes - Rule-Based Automation API
==============================================
REST API endpoints for automation rule management and execution.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Any, Optional
from pydantic import BaseModel

from ..automation import (
    AutomationService,
    TriggerType,
    ConditionOperator,
    ActionType,
    get_automation_service,
)
from ..automation.automation_service import EntityType


router = APIRouter(prefix="/automation", tags=["Automation"])


# Request models
class CreateRuleRequest(BaseModel):
    """Create rule request."""
    name: str
    entity_type: str
    trigger_type: str
    description: Optional[str] = None
    trigger_config: Optional[dict[str, Any]] = None
    conditions: Optional[list[dict[str, Any]]] = None
    condition_logic: str = "all"
    actions: Optional[list[dict[str, Any]]] = None
    priority: int = 0


class UpdateRuleRequest(BaseModel):
    """Update rule request."""
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_config: Optional[dict[str, Any]] = None
    condition_logic: Optional[str] = None
    priority: Optional[int] = None
    cooldown_seconds: Optional[int] = None
    max_executions: Optional[int] = None


class AddConditionRequest(BaseModel):
    """Add condition request."""
    field: str
    operator: str
    value: Optional[Any] = None
    secondary_value: Optional[Any] = None
    logic: str = "and"
    group_id: Optional[str] = None


class AddActionRequest(BaseModel):
    """Add action request."""
    action_type: str
    config: dict[str, Any] = {}
    order: Optional[int] = None
    delay_seconds: int = 0
    continue_on_error: bool = True


class TriggerManuallyRequest(BaseModel):
    """Trigger manually request."""
    entity_type: str
    entity_id: str
    entity_data: Optional[dict[str, Any]] = None


class EvaluateTriggerRequest(BaseModel):
    """Evaluate trigger request."""
    trigger_type: str
    entity_type: str
    entity_id: str
    entity_data: dict[str, Any]
    trigger_data: Optional[dict[str, Any]] = None


def get_service() -> AutomationService:
    """Get automation service instance."""
    return get_automation_service()


# Types and enums
@router.get("/triggers")
async def list_trigger_types():
    """List available trigger types."""
    return {
        "triggers": [
            {"value": t.value, "name": t.name}
            for t in TriggerType
        ]
    }


@router.get("/operators")
async def list_condition_operators():
    """List available condition operators."""
    return {
        "operators": [
            {"value": o.value, "name": o.name}
            for o in ConditionOperator
        ]
    }


@router.get("/actions")
async def list_action_types():
    """List available action types."""
    return {
        "actions": [
            {"value": a.value, "name": a.name}
            for a in ActionType
        ]
    }


@router.get("/entity-types")
async def list_entity_types():
    """List entity types for automation."""
    return {
        "entity_types": [
            {"value": e.value, "name": e.name}
            for e in EntityType
        ]
    }


# Rule CRUD
@router.post("/rules")
async def create_rule(request: CreateRuleRequest):
    """Create a new automation rule."""
    service = get_service()
    
    try:
        entity_type = EntityType(request.entity_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity type")
    
    try:
        trigger_type = TriggerType(request.trigger_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid trigger type")
    
    rule = await service.create_rule(
        name=request.name,
        entity_type=entity_type,
        trigger_type=trigger_type,
        description=request.description,
        trigger_config=request.trigger_config,
        conditions=request.conditions,
        condition_logic=request.condition_logic,
        actions=request.actions,
        priority=request.priority,
    )
    
    return {
        "id": rule.id,
        "name": rule.name,
        "entity_type": rule.entity_type.value,
        "trigger_type": rule.trigger_type.value,
    }


@router.get("/rules")
async def list_rules(
    entity_type: Optional[str] = None,
    trigger_type: Optional[str] = None,
    active_only: bool = True,
):
    """List automation rules."""
    service = get_service()
    
    entity = None
    if entity_type:
        try:
            entity = EntityType(entity_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid entity type")
    
    trigger = None
    if trigger_type:
        try:
            trigger = TriggerType(trigger_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid trigger type")
    
    rules = await service.list_rules(entity, trigger, active_only)
    
    return {
        "rules": [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "entity_type": r.entity_type.value,
                "trigger_type": r.trigger_type.value,
                "conditions_count": len(r.conditions),
                "actions_count": len(r.actions),
                "is_active": r.is_active,
                "priority": r.priority,
                "execution_count": r.execution_count,
                "last_executed_at": r.last_executed_at.isoformat() if r.last_executed_at else None,
            }
            for r in rules
        ]
    }


@router.get("/rules/{rule_id}")
async def get_rule(rule_id: str):
    """Get automation rule by ID."""
    service = get_service()
    rule = await service.get_rule(rule_id)
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return {
        "id": rule.id,
        "name": rule.name,
        "description": rule.description,
        "entity_type": rule.entity_type.value,
        "trigger_type": rule.trigger_type.value,
        "trigger_config": rule.trigger_config,
        "conditions": [
            {
                "id": c.id,
                "field": c.field,
                "operator": c.operator.value,
                "value": c.value,
                "secondary_value": c.secondary_value,
                "logic": c.logic,
                "group_id": c.group_id,
            }
            for c in rule.conditions
        ],
        "condition_logic": rule.condition_logic,
        "actions": [
            {
                "id": a.id,
                "action_type": a.action_type.value,
                "config": a.config,
                "order": a.order,
                "delay_seconds": a.delay_seconds,
                "continue_on_error": a.continue_on_error,
            }
            for a in rule.actions
        ],
        "is_active": rule.is_active,
        "priority": rule.priority,
        "max_executions": rule.max_executions,
        "cooldown_seconds": rule.cooldown_seconds,
        "execution_count": rule.execution_count,
        "last_executed_at": rule.last_executed_at.isoformat() if rule.last_executed_at else None,
        "created_at": rule.created_at.isoformat(),
        "updated_at": rule.updated_at.isoformat(),
    }


@router.patch("/rules/{rule_id}")
async def update_rule(rule_id: str, request: UpdateRuleRequest):
    """Update automation rule."""
    service = get_service()
    
    updates = request.model_dump(exclude_unset=True)
    rule = await service.update_rule(rule_id, updates)
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return {"success": True, "rule_id": rule_id}


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str):
    """Delete automation rule."""
    service = get_service()
    
    if not await service.delete_rule(rule_id):
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return {"success": True}


@router.post("/rules/{rule_id}/enable")
async def enable_rule(rule_id: str):
    """Enable a rule."""
    service = get_service()
    
    rule = await service.toggle_rule(rule_id, True)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return {"success": True, "is_active": True}


@router.post("/rules/{rule_id}/disable")
async def disable_rule(rule_id: str):
    """Disable a rule."""
    service = get_service()
    
    rule = await service.toggle_rule(rule_id, False)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return {"success": True, "is_active": False}


@router.get("/rules/{rule_id}/stats")
async def get_rule_stats(rule_id: str):
    """Get rule statistics."""
    service = get_service()
    stats = await service.get_rule_stats(rule_id)
    
    if not stats:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return stats


# Rule conditions and actions
@router.post("/rules/{rule_id}/conditions")
async def add_condition(rule_id: str, request: AddConditionRequest):
    """Add a condition to a rule."""
    service = get_service()
    rule = await service.get_rule(rule_id)
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    try:
        operator = ConditionOperator(request.operator)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid operator")
    
    from ..automation.automation_service import RuleCondition
    import uuid
    
    condition = RuleCondition(
        id=str(uuid.uuid4()),
        field=request.field,
        operator=operator,
        value=request.value,
        secondary_value=request.secondary_value,
        logic=request.logic,
        group_id=request.group_id,
    )
    
    rule.conditions.append(condition)
    rule.updated_at = datetime.utcnow()
    
    return {
        "id": condition.id,
        "field": condition.field,
        "operator": condition.operator.value,
    }


@router.delete("/rules/{rule_id}/conditions/{condition_id}")
async def remove_condition(rule_id: str, condition_id: str):
    """Remove a condition from a rule."""
    service = get_service()
    rule = await service.get_rule(rule_id)
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    for i, c in enumerate(rule.conditions):
        if c.id == condition_id:
            rule.conditions.pop(i)
            return {"success": True}
    
    raise HTTPException(status_code=404, detail="Condition not found")


@router.post("/rules/{rule_id}/actions")
async def add_action(rule_id: str, request: AddActionRequest):
    """Add an action to a rule."""
    service = get_service()
    rule = await service.get_rule(rule_id)
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    try:
        action_type = ActionType(request.action_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid action type")
    
    from ..automation.automation_service import RuleAction
    import uuid
    
    order = request.order if request.order is not None else len(rule.actions)
    
    action = RuleAction(
        id=str(uuid.uuid4()),
        action_type=action_type,
        config=request.config,
        order=order,
        delay_seconds=request.delay_seconds,
        continue_on_error=request.continue_on_error,
    )
    
    rule.actions.append(action)
    rule.actions.sort(key=lambda a: a.order)
    rule.updated_at = datetime.utcnow()
    
    return {
        "id": action.id,
        "action_type": action.action_type.value,
        "order": action.order,
    }


@router.delete("/rules/{rule_id}/actions/{action_id}")
async def remove_action(rule_id: str, action_id: str):
    """Remove an action from a rule."""
    service = get_service()
    rule = await service.get_rule(rule_id)
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    for i, a in enumerate(rule.actions):
        if a.id == action_id:
            rule.actions.pop(i)
            return {"success": True}
    
    raise HTTPException(status_code=404, detail="Action not found")


# Execution
@router.post("/rules/{rule_id}/trigger")
async def trigger_manually(rule_id: str, request: TriggerManuallyRequest):
    """Manually trigger a rule."""
    service = get_service()
    
    try:
        entity_type = EntityType(request.entity_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity type")
    
    execution = await service.trigger_manually(
        rule_id=rule_id,
        entity_type=entity_type,
        entity_id=request.entity_id,
        entity_data=request.entity_data,
    )
    
    if not execution:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return {
        "id": execution.id,
        "rule_id": execution.rule_id,
        "status": execution.status,
        "actions_executed": len(execution.actions_executed),
    }


@router.post("/evaluate")
async def evaluate_trigger(request: EvaluateTriggerRequest):
    """Evaluate and execute rules for a trigger."""
    service = get_service()
    
    try:
        trigger_type = TriggerType(request.trigger_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid trigger type")
    
    try:
        entity_type = EntityType(request.entity_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity type")
    
    executions = await service.evaluate_trigger(
        trigger_type=trigger_type,
        entity_type=entity_type,
        entity_id=request.entity_id,
        entity_data=request.entity_data,
        trigger_data=request.trigger_data,
    )
    
    return {
        "executions": [
            {
                "id": e.id,
                "rule_id": e.rule_id,
                "status": e.status,
            }
            for e in executions
        ],
        "count": len(executions),
    }


@router.get("/executions/{execution_id}")
async def get_execution(execution_id: str):
    """Get execution by ID."""
    service = get_service()
    execution = await service.get_execution(execution_id)
    
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    return {
        "id": execution.id,
        "rule_id": execution.rule_id,
        "entity_type": execution.entity_type.value,
        "entity_id": execution.entity_id,
        "trigger_type": execution.trigger_type.value,
        "trigger_data": execution.trigger_data,
        "conditions_met": execution.conditions_met,
        "actions_executed": execution.actions_executed,
        "status": execution.status,
        "error": execution.error,
        "started_at": execution.started_at.isoformat(),
        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
    }


@router.get("/rules/{rule_id}/executions")
async def get_rule_executions(
    rule_id: str,
    limit: int = 50,
    offset: int = 0,
):
    """Get executions for a rule."""
    service = get_service()
    executions = await service.get_rule_executions(rule_id, limit, offset)
    
    return {
        "rule_id": rule_id,
        "executions": [
            {
                "id": e.id,
                "entity_type": e.entity_type.value,
                "entity_id": e.entity_id,
                "status": e.status,
                "started_at": e.started_at.isoformat(),
            }
            for e in executions
        ]
    }


@router.get("/entity/{entity_type}/{entity_id}/executions")
async def get_entity_executions(
    entity_type: str,
    entity_id: str,
    limit: int = 50,
):
    """Get executions for an entity."""
    service = get_service()
    
    try:
        entity = EntityType(entity_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity type")
    
    executions = await service.get_entity_executions(entity, entity_id, limit)
    
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "executions": [
            {
                "id": e.id,
                "rule_id": e.rule_id,
                "status": e.status,
                "started_at": e.started_at.isoformat(),
            }
            for e in executions
        ]
    }


# Stats
@router.get("/stats")
async def get_automation_stats():
    """Get overall automation statistics."""
    service = get_service()
    return await service.get_automation_stats()


# Add missing import
from datetime import datetime
